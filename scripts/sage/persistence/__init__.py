"""
Persistence Package

安全なCSV追記、バックアップ管理を提供。
"""

from .backup import BackupInfo, BackupManager, create_pre_operation_backup
from .csv_writer import (
    DiffEntry,
    SafeCSVWriter,
    WriteResult,
    safe_append_episodes,
)

__all__ = [
    "BackupManager",
    "BackupInfo",
    "create_pre_operation_backup",
    "SafeCSVWriter",
    "WriteResult",
    "DiffEntry",
    "safe_append_episodes",
]
