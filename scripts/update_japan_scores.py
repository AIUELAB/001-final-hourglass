#!/usr/bin/env python3
"""
日本向けスコア一括更新スクリプト。

1. 全人物の is_japanese フラグをWikidata P27から取得
2. fame_score_japan を計算
3. CSVを更新
"""

import csv
import json
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

# パス設定
PROJECT_ROOT = Path(__file__).parent.parent
CSV_PATH = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
CACHE_DB = PROJECT_ROOT / "data" / "cache" / "japan_score.db"
REPORT_PATH = PROJECT_ROOT / "src" / "reports" / f"japan_score_update_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

# Wikidata設定
WIKIDATA_API = "https://www.wikidata.org/wiki/Special:EntityData"
Q_JAPAN = "Q17"
REQUEST_INTERVAL = 0.15  # レート制限


def init_cache() -> sqlite3.Connection:
    """キャッシュDBを初期化"""
    CACHE_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(CACHE_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS japanese_cache (
            person_id TEXT PRIMARY KEY,
            wikidata_id TEXT,
            is_japanese INTEGER,
            fetched_at TEXT
        )
    """)
    conn.commit()
    return conn


def get_cached_japanese(conn: sqlite3.Connection, person_id: str) -> Optional[bool]:
    """キャッシュから is_japanese を取得"""
    cursor = conn.execute("SELECT is_japanese FROM japanese_cache WHERE person_id = ?", (person_id,))
    row = cursor.fetchone()
    if row:
        return bool(row[0])
    return None


def cache_japanese(conn: sqlite3.Connection, person_id: str, wikidata_id: str, is_japanese: bool):
    """is_japanese をキャッシュに保存"""
    conn.execute(
        """
        INSERT OR REPLACE INTO japanese_cache (person_id, wikidata_id, is_japanese, fetched_at)
        VALUES (?, ?, ?, ?)
    """,
        (person_id, wikidata_id, 1 if is_japanese else 0, datetime.now().isoformat()),
    )
    conn.commit()


def fetch_is_japanese(wikidata_id: str) -> bool:
    """Wikidata APIから is_japanese を取得"""
    if not wikidata_id or not wikidata_id.startswith("Q"):
        return False

    time.sleep(REQUEST_INTERVAL)

    url = f"{WIKIDATA_API}/{wikidata_id}.json"
    headers = {"User-Agent": "FameScoreBot/3.0"}

    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code != 200:
            return False

        data = response.json()
        entity = data.get("entities", {}).get(wikidata_id, {})
        claims = entity.get("claims", {})

        # P27 (country of citizenship) をチェック
        p27_claims = claims.get("P27", [])
        for claim in p27_claims:
            value = claim.get("mainsnak", {}).get("datavalue", {}).get("value", {})
            if value.get("id") == Q_JAPAN:
                return True

        return False

    except Exception:
        return False


def search_wikidata_id(person_name: str) -> Optional[str]:
    """人物名からWikidata IDを検索"""
    time.sleep(REQUEST_INTERVAL)

    url = "https://www.wikidata.org/w/api.php"
    params = {
        "action": "wbsearchentities",
        "search": person_name,
        "language": "ja",
        "format": "json",
        "limit": 1,
    }
    headers = {"User-Agent": "FameScoreBot/3.0"}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            results = data.get("search", [])
            if results:
                return results[0].get("id")
    except Exception:
        pass

    return None


def calculate_japan_score(
    global_score: float,
    is_japanese: bool,
    category: str,
    wikipedia_pv_ja: float,
    multi_lang_pv: float,
) -> float:
    """日本向けスコアを計算（scorer_japan.pyと同じロジック）"""
    if not is_japanese:
        return global_score

    # 設定値（config/fame_score_japan.yamlと同じ）
    BASE_ALPHA = 0.10
    CATEGORY_WEIGHTS = {
        "スポーツ": 0.40,
        "音楽": 0.20,
        "エンターテイメント": 0.20,
        "アニメ": 0.25,
        "漫画": 0.25,
        "ゲーム": 0.20,
        "芸術・文化": 0.15,
        "default": 0.05,
    }
    PV_RATIO_MAX = 0.15
    PV_RATIO_SCALE = 0.50

    # 上乗せ計算
    boost = BASE_ALPHA
    boost += CATEGORY_WEIGHTS.get(category, CATEGORY_WEIGHTS["default"])

    if multi_lang_pv > 0 and wikipedia_pv_ja > 0:
        ja_ratio = wikipedia_pv_ja / multi_lang_pv
        pv_bonus = min(ja_ratio * PV_RATIO_SCALE, PV_RATIO_MAX)
        boost += pv_bonus

    return round(global_score * (1 + boost), 2)


def main(dry_run: bool = False, limit: int = 0):
    """メイン処理"""
    print(f"=== 日本向けスコア更新 ({'dry-run' if dry_run else '実行'}モード) ===")
    print(f"開始時刻: {datetime.now().isoformat()}")

    # キャッシュ初期化
    conn = init_cache()

    # CSV読み込み
    with open(CSV_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        rows = list(reader)

    # 新しいカラムを追加
    if "is_japanese" not in fieldnames:
        fieldnames.append("is_japanese")
    if "fame_score_japan" not in fieldnames:
        fieldnames.append("fame_score_japan")

    # 重複排除（person_id単位）
    seen_persons = {}
    for row in rows:
        pid = row.get("person_id", "")
        if pid and pid not in seen_persons:
            seen_persons[pid] = row

    persons = list(seen_persons.values())
    total = len(persons)

    if limit > 0:
        persons = persons[:limit]

    print(f"対象人物数: {len(persons)} / {total}")

    stats = {
        "total": len(persons),
        "japanese": 0,
        "non_japanese": 0,
        "cached": 0,
        "fetched": 0,
        "errors": 0,
    }
    updates = []

    for i, row in enumerate(persons):
        pid = row.get("person_id", "")
        name = row.get("person_name", "")

        # 進捗表示（100件ごと）
        if (i + 1) % 100 == 0:
            print(f"  処理中: {i + 1}/{len(persons)} ({stats['japanese']}人が日本人)")

        # キャッシュ確認
        cached_result = get_cached_japanese(conn, pid)
        if cached_result is not None:
            is_japanese = cached_result
            stats["cached"] += 1
        else:
            # Wikidata IDを取得
            wikidata_id = search_wikidata_id(name)
            if wikidata_id:
                is_japanese = fetch_is_japanese(wikidata_id)
                cache_japanese(conn, pid, wikidata_id, is_japanese)
                stats["fetched"] += 1
            else:
                is_japanese = False
                stats["errors"] += 1

        if is_japanese:
            stats["japanese"] += 1
        else:
            stats["non_japanese"] += 1

        # 日本向けスコア計算
        global_score = float(row.get("fame_score_v3", 0) or 0)
        category = row.get("category", "")
        ja_pv = float(row.get("wikipedia_pv", 0) or 0)
        multi_pv = float(row.get("multi_lang_pv", 0) or 0)

        japan_score = calculate_japan_score(global_score, is_japanese, category, ja_pv, multi_pv)

        # 更新記録
        if is_japanese and japan_score != global_score:
            updates.append(
                {
                    "person_id": pid,
                    "person_name": name,
                    "category": category,
                    "global_score": global_score,
                    "japan_score": japan_score,
                    "boost": round((japan_score / global_score - 1) * 100, 1) if global_score > 0 else 0,
                }
            )

        # CSV行を更新
        seen_persons[pid]["is_japanese"] = "True" if is_japanese else "False"
        seen_persons[pid]["fame_score_japan"] = str(japan_score)

    # 全行にis_japanese/fame_score_japanを適用
    for row in rows:
        pid = row.get("person_id", "")
        if pid in seen_persons:
            row["is_japanese"] = seen_persons[pid].get("is_japanese", "False")
            row["fame_score_japan"] = seen_persons[pid].get("fame_score_japan", row.get("fame_score_v3", "0"))

    # CSV書き出し
    if not dry_run:
        with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    # レポート作成
    # Top20日本人をスコア順で抽出
    updates_sorted = sorted(updates, key=lambda x: x["japan_score"], reverse=True)[:20]

    report = {
        "timestamp": datetime.now().isoformat(),
        "mode": "dry-run" if dry_run else "applied",
        "stats": stats,
        "top20_japanese": updates_sorted,
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 結果表示
    print("\n=== 完了 ===")
    print(f"日本人: {stats['japanese']}人")
    print(f"非日本人: {stats['non_japanese']}人")
    print(f"キャッシュ利用: {stats['cached']}件")
    print(f"API取得: {stats['fetched']}件")

    print("\n=== 日本向けTop10 ===")
    for i, u in enumerate(updates_sorted[:10], 1):
        print(
            f"{i}. {u['person_name']} ({u['category']}): {u['global_score']:.2f} → {u['japan_score']:.2f} (+{u['boost']:.1f}%)"
        )

    print(f"\nレポート: {REPORT_PATH}")

    conn.close()
    return report


if __name__ == "__main__":
    import sys

    dry_run = "--dry-run" in sys.argv
    limit_arg = [a for a in sys.argv if a.startswith("--limit=")]
    limit = int(limit_arg[0].split("=")[1]) if limit_arg else 0

    main(dry_run=dry_run, limit=limit)
