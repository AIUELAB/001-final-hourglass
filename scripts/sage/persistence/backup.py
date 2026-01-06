"""
Backup Management

マスターCSVのバックアップ作成と管理。
"""

import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..config import BACKUP_DIR, MASTER_CSV


@dataclass
class BackupInfo:
    """バックアップ情報"""

    path: Path
    created_at: str
    size_bytes: int
    row_count: int

    def to_dict(self) -> dict:
        return {
            "path": str(self.path),
            "created_at": self.created_at,
            "size_bytes": self.size_bytes,
            "row_count": self.row_count,
        }


class BackupManager:
    """
    バックアップ管理

    マスターCSVの定期バックアップと世代管理。
    """

    def __init__(
        self,
        backup_dir: Path = BACKUP_DIR,
        master_csv: Path = MASTER_CSV,
        max_backups: int = 10,
    ):
        self.backup_dir = backup_dir
        self.master_csv = master_csv
        self.max_backups = max_backups
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self, suffix: str = None) -> Optional[BackupInfo]:
        """
        バックアップを作成

        Args:
            suffix: ファイル名サフィックス（オプション）

        Returns:
            BackupInfo: バックアップ情報、または None
        """
        if not self.master_csv.exists():
            return None

        # バックアップファイル名を生成
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if suffix:
            backup_name = f"MASTER_EPISODES_{timestamp}_{suffix}.csv"
        else:
            backup_name = f"MASTER_EPISODES_{timestamp}.csv"

        backup_path = self.backup_dir / backup_name

        # コピー
        shutil.copy2(self.master_csv, backup_path)

        # 情報取得
        size_bytes = backup_path.stat().st_size
        row_count = sum(1 for _ in open(backup_path, encoding="utf-8-sig")) - 1  # ヘッダー除く

        # 古いバックアップを削除
        self._cleanup_old_backups()

        return BackupInfo(
            path=backup_path,
            created_at=timestamp,
            size_bytes=size_bytes,
            row_count=row_count,
        )

    def _cleanup_old_backups(self) -> None:
        """古いバックアップを削除"""
        backups = sorted(
            self.backup_dir.glob("MASTER_EPISODES_*.csv"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        for old_backup in backups[self.max_backups :]:
            old_backup.unlink()

    def list_backups(self) -> list[BackupInfo]:
        """
        バックアップ一覧を取得

        Returns:
            list[BackupInfo]: バックアップリスト（新しい順）
        """
        backups = []

        for path in sorted(
            self.backup_dir.glob("MASTER_EPISODES_*.csv"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        ):
            size_bytes = path.stat().st_size
            row_count = sum(1 for _ in open(path, encoding="utf-8-sig")) - 1
            created_at = datetime.fromtimestamp(path.stat().st_mtime).isoformat()

            backups.append(
                BackupInfo(
                    path=path,
                    created_at=created_at,
                    size_bytes=size_bytes,
                    row_count=row_count,
                )
            )

        return backups

    def restore_backup(self, backup_path: Path) -> bool:
        """
        バックアップから復元

        Args:
            backup_path: 復元するバックアップのパス

        Returns:
            bool: 成功したか
        """
        if not backup_path.exists():
            return False

        # 現在のファイルをバックアップ
        if self.master_csv.exists():
            self.create_backup(suffix="before_restore")

        # 復元
        shutil.copy2(backup_path, self.master_csv)
        return True

    def get_latest_backup(self) -> Optional[BackupInfo]:
        """
        最新のバックアップを取得

        Returns:
            BackupInfo: 最新のバックアップ、または None
        """
        backups = self.list_backups()
        return backups[0] if backups else None


def create_pre_operation_backup(operation: str = "hybrid_gen") -> Optional[BackupInfo]:
    """
    操作前バックアップを作成

    Args:
        operation: 操作名

    Returns:
        BackupInfo: バックアップ情報
    """
    manager = BackupManager()
    return manager.create_backup(suffix=f"pre_{operation}")
