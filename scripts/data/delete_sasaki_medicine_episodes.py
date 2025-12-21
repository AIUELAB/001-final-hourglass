#!/usr/bin/env python3
"""
佐々木隆興（医学・健康カテゴリー）エピソード削除スクリプト

削除対象:
- generated/medicine_health_batch3_episodes.csv（40歳）
- generated/medicine_health_episodes.csv（70歳）
- templates/medicine_health_batch3.csv（テンプレート）

保持対象:
- preserved/data/MASTER_EPISODES_CURRENT.csv（50歳、科学・技術）→ 正常エピソード
"""

import argparse
import csv
import shutil
from datetime import datetime
from pathlib import Path

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent
BACKUP_DIR = PROJECT_ROOT / "preserved" / "backup"

# 削除対象ファイル
TARGET_FILES = [
    PROJECT_ROOT / "generated" / "medicine_health_batch3_episodes.csv",
    PROJECT_ROOT / "generated" / "medicine_health_episodes.csv",
    PROJECT_ROOT / "templates" / "medicine_health_batch3.csv",
]


def delete_sasaki_episodes(dry_run: bool = True):
    """
    佐々木隆興（医学・健康）エピソードを削除

    Args:
        dry_run: True=ドライラン（確認のみ）, False=本番実行
    """
    print("=" * 70)
    print("🗑️  佐々木隆興（医学・健康）エピソード削除")
    print("=" * 70)
    print(f"モード: {'ドライラン（確認のみ）' if dry_run else '本番実行'}")
    print()

    total_deleted = 0
    files_processed = []

    for target_file in TARGET_FILES:
        if not target_file.exists():
            print(f"⚠️  スキップ: {target_file.name}（ファイルが存在しません）")
            continue

        print(f"\n📁 処理中: {target_file.name}")

        # CSV読み込み
        try:
            with open(target_file, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames
                rows = list(reader)
        except Exception as e:
            print(f"❌ エラー: CSV読み込み失敗 - {e}")
            continue

        initial_count = len(rows)
        print(f"   初期件数: {initial_count}件")

        # 佐々木隆興を除外
        remaining = [row for row in rows if row.get("person_name") != "佐々木隆興"]
        deleted_count = initial_count - len(remaining)

        if deleted_count > 0:
            print(f"   ❌ 削除対象: {deleted_count}件（佐々木隆興）")
            total_deleted += deleted_count
            files_processed.append(target_file.name)
        else:
            print("   ℹ️  対象なし（佐々木隆興は含まれていません）")
            continue

        if not dry_run:
            # バックアップ作成
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = BACKUP_DIR / f"{target_file.stem}_{timestamp}_before_sasaki_delete.csv"

            try:
                shutil.copy2(target_file, backup_path)
                print(f"   💾 バックアップ: {backup_path.name}")
            except Exception as e:
                print(f"❌ エラー: バックアップ作成失敗 - {e}")
                continue

            # CSV書き込み
            try:
                with open(target_file, "w", encoding="utf-8-sig", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(remaining)

                print(f"   ✅ 削除完了: {len(remaining)}件残存")
            except Exception as e:
                print(f"❌ エラー: CSV書き込み失敗 - {e}")
                # バックアップから復元を試みる
                try:
                    shutil.copy2(backup_path, target_file)
                    print("   ⚠️  バックアップから復元しました")
                except Exception as restore_error:
                    print(f"❌ 致命的エラー: 復元失敗 - {restore_error}")

    print("\n" + "=" * 70)
    print("📊 処理結果サマリー")
    print("=" * 70)
    print(f"合計削除件数: {total_deleted}件")
    print(f"処理ファイル数: {len(files_processed)}件")

    if files_processed:
        print("\n処理したファイル:")
        for filename in files_processed:
            print(f"  - {filename}")

    if dry_run:
        print("\n⚠️  ドライランモード：実際の削除は行われていません")
        print("   本番実行するには --execute フラグを付けてください：")
        print("   python scripts/delete_sasaki_medicine_episodes.py --execute")
    else:
        print("\n✅ 削除処理完了")
        print(f"   バックアップ保存先: {BACKUP_DIR}")

    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="佐々木隆興（医学・健康カテゴリー）エピソード削除スクリプト",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # ドライラン（確認のみ）
  python scripts/delete_sasaki_medicine_episodes.py

  # 本番実行
  python scripts/delete_sasaki_medicine_episodes.py --execute
        """,
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="実際に削除を実行（デフォルト: ドライラン）",
    )

    args = parser.parse_args()

    delete_sasaki_episodes(dry_run=not args.execute)


if __name__ == "__main__":
    main()
