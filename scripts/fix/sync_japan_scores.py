#!/usr/bin/env python3
"""
Phase 33: is_japanese/fame_score_japan同期

問題:
- 3234件でis_japaneseが欠損
- 2845人で同一人物内に混在（空と非空）

解決:
- 同一person_id内で、非空の値を空のエピソードにコピー
- fame_score_japanも同様に同期
"""

import csv
from collections import defaultdict
from pathlib import Path

CSV_PATH = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")


def analyze_missing() -> dict:
    """欠損状況を分析"""
    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # 人物ごとのデータ
    person_data = defaultdict(lambda: {"is_jp": set(), "fame_jp": set(), "episodes": []})
    for r in rows:
        pid = r.get("person_id", "")
        is_jp = r.get("is_japanese", "")
        fame_jp = r.get("fame_score_japan", "")
        person_data[pid]["is_jp"].add(is_jp)
        person_data[pid]["fame_jp"].add(fame_jp)
        person_data[pid]["episodes"].append(r)

    # 混在を検出
    mixed_is_jp = [pid for pid, data in person_data.items() if len(data["is_jp"]) > 1 and "" in data["is_jp"]]
    mixed_fame = [pid for pid, data in person_data.items() if len(data["fame_jp"]) > 1 and "" in data["fame_jp"]]

    return {
        "total_persons": len(person_data),
        "is_japanese_missing": sum(1 for r in rows if not r.get("is_japanese", "")),
        "fame_score_japan_missing": sum(1 for r in rows if not r.get("fame_score_japan", "")),
        "mixed_is_japanese": len(mixed_is_jp),
        "mixed_fame_score_japan": len(mixed_fame),
    }


def sync_japan_scores(dry_run: bool = True) -> dict:
    """同一人物内でis_japaneseとfame_score_japanを同期"""
    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    # 人物ごとに非空の値を収集
    person_values = defaultdict(lambda: {"is_japanese": None, "fame_score_japan": None})
    for r in rows:
        pid = r.get("person_id", "")
        is_jp = r.get("is_japanese", "")
        fame_jp = r.get("fame_score_japan", "")

        # 非空の値を採用
        if is_jp and person_values[pid]["is_japanese"] is None:
            person_values[pid]["is_japanese"] = is_jp
        if fame_jp and person_values[pid]["fame_score_japan"] is None:
            person_values[pid]["fame_score_japan"] = fame_jp

    # 同期
    changes_is_jp = []
    changes_fame = []
    for row in rows:
        pid = row.get("person_id", "")
        values = person_values[pid]

        # is_japanese の同期
        if not row.get("is_japanese", "") and values["is_japanese"]:
            changes_is_jp.append(
                {
                    "person_id": pid,
                    "person_name": row.get("person_name", ""),
                    "episode_id": row.get("episode_id", ""),
                    "old": "",
                    "new": values["is_japanese"],
                }
            )
            row["is_japanese"] = values["is_japanese"]

        # fame_score_japan の同期
        if not row.get("fame_score_japan", "") and values["fame_score_japan"]:
            changes_fame.append(
                {
                    "person_id": pid,
                    "person_name": row.get("person_name", ""),
                    "episode_id": row.get("episode_id", ""),
                    "old": "",
                    "new": values["fame_score_japan"],
                }
            )
            row["fame_score_japan"] = values["fame_score_japan"]

    if not dry_run and (changes_is_jp or changes_fame):
        with open(CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    return {
        "total_rows": len(rows),
        "is_japanese_synced": len(changes_is_jp),
        "fame_score_japan_synced": len(changes_fame),
        "dry_run": dry_run,
        "sample_is_jp": changes_is_jp[:10],
        "sample_fame": changes_fame[:10],
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="is_japanese/fame_score_japan同期")
    parser.add_argument("--execute", action="store_true", help="実際に修正を適用")
    args = parser.parse_args()

    print("=== Phase 33: is_japanese/fame_score_japan同期 ===\n")

    # 分析
    print("1. 欠損分析...")
    analysis = analyze_missing()
    print(f"   総人物数: {analysis['total_persons']}")
    print(f"   is_japanese欠損: {analysis['is_japanese_missing']}件")
    print(f"   fame_score_japan欠損: {analysis['fame_score_japan_missing']}件")
    print(f"   is_japanese混在人物: {analysis['mixed_is_japanese']}人（同期可能）")
    print(f"   fame_score_japan混在人物: {analysis['mixed_fame_score_japan']}人（同期可能）")

    # 同期
    print("\n2. 同期処理...")
    dry_run = not args.execute
    result = sync_japan_scores(dry_run=dry_run)

    print(f"   総行数: {result['total_rows']}")
    print(f"   is_japanese同期: {result['is_japanese_synced']}件")
    print(f"   fame_score_japan同期: {result['fame_score_japan_synced']}件")
    print(f"   モード: {'dry-run' if dry_run else '実行'}")

    if result["sample_is_jp"]:
        print("\n   is_japaneseサンプル:")
        for c in result["sample_is_jp"][:5]:
            print(f"     {c['person_name']}: '' → {c['new']}")

    if result["sample_fame"]:
        print("\n   fame_score_japanサンプル:")
        for c in result["sample_fame"][:5]:
            print(f"     {c['person_name']}: '' → {c['new']}")

    if dry_run:
        print("\n※ dry-runモードです。--execute で実際に適用します。")
    else:
        print("\n✓ 同期完了")

    return result


if __name__ == "__main__":
    main()
