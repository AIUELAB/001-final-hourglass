"""
BackupManager テストモジュール

backup_manager.py の単体テストを提供します。
"""

import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from src.backup_manager import BackupManager


@pytest.fixture
def temp_backup_dir(tmp_path: Path) -> Path:
    """テスト用のバックアップディレクトリ"""
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir(parents=True)
    return backup_dir


@pytest.fixture
def sample_csv(tmp_path: Path) -> Path:
    """テスト用のCSVファイル"""
    csv_path = tmp_path / "test.csv"
    csv_path.write_text("header1,header2\nvalue1,value2", encoding="utf-8")
    return csv_path


@pytest.fixture
def manager(temp_backup_dir: Path) -> BackupManager:
    """テスト用のBackupManagerインスタンス"""
    return BackupManager(backup_dir=temp_backup_dir)


class TestBackupManagerInit:
    """初期化テスト"""

    def test_init_with_custom_dir(self, temp_backup_dir: Path) -> None:
        """カスタムディレクトリで初期化できる"""
        manager = BackupManager(backup_dir=temp_backup_dir)
        assert manager.backup_dir == temp_backup_dir

    def test_init_creates_directory(self, tmp_path: Path) -> None:
        """存在しないディレクトリは自動作成される"""
        new_dir = tmp_path / "new_backup_dir"
        assert not new_dir.exists()

        manager = BackupManager(backup_dir=new_dir)
        assert new_dir.exists()

    def test_init_with_default_dir(self) -> None:
        """デフォルトディレクトリで初期化できる"""
        with patch("src.backup_manager.get_project_root") as mock_root:
            mock_root.return_value = Path("/mock/project")
            with patch.object(Path, "mkdir"):
                manager = BackupManager()
                assert manager.backup_dir == Path("/mock/project/preserved/backups")


class TestCreateBackup:
    """create_backup メソッドのテスト"""

    def test_creates_backup_file(self, manager: BackupManager, sample_csv: Path) -> None:
        """バックアップファイルが作成される"""
        backup_path = manager.create_backup(sample_csv)

        assert backup_path.exists()
        assert backup_path.name.startswith("MASTER_EPISODES_")
        assert backup_path.suffix == ".csv"

    def test_backup_contains_same_content(self, manager: BackupManager, sample_csv: Path) -> None:
        """バックアップは元ファイルと同じ内容を持つ"""
        backup_path = manager.create_backup(sample_csv)

        original_content = sample_csv.read_text(encoding="utf-8")
        backup_content = backup_path.read_text(encoding="utf-8")

        assert original_content == backup_content

    def test_backup_has_timestamp_in_name(self, manager: BackupManager, sample_csv: Path) -> None:
        """バックアップ名にタイムスタンプが含まれる"""
        backup_path = manager.create_backup(sample_csv)

        # MASTER_EPISODES_YYYYMMDD_HHMMSS.csv 形式
        name_parts = backup_path.stem.split("_")
        assert len(name_parts) == 4  # MASTER, EPISODES, date, time
        assert len(name_parts[2]) == 8  # YYYYMMDD
        assert len(name_parts[3]) == 6  # HHMMSS

    def test_multiple_backups_have_unique_names(self, manager: BackupManager, sample_csv: Path) -> None:
        """複数のバックアップは異なる名前を持つ"""
        backup1 = manager.create_backup(sample_csv)
        time.sleep(1.1)  # タイムスタンプが異なることを保証
        backup2 = manager.create_backup(sample_csv)

        assert backup1.name != backup2.name


class TestRestoreBackup:
    """restore_backup メソッドのテスト"""

    def test_restores_from_backup(self, manager: BackupManager, sample_csv: Path, tmp_path: Path) -> None:
        """バックアップから復元できる"""
        backup_path = manager.create_backup(sample_csv)

        # 元ファイルを変更
        sample_csv.write_text("modified,content", encoding="utf-8")

        # 新しい場所に復元
        restore_path = tmp_path / "restored.csv"
        manager.restore_backup(backup_path, restore_path)

        assert restore_path.exists()
        restored_content = restore_path.read_text(encoding="utf-8")
        assert restored_content == "header1,header2\nvalue1,value2"

    def test_restore_raises_on_missing_backup(self, manager: BackupManager, tmp_path: Path) -> None:
        """存在しないバックアップでは例外が発生する"""
        fake_backup = tmp_path / "nonexistent.csv"
        target_path = tmp_path / "target.csv"

        with pytest.raises(FileNotFoundError):
            manager.restore_backup(fake_backup, target_path)


class TestCleanupOldBackups:
    """cleanup_old_backups メソッドのテスト"""

    def test_deletes_old_backups(self, manager: BackupManager, temp_backup_dir: Path) -> None:
        """古いバックアップが削除される"""
        # 古いバックアップファイルを作成
        old_backup = temp_backup_dir / "MASTER_EPISODES_20200101_000000.csv"
        old_backup.write_text("old content", encoding="utf-8")

        # ファイルの修正時刻を60日前に設定
        old_time = (datetime.now() - timedelta(days=60)).timestamp()
        import os

        os.utime(old_backup, (old_time, old_time))

        deleted_count = manager.cleanup_old_backups(days=30)

        assert deleted_count == 1
        assert not old_backup.exists()

    def test_keeps_recent_backups(self, manager: BackupManager, temp_backup_dir: Path) -> None:
        """新しいバックアップは保持される"""
        # 新しいバックアップファイルを作成
        recent_backup = temp_backup_dir / "MASTER_EPISODES_20991231_235959.csv"
        recent_backup.write_text("recent content", encoding="utf-8")

        deleted_count = manager.cleanup_old_backups(days=30)

        assert deleted_count == 0
        assert recent_backup.exists()

    def test_returns_zero_when_no_old_backups(self, manager: BackupManager) -> None:
        """古いバックアップがない場合は0を返す"""
        deleted_count = manager.cleanup_old_backups(days=30)
        assert deleted_count == 0


class TestListBackups:
    """list_backups メソッドのテスト"""

    def test_lists_all_backups(self, manager: BackupManager, temp_backup_dir: Path) -> None:
        """全てのバックアップをリストする"""
        # テスト用バックアップを作成
        (temp_backup_dir / "MASTER_EPISODES_20240101_000000.csv").write_text("1")
        (temp_backup_dir / "MASTER_EPISODES_20240102_000000.csv").write_text("2")
        (temp_backup_dir / "MASTER_EPISODES_20240103_000000.csv").write_text("3")

        backups = manager.list_backups()

        assert len(backups) == 3

    def test_lists_with_limit(self, manager: BackupManager, temp_backup_dir: Path) -> None:
        """limitで取得数を制限できる"""
        (temp_backup_dir / "MASTER_EPISODES_20240101_000000.csv").write_text("1")
        (temp_backup_dir / "MASTER_EPISODES_20240102_000000.csv").write_text("2")
        (temp_backup_dir / "MASTER_EPISODES_20240103_000000.csv").write_text("3")

        backups = manager.list_backups(limit=2)

        assert len(backups) == 2

    def test_sorts_by_mtime_descending(self, manager: BackupManager, temp_backup_dir: Path) -> None:
        """修正時刻の降順でソートされる"""
        import os

        # 3つのファイルを異なるタイムスタンプで作成
        f1 = temp_backup_dir / "MASTER_EPISODES_20240101_000000.csv"
        f2 = temp_backup_dir / "MASTER_EPISODES_20240102_000000.csv"
        f3 = temp_backup_dir / "MASTER_EPISODES_20240103_000000.csv"

        f1.write_text("1")
        f2.write_text("2")
        f3.write_text("3")

        # 明示的にmtimeを設定
        os.utime(f1, (1000, 1000))
        os.utime(f2, (2000, 2000))
        os.utime(f3, (3000, 3000))

        backups = manager.list_backups()

        assert backups[0].name == f3.name  # 最新
        assert backups[2].name == f1.name  # 最古

    def test_returns_empty_list_when_no_backups(self, manager: BackupManager) -> None:
        """バックアップがない場合は空リストを返す"""
        backups = manager.list_backups()
        assert backups == []


class TestGetLatestBackup:
    """get_latest_backup メソッドのテスト"""

    def test_returns_latest_backup(self, manager: BackupManager, temp_backup_dir: Path) -> None:
        """最新のバックアップを返す"""
        import os

        f1 = temp_backup_dir / "MASTER_EPISODES_20240101_000000.csv"
        f2 = temp_backup_dir / "MASTER_EPISODES_20240102_000000.csv"

        f1.write_text("old")
        f2.write_text("new")

        os.utime(f1, (1000, 1000))
        os.utime(f2, (2000, 2000))

        latest = manager.get_latest_backup()

        assert latest is not None
        assert latest.name == f2.name

    def test_returns_none_when_no_backups(self, manager: BackupManager) -> None:
        """バックアップがない場合はNoneを返す"""
        latest = manager.get_latest_backup()
        assert latest is None
