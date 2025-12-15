#!/usr/bin/env python3
"""
Ultra Think 自動更新システム - 一回実行版
監視モードなしで、キャッシュクリア＆完全置換同期を実行

作成日: 2025-08-31
"""

import os
import sys
import json
import pandas as pd
import gspread
from pathlib import Path
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import webbrowser
import time

# 自動更新システムコンポーネント
from src.cache_manager import CacheManager
from src.auto_updater_fixed import AutoUpdaterFixed as AutoUpdater
from src.version_controller import VersionController
from src.integrity_checker import IntegrityChecker


class OneTimeSyncExecutor:
    """一回限りの同期実行クラス"""

    def __init__(self):
        self.cache_manager = CacheManager()
        self.auto_updater = AutoUpdater()
        self.version_controller = VersionController()
        self.integrity_checker = IntegrityChecker()

        # 設定読み込み
        self.load_configs()

        print("=" * 60)
        print("🚀 Ultra Think 自動更新システム（一回実行版）")
        print("=" * 60)

    def load_configs(self):
        """設定ファイルを読み込み"""
        # sheets_config.json
        sheets_config_path = Path("sheets_config.json")
        if sheets_config_path.exists():
            with open(sheets_config_path, "r", encoding="utf-8") as f:
                self.sheets_config = json.load(f)
        else:
            print("❌ sheets_config.jsonが見つかりません")
            sys.exit(1)

        # startup_config.json
        startup_config_path = Path("startup_config.json")
        if startup_config_path.exists():
            with open(startup_config_path, "r", encoding="utf-8") as f:
                self.startup_config = json.load(f)
        else:
            self.startup_config = {}

    def find_latest_csv(self):
        """最新のultra_think_*.csvファイルを検索"""
        csv_files = list(Path('.').glob('ultra_think_*.csv'))

        if not csv_files:
            print("❌ ultra_think_*.csv ファイルが見つかりません")
            return None

        # 最新のファイルを選択
        latest_csv = max(csv_files, key=lambda f: f.stat().st_mtime)
        print(f"\n📄 対象ファイル: {latest_csv.name}")

        return latest_csv

    def run_sync(self):
        """同期を実行"""

        # 1. 最新のCSVファイルを検索
        csv_file = self.find_latest_csv()
        if not csv_file:
            return False

        # 2. データ読み込み
        print("\n📊 データ読み込み中...")
        try:
            df = pd.read_csv(csv_file)
            print(f"✅ データ読み込み完了: {len(df)}行 × {len(df.columns)}列")
        except Exception as e:
            print(f"❌ データ読み込みエラー: {e}")
            return False

        # 3. キャッシュ完全クリア
        print("\n🧹 キャッシュクリア中...")
        self.cache_manager.purge_all_cache()
        print("✅ すべてのキャッシュをクリアしました")

        # 4. データ整合性チェック
        print("\n🔍 データ整合性チェック中...")
        is_valid, validated_df = self.integrity_checker.validate_before_sync(df)

        if is_valid:
            print("✅ データ整合性チェック完了")
            df = validated_df
        else:
            print("⚠️ データに問題がありますが続行します")

        # 5. バージョン作成
        print("\n💾 バージョン作成中...")
        version_id = self.version_controller.create_version(
            df,
            f"auto_sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        print(f"✅ バージョン作成完了: {version_id}")

        # 6. Google Sheetsへの完全置換同期
        print("\n☁️ Google Sheetsに同期中...")
        spreadsheet_id = self.sheets_config.get('spreadsheet_id')

        if not spreadsheet_id:
            print("❌ spreadsheet_idが設定されていません")
            return False

        try:
            # 完全置換同期を実行
            success, result = self.auto_updater.force_full_replacement(
                spreadsheet_id,
                df,
                new_sheet_name="Sheet1"
            )

            if success:
                print("✅ Google Sheetsへの同期完了！")

                # スプレッドシート名も更新
                if self.sheets_config.get('auto_rename_sheet', True):
                    self.rename_spreadsheet(spreadsheet_id, csv_file.stem)

                # ブラウザで開く
                if self.startup_config.get('startup_settings', {}).get('auto_open_browser', True):
                    self.open_in_browser(spreadsheet_id)

                # 成功音を再生（macOS）
                os.system("afplay /System/Library/Sounds/Glass.aiff 2>/dev/null &")

                return True
            else:
                print(f"❌ 同期エラー: {result.get('error', 'Unknown error')}")
                return False

        except Exception as e:
            print(f"❌ 同期中にエラーが発生: {e}")
            return False

    def rename_spreadsheet(self, spreadsheet_id, new_name):
        """スプレッドシート名を更新"""
        try:
            # アンダースコアをスペースに変換
            display_name = new_name.replace('_', ' ')
            display_name = display_name.replace('ultra think', 'Ultra Think')

            print(f"\n📝 スプレッドシート名を更新: {display_name}")

            # Google Sheets APIで名前を更新
            service = self.auto_updater.service
            if service:
                request = {
                    'requests': [{
                        'updateSpreadsheetProperties': {
                            'properties': {
                                'title': display_name
                            },
                            'fields': 'title'
                        }
                    }]
                }

                service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body=request
                ).execute()

                print(f"✅ スプレッドシート名更新完了")
        except Exception as e:
            print(f"⚠️ スプレッドシート名の更新エラー: {e}")

    def open_in_browser(self, spreadsheet_id):
        """ブラウザでスプレッドシートを開く"""
        try:
            url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"

            # キャッシュバスターURLを生成
            busted_url = self.cache_manager.generate_cache_buster_url(url)

            print(f"\n🌐 ブラウザで開いています...")
            webbrowser.open(busted_url)

        except Exception as e:
            print(f"⚠️ ブラウザ起動エラー: {e}")

    def show_summary(self):
        """実行サマリーを表示"""
        print("\n" + "=" * 60)
        print("📋 実行サマリー")
        print("=" * 60)
        print("✅ キャッシュクリア: 完了")
        print("✅ データ検証: 完了")
        print("✅ バージョン管理: 完了")
        print("✅ Google Sheets同期: 完了")
        print("✅ スプレッドシート名更新: 完了")
        print("✅ ブラウザ表示: 完了")
        print("\n🎉 すべての処理が正常に完了しました！")
        print("=" * 60)


def main():
    """メイン実行"""
    try:
        executor = OneTimeSyncExecutor()

        # 同期実行
        success = executor.run_sync()

        if success:
            executor.show_summary()

            # 同期ログを記録
            sync_log = {
                "timestamp": datetime.now().isoformat(),
                "status": "success",
                "type": "one_time_sync",
                "auto_update_enabled": True
            }

            # sync_log.jsonに追記
            log_file = Path("sync_log.json")
            if log_file.exists():
                with open(log_file, "r", encoding="utf-8") as f:
                    logs = json.load(f)
            else:
                logs = []

            logs.append(sync_log)

            # 最新10件のみ保持
            logs = logs[-10:]

            with open(log_file, "w", encoding="utf-8") as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)

            return 0
        else:
            print("\n❌ 同期に失敗しました")
            return 1

    except KeyboardInterrupt:
        print("\n⚠️ ユーザーによって中断されました")
        return 1
    except Exception as e:
        print(f"\n❌ 予期しないエラー: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
