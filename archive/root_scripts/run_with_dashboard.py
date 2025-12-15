#!/usr/bin/env python3
"""
誕生年取得システム実行スクリプト（ダッシュボード付き）
リアルタイム監視ダッシュボードと共に処理を実行
"""

import subprocess
import time
import webbrowser
import os
import signal
import sys
from pathlib import Path
import logging
from datetime import datetime

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BirthCollectionWithDashboard:
    """ダッシュボード付き誕生年取得システム"""

    def __init__(self):
        self.server_process = None
        self.collection_process = None
        self.dashboard_url = "http://localhost:5000"

    def start_monitor_server(self):
        """監視サーバーを起動"""
        logger.info("📡 監視サーバーを起動中...")

        try:
            # Pythonサーバーを起動
            self.server_process = subprocess.Popen(
                ['python3', 'birth_collection_server.py'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid if sys.platform != 'win32' else None
            )

            # サーバー起動を待つ
            time.sleep(2)

            # サーバーが正常に起動したか確認
            if self.server_process.poll() is None:
                logger.info(f"✅ 監視サーバー起動成功: {self.dashboard_url}")
                return True
            else:
                logger.error("❌ 監視サーバーの起動に失敗しました")
                return False

        except Exception as e:
            logger.error(f"サーバー起動エラー: {e}")
            return False

    def open_dashboard(self):
        """ダッシュボードをブラウザで開く"""
        logger.info("🌐 ダッシュボードをブラウザで開いています...")

        try:
            # デフォルトブラウザで開く
            webbrowser.open(self.dashboard_url)
            logger.info("✅ ダッシュボードが開きました")
            return True

        except Exception as e:
            logger.error(f"ブラウザ起動エラー: {e}")
            # 手動でURLを表示
            logger.info(f"手動でブラウザから開いてください: {self.dashboard_url}")
            return False

    def start_collection_process(self, process_type='wikipedia'):
        """データ収集プロセスを開始"""
        logger.info(f"🚀 {process_type}収集プロセスを開始...")

        script_map = {
            'wikipedia': 'run_full_birth_collection.py',
            'wikidata': 'wikidata_birth_collector_optimized.py',
            'firecrawl': 'firecrawl_birth_collector.py'
        }

        script_path = script_map.get(process_type)
        if not script_path or not Path(script_path).exists():
            logger.error(f"❌ スクリプトが見つかりません: {script_path}")
            return False

        try:
            # 収集プロセスを起動
            self.collection_process = subprocess.Popen(
                ['python3', script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                preexec_fn=os.setsid if sys.platform != 'win32' else None
            )

            logger.info(f"✅ {process_type}収集プロセス開始")
            return True

        except Exception as e:
            logger.error(f"収集プロセス起動エラー: {e}")
            return False

    def monitor_processes(self):
        """プロセスを監視"""
        logger.info("👀 プロセス監視中...")

        try:
            while True:
                # サーバープロセスの確認
                if self.server_process and self.server_process.poll() is not None:
                    logger.warning("⚠️ 監視サーバーが停止しました")
                    break

                # 収集プロセスの確認
                if self.collection_process:
                    retcode = self.collection_process.poll()
                    if retcode is not None:
                        if retcode == 0:
                            logger.info("✅ 収集プロセスが正常終了しました")
                        else:
                            logger.error(f"❌ 収集プロセスがエラー終了しました: {retcode}")
                        break

                # 1秒待機
                time.sleep(1)

        except KeyboardInterrupt:
            logger.info("\n⚠️ 中断シグナルを受信しました")

    def cleanup(self):
        """クリーンアップ処理"""
        logger.info("🧹 クリーンアップ中...")

        # 収集プロセスを終了
        if self.collection_process and self.collection_process.poll() is None:
            if sys.platform != 'win32':
                os.killpg(os.getpgid(self.collection_process.pid), signal.SIGTERM)
            else:
                self.collection_process.terminate()
            self.collection_process.wait(timeout=5)
            logger.info("収集プロセスを終了しました")

        # サーバープロセスを終了
        if self.server_process and self.server_process.poll() is None:
            if sys.platform != 'win32':
                os.killpg(os.getpgid(self.server_process.pid), signal.SIGTERM)
            else:
                self.server_process.terminate()
            self.server_process.wait(timeout=5)
            logger.info("監視サーバーを終了しました")

    def run(self, process_type='wikipedia'):
        """メイン実行"""
        logger.info("=" * 70)
        logger.info("🎯 誕生年取得システム（ダッシュボード付き）")
        logger.info("=" * 70)

        try:
            # 1. 監視サーバー起動
            if not self.start_monitor_server():
                logger.error("監視サーバーの起動に失敗しました")
                return

            # 2. ダッシュボードを開く
            time.sleep(1)
            self.open_dashboard()

            # 3. 収集プロセス開始
            time.sleep(1)
            if not self.start_collection_process(process_type):
                logger.error("収集プロセスの起動に失敗しました")
                return

            # 4. プロセス監視
            self.monitor_processes()

        except Exception as e:
            logger.error(f"実行エラー: {e}")

        finally:
            # 5. クリーンアップ
            self.cleanup()
            logger.info("=" * 70)
            logger.info("✅ システム終了")
            logger.info("=" * 70)


def main():
    """メイン処理"""
    import argparse

    parser = argparse.ArgumentParser(description='誕生年取得システム（ダッシュボード付き）')
    parser.add_argument(
        '--type',
        choices=['wikipedia', 'wikidata', 'firecrawl'],
        default='wikipedia',
        help='収集タイプ（デフォルト: wikipedia）'
    )

    args = parser.parse_args()

    # システム実行
    system = BirthCollectionWithDashboard()
    system.run(args.type)


if __name__ == "__main__":
    main()
