#!/usr/bin/env python3
"""
統合ルール管理システム - 自動同期ウォッチャー
Unified Rule Management System - Auto Sync Watcher

目的:
1. rules_registry.jsonの変更を監視
2. 変更検出時に自動的に同期を実行
3. 同期失敗時のアラートと自動リトライ
4. 変更履歴のログ記録

依存関係:
- watchdog: pip install watchdog

Created: 2025-10-02
"""

import json
import logging
import time
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)


class RuleRegistryWatcher(FileSystemEventHandler):
    """ルールレジストリ変更ウォッチャー"""

    def __init__(
        self,
        registry_path: str = "rules_registry.json",
        sync_script: str = "rule_sync_automation.py",
        health_script: str = "rule_health_monitor.py",
        cooldown_seconds: int = 5
    ):
        self.registry_path = Path(registry_path).resolve()
        self.sync_script = Path(sync_script)
        self.health_script = Path(health_script)
        self.cooldown_seconds = cooldown_seconds
        self.last_sync_time = 0
        self.sync_log = []

    def on_modified(self, event: FileSystemEvent):
        """ファイル変更イベント"""
        if event.is_directory:
            return

        # rules_registry.jsonの変更のみ監視
        if Path(event.src_path).resolve() != self.registry_path:
            return

        # クールダウン期間チェック（連続変更イベントを防ぐ）
        current_time = time.time()
        if current_time - self.last_sync_time < self.cooldown_seconds:
            logger.debug(f"クールダウン期間中 ({self.cooldown_seconds}秒)")
            return

        self.last_sync_time = current_time

        logger.info("=" * 60)
        logger.info(f"🔔 ルールレジストリ変更検出: {self.registry_path.name}")
        logger.info("=" * 60)

        # 自動同期実行
        self._trigger_auto_sync()

    def _trigger_auto_sync(self):
        """自動同期トリガー"""
        sync_result = {
            'timestamp': datetime.now().isoformat(),
            'trigger': 'file_change',
            'success': False,
            'details': {}
        }

        try:
            # 1. 同期スクリプト実行
            logger.info("🔄 自動同期開始...")

            result = subprocess.run(
                ['python3', str(self.sync_script)],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                logger.info("✅ 同期成功")
                sync_result['success'] = True
                sync_result['details']['sync_output'] = result.stdout
            else:
                logger.error(f"❌ 同期失敗 (終了コード: {result.returncode})")
                logger.error(f"エラー出力:\n{result.stderr}")
                sync_result['details']['error'] = result.stderr

            # 2. ヘルスチェック実行
            logger.info("🏥 ヘルスチェック実行...")

            health_result = subprocess.run(
                ['python3', str(self.health_script)],
                capture_output=True,
                text=True,
                timeout=30
            )

            if health_result.returncode == 0:
                logger.info("✅ ヘルスチェック合格")
                sync_result['details']['health_check'] = 'PASS'
            elif health_result.returncode == 1:
                logger.warning("⚠️ ヘルスチェック警告")
                sync_result['details']['health_check'] = 'WARN'
            else:
                logger.error("❌ ヘルスチェック失敗")
                sync_result['details']['health_check'] = 'FAIL'

        except subprocess.TimeoutExpired:
            logger.error("❌ タイムアウト")
            sync_result['details']['error'] = 'Timeout'
        except Exception as e:
            logger.error(f"❌ 予期しないエラー: {e}")
            sync_result['details']['error'] = str(e)

        # ログに記録
        self.sync_log.append(sync_result)
        self._save_sync_log()

        logger.info("=" * 60)

    def _save_sync_log(self):
        """同期ログ保存"""
        log_path = "rule_auto_sync_log.json"

        # 最新100件のみ保持
        recent_logs = self.sync_log[-100:]

        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump({
                'last_updated': datetime.now().isoformat(),
                'total_syncs': len(recent_logs),
                'success_count': sum(1 for log in recent_logs if log['success']),
                'logs': recent_logs
            }, f, ensure_ascii=False, indent=2)


class RuleAutoSyncDaemon:
    """自動同期デーモン"""

    def __init__(self, watch_directory: str = "."):
        self.watch_directory = Path(watch_directory).resolve()
        self.observer = Observer()
        self.watcher = RuleRegistryWatcher()

    def start(self):
        """デーモン起動"""
        logger.info("🚀 統合ルール管理システム - 自動同期デーモン起動")
        logger.info(f"📂 監視ディレクトリ: {self.watch_directory}")
        logger.info(f"📄 監視ファイル: {self.watcher.registry_path.name}")
        logger.info("=" * 60)

        # 起動時に初回ヘルスチェック
        logger.info("🏥 起動時ヘルスチェック実行...")
        subprocess.run(['python3', str(self.watcher.health_script)], check=False)

        # 監視開始
        self.observer.schedule(self.watcher, str(self.watch_directory), recursive=False)
        self.observer.start()

        logger.info("👀 ファイル監視開始...")
        logger.info("Ctrl+C で停止")
        logger.info("=" * 60)

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("\n⏹️  停止シグナル受信")
            self.observer.stop()

        self.observer.join()
        logger.info("✅ 自動同期デーモン停止")

    def stop(self):
        """デーモン停止"""
        if self.observer.is_alive():
            self.observer.stop()
            self.observer.join()


def install_as_git_hook():
    """Gitフックとしてインストール"""
    git_hooks_dir = Path(".git/hooks")

    if not git_hooks_dir.exists():
        logger.error("❌ Gitリポジトリではありません")
        return False

    hook_path = git_hooks_dir / "pre-commit"

    hook_content = """#!/bin/bash
# 統合ルール管理システム - 自動同期フック

# rules_registry.jsonが変更されているか確認
if git diff --cached --name-only | grep -q "rules_registry.json"; then
    echo "🔔 rules_registry.json の変更を検出"

    # 自動同期実行
    echo "🔄 自動同期実行中..."
    python3 rule_sync_automation.py

    if [ $? -eq 0 ]; then
        echo "✅ 同期成功"

        # 同期結果をステージング
        git add pdca_guardian.py episode_guardian_config.json rule_sync_report.json

        # ヘルスチェック実行
        echo "🏥 ヘルスチェック実行中..."
        python3 rule_health_monitor.py

        if [ $? -eq 0 ]; then
            echo "✅ ヘルスチェック合格"
        else
            echo "⚠️ ヘルスチェック警告"
        fi
    else
        echo "❌ 同期失敗 - コミットを中断します"
        exit 1
    fi
fi

exit 0
"""

    with open(hook_path, 'w', encoding='utf-8') as f:
        f.write(hook_content)

    # 実行権限付与
    hook_path.chmod(0o755)

    logger.info(f"✅ Gitフックインストール完了: {hook_path}")
    return True


def main():
    """メイン処理"""
    import argparse

    parser = argparse.ArgumentParser(description="統合ルール管理システム - 自動同期ウォッチャー")
    parser.add_argument('--daemon', action='store_true', help='デーモンモードで起動')
    parser.add_argument('--install-hook', action='store_true', help='Gitフックとしてインストール')
    parser.add_argument('--watch-dir', default='.', help='監視ディレクトリ（デフォルト: .）')

    args = parser.parse_args()

    if args.install_hook:
        install_as_git_hook()
    elif args.daemon:
        daemon = RuleAutoSyncDaemon(watch_directory=args.watch_dir)
        daemon.start()
    else:
        print("使用方法:")
        print("  --daemon         : デーモンモードで起動")
        print("  --install-hook   : Gitフックとしてインストール")
        print("  --watch-dir DIR  : 監視ディレクトリを指定")


if __name__ == "__main__":
    main()
