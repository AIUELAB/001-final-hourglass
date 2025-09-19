#!/usr/bin/env python3
"""
Google Sheetsファイル名同期検証スクリプト
PDCAガーディアンと連携して自動検証を行う
"""

import json
import os
import sys
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

def check_filename_sync():
    """ファイル名同期をチェック"""

    # 設定ファイルを読み込み
    with open('sheets_config.json', 'r') as f:
        config = json.load(f)

    csv_file = config.get('csv_file', '')
    sheet_name = config.get('sheet_name', '')
    spreadsheet_id = config.get('spreadsheet_id', '')

    # 期待されるスプレッドシート名を計算
    base_name = csv_file.replace('.csv', '')
    expected_name = base_name.replace('_', ' ').title()
    expected_name = expected_name.replace('Ultra Think', 'Ultra Think')

    print(f"📁 CSVファイル: {csv_file}")
    print(f"📝 現在のシート名: {sheet_name}")
    print(f"✅ 期待されるシート名: {expected_name}")

    # Google Sheets APIで実際の名前を確認
    try:
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
        creds_path = 'key/credentials.json'

        if os.path.exists(creds_path):
            creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
            service = build('sheets', 'v4', credentials=creds)

            # スプレッドシートの情報を取得
            spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            actual_name = spreadsheet.get('properties', {}).get('title', '')

            print(f"🌐 Google Sheets実際の名前: {actual_name}")

            # 検証
            if actual_name == expected_name:
                print("✅ ファイル名は正しく同期されています")
                return True
            else:
                print("❌ ファイル名が同期されていません！")
                print(f"   期待: {expected_name}")
                print(f"   実際: {actual_name}")
                return False
    except Exception as e:
        print(f"⚠️ API確認中にエラー: {e}")
        # 設定ファイルベースでチェック
        if sheet_name == expected_name:
            print("✅ 設定ファイルでは同期されています")
            return True
        else:
            print("❌ 設定ファイルでも同期されていません")
            return False

if __name__ == "__main__":
    result = check_filename_sync()
    sys.exit(0 if result else 1)
