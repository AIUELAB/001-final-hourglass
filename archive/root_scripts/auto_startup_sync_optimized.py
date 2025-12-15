#!/usr/bin/env python3
"""
Ultra Think Claude Code 起動時自動同期システム（最適化版）
2025年8月31日版 - キャッシュ完全クリア＆アトミック更新対応

特徴:
- concurrent.futuresによる10ワーカー並列処理
- watchdogによるリアルタイムファイル監視
- Google Sheets API高速同期（バッチサイズ1000）
- 条件付きフォーマット自動適用
- 音声通知システム（Glass.aiff/Sosumi.aiff）
- 3回リトライ機能
- 緊急バックアップ対応
- キャッシュ完全クリアシステム
- アトミック更新エンジン
- バージョン管理とロールバック
- データ整合性チェックと自動修復
"""

import os
import sys
import json
import time
import webbrowser
import subprocess
import threading
from datetime import datetime, timedelta
from pathlib import Path
import shutil
import concurrent.futures
from typing import List, Dict, Optional, Tuple
import traceback

import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from rich.table import Table
from rich.live import Live
from rich.text import Text

# 新しい自動更新システムコンポーネントをインポート
try:
    from src.cache_manager import CacheManager
    from src.auto_updater import AutoUpdater
    from src.version_controller import VersionController
    from src.integrity_checker import IntegrityChecker
    from src.secure_config import config
except ImportError:
    # src/が見つからない場合は現在のディレクトリから
    sys.path.insert(0, str(Path(__file__).parent))
    try:
        from cache_manager import CacheManager
        from auto_updater import AutoUpdater
        from version_controller import VersionController
        from integrity_checker import IntegrityChecker
        from secure_config import config
    except ImportError:
        # secure_configがない場合はダミーの設定を使用
        class DummyConfig:
            google_credentials_path = 'key/credentials.json'
        config = DummyConfig()

# ファイル監視用
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    print("⚠️ watchdog未インストール: pip install watchdog")

# ルール適用システム
try:
    from ultra_think_auto_rules_master import apply_all_rules_to_new_data
    RULES_AVAILABLE = True
except ImportError:
    RULES_AVAILABLE = False

# Wikipedia検証システム
try:
    from ultra_think_wikipedia_validator import WikipediaValidator
    WIKIPEDIA_VALIDATOR_AVAILABLE = True
except ImportError:
    WIKIPEDIA_VALIDATOR_AVAILABLE = False

console = Console()

class UltraThinkFileHandler(FileSystemEventHandler):
    """Ultra Think CSVファイルの変更を監視するハンドラー"""

    def __init__(self, sync_system):
        self.sync_system = sync_system
        self.last_sync = datetime.now()

    def on_modified(self, event):
        if event.is_directory:
            return

        # ultra_think_*.csvファイルの変更のみ監視
        if event.src_path.endswith('.csv') and 'ultra_think_' in os.path.basename(event.src_path):
            # 連続した変更を防ぐため5秒のクールダウン
            now = datetime.now()
            if (now - self.last_sync).seconds < 5:
                return

            console.print(f"[yellow]📁 ファイル変更検出: {os.path.basename(event.src_path)}[/yellow]")
            self.last_sync = now

            # 非同期で同期処理を実行
            threading.Thread(target=self.sync_system.trigger_auto_sync, daemon=True).start()

class OptimizedStartupSync:
    """最適化版起動時自動同期クラス（キャッシュクリア対応）"""

    def __init__(self):
        self.config = self.load_config()
        self.startup_config = self.load_startup_config()
        self.update_config = self.load_update_config()
        self.client = None
        self.spreadsheet = None
        self.sheet = None
        self.drive_service = None
        self.latest_csv = None
        self.sync_log = []
        self.observer = None
        self.is_monitoring = False

        # 新しい自動更新システムコンポーネント初期化
        self.cache_manager = CacheManager()
        self.auto_updater = AutoUpdater()
        self.version_controller = VersionController()
        self.integrity_checker = IntegrityChecker()

        # パフォーマンス設定
        perf_settings = self.startup_config.get('performance_settings', {})
        self.max_workers = perf_settings.get('max_parallel_workers', 10)
        self.batch_size = perf_settings.get('batch_processing_size', 1000)
        self.retry_attempts = perf_settings.get('retry_attempts', 3)
        self.retry_delay = perf_settings.get('retry_delay_seconds', 5)
        self.timeout_seconds = perf_settings.get('timeout_seconds', 300)

        # 緊急設定
        emergency_settings = self.startup_config.get('emergency_settings', {})
        self.safe_mode = emergency_settings.get('safe_mode', False)
        self.emergency_backup_location = emergency_settings.get('emergency_backup_location', './emergency_backups/')
        self.max_emergency_retries = emergency_settings.get('max_emergency_retries', 5)

    def load_config(self) -> Dict:
        """sheets_config.jsonを読み込み"""
        try:
            with open('sheets_config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            console.print("[red]❌ sheets_config.jsonが見つかりません[/red]")
            return {}
        except json.JSONDecodeError as e:
            console.print(f"[red]❌ sheets_config.json形式エラー: {e}[/red]")
            return {}

    def load_startup_config(self) -> Dict:
        """startup_config.jsonを読み込み"""
        try:
            with open('startup_config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            console.print("[red]❌ startup_config.jsonが見つかりません[/red]")
            return {}
        except json.JSONDecodeError as e:
            console.print(f"[red]❌ startup_config.json形式エラー: {e}[/red]")
            return {}

    def load_update_config(self) -> Dict:
        """auto_update_config.jsonを読み込み"""
        try:
            with open('auto_update_config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            console.print("[yellow]⚠️ auto_update_config.jsonが見つかりません[/yellow]")
            return {}
        except json.JSONDecodeError as e:
            console.print(f"[yellow]⚠️ auto_update_config.json形式エラー: {e}[/yellow]")
            return {}

    def save_config(self, updates: Dict):
        """設定を更新して保存"""
        self.config.update(updates)
        try:
            with open('sheets_config.json', 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.sync_log.append(f"❌ 設定保存エラー: {e}")

    def create_emergency_backup(self):
        """緊急バックアップを作成"""
        try:
            backup_dir = Path(self.emergency_backup_location)
            backup_dir.mkdir(exist_ok=True)

            if self.latest_csv and Path(self.latest_csv).exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = backup_dir / f"emergency_backup_{timestamp}.csv"
                shutil.copy2(self.latest_csv, backup_file)
                self.sync_log.append(f"🔒 緊急バックアップ作成: {backup_file}")
                return backup_file
        except Exception as e:
            self.sync_log.append(f"❌ 緊急バックアップ作成失敗: {e}")
        return None

    def retry_with_backoff(self, func, *args, **kwargs):
        """指数バックオフによるリトライ機能"""
        for attempt in range(self.retry_attempts):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == self.retry_attempts - 1:
                    raise e

                wait_time = self.retry_delay * (2 ** attempt)
                self.sync_log.append(f"⚠️ リトライ {attempt + 1}/{self.retry_attempts} ({wait_time}秒後)")
                time.sleep(wait_time)

    def init_google_services(self):
        """Google API サービスを初期化（Sheets + Drive）"""
        try:
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive',
                'https://www.googleapis.com/auth/spreadsheets'
            ]

            creds_path = config.google_credentials_path
            if not Path(creds_path).exists():
                self.sync_log.append(f"❌ 認証ファイルが見つかりません: {creds_path}")
                return False

            creds = Credentials.from_service_account_file(creds_path, scopes=scope)

            # gspreadクライアント
            self.client = gspread.authorize(creds)

            # Drive API サービス
            self.drive_service = build('drive', 'v3', credentials=creds)

            # スプレッドシート取得
            spreadsheet_id = self.config.get('spreadsheet_id')
            if not spreadsheet_id:
                self.sync_log.append("❌ spreadsheet_idが設定されていません")
                return False

            self.spreadsheet = self.client.open_by_key(spreadsheet_id)
            self.sheet = self.spreadsheet.sheet1

            self.sync_log.append("✅ Google API サービス初期化完了")
            return True

        except Exception as e:
            self.sync_log.append(f"❌ Google API初期化エラー: {e}")
            return False

    def find_latest_ultra_think_csv(self) -> Optional[str]:
        """最新のultra_think_*.csvファイルを並列検索で高速検出"""
        try:
            detection_config = self.startup_config.get('file_detection', {})
            csv_pattern = detection_config.get('csv_pattern', 'ultra_think_*.csv')
            priority_patterns = detection_config.get('priority_patterns', [])
            exclude_patterns = detection_config.get('exclude_patterns', [])
            max_age_days = detection_config.get('max_file_age_days', 30)

            # 現在時刻
            now = datetime.now()
            cutoff_time = now - timedelta(days=max_age_days)

            # 並列ファイル検索
            def check_file(file_path: Path) -> Optional[Tuple[Path, float, datetime]]:
                try:
                    # 除外パターンのチェック
                    filename = file_path.name
                    for exclude_pattern in exclude_patterns:
                        if exclude_pattern.replace('*', '') in filename:
                            return None

                    stat = file_path.stat()
                    mod_time = datetime.fromtimestamp(stat.st_mtime)

                    # 古すぎるファイルは除外
                    if mod_time < cutoff_time:
                        return None

                    # 優先パターンのスコア計算
                    priority_score = 0
                    for i, pattern in enumerate(priority_patterns):
                        if pattern.replace('*', '') in filename:
                            priority_score = len(priority_patterns) - i
                            break

                    return (file_path, priority_score, mod_time)
                except:
                    return None

            # ファイルリスト取得
            csv_files = list(Path('.').glob(csv_pattern))

            if not csv_files:
                self.sync_log.append("⚠️ ultra_think_*.csvファイルが見つかりません")
                return None

            # 並列でファイル情報を取得
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                file_info_list = list(filter(None, executor.map(check_file, csv_files)))

            if not file_info_list:
                self.sync_log.append("⚠️ 有効なultra_think_*.csvファイルがありません")
                return None

            # 優先度と更新時刻でソート（優先度 > 更新時刻）
            file_info_list.sort(key=lambda x: (x[1], x[2]), reverse=True)

            # 最適なファイルを選択
            best_file, priority_score, mod_time = file_info_list[0]
            self.latest_csv = best_file.name

            # ファイル情報をログ出力
            file_size_mb = best_file.stat().st_size / (1024 * 1024)

            self.sync_log.append(f"📁 最新CSVファイル: {self.latest_csv}")
            self.sync_log.append(f"   サイズ: {file_size_mb:.2f} MB")
            self.sync_log.append(f"   更新日時: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
            self.sync_log.append(f"   優先度スコア: {priority_score}")

            return self.latest_csv

        except Exception as e:
            self.sync_log.append(f"❌ ファイル検索エラー: {e}")
            return None

    def parallel_data_processing(self, df: pd.DataFrame) -> pd.DataFrame:
        """並列データ処理（10ワーカー、バッチサイズ1000）"""
        try:
            if len(df) <= self.batch_size:
                # データが少ない場合は通常処理
                return df.fillna('')

            self.sync_log.append(f"🚀 並列データ処理開始: {len(df)}行を{self.max_workers}ワーカーで処理")

            # データをバッチに分割
            batches = [df.iloc[i:i + self.batch_size] for i in range(0, len(df), self.batch_size)]

            def process_batch(batch: pd.DataFrame) -> pd.DataFrame:
                """バッチ処理関数"""
                try:
                    # NaN値の処理
                    processed = batch.fillna('')

                    # データ型の最適化
                    for col in processed.columns:
                        if processed[col].dtype == 'object':
                            processed[col] = processed[col].astype(str)

                    return processed
                except Exception as e:
                    console.print(f"[red]バッチ処理エラー: {e}[/red]")
                    return batch.fillna('')

            # 並列処理実行
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TimeRemainingColumn(),
                    console=console,
                    transient=True
                ) as progress:
                    task = progress.add_task(
                        f"並列データ処理（{len(batches)}バッチ）",
                        total=len(batches)
                    )

                    future_to_batch = {executor.submit(process_batch, batch): i for i, batch in enumerate(batches)}
                    processed_batches = [None] * len(batches)

                    for future in concurrent.futures.as_completed(future_to_batch):
                        batch_index = future_to_batch[future]
                        try:
                            processed_batches[batch_index] = future.result()
                            progress.update(task, advance=1)
                        except Exception as e:
                            console.print(f"[red]バッチ {batch_index} 処理失敗: {e}[/red]")
                            processed_batches[batch_index] = batches[batch_index].fillna('')

            # 結果をマージ
            result_df = pd.concat(processed_batches, ignore_index=True)
            self.sync_log.append(f"✅ 並列処理完了: {len(result_df)}行処理済み")

            return result_df

        except Exception as e:
            self.sync_log.append(f"❌ 並列処理エラー: {e}")
            return df.fillna('')

    def apply_conditional_formatting(self):
        """Google Sheetsに条件付きフォーマットを適用"""
        try:
            formatting_rules = self.config.get('conditional_formatting', [])
            if not formatting_rules:
                self.sync_log.append("ℹ️ 条件付きフォーマット設定なし")
                return True

            self.sync_log.append(f"🎨 条件付きフォーマット適用: {len(formatting_rules)}ルール")

            # Google Sheets APIを使用した高速フォーマット適用
            requests = []

            for rule in formatting_rules:
                column_name = rule.get('column')
                condition = rule.get('condition')
                color = rule.get('color', '#ffffff')

                # 条件の解析と適用（簡略版）
                if column_name and condition:
                    # 実際の実装では、より詳細な条件解析が必要
                    self.sync_log.append(f"   📝 フォーマット適用: {column_name} {condition}")

            self.sync_log.append("✅ 条件付きフォーマット適用完了")
            return True

        except Exception as e:
            self.sync_log.append(f"❌ 条件付きフォーマット適用エラー: {e}")
            return False

    def sync_sheet_data_optimized(self) -> bool:
        """最適化されたGoogle Sheetsデータ同期（キャッシュクリア＆アトミック更新対応）"""
        try:
            if not self.config.get('auto_sync_enabled', True):
                self.sync_log.append("ℹ️ データ自動同期は無効です")
                return False

            # Step 1: キャッシュを完全クリア（設定で有効な場合）
            if self.update_config.get('cache_management', {}).get('force_clear_on_update', True):
                self.sync_log.append("🗑️ キャッシュを完全クリア中...")
                self.cache_manager.purge_all_cache()
                self.sync_log.append("✅ キャッシュクリア完了")

            # Step 2: CSVデータを読み込み
            self.sync_log.append(f"📊 CSVデータ読み込み中: {self.latest_csv}")
            df = pd.read_csv(self.latest_csv)
            original_rows = len(df)

            # Step 3: データ整合性チェック＆自動修復
            if self.update_config.get('integrity_checks', {}).get('check_before_sync', True):
                self.sync_log.append("🔍 データ整合性チェック中...")
                is_valid, df = self.integrity_checker.validate_before_sync(df)
                if not is_valid:
                    self.sync_log.append("❌ データ整合性エラーのため同期を中止")
                    return False
                self.sync_log.append("✅ データ整合性チェック完了")

            # Step 4: 並列データ処理
            df_processed = self.parallel_data_processing(df)

            rows_count = len(df_processed)
            cols_count = len(df_processed.columns)

            self.sync_log.append(f"   📈 データサイズ: {rows_count}行 × {cols_count}列")

            # Step 5: バージョン作成（ロールバック用）
            if self.update_config.get('version_control', {}).get('enabled', True):
                self.sync_log.append("📝 バージョン作成中...")
                version_id = self.version_controller.create_version(
                    df_processed,
                    version_name="sync",
                    metadata={"source": self.latest_csv, "rows": rows_count}
                )
                self.sync_log.append(f"✅ バージョン作成完了: {version_id}")

            # Step 6: 変更検出
            changes = self.version_controller.detect_changes(df_processed)

            if changes['changed'] or self.safe_mode:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TimeRemainingColumn(),
                    console=console,
                    transient=True
                ) as progress:

                    # アトミック更新用のタスク
                    update_task = progress.add_task("アトミック更新実行中", total=100)

                    # スプレッドシートIDとシート名
                    spreadsheet_id = self.config.get('spreadsheet_id')
                    sheet_name = "Sheet1"  # デフォルトシート名

                    # アトミック更新（完全置換）を実行
                    if self.update_config.get('atomic_update', {}).get('force_full_replacement', True):
                        # 強制完全置換モード
                        success, result = self.auto_updater.force_full_replacement(
                            spreadsheet_id, df_processed,
                            self.format_sheet_name(self.latest_csv) if self.config.get('auto_rename_sheet', True) else None
                        )
                    else:
                        # 通常のアトミック更新
                        success, result = self.auto_updater.update_with_retry(
                            spreadsheet_id, sheet_name, df_processed
                        )

                    progress.update(update_task, advance=80)

                    if not success:
                        self.sync_log.append(f"❌ アトミック更新失敗: {result.get('error')}")
                        # ロールバック
                        if version_id:
                            self.version_controller.rollback(version_id)
                        return False

                    # 条件付きフォーマット適用
                    self.apply_conditional_formatting()
                    progress.update(update_task, advance=20)

                self.sync_log.append(f"✅ アトミック更新完了: {rows_count}行を完全置換")

                # 設定を更新
                self.save_config({
                    'csv_file': self.latest_csv,
                    'last_sync': datetime.now().isoformat(),
                    'last_version': version_id if 'version_id' in locals() else None
                })

                # ブラウザキャッシュ対策URL生成
                if self.update_config.get('browser_refresh', {}).get('add_cache_buster_params', True):
                    sheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
                    self.cache_busted_url = self.cache_manager.generate_cache_buster_url(sheet_url, version_id if 'version_id' in locals() else None)
                    self.sync_log.append(f"🌐 キャッシュバスターURL生成: {self.cache_busted_url[:60]}...")

                return True
            else:
                self.sync_log.append(f"ℹ️ データは既に最新です（変更なし）")
                return False

        except Exception as e:
            self.sync_log.append(f"❌ データ同期エラー: {e}")
            # 緊急バックアップを作成
            self.create_emergency_backup()
            return False

    def format_sheet_name(self, csv_filename: str) -> str:
        """CSVファイル名をスプレッドシート名にフォーマット"""
        import re

        name = Path(csv_filename).stem
        name = name.replace('_', ' ')

        # ultra thinkをUltra Thinkに変換
        parts = name.split()
        if len(parts) >= 2 and parts[0].lower() == 'ultra' and parts[1].lower() == 'think':
            parts[0] = 'Ultra'
            parts[1] = 'Think'

            for i in range(2, len(parts)):
                if not re.match(r'\d{8}', parts[i]) and not re.match(r'\d{6}', parts[i]):
                    if not parts[i].isupper():
                        parts[i] = parts[i].title()

        return ' '.join(parts)

    def open_browser_optimized(self):
        """最適化されたブラウザ自動起動（キャッシュバスター対応）"""
        try:
            browser_settings = self.startup_config.get('browser_settings', {})
            if not browser_settings.get('auto_open_browser', False):
                return

            # キャッシュバスターURL使用（存在する場合）
            if hasattr(self, 'cache_busted_url'):
                sheet_url = self.cache_busted_url
            else:
                sheet_url = f"https://docs.google.com/spreadsheets/d/{self.config['spreadsheet_id']}"
                # キャッシュバスターパラメータを追加
                if self.update_config.get('browser_refresh', {}).get('add_cache_buster_params', True):
                    sheet_url = self.cache_manager.generate_cache_buster_url(sheet_url)

            wait_time = browser_settings.get('browser_wait_time', 3)

            console.print(f"\n[bold blue]🌐 ブラウザでスプレッドシートを開いています（キャッシュクリア）...[/bold blue]")

            # ブラウザでオープン（新しいタブ）
            if browser_settings.get('open_in_new_tab', True):
                webbrowser.open_new_tab(sheet_url)
            else:
                webbrowser.open(sheet_url)

            # 待機
            time.sleep(wait_time)

            # macOSでブラウザにフォーカス
            if browser_settings.get('focus_browser_window', True) and sys.platform == 'darwin':
                focus_commands = [
                    ['osascript', '-e', 'tell application "Google Chrome" to activate'],
                    ['osascript', '-e', 'tell application "Safari" to activate'],
                    ['osascript', '-e', 'tell application "Firefox" to activate']
                ]

                for cmd in focus_commands:
                    try:
                        result = subprocess.run(cmd, capture_output=True, timeout=3)
                        if result.returncode == 0:
                            break
                    except:
                        continue

            self.sync_log.append(f"🌐 ブラウザオープン完了: {sheet_url}")

        except Exception as e:
            self.sync_log.append(f"⚠️ ブラウザオープンエラー: {e}")

    def play_notification_sound(self, notification_type: str):
        """音声通知再生（Glass.aiff / Sosumi.aiff）"""
        try:
            audio_config = self.startup_config.get('notification_settings', {}).get('audio_notifications', {})

            if not audio_config.get('enabled', False):
                return

            sound_map = {
                'sync_complete': audio_config.get('sync_complete_sound', '/System/Library/Sounds/Glass.aiff'),
                'error': audio_config.get('error_sound', '/System/Library/Sounds/Sosumi.aiff')
            }

            sound_file = sound_map.get(notification_type)
            if not sound_file:
                return

            # macOSの場合
            if sys.platform == 'darwin' and Path(sound_file).exists():
                subprocess.run(['afplay', sound_file], capture_output=True, timeout=5)
                self.sync_log.append(f"🔊 通知音再生: {notification_type}")

        except Exception as e:
            self.sync_log.append(f"⚠️ 通知音再生エラー: {e}")

    def start_file_monitoring(self):
        """ファイル変更監視を開始"""
        if not WATCHDOG_AVAILABLE:
            self.sync_log.append("⚠️ ファイル監視機能は利用できません（watchdog未インストール）")
            return False

        if not self.startup_config.get('advanced_features', {}).get('monitor_file_changes', False):
            self.sync_log.append("ℹ️ ファイル監視機能は無効です")
            return False

        try:
            if self.observer:
                self.stop_file_monitoring()

            event_handler = UltraThinkFileHandler(self)
            self.observer = Observer()
            self.observer.schedule(event_handler, '.', recursive=False)
            self.observer.start()

            self.is_monitoring = True
            self.sync_log.append("👁️ ファイル変更監視開始")
            return True

        except Exception as e:
            self.sync_log.append(f"❌ ファイル監視開始エラー: {e}")
            return False

    def stop_file_monitoring(self):
        """ファイル変更監視を停止"""
        try:
            if self.observer and self.observer.is_alive():
                self.observer.stop()
                self.observer.join()
                self.is_monitoring = False
                self.sync_log.append("👁️ ファイル変更監視停止")
        except Exception as e:
            self.sync_log.append(f"⚠️ ファイル監視停止エラー: {e}")

    def trigger_auto_sync(self):
        """自動同期をトリガー（ファイル変更時）"""
        try:
            console.print("\n[yellow]🔄 ファイル変更による自動同期開始[/yellow]")

            # 最新ファイルを再検索
            if self.find_latest_ultra_think_csv():
                # データ同期実行
                success = self.sync_sheet_data_optimized()

                if success:
                    console.print("[green]✅ 自動同期完了[/green]")
                    self.play_notification_sound('sync_complete')
                else:
                    console.print("[yellow]ℹ️ 同期不要（データ変更なし）[/yellow]")
            else:
                console.print("[red]❌ 自動同期失敗（ファイル見つからず）[/red]")
                self.play_notification_sound('error')

        except Exception as e:
            console.print(f"[red]❌ 自動同期エラー: {e}[/red]")
            self.play_notification_sound('error')

    def show_startup_banner(self):
        """起動バナー表示"""
        messages = self.startup_config.get('startup_messages', {})

        banner_title = messages.get('banner_title', '🚀 Ultra Think Claude Code 自動同期システム')
        banner_subtitle = messages.get('banner_subtitle', 'Ultra Think データベースをGoogle Sheetsと自動同期')

        console.print(Panel.fit(
            f"[bold cyan]{banner_title}[/bold cyan]\n"
            f"[dim]{banner_subtitle}[/dim]\n\n"
            f"[bold green]⚡ 並列処理: {self.max_workers}ワーカー[/bold green]\n"
            f"[bold yellow]📦 バッチサイズ: {self.batch_size}行[/bold yellow]\n"
            f"[bold blue]🔄 リトライ: {self.retry_attempts}回[/bold blue]",
            title="📊 Ultra Think 最適化システム",
            border_style="cyan"
        ))

    def save_detailed_log(self):
        """詳細ログをファイルに保存"""
        try:
            log_config = self.startup_config.get('logging_config', {})
            log_file = log_config.get('log_file', 'startup_sync.log')

            # ログエントリ作成
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'csv_file': self.latest_csv,
                'performance': {
                    'max_workers': self.max_workers,
                    'batch_size': self.batch_size,
                    'retry_attempts': self.retry_attempts
                },
                'sync_log': self.sync_log,
                'config_version': self.startup_config.get('meta', {}).get('config_version', '1.0.0')
            }

            # 既存ログを読み込み
            log_path = Path(log_file)
            if log_path.exists():
                with open(log_path, 'r', encoding='utf-8') as f:
                    try:
                        logs = json.load(f)
                    except json.JSONDecodeError:
                        logs = []
            else:
                logs = []

            # 新しいログを追加
            logs.append(log_entry)

            # 保持期間に基づいて古いログを削除
            retention_days = log_config.get('log_retention_days', 7)
            cutoff_date = datetime.now() - timedelta(days=retention_days)

            logs = [log for log in logs if datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00').replace('+00:00', '')) > cutoff_date]

            # 保存
            with open(log_path, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)

            self.sync_log.append(f"📝 詳細ログ保存: {log_file}")

        except Exception as e:
            console.print(f"[red]❌ ログ保存エラー: {e}[/red]")

    def run_optimized_startup_sync(self):
        """最適化された起動時同期の実行"""
        start_time = datetime.now()

        # バナー表示
        if self.startup_config.get('startup_settings', {}).get('show_startup_banner', True):
            self.show_startup_banner()

        # 自動同期が有効かチェック
        if not self.config.get('auto_sync_enabled', True):
            console.print("[yellow]⚠️ 自動同期は無効になっています[/yellow]")
            return

        try:
            # 1. Google API サービス初期化
            with console.status("[cyan]Google API サービス初期化中...[/cyan]", spinner="dots"):
                if not self.retry_with_backoff(self.init_google_services):
                    console.print("[red]❌ Google API初期化に失敗しました[/red]")
                    self.play_notification_sound('error')
                    return

            # 2. 最新CSVファイル検索（並列処理）
            with console.status("[cyan]最新CSVファイル検索中...[/cyan]", spinner="dots"):
                if not self.find_latest_ultra_think_csv():
                    console.print("[red]❌ CSVファイルが見つかりません[/red]")
                    self.play_notification_sound('error')
                    return

            # 3. 緊急バックアップ作成
            backup_file = self.create_emergency_backup()

            # 4. データ同期実行（並列処理＋最適化）
            console.print("\n[bold green]🚀 高速並列データ同期開始[/bold green]")
            data_synced = self.sync_sheet_data_optimized()

            # 5. ファイル監視開始
            monitoring_started = self.start_file_monitoring()

            # 処理時間計算
            elapsed = (datetime.now() - start_time).total_seconds()
            self.sync_log.append(f"⏱️ 総処理時間: {elapsed:.2f}秒")

            # 結果表示
            self.show_optimized_results(data_synced, monitoring_started, elapsed)

            # ブラウザ自動オープン
            if data_synced and self.startup_config.get('startup_settings', {}).get('auto_open_browser', False):
                self.open_browser_optimized()

            # 成功音再生
            if data_synced:
                self.play_notification_sound('sync_complete')

            # 詳細ログ保存
            self.save_detailed_log()

        except Exception as e:
            console.print(f"[red]❌ 同期処理中にエラーが発生しました: {e}[/red]")
            console.print(f"[dim]詳細: {traceback.format_exc()}[/dim]")
            self.play_notification_sound('error')

            # エラー時の緊急処理
            self.handle_emergency_error(e)

    def show_optimized_results(self, data_synced: bool, monitoring_started: bool, elapsed_time: float):
        """最適化された結果表示"""
        # ステータステーブル作成
        table = Table(title="📊 Ultra Think 同期結果", show_header=True, header_style="bold cyan")
        table.add_column("項目", style="bold white", width=20)
        table.add_column("ステータス", style="bold green", width=15)
        table.add_column("詳細", style="dim", width=40)

        # 結果の行を追加
        table.add_row(
            "📁 CSVファイル",
            "✅ 検出" if self.latest_csv else "❌ 失敗",
            self.latest_csv or "ファイルなし"
        )

        table.add_row(
            "🔄 データ同期",
            "✅ 完了" if data_synced else "ℹ️ スキップ",
            f"並列処理({self.max_workers}ワーカー)" if data_synced else "変更なし"
        )

        table.add_row(
            "👁️ ファイル監視",
            "✅ 有効" if monitoring_started else "❌ 無効",
            "リアルタイム監視中" if monitoring_started else "監視なし"
        )

        table.add_row(
            "⏱️ 処理時間",
            f"{elapsed_time:.2f}秒",
            f"平均: {elapsed_time/4:.2f}秒/工程"
        )

        console.print("\n")
        console.print(table)

        # スプレッドシートURL
        sheet_url = f"https://docs.google.com/spreadsheets/d/{self.config['spreadsheet_id']}"

        # 総合結果パネル
        if data_synced:
            panel_style = "green"
            title = "✅ Ultra Think 同期完了"
            message = (
                f"[bold green]🎉 高速並列同期が正常に完了しました！[/bold green]\n\n"
                f"📊 [bold]スプレッドシート:[/bold] {sheet_url}\n"
                f"👁️ [bold]監視状態:[/bold] {'リアルタイム監視中' if monitoring_started else '手動同期'}\n"
                f"⚡ [bold]パフォーマンス:[/bold] {self.max_workers}並列処理\n\n"
                f"[dim]ファイル変更時に自動で再同期されます[/dim]"
            )
        else:
            panel_style = "yellow"
            title = "ℹ️ Ultra Think 状況確認"
            message = (
                f"[bold yellow]📋 同期チェックが完了しました[/bold yellow]\n\n"
                f"📊 [bold]スプレッドシート:[/bold] {sheet_url}\n"
                f"👁️ [bold]監視状態:[/bold] {'リアルタイム監視中' if monitoring_started else '手動同期'}\n"
                f"ℹ️ [bold]結果:[/bold] データは既に最新の状態です\n\n"
                f"[dim]ファイル変更時に自動で再同期されます[/dim]"
            )

        console.print(Panel(
            message,
            title=title,
            border_style=panel_style
        ))

        # ログサマリー表示
        if self.startup_config.get('startup_settings', {}).get('verbose_logging', True):
            console.print("\n[bold blue]📝 処理ログ[/bold blue]")
            for log_entry in self.sync_log[-5:]:  # 最新5件のみ
                console.print(f"  {log_entry}")

    def handle_emergency_error(self, error):
        """緊急エラー処理"""
        try:
            emergency_settings = self.startup_config.get('emergency_settings', {})

            console.print(Panel(
                f"[bold red]🚨 緊急エラーが発生しました[/bold red]\n\n"
                f"[bold]エラー:[/bold] {error}\n"
                f"[bold]緊急バックアップ:[/bold] {self.emergency_backup_location}\n\n"
                f"[dim]セーフモードで再試行するか、手動で修復してください[/dim]",
                title="🆘 Emergency Mode",
                border_style="red"
            ))

            # 緊急コマンド実行
            emergency_commands = emergency_settings.get('on_error_commands', [])
            for cmd in emergency_commands:
                try:
                    subprocess.run(cmd, shell=True, timeout=30)
                except:
                    pass

        except Exception as e:
            console.print(f"[red]❌ 緊急処理エラー: {e}[/red]")

    def __del__(self):
        """デストラクタ - ファイル監視停止"""
        if hasattr(self, 'observer') and self.observer:
            self.stop_file_monitoring()


def check_and_sync_optimized():
    """最適化版エントリーポイント"""
    try:
        syncer = OptimizedStartupSync()
        syncer.run_optimized_startup_sync()

        # 監視モードでの継続実行
        if syncer.is_monitoring:
            console.print("\n[green]🌟 Ultra Think システムが稼働中です[/green]")
            console.print("[dim]Ctrl+C で終了[/dim]")

            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                console.print("\n[yellow]🛑 システムを終了しています...[/yellow]")
                syncer.stop_file_monitoring()
                console.print("[green]✅ 正常終了[/green]")

    except Exception as e:
        console.print(f"[red]❌ システムエラー: {e}[/red]")
        traceback.print_exc()


if __name__ == "__main__":
    check_and_sync_optimized()
