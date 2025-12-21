#!/usr/bin/env python3
"""
有名度スコア v2 - 並列処理版

4並列でWikidata/Wikipedia APIを呼び出し、処理時間を約1/4に短縮。
レート制限対策として各ワーカーに異なるdelayを設定。

Usage:
    python scripts/fame_score_v2_parallel.py --execute --workers 4
"""

import argparse
import csv
import math
import sqlite3
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
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
    """SQLiteベースのWikipedia Pageviewsキャッシュ（スレッドセーフ版）"""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or project_root / "cache" / "wikipedia_pageviews.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
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

    def get(self, person_name: str) -> Optional[Dict]:
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "SELECT * FROM pageviews WHERE person_name = ?",
                    (person_name,),
                ).fetchone()

                if not row:
                    return None

                fetched_at = datetime.fromisoformat(row["fetched_at"])
                ttl_days = row["ttl_days"]
                if datetime.now() - fetched_at > timedelta(days=ttl_days):
                    return None

                return dict(row)

    def set(
        self,
        person_name: str,
        page_title: str,
        monthly_views: int,
        lang_count: int = 0,
        ttl_days: int = 30,
    ):
        with self._lock:
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


class WikipediaPageviewsFetcher:
    """Wikipedia Pageviews API クライアント（Wikidata統合版）"""

    def __init__(self, cache: WikipediaPageviewsCache, delay: float = 1.0, worker_id: int = 0):
        self.cache = cache
        self.delay = delay
        self.worker_id = worker_id
        self.headers = {"User-Agent": f"FinalHourglassBot/2.0-worker{worker_id}"}
        self.stats = {
            "api_calls": 0,
            "cache_hits": 0,
            "wikidata_hits": 0,
            "fallback_hits": 0,
            "errors": 0,
        }
        self.wikidata = WikidataFetcher(delay=delay / 2)

    def get_monthly_pageviews(self, person_name: str) -> Tuple[int, str]:
        cached = self.cache.get(person_name)
        if cached:
            self.stats["cache_hits"] += 1
            return cached["monthly_views"], cached["page_title"]

        try:
            page_title = self.wikidata.resolve_person(person_name)

            if page_title:
                self.stats["wikidata_hits"] += 1
            else:
                page_title = self._search_wikipedia(person_name)
                if page_title:
                    self.stats["fallback_hits"] += 1

            if not page_title:
                self.cache.set(person_name, "", 0, ttl_days=7)
                return 0, ""

            monthly_views = self._fetch_pageviews(page_title)
            ttl_days = 90 if self._is_historical(person_name) else 30
            self.cache.set(person_name, page_title, monthly_views, ttl_days=ttl_days)

            self.stats["api_calls"] += 1
            return monthly_views, page_title

        except Exception as e:
            self.stats["errors"] += 1
            return 0, ""

    def _search_wikipedia(self, person_name: str) -> Optional[str]:
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

        return results[0]["title"]

    def _fetch_pageviews(self, page_title: str) -> int:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        encoded_title = quote(page_title.replace(" ", "_"), safe="")

        url = (
            f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
            f"ja.wikipedia/all-access/all-agents/{encoded_title}/daily/"
            f"{start_date.strftime('%Y%m%d')}/{end_date.strftime('%Y%m%d')}"
        )

        time.sleep(self.delay)

        response = requests.get(url, headers=self.headers, timeout=10)

        if response.status_code == 404:
            return 0

        response.raise_for_status()
        data = response.json()

        total_views = sum(item["views"] for item in data.get("items", []))
        return total_views

    def _is_historical(self, person_name: str) -> bool:
        historical_keywords = ["時代", "世紀", "将軍", "天皇", "武将", "BC", "紀元前"]
        return any(kw in person_name for kw in historical_keywords)


def calculate_fame_score_v2(monthly_pv: int, row: Dict) -> float:
    if monthly_pv > 0:
        pv_score = math.log10(max(1, monthly_pv)) * 10
    else:
        pv_score = 0.0

    wiki_exists_bonus = 15.0 if monthly_pv > 0 else 0.0

    try:
        award_level = int(row.get("award_level", 0) or 0)
    except (ValueError, TypeError):
        award_level = 0
    award_bonus = min(9.0, award_level * 3)

    textbook_bonus = 10.0 if str(row.get("textbook", "")).upper() == "TRUE" else 0.0
    notoriety_penalty = -20.0 if str(row.get("notoriety", "")).upper() == "TRUE" else 0.0

    raw_score = pv_score + wiki_exists_bonus + award_bonus + textbook_bonus + notoriety_penalty
    fame_score = max(0.0, min(100.0, raw_score))

    return round(fame_score, 2)


def process_person(person: Dict, fetcher: WikipediaPageviewsFetcher) -> Dict:
    """1人の人物を処理"""
    person_id = person["person_id"]
    person_name = person["person_name"]

    monthly_pv, page_title = fetcher.get_monthly_pageviews(person_name)
    fame_score = calculate_fame_score_v2(monthly_pv, person)

    return {
        "person_id": person_id,
        "person_name": person_name,
        "fame_score": fame_score,
        "monthly_pv": monthly_pv,
        "page_title": page_title,
    }


def get_unique_persons(csv_path: Path) -> List[Dict]:
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


def update_csv_with_scores(csv_path: Path, person_scores: Dict[str, Dict]) -> int:
    temp_path = csv_path.with_suffix(".tmp")
    updated_count = 0
    current_time = datetime.now().isoformat()

    with open(csv_path, "r", encoding="utf-8-sig") as infile:
        reader = csv.DictReader(infile)
        fieldnames = list(reader.fieldnames)

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

    temp_path.replace(csv_path)
    return updated_count


def main():
    parser = argparse.ArgumentParser(description="有名度スコア v2 並列処理版")
    parser.add_argument("--dry-run", action="store_true", help="ドライラン")
    parser.add_argument("--execute", action="store_true", help="実行")
    parser.add_argument("--limit", type=int, help="処理件数制限")
    parser.add_argument("--workers", type=int, default=4, help="並列ワーカー数")
    parser.add_argument("--delay", type=float, default=1.0, help="API呼び出し間隔（秒）")
    parser.add_argument(
        "--csv-path",
        type=Path,
        default=project_root / "preserved/data/MASTER_EPISODES_CURRENT.csv",
        help="CSVファイルパス",
    )

    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        print("⚠️ --dry-run または --execute を指定してください")
        return

    print("=" * 70)
    print(f"有名度スコア v2 - 並列処理版（{args.workers}ワーカー）")
    print("=" * 70)

    # 共有キャッシュ
    cache = WikipediaPageviewsCache()

    # 人物リスト取得
    persons = get_unique_persons(args.csv_path)
    total = len(persons)
    print(f"\n📊 ユニーク人物数: {total}人")

    if args.limit:
        persons = persons[: args.limit]
        print(f"📊 処理対象: {len(persons)}人（--limit {args.limit}）")

    # フェッチャー作成（各ワーカー用）
    fetchers = [WikipediaPageviewsFetcher(cache, delay=args.delay, worker_id=i) for i in range(args.workers)]

    # 並列処理
    person_scores = {}
    start_time = time.time()
    processed = 0
    lock = threading.Lock()

    print("\n🚀 並列スコア算出開始...")

    def worker_task(person: Dict, worker_id: int) -> Dict:
        return process_person(person, fetchers[worker_id])

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(worker_task, person, i % args.workers): person for i, person in enumerate(persons)}

        for future in as_completed(futures):
            try:
                result = future.result()
                with lock:
                    person_scores[result["person_id"]] = result
                    processed += 1

                    if processed % 100 == 0 or processed == len(persons):
                        elapsed = time.time() - start_time
                        rate = processed / elapsed if elapsed > 0 else 0
                        eta = (len(persons) - processed) / rate if rate > 0 else 0
                        print(
                            f"\r[{processed}/{len(persons)}] {rate:.1f}人/秒, ETA: {eta / 60:.1f}分", end="", flush=True
                        )

            except Exception as e:
                print(f"\n⚠️ エラー: {e}")

    elapsed = time.time() - start_time

    # 結果表示
    print(f"\n\n✅ スコア算出完了（{elapsed:.1f}秒）")

    # 統計集計
    total_stats = {k: sum(f.stats[k] for f in fetchers) for k in fetchers[0].stats}
    print("\n📊 API統計:")
    print(f"  API呼び出し: {total_stats['api_calls']}")
    print(f"  キャッシュヒット: {total_stats['cache_hits']}")
    print(f"  Wikidataヒット: {total_stats['wikidata_hits']}")
    print(f"  フォールバック: {total_stats['fallback_hits']}")
    print(f"  エラー: {total_stats['errors']}")

    # スコア分布
    scores = [s["fame_score"] for s in person_scores.values()]
    if scores:
        print("\n📊 スコア分布:")
        print(f"  最高: {max(scores):.2f}")
        print(f"  最低: {min(scores):.2f}")
        print(f"  平均: {sum(scores) / len(scores):.2f}")
        print(f"  ユニーク値数: {len(set(scores))}")

    # Top 10
    top10 = sorted(person_scores.values(), key=lambda x: x["fame_score"], reverse=True)[:10]
    print("\n🏆 Top 10:")
    for i, p in enumerate(top10, 1):
        print(f"  {i:2}. {p['person_name'][:15]:<15} {p['fame_score']:6.2f}点 (PV: {p['monthly_pv']:,})")

    # CSV更新
    if args.execute:
        updated = update_csv_with_scores(args.csv_path, person_scores)
        print(f"\n✅ CSV更新: {updated}件")
    else:
        print("\n🔍 ドライラン完了（CSV更新なし）")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
