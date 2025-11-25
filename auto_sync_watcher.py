#!/usr/bin/env python3
"""
Ultra Think 自動同期監視システム
ファイル変更を検知して自動的にGoogle Sheetsと同期

作成日: 2025-08-31
"""

import os
import sys
import time
import subprocess
import json
from pathlib import Path
from datetime import datetime, timedelta
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading
import hashlib


class UltraThinkSyncWatcher(FileSystemEventHandler):
    """Ultra Think CSVファイルの変更を監視して自動同期"""

    def __init__(self):
        self.last_sync_time = None
        self.sync_cooldown = 5  # 5秒のクールダウン
        self.sync_lock = threading.Lock()
        self.file_hashes = {}
        self.sync_queue = set()
        self.sync_timer = None

        # 設定読み込み
        self.load_config()

        print("=" * 60)
        print("🔍 Ultra Think 自動同期監視システム起動")
        print("=" * 60)
        print(f"📁 監視対象: ultra_think_*.csv")
        print(f"⏱️ クールダウン: {self.sync_cooldown}秒")
        print(f"🔄 同期スクリプト: direct_sync.py")
        print("=" * 60)
        print("👁️ ファイル監視を開始しました...")
        print("   (Ctrl+C で終了)")
        print()

    def load_config(self):
        """設定ファイルを読み込み"""
        config_file = Path("auto_sync_config.json")

        default_config = {
            "watch_patterns": ["ultra_think_*.csv"],
            "exclude_patterns": ["*_backup_*.csv", "*_temp_*.csv"],
            "sync_cooldown": 5,
            "sync_script": "direct_sync.py",
            "auto_backup": True,
            "max_backups": 5,
            "notification_sound": True
        }

        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    loaded_config = json.load(f)
                    default_config.update(loaded_config)
            except Exception as e:
                print(f"⚠️ 設定ファイル読み込みエラー: {e}")

        # 設定を保存
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)

        self.config = default_config
        self.sync_cooldown = self.config.get("sync_cooldown", 5)

    def calculate_file_hash(self, filepath):
        """ファイルのハッシュ値を計算"""
        try:
            with open(filepath, 'rb') as f:
                file_hash = hashlib.md5()
                while chunk := f.read(8192):
                    file_hash.update(chunk)
            return file_hash.hexdigest()
        except:
            return None

    def is_ultra_think_csv(self, filepath):
        """Ultra Think CSVファイルかどうかを判定"""
        path = Path(filepath)

        # パターンマッチング
        for pattern in self.config.get("watch_patterns", ["ultra_think_*.csv"]):
            if path.match(pattern):
                # 除外パターンをチェック
                for exclude in self.config.get("exclude_patterns", []):
                    if path.match(exclude):
                        return False
                return True
        return False

    def on_modified(self, event):
        """ファイル変更イベント"""
        if event.is_directory:
            return

        if self.is_ultra_think_csv(event.src_path):
            self.handle_file_change(event.src_path, "modified")

    def on_created(self, event):
        """ファイル作成イベント"""
        if event.is_directory:
            return

        if self.is_ultra_think_csv(event.src_path):
            self.handle_file_change(event.src_path, "created")

    def on_moved(self, event):
        """ファイル移動イベント"""
        if event.is_directory:
            return

        if self.is_ultra_think_csv(event.dest_path):
            self.handle_file_change(event.dest_path, "moved")

    def handle_file_change(self, filepath, event_type):
        """ファイル変更を処理"""
        path = Path(filepath)

        # ファイルが存在しない場合はスキップ
        if not path.exists():
            return

        # ハッシュ値をチェック（実際の変更があったか確認）
        new_hash = self.calculate_file_hash(filepath)
        old_hash = self.file_hashes.get(filepath)

        if new_hash == old_hash:
            return  # 実際の変更なし

        self.file_hashes[filepath] = new_hash

        # 変更を記録
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] 📝 ファイル{event_type}: {path.name}")

        # 同期キューに追加
        self.sync_queue.add(filepath)

        # タイマーをリセット（デバウンス処理）
        if self.sync_timer:
            self.sync_timer.cancel()

        self.sync_timer = threading.Timer(self.sync_cooldown, self.execute_sync)
        self.sync_timer.start()
        print(f"   ⏳ {self.sync_cooldown}秒後に同期を実行します...")

    def execute_sync(self):
        """同期を実行"""
        with self.sync_lock:
            if not self.sync_queue:
                return

            # クールダウンチェック
            if self.last_sync_time:
                elapsed = (datetime.now() - self.last_sync_time).total_seconds()
                if elapsed < self.sync_cooldown:
                    wait_time = self.sync_cooldown - elapsed
                    print(f"   ⏳ クールダウン中... {wait_time:.1f}秒待機")
                    time.sleep(wait_time)

            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"\n[{timestamp}] 🔄 同期を開始します...")
            print("=" * 60)

            # バックアップ作成（設定が有効な場合）
            if self.config.get("auto_backup", True):
                self.create_backup()

            # 同期スクリプトを実行
            sync_script = self.config.get("sync_script", "direct_sync.py")

            try:
                # サブプロセスで同期スクリプトを実行
                result = subprocess.run(
                    [sys.executable, sync_script],
                    capture_output=True,
                    text=True,
                    timeout=120  # 2分のタイムアウト
                )

                if result.returncode == 0:
                    print(f"[{timestamp}] ✅ 同期が正常に完了しました！")

                    # 成功音を再生
                    if self.config.get("notification_sound", True):
                        os.system("afplay /System/Library/Sounds/Glass.aiff 2>/dev/null &")

                    # 同期ログを記録
                    self.log_sync_result("success", list(self.sync_queue))

                else:
                    print(f"[{timestamp}] ❌ 同期エラー: {result.stderr}")

                    # エラー音を再生
                    if self.config.get("notification_sound", True):
                        os.system("afplay /System/Library/Sounds/Sosumi.aiff 2>/dev/null &")

                    self.log_sync_result("error", list(self.sync_queue), result.stderr)

            except subprocess.TimeoutExpired:
                print(f"[{timestamp}] ⚠️ 同期タイムアウト")
                self.log_sync_result("timeout", list(self.sync_queue))

            except Exception as e:
                print(f"[{timestamp}] ❌ 同期実行エラー: {e}")
                self.log_sync_result("error", list(self.sync_queue), str(e))

            finally:
                # クリーンアップ
                self.sync_queue.clear()
                self.last_sync_time = datetime.now()

                print("=" * 60)
                print("👁️ ファイル監視を継続中...")
                print()

    def create_backup(self):
        """バックアップを作成"""
        try:
            # 最新のultra_think_*.csvを検索
            csv_files = list(Path('.').glob('ultra_think_*.csv'))
            if not csv_files:
                return

            latest_csv = max(csv_files, key=lambda f: f.stat().st_mtime)

            # バックアップディレクトリ作成
            backup_dir = Path("backups")
            backup_dir.mkdir(exist_ok=True)

            # バックアップファイル名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{latest_csv.stem}_{timestamp}.csv"
            backup_path = backup_dir / backup_name

            # コピー
            import shutil
            shutil.copy2(latest_csv, backup_path)

            print(f"   💾 バックアップ作成: {backup_name}")

            # 古いバックアップを削除
            self.cleanup_old_backups(backup_dir)

        except Exception as e:
            print(f"   ⚠️ バックアップエラー: {e}")

    def cleanup_old_backups(self, backup_dir):
        """古いバックアップを削除"""
        try:
            max_backups = self.config.get("max_backups", 5)

            # バックアップファイルを取得
            backup_files = sorted(
                backup_dir.glob("backup_*.csv"),
                key=lambda f: f.stat().st_mtime,
                reverse=True
            )

            # 古いファイルを削除
            if len(backup_files) > max_backups:
                for old_file in backup_files[max_backups:]:
                    old_file.unlink()
                    print(f"   🗑️ 古いバックアップを削除: {old_file.name}")

        except Exception as e:
            print(f"   ⚠️ バックアップクリーンアップエラー: {e}")

    def log_sync_result(self, status, files, error=None):
        """同期結果をログに記録"""
        try:
            log_file = Path("auto_sync_log.json")

            if log_file.exists():
                with open(log_file, "r", encoding="utf-8") as f:
                    logs = json.load(f)
            else:
                logs = []

            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "status": status,
                "files": [Path(f).name for f in files],
                "error": error
            }

            logs.append(log_entry)
            logs = logs[-50:]  # 最新50件のみ保持

            with open(log_file, "w", encoding="utf-8") as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)

        except Exception as e:
            print(f"   ⚠️ ログ記録エラー: {e}")


def main():
    """メイン実行"""
    # watchdogの確認
    try:
        from watchdog.observers import Observer
    except ImportError:
        print("❌ watchdogがインストールされていません")
        print("以下のコマンドでインストールしてください:")
        print("pip install watchdog")
        return 1

    # 監視設定
    event_handler = UltraThinkSyncWatcher()
    observer = Observer()

    # カレントディレクトリを監視
    observer.schedule(event_handler, '.', recursive=False)

    # 監視開始
    observer.start()

    try:
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\n🛑 監視を終了しています...")
        observer.stop()
        print("✅ 正常終了")

    observer.join()
    return 0


if __name__ == "__main__":
    sys.exit(main())
