#!/usr/bin/env python3
"""
Google Spreadsheetsのファイル名を同期するスクリプト
"""

import os
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

def sync_spreadsheet_name():
    """スプレッドシートのファイル名を同期"""

    # 設定ファイルを読み込み
    with open('sheets_config.json', 'r') as f:
        config = json.load(f)

    spreadsheet_id = config['spreadsheet_id']
    csv_file = config['csv_file']

    # CSVファイル名からスプレッドシート名を生成
    # ultra_think_with_affiliation_20250915_124801.csv
    # → Ultra Think With Affiliation 20250915 124801
    base_name = csv_file.replace('.csv', '')
    sheet_name = base_name.replace('_', ' ').title()
    sheet_name = sheet_name.replace('Ultra Think', 'Ultra Think')  # Ultra Thinkは固定

    print(f"📁 CSVファイル: {csv_file}")
    print(f"📝 新しいスプレッドシート名: {sheet_name}")

    # Google Sheets API認証
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
              'https://www.googleapis.com/auth/drive']

    creds_path = 'key/credentials.json'
    if not os.path.exists(creds_path):
        print("❌ 認証ファイルが見つかりません")
        return False

    creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)

    # Drive APIを使用してファイル名を変更
    drive_service = build('drive', 'v3', credentials=creds)

    try:
        # ファイル名を更新
        file_metadata = {'name': sheet_name}
        updated_file = drive_service.files().update(
            fileId=spreadsheet_id,
            body=file_metadata
        ).execute()

        print(f"✅ スプレッドシート名を更新しました: {updated_file.get('name')}")

        # 設定ファイルも更新
        config['sheet_name'] = sheet_name
        with open('sheets_config.json', 'w') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        print(f"✅ sheets_config.jsonも更新しました")

        return True

    except Exception as e:
        print(f"❌ エラー: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("Google Spreadsheetsファイル名同期")
    print("=" * 50)

    if sync_spreadsheet_name():
        print("\n✅ 同期完了！")
        print(f"URL: https://docs.google.com/spreadsheets/d/1G0ec3d5DHGiahLetsqey9W23HGFOn2tkEacsFd5ZSps")
    else:
        print("\n❌ 同期失敗")
