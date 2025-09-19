#!/usr/bin/env python3
"""
データベース復元スクリプト
1個前のバージョンにロールバックする
"""

import os
import sys
import shutil
from datetime import datetime
from pathlib import Path

# srcディレクトリをパスに追加
sys.path.append('src')

from version_controller import VersionController

def main():
    """メイン処理"""
    print("=" * 60)
    print("🔄 データベース復元システム")
    print("=" * 60)
    
    # バージョンコントローラーを初期化
    vc = VersionController()
    
    # 現在のバージョンを取得
    current_version = vc.get_current_version()
    if not current_version:
        print("❌ 現在のバージョン情報が見つかりません")
        return False
    
    print(f"📊 現在のバージョン: {current_version['version_id']}")
    print(f"📅 作成日時: {current_version['created_at']}")
    
    # バージョン履歴を取得
    history = vc.version_history
    if len(history) < 2:
        print("❌ ロールバック可能なバージョンがありません")
        return False
    
    # 1個前のバージョンを特定
    previous_version = history[-2]  # 最新の1つ前
    print(f"\n📋 復元対象バージョン: {previous_version['version_id']}")
    print(f"📅 作成日時: {previous_version['created_at']}")
    
    # 確認
    print("\n⚠️  現在のデータベースを1個前のバージョンに復元します")
    print("   この操作により現在のデータは失われます")
    
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
    
    # ロールバック実行
    print(f"\n🔄 ロールバック実行中...")
    success = vc.rollback(previous_version['version_id'])
    
    if success:
        print(f"✅ ロールバック完了: {previous_version['version_id']}")
        
        # 復元されたデータを確認
        restored_data = vc.get_version(previous_version['version_id'])
        if restored_data:
            data, metadata = restored_data
            print(f"📊 復元されたデータサイズ: {len(data) if hasattr(data, '__len__') else 'N/A'}")
        
        # 復元されたデータを現在のディレクトリにコピー
        data_file = Path('versions/data') / f"{previous_version['version_id']}.csv"
        if data_file.exists():
            restored_csv = Path(f"ultra_think_RESTORED_{timestamp}.csv")
            shutil.copy2(data_file, restored_csv)
            print(f"📁 復元データを保存: {restored_csv}")
        
        return True
    else:
        print("❌ ロールバックに失敗しました")
        return False

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n🎉 データベース復元が完了しました")
        else:
            print("\n💥 データベース復元に失敗しました")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
