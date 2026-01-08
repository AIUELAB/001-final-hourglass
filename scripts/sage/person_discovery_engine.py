"""
Person Discovery Engine

LLM・Web検索・Wikidataから新規有名人を自動発見するエンジン。
"""

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

import requests

from .person_discoverer import AddPersonResult, PersonDiscoverer

logger = logging.getLogger(__name__)

# プロジェクトルート
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Perplexity APIキー
PERPLEXITY_API_KEY_PATH = Path("/Users/admin/Documents/key/Perplexity_API.txt")


class DiscoveryStrategy(Enum):
    """発見戦略"""

    WIKIDATA = "wikidata"  # Wikidata SPARQL
    LLM = "llm"  # LLM提案
    WEB_SEARCH = "web_search"  # Perplexity API
    COMBINED = "combined"  # 全戦略


@dataclass
class DiscoveryCandidate:
    """発見候補"""

    name: str
    category: str
    source: str  # wikidata / llm / web_search
    sitelinks: int = 0
    wikidata_id: Optional[str] = None
    reason: str = ""  # 発見理由


@dataclass
class DiscoveryConfig:
    """発見設定"""

    strategy: DiscoveryStrategy = DiscoveryStrategy.COMBINED
    min_sitelinks: int = 30
    max_candidates: int = 20
    categories: list[str] = field(default_factory=list)
    dry_run: bool = True


@dataclass
class DiscoveryReport:
    """発見レポート"""

    timestamp: str
    strategy: str
    discovered_count: int
    added_count: int
    skipped_count: int
    candidates: list[dict] = field(default_factory=list)
    results: list[dict] = field(default_factory=list)


class PersonDiscoveryEngine:
    """自動有名人発見エンジン"""

    # Wikidata SPARQL エンドポイント
    SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
    USER_AGENT = "PersonDiscoveryEngine/1.0 (FinalHourglass)"

    # Perplexity API
    PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
    PERPLEXITY_MODEL = "sonar"

    # カテゴリマッピング（Wikidata職業 → 内部カテゴリ）
    CATEGORY_MAPPING = {
        "政治家": "政治",
        "政治": "政治",
        "実業家": "ビジネス",
        "企業家": "ビジネス",
        "経営者": "ビジネス",
        "ビジネス": "ビジネス",
        "科学者": "科学",
        "研究者": "科学",
        "物理学者": "科学",
        "化学者": "科学",
        "科学": "科学",
        "俳優": "芸術",
        "女優": "芸術",
        "歌手": "芸術",
        "音楽家": "芸術",
        "作曲家": "芸術",
        "作家": "芸術",
        "小説家": "芸術",
        "画家": "芸術",
        "監督": "芸術",
        "芸術": "芸術",
        "サッカー選手": "スポーツ",
        "野球選手": "スポーツ",
        "プロ野球選手": "スポーツ",
        "将棋棋士": "スポーツ",
        "テニス選手": "スポーツ",
        "柔道家": "スポーツ",
        "水泳選手": "スポーツ",
        "スポーツ": "スポーツ",
        "お笑い芸人": "エンターテインメント",
        "タレント": "エンターテインメント",
        "アイドル": "エンターテインメント",
        "声優": "エンターテインメント",
        "アナウンサー": "エンターテインメント",
        "エンターテインメント": "エンターテインメント",
    }

    def __init__(self, config: Optional[DiscoveryConfig] = None):
        self.config = config or DiscoveryConfig()
        self.discoverer = PersonDiscoverer()
        self._perplexity_api_key: Optional[str] = None
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": self.USER_AGENT,
                "Accept": "application/json",
            }
        )

    def _get_perplexity_api_key(self) -> Optional[str]:
        """Perplexity APIキーを取得"""
        if self._perplexity_api_key:
            return self._perplexity_api_key

        # 環境変数から取得
        key = os.environ.get("PERPLEXITY_API_KEY")
        if key:
            self._perplexity_api_key = key
            return key

        # ファイルから取得
        if PERPLEXITY_API_KEY_PATH.exists():
            self._perplexity_api_key = PERPLEXITY_API_KEY_PATH.read_text().strip()
            return self._perplexity_api_key

        return None

    def discover(self) -> list[DiscoveryCandidate]:
        """発見戦略に基づいて候補を取得"""
        candidates: list[DiscoveryCandidate] = []

        strategy = self.config.strategy

        if strategy in [DiscoveryStrategy.WIKIDATA, DiscoveryStrategy.COMBINED]:
            logger.info("Wikidata SPARQL戦略を実行中...")
            wikidata_candidates = self._discover_from_wikidata()
            candidates.extend(wikidata_candidates)
            logger.info(f"  Wikidata: {len(wikidata_candidates)}件発見")

        if strategy in [DiscoveryStrategy.LLM, DiscoveryStrategy.COMBINED]:
            logger.info("LLM戦略を実行中...")
            llm_candidates = self._discover_from_llm()
            candidates.extend(llm_candidates)
            logger.info(f"  LLM: {len(llm_candidates)}件発見")

        if strategy in [DiscoveryStrategy.WEB_SEARCH, DiscoveryStrategy.COMBINED]:
            logger.info("Web検索戦略を実行中...")
            web_candidates = self._discover_from_web()
            candidates.extend(web_candidates)
            logger.info(f"  Web: {len(web_candidates)}件発見")

        # フィルタリング・検証
        validated = self._filter_and_validate(candidates)
        logger.info(f"フィルタリング後: {len(validated)}件")

        return validated[: self.config.max_candidates]

    def _discover_from_wikidata(self) -> list[DiscoveryCandidate]:
        """Wikidata SPARQLから高sitelinks人物を発見"""
        candidates = []

        # 日本国籍の人物でsitelinkが多いものを取得
        query = f"""
        SELECT ?person ?personLabel ?sitelinks ?occupationLabel WHERE {{
          ?person wdt:P31 wd:Q5.
          ?person wdt:P27 wd:Q17.
          ?person wikibase:sitelinks ?sitelinks.
          OPTIONAL {{ ?person wdt:P106 ?occupation. }}
          FILTER(?sitelinks >= {self.config.min_sitelinks})
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "ja,en". }}
        }}
        ORDER BY DESC(?sitelinks)
        LIMIT 200
        """

        try:
            response = self._session.get(
                self.SPARQL_ENDPOINT,
                params={"query": query, "format": "json"},
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()

            bindings = data.get("results", {}).get("bindings", [])
            for binding in bindings:
                name = binding.get("personLabel", {}).get("value", "")
                if not name or name.startswith("Q"):  # ラベルがない場合スキップ
                    continue

                wikidata_id = binding.get("person", {}).get("value", "").split("/")[-1]
                sitelinks = int(binding.get("sitelinks", {}).get("value", 0))
                occupation = binding.get("occupationLabel", {}).get("value", "")

                # カテゴリ推定
                category = self.CATEGORY_MAPPING.get(occupation, "その他")

                candidates.append(
                    DiscoveryCandidate(
                        name=name,
                        category=category,
                        source="wikidata",
                        sitelinks=sitelinks,
                        wikidata_id=wikidata_id,
                        reason=f"sitelinks={sitelinks}, occupation={occupation}",
                    )
                )

            # レート制限
            time.sleep(0.5)

        except requests.RequestException as e:
            logger.error(f"Wikidata SPARQL error: {e}")

        return candidates

    def _discover_from_llm(self) -> list[DiscoveryCandidate]:
        """LLMに候補を提案させる"""
        candidates = []

        try:
            import anthropic

            client = anthropic.Anthropic()

            # 既存人物リストのサンプルを取得（重複防止用）
            existing_sample = list(self.discoverer.get_existing_names())[:50]
            existing_str = ", ".join(existing_sample[:20])

            prompt = f"""日本で有名な人物を10名提案してください。

以下の条件を満たす人物のみ:
1. Wikipediaに日本語記事がある
2. 以下のカテゴリのいずれか: 政治/ビジネス/科学/芸術/スポーツ/エンターテインメント
3. 一般的に知られている（テレビやニュースで見る）

以下の人物は既に登録済みなので除外してください:
{existing_str}...

JSON形式で出力してください:
[
  {{"name": "人物名", "category": "カテゴリ", "reason": "有名な理由"}},
  ...
]

注意: 実在する人物のみ提案してください。架空の人物は含めないでください。"""

            response = client.messages.create(
                model="claude-3-5-haiku-20241022",  # コスト効率重視
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )

            # JSON抽出
            content_block = response.content[0]
            text = content_block.text if hasattr(content_block, "text") else str(content_block)
            json_match = re.search(r"\[[\s\S]*\]", text)
            if json_match:
                suggestions = json.loads(json_match.group())
                for s in suggestions:
                    candidates.append(
                        DiscoveryCandidate(
                            name=s.get("name", ""),
                            category=self.CATEGORY_MAPPING.get(s.get("category", ""), "その他"),
                            source="llm",
                            reason=s.get("reason", "LLM提案"),
                        )
                    )

        except ImportError:
            logger.warning("anthropic module not installed, skipping LLM discovery")
        except Exception as e:
            logger.error(f"LLM discovery error: {e}")

        return candidates

    def _discover_from_web(self) -> list[DiscoveryCandidate]:
        """Perplexity APIでトレンド人物を発見"""
        candidates = []

        api_key = self._get_perplexity_api_key()
        if not api_key:
            logger.warning("Perplexity API key not found, skipping web discovery")
            return candidates

        queries = [
            "2025年に注目を集めた日本の有名人 新人 一覧",
            "最近話題の日本人 著名人 Wikipedia",
        ]

        for query in queries:
            try:
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }

                payload = {
                    "model": self.PERPLEXITY_MODEL,
                    "messages": [
                        {
                            "role": "system",
                            "content": """あなたは日本の有名人リサーチャーです。
検索結果から人物名を抽出し、JSON形式で出力してください。

出力形式:
[
  {"name": "人物名", "category": "カテゴリ", "reason": "有名な理由"},
  ...
]

カテゴリ: 政治/ビジネス/科学/芸術/スポーツ/エンターテインメント/その他
注意: 実在する人物のみ。グループ名やユニット名は除外。""",
                        },
                        {"role": "user", "content": query},
                    ],
                    "max_tokens": 1024,
                }

                response = requests.post(
                    self.PERPLEXITY_API_URL,
                    headers=headers,
                    json=payload,
                    timeout=30,
                )
                response.raise_for_status()
                data = response.json()

                text = data.get("choices", [{}])[0].get("message", {}).get("content", "")

                # JSON抽出
                json_match = re.search(r"\[[\s\S]*\]", text)
                if json_match:
                    suggestions = json.loads(json_match.group())
                    for s in suggestions:
                        candidates.append(
                            DiscoveryCandidate(
                                name=s.get("name", ""),
                                category=self.CATEGORY_MAPPING.get(s.get("category", ""), "その他"),
                                source="web_search",
                                reason=s.get("reason", "Web検索"),
                            )
                        )

                # レート制限
                time.sleep(1.0)

            except requests.RequestException as e:
                logger.error(f"Perplexity API error: {e}")
            except json.JSONDecodeError as e:
                logger.error(f"JSON parse error: {e}")

        return candidates

    def _filter_and_validate(self, candidates: list[DiscoveryCandidate]) -> list[DiscoveryCandidate]:
        """重複排除・Wikidata存在確認・閾値チェック"""
        validated = []
        seen_names: set[str] = set()

        for c in candidates:
            # 空の名前をスキップ
            if not c.name or len(c.name) < 2:
                continue

            # 重複排除（候補内）
            if c.name in seen_names:
                continue
            seen_names.add(c.name)

            # 既存DBチェック
            is_dup, _ = self.discoverer.check_duplicate(c.name)
            if is_dup:
                logger.debug(f"  スキップ（既存）: {c.name}")
                continue

            # LLM/Web候補はWikidata検証必須
            if c.source in ["llm", "web_search"]:
                wikidata = self.discoverer.search_person(c.name)
                if not wikidata:
                    logger.debug(f"  スキップ（Wikidata不在）: {c.name}")
                    continue

                # Wikidata情報で補完
                c.wikidata_id = wikidata.get("wikidata_id")
                c.sitelinks = wikidata.get("sitelinks", 0)

                # レート制限
                time.sleep(0.3)

            # sitelinks閾値チェック
            if c.sitelinks < self.config.min_sitelinks:
                logger.debug(f"  スキップ（sitelinks不足）: {c.name} ({c.sitelinks})")
                continue

            # カテゴリフィルタ
            if self.config.categories and c.category not in self.config.categories:
                continue

            validated.append(c)
            logger.info(f"  ✓ 候補: {c.name} ({c.category}, sitelinks={c.sitelinks})")

        return validated

    def add_discovered(self, candidates: list[DiscoveryCandidate], dry_run: bool = True) -> list[AddPersonResult]:
        """発見した候補をCSVに追加"""
        results = []

        for c in candidates:
            result = self.discoverer.add_person(
                name=c.name,
                category=c.category,
                dry_run=dry_run,
            )
            results.append(result)

            if result.success:
                logger.info(f"{'[DRY-RUN] ' if dry_run else ''}追加: {c.name}")
            else:
                logger.warning(f"追加失敗: {c.name} - {result.message}")

        return results

    def run(self, dry_run: Optional[bool] = None) -> DiscoveryReport:
        """発見→追加の完全実行"""
        if dry_run is None:
            dry_run = self.config.dry_run

        # 発見
        candidates = self.discover()

        # 追加
        results = self.add_discovered(candidates, dry_run=dry_run)

        # レポート作成
        report = DiscoveryReport(
            timestamp=datetime.now().isoformat(),
            strategy=self.config.strategy.value,
            discovered_count=len(candidates),
            added_count=sum(1 for r in results if r.success),
            skipped_count=sum(1 for r in results if not r.success),
            candidates=[
                {
                    "name": c.name,
                    "category": c.category,
                    "source": c.source,
                    "sitelinks": c.sitelinks,
                    "reason": c.reason,
                }
                for c in candidates
            ],
            results=[
                {
                    "name": r.person_name,
                    "person_id": r.person_id,
                    "success": r.success,
                    "message": r.message,
                }
                for r in results
            ],
        )

        return report

    def save_report(self, report: DiscoveryReport, path: Optional[Path] = None) -> Path:
        """レポートをJSONで保存"""
        if path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = PROJECT_ROOT / "src" / "reports" / f"discovery_report_{timestamp}.json"

        path.parent.mkdir(parents=True, exist_ok=True)

        report_dict = {
            "timestamp": report.timestamp,
            "strategy": report.strategy,
            "discovered_count": report.discovered_count,
            "added_count": report.added_count,
            "skipped_count": report.skipped_count,
            "candidates": report.candidates,
            "results": report.results,
        }

        path.write_text(json.dumps(report_dict, ensure_ascii=False, indent=2))
        logger.info(f"レポート保存: {path}")

        return path


# CLI用ユーティリティ関数
def discover_and_add_persons(
    strategy: str = "combined",
    min_sitelinks: int = 30,
    max_candidates: int = 20,
    categories: Optional[list[str]] = None,
    dry_run: bool = True,
) -> DiscoveryReport:
    """
    新規有名人を発見・追加するユーティリティ関数

    Args:
        strategy: 発見戦略 (wikidata/llm/web_search/combined)
        min_sitelinks: 最小sitelinks数
        max_candidates: 最大候補数
        categories: カテゴリフィルタ
        dry_run: dry-runモード

    Returns:
        DiscoveryReport
    """
    config = DiscoveryConfig(
        strategy=DiscoveryStrategy(strategy),
        min_sitelinks=min_sitelinks,
        max_candidates=max_candidates,
        categories=categories or [],
        dry_run=dry_run,
    )

    engine = PersonDiscoveryEngine(config)
    report = engine.run(dry_run=dry_run)

    # レポート保存
    engine.save_report(report)

    return report


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    strategy = sys.argv[1] if len(sys.argv) > 1 else "combined"
    dry_run = "--execute" not in sys.argv

    report = discover_and_add_persons(
        strategy=strategy,
        dry_run=dry_run,
    )

    print(f"\n発見: {report.discovered_count}件")
    print(f"追加: {report.added_count}件")
    print(f"スキップ: {report.skipped_count}件")
