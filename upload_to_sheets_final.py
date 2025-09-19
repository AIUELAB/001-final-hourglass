#!/usr/bin/env python3
"""
最終データベースをGoogle Sheetsにアップロードするスクリプト
"""

import os
import csv
import json
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Google Sheets API設定
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = 'google-credentials.json'

def load_credentials():
    """認証情報をロード"""
    if os.path.exists(SERVICE_ACCOUNT_FILE):
        return Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    else:
        # 環境変数から取得
        creds_json = os.environ.get('GOOGLE_CREDENTIALS_JSON')
        if creds_json:
            creds_info = json.loads(creds_json)
            return Credentials.from_service_account_info(creds_info, scopes=SCOPES)
        else:
            raise FileNotFoundError("Google認証情報が見つかりません")

def create_new_spreadsheet(service, title):
    """新しいスプレッドシートを作成"""
    spreadsheet = {
        'properties': {
            'title': title,
            'locale': 'ja_JP'
        },
        'sheets': [{
            'properties': {
                'title': 'Database',
                'gridProperties': {
                    'frozenRowCount': 1
                }
            }
        }]
    }
    
    try:
        spreadsheet = service.spreadsheets().create(body=spreadsheet).execute()
        return spreadsheet['spreadsheetId']
    except HttpError as e:
        print(f"エラー: {e}")
        return None

def format_spreadsheet(service, spreadsheet_id):
    """スプレッドシートのフォーマット設定"""
    requests = [
        # ヘッダー行の書式設定
        {
            'repeatCell': {
                'range': {
                    'sheetId': 0,
                    'startRowIndex': 0,
                    'endRowIndex': 1
                },
                'cell': {
                    'userEnteredFormat': {
                        'backgroundColor': {'red': 0.2, 'green': 0.3, 'blue': 0.6},
                        'textFormat': {
                            'foregroundColor': {'red': 1, 'green': 1, 'blue': 1},
                            'bold': True
                        },
                        'horizontalAlignment': 'CENTER'
                    }
                },
                'fields': 'userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)'
            }
        },
        # 列幅の自動調整
        {
            'autoResizeDimensions': {
                'dimensions': {
                    'sheetId': 0,
                    'dimension': 'COLUMNS',
                    'startIndex': 0,
                    'endIndex': 10
                }
            }
        },
        # フィルターの追加
        {
            'setBasicFilter': {
                'filter': {
                    'range': {
                        'sheetId': 0,
                        'startRowIndex': 0,
                        'startColumnIndex': 0
                    }
                }
            }
        }
    ]
    
    body = {'requests': requests}
    service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()

def add_conditional_formatting(service, spreadsheet_id):
    """条件付き書式設定（スコアに基づく色分け）"""
    requests = [
        {
            'addConditionalFormatRule': {
                'rule': {
                    'ranges': [{
                        'sheetId': 0,
                        'startColumnIndex': 2,  # recognition_score列
                        'endColumnIndex': 3
                    }],
                    'gradientRule': {
                        'minpoint': {
                            'color': {'red': 1, 'green': 0.8, 'blue': 0.8},
                            'type': 'MIN'
                        },
                        'midpoint': {
                            'color': {'red': 1, 'green': 1, 'blue': 0.8},
                            'type': 'PERCENTILE',
                            'value': '50'
                        },
                        'maxpoint': {
                            'color': {'red': 0.8, 'green': 1, 'blue': 0.8},
                            'type': 'MAX'
                        }
                    }
                },
                'index': 0
            }
        }
    ]
    
    body = {'requests': requests}
    service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()

def main():
    """メイン処理"""
    
    print("=" * 60)
    print("Google Sheetsへのアップロード処理")
    print("=" * 60)
    
    # 入力ファイル
    input_file = 'database_final_enriched_20250910_132247.csv'
    
    # データ読み込み
    print(f"\n1. データ読み込み中: {input_file}")
    data = []
    with open(input_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        for row in reader:
            data.append(row)
    
    print(f"   読み込み完了: {len(data)}行")
    
    # Google Sheets API認証
    print("\n2. Google Sheets API認証中...")
    try:
        creds = load_credentials()
        service = build('sheets', 'v4', credentials=creds)
        print("   認証成功")
    except Exception as e:
        print(f"   認証エラー: {e}")
        return
    
    # 新しいスプレッドシートを作成
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    title = f"人物データベース最終版_{timestamp}"
    
    print(f"\n3. 新しいスプレッドシートを作成中: {title}")
    spreadsheet_id = create_new_spreadsheet(service, title)
    
    if not spreadsheet_id:
        print("   スプレッドシートの作成に失敗しました")
        return
    
    print(f"   作成成功: {spreadsheet_id}")
    
    # データをアップロード
    print("\n4. データをアップロード中...")
    
    # バッチサイズを設定（一度に送信する行数）
    batch_size = 1000
    
    for i in range(0, len(data), batch_size):
        batch = data[i:i+batch_size]
        range_name = f'Database!A{i+1}'
        
        body = {
            'values': batch
        }
        
        try:
            result = service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
            
            print(f"   アップロード: {i+1}-{min(i+batch_size, len(data))}行")
        except HttpError as e:
            print(f"   エラー: {e}")
            return
    
    # フォーマット設定
    print("\n5. フォーマット設定中...")
    format_spreadsheet(service, spreadsheet_id)
    add_conditional_formatting(service, spreadsheet_id)
    print("   フォーマット設定完了")
    
    # 共有設定（オプション）
    print("\n6. 共有設定")
    spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
    print(f"   スプレッドシートURL: {spreadsheet_url}")
    
    # 設定ファイルに保存
    config = {
        'spreadsheet_id': spreadsheet_id,
        'spreadsheet_url': spreadsheet_url,
        'title': title,
        'uploaded_at': datetime.now().isoformat(),
        'total_records': len(data) - 1  # ヘッダーを除く
    }
    
    with open('sheets_upload_config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 60)
    print("アップロード完了！")
    print(f"URL: {spreadsheet_url}")
    print("=" * 60)
    
    # ブラウザで開く（macOS）
    import subprocess
    try:
        subprocess.run(['open', spreadsheet_url])
        print("\nブラウザでスプレッドシートを開きました")
    except:
        pass

if __name__ == '__main__':
    main()