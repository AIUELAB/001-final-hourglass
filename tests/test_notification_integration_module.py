"""
tests/test_notification_integration_module.py - notification_integration.py ユニットテスト
"""

import os
from unittest.mock import MagicMock, patch

import pytest


class TestNotificationConfig:
    """NotificationConfig クラステスト"""

    @patch.dict(os.environ, {}, clear=True)
    def test_default_config(self):
        """デフォルト設定"""
        from src.notification_integration import NotificationConfig

        config = NotificationConfig()

        assert config.enabled is True
        assert config.volume == 0.7
        assert config.max_duration == 2.0

    @patch.dict(os.environ, {"NOTIFICATIONS_ENABLED": "false"})
    def test_disabled_notifications(self):
        """通知無効化"""
        from src.notification_integration import NotificationConfig

        config = NotificationConfig()

        assert config.enabled is False

    @patch.dict(os.environ, {"NOTIFICATIONS_VOLUME": "0.5"})
    def test_custom_volume(self):
        """カスタム音量"""
        from src.notification_integration import NotificationConfig

        config = NotificationConfig()

        assert config.volume == 0.5

    @patch.dict(os.environ, {"NOTIFICATIONS_VOLUME": "invalid"})
    def test_invalid_float_defaults(self):
        """無効な浮動小数点はデフォルト"""
        from src.notification_integration import NotificationConfig

        config = NotificationConfig()

        assert config.volume == 0.7  # デフォルト値


class TestShouldNotify:
    """should_notify関数テスト"""

    @patch("src.notification_integration.config")
    def test_should_notify_disabled(self, mock_config):
        """通知が無効の場合"""
        from src.notification_integration import NotificationType, should_notify

        mock_config.enabled = False

        assert should_notify(NotificationType.SUCCESS) is False

    @patch("src.notification_integration.config")
    def test_should_notify_success(self, mock_config):
        """成功通知が有効の場合"""
        from src.notification_integration import NotificationType, should_notify

        mock_config.enabled = True
        mock_config.notify_success = True

        assert should_notify(NotificationType.SUCCESS) is True


class TestPlayNotification:
    """play_notification関数テスト"""

    @patch("src.notification_integration.should_notify", return_value=False)
    def test_play_notification_skipped(self, mock_should):
        """通知がスキップされる場合"""
        from src.notification_integration import NotificationType, play_notification

        result = play_notification(NotificationType.SUCCESS)

        assert result is True  # スキップは成功として扱う

    @patch("src.notification_integration.should_notify", return_value=True)
    @patch("src.notification_integration.get_configured_notification_system")
    @patch("src.notification_integration.config")
    def test_play_notification_with_repeat(self, mock_config, mock_get_system, mock_should):
        """リピート付き通知"""
        from src.notification_integration import NotificationType, play_notification

        mock_config.repeat_error = 2
        mock_system = MagicMock()
        mock_system.play_notification.return_value = True
        mock_get_system.return_value = mock_system

        result = play_notification(NotificationType.ERROR)

        assert result is True
        mock_system.play_notification.assert_called_once()


class TestNotifyWithSoundDecorator:
    """notify_with_sound デコレータテスト"""

    @patch("src.notification_integration.play_notification")
    @patch("src.notification_integration.config")
    def test_decorator_success(self, mock_config, mock_play):
        """正常実行時のデコレータ"""
        from src.notification_integration import NotificationType, notify_with_sound

        mock_config.verbose = False
        mock_play.return_value = True

        @notify_with_sound(NotificationType.INFO, "Test message")
        def test_func():
            return "result"

        result = test_func()

        assert result == "result"
        assert mock_play.call_count == 2  # 開始と成功

    @patch("src.notification_integration.play_notification")
    @patch("src.notification_integration.config")
    def test_decorator_exception(self, mock_config, mock_play):
        """例外時のデコレータ"""
        from src.notification_integration import NotificationType, notify_with_sound

        mock_config.verbose = False
        mock_play.return_value = True

        @notify_with_sound(NotificationType.INFO, "Test message")
        def test_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            test_func()

        # エラー通知が呼ばれる
        calls = mock_play.call_args_list
        assert any(c[0][0] == NotificationType.ERROR for c in calls)


class TestNotifyTaskProgressDecorator:
    """notify_task_progress デコレータテスト"""

    @patch("src.notification_integration.play_notification")
    def test_task_progress_decorator(self, mock_play):
        """タスク進捗デコレータ"""
        from src.notification_integration import notify_task_progress

        mock_play.return_value = True

        @notify_task_progress(total_steps=5)
        def test_task():
            return "done"

        result = test_task()

        assert result == "done"
        assert mock_play.call_count == 2  # 開始と完了


class TestNotificationContext:
    """notification_context コンテキストマネージャテスト"""

    @patch("src.notification_integration.play_notification")
    def test_context_success(self, mock_play):
        """正常終了時のコンテキスト"""
        from src.notification_integration import notification_context

        mock_play.return_value = True

        with notification_context(task_name="test task") as progress:
            progress("Step 1")

        assert mock_play.call_count == 3  # 開始、進捗、完了

    @patch("src.notification_integration.play_notification")
    def test_context_exception(self, mock_play):
        """例外時のコンテキスト"""
        from src.notification_integration import NotificationType, notification_context

        mock_play.return_value = True

        with pytest.raises(ValueError):
            with notification_context(task_name="test task"):
                raise ValueError("Test error")

        # エラー通知が呼ばれる
        calls = mock_play.call_args_list
        assert any(c[0][0] == NotificationType.ERROR for c in calls)


class TestNotificationLogger:
    """NotificationLogger クラステスト"""

    @patch("src.notification_integration.get_configured_notification_system")
    @patch("src.notification_integration.play_notification")
    def test_logger_error_level(self, mock_play, mock_get_system):
        """ERRORレベルのログ"""
        import logging

        from src.notification_integration import NotificationLogger

        mock_get_system.return_value = MagicMock()

        handler = NotificationLogger(level=logging.WARNING)

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="Test error",
            args=(),
            exc_info=None,
        )

        handler.emit(record)

        mock_play.assert_called_once()

    @patch("src.notification_integration.get_configured_notification_system")
    @patch("src.notification_integration.play_notification")
    def test_logger_debug_skipped(self, mock_play, mock_get_system):
        """DEBUGレベルはスキップ"""
        import logging

        from src.notification_integration import NotificationLogger

        mock_get_system.return_value = MagicMock()

        handler = NotificationLogger(level=logging.WARNING)

        record = logging.LogRecord(
            name="test",
            level=logging.DEBUG,
            pathname="",
            lineno=0,
            msg="Debug message",
            args=(),
            exc_info=None,
        )

        handler.emit(record)

        mock_play.assert_not_called()


class TestQuickNotifyFunctions:
    """quick_notify_* 関数テスト"""

    @patch("src.notification_integration.play_notification")
    def test_quick_notify_success(self, mock_play):
        """quick_notify_success"""
        from src.notification_integration import NotificationType, quick_notify_success

        quick_notify_success("Test success")

        mock_play.assert_called_once()
        assert mock_play.call_args[0][0] == NotificationType.SUCCESS

    @patch("src.notification_integration.play_notification")
    def test_quick_notify_error(self, mock_play):
        """quick_notify_error"""
        from src.notification_integration import NotificationType, quick_notify_error

        quick_notify_error("Test error")

        mock_play.assert_called_once()
        assert mock_play.call_args[0][0] == NotificationType.ERROR


class TestGetNotificationStatus:
    """get_notification_status関数テスト"""

    @patch("src.notification_integration.get_configured_notification_system")
    @patch("src.notification_integration.config")
    def test_get_status(self, mock_config, mock_get_system):
        """ステータス取得"""
        from src.notification_integration import get_notification_status

        mock_config.enabled = True
        mock_config.volume = 0.7
        mock_config.integrate_data_scripts = True
        mock_config.integrate_automation = True

        mock_system = MagicMock()
        mock_system.get_status.return_value = {"system_status": "ok"}
        mock_get_system.return_value = mock_system

        status = get_notification_status()

        assert "system_status" in status
        assert status["config_enabled"] is True
