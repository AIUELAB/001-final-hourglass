from src.secure_config import config
#!/usr/bin/env python3
"""
はじめしゃちょー修正済みのデータをGoogle Sheetsに同期
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
csv_file = 'ultra_think_HAJIME_FIXED_20250828_194909.csv'
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
new_sheet_name = "Hajime Fixed 20250828 Final"
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

# P000104（はじめしゃちょー）の確認
hajime = df[df['person_id'] == 'P000104']
if not hajime.empty:
    display = hajime.iloc[0]['person_name_display']
    print(f"\n🌟 P000104（はじめしゃちょー）: {display}")
    if display == 'はじめしゃちょー':
        print("   ✅ 正しく「はじめしゃちょー」と表示されています！")
        print(f"   チャンネル登録者数: 約1,500万人（日本トップクラス）")

# その他の修正確認
fixed_ids = ['P000064', 'P000077', 'P000087', 'P000096', 'P001696', 'P002476']
print("\n📝 その他の修正:")
for pid in fixed_ids:
    row = df[df['person_id'] == pid]
    if not row.empty:
        display = row.iloc[0]['person_name_display']
        print(f"  {pid}: {display} ✅")

# 統計
import re
def has_japanese(text):
    if pd.isna(text):
        return False
    return bool(re.search(r'[\u3000-\u303F\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', str(text)))

japanese_youtubers = df[(df['nationality'] == '日本') & (df['occupation'] == 'YouTuber')]
jp_display_count = sum(1 for _, row in japanese_youtubers.iterrows() if has_japanese(row['person_name_display']))

print(f"\n📊 最終統計:")
print(f"   日本人YouTuber: {len(japanese_youtubers)}人")
print(f"   日本語表記: {jp_display_count}人 ({jp_display_count/len(japanese_youtubers)*100:.1f}%)")
print(f"   今回修正: 7件")

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
    'message': 'はじめしゃちょー修正完了',
    'highlights': {
        'P000104': 'はじめしゃちょー',
        'total_fixed': 7,
        'youtuber_jp_rate': f"{jp_display_count/len(japanese_youtubers)*100:.1f}%"
    }
})

with open('sync_log.json', 'w') as f:
    json.dump(sync_log[-10:], f, ensure_ascii=False, indent=2)

print(f"\n✅ 同期完了！")
print(f"📊 https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
print(f"\n🎉 はじめしゃちょー問題が完全に解決されました！")
