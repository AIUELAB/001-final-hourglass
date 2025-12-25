#!/usr/bin/env python3
"""
Wikidata ID重複検出スクリプト。

同一Wikidata IDを持つ複数のperson_idを検出し、
統合計画を出力する。
"""

import csv
import sqlite3
from collections import defaultdict
from pathlib import Path


def main():
    # fame_cacheから重複を取得
    conn = sqlite3.connect("data/cache/fame_score.db")
    cursor = conn.execute("""
        SELECT wikidata_id, person_id, person_name, sitelinks, multi_lang_pv, fame_score_v3
        FROM fame_cache
        WHERE wikidata_id IS NOT NULL AND wikidata_id != ''
        ORDER BY wikidata_id
    """)

    # Wikidata ID -> entries マッピング
    wikidata_entries = defaultdict(list)
    for row in cursor:
        wikidata_entries[row[0]].append(
            {
                "person_id": row[1],
                "person_name": row[2],
                "sitelinks": row[3] or 0,
                "multi_lang_pv": row[4] or 0,
                "fame_score": row[5] or 0,
            }
        )
    conn.close()

    # CSVからエピソード数を取得
    episode_counts = defaultdict(int)
    csv_path = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")
    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = row.get("person_id", "")
            if pid:
                episode_counts[pid] += 1

    # 重複のみ抽出
    duplicates = {wid: entries for wid, entries in wikidata_entries.items() if len(entries) > 1}

    print("=== Wikidata ID重複検出結果 ===\n")
    print(f"総重複グループ数: {len(duplicates)}")

    # カウント
    count_3plus = sum(1 for entries in duplicates.values() if len(entries) >= 3)
    count_2 = sum(1 for entries in duplicates.values() if len(entries) == 2)
    print(f"  - 3件以上: {count_3plus}")
    print(f"  - 2件: {count_2}")

    # 3件以上の詳細
    print("\n=== 3件以上の重複 ===")
    for wid, entries in sorted(duplicates.items(), key=lambda x: -len(x[1])):
        if len(entries) >= 3:
            print(f"\n{wid} ({len(entries)}件):")
            for e in entries:
                eps = episode_counts.get(e["person_id"], 0)
                print(f"  {e['person_id']}: {e['person_name']} (エピソード:{eps}, score:{e['fame_score']:.1f})")

    # 2件重複サンプル
    print("\n\n=== 2件重複サンプル（30件） ===")
    sample_count = 0
    for wid, entries in duplicates.items():
        if len(entries) == 2:
            sample_count += 1
            if sample_count > 30:
                break
            print(f"\n{wid}:")
            for e in entries:
                eps = episode_counts.get(e["person_id"], 0)
                print(f"  {e['person_id']}: {e['person_name']} (エピソード:{eps})")

    # 統合計画サマリー
    print("\n\n=== 統合計画サマリー ===")
    total_pids_to_remove = sum(len(entries) - 1 for entries in duplicates.values())
    total_episodes_affected = 0

    for wid, entries in duplicates.items():
        # エピソード数でソート（多い方を残す）
        sorted_entries = sorted(entries, key=lambda x: episode_counts.get(x["person_id"], 0), reverse=True)
        # 2番目以降のエピソード数を集計
        for e in sorted_entries[1:]:
            total_episodes_affected += episode_counts.get(e["person_id"], 0)

    print(f"削除対象person_id数: {total_pids_to_remove}")
    print(f"移動対象エピソード数: {total_episodes_affected}")


if __name__ == "__main__":
    main()
