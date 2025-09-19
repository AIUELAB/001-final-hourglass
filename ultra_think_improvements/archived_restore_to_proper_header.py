#!/usr/bin/env python3
"""
適切なヘッダー構造復元スクリプト
person_idが1行目に来る適切なヘッダー構造のデータファイルに復元する
"""

import os
import shutil
from datetime import datetime
from pathlib import Path

def main():
    """メイン処理"""
    print("=" * 60)
    print("🔄 適切なヘッダー構造復元システム")
    print("=" * 60)

    # 適切なヘッダー構造のファイル
    source_file = "ultra_think_FICTIONAL_REMOVED_20250831_073607.csv"

    if not Path(source_file).exists():
        print(f"❌ ソースファイル {source_file} が見つかりません")
        return False

    print(f"📊 現在のバージョン: auto_sync_20250831_045606_20250831_045606")
    print(f"📋 復元対象ファイル: {source_file}")

    # ヘッダー構造を確認
    with open(source_file, 'r', encoding='utf-8') as f:
        header = f.readline().strip()

    print(f"📋 ヘッダー構造: {header[:50]}...")

    # 現在のデータベースファイルをバックアップ
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = Path('emergency_backups')
    backup_dir.mkdir(exist_ok=True)

    # 最新のultra_think_*.csvファイルをバックアップ
    csv_files = list(Path('.').glob('ultra_think_*.csv'))
    if csv_files:
        latest_csv = max(csv_files, key=lambda x: x.stat().st_mtime)
        backup_file = backup_dir / f'emergency_backup_{timestamp}.csv'
        shutil.copy2(latest_csv, backup_file)
        print(f"✅ 現在のデータベースをバックアップ: {backup_file}")

    print(f"\n📁 復元対象ファイル: {source_file}")

    # 復元実行
    print(f"\n🔄 復元実行中...")

    # 復元されたデータを現在のディレクトリにコピー
    restored_csv = Path(f"ultra_think_PROPER_HEADER_RESTORED_{timestamp}.csv")
    shutil.copy2(source_file, restored_csv)
    print(f"✅ 復元データを保存: {restored_csv}")

    # 現在のバージョン情報を更新（カスタムバージョンとして）
    current_version_file = Path('versions/current_version.json')
    if current_version_file.exists():
        # バックアップを作成
        current_backup = Path(f'versions/current_version_backup_{timestamp}.json')
        shutil.copy2(current_version_file, current_backup)
        print(f"✅ 現在のバージョン情報をバックアップ: {current_backup}")

        # カスタムバージョン情報を作成
        custom_version_info = {
            "version_id": f"proper_header_restore_{timestamp}",
            "timestamp": timestamp,
            "created_at": datetime.now().isoformat(),
            "hash": "custom_restore",
            "metadata": {
                "restore_type": "proper_header_structure",
                "source_file": source_file,
                "header_structure": "episode_id,person_id,episode_hash,..."
            },
            "size": 52902  # ヘッダー除く
        }

        # カスタムバージョンに更新
        with open(current_version_file, 'w', encoding='utf-8') as f:
            import json
            json.dump(custom_version_info, f, ensure_ascii=False, indent=2)
        print(f"✅ 現在のバージョンを更新: proper_header_restore_{timestamp}")

    # 復元されたデータの情報を表示
    try:
        import pandas as pd
        df = pd.read_csv(restored_csv)
        print(f"📊 復元されたデータ件数: {len(df)}件")
        print(f"📊 復元されたデータ列数: {len(df.columns)}列")
        print(f"📊 最初の列: {list(df.columns)[:5]}")
    except ImportError:
        print("📊 pandasが利用できないため、データ詳細は表示できません")
        # 手動で行数を確認
        with open(restored_csv, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        print(f"📊 復元されたデータ件数: {len(lines)-1}件（ヘッダー除く）")

    print(f"\n🎉 適切なヘッダー構造への復元が完了しました")
    print(f"📁 復元されたファイル: {restored_csv}")

    return True

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            print("\n💥 適切なヘッダー構造への復元に失敗しました")
            exit(1)
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
