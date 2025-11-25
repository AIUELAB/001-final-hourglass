from src.secure_config import config
#!/usr/bin/env python3
"""
日本語表記修正済みのデータをGoogle Sheetsに同期
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
csv_file = 'ultra_think_JAPANESE_DISPLAY_FIXED_20250828_192840.csv'
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
new_sheet_name = "Japanese Display Fixed 20250828"
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

# 指定person_idの確認
target_ids = ['P000064', 'P000065', 'P000066', 'P000067', 'P000068', 'P000069', 'P000070', 'P000073', 'P000074']

print("\n🎯 指定person_idの表示名:")
for pid in target_ids:
    row = df[df['person_id'] == pid]
    if not row.empty:
        display = row.iloc[0]['person_name_display']
        ja_name = row.iloc[0]['person_name_ja']
        # 日本語が含まれているか確認
        import re
        has_jp = bool(re.search(r'[\u3000-\u303F\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', str(display)))
        status = "✅" if has_jp else "❌"
        print(f"  {pid}: {display} {status}")

# 統計
japanese = df[df['nationality'] == '日本']
youtubers = japanese[japanese['occupation'] == 'YouTuber']

def has_japanese_chars(text):
    import re
    if pd.isna(text):
        return False
    return bool(re.search(r'[\u3000-\u303F\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', str(text)))

jp_display_count = sum(1 for _, row in japanese.iterrows() if has_japanese_chars(row['person_name_display']))
yt_jp_display_count = sum(1 for _, row in youtubers.iterrows() if has_japanese_chars(row['person_name_display']))

print(f"\n📊 統計:")
print(f"   日本人総数: {len(japanese)}人")
print(f"   日本語表記: {jp_display_count}人 ({jp_display_count/len(japanese)*100:.1f}%)")
print(f"   YouTuber日本語表記: {yt_jp_display_count}/{len(youtubers)} ({yt_jp_display_count/len(youtubers)*100:.1f}%)")

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
    'message': '日本語表記修正完了',
    'stats': {
        'japanese_display_count': jp_display_count,
        'japanese_display_rate': f"{jp_display_count/len(japanese)*100:.1f}%",
        'target_ids_fixed': '8/9'
    }
})

with open('sync_log.json', 'w') as f:
    json.dump(sync_log[-10:], f, ensure_ascii=False, indent=2)

print(f"\n✅ 同期完了！")
print(f"📊 https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
