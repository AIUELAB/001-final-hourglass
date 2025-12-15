#!/usr/bin/env python3
"""
シンプルで確実な音声通知システム
Claude Code用の軽量実装
"""

import os
import platform
import subprocess
import sys
from typing import Optional


class SimpleNotification:
    """シンプルな音声通知クラス"""

    def __init__(self):
        self.system = platform.system()
        self.enabled = self._check_audio_capability()

    def _check_audio_capability(self) -> bool:
        """音声機能が利用可能かチェック"""
        if self.system == "Darwin":  # macOS
            # osascriptは常に利用可能
            return True
        elif self.system == "Linux":
            # pactl or beep command check
            return self._command_exists("pactl") or self._command_exists("beep")
        elif self.system == "Windows":
            return True  # winsound is built-in
        return False

    def _command_exists(self, command: str) -> bool:
        """コマンドが存在するかチェック"""
        try:
            subprocess.run(
                ["which", command],
                capture_output=True,
                check=False,
                timeout=1
            )
            return True
        except:
            return False

    def play_sound(self, sound_type: str = "default") -> None:
        """音を再生"""
        if not self.enabled:
            print(f"🔔 [{sound_type}] (音声通知は利用できません)")
            return

        try:
            if self.system == "Darwin":  # macOS
                self._play_macos_sound(sound_type)
            elif self.system == "Linux":
                self._play_linux_sound(sound_type)
            elif self.system == "Windows":
                self._play_windows_sound(sound_type)
        except Exception as e:
            print(f"🔔 [{sound_type}] (音声再生エラー: {e})")

    def _play_macos_sound(self, sound_type: str) -> None:
        """macOSで音を再生"""
        # osascriptでビープ音を鳴らす（最も確実）
        if sound_type == "error":
            count = 2
        elif sound_type == "warning":
            count = 1
        else:
            count = 1

        script = f'beep {count}'
        subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            timeout=2
        )

    def _play_linux_sound(self, sound_type: str) -> None:
        """Linuxで音を再生"""
        # pactl or beep command
        if self._command_exists("pactl"):
            subprocess.run(
                ["pactl", "play-sample", "bell"],
                capture_output=True,
                timeout=1
            )
        elif self._command_exists("beep"):
            if sound_type == "error":
                freq = 400
            elif sound_type == "warning":
                freq = 600
            else:
                freq = 800
            subprocess.run(
                ["beep", "-f", str(freq), "-l", "200"],
                capture_output=True,
                timeout=1
            )
        else:
            # ASCII bell
            print("\a", end="", flush=True)

    def _play_windows_sound(self, sound_type: str) -> None:
        """Windowsで音を再生"""
        import winsound
        if sound_type == "error":
            winsound.MessageBeep(winsound.MB_ICONHAND)
        elif sound_type == "warning":
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        else:
            winsound.MessageBeep(winsound.MB_OK)

# グローバルインスタンス
_notifier = SimpleNotification()

def notify_success(message: str = "") -> None:
    """成功通知"""
    _notifier.play_sound("success")
    if message:
        print(f"✅ {message}")

def notify_error(message: str = "") -> None:
    """エラー通知"""
    _notifier.play_sound("error")
    if message:
        print(f"❌ {message}")

def notify_warning(message: str = "") -> None:
    """警告通知"""
    _notifier.play_sound("warning")
    if message:
        print(f"⚠️ {message}")

def notify_complete(message: str = "タスク完了") -> None:
    """完了通知"""
    _notifier.play_sound("complete")
    print(f"🎵 {message}")

def notify_waiting(message: str = "ユーザー入力待機中...") -> None:
    """待機通知"""
    _notifier.play_sound("waiting")
    print(f"⏳ {message}")

# テスト関数
def test_notifications():
    """通知システムのテスト"""
    print("🎵 音声通知システムテスト")
    print("=" * 40)

    print("\n1. 成功通知テスト...")
    notify_success("処理が成功しました")

    import time
    time.sleep(1)

    print("\n2. エラー通知テスト...")
    notify_error("エラーが発生しました")

    time.sleep(1)

    print("\n3. 完了通知テスト...")
    notify_complete("すべてのタスクが完了しました")

    print("\n" + "=" * 40)
    print("✅ テスト完了！")

if __name__ == "__main__":
    test_notifications()
