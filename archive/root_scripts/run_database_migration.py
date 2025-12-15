#!/usr/bin/env python3
"""
データベースマイグレーション実行スクリプト

目的: 括弧表示システムに必要なカラムを追加

使用方法:
    python run_database_migration.py [database_path]
"""

import sqlite3
from src.database_utils import get_connection
import sys
import os
from datetime import datetime
from pathlib import Path


def run_migration(db_path: str, dry_run: bool = False) -> bool:
    """
    マイグレーション実行

    Args:
        db_path: データベースファイルパス
        dry_run: True の場合、SQLを表示するのみ（実行しない）

    Returns:
        成功した場合 True
    """
    migration_file = Path(__file__).parent / "migrations" / "add_bracket_display_columns.sql"

    if not migration_file.exists():
        print(f"❌ マイグレーションファイルが見つかりません: {migration_file}")
        return False

    # SQLファイルを読み込み
    with open(migration_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    # SQL文を抽出（コメント除外）
    lines = []
    for line in sql_content.split('\n'):
        line = line.strip()
        # コメント行をスキップ
        if line.startswith('--') or not line:
            continue
        lines.append(line)

    # セミコロンで分割してSQL文を抽出
    sql_text = ' '.join(lines)
    sql_statements = [
        stmt.strip()
        for stmt in sql_text.split(';')
        if stmt.strip()
    ]

    if dry_run:
        print("="*80)
        print("Dry Run モード - 実行予定のSQL:")
        print("="*80)
        for i, stmt in enumerate(sql_statements, 1):
            print(f"\n[SQL {i}]")
            print(stmt)
        print("\n" + "="*80)
        return True

    # バックアップ作成
    backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"📦 バックアップ作成中: {backup_path}")

    try:
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"✅ バックアップ完了")
    except Exception as e:
        print(f"❌ バックアップ失敗: {e}")
        return False

    # マイグレーション実行
    print(f"\n🚀 マイグレーション実行中...")

    try:
        conn = get_connection(db_path)
        cursor = conn.cursor()

        for i, stmt in enumerate(sql_statements, 1):
            print(f"  [{i}/{len(sql_statements)}] 実行中...")
            cursor.execute(stmt)

        conn.commit()
        conn.close()

        print(f"✅ マイグレーション成功！")
        print(f"\n追加されたカラム:")
        print(f"  - entity_type")
        print(f"  - group_affiliation")
        print(f"  - primary_work")
        print(f"  - show_group_in_bracket")
        print(f"  - group_status")
        print(f"  - fame_level")
        print(f"  - bracket_display_text")
        print(f"  - bracket_data_updated_at")

        return True

    except sqlite3.Error as e:
        print(f"❌ マイグレーション失敗: {e}")
        print(f"\n🔄 ロールバック中...")

        # バックアップから復元
        try:
            shutil.copy2(backup_path, db_path)
            print(f"✅ ロールバック完了（バックアップから復元）")
        except Exception as restore_error:
            print(f"❌ ロールバック失敗: {restore_error}")

        return False


def verify_migration(db_path: str) -> bool:
    """
    マイグレーション検証

    Args:
        db_path: データベースファイルパス

    Returns:
        検証成功した場合 True
    """
    print(f"\n🔍 マイグレーション検証中...")

    required_columns = [
        'entity_type',
        'group_affiliation',
        'primary_work',
        'show_group_in_bracket',
        'group_status',
        'fame_level',
        'bracket_display_text',
        'bracket_data_updated_at'
    ]

    try:
        conn = get_connection(db_path)
        cursor = conn.cursor()

        # personsテーブルのカラム一覧取得
        cursor.execute("PRAGMA table_info(persons)")
        columns = [row[1] for row in cursor.fetchall()]

        missing_columns = [col for col in required_columns if col not in columns]

        if missing_columns:
            print(f"❌ 検証失敗: 以下のカラムが見つかりません")
            for col in missing_columns:
                print(f"  - {col}")
            return False

        print(f"✅ 検証成功: すべてのカラムが正常に追加されています")

        # サンプルクエリ実行
        cursor.execute("""
            SELECT
                person_name_ja,
                entity_type,
                group_affiliation,
                show_group_in_bracket
            FROM persons
            LIMIT 5
        """)

        results = cursor.fetchall()
        print(f"\nサンプルデータ（5件）:")
        print(f"{'人物名':<20} {'種類':<20} {'グループ':<20} {'括弧表示':<10}")
        print("-" * 80)
        for row in results:
            print(f"{row[0]:<20} {row[1] or 'NULL':<20} {row[2] or 'NULL':<20} {row[3]:<10}")

        conn.close()
        return True

    except sqlite3.Error as e:
        print(f"❌ 検証失敗: {e}")
        return False


def main():
    """メイン処理"""

    print("="*80)
    print("括弧表示システム - データベースマイグレーション")
    print("="*80)

    # データベースパスの取得
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        # デフォルトパス
        db_path = "ultra_think_database_20241001_112630.db"

    if not os.path.exists(db_path):
        print(f"❌ データベースが見つかりません: {db_path}")
        print(f"\n使用方法:")
        print(f"  python run_database_migration.py [database_path]")
        sys.exit(1)

    print(f"\nデータベース: {db_path}")
    print(f"サイズ: {os.path.getsize(db_path) / 1024 / 1024:.2f} MB")

    # Dry Run オプション
    dry_run = '--dry-run' in sys.argv

    if dry_run:
        print(f"\n⚠️ Dry Run モード（実際には実行しません）")

    # 確認プロンプト
    if not dry_run:
        response = input(f"\nマイグレーションを実行しますか？ (yes/no): ")
        if response.lower() != 'yes':
            print("❌ マイグレーションをキャンセルしました")
            sys.exit(0)

    # マイグレーション実行
    success = run_migration(db_path, dry_run)

    if not success:
        print(f"\n❌ マイグレーション失敗")
        sys.exit(1)

    # 検証（Dry Runでない場合）
    if not dry_run:
        verify_success = verify_migration(db_path)

        if not verify_success:
            print(f"\n❌ 検証失敗")
            sys.exit(1)

    print(f"\n{'='*80}")
    print(f"✅ すべての処理が完了しました！")
    print(f"{'='*80}")


if __name__ == '__main__':
    main()
