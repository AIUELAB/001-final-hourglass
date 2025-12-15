#!/usr/bin/env python3
"""
Foreign Names Corrected Database Sync Script
Sync ultra_think_FOREIGN_NAMES_CORRECTED_20250831_140703.csv to Google Sheets and open in browser.
"""

import os
import json
import webbrowser
import pandas as pd
from pathlib import Path
from datetime import datetime
from google_sheets_sync import GoogleSheetsSync

CSV_FILE = "ultra_think_FOREIGN_NAMES_CORRECTED_20250831_140703.csv"

def format_spreadsheet_name(csv_filename):
    """CSVファイル名をスプレッドシート名にフォーマット"""
    import re

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

def update_sheets_config():
    """sheets_config.jsonを更新"""
    config_file = "sheets_config.json"

    # CSVファイルの存在確認
    if not os.path.exists(CSV_FILE):
        print(f"❌ CSVファイルが見つかりません: {CSV_FILE}")
        return False

    print(f"📁 CSVファイル確認: {CSV_FILE}")

    # 設定を読み込み
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # 旧設定を記録
    old_csv = config.get("csv_file", "")
    old_sheet_name = config.get("sheet_name", "")

    # 新しい設定
    config["csv_file"] = CSV_FILE
    config["sheet_name"] = format_spreadsheet_name(CSV_FILE)
    config["last_sync"] = datetime.now().isoformat()
    config["database_type"] = "FOREIGN_NAMES_CORRECTED"

    # 設定を保存
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print(f"✅ 設定更新完了:")
    print(f"   CSV: {old_csv} → {CSV_FILE}")
    print(f"   シート名: {old_sheet_name} → {config['sheet_name']}")

    return True

def sync_to_google_sheets():
    """Google Sheetsに同期"""
    try:
        # GoogleSheetsSync インスタンスを作成
        sync = GoogleSheetsSync()

        # 認証情報をセットアップ
        if not sync.setup_credentials():
            print("❌ Google Sheets API認証に失敗しました")
            return False

        print("✅ Google Sheets API接続成功")

        # スプレッドシートを作成または取得
        if not sync.create_or_get_spreadsheet():
            print("❌ スプレッドシートの作成/取得に失敗しました")
            return False

        # スプレッドシート名を同期
        try:
            expected_sheet_name = format_spreadsheet_name(CSV_FILE)
            current_sheet_name = sync.sheet.title

            if current_sheet_name != expected_sheet_name:
                sync.sheet.update_title(expected_sheet_name)
                print(f"📝 スプレッドシート名を更新: {current_sheet_name} → {expected_sheet_name}")
            else:
                print(f"✅ スプレッドシート名は既に正しい形式: {expected_sheet_name}")
        except Exception as e:
            print(f"⚠️ スプレッドシート名更新エラー: {e}")

        # CSVファイルのデータを読み込み（最初の5000行のみ）
        print("\n📊 データ読み込み中...")
        df = pd.read_csv(CSV_FILE, encoding='utf-8')
        original_rows = len(df)

        # 最初の5000行に制限
        if len(df) > 5000:
            df = df.head(5000)
            print(f"⚠️ データサイズが大きいため、最初の5000行のみ同期します (元: {original_rows}行)")

        print(f"📊 同期対象データ: {len(df)}行 x {len(df.columns)}列")

        # 一時的にCSVファイルを設定に反映させてアップロード
        sync.csv_file = CSV_FILE

        # CSVファイルをGoogle Sheetsにアップロード
        print("\n📊 データアップロード開始...")
        result = sync.upload_csv_to_sheets()

        if result:
            # 同期ログを更新
            sync_log_file = "sync_log.json"
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "csv_file": CSV_FILE,
                "rows_synced": len(df),
                "total_rows": original_rows,
                "status": "success",
                "message": "外国名修正データベース同期完了"
            }

            # 既存のログを読み込み
            logs = []
            if os.path.exists(sync_log_file):
                with open(sync_log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)

            # 新しいエントリを追加（最大10件保持）
            logs.insert(0, log_entry)
            logs = logs[:10]

            # ログを保存
            with open(sync_log_file, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)

            spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{sync.spreadsheet_id}"

            print("\n" + "=" * 60)
            print("✅ 同期完了！")
            print(f"📊 ファイル: {CSV_FILE}")
            print(f"📝 シート名: {sync.sheet_name}")
            print(f"📊 同期データ: {len(df)}行 (全{original_rows}行中)")
            print(f"🔗 URL: {spreadsheet_url}")
            print("=" * 60)

            return spreadsheet_url
        else:
            print("❌ 同期に失敗しました")
            return False

    except Exception as e:
        print(f"❌ エラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def open_in_browser(url):
    """ブラウザでスプレッドシートを開く"""
    try:
        print(f"\n🌐 ブラウザでスプレッドシートを開いています...")
        webbrowser.open_new_tab(url)
        print("✅ ブラウザで開きました")
        return True
    except Exception as e:
        print(f"⚠️ ブラウザ起動エラー: {e}")
        print(f"🔗 手動でアクセスしてください: {url}")
        return False

def main():
    """メイン実行関数"""
    print("=" * 60)
    print("🚀 外国名修正データベース同期スクリプト")
    print("=" * 60)
    print(f"📁 対象ファイル: {CSV_FILE}")
    print(f"📊 処理制限: 最初の5000行")
    print("=" * 60)

    # 1. sheets_config.jsonを更新
    print("\n📝 Step 1: 設定ファイル更新")
    if not update_sheets_config():
        print("❌ 設定ファイルの更新に失敗しました")
        return False

    # 2. Google Sheetsに同期
    print("\n☁️ Step 2: Google Sheets同期")
    spreadsheet_url = sync_to_google_sheets()
    if not spreadsheet_url:
        print("❌ Google Sheets同期に失敗しました")
        return False

    # 3. ブラウザで開く
    print("\n🌐 Step 3: ブラウザ起動")
    open_in_browser(spreadsheet_url)

    print("\n🎉 すべての処理が完了しました！")
    return True

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
