"""
Phase 28: マスターCSVカラム名を日本語→英語に変換

Usage:
    python scripts/migration/migrate_csv_columns_to_english.py [--dry-run]
"""

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.sage.constants import LEGACY_COLUMN_MAP


def migrate(dry_run: bool = True) -> dict:
    """
    マスターCSVのカラム名を日本語→英語に変換

    Args:
        dry_run: True の場合は実際に書き込まない

    Returns:
        dict: 実行結果
    """
    csv_path = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")

    if not csv_path.exists():
        return {"success": False, "error": "Master CSV not found"}

    # 読み込み
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    original_columns = list(df.columns)

    # 変換対象カラムの確認
    columns_to_rename = {}
    for jp_name, en_name in LEGACY_COLUMN_MAP.items():
        if jp_name in df.columns:
            columns_to_rename[jp_name] = en_name

    if not columns_to_rename:
        return {
            "success": True,
            "message": "No Japanese columns found to rename",
            "renamed_count": 0,
        }

    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "columns_to_rename": columns_to_rename,
            "renamed_count": len(columns_to_rename),
        }

    # バックアップ作成
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = csv_path.parent / f"MASTER_EPISODES_pre_english_{timestamp}.csv"
    df.to_csv(backup_path, index=False, encoding="utf-8-sig")

    # カラム名変換
    df = df.rename(columns=columns_to_rename)

    # 保存
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    return {
        "success": True,
        "dry_run": False,
        "columns_renamed": columns_to_rename,
        "renamed_count": len(columns_to_rename),
        "backup_path": str(backup_path),
        "total_rows": len(df),
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Migrate CSV columns to English")
    parser.add_argument("--dry-run", action="store_true", help="Preview without changes")
    args = parser.parse_args()

    result = migrate(dry_run=args.dry_run)

    print("\n=== Phase 28: CSV Column Migration ===")
    print(f"Success: {result['success']}")

    if result.get("dry_run"):
        print("\n[DRY RUN] Columns to rename:")
        for jp, en in result.get("columns_to_rename", {}).items():
            print(f"  {jp} → {en}")
        print(f"\nTotal: {result['renamed_count']} columns")
        print("\nRun without --dry-run to apply changes.")
    elif result.get("renamed_count", 0) > 0:
        print(f"\nRenamed {result['renamed_count']} columns:")
        for jp, en in result.get("columns_renamed", {}).items():
            print(f"  {jp} → {en}")
        print(f"\nBackup: {result.get('backup_path')}")
        print(f"Total rows: {result.get('total_rows')}")
    else:
        print(f"\n{result.get('message', result.get('error', 'Unknown'))}")


if __name__ == "__main__":
    main()
