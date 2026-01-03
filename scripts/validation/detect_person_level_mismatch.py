#!/usr/bin/env python3
"""
person-level項目の不整合検出スクリプト

同一人物内で統一すべき項目（celebrity_score_v2等）が
異なる値を持つエピソードを検出する。

使用方法:
    python scripts/validation/detect_person_level_mismatch.py
    python scripts/validation/detect_person_level_mismatch.py --fix  # 修正も実行
"""

import argparse
import csv
from collections import defaultdict
from pathlib import Path


CSV_PATH = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")

# person-level項目（同一人物で統一すべき項目）
PERSON_LEVEL_COLUMNS = [
    "celebrity_score_v2",
    "sitelinks_count",
    "multi_lang_pv",
]


def detect_mismatches():
    """不整合を検出"""
    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames

    # person_id別に値を集計
    person_values = defaultdict(lambda: defaultdict(set))
    person_episodes = defaultdict(list)

    for row in rows:
        pid = row.get("person_id", "")
        if not pid:
            continue
        person_episodes[pid].append(row)
        for col in PERSON_LEVEL_COLUMNS:
            val = row.get(col, "")
            if val:
                person_values[pid][col].add(val)

    # 不整合を検出
    mismatches = []
    for pid, col_values in person_values.items():
        for col, values in col_values.items():
            if len(values) > 1:
                mismatches.append(
                    {
                        "person_id": pid,
                        "person_name": person_episodes[pid][0].get("person_name", ""),
                        "column": col,
                        "values": list(values),
                        "episode_count": len(person_episodes[pid]),
                    }
                )

    return mismatches, rows, fieldnames, person_episodes


def fix_mismatches(rows, fieldnames, person_episodes):
    """不整合を修正（最頻値に統一）"""
    fixed_count = 0

    for pid, episodes in person_episodes.items():
        if len(episodes) <= 1:
            continue

        # 各カラムの最頻値を取得
        for col in PERSON_LEVEL_COLUMNS:
            values = [ep.get(col, "") for ep in episodes if ep.get(col)]
            if not values:
                continue

            # 最頻値を取得
            from collections import Counter

            most_common = Counter(values).most_common(1)[0][0]

            # 全エピソードを最頻値に統一
            for ep in episodes:
                if ep.get(col) != most_common:
                    ep[col] = most_common
                    fixed_count += 1

    # 保存
    with open(CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return fixed_count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fix", action="store_true", help="不整合を修正")
    args = parser.parse_args()

    print("=" * 70)
    print("person-level項目 不整合検出")
    print("=" * 70)

    mismatches, rows, fieldnames, person_episodes = detect_mismatches()

    if not mismatches:
        print("不整合なし")
        return

    print(f"\n不整合件数: {len(mismatches)}")
    print()

    # 人物別に集約
    person_mismatches = defaultdict(list)
    for m in mismatches:
        person_mismatches[m["person_id"]].append(m)

    print(f"影響人物数: {len(person_mismatches)}")
    print()

    # 上位10件を表示
    print("代表例（上位10人物）:")
    for i, (pid, mm) in enumerate(list(person_mismatches.items())[:10]):
        name = mm[0]["person_name"]
        cols = [m["column"] for m in mm]
        print(f"  {pid} ({name}): {', '.join(cols)}")

    if args.fix:
        print()
        print("=" * 70)
        print("修正実行中...")
        fixed = fix_mismatches(rows, fieldnames, person_episodes)
        print(f"修正完了: {fixed}件の値を更新")
    else:
        print()
        print("修正するには --fix オプションを付けて実行してください")


if __name__ == "__main__":
    main()
