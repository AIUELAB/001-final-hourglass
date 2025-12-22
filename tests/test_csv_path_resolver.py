"""
tests/test_csv_path_resolver.py - csv_path_resolver.py ユニットテスト
"""

from pathlib import Path

import pytest

from src.csv_path_resolver import (
    get_backup_dir,
    get_config_dir,
    get_master_csv_path,
    get_person_sources_dir,
    get_project_root,
    get_reports_dir,
    verify_master_csv_exists,
)


class TestGetProjectRoot:
    """get_project_root関数テスト"""

    def test_returns_path(self):
        """Pathオブジェクトを返す"""
        result = get_project_root()
        assert isinstance(result, Path)

    def test_project_root_exists(self):
        """プロジェクトルートが存在する"""
        result = get_project_root()
        assert result.exists()

    def test_project_root_is_directory(self):
        """プロジェクトルートがディレクトリ"""
        result = get_project_root()
        assert result.is_dir()

    def test_contains_src_directory(self):
        """プロジェクトルートにsrcディレクトリがある"""
        result = get_project_root()
        src_dir = result / "src"
        assert src_dir.exists()

    def test_contains_tests_directory(self):
        """プロジェクトルートにtestsディレクトリがある"""
        result = get_project_root()
        tests_dir = result / "tests"
        assert tests_dir.exists()

    def test_is_absolute_path(self):
        """絶対パスを返す"""
        result = get_project_root()
        assert result.is_absolute()


class TestGetMasterCsvPath:
    """get_master_csv_path関数テスト"""

    def test_returns_path(self):
        """Pathオブジェクトを返す"""
        result = get_master_csv_path()
        assert isinstance(result, Path)

    def test_correct_filename(self):
        """正しいファイル名"""
        result = get_master_csv_path()
        assert result.name == "MASTER_EPISODES_CURRENT.csv"

    def test_in_preserved_data(self):
        """preserved/data/配下にある"""
        result = get_master_csv_path()
        assert "preserved" in result.parts
        assert "data" in result.parts

    def test_is_absolute_path(self):
        """絶対パスを返す"""
        result = get_master_csv_path()
        assert result.is_absolute()

    def test_based_on_project_root(self):
        """プロジェクトルートベース"""
        project_root = get_project_root()
        csv_path = get_master_csv_path()
        expected = project_root / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
        assert csv_path == expected


class TestGetBackupDir:
    """get_backup_dir関数テスト"""

    def test_returns_path(self):
        """Pathオブジェクトを返す"""
        result = get_backup_dir()
        assert isinstance(result, Path)

    def test_directory_exists(self):
        """ディレクトリが存在する（自動作成）"""
        result = get_backup_dir()
        assert result.exists()

    def test_is_directory(self):
        """ディレクトリである"""
        result = get_backup_dir()
        assert result.is_dir()

    def test_in_preserved(self):
        """preserved/配下にある"""
        result = get_backup_dir()
        assert "preserved" in result.parts
        assert "backups" in result.parts

    def test_is_absolute_path(self):
        """絶対パスを返す"""
        result = get_backup_dir()
        assert result.is_absolute()


class TestGetConfigDir:
    """get_config_dir関数テスト"""

    def test_returns_path(self):
        """Pathオブジェクトを返す"""
        result = get_config_dir()
        assert isinstance(result, Path)

    def test_correct_name(self):
        """正しいディレクトリ名"""
        result = get_config_dir()
        assert result.name == "config"

    def test_is_absolute_path(self):
        """絶対パスを返す"""
        result = get_config_dir()
        assert result.is_absolute()

    def test_based_on_project_root(self):
        """プロジェクトルートベース"""
        project_root = get_project_root()
        config_dir = get_config_dir()
        expected = project_root / "config"
        assert config_dir == expected


class TestGetReportsDir:
    """get_reports_dir関数テスト"""

    def test_returns_path(self):
        """Pathオブジェクトを返す"""
        result = get_reports_dir()
        assert isinstance(result, Path)

    def test_directory_exists(self):
        """ディレクトリが存在する（自動作成）"""
        result = get_reports_dir()
        assert result.exists()

    def test_is_directory(self):
        """ディレクトリである"""
        result = get_reports_dir()
        assert result.is_dir()

    def test_correct_name(self):
        """正しいディレクトリ名"""
        result = get_reports_dir()
        assert result.name == "reports"

    def test_is_absolute_path(self):
        """絶対パスを返す"""
        result = get_reports_dir()
        assert result.is_absolute()


class TestVerifyMasterCsvExists:
    """verify_master_csv_exists関数テスト"""

    def test_returns_bool(self):
        """bool値を返す"""
        result = verify_master_csv_exists()
        assert isinstance(result, bool)

    def test_checks_correct_path(self):
        """正しいパスをチェック"""
        csv_path = get_master_csv_path()
        expected = csv_path.exists()
        result = verify_master_csv_exists()
        assert result == expected


class TestGetPersonSourcesDir:
    """get_person_sources_dir関数テスト"""

    def test_returns_path(self):
        """Pathオブジェクトを返す"""
        result = get_person_sources_dir()
        assert isinstance(result, Path)

    def test_directory_exists(self):
        """ディレクトリが存在する（自動作成）"""
        result = get_person_sources_dir()
        assert result.exists()

    def test_is_directory(self):
        """ディレクトリである"""
        result = get_person_sources_dir()
        assert result.is_dir()

    def test_in_config(self):
        """config/配下にある"""
        result = get_person_sources_dir()
        assert "config" in result.parts
        assert "person_sources" in result.parts

    def test_is_absolute_path(self):
        """絶対パスを返す"""
        result = get_person_sources_dir()
        assert result.is_absolute()

    def test_based_on_config_dir(self):
        """config_dirベース"""
        config_dir = get_config_dir()
        sources_dir = get_person_sources_dir()
        expected = config_dir / "person_sources"
        assert sources_dir == expected


class TestIntegration:
    """統合テスト"""

    def test_all_paths_under_project_root(self):
        """すべてのパスがプロジェクトルート配下"""
        project_root = get_project_root()

        paths = [
            get_master_csv_path(),
            get_backup_dir(),
            get_config_dir(),
            get_reports_dir(),
            get_person_sources_dir(),
        ]

        for path in paths:
            # パスがプロジェクトルートから始まることを確認
            try:
                path.relative_to(project_root)
            except ValueError:
                pytest.fail(f"{path} is not under project root {project_root}")

    def test_paths_are_consistent(self):
        """パスの一貫性"""
        # 複数回呼び出しても同じ結果
        root1 = get_project_root()
        root2 = get_project_root()
        assert root1 == root2

        csv1 = get_master_csv_path()
        csv2 = get_master_csv_path()
        assert csv1 == csv2
