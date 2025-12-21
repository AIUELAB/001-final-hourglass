#!/usr/bin/env python3
"""
スキーマ変更スクリプト - name_raw, title, affiliation カラム追加

使用方法:
    python scripts/add_normalization_columns.py --dry-run  # 確認のみ
    python scripts/add_normalization_columns.py --execute  # 実行
"""

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent
CSV_PATH = PROJECT_ROOT / "preserved" / "MASTER_EPISODES_CURRENT.csv"
DB_PATH = PROJECT_ROOT / "episode_database.db"


def add_csv_columns(dry_run: bool = True) -> dict:
    """CSVに3カラムを追加"""
    print(f"\n📂 CSV読み込み: {CSV_PATH}")
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")

    original_columns = list(df.columns)
    print(f"  現在のカラム数: {len(original_columns)}")

    # 追加するカラム
    new_columns = ["name_raw", "title", "affiliation"]
    added = []
    skipped = []

    for col in new_columns:
        if col in df.columns:
            skipped.append(col)
            print(f"  ⚠️ {col}: 既に存在（スキップ）")
        else:
            added.append(col)
            df[col] = ""  # 空文字で初期化
            print(f"  ✅ {col}: 追加")

    result = {
        "csv_path": str(CSV_PATH),
        "original_columns": len(original_columns),
        "new_columns": len(df.columns),
        "added": added,
        "skipped": skipped,
    }

    if not dry_run and added:
        # UTF-8 BOM付きで保存
        df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
        print(f"  💾 保存完了: {len(df)}件")

    return result


def add_sqlite_columns(dry_run: bool = True) -> dict:
    """SQLiteに3カラムを追加"""
    print(f"\n📂 SQLite確認: {DB_PATH}")

    if not DB_PATH.exists():
        print("  ⚠️ SQLite DBが見つかりません（スキップ）")
        return {"status": "not_found"}

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 既存のカラムを確認
    cursor.execute("PRAGMA table_info(persons)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    print(f"  現在のカラム数: {len(existing_columns)}")

    # 追加するカラム
    new_columns = [
        ("name_raw", "TEXT"),
        ("title", "TEXT"),
        ("affiliation", "TEXT"),
    ]

    added = []
    skipped = []

    for col_name, col_type in new_columns:
        if col_name in existing_columns:
            skipped.append(col_name)
            print(f"  ⚠️ {col_name}: 既に存在（スキップ）")
        else:
            added.append(col_name)
            if not dry_run:
                cursor.execute(f"ALTER TABLE persons ADD COLUMN {col_name} {col_type}")
                print(f"  ✅ {col_name}: 追加")
            else:
                print(f"  🔍 {col_name}: 追加予定（dry-run）")

    if not dry_run:
        conn.commit()
        print("  💾 コミット完了")

    conn.close()

    return {
        "db_path": str(DB_PATH),
        "added": added,
        "skipped": skipped,
    }


def main():
    parser = argparse.ArgumentParser(description="スキーマ変更: name_raw, title, affiliation追加")
    parser.add_argument("--dry-run", action="store_true", help="実行せずに確認のみ")
    parser.add_argument("--execute", action="store_true", help="実行")
    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        print("⚠️ --dry-run または --execute を指定してください")
        return

    dry_run = not args.execute

    print("=" * 60)
    print(f"🔧 スキーマ変更 {'(dry-run)' if dry_run else '(実行)'}")
    print("=" * 60)
    print(f"  実行日時: {datetime.now().isoformat()}")

    # CSV変更
    csv_result = add_csv_columns(dry_run)

    # SQLite変更
    sqlite_result = add_sqlite_columns(dry_run)

    # 結果サマリー
    print("\n" + "=" * 60)
    print("📊 結果サマリー")
    print("=" * 60)
    print(f"  CSV追加: {csv_result.get('added', [])}")
    print(f"  CSVスキップ: {csv_result.get('skipped', [])}")
    print(f"  SQLite追加: {sqlite_result.get('added', [])}")
    print(f"  SQLiteスキップ: {sqlite_result.get('skipped', [])}")

    if dry_run:
        print("\n💡 実行するには --execute を指定してください")


if __name__ == "__main__":
    main()
