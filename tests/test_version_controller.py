#!/usr/bin/env python3
"""version_controller テスト"""

import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from version_controller import VersionController


class TestVersionController:
    """VersionControllerのテスト"""

    def test_init(self):
        """初期化テスト"""
        with tempfile.TemporaryDirectory() as tmpdir:
            vc = VersionController(versions_dir=tmpdir, max_versions=5)
            assert vc.versions_dir == Path(tmpdir)
            assert vc.max_versions == 5

    def test_directory_creation(self):
        """ディレクトリ作成テスト"""
        with tempfile.TemporaryDirectory() as tmpdir:
            versions_path = Path(tmpdir) / "test_versions"
            vc = VersionController(versions_dir=str(versions_path))
            assert versions_path.exists()
            assert (versions_path / "data").exists()
            assert (versions_path / "metadata").exists()
            assert (versions_path / "snapshots").exists()

    def test_load_history_empty(self):
        """空の履歴ロード"""
        with tempfile.TemporaryDirectory() as tmpdir:
            vc = VersionController(versions_dir=tmpdir)
            assert vc.version_history == []

    def test_default_max_versions(self):
        """デフォルトmax_versions"""
        with tempfile.TemporaryDirectory() as tmpdir:
            vc = VersionController(versions_dir=tmpdir)
            assert vc.max_versions == 10

    def test_history_file_path(self):
        """履歴ファイルパステスト"""
        with tempfile.TemporaryDirectory() as tmpdir:
            vc = VersionController(versions_dir=tmpdir)
            assert vc.history_file == Path(tmpdir) / "version_history.json"

    def test_current_file_path(self):
        """現在バージョンファイルパステスト"""
        with tempfile.TemporaryDirectory() as tmpdir:
            vc = VersionController(versions_dir=tmpdir)
            assert vc.current_file == Path(tmpdir) / "current_version.json"

    def test_snapshots_dir_creation(self):
        """snapshotsディレクトリ作成テスト"""
        with tempfile.TemporaryDirectory() as tmpdir:
            versions_path = Path(tmpdir) / "versions"
            vc = VersionController(versions_dir=str(versions_path))
            assert (versions_path / "snapshots").exists()
