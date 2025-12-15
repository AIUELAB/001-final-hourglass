#!/usr/bin/env python3
"""version_controller テスト"""

import sys
import tempfile
from pathlib import Path


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

    def test_calculate_hash_string(self):
        """文字列ハッシュ計算テスト"""
        with tempfile.TemporaryDirectory() as tmpdir:
            vc = VersionController(versions_dir=tmpdir)
            hash1 = vc.calculate_hash("test data")
            hash2 = vc.calculate_hash("test data")
            hash3 = vc.calculate_hash("different data")
            assert hash1 == hash2
            assert hash1 != hash3

    def test_calculate_hash_dict(self):
        """辞書ハッシュ計算テスト"""
        with tempfile.TemporaryDirectory() as tmpdir:
            vc = VersionController(versions_dir=tmpdir)
            data = {"key": "value", "number": 123}
            hash1 = vc.calculate_hash(data)
            hash2 = vc.calculate_hash(data)
            assert hash1 == hash2
            assert len(hash1) == 64  # SHA256

    def test_calculate_hash_dataframe(self):
        """DataFrameハッシュ計算テスト"""
        import pandas as pd

        with tempfile.TemporaryDirectory() as tmpdir:
            vc = VersionController(versions_dir=tmpdir)
            df = pd.DataFrame({"col1": [1, 2], "col2": ["a", "b"]})
            hash1 = vc.calculate_hash(df)
            assert len(hash1) == 64

    def test_save_and_load_history(self):
        """履歴保存・読み込みテスト"""

        with tempfile.TemporaryDirectory() as tmpdir:
            vc = VersionController(versions_dir=tmpdir)
            vc.version_history = [{"version": "v1", "timestamp": "2025-01-01"}]
            vc._save_history()

            # ファイルが作成されたことを確認
            assert vc.history_file.exists()

            # 新しいインスタンスで読み込み
            vc2 = VersionController(versions_dir=tmpdir)
            assert len(vc2.version_history) == 1
            assert vc2.version_history[0]["version"] == "v1"

    def test_logger_exists(self):
        """ロガー存在確認"""
        with tempfile.TemporaryDirectory() as tmpdir:
            vc = VersionController(versions_dir=tmpdir)
            assert hasattr(vc, "logger")
