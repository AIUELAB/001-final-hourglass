#!/usr/bin/env python3
"""
有名度スコア v2 - Wikipedia Pageviews 中心の連続スコア算出

同点問題を解消するため、対数スケールのPVスコアを使用。
SQLiteキャッシュにより、再実行時のAPI呼び出しを削減。

Usage:
    # テスト（100件、ドライラン）
    python scripts/fame_score_v2.py --dry-run --limit 100

    # 実行（全件）
    python scripts/fame_score_v2.py --execute

    # キャッシュ確認
    python scripts/fame_score_v2.py --cache-stats
"""

import argparse
import csv
import math
import sqlite3
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote

import requests

# プロジェクトルート
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.wikidata_fetcher import WikidataFetcher


class WikipediaPageviewsCache:
    """SQLiteベースのWikipedia Pageviewsキャッシュ"""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or project_root / "cache" / "wikipedia_pageviews.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """データベース初期化"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pageviews (
                    person_name TEXT PRIMARY KEY,
                    page_title TEXT,
                    monthly_views INTEGER,
                    lang_count INTEGER DEFAULT 0,
                    fetched_at TEXT,
                    ttl_days INTEGER DEFAULT 30
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_fetched_at
                ON pageviews(fetched_at)
            """)

    def get(self, person_name: str) -> Optional[Dict]:
        """キャッシュからデータ取得（TTL期限切れはNone）"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM pageviews WHERE person_name = ?",
                (person_name,),
            ).fetchone()

            if not row:
                return None

            # TTLチェック
            fetched_at = datetime.fromisoformat(row["fetched_at"])
            ttl_days = row["ttl_days"]
            if datetime.now() - fetched_at > timedelta(days=ttl_days):
                return None  # 期限切れ

            return dict(row)

    def set(
        self,
        person_name: str,
        page_title: str,
        monthly_views: int,
        lang_count: int = 0,
        ttl_days: int = 30,
    ):
        """キャッシュにデータ保存"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO pageviews
                (person_name, page_title, monthly_views, lang_count, fetched_at, ttl_days)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    person_name,
                    page_title,
                    monthly_views,
                    lang_count,
                    datetime.now().isoformat(),
                    ttl_days,
                ),
            )

    def get_stats(self) -> Dict:
        """キャッシュ統計"""
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM pageviews").fetchone()[0]
            valid = conn.execute(
                """
                SELECT COUNT(*) FROM pageviews
                WHERE datetime(fetched_at, '+' || ttl_days || ' days') > datetime('now')
            """
            ).fetchone()[0]
            expired = total - valid

            return {"total": total, "valid": valid, "expired": expired}


class WikipediaPageviewsFetcher:
    """Wikipedia Pageviews API クライアント（Wikidata統合版）"""

    def __init__(self, cache: WikipediaPageviewsCache, delay: float = 1.0):
        self.cache = cache
        self.delay = delay
        self.headers = {"User-Agent": "FinalHourglassBot/2.0 (https://github.com/AIUELAB/001-final-hourglass)"}
        self.stats = {
            "api_calls": 0,
            "cache_hits": 0,
            "wikidata_hits": 0,
            "fallback_hits": 0,
            "errors": 0,
        }
        # Wikidata統合
        self.wikidata = WikidataFetcher(delay=delay / 2)

    def get_monthly_pageviews(self, person_name: str) -> Tuple[int, str]:
        """
        月間ページビュー数を取得（Wikidata統合版）

        解決順序:
        1. キャッシュ確認
        2. Wikidata経由でページタイトル解決
        3. フォールバック: Wikipedia Search API
        4. Pageviews API でPV取得

        Returns:
            Tuple[int, str]: (月間PV数, ページタイトル)
        """
        # キャッシュチェック
        cached = self.cache.get(person_name)
        if cached:
            self.stats["cache_hits"] += 1
            return cached["monthly_views"], cached["page_title"]

        try:
            # Step 1: Wikidata経由でページタイトル解決
            page_title = self.wikidata.resolve_person(person_name)

            if page_title:
                self.stats["wikidata_hits"] += 1
            else:
                # Step 2: フォールバック - Wikipedia Search API
                page_title = self._search_wikipedia(person_name)
                if page_title:
                    self.stats["fallback_hits"] += 1

            if not page_title:
                self.cache.set(person_name, "", 0, ttl_days=7)  # 短いTTL
                return 0, ""

            # Step 3: Pageviews取得
            monthly_views = self._fetch_pageviews(page_title)

            # キャッシュ保存
            ttl_days = 90 if self._is_historical(person_name) else 30
            self.cache.set(person_name, page_title, monthly_views, ttl_days=ttl_days)

            self.stats["api_calls"] += 1
            return monthly_views, page_title

        except Exception as e:
            self.stats["errors"] += 1
            print(f"  ⚠️ API Error [{person_name}]: {e}")
            return 0, ""

    def _search_wikipedia(self, person_name: str) -> Optional[str]:
        """Wikipedia日本語版でページを検索"""
        search_url = "https://ja.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "list": "search",
            "srsearch": person_name,
            "format": "json",
            "utf8": 1,
        }

        response = requests.get(search_url, params=params, headers=self.headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        results = data.get("query", {}).get("search", [])
        if not results:
            return None

        # 最初の検索結果を使用
        return results[0]["title"]

    def _fetch_pageviews(self, page_title: str) -> int:
        """過去30日間のページビュー数を取得"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        # URLエンコード（スペース→アンダースコア）
        encoded_title = quote(page_title.replace(" ", "_"), safe="")

        url = (
            f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
            f"ja.wikipedia/all-access/all-agents/{encoded_title}/daily/"
            f"{start_date.strftime('%Y%m%d')}/{end_date.strftime('%Y%m%d')}"
        )

        # レート制限対策
        time.sleep(self.delay)

        response = requests.get(url, headers=self.headers, timeout=10)

        if response.status_code == 404:
            return 0  # ページビューデータなし

        response.raise_for_status()
        data = response.json()

        total_views = sum(item["views"] for item in data.get("items", []))
        return total_views

    def _is_historical(self, person_name: str) -> bool:
        """歴史上の人物かどうかを推定（長めのTTL用）"""
        # 簡易判定: 〜時代、〜世紀、〜年生などのキーワード
        historical_keywords = ["時代", "世紀", "将軍", "天皇", "武将", "BC", "紀元前"]
        return any(kw in person_name for kw in historical_keywords)


def calculate_fame_score_v2(monthly_pv: int, row: Dict) -> float:
    """
    有名度スコア v2 を計算

    Args:
        monthly_pv: 月間ページビュー数
        row: エピソードデータ

    Returns:
        float: 有名度スコア (0.00-100.00)
    """
    # PVスコア（対数スケール、キャップなし）
    # log10(1) = 0, log10(1000) = 30, log10(100000) = 50, log10(1000000) = 60
    # 高PVの差を保持するためキャップを撤廃（2024-12-20修正）
    if monthly_pv > 0:
        pv_score = math.log10(max(1, monthly_pv)) * 10
    else:
        pv_score = 0.0

    # Wikipedia存在ボーナス（15点）
    wiki_exists_bonus = 15.0 if monthly_pv > 0 else 0.0

    # 受賞歴ボーナス（0-9点）
    try:
        award_level = int(row.get("award_level", 0) or 0)
    except (ValueError, TypeError):
        award_level = 0  # 非数値の場合は0
    award_bonus = min(9.0, award_level * 3)

    # 教科書掲載ボーナス（10点）
    textbook_bonus = 10.0 if str(row.get("textbook", "")).upper() == "TRUE" else 0.0

    # 悪名ペナルティ（-20点）
    notoriety_penalty = -20.0 if str(row.get("notoriety", "")).upper() == "TRUE" else 0.0

    # 合計（0-100点）
    raw_score = pv_score + wiki_exists_bonus + award_bonus + textbook_bonus + notoriety_penalty
    fame_score = max(0.0, min(100.0, raw_score))

    return round(fame_score, 2)


def get_unique_persons(csv_path: Path) -> List[Dict]:
    """CSVからユニークな人物リストを取得"""
    persons = {}

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            person_id = row.get("person_id", "")
            person_name = row.get("person_name", "")

            if person_id and person_id not in persons:
                persons[person_id] = {
                    "person_id": person_id,
                    "person_name": person_name,
                    "award_level": row.get("award_level", 0),
                    "textbook": row.get("textbook", ""),
                    "notoriety": row.get("notoriety", ""),
                }

    return list(persons.values())


def update_csv_with_scores(
    csv_path: Path,
    person_scores: Dict[str, Dict],
    dry_run: bool = False,
) -> int:
    """CSVにスコアを反映"""
    if dry_run:
        print("\n🔍 ドライラン: CSVは更新しません")
        return 0

    # 一時ファイルに書き込み
    temp_path = csv_path.with_suffix(".tmp")
    updated_count = 0
    current_time = datetime.now().isoformat()

    with open(csv_path, "r", encoding="utf-8-sig") as infile:
        reader = csv.DictReader(infile)
        fieldnames = list(reader.fieldnames)

        # 新カラム追加（存在しない場合）
        new_cols = ["fame_score_v2", "wikipedia_pv", "fame_score_updated_at"]
        for col in new_cols:
            if col not in fieldnames:
                fieldnames.append(col)

        with open(temp_path, "w", encoding="utf-8-sig", newline="") as outfile:
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()

            for row in reader:
                person_id = row.get("person_id", "")
                if person_id in person_scores:
                    score_data = person_scores[person_id]
                    row["fame_score_v2"] = str(score_data["fame_score"])
                    row["wikipedia_pv"] = str(score_data["monthly_pv"])
                    row["fame_score_updated_at"] = current_time
                    updated_count += 1

                writer.writerow(row)

    # 置き換え
    temp_path.replace(csv_path)
    return updated_count


def main():
    parser = argparse.ArgumentParser(description="有名度スコア v2 算出スクリプト")
    parser.add_argument("--dry-run", action="store_true", help="ドライラン（CSV更新しない）")
    parser.add_argument("--execute", action="store_true", help="実行（CSV更新する）")
    parser.add_argument("--limit", type=int, help="処理件数制限")
    parser.add_argument("--delay", type=float, default=1.0, help="API呼び出し間隔（秒）")
    parser.add_argument("--cache-stats", action="store_true", help="キャッシュ統計表示")
    parser.add_argument(
        "--csv-path",
        type=Path,
        default=project_root / "preserved/data/MASTER_EPISODES_CURRENT.csv",
        help="CSVファイルパス",
    )

    args = parser.parse_args()

    # キャッシュ初期化
    cache = WikipediaPageviewsCache()

    if args.cache_stats:
        stats = cache.get_stats()
        print("📊 キャッシュ統計:")
        print(f"  総件数: {stats['total']}")
        print(f"  有効: {stats['valid']}")
        print(f"  期限切れ: {stats['expired']}")
        return

    if not args.dry_run and not args.execute:
        print("⚠️ --dry-run または --execute を指定してください")
        return

    print("=" * 70)
    print("有名度スコア v2 - Wikipedia Pageviews 中心の連続スコア算出")
    print("=" * 70)

    # ユニークな人物を取得
    persons = get_unique_persons(args.csv_path)
    total = len(persons)
    print(f"\n📊 ユニーク人物数: {total}人")

    if args.limit:
        persons = persons[: args.limit]
        print(f"📊 処理対象: {len(persons)}人（--limit {args.limit}）")

    # フェッチャー初期化
    fetcher = WikipediaPageviewsFetcher(cache, delay=args.delay)

    # スコア計算
    person_scores = {}
    start_time = time.time()

    print("\n🚀 スコア算出開始...")

    for i, person in enumerate(persons):
        person_id = person["person_id"]
        person_name = person["person_name"]

        print(f"\r[{i + 1}/{len(persons)}] {person_name[:20]:<20}", end="", flush=True)

        monthly_pv, page_title = fetcher.get_monthly_pageviews(person_name)
        fame_score = calculate_fame_score_v2(monthly_pv, person)

        person_scores[person_id] = {
            "person_name": person_name,
            "fame_score": fame_score,
            "monthly_pv": monthly_pv,
            "page_title": page_title,
        }

    elapsed = time.time() - start_time

    # 結果表示
    print(f"\n\n✅ スコア算出完了（{elapsed:.1f}秒）")
    print("\n📊 API統計:")
    print(f"  API呼び出し: {fetcher.stats['api_calls']}")
    print(f"  キャッシュヒット: {fetcher.stats['cache_hits']}")
    print(f"  エラー: {fetcher.stats['errors']}")

    # スコア分布
    scores = [s["fame_score"] for s in person_scores.values()]
    if scores:
        print("\n📊 スコア分布:")
        print(f"  最高: {max(scores):.2f}")
        print(f"  最低: {min(scores):.2f}")
        print(f"  平均: {sum(scores) / len(scores):.2f}")
        print(f"  ユニーク値数: {len(set(scores))}")

    # Top 10表示
    top10 = sorted(person_scores.values(), key=lambda x: x["fame_score"], reverse=True)[:10]
    print("\n🏆 Top 10:")
    for i, p in enumerate(top10, 1):
        print(f"  {i:2}. {p['person_name'][:15]:<15} {p['fame_score']:6.2f}点 (PV: {p['monthly_pv']:,})")

    # CSV更新
    if args.execute:
        updated = update_csv_with_scores(args.csv_path, person_scores, dry_run=False)
        print(f"\n✅ CSV更新: {updated}件")
    else:
        print("\n🔍 ドライラン完了（CSV更新なし）")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
