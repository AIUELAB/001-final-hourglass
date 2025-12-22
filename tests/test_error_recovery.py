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

    @patch("error_recovery.get_session_manager")
    def test_safe_execute_with_args(self, mock_session):
        """引数付きのsafe_execute"""
        from error_recovery import safe_execute

        mock_manager = MagicMock()
        mock_manager.get.return_value = []
        mock_session.return_value = mock_manager

        def add_func(a, b):
            return a + b

        result = safe_execute(add_func, 3, 4)
        assert result == 7


class TestWithRetry:
    """with_retryデコレーターのテスト"""

    def test_retry_success_first_attempt(self):
        """初回成功"""
        from error_recovery import with_retry

        @with_retry(max_retries=3)
        def always_success():
            return "success"

        result = always_success()
        assert result == "success"

    def test_retry_success_after_failures(self):
        """リトライ後成功"""
        from error_recovery import with_retry

        call_count = 0

        @with_retry(max_retries=3, delay=0)
        def eventual_success():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("temporary error")
            return "success"

        result = eventual_success()
        assert result == "success"
        assert call_count == 3

    def test_retry_all_failures(self):
        """全リトライ失敗"""
        import pytest
        from error_recovery import with_retry

        @with_retry(max_retries=2, delay=0)
        def always_fail():
            raise ValueError("always fails")

        with pytest.raises(ValueError):
            always_fail()

    def test_retry_with_backoff(self):
        """バックオフ付きリトライ"""
        from error_recovery import with_retry

        @with_retry(max_retries=1, delay=0, backoff=2.0)
        def success_func():
            return 42

        result = success_func()
        assert result == 42


class TestErrorHandler:
    """ErrorHandlerコンテキストマネージャーのテスト"""

    @patch("error_recovery.get_session_manager")
    def test_error_handler_no_error(self, mock_session):
        """エラーなし"""
        from error_recovery import ErrorHandler

        mock_manager = MagicMock()
        mock_manager.get.return_value = []
        mock_session.return_value = mock_manager

        with ErrorHandler(context="test"):
            result = 1 + 1
        assert result == 2

    @patch("error_recovery.get_session_manager")
    def test_error_handler_suppress_error(self, mock_session):
        """エラー抑制"""
        from error_recovery import ErrorHandler

        mock_manager = MagicMock()
        mock_manager.get.return_value = []
        mock_manager.restore_session.return_value = False
        mock_session.return_value = mock_manager

        # suppress=Trueでエラーが抑制される
        with ErrorHandler(context="test", suppress=True):
            raise ValueError("test error")
        # ここに到達すればエラーは抑制された

    @patch("error_recovery.get_session_manager")
    def test_error_handler_not_suppress(self, mock_session):
        """エラー非抑制"""
        import pytest
        from error_recovery import ErrorHandler

        mock_manager = MagicMock()
        mock_manager.get.return_value = []
        mock_session.return_value = mock_manager

        # suppress=Falseでエラーは再送出される
        with pytest.raises(ValueError):
            with ErrorHandler(context="test", suppress=False):
                raise ValueError("test error")

    @patch("error_recovery.get_session_manager")
    def test_error_handler_with_recovery_action(self, mock_session):
        """復旧アクション付き"""
        from error_recovery import ErrorHandler

        mock_manager = MagicMock()
        mock_manager.get.return_value = []
        mock_manager.restore_session.return_value = True
        mock_session.return_value = mock_manager

        recovery_called = False

        def recovery_action():
            nonlocal recovery_called
            recovery_called = True

        with ErrorHandler(context="test", suppress=True, recovery_action=recovery_action):
            raise ValueError("test")

        assert recovery_called is True


class TestRecoveryActions:
    """復旧アクションテスト"""

    def test_recovery_actions_dict_exists(self):
        """RECOVERY_ACTIONSが存在"""
        from error_recovery import RECOVERY_ACTIONS

        assert isinstance(RECOVERY_ACTIONS, dict)
        assert FileNotFoundError in RECOVERY_ACTIONS
        assert PermissionError in RECOVERY_ACTIONS
        assert ConnectionError in RECOVERY_ACTIONS
        assert KeyError in RECOVERY_ACTIONS
        assert ValueError in RECOVERY_ACTIONS

    def test_get_recovery_action_known_error(self):
        """既知のエラータイプ"""
        from error_recovery import get_recovery_action

        error = ValueError("test")
        action = get_recovery_action(error)
        assert action is not None

    def test_get_recovery_action_file_not_found(self):
        """FileNotFoundError"""
        from error_recovery import get_recovery_action

        error = FileNotFoundError("test file")
        action = get_recovery_action(error)
        assert action is not None


class TestRecoverFromError:
    """recover_from_errorメソッドのテスト"""

    @patch("error_recovery.get_session_manager")
    def test_recover_with_session_restore(self, mock_session):
        """セッション復元成功"""
        from error_recovery import ErrorRecovery

        mock_manager = MagicMock()
        mock_manager.get.return_value = []
        mock_manager.restore_session.return_value = True
        mock_session.return_value = mock_manager

        recovery = ErrorRecovery()
        error = ValueError("test")
        result = recovery.recover_from_error(error)
        assert result is True

    @patch("error_recovery.get_session_manager")
    def test_recover_session_restore_fail(self, mock_session):
        """セッション復元失敗"""
        from error_recovery import ErrorRecovery

        mock_manager = MagicMock()
        mock_manager.get.return_value = []
        mock_manager.restore_session.return_value = False
        mock_session.return_value = mock_manager

        recovery = ErrorRecovery()
        error = ValueError("test")
        result = recovery.recover_from_error(error)
        assert result is False

    @patch("error_recovery.get_session_manager")
    def test_recover_with_action(self, mock_session):
        """復旧アクション付き"""
        from error_recovery import ErrorRecovery

        mock_manager = MagicMock()
        mock_manager.get.return_value = []
        mock_manager.restore_session.return_value = True
        mock_session.return_value = mock_manager

        action_called = False

        def recovery_action():
            nonlocal action_called
            action_called = True

        recovery = ErrorRecovery()
        error = ValueError("test")
        result = recovery.recover_from_error(error, recovery_action=recovery_action)
        assert result is True
        assert action_called is True

    @patch("error_recovery.get_session_manager")
    def test_recover_action_fails(self, mock_session):
        """復旧アクション失敗"""
        from error_recovery import ErrorRecovery

        mock_manager = MagicMock()
        mock_manager.get.return_value = []
        mock_manager.restore_session.return_value = True
        mock_session.return_value = mock_manager

        def failing_action():
            raise RuntimeError("action failed")

        recovery = ErrorRecovery()
        error = ValueError("test")
        result = recovery.recover_from_error(error, recovery_action=failing_action)
        assert result is False


class TestDisplayError:
    """display_errorメソッドのテスト"""

    @patch("error_recovery.get_session_manager")
    @patch("error_recovery.console")
    def test_display_error(self, mock_console, mock_session):
        """エラー表示"""
        from error_recovery import ErrorRecovery

        mock_manager = MagicMock()
        mock_manager.get.return_value = []
        mock_session.return_value = mock_manager

        recovery = ErrorRecovery()
        error = ValueError("test error")
        recovery.display_error(error, context="test")

        # consoleが呼ばれたことを確認
        mock_console.print.assert_called()
