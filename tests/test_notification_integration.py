"""
tests/test_notification_integration.py - notification_integration.py ユニットテスト
"""

import logging
from unittest.mock import MagicMock, patch

import pytest


class TestNotifyLongRunningExcept:
    """notify_task_progress デコレータの except ブロック(L225-228)テスト"""

    @patch("src.notification_integration.play_notification")
    def test_notify_task_progress_exception_reraises(self, mock_play):
        """デコレートした関数が例外を投げると、ERROR通知後にre-raise"""
        from src.notification_integration import NotificationType, notify_task_progress

        @notify_task_progress(total_steps=3)
        def failing_func():
            raise RuntimeError("something went wrong")

        with pytest.raises(RuntimeError, match="something went wrong"):
            failing_func()

        # ERROR通知が呼ばれたことを確認
        error_calls = [c for c in mock_play.call_args_list if c[0][0] == NotificationType.ERROR]
        assert len(error_calls) == 1
        assert "Failed failing_func" in error_calls[0][0][1]


class TestNotificationLoggerEmit:
    """NotificationLogger.emit の WARNING/INFO 分岐(L286, L288)テスト"""

    @patch("src.notification_integration.play_notification")
    @patch("src.notification_integration.get_configured_notification_system")
    def test_emit_warning_level(self, mock_system, mock_play):
        """WARNING レベルのログレコードで WARNING 通知"""
        from src.notification_integration import NotificationLogger, NotificationType

        handler = NotificationLogger(level=logging.DEBUG)

        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="",
            lineno=0,
            msg="warning message",
            args=(),
            exc_info=None,
        )

        handler.emit(record)

        mock_play.assert_called_once()
        call_args = mock_play.call_args
        assert call_args[0][0] == NotificationType.WARNING

    @patch("src.notification_integration.play_notification")
    @patch("src.notification_integration.get_configured_notification_system")
    def test_emit_info_level(self, mock_system, mock_play):
        """INFO レベルのログレコードで INFO 通知"""
        from src.notification_integration import NotificationLogger, NotificationType

        handler = NotificationLogger(level=logging.DEBUG)

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="info message",
            args=(),
            exc_info=None,
        )

        handler.emit(record)

        mock_play.assert_called_once()
        call_args = mock_play.call_args
        assert call_args[0][0] == NotificationType.INFO


class TestSetupNotificationLogging:
    """setup_notification_logging 関数(L298-299)テスト"""

    @patch("src.notification_integration.get_configured_notification_system")
    def test_setup_adds_handler(self, mock_system):
        """setup_notification_logging がルートロガーにハンドラを追加する"""
        from src.notification_integration import (
            NotificationLogger,
            setup_notification_logging,
        )

        root_logger = logging.getLogger()
        initial_count = len(root_logger.handlers)

        setup_notification_logging(level=logging.WARNING)

        assert len(root_logger.handlers) == initial_count + 1
        added = root_logger.handlers[-1]
        assert isinstance(added, NotificationLogger)

        # クリーンアップ
        root_logger.removeHandler(added)


class TestNotificationLoggerEmitAdditional:
    """NotificationLogger.emit の ERROR/DEBUG 分岐テスト"""

    @patch("src.notification_integration.play_notification")
    @patch("src.notification_integration.get_configured_notification_system")
    def test_emit_error_level(self, mock_system, mock_play):
        """ERROR レベルのログレコードで ERROR 通知(L284)"""
        from src.notification_integration import NotificationLogger, NotificationType

        handler = NotificationLogger(level=logging.DEBUG)

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="error message",
            args=(),
            exc_info=None,
        )

        handler.emit(record)

        mock_play.assert_called_once()
        call_args = mock_play.call_args
        assert call_args[0][0] == NotificationType.ERROR

    @patch("src.notification_integration.play_notification")
    @patch("src.notification_integration.get_configured_notification_system")
    def test_emit_debug_level_skipped(self, mock_system, mock_play):
        """DEBUG レベルのログレコードはスキップ(L290)"""
        from src.notification_integration import NotificationLogger

        handler = NotificationLogger(level=logging.DEBUG)

        record = logging.LogRecord(
            name="test",
            level=logging.DEBUG,
            pathname="",
            lineno=0,
            msg="debug message",
            args=(),
            exc_info=None,
        )

        handler.emit(record)

        mock_play.assert_not_called()
