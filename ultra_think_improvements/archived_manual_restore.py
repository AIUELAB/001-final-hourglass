#!/usr/bin/env python3
"""
手動データベース復元スクリプト
バージョン管理システムを使わずに直接ファイルを復元
"""

import os
import shutil
from datetime import datetime
from pathlib import Path

def main():
    """メイン処理"""
    print("=" * 60)
    print("🔄 手動データベース復元システム")
    print("=" * 60)
    
    # 現在のバージョン履歴を確認
    history_file = Path('versions/version_history.json')
    if not history_file.exists():
        print("❌ バージョン履歴ファイルが見つかりません")
        return False
    
    # バージョン履歴を読み込み
    import json
    with open(history_file, 'r', encoding='utf-8') as f:
        history = json.load(f)
    
    if len(history) < 2:
        print("❌ ロールバック可能なバージョンがありません")
        return False
    
    # 現在のバージョンと1個前のバージョンを特定
    current_version = history[-1]
    previous_version = history[-2]
    
    print(f"📊 現在のバージョン: {current_version['version_id']}")
    print(f"📅 作成日時: {current_version['created_at']}")
    print(f"\n📋 復元対象バージョン: {previous_version['version_id']}")
    print(f"📅 作成日時: {previous_version['created_at']}")
    
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
    
    # 復元対象のデータファイルを確認
    restore_data_file = Path('versions/data') / f"{previous_version['version_id']}.csv"
    if not restore_data_file.exists():
        print(f"❌ 復元対象のデータファイルが見つかりません: {restore_data_file}")
        return False
    
    print(f"\n📁 復元対象ファイル: {restore_data_file}")
    
    # 復元実行
    print(f"\n🔄 復元実行中...")
    
    # 復元されたデータを現在のディレクトリにコピー
    restored_csv = Path(f"ultra_think_RESTORED_{timestamp}.csv")
    shutil.copy2(restore_data_file, restored_csv)
    print(f"✅ 復元データを保存: {restored_csv}")
    
    # 現在のバージョン情報を更新
    current_version_file = Path('versions/current_version.json')
    if current_version_file.exists():
        # バックアップを作成
        current_backup = Path(f'versions/current_version_backup_{timestamp}.json')
        shutil.copy2(current_version_file, current_backup)
        print(f"✅ 現在のバージョン情報をバックアップ: {current_backup}")
        
        # 前のバージョンに更新
        with open(current_version_file, 'w', encoding='utf-8') as f:
            json.dump(previous_version, f, ensure_ascii=False, indent=2)
        print(f"✅ 現在のバージョンを更新: {previous_version['version_id']}")
    
    # 復元されたデータの情報を表示
    try:
        import pandas as pd
        df = pd.read_csv(restored_csv)
        print(f"📊 復元されたデータ件数: {len(df)}件")
        print(f"📊 復元されたデータ列数: {len(df.columns)}列")
    except ImportError:
        print("📊 pandasが利用できないため、データ詳細は表示できません")
    
    print(f"\n🎉 データベース復元が完了しました")
    print(f"📁 復元されたファイル: {restored_csv}")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            print("\n💥 データベース復元に失敗しました")
            exit(1)
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
