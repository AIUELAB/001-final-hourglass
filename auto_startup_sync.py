from src.secure_config import config
#!/usr/bin/env python3
"""
Claude Code起動時自動同期システム
起動時に最新のultra_think_*.csvファイルをGoogle Sheetsと自動同期
全ルールも自動適用（Wikipedia検証を含む）
"""

import os
import sys
import json
import time
import webbrowser
import subprocess
from datetime import datetime
from pathlib import Path
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table
import traceback

# ルール適用システムをインポート
try:
    from ultra_think_auto_rules_master import apply_all_rules_to_new_data
    RULES_AVAILABLE = True
except ImportError:
    RULES_AVAILABLE = False

# Wikipedia検証システムをインポート
try:
    from ultra_think_wikipedia_validator import WikipediaValidator
    WIKIPEDIA_VALIDATOR_AVAILABLE = True
except ImportError:
    WIKIPEDIA_VALIDATOR_AVAILABLE = False

console = Console()

class StartupSync:
    """起動時自動同期クラス"""
    
    def __init__(self):
        self.config = self.load_config()
        self.startup_config = self.load_startup_config()
        self.client = None
        self.spreadsheet = None
        self.sheet = None
        self.latest_csv = None
        self.sync_log = []
        
    def load_config(self):
        """設定ファイルを読み込み"""
        try:
            with open('sheets_config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            console.print("[yellow]⚠️ sheets_config.jsonが見つかりません[/yellow]")
            return {
                'spreadsheet_id': '1G0ec3d5DHGiahLetsqey9W23HGFOn2tkEacsFd5ZSps',
                'auto_sync_enabled': True,
                'auto_rename_sheet': True
            }
    
    def load_startup_config(self):
        """起動設定ファイルを読み込み"""
        try:
            with open('startup_config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            console.print("[yellow]⚠️ startup_config.jsonが見つかりません[/yellow]")
            return {
                'startup_settings': {'auto_open_browser': False},
                'browser_settings': {'default_browser': 'default'},
                'startup_messages': {
                    'banner_title': '🚀 Ultra Think Claude Code 自動同期システム',
                    'success_message': '✅ 同期完了！'
                }
            }
    
    def save_config(self, updates):
        """設定を更新して保存"""
        self.config.update(updates)
        with open('sheets_config.json', 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
    
    def init_google_client(self):
        """Google Sheets APIクライアントを初期化"""
        try:
            scope = ['https://spreadsheets.google.com/feeds',
                     'https://www.googleapis.com/auth/drive']
            
            creds = Credentials.from_service_account_file(
                config.google_credentials_path,
                scopes=scope
            )
            
            self.client = gspread.authorize(creds)
            self.spreadsheet = self.client.open_by_key(self.config['spreadsheet_id'])
            self.sheet = self.spreadsheet.sheet1
            
            self.sync_log.append(f"✅ Google Sheets API接続成功")
            return True
            
        except Exception as e:
            self.sync_log.append(f"❌ API接続エラー: {e}")
            return False
    
    def find_latest_ultra_think_csv(self):
        """最新のultra_think_*.csvファイルを検索"""
        try:
            csv_files = list(Path('.').glob('ultra_think_*.csv'))
            if not csv_files:
                self.sync_log.append("⚠️ ultra_think_*.csvファイルが見つかりません")
                return None
            
            # 更新日時でソート
            latest_file = max(csv_files, key=lambda x: x.stat().st_mtime)
            self.latest_csv = latest_file.name
            
            # ファイル情報
            file_stat = latest_file.stat()
            file_size_mb = file_stat.st_size / (1024 * 1024)
            mod_time = datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            
            self.sync_log.append(f"📁 最新CSVファイル: {self.latest_csv}")
            self.sync_log.append(f"   サイズ: {file_size_mb:.2f} MB")
            self.sync_log.append(f"   更新日時: {mod_time}")
            
            return self.latest_csv
            
        except Exception as e:
            self.sync_log.append(f"❌ ファイル検索エラー: {e}")
            return None
    
    def format_sheet_name(self, csv_filename):
        """CSVファイル名をスプレッドシート名にフォーマット"""
        name = csv_filename.replace('.csv', '')
        name = name.replace('_', ' ')
        
        parts = name.split()
        if len(parts) >= 2 and parts[0].lower() == 'ultra' and parts[1].lower() == 'think':
            parts[0] = 'Ultra'
            parts[1] = 'Think'
            for i in range(2, len(parts)):
                if not parts[i].isdigit() and not parts[i].isupper():
                    parts[i] = parts[i].upper()
        
        return ' '.join(parts)
    
    def sync_sheet_name(self):
        """スプレッドシート名を同期"""
        if not self.config.get('auto_rename_sheet', True):
            self.sync_log.append("ℹ️ スプレッドシート名の自動更新は無効です")
            return False
        
        try:
            new_name = self.format_sheet_name(self.latest_csv)
            current_name = self.spreadsheet.title
            
            if current_name != new_name:
                self.spreadsheet.update_title(new_name)
                self.sync_log.append(f"📝 スプレッドシート名更新:")
                self.sync_log.append(f"   旧: {current_name}")
                self.sync_log.append(f"   新: {new_name}")
                
                # 設定を更新
                self.save_config({
                    'csv_file': self.latest_csv,
                    'sheet_name': new_name,
                    'last_sync': datetime.now().isoformat()
                })
                return True
            else:
                self.sync_log.append(f"ℹ️ スプレッドシート名は既に最新: {current_name}")
                return False
                
        except Exception as e:
            self.sync_log.append(f"❌ スプレッドシート名更新エラー: {e}")
            return False
    
    def apply_rules_if_available(self, df: pd.DataFrame) -> pd.DataFrame:
        """ルールが利用可能な場合は適用"""
        if RULES_AVAILABLE:
            self.sync_log.append("🎯 ルール自動適用を開始...")
            try:
                # ルールを適用（Google Sheets同期なし、後で行うため）
                df_processed = apply_all_rules_to_new_data(df, sync_to_sheets=False)
                self.sync_log.append("✅ ルール適用完了")
                return df_processed
            except Exception as e:
                self.sync_log.append(f"⚠️ ルール適用エラー: {e}")
                return df
        else:
            self.sync_log.append("ℹ️ ルール適用システムは利用できません")
            return df
    
    def sync_sheet_data(self):
        """スプレッドシートのデータを同期"""
        if not self.config.get('auto_sync_enabled', True):
            self.sync_log.append("ℹ️ データ自動同期は無効です")
            return False
        
        try:
            # CSVデータを読み込み
            self.sync_log.append(f"📊 CSVデータを読み込み中...")
            df = pd.read_csv(self.latest_csv)
            
            # ルールを適用
            if self.config.get('auto_apply_rules', True):
                df = self.apply_rules_if_available(df)
            
            df = df.fillna('')  # NaNを空文字列に置換
            
            rows_count = len(df)
            cols_count = len(df.columns)
            
            self.sync_log.append(f"   行数: {rows_count}")
            self.sync_log.append(f"   列数: {cols_count}")
            
            # 現在のシートのサイズを取得
            current_values = self.sheet.get_all_values()
            current_rows = len(current_values)
            
            # データが異なる場合のみ更新
            if current_rows != rows_count + 1:  # +1 for header
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    console=console,
                    transient=True
                ) as progress:
                    task = progress.add_task("データをアップロード中...", total=100)
                    
                    # 既存データをクリア
                    self.sheet.clear()
                    progress.update(task, advance=30)
                    
                    # ヘッダーと全データを一括更新
                    data = [df.columns.tolist()] + df.values.tolist()
                    progress.update(task, advance=30)
                    
                    # バッチ更新
                    self.sheet.update('A1', data)
                    progress.update(task, advance=40)
                
                self.sync_log.append(f"✅ データ同期完了: {rows_count}行を更新")
                return True
            else:
                self.sync_log.append(f"ℹ️ データは既に最新です（{current_rows - 1}行）")
                return False
                
        except Exception as e:
            self.sync_log.append(f"❌ データ同期エラー: {e}")
            return False
    
    def apply_wikipedia_verification(self):
        """Wikipedia検証を適用"""
        try:
            # CSVファイルを読み込み
            df = pd.read_csv(self.latest_csv)
            original_count = len(df)
            
            # Wikipedia検証実行
            validator = WikipediaValidator(use_parallel=True, max_workers=10)
            df_clean, removed_persons = validator.verify_all_persons(df, dry_run=False)
            
            if removed_persons:
                # 削除記録を保存
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                removed_df = pd.DataFrame(removed_persons)
                removed_file = f"removed_placeholders_{timestamp}.csv"
                removed_df.to_csv(removed_file, index=False)
                
                # クリーンなデータを保存
                output_file = f"ultra_think_VERIFIED_{timestamp}.csv"
                df_clean.to_csv(output_file, index=False)
                
                # 設定を更新
                self.save_config({
                    'csv_file': output_file,
                    'last_wikipedia_verify': datetime.now().isoformat()
                })
                
                # CSVファイルを更新
                self.latest_csv = output_file
                
                # Google Sheetsに再同期
                if self.sheet:
                    self.sync_sheet_data()
                
                self.sync_log.append(f"✅ Wikipedia検証完了: {len(removed_persons)}件削除")
                self.sync_log.append(f"   残存: {original_count} → {len(df_clean)}人")
                return True
            else:
                self.sync_log.append("ℹ️ Wikipedia検証: 削除対象なし")
                return False
                
        except Exception as e:
            self.sync_log.append(f"❌ Wikipedia検証エラー: {e}")
            return False
    
    def apply_rules_to_data(self):
        """ルールを適用"""
        try:
            # ルール適用が利用可能かチェック
            if not RULES_AVAILABLE:
                self.sync_log.append("⚠️ ルール適用モジュールが利用できません")
                return False
            
            # CSVファイルを読み込み
            df = pd.read_csv(self.latest_csv)
            
            # 並列ルール適用
            console.print(Panel.fit(
                "[bold cyan]🚀 Ultra Think 並列ルール適用（サブエージェント）[/bold cyan]",
                title="並列処理開始",
                border_style="cyan"
            ))
            
            # ルール適用実行
            df_updated = apply_all_rules_to_new_data(df, use_parallel=True)
            
            if df_updated is not None:
                # 更新されたデータを保存
                df_updated.to_csv(self.latest_csv, index=False)
                
                # Google Sheetsに再同期
                if self.sheet:
                    self.sync_sheet_data()
                
                self.sync_log.append("✅ ルール適用完了")
                return True
            else:
                self.sync_log.append("ℹ️ ルール適用: 更新なし")
                return False
                
        except Exception as e:
            self.sync_log.append(f"❌ ルール適用エラー: {e}")
            traceback.print_exc()
            return False
    
    def run_startup_sync(self):
        """起動時同期を実行"""
        start_time = datetime.now()
        
        console.print(Panel.fit(
            "[bold cyan]🚀 Claude Code 起動時自動同期[/bold cyan]\n"
            "[dim]Ultra Think データベースをGoogle Sheetsと同期します[/dim]",
            title="📊 Ultra Think 自動同期",
            border_style="cyan"
        ))
        
        # 自動同期が有効かチェック
        if not self.config.get('auto_sync_enabled', True):
            console.print("[yellow]⚠️ 自動同期は無効になっています[/yellow]")
            console.print("有効にするには sheets_config.json の auto_sync_enabled を true に設定してください")
            return
        
        # 同期実行
        with console.status("[cyan]同期処理を実行中...[/cyan]", spinner="dots"):
            # 1. Google Sheets APIに接続
            if not self.init_google_client():
                self.show_results(False)
                return
            
            # 2. 最新のCSVファイルを検索
            if not self.find_latest_ultra_think_csv():
                self.show_results(False)
                return
            
            # 3. スプレッドシート名を同期
            name_synced = self.sync_sheet_name()
            
            # 4. データを同期
            data_synced = self.sync_sheet_data()
        
        # 5. Wikipedia検証（設定が有効な場合）
        wikipedia_verified = False
        if self.config.get('auto_wikipedia_verify', True) and WIKIPEDIA_VALIDATOR_AVAILABLE:
            console.print("\n[bold yellow]🔍 Wikipedia検証開始[/bold yellow]")
            wikipedia_verified = self.apply_wikipedia_verification()
        
        # 6. ルール適用（設定が有効な場合）
        rules_applied = False
        if self.config.get('auto_apply_rules', True):
            console.print("\n[bold green]🆕 新規データへのルール自動適用[/bold green]")
            rules_applied = self.apply_rules_to_data()
        
        # 処理時間
        elapsed = (datetime.now() - start_time).total_seconds()
        self.sync_log.append(f"⏱️ 処理時間: {elapsed:.2f}秒")
        
        # 結果表示
        success = name_synced or data_synced or wikipedia_verified or rules_applied
        self.show_results(success)
        
        # ブラウザ自動オープン
        if success and self.startup_config.get('startup_settings', {}).get('auto_open_browser', False):
            self.open_browser_to_sheet()
    
    def show_results(self, success):
        """同期結果を表示"""
        if success:
            panel_style = "green"
            title = "✅ 同期完了"
        else:
            panel_style = "yellow"
            title = "ℹ️ 同期状況"
        
        # ログを整形
        log_text = "\n".join(self.sync_log)
        
        # スプレッドシートのURL
        sheet_url = f"https://docs.google.com/spreadsheets/d/{self.config['spreadsheet_id']}"
        
        console.print(Panel(
            f"{log_text}\n\n[dim]スプレッドシート: {sheet_url}[/dim]",
            title=title,
            border_style=panel_style
        ))
        
        # 同期ログをファイルに保存
        self.save_sync_log()
        
        # 音声通知
        if success and self.startup_config.get('notification_settings', {}).get('audio_notifications', {}).get('enabled', False):
            self.play_notification_sound('sync_complete')
    
    def save_sync_log(self):
        """同期ログをファイルに保存"""
        log_file = Path('sync_log.json')
        
        # 既存のログを読み込み
        if log_file.exists():
            with open(log_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
        else:
            logs = []
        
        # 新しいログを追加
        logs.append({
            'timestamp': datetime.now().isoformat(),
            'csv_file': self.latest_csv,
            'log': self.sync_log
        })
        
        # 最新の10件のみ保持
        logs = logs[-10:]
        
        # 保存
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
    
    def open_browser_to_sheet(self):
        """ブラウザでGoogle Sheetsを自動オープン"""
        try:
            sheet_url = f"https://docs.google.com/spreadsheets/d/{self.config['spreadsheet_id']}"
            browser_settings = self.startup_config.get('browser_settings', {})
            
            # ブラウザ設定を取得
            wait_time = browser_settings.get('browser_wait_time', 2)
            
            console.print(f"\n[bold blue]🌐 ブラウザでスプレッドシートを開いています...[/bold blue]")
            
            # ブラウザでオープン
            webbrowser.open(sheet_url)
            
            # 少し待機
            time.sleep(wait_time)
            
            # macOSの場合、ブラウザにフォーカスを当てる
            if browser_settings.get('focus_browser_window', True) and sys.platform == 'darwin':
                try:
                    subprocess.run(['osascript', '-e', 'tell application "Safari" to activate'], 
                                   capture_output=True, timeout=5)
                except:
                    try:
                        subprocess.run(['osascript', '-e', 'tell application "Google Chrome" to activate'], 
                                       capture_output=True, timeout=5)
                    except:
                        pass  # フォーカスに失敗してもエラーにしない
            
            self.sync_log.append(f"🌐 ブラウザでスプレッドシートを開きました: {sheet_url}")
            
        except Exception as e:
            self.sync_log.append(f"⚠️ ブラウザオープンエラー: {e}")
    
    def play_notification_sound(self, notification_type):
        """通知音を再生"""
        try:
            audio_config = self.startup_config.get('notification_settings', {}).get('audio_notifications', {})
            
            if notification_type == 'sync_complete':
                sound_file = audio_config.get('sync_complete_sound', '/System/Library/Sounds/Glass.aiff')
            elif notification_type == 'error':
                sound_file = audio_config.get('error_sound', '/System/Library/Sounds/Sosumi.aiff')
            else:
                return
            
            # macOSの場合
            if sys.platform == 'darwin' and os.path.exists(sound_file):
                subprocess.run(['afplay', sound_file], capture_output=True, timeout=3)
                self.sync_log.append(f"🔊 通知音を再生: {notification_type}")
            
        except Exception as e:
            self.sync_log.append(f"⚠️ 通知音再生エラー: {e}")


def check_and_sync():
    """起動時に自動的に呼ばれるエントリーポイント"""
    syncer = StartupSync()
    syncer.run_startup_sync()


if __name__ == "__main__":
    # 直接実行された場合
    check_and_sync()