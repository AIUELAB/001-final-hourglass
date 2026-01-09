#!/usr/bin/env python3
"""
品質ゲート: episode_fame_score (col30) と episode_fame_v6 の同期チェック

pre-commit hookから呼び出し可能
exit 0: OK, exit 1: NG
"""

import csv
import sys
from pathlib import Path

CSV_PATH = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")
MAX_DIFF_THRESHOLD = 0.1  # 許容誤差
MAX_DESYNC_COUNT = 10  # 許容する非同期件数


def check_sync():
    """同期チェック"""
    if not CSV_PATH.exists():
        print("SKIP: CSVファイルが存在しません")
        return 0

    with open(CSV_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    desync_count = 0
    desync_examples = []

    for row in rows:
        col30 = row.get("episode_fame_score", "")
        v6 = row.get("episode_fame_v6", "")

        if not col30 or not v6:
            continue

        try:
            col30_val = float(col30)
            v6_val = float(v6)

            if abs(col30_val - v6_val) > MAX_DIFF_THRESHOLD:
                desync_count += 1
                if len(desync_examples) < 5:
                    eid = row.get("\ufeffepisode_id") or row.get("episode_id")
                    desync_examples.append(f"  {eid}: col30={col30_val:.2f}, v6={v6_val:.2f}")
        except ValueError:
            pass

    if desync_count > MAX_DESYNC_COUNT:
        print("=" * 60)
        print("episode_fame_score 同期チェック")
        print("=" * 60)
        print(f"非同期件数: {desync_count}件 (閾値: {MAX_DESYNC_COUNT})")
        print("ステータス: FAIL")
        print("\n【非同期例】")
        for ex in desync_examples:
            print(ex)
        print("\n修正: python scripts/migrations/sync_episode_fame_v6_to_col30.py")
        return 1

    print(f"episode_fame_score 同期チェック: OK ({desync_count}件)")
    return 0


if __name__ == "__main__":
    sys.exit(check_sync())
