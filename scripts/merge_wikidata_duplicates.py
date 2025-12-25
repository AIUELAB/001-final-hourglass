#!/usr/bin/env python3
"""
Wikidata ID重複エントリの統合スクリプト。

同一Wikidata IDを持つ複数のperson_idを統合し、
エピソードを一つのperson_idに集約する。

戦略:
- エピソード数が最も多いperson_idを正規IDとして採用
- 同数の場合はfame_scoreが高い方を採用
- 他のperson_idのエピソードを正規IDに移行
"""

import csv
import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# パス
CACHE_DB = Path("data/cache/fame_score.db")
CSV_PATH = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")
BACKUP_PATH = Path(f"preserved/data/MASTER_EPISODES_BACKUP_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
REPORT_PATH = Path("src/reports/wikidata_duplicate_merge_report.txt")


def get_duplicates():
    """fame_cacheから重複Wikidata IDを取得"""
    conn = sqlite3.connect(str(CACHE_DB))
    cursor = conn.execute("""
        SELECT wikidata_id, person_id, person_name, fame_score_v3
        FROM fame_cache
        WHERE wikidata_id IS NOT NULL AND wikidata_id != ''
        ORDER BY wikidata_id
    """)

    wikidata_entries = defaultdict(list)
    for row in cursor:
        wikidata_entries[row[0]].append(
            {
                "person_id": row[1],
                "person_name": row[2],
                "fame_score": row[3] or 0,
            }
        )
    conn.close()

    return {wid: entries for wid, entries in wikidata_entries.items() if len(entries) > 1}


def get_episode_counts():
    """CSVからperson_idごとのエピソード数を取得"""
    counts = defaultdict(int)
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = row.get("person_id", "")
            if pid:
                counts[pid] += 1
    return counts


def create_merge_plan(duplicates, episode_counts):
    """統合計画を作成"""
    merge_plan = []

    for wikidata_id, entries in duplicates.items():
        # エピソード数でソート、同数ならfame_scoreでソート
        sorted_entries = sorted(
            entries, key=lambda x: (episode_counts.get(x["person_id"], 0), x["fame_score"]), reverse=True
        )

        canonical = sorted_entries[0]
        to_merge = sorted_entries[1:]

        merge_plan.append(
            {
                "wikidata_id": wikidata_id,
                "canonical_pid": canonical["person_id"],
                "canonical_name": canonical["person_name"],
                "canonical_episodes": episode_counts.get(canonical["person_id"], 0),
                "merge_from": [
                    {
                        "person_id": e["person_id"],
                        "person_name": e["person_name"],
                        "episodes": episode_counts.get(e["person_id"], 0),
                    }
                    for e in to_merge
                ],
            }
        )

    return merge_plan


def execute_merge(merge_plan, dry_run=True):
    """統合を実行"""
    # person_id置換マップを作成
    replacement_map = {}
    for plan in merge_plan:
        canonical_pid = plan["canonical_pid"]
        canonical_name = plan["canonical_name"]
        for merge_entry in plan["merge_from"]:
            replacement_map[merge_entry["person_id"]] = {
                "new_pid": canonical_pid,
                "new_name": canonical_name,
            }

    if dry_run:
        print(f"\n[DRY RUN] 置換対象: {len(replacement_map)} person_ids")
        return replacement_map, 0

    # バックアップ作成
    print(f"バックアップ作成: {BACKUP_PATH}")
    with open(CSV_PATH, encoding="utf-8-sig") as src:
        with open(BACKUP_PATH, "w", encoding="utf-8-sig") as dst:
            dst.write(src.read())

    # CSV読み込み・更新
    rows = []
    updated_count = 0

    with open(CSV_PATH, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames

        for row in reader:
            pid = row.get("person_id", "")
            if pid in replacement_map:
                replacement = replacement_map[pid]
                row["person_id"] = replacement["new_pid"]
                row["person_name"] = replacement["new_name"]
                updated_count += 1
            rows.append(row)

    # CSV書き込み
    with open(CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"CSV更新完了: {updated_count} エピソードの person_id を更新")
    return replacement_map, updated_count


def cleanup_fame_cache(merge_plan, dry_run=True):
    """fame_cacheから重複エントリを削除"""
    pids_to_delete = []
    for plan in merge_plan:
        for merge_entry in plan["merge_from"]:
            pids_to_delete.append(merge_entry["person_id"])

    if dry_run:
        print(f"\n[DRY RUN] 削除対象fame_cache: {len(pids_to_delete)} entries")
        return len(pids_to_delete)

    conn = sqlite3.connect(str(CACHE_DB))
    cursor = conn.cursor()

    for pid in pids_to_delete:
        cursor.execute("DELETE FROM fame_cache WHERE person_id = ?", (pid,))

    conn.commit()
    deleted = cursor.rowcount  # 最後の削除のみ返す
    conn.close()

    print(f"fame_cache削除完了: {len(pids_to_delete)} entries")
    return len(pids_to_delete)


def generate_report(merge_plan, episode_counts):
    """レポート生成"""
    lines = []
    lines.append("=" * 70)
    lines.append("Wikidata ID重複統合レポート")
    lines.append(f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 70)
    lines.append("")

    # サマリー
    total_groups = len(merge_plan)
    total_merge_pids = sum(len(p["merge_from"]) for p in merge_plan)
    total_merge_episodes = sum(sum(e["episodes"] for e in p["merge_from"]) for p in merge_plan)

    lines.append("## サマリー")
    lines.append(f"- 統合グループ数: {total_groups}")
    lines.append(f"- 削除されるperson_id数: {total_merge_pids}")
    lines.append(f"- 移動されるエピソード数: {total_merge_episodes}")
    lines.append("")

    # 3件以上の詳細
    lines.append("=" * 70)
    lines.append("## 3件以上の重複グループ")
    lines.append("=" * 70)

    for plan in merge_plan:
        if len(plan["merge_from"]) >= 2:
            lines.append("")
            lines.append(f"### {plan['wikidata_id']}")
            lines.append(
                f"正規: {plan['canonical_pid']} | {plan['canonical_name']} ({plan['canonical_episodes']}エピソード)"
            )
            for e in plan["merge_from"]:
                lines.append(f"  統合: {e['person_id']} | {e['person_name']} ({e['episodes']}エピソード)")

    # 2件重複の詳細（全件）
    lines.append("")
    lines.append("=" * 70)
    lines.append("## 2件重複グループ")
    lines.append("=" * 70)

    for plan in merge_plan:
        if len(plan["merge_from"]) == 1:
            lines.append("")
            lines.append(f"### {plan['wikidata_id']}")
            lines.append(
                f"正規: {plan['canonical_pid']} | {plan['canonical_name']} ({plan['canonical_episodes']}エピソード)"
            )
            e = plan["merge_from"][0]
            lines.append(f"  統合: {e['person_id']} | {e['person_name']} ({e['episodes']}エピソード)")

    report_text = "\n".join(lines)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report_text)

    print(f"\nレポート保存: {REPORT_PATH}")
    return report_text


def main():
    import sys

    dry_run = "--execute" not in sys.argv

    print("=== Wikidata ID重複統合 ===\n")

    # 重複検出
    duplicates = get_duplicates()
    print(f"重複グループ数: {len(duplicates)}")

    # エピソード数取得
    episode_counts = get_episode_counts()

    # 統合計画作成
    merge_plan = create_merge_plan(duplicates, episode_counts)

    # レポート生成
    generate_report(merge_plan, episode_counts)

    if dry_run:
        print("\n[DRY RUN モード] --execute オプションで実行")
        execute_merge(merge_plan, dry_run=True)
        cleanup_fame_cache(merge_plan, dry_run=True)
    else:
        print("\n[実行モード]")
        execute_merge(merge_plan, dry_run=False)
        cleanup_fame_cache(merge_plan, dry_run=False)
        print("\n統合完了!")


if __name__ == "__main__":
    main()
