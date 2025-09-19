#!/usr/bin/env python3
"""
Ultra Think データベース同期実行スクリプト
"""

import sys
import os
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from google_sheets_sync import GoogleSheetsSync

def main():
    """メイン実行関数"""
    print("🚀 Ultra Think データベース同期開始...")
    
    try:
        # GoogleSheetsSync インスタンスを作成
        sync = GoogleSheetsSync()
        
        # 認証情報をセットアップ
        sync.setup_credentials()
        
        print("✅ Google Sheets API接続成功")
        
        # スプレッドシートを作成または取得
        if not sync.create_or_get_spreadsheet():
            print("❌ スプレッドシートの作成/取得に失敗しました")
            return False
        
        # CSVファイルをGoogle Sheetsにアップロード
        result = sync.upload_csv_to_sheets()
        
        if result:
            print("✅ 同期完了！")
            return True
        else:
            print("❌ 同期に失敗しました")
            return False
            
    except Exception as e:
        print(f"❌ エラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)