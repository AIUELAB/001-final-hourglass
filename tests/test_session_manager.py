#!/usr/bin/env python3
"""session_manager テスト"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

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
