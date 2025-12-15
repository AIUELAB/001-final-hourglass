#!/usr/bin/env python3
"""error_recovery テスト"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch


sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestErrorRecovery:
    """ErrorRecoveryのテスト"""

    @patch("error_recovery.get_session_manager")
    def test_init(self, mock_session):
        """初期化テスト"""
        from error_recovery import ErrorRecovery

        mock_session.return_value = MagicMock()
        recovery = ErrorRecovery(max_retries=5, retry_delay=2)
        assert recovery.max_retries == 5
        assert recovery.retry_delay == 2

    @patch("error_recovery.get_session_manager")
    def test_default_values(self, mock_session):
        """デフォルト値テスト"""
        from error_recovery import ErrorRecovery

        mock_session.return_value = MagicMock()
        recovery = ErrorRecovery()
        assert recovery.max_retries == 3
        assert recovery.retry_delay == 1

    @patch("error_recovery.get_session_manager")
    def test_error_log_file_path(self, mock_session):
        """エラーログファイルパス"""
        from error_recovery import ErrorRecovery

        mock_session.return_value = MagicMock()
        recovery = ErrorRecovery()
        assert "error_log.txt" in str(recovery.error_log_file)

    @patch("error_recovery.get_session_manager")
    def test_log_error(self, mock_session):
        """エラーログ記録テスト"""
        from error_recovery import ErrorRecovery

        mock_manager = MagicMock()
        mock_manager.get.return_value = []
        mock_session.return_value = mock_manager

        with tempfile.TemporaryDirectory() as tmpdir:
            recovery = ErrorRecovery()
            recovery.error_log_file = Path(tmpdir) / "error_log.txt"

            test_error = ValueError("test error message")
            recovery.log_error(test_error, context="test context")

            # セッションに記録されたことを確認
            mock_manager.set.assert_called()

            # ファイルに記録されたことを確認
            assert recovery.error_log_file.exists()
            content = recovery.error_log_file.read_text()
            assert "test error message" in content
            assert "test context" in content


class TestSafeExecute:
    """safe_execute関数のテスト"""

    @patch("error_recovery.get_session_manager")
    def test_safe_execute_success(self, mock_session):
        """成功時のsafe_execute"""
        from error_recovery import safe_execute

        mock_manager = MagicMock()
        mock_manager.get.return_value = []
        mock_session.return_value = mock_manager

        def success_func():
            return 42

        result = safe_execute(success_func)
        assert result == 42

    @patch("error_recovery.get_session_manager")
    def test_safe_execute_failure(self, mock_session):
        """失敗時のsafe_execute"""
        from error_recovery import safe_execute

        mock_manager = MagicMock()
        mock_manager.get.return_value = []
        mock_session.return_value = mock_manager

        def fail_func():
            raise ValueError("error")

        result = safe_execute(fail_func)
        assert result is None
