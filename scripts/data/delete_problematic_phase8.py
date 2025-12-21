#!/usr/bin/env python3
"""
問題Phase8エピソードの削除スクリプト

誤指令F-001により生成された問題エピソード（1件）を削除する：
- EDD16CB43: 伊能忠敬 (71歳) - 「すでにこの世を去っていましたが」
"""

import csv
import shutil
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
BACKUP_DIR = PROJECT_ROOT / "preserved" / "backup"

# 削除対象のepisode_id
DELETE_IDS = ["EDD16CB43"]


def delete_episodes(dry_run: bool = True):
    """問題エピソードを削除"""

    print("=" * 70)
    print("🗑️  問題Phase8エピソード削除")
    print("=" * 70)
    print(f"対象: {MASTER_CSV}")
    print(f"モード: {'ドライラン' if dry_run else '本番実行'}")
    print(f"削除ID: {', '.join(DELETE_IDS)}")
    print()

    # CSV読み込み
    with open(MASTER_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    initial_count = len(rows)
    print(f"📊 初期件数: {initial_count}件")

    # 削除対象を特定
    to_delete = []
    remaining = []

    for row in rows:
        episode_id = row.get("episode_id", "")
        if episode_id in DELETE_IDS:
            to_delete.append(row)
            print(f"\n❌ 削除: {episode_id}")
            print(f"   人物: {row.get('person_name')} ({row.get('age')}歳)")
            print(f"   本文: {row.get('episode_text', '')[:100]}...")
        else:
            remaining.append(row)

    final_count = len(remaining)
    deleted_count = len(to_delete)

    print(f"\n📊 削除件数: {deleted_count}件")
    print(f"📊 残存件数: {final_count}件")

    if dry_run:
        print("\n⚠️  ドライランモード：実際の削除は行いません")
        print("   本番実行するには --execute フラグを付けてください")
        return

    # バックアップ作成
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"MASTER_EPISODES_CURRENT_{timestamp}_before_phase8_delete.csv"

    shutil.copy2(MASTER_CSV, backup_path)
    print(f"\n💾 バックアップ作成: {backup_path}")

    # CSV書き込み
    with open(MASTER_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(remaining)

    print(f"\n✅ 削除完了: {MASTER_CSV}")
    print(f"   削除: {deleted_count}件")
    print(f"   残存: {final_count}件")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="問題Phase8エピソード削除")
    parser.add_argument("--execute", action="store_true", help="本番実行（デフォルトはドライラン）")
    args = parser.parse_args()

    delete_episodes(dry_run=not args.execute)
