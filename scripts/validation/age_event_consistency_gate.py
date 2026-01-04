#!/usr/bin/env python3
"""
年齢-イベント整合性ゲート

重要イベント（ノーベル賞受賞、大統領就任等）を記述するエピソードにおいて、
年齢フィールドがWikidata生年と整合しているかを検証する。

使用方法:
    python scripts/validation/age_event_consistency_gate.py [--fix]

終了コード:
    0: 不整合なし
    1: 不整合あり
"""

import argparse
import csv
import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
CSV_PATH = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
DB_PATH = PROJECT_ROOT / "data" / "cache" / "fame_score.db"
REPORT_DIR = PROJECT_ROOT / "src" / "reports"

# 重要イベントと検証用データ
CRITICAL_EVENTS = {
    "ノーベル賞": {
        "pattern": r"ノーベル.+賞(を)?受賞(し|しま)",
        "wikidata_property": "P166",  # award received
    },
}


def load_wikidata_cache():
    """Wikidataキャッシュから生年を取得"""
    cache_file = REPORT_DIR / "wikidata_birth_years.json"
    if cache_file.exists():
        with open(cache_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def check_age_consistency(episodes: list, wikidata_cache: dict) -> list:
    """年齢整合性をチェック"""
    issues = []

    # DBからWikidata IDを取得
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    for ep in episodes:
        text = ep.get("episode_text", "")
        person_id = ep.get("person_id", "")
        age_str = ep.get("age", "")

        try:
            age = int(float(age_str))
        except (ValueError, TypeError):
            continue

        # 重要イベントのチェック
        for event_name, event_config in CRITICAL_EVENTS.items():
            if not re.search(event_config["pattern"], text):
                continue

            # Wikidata IDを取得
            cursor.execute("SELECT wikidata_id FROM fame_cache WHERE person_id = ?", (person_id,))
            row = cursor.fetchone()
            if not row or not row[0]:
                continue

            wikidata_id = row[0]
            birth_info = wikidata_cache.get(wikidata_id, {})
            birth_year = birth_info.get("birth_year")

            if not birth_year:
                continue

            # 本文から受賞年を抽出（「受賞」の近くにある年のみ）
            # パターン: 「XXXX年...受賞」または「受賞...XXXX年」
            award_year_match = re.search(r"(\d{4})年.{0,15}(ノーベル|受賞)|ノーベル.+賞.{0,10}(\d{4})年", text[:300])
            if not award_year_match:
                continue

            event_year = int(award_year_match.group(1) or award_year_match.group(3))
            expected_age = event_year - birth_year

            # 許容差: ±1歳（誕生日タイミング）
            if abs(age - expected_age) > 1:
                issues.append(
                    {
                        "episode_id": ep.get("episode_id"),
                        "person_name": ep.get("person_name"),
                        "event": event_name,
                        "current_age": age,
                        "expected_age": expected_age,
                        "event_year": event_year,
                        "birth_year": birth_year,
                    }
                )

    conn.close()
    return issues


def main():
    parser = argparse.ArgumentParser(description="年齢-イベント整合性ゲート")
    parser.add_argument("--fix", action="store_true", help="修正を実行")
    args = parser.parse_args()

    print("=" * 60)
    print("年齢-イベント整合性ゲート")
    print("=" * 60)

    # データ読み込み
    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        episodes = list(csv.DictReader(f))

    wikidata_cache = load_wikidata_cache()

    print(f"エピソード数: {len(episodes)}")
    print(f"Wikidataキャッシュ: {len(wikidata_cache)}件")

    # チェック実行
    issues = check_age_consistency(episodes, wikidata_cache)

    print(f"\n不整合: {len(issues)}件")

    if issues:
        print("\n【検出された不整合】")
        for issue in issues[:10]:
            print(f"  {issue['episode_id']} ({issue['person_name']})")
            print(f"    {issue['event']}: {issue['current_age']}歳 → 期待{issue['expected_age']}歳")
        return 1
    else:
        print("\n✅ 不整合なし")
        return 0


if __name__ == "__main__":
    exit(main())
