#!/usr/bin/env python3
"""
IDEキャッシュクリア自動化スクリプト

このスクリプトは、IDEのキャッシュを自動的にクリアして、
削除済みファイルのエラー表示問題を解決します。

対応IDE:
- Cursor
- VS Code
- IntelliJ IDEA
- PyCharm
"""

import logging
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("ide_cache_clear.log"), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# 定数定義
APPLICATION_SUPPORT = "Application Support"
PYCHARM_PATTERN = "PyCharm*"


class IDECacheCleaner:
    """IDEキャッシュクリアクラス"""

    def __init__(self):
        self.home_dir = Path.home()
        self.cache_dirs = {
            "cursor": [
                self.home_dir / "Library" / APPLICATION_SUPPORT / "Cursor" / "Cache",
                self.home_dir / "Library" / APPLICATION_SUPPORT / "Cursor" / "Code Cache",
                self.home_dir / "Library" / APPLICATION_SUPPORT / "Cursor" / "GPUCache",
                self.home_dir / "Library" / APPLICATION_SUPPORT / "Cursor" / "CachedData",
            ],
            "vscode": [
                self.home_dir / "Library" / APPLICATION_SUPPORT / "Code" / "Cache",
                self.home_dir / "Library" / APPLICATION_SUPPORT / "Code" / "Code Cache",
                self.home_dir / "Library" / APPLICATION_SUPPORT / "Code" / "GPUCache",
                self.home_dir / "Library" / APPLICATION_SUPPORT / "Code" / "CachedData",
            ],
            "intellij": [
                self.home_dir / "Library" / "Caches" / "JetBrains",
                self.home_dir / "Library" / APPLICATION_SUPPORT / "JetBrains",
            ],
            "pycharm": [
                self.home_dir / "Library" / "Caches" / PYCHARM_PATTERN,
                self.home_dir / "Library" / APPLICATION_SUPPORT / PYCHARM_PATTERN,
            ],
        }

    def get_installed_ides(self) -> List[str]:
        """インストールされているIDEを検出"""
        installed = []

        # Cursor
        if (self.home_dir / "Library" / APPLICATION_SUPPORT / "Cursor").exists():
            installed.append("cursor")

        # VS Code
        if (self.home_dir / "Library" / APPLICATION_SUPPORT / "Code").exists():
            installed.append("vscode")

        # IntelliJ
        if (self.home_dir / "Library" / "Caches" / "JetBrains").exists():
            installed.append("intellij")

        # PyCharm
        if any((self.home_dir / "Library" / "Caches").glob(PYCHARM_PATTERN)):
            installed.append("pycharm")

        return installed

    def clear_cache_directory(self, cache_dir: Path) -> bool:
        """キャッシュディレクトリをクリア"""
        try:
            if cache_dir.exists():
                if cache_dir.is_dir():
                    shutil.rmtree(cache_dir)
                    logger.info(f"キャッシュディレクトリを削除: {cache_dir}")
                else:
                    cache_dir.unlink()
                    logger.info(f"キャッシュファイルを削除: {cache_dir}")
                return True
            else:
                logger.debug(f"キャッシュディレクトリが存在しません: {cache_dir}")
                return False
        except Exception as e:
            logger.error(f"キャッシュディレクトリの削除に失敗: {cache_dir} - {e}")
            return False

    def clear_ide_cache(self, ide_name: str) -> Dict[str, int]:
        """指定されたIDEのキャッシュをクリア"""
        results = {"success": 0, "failed": 0}

        if ide_name not in self.cache_dirs:
            logger.error(f"未対応のIDE: {ide_name}")
            return results

        logger.info(f"{ide_name.upper()}のキャッシュクリアを開始")

        for cache_dir in self.cache_dirs[ide_name]:
            if self.clear_cache_directory(cache_dir):
                results["success"] += 1
            else:
                results["failed"] += 1

        return results

    def clear_all_ide_cache(self) -> Dict[str, Dict[str, int]]:
        """すべてのIDEのキャッシュをクリア"""
        installed_ides = self.get_installed_ides()
        results = {}

        logger.info(f"インストールされているIDE: {', '.join(installed_ides)}")

        for ide in installed_ides:
            results[ide] = self.clear_ide_cache(ide)

        return results

    def restart_ide(self, ide_name: str) -> bool:
        """IDEを再起動"""
        try:
            if ide_name == "cursor":
                subprocess.run(["killall", "Cursor"], check=False)
                subprocess.run(["open", "-a", "Cursor"], check=True)
            elif ide_name == "vscode":
                subprocess.run(["killall", "Code"], check=False)
                subprocess.run(["open", "-a", "Visual Studio Code"], check=True)
            elif ide_name == "intellij":
                subprocess.run(["killall", "IntelliJ IDEA"], check=False)
                subprocess.run(["open", "-a", "IntelliJ IDEA"], check=True)
            elif ide_name == "pycharm":
                subprocess.run(["killall", "PyCharm"], check=False)
                subprocess.run(["open", "-a", "PyCharm"], check=True)
            else:
                logger.error(f"未対応のIDE再起動: {ide_name}")
                return False

            logger.info(f"{ide_name.upper()}を再起動しました")
            return True

        except Exception as e:
            logger.error(f"IDE再起動に失敗: {ide_name} - {e}")
            return False

    def restart_all_ides(self) -> Dict[str, bool]:
        """すべてのIDEを再起動"""
        installed_ides = self.get_installed_ides()
        results = {}

        for ide in installed_ides:
            results[ide] = self.restart_ide(ide)

        return results


def main():
    """メイン関数"""
    cleaner = IDECacheCleaner()

    print("🚀 IDEキャッシュクリア自動化ツール")
    print("=" * 50)

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
    for ide, results in cache_results.items():
        success = results["success"]
        failed = results["failed"]
        total = success + failed
        print(f"  {ide.upper()}: {success}/{total} 成功")

    # IDE再起動の確認
    restart = input("\n🔄 IDEを再起動しますか？ (y/N): ").lower().strip()
    if restart in ["y", "yes"]:
        print("\n🔄 IDE再起動を実行中...")
        restart_results = cleaner.restart_all_ides()

        print("\n📊 再起動結果:")
        for ide, success in restart_results.items():
            status = "✅ 成功" if success else "❌ 失敗"
            print(f"  {ide.upper()}: {status}")

    print("\n✨ キャッシュクリア完了！")
    print("💡 削除済みファイルのエラー表示が解消されるはずです")


if __name__ == "__main__":
    main()
