#!/usr/bin/env python3
"""notification_system テスト"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from notification_system import AudioNotificationSystem, NotificationType


class TestNotificationType:
    """NotificationTypeのテスト"""

    def test_success_type(self):
        assert NotificationType.SUCCESS.value == "success"

    def test_error_type(self):
        assert NotificationType.ERROR.value == "error"

    def test_warning_type(self):
        assert NotificationType.WARNING.value == "warning"

    def test_info_type(self):
        assert NotificationType.INFO.value == "info"

    def test_task_start_type(self):
        assert NotificationType.TASK_START.value == "task_start"

    def test_task_complete_type(self):
        assert NotificationType.TASK_COMPLETE.value == "task_complete"


class TestAudioNotificationSystem:
    """AudioNotificationSystemのテスト"""

    def test_init_default(self):
        """デフォルト初期化"""
        system = AudioNotificationSystem()
        assert system.enabled is True
        assert system.volume == 0.7
        assert system.max_duration == 2.0

    def test_init_disabled(self):
        """無効化状態で初期化"""
        system = AudioNotificationSystem(enabled=False)
        assert system.enabled is False

    def test_init_custom_volume(self):
        """カスタム音量で初期化"""
        system = AudioNotificationSystem(volume=0.5)
        assert system.volume == 0.5

    def test_init_custom_sounds_dir(self):
        """カスタムサウンドディレクトリで初期化"""
        system = AudioNotificationSystem(custom_sounds_dir="/tmp/sounds")
        assert system.custom_sounds_dir == Path("/tmp/sounds")

    def test_init_max_duration(self):
        """最大時間設定"""
        system = AudioNotificationSystem(max_duration=5.0)
        assert system.max_duration == 5.0

    def test_default_max_duration(self):
        """デフォルト最大時間"""
        system = AudioNotificationSystem()
        assert system.max_duration == 2.0

    def test_volume_range(self):
        """音量範囲"""
        system = AudioNotificationSystem(volume=0.0)
        assert system.volume == 0.0

        system2 = AudioNotificationSystem(volume=1.0)
        assert system2.volume == 1.0

    def test_volume_clamp_min(self):
        """音量下限クランプ"""
        system = AudioNotificationSystem(volume=-0.5)
        assert system.volume == 0.0

    def test_volume_clamp_max(self):
        """音量上限クランプ"""
        system = AudioNotificationSystem(volume=1.5)
        assert system.volume == 1.0

    def test_platform_detection(self):
        """プラットフォーム検出"""
        system = AudioNotificationSystem()
        assert system.platform in ["darwin", "linux", "windows"]

    def test_sound_config_exists(self):
        """サウンド設定存在確認"""
        system = AudioNotificationSystem()
        assert hasattr(system, "sound_config")
        assert NotificationType.SUCCESS in system.sound_config
        assert NotificationType.ERROR in system.sound_config

    def test_sound_config_has_frequency(self):
        """サウンド設定の周波数"""
        system = AudioNotificationSystem()
        config = system.sound_config[NotificationType.SUCCESS]
        assert "frequency" in config
        assert isinstance(config["frequency"], list)

    def test_sound_config_has_duration(self):
        """サウンド設定の持続時間"""
        system = AudioNotificationSystem()
        config = system.sound_config[NotificationType.SUCCESS]
        assert "duration" in config

    def test_sound_config_has_description(self):
        """サウンド設定の説明"""
        system = AudioNotificationSystem()
        config = system.sound_config[NotificationType.SUCCESS]
        assert "description" in config

    def test_all_notification_types_have_config(self):
        """全通知タイプに設定があることを確認"""
        system = AudioNotificationSystem()
        for ntype in [
            NotificationType.SUCCESS,
            NotificationType.ERROR,
            NotificationType.WARNING,
            NotificationType.INFO,
        ]:
            assert ntype in system.sound_config

    def test_logger_exists(self):
        """ロガー存在確認"""
        system = AudioNotificationSystem()
        assert hasattr(system, "logger")
