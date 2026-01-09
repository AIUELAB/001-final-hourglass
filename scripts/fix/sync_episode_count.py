#!/usr/bin/env python3
"""
Phase 32: episode_count同期修正

問題:
- 802人でepisode_countが不整合
- 1626.0: 679件（旧マイグレーション残骸）
- 空文字: 356件

修正方針:
- 各person_idのエピソード数を実カウント
- 全エピソードのepisode_countを統一
"""

import csv
from collections import Counter, defaultdict
from pathlib import Path

CSV_PATH = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")


def analyze_inconsistency() -> dict:
    """不整合を分析"""
    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # 人物ごとのepisode_count値と実エピソード数
    person_counts = defaultdict(set)
    person_actual = defaultdict(int)

    for row in rows:
        pid = row.get("person_id", "")
        count = row.get("episode_count", "")
        if pid:
            person_counts[pid].add(count)
            person_actual[pid] += 1

    # 不整合検出
    inconsistent = {
        pid: {"values": sorted(counts), "actual": person_actual[pid]}
        for pid, counts in person_counts.items()
        if len(counts) > 1
    }

    return {
        "total_persons": len(person_counts),
        "inconsistent_count": len(inconsistent),
        "inconsistent": inconsistent,
    }


def sync_episode_counts(dry_run: bool = True) -> dict:
    """episode_countを同期"""
    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    # 人物ごとの実エピソード数をカウント
    person_actual = Counter(row.get("person_id", "") for row in rows)

    # 修正
    changes = []
    for row in rows:
        pid = row.get("person_id", "")
        old_count = row.get("episode_count", "")
        new_count = str(float(person_actual[pid]))

        if old_count != new_count:
            changes.append(
                {
                    "person_id": pid,
                    "person_name": row.get("person_name", ""),
                    "episode_id": row.get("episode_id", ""),
                    "old": old_count,
                    "new": new_count,
                }
            )
            row["episode_count"] = new_count

    if not dry_run and changes:
        with open(CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    return {
        "total_rows": len(rows),
        "changes": len(changes),
        "dry_run": dry_run,
        "sample_changes": changes[:20],
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="episode_count同期")
    parser.add_argument("--execute", action="store_true", help="実際に修正を適用")
    args = parser.parse_args()

    print("=== Phase 32: episode_count同期修正 ===\n")

    # 分析
    print("1. 不整合分析...")
    analysis = analyze_inconsistency()
    print(f"   総人物数: {analysis['total_persons']}")
    print(f"   不整合人物数: {analysis['inconsistent_count']}")

    # 同期
    print("\n2. 同期処理...")
    dry_run = not args.execute
    result = sync_episode_counts(dry_run=dry_run)

    print(f"   総行数: {result['total_rows']}")
    print(f"   変更行数: {result['changes']}")
    print(f"   モード: {'dry-run' if dry_run else '実行'}")

    if result["sample_changes"]:
        print("\n   サンプル変更:")
        for c in result["sample_changes"][:10]:
            print(f"     {c['person_name']}: {c['old']} → {c['new']}")

    if dry_run:
        print("\n※ dry-runモードです。--execute で実際に適用します。")
    else:
        print("\n✓ episode_count同期完了")

    return result


if __name__ == "__main__":
    main()
