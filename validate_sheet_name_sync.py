#!/usr/bin/env python3
"""
スプレッドシート名同期検証スクリプト
CSVファイル名とスプレッドシート名の一致を確認し、必要に応じて修正
"""

import os
import json
import glob
import re
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

def format_spreadsheet_name(csv_filename):
    """CSVファイル名をスプレッドシート名にフォーマット（永続ルール適用）"""
    # .csv拡張子を削除
    name = csv_filename.replace('.csv', '')
    
    # アンダースコアをスペースに変換
    name = name.replace('_', ' ')
    
    # ultra thinkをUltra Thinkに変換（大文字化）
    parts = name.split()
    if len(parts) >= 2 and parts[0].lower() == 'ultra' and parts[1].lower() == 'think':
        parts[0] = 'Ultra'
        parts[1] = 'Think'
        # 残りの部分を適切に大文字化
        for i in range(2, len(parts)):
            # 日付形式（YYYYMMDD）と時刻形式（HHMMSS）はそのまま保持
            if re.match(r'\d{8}', parts[i]) or re.match(r'\d{6}', parts[i]):
                pass  # 数字はそのまま
            elif parts[i].isupper():
                pass  # すでに大文字の場合はそのまま
            else:
                # 各単語の最初を大文字に
                parts[i] = parts[i].title()
    
    return ' '.join(parts)

def find_latest_ultra_think_csv():
    """最新のultra_think_*.csvファイルを見つける"""
    csv_files = glob.glob("ultra_think_*.csv")
    if not csv_files:
        return None
    
    # ファイル更新日時でソート
    latest_file = max(csv_files, key=lambda f: os.path.getmtime(f))
    return latest_file

def validate_and_sync():
    """スプレッドシート名を検証して同期"""
    
    print("🔍 スプレッドシート名同期検証を開始...")
    print("=" * 60)
    
    # 設定ファイル読み込み
    config_file = 'sheets_config.json'
    if not os.path.exists(config_file):
        print(f"❌ {config_file}が見つかりません")
        return False
    
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # 最新のCSVファイルを取得
    latest_csv = find_latest_ultra_think_csv()
    if not latest_csv:
        print("❌ ultra_think_*.csvファイルが見つかりません")
        return False
    
    print(f"📁 最新CSVファイル: {latest_csv}")
    
    # 期待されるスプレッドシート名を生成
    expected_sheet_name = format_spreadsheet_name(latest_csv)
    print(f"📋 期待されるスプレッドシート名: {expected_sheet_name}")
    
    try:
        # Google Sheets API認証
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
                  'https://www.googleapis.com/auth/drive']
        
        creds = Credentials.from_service_account_file(
            'key/credentials.json',
            scopes=SCOPES
        )
        
        client = gspread.authorize(creds)
        
        # スプレッドシートを取得
        spreadsheet_id = config.get('spreadsheet_id')
        if not spreadsheet_id:
            print("❌ spreadsheet_idが設定されていません")
            return False
        
        spreadsheet = client.open_by_key(spreadsheet_id)
        current_sheet_name = spreadsheet.title
        
        print(f"📊 現在のスプレッドシート名: {current_sheet_name}")
        
        # 名前が一致しているか確認
        if current_sheet_name == expected_sheet_name:
            print("✅ スプレッドシート名は正しく同期されています！")
            validation_result = {
                'status': 'SYNCED',
                'csv_file': latest_csv,
                'spreadsheet_name': current_sheet_name,
                'expected_name': expected_sheet_name
            }
        else:
            print(f"⚠️ スプレッドシート名が一致しません")
            print(f"  現在: {current_sheet_name}")
            print(f"  期待: {expected_sheet_name}")
            
            # 自動修正を実行
            print("\n🔧 スプレッドシート名を修正中...")
            spreadsheet.update_title(expected_sheet_name)
            print(f"✅ スプレッドシート名を更新しました: {expected_sheet_name}")
            
            validation_result = {
                'status': 'FIXED',
                'csv_file': latest_csv,
                'old_name': current_sheet_name,
                'new_name': expected_sheet_name
            }
        
        # 設定ファイルを更新
        config['csv_file'] = latest_csv
        config['sheet_name'] = expected_sheet_name
        config['last_validated'] = datetime.now().isoformat()
        config['sheet_name_sync_rule'] = 'auto'  # 永続ルール有効
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        print("\n📄 設定ファイルを更新しました")
        
        # 検証レポートを保存
        report_file = f'SHEET_NAME_VALIDATION_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        validation_result['timestamp'] = datetime.now().isoformat()
        validation_result['spreadsheet_id'] = spreadsheet_id
        validation_result['spreadsheet_url'] = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(validation_result, f, ensure_ascii=False, indent=2)
        
        print(f"📊 検証レポート保存: {report_file}")
        
        print("\n" + "=" * 60)
        print("✅ スプレッドシート名同期検証完了！")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """メイン実行関数"""
    success = validate_and_sync()
    
    if success:
        print("\n📌 永続ルール確認:")
        print("  • CSVファイル名とスプレッドシート名は常に同期")
        print("  • ultra_think_*.csv → Ultra Think * 形式")
        print("  • アンダースコア(_) → スペース( )に変換")
        print("  • 日付・時刻はそのまま保持")
        
        # 自動同期の状態を確認
        config_file = 'sheets_config.json'
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        if config.get('auto_rename_sheet', False):
            print("\n✅ 自動同期は有効です (auto_rename_sheet: true)")
        else:
            print("\n⚠️ 自動同期が無効です。有効にすることをお勧めします。")
    
    return success

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)