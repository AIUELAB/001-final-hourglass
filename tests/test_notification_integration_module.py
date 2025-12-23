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


class TestNotificationConfigEnvVars:
    """NotificationConfig 環境変数テスト"""

    @patch.dict(os.environ, {"NOTIFICATIONS_MAX_DURATION": "5"})
    def test_int_env_valid(self):
        """有効な整数環境変数"""
        from src.notification_integration import NotificationConfig

        config = NotificationConfig()
        # max_durationはfloatだが、_get_int_envの他の使用箇所をテスト
        assert config.max_duration == 5.0

    @patch.dict(os.environ, {"NOTIFICATIONS_MAX_DURATION": "invalid"})
    def test_int_env_invalid(self):
        """無効な整数環境変数"""
        from src.notification_integration import NotificationConfig

        config = NotificationConfig()
        # デフォルト値
        assert config.max_duration == 2.0


class TestShouldNotifyTypes:
    """should_notify 通知タイプテスト"""

    @patch("src.notification_integration.config")
    def test_should_notify_warning(self, mock_config):
        """警告通知"""
        from src.notification_integration import NotificationType, should_notify

        mock_config.enabled = True
        mock_config.notify_warning = True

        assert should_notify(NotificationType.WARNING) is True

    @patch("src.notification_integration.config")
    def test_should_notify_error(self, mock_config):
        """エラー通知"""
        from src.notification_integration import NotificationType, should_notify

        mock_config.enabled = True
        mock_config.notify_error = True

        assert should_notify(NotificationType.ERROR) is True

    @patch("src.notification_integration.config")
    def test_should_notify_info(self, mock_config):
        """情報通知"""
        from src.notification_integration import NotificationType, should_notify

        mock_config.enabled = True
        mock_config.notify_info = True

        assert should_notify(NotificationType.INFO) is True

    @patch("src.notification_integration.config")
    def test_should_notify_progress(self, mock_config):
        """進捗通知"""
        from src.notification_integration import NotificationType, should_notify

        mock_config.enabled = True
        mock_config.notify_progress = True

        assert should_notify(NotificationType.PROGRESS) is True


class TestPlayNotificationRepeat:
    """play_notification リピートテスト"""

    @patch("src.notification_integration.should_notify", return_value=True)
    @patch("src.notification_integration.get_configured_notification_system")
    @patch("src.notification_integration.config")
    def test_play_notification_success_repeat(self, mock_config, mock_get_system, mock_should):
        """成功通知のリピート"""
        from src.notification_integration import NotificationType, play_notification

        mock_config.repeat_success = 3
        mock_system = MagicMock()
        mock_system.play_notification.return_value = True
        mock_get_system.return_value = mock_system

        result = play_notification(NotificationType.SUCCESS)

        assert result is True

    @patch("src.notification_integration.should_notify", return_value=True)
    @patch("src.notification_integration.get_configured_notification_system")
    @patch("src.notification_integration.config")
    def test_play_notification_warning_repeat(self, mock_config, mock_get_system, mock_should):
        """警告通知のリピート"""
        from src.notification_integration import NotificationType, play_notification

        mock_config.repeat_warning = 2
        mock_system = MagicMock()
        mock_system.play_notification.return_value = True
        mock_get_system.return_value = mock_system

        result = play_notification(NotificationType.WARNING)

        assert result is True


class TestNotifyWithSoundVerbose:
    """notify_with_sound verbose モードテスト"""

    @patch("src.notification_integration.play_notification")
    @patch("src.notification_integration.config")
    def test_decorator_verbose(self, mock_config, mock_play, capsys):
        """verboseモードのデコレータ"""
        from src.notification_integration import NotificationType, notify_with_sound

        mock_config.verbose = True
        mock_play.return_value = True

        @notify_with_sound(NotificationType.INFO, "Verbose test")
        def test_func():
            return "result"

        result = test_func()
        captured = capsys.readouterr()

        assert result == "result"
        assert "🔊" in captured.out


class TestQuickNotifyAllFunctions:
    """quick_notify_* 全関数テスト"""

    @patch("src.notification_integration.play_notification")
    def test_quick_notify_warning(self, mock_play):
        """quick_notify_warning"""
        from src.notification_integration import NotificationType, quick_notify_warning

        quick_notify_warning("Test warning")

        mock_play.assert_called_once()
        assert mock_play.call_args[0][0] == NotificationType.WARNING

    @patch("src.notification_integration.play_notification")
    def test_quick_notify_info(self, mock_play):
        """quick_notify_info"""
        from src.notification_integration import NotificationType, quick_notify_info

        quick_notify_info("Test info")

        mock_play.assert_called_once()
        assert mock_play.call_args[0][0] == NotificationType.INFO

    @patch("src.notification_integration.play_notification")
    def test_quick_notify_progress(self, mock_play):
        """quick_notify_progress"""
        from src.notification_integration import NotificationType, quick_notify_progress

        quick_notify_progress("Test progress")

        mock_play.assert_called_once()
        assert mock_play.call_args[0][0] == NotificationType.PROGRESS


class TestPrintNotificationStatus:
    """print_notification_status関数テスト"""

    @patch("src.notification_integration.get_notification_status")
    def test_print_status(self, mock_get_status, capsys):
        """ステータス出力"""
        from src.notification_integration import print_notification_status

        mock_get_status.return_value = {
            "config_enabled": True,
            "volume": 0.7,
        }

        print_notification_status()

        captured = capsys.readouterr()
        assert "Audio Notification System Status" in captured.out
        assert "config_enabled" in captured.out


class TestNotifyDataQualityCheck:
    """notify_data_quality_check デコレータテスト"""

    @patch("src.notification_integration.play_notification")
    @patch("src.notification_integration.config")
    def test_data_quality_check_decorator(self, mock_config, mock_play):
        """データ品質チェックデコレータ"""
        from src.notification_integration import notify_data_quality_check

        mock_config.verbose = False
        mock_play.return_value = True

        @notify_data_quality_check
        def check_duplicates():
            return "no duplicates"

        result = check_duplicates()

        assert result == "no duplicates"
        mock_play.assert_called()


class TestNotifyDataProcessing:
    """notify_data_processing デコレータテスト"""

    @patch("src.notification_integration.play_notification")
    @patch("src.notification_integration.config")
    def test_data_processing_decorator(self, mock_config, mock_play):
        """データ処理デコレータ"""
        from src.notification_integration import notify_data_processing

        mock_config.verbose = False
        mock_play.return_value = True

        @notify_data_processing
        def process_csv():
            return 100

        result = process_csv()

        assert result == 100
        mock_play.assert_called()


class TestNotifyAutomationTask:
    """notify_automation_task デコレータテスト"""

    @patch("src.notification_integration.play_notification")
    @patch("src.notification_integration.config")
    def test_automation_task_decorator(self, mock_config, mock_play):
        """自動化タスクデコレータ"""
        from src.notification_integration import notify_automation_task

        mock_config.verbose = False
        mock_play.return_value = True

        @notify_automation_task
        def backup_data():
            return "backup complete"

        result = backup_data()

        assert result == "backup complete"
        mock_play.assert_called()


class TestGetIntEnvValueError:
    """_get_int_env ValueError テスト（カバレッジ向上用）"""

    @patch.dict(os.environ, {"REPEAT_ERROR_NOTIFICATIONS": "not_a_number"})
    def test_int_env_invalid_returns_default(self):
        """無効な整数環境変数はデフォルト値を返す"""
        from src.notification_integration import NotificationConfig

        config = NotificationConfig()
        # 無効な値の場合、デフォルト値(2)が返る
        assert config.repeat_error == 2

    @patch.dict(os.environ, {"REPEAT_SUCCESS_NOTIFICATIONS": "abc"})
    def test_int_env_invalid_success_repeat(self):
        """成功リピートの無効値"""
        from src.notification_integration import NotificationConfig

        config = NotificationConfig()
        assert config.repeat_success == 1

    @patch.dict(os.environ, {"REPEAT_WARNING_NOTIFICATIONS": ""})
    def test_int_env_empty_string(self):
        """空文字列の場合"""
        from src.notification_integration import NotificationConfig

        config = NotificationConfig()
        assert config.repeat_warning == 1


class TestGetConfiguredNotificationSystemInit:
    """get_configured_notification_system 初期化テスト（カバレッジ向上用）"""

    def test_creates_new_system_when_none(self):
        """グローバル変数がNoneの時に新規作成"""
        import src.notification_integration as ni

        # グローバル変数をリセット
        original_system = ni.notification_system
        ni.notification_system = None

        try:
            system = ni.get_configured_notification_system()
            assert system is not None
            assert isinstance(system, ni.AudioNotificationSystem)
        finally:
            ni.notification_system = original_system

    def test_returns_existing_system(self):
        """既存システムがある場合は再利用"""
        import src.notification_integration as ni

        # 一度システムを取得
        system1 = ni.get_configured_notification_system()
        # 再度取得
        system2 = ni.get_configured_notification_system()
        # 同じインスタンスであることを確認
        assert system1 is system2


class TestPlayNotificationRepeatBranches:
    """play_notification repeat分岐テスト（カバレッジ向上用）"""

    @patch("src.notification_integration.should_notify", return_value=True)
    @patch("src.notification_integration.get_configured_notification_system")
    @patch("src.notification_integration.config")
    def test_play_notification_info_default_repeat(self, mock_config, mock_get_system, mock_should):
        """INFO通知のデフォルトrepeat=1"""
        from src.notification_integration import NotificationType, play_notification

        mock_system = MagicMock()
        mock_system.play_notification.return_value = True
        mock_get_system.return_value = mock_system

        result = play_notification(NotificationType.INFO)

        assert result is True
        # repeat=1でplay_notificationが呼ばれる
        mock_system.play_notification.assert_called_once()

    @patch("src.notification_integration.should_notify", return_value=True)
    @patch("src.notification_integration.get_configured_notification_system")
    @patch("src.notification_integration.config")
    def test_play_notification_waiting_default_repeat(self, mock_config, mock_get_system, mock_should):
        """WAITING通知のデフォルトrepeat=1"""
        from src.notification_integration import NotificationType, play_notification

        mock_system = MagicMock()
        mock_system.play_notification.return_value = True
        mock_get_system.return_value = mock_system

        result = play_notification(NotificationType.WAITING)

        assert result is True
        mock_system.play_notification.assert_called_once()

    @patch("src.notification_integration.should_notify", return_value=True)
    @patch("src.notification_integration.get_configured_notification_system")
    @patch("src.notification_integration.config")
    def test_play_notification_progress_default_repeat(self, mock_config, mock_get_system, mock_should):
        """PROGRESS通知のデフォルトrepeat=1"""
        from src.notification_integration import NotificationType, play_notification

        mock_system = MagicMock()
        mock_system.play_notification.return_value = True
        mock_get_system.return_value = mock_system

        result = play_notification(NotificationType.PROGRESS)

        assert result is True
        mock_system.play_notification.assert_called_once()

    @patch("src.notification_integration.should_notify", return_value=True)
    @patch("src.notification_integration.get_configured_notification_system")
    @patch("src.notification_integration.config")
    def test_play_notification_task_start_default_repeat(self, mock_config, mock_get_system, mock_should):
        """TASK_START通知のデフォルトrepeat=1"""
        from src.notification_integration import NotificationType, play_notification

        mock_system = MagicMock()
        mock_system.play_notification.return_value = True
        mock_get_system.return_value = mock_system

        result = play_notification(NotificationType.TASK_START)

        assert result is True
        mock_system.play_notification.assert_called_once()

    @patch("src.notification_integration.should_notify", return_value=True)
    @patch("src.notification_integration.get_configured_notification_system")
    @patch("src.notification_integration.config")
    def test_play_notification_task_complete_default_repeat(self, mock_config, mock_get_system, mock_should):
        """TASK_COMPLETE通知のデフォルトrepeat=1"""
        from src.notification_integration import NotificationType, play_notification

        mock_system = MagicMock()
        mock_system.play_notification.return_value = True
        mock_get_system.return_value = mock_system

        result = play_notification(NotificationType.TASK_COMPLETE)

        assert result is True
        mock_system.play_notification.assert_called_once()

    @patch("src.notification_integration.should_notify", return_value=True)
    @patch("src.notification_integration.get_configured_notification_system")
    @patch("src.notification_integration.config")
    def test_play_notification_with_explicit_repeat(self, mock_config, mock_get_system, mock_should):
        """明示的なrepeat指定"""
        from src.notification_integration import NotificationType, play_notification

        mock_system = MagicMock()
        mock_system.play_notification.return_value = True
        mock_get_system.return_value = mock_system

        result = play_notification(NotificationType.INFO, repeat=3)

        assert result is True
        # repeat=3が渡される
        call_args = mock_system.play_notification.call_args
        assert call_args[0][2] == 3  # 3番目の引数がrepeat
