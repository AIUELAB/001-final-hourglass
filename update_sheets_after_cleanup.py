from src.secure_config import config
#!/usr/bin/env python3
"""
プレースホルダー削除後のGoogle Sheets更新
"""

import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime


def update_google_sheets_with_clean_data():
    """クリーンなデータでGoogle Sheetsを更新"""
    
    # 認証設定
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    
    creds = Credentials.from_service_account_file(
        config.google_credentials_path,
        scopes=scope
    )
    
    client = gspread.authorize(creds)
    
    # スプレッドシートを開く
    spreadsheet_id = '1G0ec3d5DHGiahLetsqey9W23HGFOn2tkEacsFd5ZSps'
    sheet = client.open_by_key(spreadsheet_id).sheet1
    
    # クリーンなデータを読み込み
    csv_file = "ultra_think_CLEANED_20250827_223821.csv"
    print(f"読み込み中: {csv_file}")
    df = pd.read_csv(csv_file)
    
    # NaNを空文字列に置換
    df = df.fillna('')
    
    print(f"データ準備完了: {len(df)}行 x {len(df.columns)}列")
    print(f"（プレースホルダー330件削除済み）")
    
    # 既存のデータをクリア
    print("\nGoogle Sheetsの既存データをクリア中...")
    sheet.clear()
    
    # ヘッダーと全データを一括更新
    print("新しいデータをアップロード中...")
    data = [df.columns.tolist()] + df.values.tolist()
    
    # バッチ更新（より効率的）
    sheet.update('A1', data)
    
    print(f"\n✅ Google Sheets更新完了!")
    print(f"   更新行数: {len(df)}行（削除前: 5888行 → 削除後: 5558行）")
    print(f"   削除されたプレースホルダー: 330件")
    print(f"   スプレッドシートURL: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
    
    # 更新統計を返す
    return {
        'total_rows': len(df),
        'deleted_placeholders': 330,
        'timestamp': datetime.now().isoformat()
    }


if __name__ == "__main__":
    print("=== Google Sheets更新（プレースホルダー削除後） ===\n")
    
    try:
        stats = update_google_sheets_with_clean_data()
        
        print("\n更新統計:")
        print(f"  総行数: {stats['total_rows']}")
        print(f"  削除数: {stats['deleted_placeholders']}")
        print(f"  更新時刻: {stats['timestamp']}")
        
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()