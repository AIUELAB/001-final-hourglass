from src.secure_config import config
#!/usr/bin/env python3
"""
クイックアップロード - スプレッドシートIDを直接指定
"""

import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ========================================
# ここにスプレッドシートIDを入力してください
# ========================================
SPREADSHEET_ID = "1G0ec3d5DHGiahLetsqey9W23HGFOn2tkEacsFd5ZSps"  # ← ここに貼り付け

def quick_upload():
    """素早くアップロード"""
    
    if not SPREADSHEET_ID:
        print("❌ エラー: SPREADSHEET_IDを設定してください")
        print("\n使い方:")
        print("1. Google Sheetsで新規スプレッドシートを作成")
        print("2. URLからIDをコピー")
        print("   例: https://docs.google.com/spreadsheets/d/【ここがID】/edit")
        print("3. このファイルの SPREADSHEET_ID = \"\" の部分にIDを貼り付け")
        print("4. 再度実行")
        return
    
    try:
        print("🚀 アップロード開始...")
        
        # 認証
        credentials = Credentials.from_service_account_file(
            config.google_credentials_path,
            scopes=[
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive.file'
            ]
        )
        client = gspread.authorize(credentials)
        
        # CSV読み込み
        df = pd.read_csv("ultra_think_NO_FAKE_RESEARCHERS_20250827_143418.csv", encoding='utf-8')
        print(f"📊 データ: {len(df)}行 x {len(df.columns)}列")
        
        # データ準備
        df = df.fillna('').astype(str)
        data = [df.columns.tolist()] + df.values.tolist()
        
        # スプレッドシートを開く
        sheet = client.open_by_key(SPREADSHEET_ID)
        worksheet = sheet.sheet1
        
        # アップロード
        print("📤 アップロード中...")
        worksheet.clear()
        worksheet.update(data, range_name='A1')
        worksheet.freeze(rows=1)
        
        print("✅ 完了！")
        print(f"\n🔗 URL: {sheet.url}")
        
        # 保存
        with open("sheet_info.txt", "w") as f:
            f.write(f"URL: {sheet.url}\n")
            f.write(f"ID: {SPREADSHEET_ID}\n")
        
    except Exception as e:
        print(f"❌ エラー: {e}")

if __name__ == "__main__":
    quick_upload()