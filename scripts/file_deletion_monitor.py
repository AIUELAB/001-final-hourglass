#!/usr/bin/env python3
"""
ファイル削除監視スクリプト

このスクリプトは、指定されたディレクトリのファイル削除を監視し、
削除が検出された場合に自動的にIDEキャッシュクリアを実行します。
"""

import os
import time
import json
import logging
from pathlib import Path
from typing import Set, Dict, List, Any
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from clear_ide_cache import IDECacheCleaner

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('file_deletion_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FileDeletionHandler(FileSystemEventHandler):
    """ファイル削除イベントハンドラー"""

    def __init__(self, cache_cleaner: IDECacheCleaner, auto_restart: bool = False):
        self.cache_cleaner = cache_cleaner
        self.auto_restart = auto_restart
        self.deleted_files: Set[str] = set()
        self.last_cleanup_time: float = 0.0
        self.cleanup_cooldown = 30  # 30秒のクールダウン

    def on_deleted(self, event):
        """ファイル削除時の処理"""
        if event.is_directory:
            return

        file_path = event.src_path
        current_time = time.time()

        logger.info(f"ファイル削除を検出: {file_path}")
        self.deleted_files.add(file_path)

        # クールダウン期間を過ぎている場合のみキャッシュクリアを実行
        if current_time - self.last_cleanup_time > self.cleanup_cooldown:
            self.trigger_cache_cleanup()
            self.last_cleanup_time = current_time

    def trigger_cache_cleanup(self):
        """キャッシュクリアを実行"""
        try:
            logger.info("自動キャッシュクリアを実行中...")

            # キャッシュクリア実行
            cache_results = self.cache_cleaner.clear_all_ide_cache()

            # 結果をログに記録
            for ide, results in cache_results.items():
                success = results['success']
                failed = results['failed']
                logger.info(f"{ide.upper()} キャッシュクリア: {success}成功, {failed}失敗")

            # 自動再起動が有効な場合
            if self.auto_restart:
                logger.info("IDE自動再起動を実行中...")
                restart_results = self.cache_cleaner.restart_all_ides()

                for ide, success in restart_results.items():
                    status = "成功" if success else "失敗"
                    logger.info(f"{ide.upper()} 再起動: {status}")

            # 削除されたファイルリストをクリア
            self.deleted_files.clear()

            logger.info("自動キャッシュクリア完了")

        except Exception as e:
            logger.error(f"キャッシュクリア実行中にエラーが発生: {e}")

class FileDeletionMonitor:
    """ファイル削除監視クラス"""

    def __init__(self, target_dirs: List[str], auto_restart: bool = False):
        self.target_dirs = [Path(d) for d in target_dirs]
        self.auto_restart = auto_restart
        self.cache_cleaner = IDECacheCleaner()
        self.observer = Observer()
        self.handler = FileDeletionHandler(self.cache_cleaner, auto_restart)

    def start_monitoring(self):
        """監視を開始"""
        logger.info("ファイル削除監視を開始")
        logger.info(f"監視ディレクトリ: {[str(d) for d in self.target_dirs]}")
        logger.info(f"自動再起動: {'有効' if self.auto_restart else '無効'}")

        # 各ディレクトリに監視を設定
        for target_dir in self.target_dirs:
            if target_dir.exists():
                self.observer.schedule(self.handler, str(target_dir), recursive=True)
                logger.info(f"監視開始: {target_dir}")
            else:
                logger.warning(f"ディレクトリが存在しません: {target_dir}")

        self.observer.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("監視を停止中...")
            self.stop_monitoring()

    def stop_monitoring(self):
        """監視を停止"""
        self.observer.stop()
        self.observer.join()
        logger.info("ファイル削除監視を停止")

def load_config() -> Dict[str, Any]:
    """設定ファイルを読み込み"""
    config_file = Path("scripts/monitor_config.json")

    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"設定ファイルの読み込みに失敗: {e}")

    # デフォルト設定
    return {
        "target_directories": ["."],
        "auto_restart": False,
        "cleanup_cooldown": 30
    }

def main():
    """メイン関数"""
    print("🔍 ファイル削除監視ツール")
    print("=" * 40)

    # 設定読み込み
    config = load_config()
    target_dirs = config.get("target_directories", ["."])
    auto_restart = config.get("auto_restart", False)

    print(f"📁 監視ディレクトリ: {target_dirs}")
    print(f"🔄 自動再起動: {'有効' if auto_restart else '無効'}")

    # 監視開始
    monitor = FileDeletionMonitor(target_dirs, auto_restart)

    try:
        monitor.start_monitoring()
    except KeyboardInterrupt:
        print("\n👋 監視を終了します")

if __name__ == "__main__":
    main()
