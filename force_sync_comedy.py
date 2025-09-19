from src.secure_config import config
#!/usr/bin/env python3
"""
修正済みのお笑い芸人データを強制的にGoogle Sheetsに同期
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
csv_file = 'ultra_think_COMEDY_GROUPS_FIXED_20250828_190550.csv'
df = pd.read_csv(csv_file)

print(f"📊 {csv_file}を強制同期中...")
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
new_sheet_name = "Comedy Groups Fixed 20250828"
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

# P000057の確認
p000057 = df[df['person_id'] == 'P000057']
if not p000057.empty:
    display = p000057.iloc[0]['person_name_display']
    print(f"\n🎯 P000057: {display}")
    if '(ジャングルポケット)' in str(display):
        print("   ✅ グループ名が正しく表示されています！")

# 統計
comedians = df[df['occupation'] == 'お笑い芸人']
with_groups = comedians[comedians['person_name_display'].str.contains(r'\(.*\)', na=False, regex=True)]

print(f"\n📊 お笑い芸人統計:")
print(f"   総数: {len(comedians)}人")
print(f"   グループ表示: {len(with_groups)}人 ({len(with_groups)/len(comedians)*100:.1f}%)")

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
    'message': 'お笑い芸人グループ名修正完了'
})

with open('sync_log.json', 'w') as f:
    json.dump(sync_log[-10:], f, ensure_ascii=False, indent=2)

print(f"\n✅ 同期完了！")
print(f"📊 https://docs.google.com/spreadsheets/d/{spreadsheet_id}")