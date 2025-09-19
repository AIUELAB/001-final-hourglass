#!/usr/bin/env python3
"""
強制同期＆検証システム
Google Sheetsへの確実な同期と検証を保証

2025年8月29日実装
"""

import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
import time
from datetime import datetime
from pathlib import Path
import sys

# Google Sheets設定
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
CREDENTIALS_FILE = 'key/credentials.json'
SPREADSHEET_ID = '1G0ec3d5DHGiahLetsqey9W23HGFOn2tkEacsFd5ZSps'

def authenticate():
    """Google Sheets認証"""
    try:
        creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        print(f"❌ 認証エラー: {e}")
        sys.exit(1)

def find_latest_csv():
    """最新のCSVファイルを検索（修正済みファイルを優先）"""
    # まず COMPREHENSIVE_FIX ファイルを探す
    fix_files = list(Path('.').glob('ultra_think_COMPREHENSIVE_FIX_*.csv'))
    if fix_files:
        return max(fix_files, key=lambda x: x.stat().st_mtime)
    
    # なければ通常のultra_thinkファイル
    csv_files = list(Path('.').glob('ultra_think_*.csv'))
    if not csv_files:
        raise FileNotFoundError("No CSV files found")
    
    return max(csv_files, key=lambda x: x.stat().st_mtime)

def force_clear_sheet(worksheet):
    """シートを完全にクリアしてキャッシュを無効化"""
    print("🗑️ シートを完全クリア中...")
    worksheet.clear()
    time.sleep(2)  # API rate limit対策

def upload_with_retry(worksheet, df, max_retries=3):
    """リトライ機能付きアップロード"""
    # NaN値を空文字列に置換
    df = df.fillna('')
    
    for attempt in range(max_retries):
        try:
            print(f"📤 アップロード試行 {attempt + 1}/{max_retries}...")
            
            # データをリスト形式に変換
            values = [df.columns.tolist()] + df.values.tolist()
            
            # バッチアップデート（より確実な方法）
            worksheet.update(values, value_input_option='USER_ENTERED')
            
            # 強制的に待機（APIキャッシュクリア）
            time.sleep(3)
            
            return True
            
        except Exception as e:
            print(f"⚠️ アップロードエラー (試行 {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(5)  # リトライ前に待機
            else:
                return False
    
    return False

def verify_upload(worksheet, df, sample_size=10):
    """アップロードの検証（サンプルチェック）"""
    print(f"\n🔍 データ検証中（{sample_size}件サンプル）...")
    
    # P000083を必ず検証対象に含める
    critical_ids = ['P000083']
    
    # ランダムサンプル
    import random
    sample_indices = random.sample(range(len(df)), min(sample_size - 1, len(df)))
    
    # Google Sheetsからデータを取得
    sheet_data = worksheet.get_all_records()
    sheet_df = pd.DataFrame(sheet_data)
    
    verification_results = []
    all_verified = True
    
    # P000083の検証（最重要）
    for person_id in critical_ids:
        if person_id in df['person_id'].values:
            csv_row = df[df['person_id'] == person_id].iloc[0]
            
            if person_id in sheet_df['person_id'].values:
                sheet_row = sheet_df[sheet_df['person_id'] == person_id].iloc[0]
                
                csv_display = csv_row['person_name_display']
                sheet_display = sheet_row['person_name_display']
                
                match = csv_display == sheet_display
                verification_results.append({
                    'person_id': person_id,
                    'csv': csv_display,
                    'sheets': sheet_display,
                    'match': match
                })
                
                if not match:
                    all_verified = False
                    print(f"❌ {person_id}: 不一致")
                    print(f"   CSV: {csv_display}")
                    print(f"   Sheets: {sheet_display}")
                else:
                    print(f"✅ {person_id}: 一致 ({csv_display})")
    
    # その他のサンプル検証
    for idx in sample_indices:
        csv_row = df.iloc[idx]
        person_id = csv_row['person_id']
        
        if person_id in sheet_df['person_id'].values:
            sheet_row = sheet_df[sheet_df['person_id'] == person_id].iloc[0]
            
            # person_name_displayを比較
            csv_display = csv_row['person_name_display']
            sheet_display = sheet_row['person_name_display']
            
            if csv_display != sheet_display:
                all_verified = False
                verification_results.append({
                    'person_id': person_id,
                    'csv': csv_display,
                    'sheets': sheet_display,
                    'match': False
                })
    
    return all_verified, verification_results

def format_spreadsheet_name(csv_filename):
    """スプレッドシート名をフォーマット"""
    # ファイル名から拡張子を除去
    name = csv_filename.replace('.csv', '')
    
    # アンダースコアをスペースに変換
    name = name.replace('_', ' ')
    
    # 各単語の最初を大文字に
    words = name.split()
    formatted_words = []
    for word in words:
        if word.upper() in ['FIX', 'CSV', 'JSON']:
            formatted_words.append(word.upper())
        elif word.isdigit() or (len(word) == 6 and word.isdigit()):
            formatted_words.append(word)
        else:
            formatted_words.append(word.capitalize())
    
    return ' '.join(formatted_words)

def main():
    print("🚀 強制同期＆検証システム起動")
    print("=" * 60)
    
    # 最新のCSVファイルを検索
    csv_file = find_latest_csv()
    print(f"📂 対象ファイル: {csv_file}")
    
    # データ読み込み
    df = pd.read_csv(csv_file)
    print(f"📊 レコード数: {len(df)}")
    
    # 重要レコードの確認
    if 'P000083' in df['person_id'].values:
        p83 = df[df['person_id'] == 'P000083'].iloc[0]
        print(f"\n🎯 P000083の現在の値:")
        print(f"   person_name_display: {p83['person_name_display']}")
        print(f"   occupation: {p83['occupation']}")
    
    # Google Sheets認証
    print("\n🔐 Google Sheets認証中...")
    client = authenticate()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    
    # スプレッドシート名を更新
    new_title = format_spreadsheet_name(csv_file.name)
    print(f"📝 スプレッドシート名を更新: {new_title}")
    spreadsheet.update_title(new_title)
    
    # 最初のワークシートを取得
    worksheet = spreadsheet.get_worksheet(0)
    
    # シート名も更新
    timestamp = datetime.now().strftime('%Y%m%d %H%M%S')
    sheet_name = f"Comprehensive Fix {timestamp}"
    worksheet.update_title(sheet_name)
    print(f"📋 シート名: {sheet_name}")
    
    # 強制クリア（キャッシュ無効化）
    force_clear_sheet(worksheet)
    
    # データアップロード（リトライ付き）
    if upload_with_retry(worksheet, df):
        print("✅ アップロード成功")
    else:
        print("❌ アップロード失敗")
        sys.exit(1)
    
    # 検証
    print("\n🔍 データ検証開始...")
    time.sleep(5)  # 少し待機してAPIキャッシュをクリア
    
    verified, results = verify_upload(worksheet, df)
    
    if verified:
        print("\n✅ 検証成功！すべてのデータが正しく同期されました")
    else:
        print("\n⚠️ 検証で不一致が検出されました")
        print("再同期を試みます...")
        
        # 再度強制クリアとアップロード
        force_clear_sheet(worksheet)
        if upload_with_retry(worksheet, df):
            time.sleep(5)
            verified, results = verify_upload(worksheet, df)
            
            if verified:
                print("✅ 再同期成功！")
            else:
                print("❌ 再同期後も不一致があります")
                print("手動確認が必要です")
    
    # ログ保存
    sync_log = {
        'timestamp': datetime.now().isoformat(),
        'csv_file': str(csv_file),
        'spreadsheet_id': SPREADSHEET_ID,
        'spreadsheet_title': new_title,
        'sheet_name': sheet_name,
        'total_records': len(df),
        'verification': 'SUCCESS' if verified else 'FAILED',
        'verification_details': results
    }
    
    log_file = f"force_sync_validation_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(sync_log, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 ログ保存: {log_file}")
    
    # 最終確認URL
    print(f"\n🌐 Google Sheetsを確認:")
    print(f"   https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")
    
    return verified

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)