#!/usr/bin/env python3
"""
100%完工したデータをGoogle Sheetsに同期
"""

import pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from datetime import datetime
import json
import os

def main():
    print("=" * 80)
    print("📊 Google Sheets同期 - 100%完工データ")
    print("=" * 80)

    # 最新のCSVファイルを読み込み
    csv_file = 'ultra_think_100_PERCENT_COMPLETE_20250915_190404.csv'
    print(f"\n📂 データ読み込み: {csv_file}")
    df = pd.read_csv(csv_file)
    print(f"✅ {len(df):,}件のデータを読み込みました")

    # Google Sheets認証
    print("\n🔐 Google Sheets認証...")

    # サービスアカウントキーのパス
    key_path = '/Users/admin/Documents/key/ultra-think-435923-b36550c5b7cc.json'

    # 認証情報を設定
    creds = Credentials.from_service_account_file(
        key_path,
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )

    service = build('sheets', 'v4', credentials=creds)
    print("✅ 認証成功")

    # スプレッドシートID（既存のスプレッドシート）
    spreadsheet_id = '1HnV0x-U9HjbGur7VQpB66T0x5HMcPLHQCdMOTQ_HkwE'

    # スプレッドシート名を更新
    new_title = 'Ultra Think 100 PERCENT COMPLETE 20250915 190404'

    try:
        # スプレッドシート名を更新
        print(f"\n📝 スプレッドシート名を更新: {new_title}")
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={
                'requests': [{
                    'updateSpreadsheetProperties': {
                        'properties': {
                            'title': new_title
                        },
                        'fields': 'title'
                    }
                }]
            }
        ).execute()
        print("✅ スプレッドシート名更新完了")
    except Exception as e:
        print(f"⚠️ スプレッドシート名更新エラー: {e}")

    # データを準備（NaNを空文字列に置換）
    df = df.fillna('')

    # データをリスト形式に変換
    values = [df.columns.tolist()] + df.values.tolist()

    # シート名
    sheet_name = 'Sheet1'
    range_name = f'{sheet_name}!A1'

    # 既存のシートをクリア
    print("\n🧹 既存データをクリア...")
    try:
        service.spreadsheets().values().clear(
            spreadsheetId=spreadsheet_id,
            range=sheet_name
        ).execute()
        print("✅ クリア完了")
    except Exception as e:
        print(f"⚠️ クリアエラー: {e}")

    # データを書き込み
    print(f"\n📤 {len(df):,}件のデータをアップロード...")

    body = {
        'values': values,
        'majorDimension': 'ROWS'
    }

    result = service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=range_name,
        valueInputOption='RAW',
        body=body
    ).execute()

    updated_cells = result.get('updatedCells', 0)
    print(f"✅ {updated_cells:,}セルを更新しました")

    # フォーマット設定
    print("\n🎨 フォーマット設定...")

    # ヘッダー行を太字に
    requests = [
        {
            'repeatCell': {
                'range': {
                    'sheetId': 0,
                    'startRowIndex': 0,
                    'endRowIndex': 1
                },
                'cell': {
                    'userEnteredFormat': {
                        'textFormat': {
                            'bold': True
                        }
                    }
                },
                'fields': 'userEnteredFormat.textFormat.bold'
            }
        },
        # 列幅の自動調整
        {
            'autoResizeDimensions': {
                'dimensions': {
                    'sheetId': 0,
                    'dimension': 'COLUMNS',
                    'startIndex': 0,
                    'endIndex': len(df.columns)
                }
            }
        }
    ]

    try:
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={'requests': requests}
        ).execute()
        print("✅ フォーマット設定完了")
    except Exception as e:
        print(f"⚠️ フォーマット設定エラー: {e}")

    # 成功レポート
    print("\n" + "=" * 80)
    print("🎉 同期完了！")
    print("=" * 80)

    print(f"\n📊 同期結果:")
    print(f"  総レコード数: {len(df):,}件")
    print(f"  総カラム数: {len(df.columns)}列")
    print(f"  更新セル数: {updated_cells:,}セル")

    # Brave Search統計
    brave_count = df[df['search_source'].str.contains('brave', na=False)]
    print(f"\n🔍 Brave Search統計:")
    print(f"  実データ: {len(brave_count):,}件 ({len(brave_count)/len(df)*100:.1f}%)")

    # スプレッドシートURL
    sheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
    print(f"\n📎 スプレッドシートURL:")
    print(f"  {sheet_url}")

    # 同期ログを保存
    sync_log = {
        'sync_date': datetime.now().isoformat(),
        'csv_file': csv_file,
        'spreadsheet_id': spreadsheet_id,
        'spreadsheet_title': new_title,
        'total_records': len(df),
        'total_columns': len(df.columns),
        'updated_cells': updated_cells,
        'brave_search_count': len(brave_count),
        'completion_rate': 100.0,
        'sheet_url': sheet_url
    }

    with open('google_sheets_sync_log.json', 'w', encoding='utf-8') as f:
        json.dump(sync_log, f, indent=2, ensure_ascii=False)

    print(f"\n📁 同期ログ: google_sheets_sync_log.json")

    # ブラウザで開く
    print(f"\n🌐 ブラウザでスプレッドシートを開いています...")
    import webbrowser
    webbrowser.open(sheet_url)

if __name__ == "__main__":
    main()