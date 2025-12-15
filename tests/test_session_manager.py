#!/usr/bin/env python3
"""session_manager テスト"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestSessionManager:
    """SessionManagerのテスト"""

    @patch("session_manager.signal.signal")
    def test_init(self, mock_signal):
        """初期化テスト"""
        from session_manager import SessionManager

        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SessionManager(session_dir=tmpdir)
            assert sm.session_dir == Path(tmpdir)
            assert sm.auto_save_interval == 60

    @patch("session_manager.signal.signal")
    def test_directory_creation(self, mock_signal):
        """ディレクトリ作成テスト"""
        from session_manager import SessionManager

        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = Path(tmpdir) / "test_sessions"
            sm = SessionManager(session_dir=str(session_path))
            assert session_path.exists()
            assert (session_path / "backups").exists()

    @patch("session_manager.signal.signal")
    def test_session_data_init(self, mock_signal):
        """セッションデータ初期化テスト"""
        from session_manager import SessionManager

        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SessionManager(session_dir=tmpdir)
            assert isinstance(sm.session_data, dict)

    @patch("session_manager.signal.signal")
    def test_session_file_path(self, mock_signal):
        """セッションファイルパステスト"""
        from session_manager import SessionManager

        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SessionManager(session_dir=tmpdir)
            assert sm.session_file == Path(tmpdir) / "current_session.json"

    @patch("session_manager.signal.signal")
    def test_set_and_get(self, mock_signal):
        """set/getテスト"""
        from session_manager import SessionManager

        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SessionManager(session_dir=tmpdir)
            sm.set("key1", "value1")
            sm.set("key2", 123)
            assert sm.get("key1") == "value1"
            assert sm.get("key2") == 123
            assert sm.get("nonexistent") is None
            assert sm.get("nonexistent", "default") == "default"

    @patch("session_manager.signal.signal")
    def test_delete(self, mock_signal):
        """deleteテスト"""
        from session_manager import SessionManager

        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SessionManager(session_dir=tmpdir)
            sm.set("key1", "value1")
            sm.delete("key1")
            assert sm.get("key1") is None
            # 存在しないキー削除（エラーなし）
            sm.delete("nonexistent")

    @patch("session_manager.signal.signal")
    def test_clear(self, mock_signal):
        """clearテスト"""
        from session_manager import SessionManager

        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SessionManager(session_dir=tmpdir)
            sm.set("key1", "value1")
            sm.set("key2", "value2")
            sm.clear()
            assert sm.session_data == {}

    @patch("session_manager.signal.signal")
    def test_get_all(self, mock_signal):
        """get_allテスト"""
        from session_manager import SessionManager

        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SessionManager(session_dir=tmpdir)
            sm.set("key1", "value1")
            all_data = sm.get_all()
            assert "key1" in all_data
            # コピーであることを確認
            all_data["key1"] = "modified"
            assert sm.get("key1") == "value1"

    @patch("session_manager.signal.signal")
    def test_save_and_restore_session(self, mock_signal):
        """save/restoreセッションテスト"""
        from session_manager import SessionManager

        with tempfile.TemporaryDirectory() as tmpdir:
            sm1 = SessionManager(session_dir=tmpdir)
            sm1.set("test_data", {"foo": "bar"})
            sm1.save_session()

            sm2 = SessionManager(session_dir=tmpdir)
            result = sm2.restore_session()
            assert result is True
            assert sm2.get("test_data") == {"foo": "bar"}

    @patch("session_manager.signal.signal")
    def test_create_and_list_checkpoints(self, mock_signal):
        """チェックポイント作成・リストテスト"""
        from session_manager import SessionManager

        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SessionManager(session_dir=tmpdir)
            sm.set("data", "test")
            sm.create_checkpoint("test_cp")
            checkpoints = sm.list_checkpoints()
            assert len(checkpoints) >= 1
            assert any("test_cp" in cp for cp in checkpoints)

    @patch("session_manager.signal.signal")
    def test_restore_checkpoint(self, mock_signal):
        """チェックポイント復元テスト"""
        from session_manager import SessionManager

        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SessionManager(session_dir=tmpdir)
            sm.set("original", "data")
            sm.create_checkpoint("restore_test")

            # チェックポイント名を取得
            checkpoints = sm.list_checkpoints()
            cp_name = [cp for cp in checkpoints if "restore_test" in cp][0]

            # データ変更
            sm.set("original", "changed")
            assert sm.get("original") == "changed"

            # 復元
            result = sm.restore_checkpoint(cp_name)
            assert result is True
            assert sm.get("original") == "data"

    @patch("session_manager.signal.signal")
    def test_restore_nonexistent_checkpoint(self, mock_signal):
        """存在しないチェックポイント復元テスト"""
        from session_manager import SessionManager

        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SessionManager(session_dir=tmpdir)
            result = sm.restore_checkpoint("nonexistent.json")
            assert result is False
