#!/usr/bin/env python3
"""
IDEキャッシュクリア統合スクリプト

このスクリプトは、ファイル削除監視とIDEキャッシュクリアを統合し、
削除済みファイルのエラー表示問題を自動的に解決します。

使用方法:
1. 手動実行: python auto_cache_cleaner.py
2. 監視モード: python auto_cache_cleaner.py --monitor
3. 自動再起動: python auto_cache_cleaner.py --monitor --auto-restart
"""

import argparse
import sys
import logging
from pathlib import Path

# スクリプトディレクトリをパスに追加
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from clear_ide_cache import IDECacheCleaner
from file_deletion_monitor import FileDeletionMonitor

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('auto_cache_cleaner.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def manual_cleanup():
    """手動キャッシュクリア"""
    print("🧹 手動キャッシュクリアを実行")
    print("=" * 40)

    cleaner = IDECacheCleaner()

    # インストールされているIDEを確認
    installed_ides = cleaner.get_installed_ides()
    if not installed_ides:
        print("❌ インストールされているIDEが見つかりません")
        return

    print(f"📋 検出されたIDE: {', '.join(installed_ides)}")

    # キャッシュクリア実行
    print("\n🧹 キャッシュクリアを実行中...")
    cache_results = cleaner.clear_all_ide_cache()

    # 結果表示
    print("\n📊 キャッシュクリア結果:")
    total_success = 0
    total_failed = 0

    for ide, results in cache_results.items():
        success = results['success']
        failed = results['failed']
        total = success + failed
        total_success += success
        total_failed += failed
        print(f"  {ide.upper()}: {success}/{total} 成功")

    print(f"\n📈 総合結果: {total_success}成功, {total_failed}失敗")

    # IDE再起動の確認
    restart = input("\n🔄 IDEを再起動しますか？ (y/N): ").lower().strip()
    if restart in ['y', 'yes']:
        print("\n🔄 IDE再起動を実行中...")
        restart_results = cleaner.restart_all_ides()

        print("\n📊 再起動結果:")
        for ide, success in restart_results.items():
            status = "✅ 成功" if success else "❌ 失敗"
            print(f"  {ide.upper()}: {status}")

    print("\n✨ キャッシュクリア完了！")

def start_monitoring(auto_restart: bool = False):
    """監視モードを開始"""
    print("🔍 ファイル削除監視モードを開始")
    print("=" * 50)

    # 設定ファイルの確認
    config_file = script_dir / "monitor_config.json"
    if not config_file.exists():
        print("⚠️  設定ファイルが見つかりません。デフォルト設定を使用します。")
        target_dirs = ["."]
    else:
        import json
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
            target_dirs = config.get("target_directories", ["."])

    print(f"📁 監視ディレクトリ: {target_dirs}")
    print(f"🔄 自動再起動: {'有効' if auto_restart else '無効'}")
    print("\n💡 Ctrl+C で監視を停止できます")

    # 監視開始
    monitor = FileDeletionMonitor(target_dirs, auto_restart)

    try:
        monitor.start_monitoring()
    except KeyboardInterrupt:
        print("\n👋 監視を終了します")

def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="IDEキャッシュクリア統合ツール",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python auto_cache_cleaner.py              # 手動キャッシュクリア
  python auto_cache_cleaner.py --monitor    # ファイル削除監視モード
  python auto_cache_cleaner.py --monitor --auto-restart  # 自動再起動付き監視
        """
    )

    parser.add_argument(
        '--monitor',
        action='store_true',
        help='ファイル削除監視モードを有効にする'
    )

    parser.add_argument(
        '--auto-restart',
        action='store_true',
        help='IDE自動再起動を有効にする（監視モードでのみ有効）'
    )

    args = parser.parse_args()

    print("🚀 IDEキャッシュクリア統合ツール")
    print("=" * 50)

    if args.monitor:
        start_monitoring(args.auto_restart)
    else:
        manual_cleanup()

if __name__ == "__main__":
    main()
