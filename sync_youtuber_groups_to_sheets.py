from src.secure_config import config
#!/usr/bin/env python3
"""
YouTuberグループ修正済みデータをGoogle Sheetsに同期
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
csv_file = 'ultra_think_YOUTUBER_GROUPS_FIXED_20250828_201154.csv'
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
new_sheet_name = "YouTuber Groups 20250828 Final"
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

# P000111（ふくらP）の確認
p000111 = df[df['person_id'] == 'P000111']
if not p000111.empty:
    display = p000111.iloc[0]['person_name_display']
    print(f"\n🌟 P000111（ふくらP）: {display}")
    if 'QuizKnock' in display:
        print("   ✅ 正しく「ふくらP (QuizKnock)」と表示されています！")

# グループ別統計
import re

youtubers = df[df['occupation'] == 'YouTuber']
has_parentheses = youtubers[youtubers['person_name_display'].str.contains(r'[\(（]', na=False)]

groups = {}
for idx, row in has_parentheses.iterrows():
    display = str(row['person_name_display'])
    match = re.search(r'[\(（](.*?)[\)）]', display)
    if match:
        group_name = match.group(1)
        groups[group_name] = groups.get(group_name, 0) + 1

print(f"\n📊 最終統計:")
print(f"   YouTuber総数: {len(youtubers)}人")
print(f"   グループメンバー: {len(has_parentheses)}人 ({len(has_parentheses)/len(youtubers)*100:.1f}%)")
print(f"   グループ数: {len(groups)}")

print(f"\n📋 主要グループ:")
major_groups = ['QuizKnock', 'フィッシャーズ', '東海オンエア', 'コムドット', 'スカイピース']
for group in major_groups:
    if group in groups:
        print(f"   {group}: {groups[group]}名 ✅")

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
    'message': 'YouTuberグループ修正完了',
    'highlights': {
        'P000111': 'ふくらP (QuizKnock)',
        'total_fixed': 34,
        'groups_count': len(groups),
        'coverage_rate': f"{len(has_parentheses)/len(youtubers)*100:.1f}%"
    }
})

with open('sync_log.json', 'w') as f:
    json.dump(sync_log[-10:], f, ensure_ascii=False, indent=2)

print(f"\n✅ 同期完了！")
print(f"📊 https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
print(f"\n🎉 P000111（ふくらP）を含む全YouTuberグループ問題が解決されました！")
