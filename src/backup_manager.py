"""
Backup Manager - MASTER CSVの自動バックアップ管理

このモジュールはMASTER CSVのタイムスタンプ付きバックアップを作成・管理します。

主な機能:
- タイムスタンプ付きバックアップ作成
- バックアップからの復元
- 古いバックアップの自動削除（30日以上前）

使用方法:
    >>> from src.backup_manager import BackupManager
    >>> manager = BackupManager()
    >>> backup_path = manager.create_backup(master_csv_path)
    >>> print(f"Backup created: {backup_path}")
"""

import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from src.csv_path_resolver import get_project_root


class BackupManager:
    """バックアップ管理"""

    def __init__(self, backup_dir: Optional[Path] = None):
        """
        初期化

        Args:
            backup_dir: バックアップディレクトリ（省略時はデフォルト）
        """
        if backup_dir is None:
            self.backup_dir = get_project_root() / "preserved" / "backups"
        else:
            self.backup_dir = backup_dir

        # ディレクトリが存在しない場合は作成
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self, csv_path: Path) -> Path:
        """
        タイムスタンプ付きバックアップ作成

        Args:
            csv_path: バックアップ元のCSVファイルパス

        Returns:
            作成されたバックアップファイルのパス

        Example:
            >>> manager = BackupManager()
            >>> backup_path = manager.create_backup(Path("preserved/data/MASTER_EPISODES_CURRENT.csv"))
            >>> print(backup_path)
            preserved/backups/MASTER_EPISODES_20251217_103000.csv
        """
        # タイムスタンプ生成
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"MASTER_EPISODES_{timestamp}.csv"
        backup_path = self.backup_dir / backup_name

        # ファイルコピー（メタデータも保持）
        shutil.copy2(csv_path, backup_path)

        print(f"✅ Backup created: {backup_path}")

        # 古いバックアップの削除（30日以上前）
        self.cleanup_old_backups(days=30)

        return backup_path

    def restore_backup(self, backup_path: Path, target_path: Path) -> None:
        """
        バックアップから復元

        Args:
            backup_path: バックアップファイルのパス
            target_path: 復元先のパス

        Example:
            >>> manager = BackupManager()
            >>> manager.restore_backup(
            ...     Path("preserved/backups/MASTER_EPISODES_20251217_103000.csv"),
            ...     Path("preserved/data/MASTER_EPISODES_CURRENT.csv")
            ... )
        """
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        # バックアップから復元
        shutil.copy2(backup_path, target_path)

        print(f"✅ Restored from backup: {backup_path}")

    def cleanup_old_backups(self, days: int = 30) -> int:
        """
        古いバックアップを削除

        Args:
            days: 保持する日数（これより古いバックアップを削除）

        Returns:
            削除されたファイル数

        Example:
            >>> manager = BackupManager()
            >>> deleted_count = manager.cleanup_old_backups(days=30)
            >>> print(f"Deleted {deleted_count} old backups")
        """
        cutoff = datetime.now() - timedelta(days=days)
        deleted_count = 0

        for backup_file in self.backup_dir.glob("MASTER_EPISODES_*.csv"):
            # ファイルの最終更新時刻を取得
            file_mtime = datetime.fromtimestamp(backup_file.stat().st_mtime)

            if file_mtime < cutoff:
                backup_file.unlink()
                print(f"🗑️  Deleted old backup: {backup_file.name}")
                deleted_count += 1

        return deleted_count

    def list_backups(self, limit: Optional[int] = None) -> list[Path]:
        """
        バックアップファイルのリストを取得（新しい順）

        Args:
            limit: 取得する最大数（Noneの場合は全件）

        Returns:
            バックアップファイルのパスリスト

        Example:
            >>> manager = BackupManager()
            >>> backups = manager.list_backups(limit=5)
            >>> for backup in backups:
            ...     print(backup.name)
        """
        # バックアップファイルを取得し、タイムスタンプでソート（新しい順）
        backups = sorted(
            self.backup_dir.glob("MASTER_EPISODES_*.csv"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        if limit:
            backups = backups[:limit]

        return backups

    def get_latest_backup(self) -> Optional[Path]:
        """
        最新のバックアップファイルを取得

        Returns:
            最新のバックアップファイルのパス（存在しない場合はNone）

        Example:
            >>> manager = BackupManager()
            >>> latest = manager.get_latest_backup()
            >>> if latest:
            ...     print(f"Latest backup: {latest.name}")
        """
        backups = self.list_backups(limit=1)
        return backups[0] if backups else None


if __name__ == "__main__":
    # 動作確認用
    from src.csv_path_resolver import get_master_csv_path

    manager = BackupManager()

    print("=== Backup Manager Test ===\n")

    # 最新バックアップの確認
    latest = manager.get_latest_backup()
    if latest:
        print(f"Latest backup: {latest.name}")
        print(f"  Created: {datetime.fromtimestamp(latest.stat().st_mtime)}")
    else:
        print("No backups found")

    # バックアップ一覧の表示
    backups = manager.list_backups(limit=5)
    print(f"\nBackup files (latest {len(backups)}):")
    for backup in backups:
        file_mtime = datetime.fromtimestamp(backup.stat().st_mtime)
        file_size = backup.stat().st_size / (1024 * 1024)  # MB
        print(f"  - {backup.name} ({file_size:.2f} MB, {file_mtime})")

    # テストバックアップ作成（ユーザー確認）
    print("\n⚠️  Create a test backup? (y/n): ", end="")
    if input().lower() == "y":
        master_csv = get_master_csv_path()
        backup_path = manager.create_backup(master_csv)
        print(f"✅ Test backup created: {backup_path}")
