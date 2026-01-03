#!/usr/bin/env python3
"""
Stage 1: collect-sources - エピソード情報源収集パイプライン

このスクリプトは人物リストから関連情報源を収集します。

処理フロー:
1. 入力CSV（person_name, birth_year, person_type）またはコマンドライン引数から人物情報を取得
2. API経由（Wikidata, Wikipedia）またはCSV経由で情報源を収集
3. source_id（MD5ハッシュ）を生成して冪等性を保証
4. センシティブフィルター適用
5. episode_sources.csv に出力

使用例:
    # 手動CSVから収集（--execute なしはデフォルトで dry-run）
    python scripts/pipeline_collect_sources.py \\
        --input config/person_sources/manual_sources.csv \\
        --output generated/episode_sources.csv \\
        --mode manual

    # 本番実行
    python scripts/pipeline_collect_sources.py \\
        --input config/person_sources/manual_sources.csv \\
        --output generated/episode_sources.csv \\
        --mode manual \\
        --execute

    # API経由（Phase 2実装予定）
    python scripts/pipeline_collect_sources.py \\
        --input input_persons.csv \\
        --output generated/episode_sources.csv \\
        --mode api \\
        --sources wikidata,wikipedia \\
        --execute
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models.episode_source import EpisodeSource
from src.sensitive_filter import SensitiveFilter
from src.source_adapters.base import PersonCandidate

# ロガー設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


# API統合（graceful degradation）
try:
    from tenacity import retry, stop_after_attempt, wait_exponential

    TENACITY_AVAILABLE = True
except ImportError:
    logger.warning("tenacity not installed. Retry functionality disabled.")
    TENACITY_AVAILABLE = False

    # ダミーデコレータ
    def retry(*args, **kwargs):
        def decorator(func):
            return func

        return decorator

    stop_after_attempt = wait_exponential = lambda x: None

try:
    from qwikidata.sparql import return_sparql_query_results

    QWIKIDATA_AVAILABLE = True
except ImportError:
    logger.warning("qwikidata not installed. Wikidata API disabled.")
    QWIKIDATA_AVAILABLE = False

try:
    import wikipediaapi

    WIKIPEDIA_API_AVAILABLE = True
except ImportError:
    logger.warning("wikipedia-api not installed. Wikipedia API disabled.")
    WIKIPEDIA_API_AVAILABLE = False


class SourceCollector:
    """情報源収集クラス"""

    def __init__(
        self,
        mode: str = "manual",
        sources: Optional[List[str]] = None,
        sensitive_filter: Optional[SensitiveFilter] = None,
    ):
        """
        初期化

        Args:
            mode: 収集モード（manual, api, hybrid）
            sources: 使用するAPIソース（wikidata, wikipedia）
            sensitive_filter: センシティブフィルター
        """
        self.mode = mode
        self.sources = sources or []
        self.sensitive_filter = sensitive_filter or SensitiveFilter()
        self.collected_sources: List[EpisodeSource] = []
        self.skipped_sources: List[Dict] = []

        # API可用性チェック
        if mode in ["api", "hybrid"]:
            if "wikidata" in self.sources and not QWIKIDATA_AVAILABLE:
                logger.warning("Wikidata source requested but qwikidata not installed")
                self.sources.remove("wikidata")

            if "wikipedia" in self.sources and not WIKIPEDIA_API_AVAILABLE:
                logger.warning("Wikipedia source requested but wikipedia-api not installed")
                self.sources.remove("wikipedia")

    def collect_from_csv(self, input_csv: Path) -> List[EpisodeSource]:
        """
        手動CSVから情報源を収集

        CSVフォーマット:
            person_name, person_id, person_type, source_url, raw_text, context

        Args:
            input_csv: 入力CSVパス

        Returns:
            EpisodeSourceのリスト
        """
        logger.info(f"Collecting sources from CSV: {input_csv}")

        if not input_csv.exists():
            raise FileNotFoundError(f"Input CSV not found: {input_csv}")

        df = pd.read_csv(input_csv, encoding="utf-8-sig")

        # 必須カラムチェック
        required_columns = ["person_name", "source_url", "raw_text"]
        missing_columns = set(required_columns) - set(df.columns)
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

        sources = []
        for idx, row in df.iterrows():
            try:
                # センシティブフィルター適用
                candidate = PersonCandidate(
                    person_name=row["person_name"],
                    category=row.get("category", ""),
                    person_type=row.get("person_type", "REAL"),
                    description=row.get("description", ""),
                )

                is_sensitive, reason = self.sensitive_filter.is_sensitive(candidate)
                if is_sensitive:
                    self.skipped_sources.append(
                        {
                            "person_name": row["person_name"],
                            "source_url": row["source_url"],
                            "skip_reason": reason,
                        }
                    )
                    logger.warning(f"Skipped sensitive source: {row['person_name']} - {reason}")
                    continue

                # EpisodeSource生成
                source = EpisodeSource(
                    person_name=row["person_name"],
                    person_id=row.get("person_id", ""),
                    person_type=row.get("person_type", "REAL"),
                    source_url=row["source_url"],
                    source_type="manual",
                    raw_text=row["raw_text"],
                    context=row.get("context", ""),
                    evidence_quality=row.get("evidence_quality", "C"),
                )

                sources.append(source)

            except Exception as e:
                logger.error(f"Error processing row {idx}: {e}")
                self.skipped_sources.append(
                    {
                        "person_name": row.get("person_name", "UNKNOWN"),
                        "source_url": row.get("source_url", ""),
                        "skip_reason": f"processing_error: {e}",
                    }
                )

        logger.info(f"Collected {len(sources)} sources from CSV, skipped {len(self.skipped_sources)}")
        self.collected_sources.extend(sources)
        return sources

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch_from_wikidata(self, person_name: str, birth_year: Optional[int] = None) -> List[Dict]:
        """
        Wikidata APIから情報を取得

        Args:
            person_name: 人物名
            birth_year: 生年（フィルタリング用）

        Returns:
            Wikidataプロパティのリスト
        """
        if not QWIKIDATA_AVAILABLE:
            logger.warning("Wikidata API not available")
            return []

        logger.info(f"Fetching from Wikidata: {person_name}")

        query = f"""
        SELECT ?item ?itemLabel ?birthDate ?deathDate ?description WHERE {{
          ?item wdt:P31 wd:Q5.
          ?item rdfs:label "{person_name}"@ja.
          OPTIONAL {{ ?item wdt:P569 ?birthDate. }}
          OPTIONAL {{ ?item wdt:P570 ?deathDate. }}
          OPTIONAL {{ ?item schema:description ?description. FILTER(LANG(?description) = "ja") }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "ja". }}
        }}
        LIMIT 5
        """

        try:
            results = return_sparql_query_results(query)
            return results.get("results", {}).get("bindings", [])
        except Exception as e:
            logger.error(f"Wikidata API error: {e}")
            return []

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch_from_wikipedia(self, person_name: str, max_length: int = 250) -> Optional[Dict]:
        """
        Wikipedia APIから情報を取得

        Args:
            person_name: 人物名
            max_length: 最大テキスト長（著作権遵守）

        Returns:
            Wikipediaページ情報
        """
        if not WIKIPEDIA_API_AVAILABLE:
            logger.warning("Wikipedia API not available")
            return None

        logger.info(f"Fetching from Wikipedia: {person_name}")

        try:
            wiki = wikipediaapi.Wikipedia("ja")
            page = wiki.page(person_name)

            if not page.exists():
                logger.warning(f"Wikipedia page not found: {person_name}")
                return None

            # キーフレーズのみ抽出（著作権遵守）
            summary = page.summary[:max_length]

            return {
                "title": page.title,
                "url": page.fullurl,
                "summary": summary,
            }

        except Exception as e:
            logger.error(f"Wikipedia API error: {e}")
            return None

    def collect_from_api(self, input_csv: Path) -> List[EpisodeSource]:
        """
        API経由で情報源を収集（Phase 2実装）

        Args:
            input_csv: 入力CSV（person_name, birth_year, person_type）

        Returns:
            EpisodeSourceのリスト
        """
        logger.info(f"Collecting sources from API: {input_csv}")

        if not input_csv.exists():
            raise FileNotFoundError(f"Input CSV not found: {input_csv}")

        df = pd.read_csv(input_csv, encoding="utf-8-sig")

        sources = []
        for idx, row in df.iterrows():
            person_name = row["person_name"]
            birth_year = row.get("birth_year")
            person_type = row.get("person_type", "REAL")

            logger.info(f"Processing {idx + 1}/{len(df)}: {person_name}")

            # センシティブフィルター適用
            candidate = PersonCandidate(
                person_name=person_name,
                person_type=person_type,
                birth_year=birth_year,
            )

            is_sensitive, reason = self.sensitive_filter.is_sensitive(candidate)
            if is_sensitive:
                self.skipped_sources.append(
                    {
                        "person_name": person_name,
                        "source_url": "",
                        "skip_reason": reason,
                    }
                )
                logger.warning(f"Skipped sensitive person: {person_name} - {reason}")
                continue

            # Wikidata取得
            if "wikidata" in self.sources:
                wikidata_results = self.fetch_from_wikidata(person_name, birth_year)
                # TODO: Wikidata結果をEpisodeSourceに変換

            # Wikipedia取得
            if "wikipedia" in self.sources:
                wikipedia_data = self.fetch_from_wikipedia(person_name)
                if wikipedia_data:
                    source = EpisodeSource(
                        person_name=person_name,
                        person_id="",  # 後で採番
                        person_type=person_type,
                        source_url=wikipedia_data["url"],
                        source_type="wikipedia",
                        raw_text=wikipedia_data["summary"],
                        context=f"{person_name}のWikipedia情報",
                    )
                    sources.append(source)

        logger.info(f"Collected {len(sources)} sources from API, skipped {len(self.skipped_sources)}")
        self.collected_sources.extend(sources)
        return sources

    def generate_search_queries(self, input_csv: Path, output_csv: Path):
        """
        検索クエリ一覧を生成（API無し環境用）

        Args:
            input_csv: 入力CSV（person_name, birth_year, person_type）
            output_csv: 出力CSVパス
        """
        logger.info(f"Generating search queries: {output_csv}")

        df = pd.read_csv(input_csv, encoding="utf-8-sig")

        queries = []
        for _, row in df.iterrows():
            person_name = row["person_name"]

            # クエリパターン
            query_patterns = [
                f'"{person_name}" 逸話 エピソード',
                f'"{person_name}" 自伝 回想',
                f'"{person_name}" インタビュー',
                f'"{person_name}" 業績',
            ]

            for pattern in query_patterns:
                queries.append({"person_name": person_name, "search_query": pattern})

        query_df = pd.DataFrame(queries)
        query_df.to_csv(output_csv, index=False, encoding="utf-8-sig")

        logger.info(f"Generated {len(queries)} search queries")

    def check_duplicates(self, existing_sources_csv: Optional[Path] = None) -> List[EpisodeSource]:
        """
        重複チェック（冪等性保証）

        Args:
            existing_sources_csv: 既存ソースCSVパス

        Returns:
            重複除外後のソースリスト
        """
        if not existing_sources_csv or not existing_sources_csv.exists():
            logger.info("No existing sources, skipping duplicate check")
            return self.collected_sources

        logger.info(f"Checking duplicates against: {existing_sources_csv}")

        existing_df = pd.read_csv(existing_sources_csv, encoding="utf-8-sig")
        existing_ids = set(existing_df["source_id"].values)

        unique_sources = []
        duplicate_count = 0

        for source in self.collected_sources:
            if source.source_id in existing_ids:
                logger.debug(f"Duplicate source_id: {source.source_id}")
                duplicate_count += 1
                self.skipped_sources.append(
                    {
                        "person_name": source.person_name,
                        "source_url": source.source_url,
                        "skip_reason": "duplicate_source_id",
                    }
                )
            else:
                unique_sources.append(source)

        logger.info(f"Removed {duplicate_count} duplicate sources")
        return unique_sources

    def save_to_csv(self, sources: List[EpisodeSource], output_csv: Path):
        """
        CSV保存

        Args:
            sources: EpisodeSourceのリスト
            output_csv: 出力CSVパス
        """
        logger.info(f"Saving {len(sources)} sources to: {output_csv}")

        # DataFrameに変換
        data = [source.to_dict() for source in sources]
        df = pd.DataFrame(data)

        # CSV保存（BOM付きUTF-8）
        df.to_csv(output_csv, index=False, encoding="utf-8-sig")

        logger.info(f"Saved {len(sources)} sources")

    def save_skipped_to_csv(self, output_csv: Path):
        """
        スキップしたソースをCSV保存

        Args:
            output_csv: 出力CSVパス
        """
        if not self.skipped_sources:
            logger.info("No skipped sources")
            return

        logger.info(f"Saving {len(self.skipped_sources)} skipped sources to: {output_csv}")

        df = pd.DataFrame(self.skipped_sources)
        df.to_csv(output_csv, index=False, encoding="utf-8-sig")

    def get_statistics(self) -> Dict:
        """統計情報を取得"""
        return {
            "collected_count": len(self.collected_sources),
            "skipped_count": len(self.skipped_sources),
            "mode": self.mode,
            "sources": self.sources,
        }


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(
        description="Stage 1: collect-sources - エピソード情報源収集",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # 入出力
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="入力CSV（person_name, birth_year, person_type または manual_sources形式）",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="generated/episode_sources.csv",
        help="出力CSVパス（デフォルト: generated/episode_sources.csv）",
    )

    # モード
    parser.add_argument(
        "--mode",
        type=str,
        choices=["manual", "api", "hybrid"],
        default="manual",
        help="収集モード（manual: 手動CSV, api: API経由, hybrid: 両方）",
    )

    # API設定
    parser.add_argument("--sources", type=str, help="使用するAPIソース（カンマ区切り: wikidata,wikipedia）")

    # 実行モード
    parser.add_argument("--dry-run", action="store_true", default=True, help="ドライラン（デフォルト: True）")
    parser.add_argument("--execute", action="store_true", help="実際に実行（ファイル書き込み）")

    # オプション
    parser.add_argument("--check-duplicates", type=str, help="重複チェック対象の既存CSVパス")
    parser.add_argument("--generate-queries", action="store_true", help="検索クエリ一覧を生成")
    parser.add_argument("--verbose", action="store_true", help="詳細ログ出力")

    args = parser.parse_args()

    # ロガー設定
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # 実行モード確認
    if args.execute:
        dry_run = False
    else:
        dry_run = True

    logger.info("=" * 60)
    logger.info("Stage 1: collect-sources")
    logger.info("=" * 60)
    logger.info(f"Mode: {args.mode}")
    logger.info(f"Input: {args.input}")
    logger.info(f"Output: {args.output}")
    logger.info(f"Dry-run: {dry_run}")
    logger.info("=" * 60)

    # パス解決
    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.is_absolute():
        input_path = project_root / input_path

    if not output_path.is_absolute():
        output_path = project_root / output_path

    # SourceCollector初期化
    sources_list = args.sources.split(",") if args.sources else []
    collector = SourceCollector(mode=args.mode, sources=sources_list)

    try:
        # 情報源収集
        if args.mode == "manual":
            sources = collector.collect_from_csv(input_path)
        elif args.mode == "api":
            sources = collector.collect_from_api(input_path)
        elif args.mode == "hybrid":
            sources = collector.collect_from_csv(input_path)
            sources.extend(collector.collect_from_api(input_path))
        else:
            raise ValueError(f"Invalid mode: {args.mode}")

        # 重複チェック
        if args.check_duplicates:
            existing_path = Path(args.check_duplicates)
            if not existing_path.is_absolute():
                existing_path = project_root / existing_path
            sources = collector.check_duplicates(existing_path)

        # 検索クエリ生成
        if args.generate_queries:
            query_output = output_path.parent / "search_queries.csv"
            collector.generate_search_queries(input_path, query_output)

        # 統計表示
        stats = collector.get_statistics()
        logger.info("=" * 60)
        logger.info("Statistics:")
        logger.info(f"  Collected: {stats['collected_count']}")
        logger.info(f"  Skipped: {stats['skipped_count']}")
        logger.info("=" * 60)

        # ファイル保存
        if not dry_run:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            collector.save_to_csv(sources, output_path)

            # スキップしたソースを保存
            skipped_output = output_path.parent / "skipped_sources.csv"
            collector.save_skipped_to_csv(skipped_output)

            logger.info("✅ Stage 1: collect-sources completed successfully")
        else:
            logger.info("⚠️  Dry-run mode: No files written")
            logger.info(f"Would save {len(sources)} sources to: {output_path}")

    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
