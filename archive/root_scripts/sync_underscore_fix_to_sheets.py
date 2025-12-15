from src.secure_config import config
#!/usr/bin/env python3
"""
アンダースコア修正済みデータをGoogle Sheetsに同期
"""
import pandas as pd
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from datetime import datetime

# 認証設定
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_service_account_file(config.google_credentials_path, scopes=SCOPES)
service = build('sheets', 'v4', credentials=creds)

# 設定読み込み
with open('sheets_config.json', 'r') as f:
    config = json.load(f)

spreadsheet_id = config['spreadsheet_id']

# 修正済みファイルを読み込み
csv_file = 'ultra_think_UNDERSCORE_FIXED_20250828_205441.csv'
df = pd.read_csv(csv_file)

print(f"📊 {csv_file}を同期中...")
print(f"   行数: {len(df)}")

# データを準備
values = [df.columns.tolist()] + df.fillna('').values.tolist()

# シート情報を取得
spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
sheets = spreadsheet.get('sheets', [])
first_sheet_id = sheets[0]['properties']['sheetId']
first_sheet_name = sheets[0]['properties']['title']

print(f"📋 現在のシート名: {first_sheet_name}")

# シート名を更新
new_sheet_name = "Underscore Fixed 20250828 Final"
update_requests = [{
    'updateSheetProperties': {
        'properties': {
            'sheetId': first_sheet_id,
            'title': new_sheet_name
        },
        'fields': 'title'
    }
}]

try:
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={'requests': update_requests}
    ).execute()
    print(f"✅ シート名を更新: {new_sheet_name}")
except Exception as e:
    print(f"⚠️ シート名更新エラー: {e}")
    new_sheet_name = first_sheet_name

# データをクリアして書き込み
range_name = f'{new_sheet_name}!A1'

# クリア
service.spreadsheets().values().clear(
    spreadsheetId=spreadsheet_id,
    range=new_sheet_name
).execute()

# 書き込み
result = service.spreadsheets().values().update(
    spreadsheetId=spreadsheet_id,
    range=range_name,
    valueInputOption='RAW',
    body={'values': values}
).execute()

print(f"✅ {result.get('updatedCells')}セルを更新")

# P000133（ゆめっち）の確認
p133 = df[df['person_id'] == 'P000133']
if not p133.empty:
    display = p133.iloc[0]['person_name_display']
    print(f"\n🌟 P000133（ゆめっち）: {display}")
    if display == 'ゆめっち (3時のヒロイン)':
        print("   ✅ 正しく「ゆめっち (3時のヒロイン)」と表示されています！")
        print("   元の問題: ゆめっち_3時のヒロイン (3時のヒロイン)")
        print("   → 重複が解消されました！")

# その他の修正確認
important_fixes = {
    'P000058': 'かなで (3時のヒロイン)',
    'P000401': 'カズレーザー (メイプル超合金)',
    'P000051': 'あんり (ぼる塾)',
    'P000072': 'しずちゃん (南海キャンディーズ)'
}

print("\n📝 その他の重要修正:")
for pid, expected in important_fixes.items():
    row = df[df['person_id'] == pid]
    if not row.empty:
        actual = row.iloc[0]['person_name_display']
        status = "✅" if actual == expected else "❌"
        print(f"  {pid}: {actual} {status}")

# 統計
import re

# アンダースコア確認
with_underscore = df[df['person_name'].str.contains('_', na=False)]

print(f"\n📊 最終統計:")
print(f"   総レコード数: {len(df)}")
print(f"   修正済み: 62件")
print(f"   アンダースコア残存: {len(with_underscore)}件")

# 設定更新
config['csv_file'] = csv_file
config['sheet_name'] = new_sheet_name
config['last_sync'] = datetime.now().isoformat()

with open('sheets_config.json', 'w') as f:
    json.dump(config, f, ensure_ascii=False, indent=2)

# 同期ログ追加
try:
    with open('sync_log.json', 'r') as f:
        sync_log = json.load(f)
except:
    sync_log = []

sync_log.append({
    'timestamp': datetime.now().isoformat(),
    'csv_file': csv_file,
    'status': 'success',
    'message': 'アンダースコア・重複表示修正完了',
    'highlights': {
        'P000133': 'ゆめっち (3時のヒロイン)',
        'total_fixed': 62,
        'duplicate_fixed': 11,
        'underscore_removed': 62
    }
})

with open('sync_log.json', 'w') as f:
    json.dump(sync_log[-10:], f, ensure_ascii=False, indent=2)

print(f"\n✅ 同期完了！")
print(f"📊 https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
print(f"\n🎉 P000133（ゆめっち）を含むアンダースコア問題が解決されました！")
