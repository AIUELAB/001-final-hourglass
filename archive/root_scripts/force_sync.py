#!/usr/bin/env python3
"""
Ultra Think データベース強制同期スクリプト
trusted_episodes_latest.csvファイルをGoogle Sheetsに同期
"""

import os
import json
import glob
from pathlib import Path
from datetime import datetime
from google_sheets_sync import GoogleSheetsSync

def format_spreadsheet_name(csv_filename):
    """CSVファイル名をスプレッドシート名にフォーマット（永続ルール適用）"""
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

def find_latest_ultra_think_csv():
    """trusted_episodes_latest.csvファイルを確認"""
    trusted_csv = "trusted_episodes_latest.csv"
    if not os.path.exists(trusted_csv):
        return None

    # trusted_episodes_latest.csvのみを使用
    return trusted_csv

def update_config_with_latest_csv():
    """設定ファイルをtrusted_episodes_latest.csvで更新"""
    config_file = "sheets_config.json"

    # trusted_episodes_latest.csvファイルを取得
    latest_csv = find_latest_ultra_think_csv()
    if not latest_csv:
        print("❌ trusted_episodes_latest.csvファイルが見つかりません")
        return None

    print(f"📁 検証済みCSVファイル: {latest_csv}")

    # 設定を読み込み
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # CSVファイル名とシート名を更新
    old_csv = config.get("csv_file", "")
    config["csv_file"] = latest_csv

    # シート名を生成（Ultra Think形式に変換）
    sheet_name = format_spreadsheet_name(latest_csv)
    config["sheet_name"] = sheet_name

    # 設定を保存
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print(f"✅ 設定を更新: {old_csv} → {latest_csv}")
    return latest_csv

def main():
    """メイン実行関数"""
    print("=" * 50)
    print("🚀 Ultra Think 検証済みデータベース強制同期")
    print("=" * 50)

    # trusted_episodes_latest.csvで設定を更新
    latest_csv = update_config_with_latest_csv()
    if not latest_csv:
        return False

    try:
        # GoogleSheetsSync インスタンスを作成
        sync = GoogleSheetsSync()

        # 認証情報をセットアップ
        sync.setup_credentials()
        print("✅ Google Sheets API接続成功")

        # スプレッドシートを作成または取得
        if not sync.create_or_get_spreadsheet():
            print("❌ スプレッドシートの作成/取得に失敗しました")
            return False

        # スプレッドシート名を同期（永続ルール適用）
        try:
            expected_sheet_name = format_spreadsheet_name(latest_csv)
            current_sheet_name = sync.spreadsheet.title

            if current_sheet_name != expected_sheet_name:
                sync.spreadsheet.update_title(expected_sheet_name)
                print(f"📝 スプレッドシート名を更新: {current_sheet_name} → {expected_sheet_name}")
            else:
                print(f"✅ スプレッドシート名は既に正しい形式: {expected_sheet_name}")
        except Exception as e:
            print(f"⚠️ スプレッドシート名更新エラー: {e}")

        # CSVファイルをGoogle Sheetsにアップロード
        print("\n📊 データアップロード開始...")
        result = sync.upload_csv_to_sheets()

        if result:
            # 同期ログを更新
            sync_log_file = "sync_log.json"
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "csv_file": latest_csv,
                "status": "success",
                "message": "強制同期完了"
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

            print("\n" + "=" * 50)
            print("✅ 同期完了！")
            print(f"📊 ファイル: {latest_csv}")
            print(f"📝 シート名: {sync.sheet_name}")
            print(f"🔗 URL: https://docs.google.com/spreadsheets/d/{sync.spreadsheet_id}")
            print("=" * 50)
            return True
        else:
            print("❌ 同期に失敗しました")
            return False

    except Exception as e:
        print(f"❌ エラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
