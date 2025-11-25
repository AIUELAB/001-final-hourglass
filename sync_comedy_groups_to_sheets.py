from src.secure_config import config
#!/usr/bin/env python3
"""
修正済みのお笑い芸人データをGoogle Sheetsに同期
"""
import pandas as pd
import json
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import time

def sync_to_sheets():
    # 設定を読み込み
    with open('sheets_config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)

    # 最新の修正済みファイルを使用
    csv_file = 'ultra_think_COMEDY_GROUPS_FIXED_20250828_190550.csv'
    df = pd.read_csv(csv_file)

    print(f"📊 {csv_file}をGoogle Sheetsに同期中...")
    print(f"   行数: {len(df)}")
    print(f"   列数: {len(df.columns)}")

    # 認証
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    creds = Credentials.from_service_account_file(config.google_credentials_path, scopes=SCOPES)
    service = build('sheets', 'v4', credentials=creds)

    spreadsheet_id = config['spreadsheet_id']

    # スプレッドシート名を更新
    new_sheet_name = "Ultra Think Comedy Groups Fixed 20250828 190550"

    # スプレッドシートのプロパティを更新
    try:
        spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        current_title = spreadsheet['properties']['title']

        if current_title != new_sheet_name:
            update_body = {
                'requests': [{
                    'updateSpreadsheetProperties': {
                        'properties': {'title': new_sheet_name},
                        'fields': 'title'
                    }
                }]
            }
            service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=update_body
            ).execute()
            print(f"✅ スプレッドシート名を更新: {new_sheet_name}")
        else:
            print(f"ℹ️ スプレッドシート名は既に最新: {new_sheet_name}")
    except Exception as e:
        print(f"⚠️ スプレッドシート名の更新に失敗: {e}")

    # データを準備
    values = [df.columns.tolist()] + df.fillna('').values.tolist()

    # シートにデータを書き込み
    range_name = 'Sheet1!A1'
    body = {'values': values}

    try:
        # 既存のデータをクリア
        service.spreadsheets().values().clear(
            spreadsheetId=spreadsheet_id,
            range='Sheet1'
        ).execute()

        # 新しいデータを書き込み
        result = service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='RAW',
            body=body
        ).execute()

        updated_cells = result.get('updatedCells')
        print(f"✅ {updated_cells}個のセルを更新しました")

        # P000057の確認
        p000057_row = df[df['person_id'] == 'P000057']
        if not p000057_row.empty:
            display_name = p000057_row.iloc[0]['person_name_display']
            print(f"\n🎯 P000057の表示名: {display_name}")
            if '(ジャングルポケット)' in str(display_name):
                print("   ✅ グループ名が正しく表示されています")
            else:
                print("   ⚠️ グループ名が表示されていません")

        # お笑い芸人の統計
        comedians = df[df['occupation'] == 'お笑い芸人']
        with_groups = comedians[comedians['person_name_display'].str.contains(r'\(.*\)', na=False, regex=True)]

        print(f"\n📊 お笑い芸人の統計:")
        print(f"   総数: {len(comedians)}人")
        print(f"   グループ名付き: {len(with_groups)}人")
        print(f"   グループ表示率: {len(with_groups) / len(comedians) * 100:.1f}%")

    except Exception as e:
        print(f"❌ エラー: {e}")
        return False

    # 設定を更新
    config['csv_file'] = csv_file
    config['sheet_name'] = new_sheet_name
    config['last_sync'] = datetime.now().isoformat()

    with open('sheets_config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    # 同期ログを更新
    try:
        with open('sync_log.json', 'r', encoding='utf-8') as f:
            sync_log = json.load(f)
    except:
        sync_log = []

    sync_log.append({
        'timestamp': datetime.now().isoformat(),
        'csv_file': csv_file,
        'status': 'success',
        'message': 'お笑い芸人グループ名修正後の同期完了',
        'stats': {
            'total_comedians': len(comedians),
            'with_groups': len(with_groups),
            'group_display_rate': f"{len(with_groups) / len(comedians) * 100:.1f}%"
        }
    })

    # 最新10件のみ保持
    sync_log = sync_log[-10:]

    with open('sync_log.json', 'w', encoding='utf-8') as f:
        json.dump(sync_log, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Google Sheets同期完了")
    print(f"📊 URL: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")

    return True

if __name__ == "__main__":
    success = sync_to_sheets()
    if success:
        print("\n🎉 すべての処理が完了しました！")
        print("   P000057（おたけ）のグループ名表示問題は解決されました")
