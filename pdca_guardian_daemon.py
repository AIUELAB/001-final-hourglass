#!/usr/bin/env python3
"""
PDCA Guardian Daemon - デーモンモードで起動
PDCAガーディアンをバックグラウンドで継続実行
"""

import sys
import time
import signal
import logging
from pathlib import Path

# PDCAガーディアンのインポート
from pdca_guardian import PDCAGuardian

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [PDCADaemon] - %(message)s'
)
logger = logging.getLogger(__name__)

# グローバル変数
running = True


def signal_handler(signum, frame):
    """シグナルハンドラ - 終了処理"""
    global running
    logger.info("終了シグナルを受信しました")
    running = False


def main():
    """デーモンメイン処理"""
    global running

    # シグナルハンドラの設定
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    logger.info("="*60)
    logger.info("🛡️ PDCA Guardian Daemon 起動")
    logger.info("="*60)

    # PDCAガーディアンの初期化
    try:
        guardian = PDCAGuardian()
        logger.info("✅ PDCAガーディアン初期化完了")
    except Exception as e:
        logger.error(f"❌ 初期化エラー: {e}")
        sys.exit(1)

    # PIDファイルの作成
    pid_file = Path(".pids/pdca_guardian.pid")
    pid_file.parent.mkdir(exist_ok=True)
    with open(pid_file, 'w') as f:
        import os
        f.write(str(os.getpid()))
    logger.info(f"PIDファイル作成: {pid_file}")

    # メインループ
    logger.info("監視モードを開始します（30秒間隔）")
    logger.info("終了するには Ctrl+C を押してください")

    check_count = 0
    while running:
        try:
            check_count += 1
            logger.info(f"\n--- ヘルスチェック #{check_count} ---")

            # 統計情報の表示
            logger.info(f"永続ルール数: {len(getattr(guardian, 'persistent_rules', []))}")
            logger.info(f"失敗パターン: {len(getattr(guardian, 'failure_patterns', []))}")
            logger.info(f"成功パターン: {len(getattr(guardian, 'success_patterns', []))}")

            # 30秒スリープ（1秒ごとにrunning確認）
            for _ in range(30):
                if not running:
                    break
                time.sleep(1)

        except KeyboardInterrupt:
            logger.info("\nキーボード割り込みを受信")
            break
        except Exception as e:
            logger.error(f"エラー発生: {e}")
            logger.info("5秒後にリトライします...")
            time.sleep(5)

    # 終了処理
    logger.info("\n" + "="*60)
    logger.info("🛡️ PDCA Guardian Daemon 終了")
    logger.info("="*60)

    # PIDファイルの削除
    if pid_file.exists():
        pid_file.unlink()
        logger.info(f"PIDファイル削除: {pid_file}")


if __name__ == "__main__":
    main()
