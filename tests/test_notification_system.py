"""
AudioNotificationSystem テストモジュール

notification_system.py の単体テストを提供します。
"""

import subprocess

import pytest
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

from src.notification_system import (
    NotificationType,
    AudioNotificationSystem,
    notify_success,
    notify_error,
    notify_task_complete,
    notify_progress,
    get_notification_system,
)


class TestNotificationType:
    """NotificationType Enumのテスト"""

    def test_success_type(self):
        """SUCCESS タイプが存在"""
        assert NotificationType.SUCCESS.value == "success"

    def test_error_type(self):
        """ERROR タイプが存在"""
        assert NotificationType.ERROR.value == "error"

    def test_warning_type(self):
        """WARNING タイプが存在"""
        assert NotificationType.WARNING.value == "warning"

    def test_info_type(self):
        """INFO タイプが存在"""
        assert NotificationType.INFO.value == "info"

    def test_task_start_type(self):
        """TASK_START タイプが存在"""
        assert NotificationType.TASK_START.value == "task_start"

    def test_task_complete_type(self):
        """TASK_COMPLETE タイプが存在"""
        assert NotificationType.TASK_COMPLETE.value == "task_complete"

    def test_progress_type(self):
        """PROGRESS タイプが存在"""
        assert NotificationType.PROGRESS.value == "progress"

    def test_waiting_type(self):
        """WAITING タイプが存在"""
        assert NotificationType.WAITING.value == "waiting"

    def test_all_types_count(self):
        """全タイプ数"""
        assert len(NotificationType) == 8


class TestAudioNotificationSystemInit:
    """初期化テスト"""

    @patch("src.notification_system.AudioNotificationSystem._test_audio_system")
    def test_init_default(self, mock_test):
        """デフォルト初期化"""
        mock_test.return_value = True
        system = AudioNotificationSystem()

        assert system.enabled is True
        assert system.volume == 0.7
        assert system.max_duration == 2.0
        assert system.custom_sounds_dir is None

    @patch("src.notification_system.AudioNotificationSystem._test_audio_system")
    def test_init_disabled(self, mock_test):
        """無効化状態で初期化"""
        mock_test.return_value = True
        system = AudioNotificationSystem(enabled=False)

        assert system.enabled is False

    @patch("src.notification_system.AudioNotificationSystem._test_audio_system")
    def test_init_custom_volume(self, mock_test):
        """カスタムボリュームで初期化"""
        mock_test.return_value = True
        system = AudioNotificationSystem(volume=0.5)

        assert system.volume == 0.5

    @patch("src.notification_system.AudioNotificationSystem._test_audio_system")
    def test_init_volume_clamped(self, mock_test):
        """ボリュームがクランプされる"""
        mock_test.return_value = True

        system_high = AudioNotificationSystem(volume=1.5)
        assert system_high.volume == 1.0

        system_low = AudioNotificationSystem(volume=-0.5)
        assert system_low.volume == 0.0

    @patch("src.notification_system.AudioNotificationSystem._test_audio_system")
    def test_init_custom_sounds_dir(self, mock_test, tmp_path):
        """カスタムサウンドディレクトリで初期化"""
        mock_test.return_value = True
        sounds_dir = tmp_path / "sounds"
        system = AudioNotificationSystem(custom_sounds_dir=str(sounds_dir))

        assert system.custom_sounds_dir == sounds_dir
        assert sounds_dir.exists()


class TestSoundConfig:
    """サウンド設定テスト"""

    @patch("src.notification_system.AudioNotificationSystem._test_audio_system")
    def test_default_config_has_all_types(self, mock_test):
        """全通知タイプの設定が存在"""
        mock_test.return_value = True
        system = AudioNotificationSystem()

        for notification_type in NotificationType:
            assert notification_type in system.sound_config

    @patch("src.notification_system.AudioNotificationSystem._test_audio_system")
    def test_config_has_required_keys(self, mock_test):
        """設定に必要なキーが存在"""
        mock_test.return_value = True
        system = AudioNotificationSystem()

        for config in system.sound_config.values():
            assert "frequency" in config
            assert "duration" in config
            assert "system_sound" in config
            assert "description" in config


class TestEnableDisable:
    """有効/無効化テスト"""

    @patch("src.notification_system.AudioNotificationSystem._test_audio_system")
    def test_enable(self, mock_test):
        """有効化"""
        mock_test.return_value = True
        system = AudioNotificationSystem(enabled=False)

        system.enable()
        assert system.enabled is True

    @patch("src.notification_system.AudioNotificationSystem._test_audio_system")
    def test_disable(self, mock_test):
        """無効化"""
        mock_test.return_value = True
        system = AudioNotificationSystem(enabled=True)

        system.disable()
        assert system.enabled is False


class TestSetVolume:
    """ボリューム設定テスト"""

    @patch("src.notification_system.AudioNotificationSystem._test_audio_system")
    def test_set_volume(self, mock_test):
        """ボリューム設定"""
        mock_test.return_value = True
        system = AudioNotificationSystem()

        system.set_volume(0.3)
        assert system.volume == 0.3

    @patch("src.notification_system.AudioNotificationSystem._test_audio_system")
    def test_set_volume_clamped_high(self, mock_test):
        """高いボリュームがクランプされる"""
        mock_test.return_value = True
        system = AudioNotificationSystem()

        system.set_volume(2.0)
        assert system.volume == 1.0

    @patch("src.notification_system.AudioNotificationSystem._test_audio_system")
    def test_set_volume_clamped_low(self, mock_test):
        """低いボリュームがクランプされる"""
        mock_test.return_value = True
        system = AudioNotificationSystem()

        system.set_volume(-1.0)
        assert system.volume == 0.0


class TestGetStatus:
    """ステータス取得テスト"""

    @patch("src.notification_system.AudioNotificationSystem._test_audio_system")
    def test_get_status(self, mock_test):
        """ステータス取得"""
        mock_test.return_value = True
        system = AudioNotificationSystem(volume=0.8)

        status = system.get_status()

        assert status["enabled"] is True
        assert status["volume"] == 0.8
        assert status["max_duration"] == 2.0
        assert "platform" in status
        assert "available_notifications" in status
        assert len(status["available_notifications"]) == 8

    @patch("src.notification_system.AudioNotificationSystem._test_audio_system")
    def test_get_status_with_custom_dir(self, mock_test, tmp_path):
        """カスタムディレクトリ付きステータス"""
        mock_test.return_value = True
        sounds_dir = tmp_path / "sounds"
        system = AudioNotificationSystem(custom_sounds_dir=str(sounds_dir))

        status = system.get_status()

        assert status["custom_sounds_dir"] == str(sounds_dir)


class TestPlayNotification:
    """play_notification メソッドのテスト"""

    @patch("src.notification_system.AudioNotificationSystem._test_audio_system")
    def test_play_when_disabled(self, mock_test):
        """無効時は即座にTrue"""
        mock_test.return_value = True
        system = AudioNotificationSystem(enabled=False)

        result = system.play_notification(NotificationType.SUCCESS)
        assert result is True

    @patch("src.notification_system.AudioNotificationSystem._test_audio_system")
    @patch("src.notification_system.AudioNotificationSystem._play_custom_sound")
    @patch("src.notification_system.AudioNotificationSystem._play_system_sound")
    @patch("src.notification_system.AudioNotificationSystem._play_generated_beep")
    def test_play_tries_methods_in_order(self, mock_beep, mock_system, mock_custom, mock_test):
        """再生メソッドを順番に試行"""
        mock_test.return_value = True
        mock_custom.return_value = False
        mock_system.return_value = False
        mock_beep.return_value = True

        system = AudioNotificationSystem()
        result = system.play_notification(NotificationType.SUCCESS)

        assert result is True
        mock_custom.assert_called_once()
        mock_system.assert_called_once()
        mock_beep.assert_called_once()

    @patch("src.notification_system.AudioNotificationSystem._test_audio_system")
    @patch("src.notification_system.AudioNotificationSystem._play_custom_sound")
    def test_play_custom_sound_success(self, mock_custom, mock_test):
        """カスタムサウンド成功"""
        mock_test.return_value = True
        mock_custom.return_value = True

        system = AudioNotificationSystem()
        result = system.play_notification(NotificationType.SUCCESS)

        assert result is True

    @patch("src.notification_system.AudioNotificationSystem._test_audio_system")
    @patch("src.notification_system.AudioNotificationSystem._play_custom_sound")
    @patch("src.notification_system.AudioNotificationSystem._play_system_sound")
    @patch("src.notification_system.AudioNotificationSystem._play_generated_beep")
    def test_play_all_methods_fail(self, mock_beep, mock_system, mock_custom, mock_test):
        """全メソッド失敗"""
        mock_test.return_value = True
        mock_custom.return_value = False
        mock_system.return_value = False
        mock_beep.return_value = False

        system = AudioNotificationSystem()
        result = system.play_notification(NotificationType.SUCCESS)

        assert result is False

    @patch("src.notification_system.AudioNotificationSystem._test_audio_system")
    @patch("src.notification_system.AudioNotificationSystem._play_custom_sound")
    def test_play_with_repeat(self, mock_custom, mock_test):
        """リピート再生"""
        mock_test.return_value = True
        mock_custom.return_value = True

        system = AudioNotificationSystem()
        result = system.play_notification(NotificationType.SUCCESS, repeat=3)

        assert result is True
        assert mock_custom.call_count == 3


class TestPlayCustomSound:
    """_play_custom_sound メソッドのテスト"""

    @patch("src.notification_system.AudioNotificationSystem._test_audio_system")
    def test_no_custom_dir(self, mock_test):
        """カスタムディレクトリなし"""
        mock_test.return_value = True
        system = AudioNotificationSystem()

        result = system._play_custom_sound(NotificationType.SUCCESS)
        assert result is False

    @patch("src.notification_system.AudioNotificationSystem._test_audio_system")
    @patch("src.notification_system.AudioNotificationSystem._play_sound_file")
    def test_custom_sound_found(self, mock_play_file, mock_test, tmp_path):
        """カスタムサウンドファイルが見つかった"""
        mock_test.return_value = True
        mock_play_file.return_value = True

        sounds_dir = tmp_path / "sounds"
        sounds_dir.mkdir()
        (sounds_dir / "success.wav").touch()

        system = AudioNotificationSystem(custom_sounds_dir=str(sounds_dir))
        result = system._play_custom_sound(NotificationType.SUCCESS)

        assert result is True
        mock_play_file.assert_called_once()

    @patch("src.notification_system.AudioNotificationSystem._test_audio_system")
    def test_custom_sound_not_found(self, mock_test, tmp_path):
        """カスタムサウンドファイルが見つからない"""
        mock_test.return_value = True

        sounds_dir = tmp_path / "sounds"
        sounds_dir.mkdir()

        system = AudioNotificationSystem(custom_sounds_dir=str(sounds_dir))
        result = system._play_custom_sound(NotificationType.SUCCESS)

        assert result is False


class TestPlaySequence:
    """play_sequence メソッドのテスト"""

    @patch("src.notification_system.AudioNotificationSystem._test_audio_system")
    @patch("src.notification_system.AudioNotificationSystem.play_notification")
    @patch("time.sleep")
    def test_play_sequence_synchronous(self, mock_sleep, mock_play, mock_test):
        """同期シーケンス再生"""
        mock_test.return_value = True
        mock_play.return_value = True

        system = AudioNotificationSystem()
        sequence = [NotificationType.SUCCESS, NotificationType.INFO, NotificationType.ERROR]

        system.play_sequence(sequence, delay=0.1, background=False)

        assert mock_play.call_count == 3
        assert mock_sleep.call_count == 2  # 間のディレイ

    @patch("src.notification_system.AudioNotificationSystem._test_audio_system")
    @patch("src.notification_system.AudioNotificationSystem.play_notification")
    def test_play_sequence_background(self, mock_play, mock_test):
        """バックグラウンドシーケンス再生"""
        mock_test.return_value = True
        mock_play.return_value = True

        system = AudioNotificationSystem()
        sequence = [NotificationType.SUCCESS]

        system.play_sequence(sequence, delay=0.01, background=True)

        # バックグラウンドスレッドが完了するまで少し待機
        import time

        time.sleep(0.1)

        mock_play.assert_called()


class TestConvenienceFunctions:
    """便利関数のテスト"""

    @patch("src.notification_system.AudioNotificationSystem._test_audio_system")
    @patch("src.notification_system.AudioNotificationSystem.play_notification")
    def test_notify_success(self, mock_play, mock_test):
        """notify_success関数"""
        mock_test.return_value = True
        mock_play.return_value = True

        notify_success("Test message")

        mock_play.assert_called_once()
        call_args = mock_play.call_args
        assert call_args[0][0] == NotificationType.SUCCESS

    @patch("src.notification_system.AudioNotificationSystem._test_audio_system")
    @patch("src.notification_system.AudioNotificationSystem.play_notification")
    def test_notify_error(self, mock_play, mock_test):
        """notify_error関数"""
        mock_test.return_value = True
        mock_play.return_value = True

        notify_error("Error message")

        mock_play.assert_called_once()
        call_args = mock_play.call_args
        assert call_args[0][0] == NotificationType.ERROR

    @patch("src.notification_system.AudioNotificationSystem._test_audio_system")
    @patch("src.notification_system.AudioNotificationSystem.play_notification")
    def test_notify_task_complete(self, mock_play, mock_test):
        """notify_task_complete関数"""
        mock_test.return_value = True
        mock_play.return_value = True

        notify_task_complete("Task done")

        mock_play.assert_called_once()
        call_args = mock_play.call_args
        assert call_args[0][0] == NotificationType.TASK_COMPLETE

    @patch("src.notification_system.AudioNotificationSystem._test_audio_system")
    @patch("src.notification_system.AudioNotificationSystem.play_notification")
    def test_notify_progress(self, mock_play, mock_test):
        """notify_progress関数"""
        mock_test.return_value = True
        mock_play.return_value = True

        notify_progress("Progress update")

        mock_play.assert_called_once()
        call_args = mock_play.call_args
        assert call_args[0][0] == NotificationType.PROGRESS


class TestGetNotificationSystem:
    """get_notification_system 関数のテスト"""

    @patch("src.notification_system.AudioNotificationSystem._test_audio_system")
    def test_creates_singleton(self, mock_test):
        """シングルトンを作成"""
        mock_test.return_value = True

        # グローバル変数をリセット
        import src.notification_system as ns

        ns._global_notification_system = None

        system1 = get_notification_system()
        system2 = get_notification_system()

        assert system1 is system2

    @patch("src.notification_system.AudioNotificationSystem._test_audio_system")
    def test_accepts_kwargs(self, mock_test):
        """引数を受け入れる"""
        mock_test.return_value = True

        # グローバル変数をリセット
        import src.notification_system as ns

        ns._global_notification_system = None

        system = get_notification_system(volume=0.5, enabled=False)

        assert system.volume == 0.5
        assert system.enabled is False


class TestPlatformSpecificMethods:
    """プラットフォーム固有メソッドのテスト"""

    @patch("src.notification_system.AudioNotificationSystem._test_audio_system")
    @patch("subprocess.run")
    def test_play_macos_beep(self, mock_run, mock_test):
        """macOS beep再生"""
        mock_test.return_value = True
        mock_run.return_value = MagicMock(returncode=0)

        system = AudioNotificationSystem()
        result = system._play_macos_beep([500, 600], 0.1)

        assert result is True
        assert mock_run.call_count >= 1

    @patch("src.notification_system.AudioNotificationSystem._test_audio_system")
    @patch("subprocess.run")
    def test_play_macos_beep_failure(self, mock_run, mock_test):
        """macOS beep再生失敗"""
        mock_test.return_value = True
        mock_run.side_effect = Exception("Command failed")

        system = AudioNotificationSystem()
        result = system._play_macos_beep([500], 0.1)

        assert result is False

    @patch("src.notification_system.AudioNotificationSystem._test_audio_system")
    def test_play_windows_beep_no_winsound(self, mock_test):
        """Windowsでwinsoundなし"""
        mock_test.return_value = True

        # winsoundをNoneに設定
        import src.notification_system as ns

        original_winsound = ns.winsound
        ns.winsound = None

        system = AudioNotificationSystem()
        result = system._play_windows_beep([500], 0.1)

        # 元に戻す
        ns.winsound = original_winsound

        assert result is False


class TestAudioSystemTest:
    """_test_audio_system メソッドのテスト"""

    def test_test_audio_when_disabled(self):
        """無効時はTrueを返す"""
        with patch("subprocess.run"):
            system = AudioNotificationSystem(enabled=False)
            # 無効時は_test_audio_systemが呼ばれてもTrueを返す
            result = system._test_audio_system()
            assert result is True

    @patch("subprocess.run")
    def test_test_audio_darwin_success(self, mock_run):
        """macOSでオーディオテスト成功"""
        mock_run.return_value = MagicMock(returncode=0)

        system = AudioNotificationSystem.__new__(AudioNotificationSystem)
        system.enabled = True
        system.platform = "darwin"
        system.logger = MagicMock()

        result = system._test_audio_system()
        assert result is True

    @patch("subprocess.run")
    def test_test_audio_linux_success(self, mock_run):
        """Linuxでオーディオテスト成功"""
        mock_run.return_value = MagicMock(returncode=0)

        system = AudioNotificationSystem.__new__(AudioNotificationSystem)
        system.enabled = True
        system.platform = "linux"
        system.logger = MagicMock()

        result = system._test_audio_system()
        assert result is True

    @patch("subprocess.run")
    def test_test_audio_failure(self, mock_run):
        """オーディオテスト失敗"""
        mock_run.side_effect = Exception("Audio failed")

        system = AudioNotificationSystem.__new__(AudioNotificationSystem)
        system.enabled = True
        system.platform = "darwin"
        system.logger = MagicMock()

        result = system._test_audio_system()
        assert result is False


class TestPlaySoundFile:
    """_play_sound_file メソッドのテスト"""

    @patch("src.notification_system.AudioNotificationSystem._test_audio_system")
    @patch("subprocess.run")
    def test_play_sound_file_darwin_success(self, mock_run, mock_test, tmp_path):
        """macOSでサウンドファイル再生成功"""
        mock_test.return_value = True
        mock_run.return_value = MagicMock(returncode=0)

        system = AudioNotificationSystem()
        system.platform = "darwin"

        sound_file = tmp_path / "test.wav"
        sound_file.touch()

        result = system._play_sound_file(sound_file)
        assert result is True
        mock_run.assert_called_once()

    @patch("src.notification_system.AudioNotificationSystem._test_audio_system")
    @patch("subprocess.run")
    def test_play_sound_file_linux_success(self, mock_run, mock_test, tmp_path):
        """Linuxでサウンドファイル再生成功"""
        mock_test.return_value = True
        # which コマンドも run コマンドも成功
        mock_run.return_value = MagicMock(returncode=0)

        system = AudioNotificationSystem()
        system.platform = "linux"

        sound_file = tmp_path / "test.wav"
        sound_file.touch()

        result = system._play_sound_file(sound_file)
        assert result is True

    @patch("src.notification_system.AudioNotificationSystem._test_audio_system")
    @patch("subprocess.run")
    def test_play_sound_file_windows_success(self, mock_run, mock_test, tmp_path):
        """Windowsでサウンドファイル再生成功"""
        mock_test.return_value = True
        mock_run.return_value = MagicMock(returncode=0)

        system = AudioNotificationSystem()
        system.platform = "windows"

        sound_file = tmp_path / "test.wav"
        sound_file.touch()

        result = system._play_sound_file(sound_file)
        assert result is True

    @patch("src.notification_system.AudioNotificationSystem._test_audio_system")
    @patch("subprocess.run")
    def test_play_sound_file_failure(self, mock_run, mock_test, tmp_path):
        """サウンドファイル再生失敗"""
        mock_test.return_value = True
        mock_run.side_effect = Exception("Failed to play")

        system = AudioNotificationSystem()
        system.platform = "darwin"

        sound_file = tmp_path / "test.wav"
        sound_file.touch()

        result = system._play_sound_file(sound_file)
        assert result is False


class TestPlaySystemSound:
    """_play_system_sound メソッドのテスト"""

    @patch("src.notification_system.AudioNotificationSystem._test_audio_system")
    def test_play_system_sound_no_config(self, mock_test):
        """設定なしの場合はFalse"""
        mock_test.return_value = True
        system = AudioNotificationSystem()
        # 設定にsystem_soundがない場合
        system.sound_config[NotificationType.SUCCESS] = {"system_sound": None}

        result = system._play_system_sound(NotificationType.SUCCESS)
        assert result is False

    @patch("src.notification_system.AudioNotificationSystem._test_audio_system")
    @patch("subprocess.run")
    def test_play_system_sound_darwin_success(self, mock_run, mock_test):
        """macOSでシステムサウンド再生成功"""
        mock_test.return_value = True
        mock_run.return_value = MagicMock(returncode=0)

        system = AudioNotificationSystem()
        system.platform = "darwin"

        result = system._play_system_sound(NotificationType.SUCCESS)
        assert result is True

    @patch("src.notification_system.AudioNotificationSystem._test_audio_system")
    @patch("subprocess.run")
    def test_play_system_sound_darwin_failure(self, mock_run, mock_test):
        """macOSでシステムサウンド再生失敗"""
        mock_test.return_value = True
        mock_run.side_effect = Exception("Sound not found")

        system = AudioNotificationSystem()
        system.platform = "darwin"

        result = system._play_system_sound(NotificationType.SUCCESS)
        assert result is False

    @patch("src.notification_system.AudioNotificationSystem._test_audio_system")
    @patch("src.notification_system.AudioNotificationSystem._play_sound_file")
    @patch("pathlib.Path.exists")
    def test_play_system_sound_linux_success(self, mock_exists, mock_play_file, mock_test):
        """Linuxでシステムサウンド再生成功"""
        mock_test.return_value = True
        mock_exists.return_value = True
        mock_play_file.return_value = True

        system = AudioNotificationSystem()
        system.platform = "linux"

        result = system._play_system_sound(NotificationType.SUCCESS)
        assert result is True


class TestPlayGeneratedBeep:
    """_play_generated_beep メソッドのテスト"""

    @patch("src.notification_system.AudioNotificationSystem._test_audio_system")
    @patch("src.notification_system.AudioNotificationSystem._play_macos_beep")
    def test_play_generated_beep_darwin(self, mock_macos, mock_test):
        """macOSでビープ生成"""
        mock_test.return_value = True
        mock_macos.return_value = True

        system = AudioNotificationSystem()
        system.platform = "darwin"

        result = system._play_generated_beep(NotificationType.SUCCESS)
        assert result is True
        mock_macos.assert_called_once()

    @patch("src.notification_system.AudioNotificationSystem._test_audio_system")
    @patch("src.notification_system.AudioNotificationSystem._play_linux_beep")
    def test_play_generated_beep_linux(self, mock_linux, mock_test):
        """Linuxでビープ生成"""
        mock_test.return_value = True
        mock_linux.return_value = True

        system = AudioNotificationSystem()
        system.platform = "linux"

        result = system._play_generated_beep(NotificationType.SUCCESS)
        assert result is True
        mock_linux.assert_called_once()

    @patch("src.notification_system.AudioNotificationSystem._test_audio_system")
    @patch("src.notification_system.AudioNotificationSystem._play_windows_beep")
    def test_play_generated_beep_windows(self, mock_windows, mock_test):
        """Windowsでビープ生成"""
        mock_test.return_value = True
        mock_windows.return_value = True

        system = AudioNotificationSystem()
        system.platform = "windows"

        result = system._play_generated_beep(NotificationType.SUCCESS)
        assert result is True
        mock_windows.assert_called_once()

    @patch("src.notification_system.AudioNotificationSystem._test_audio_system")
    @patch("src.notification_system.AudioNotificationSystem._play_macos_beep")
    def test_play_generated_beep_failure(self, mock_macos, mock_test):
        """ビープ生成失敗"""
        mock_test.return_value = True
        mock_macos.side_effect = Exception("Beep failed")

        system = AudioNotificationSystem()
        system.platform = "darwin"

        result = system._play_generated_beep(NotificationType.SUCCESS)
        assert result is False


class TestPlayLinuxBeep:
    """_play_linux_beep メソッドのテスト"""

    @patch("src.notification_system.AudioNotificationSystem._test_audio_system")
    @patch("subprocess.run")
    def test_play_linux_beep_speaker_test_success(self, mock_run, mock_test):
        """speaker-testで成功"""
        mock_test.return_value = True
        mock_run.return_value = MagicMock(returncode=0)

        system = AudioNotificationSystem()
        result = system._play_linux_beep([500], 0.1)

        assert result is True

    @patch("src.notification_system.AudioNotificationSystem._test_audio_system")
    @patch("subprocess.run")
    def test_play_linux_beep_pactl_success(self, mock_run, mock_test):
        """pactlで成功"""
        mock_test.return_value = True

        # speaker-test失敗、pactl成功
        def side_effect(*args, **kwargs):
            cmd = args[0]
            if cmd[0] == "speaker-test":
                raise subprocess.CalledProcessError(1, cmd)
            elif cmd[0] == "pactl":
                result = MagicMock()
                result.stdout = "123"  # module_id
                return result
            return MagicMock(returncode=0)

        mock_run.side_effect = side_effect

        system = AudioNotificationSystem()
        result = system._play_linux_beep([500], 0.1)

        assert result is True

    @patch("src.notification_system.AudioNotificationSystem._test_audio_system")
    @patch("subprocess.run")
    def test_play_linux_beep_beep_command_success(self, mock_run, mock_test):
        """beepコマンドで成功"""
        mock_test.return_value = True

        # speaker-test, pactl失敗、beep成功
        call_count = [0]

        def side_effect(*args, **kwargs):
            cmd = args[0]
            call_count[0] += 1
            if cmd[0] in ("speaker-test", "pactl"):
                raise subprocess.CalledProcessError(1, cmd)
            elif cmd[0] == "beep":
                return MagicMock(returncode=0)
            raise subprocess.CalledProcessError(1, cmd)

        mock_run.side_effect = side_effect

        system = AudioNotificationSystem()
        result = system._play_linux_beep([500], 0.1)

        assert result is True

    @patch("src.notification_system.AudioNotificationSystem._test_audio_system")
    @patch("subprocess.run")
    def test_play_linux_beep_all_fail(self, mock_run, mock_test):
        """全て失敗"""
        mock_test.return_value = True
        mock_run.side_effect = subprocess.CalledProcessError(1, "cmd")

        system = AudioNotificationSystem()
        result = system._play_linux_beep([500], 0.1)

        assert result is False
