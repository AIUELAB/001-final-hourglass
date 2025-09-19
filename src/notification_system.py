"""
Audio Notification System for Claude Code

Provides cross-platform audio notifications for task completion, errors, and progress updates.
Supports system sounds, generated tones, and custom sound files.
"""

import logging
import platform
import subprocess
import sys
import threading
import time
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    import winsound  # Windows audio support
except ImportError:
    winsound = None


class NotificationType(Enum):
    """Types of notifications supported by the system."""
    SUCCESS = "success"
    ERROR = "error" 
    WARNING = "warning"
    INFO = "info"
    TASK_START = "task_start"
    TASK_COMPLETE = "task_complete"
    PROGRESS = "progress"
    WAITING = "waiting"


class AudioNotificationSystem:
    """
    Cross-platform audio notification system.
    
    Provides audio feedback for various events and task states.
    Falls back gracefully when audio is not available.
    """
    
    def __init__(
        self,
        enabled: bool = True,
        custom_sounds_dir: Optional[Union[str, Path]] = None,
        volume: float = 0.7,
        max_duration: float = 2.0,
    ) -> None:
        """
        Initialize the audio notification system.
        
        Args:
            enabled: Whether audio notifications are enabled
            custom_sounds_dir: Directory containing custom sound files
            volume: Audio volume (0.0 to 1.0) 
            max_duration: Maximum duration for generated sounds
        """
        self.enabled = enabled
        self.volume = max(0.0, min(1.0, volume))
        self.max_duration = max_duration
        self.platform = platform.system().lower()
        self.logger = logging.getLogger(__name__)
        
        # Setup custom sounds directory
        self.custom_sounds_dir = None
        if custom_sounds_dir:
            self.custom_sounds_dir = Path(custom_sounds_dir)
            self.custom_sounds_dir.mkdir(exist_ok=True)
        
        # Sound configuration for each notification type
        self.sound_config = self._get_default_sound_config()
        
        # Test audio system on initialization
        self._test_audio_system()
    
    def _get_default_sound_config(self) -> Dict[NotificationType, Dict[str, Any]]:
        """Get default sound configuration for each notification type."""
        return {
            NotificationType.SUCCESS: {
                "frequency": [800, 1000, 1200],
                "duration": 0.15,
                "system_sound": "Glass",  # macOS
                "description": "Task completed successfully"
            },
            NotificationType.ERROR: {
                "frequency": [300, 200, 150],
                "duration": 0.3,
                "system_sound": "Sosumi",  # macOS
                "description": "Error occurred"
            },
            NotificationType.WARNING: {
                "frequency": [600, 400],
                "duration": 0.2,
                "system_sound": "Ping",  # macOS
                "description": "Warning condition"
            },
            NotificationType.INFO: {
                "frequency": [500],
                "duration": 0.1,
                "system_sound": "Pop",  # macOS
                "description": "Information notification"
            },
            NotificationType.TASK_START: {
                "frequency": [400, 600],
                "duration": 0.1,
                "system_sound": "Tink",  # macOS
                "description": "Task started"
            },
            NotificationType.TASK_COMPLETE: {
                "frequency": [600, 800, 1000],
                "duration": 0.2,
                "system_sound": "Glass",  # macOS
                "description": "Task completed"
            },
            NotificationType.PROGRESS: {
                "frequency": [700],
                "duration": 0.05,
                "system_sound": "Tink",  # macOS
                "description": "Progress update"
            },
            NotificationType.WAITING: {
                "frequency": [400, 500, 400],
                "duration": 0.15,
                "system_sound": "Submarine",  # macOS
                "description": "Waiting for input"
            },
        }
    
    def _test_audio_system(self) -> bool:
        """Test if audio system is working properly."""
        if not self.enabled:
            return True
        
        try:
            # Try to play a very quiet test beep
            if self.platform == "darwin":  # macOS
                subprocess.run(
                    ["afplay", "/System/Library/Sounds/Tink.aiff"],
                    check=False,
                    capture_output=True,
                    timeout=1.0
                )
            elif self.platform == "linux":
                # Test if speaker-test or pactl is available
                result = subprocess.run(
                    ["which", "pactl"],
                    capture_output=True,
                    text=True,
                    check=False
                )
                if result.returncode == 0:
                    return True
            elif self.platform == "windows" and winsound:
                winsound.Beep(1000, 50)
            
            self.logger.debug("Audio system test completed successfully")
            return True
        except Exception as e:
            self.logger.warning(f"Audio system test failed: {e}")
            return False
    
    def play_notification(
        self,
        notification_type: NotificationType,
        custom_message: Optional[str] = None,
        repeat: int = 1,
    ) -> bool:
        """
        Play a notification sound.
        
        Args:
            notification_type: Type of notification to play
            custom_message: Optional custom message for logging
            repeat: Number of times to repeat the sound
            
        Returns:
            True if sound was played successfully, False otherwise
        """
        if not self.enabled:
            return True
        
        config = self.sound_config.get(notification_type, {})
        message = custom_message or config.get("description", "Unknown notification")
        
        self.logger.info(f"Playing {notification_type.value} notification: {message}")
        
        success = False
        for _ in range(repeat):
            # Try custom sound file first
            if self._play_custom_sound(notification_type):
                success = True
            # Fall back to system sound
            elif self._play_system_sound(notification_type):
                success = True
            # Fall back to generated beep
            elif self._play_generated_beep(notification_type):
                success = True
            else:
                self.logger.warning(f"Failed to play {notification_type.value} notification")
                break
        
        return success
    
    def _play_custom_sound(self, notification_type: NotificationType) -> bool:
        """Try to play a custom sound file for the notification type."""
        if not self.custom_sounds_dir or not self.custom_sounds_dir.exists():
            return False
        
        # Look for custom sound files
        for ext in ['.wav', '.mp3', '.aiff', '.m4a']:
            sound_file = self.custom_sounds_dir / f"{notification_type.value}{ext}"
            if sound_file.exists():
                return self._play_sound_file(sound_file)
        
        return False
    
    def _play_sound_file(self, sound_file: Path) -> bool:
        """Play a sound file using platform-appropriate method."""
        try:
            if self.platform == "darwin":  # macOS
                subprocess.run(
                    ["afplay", str(sound_file)],
                    check=True,
                    capture_output=True,
                    timeout=self.max_duration + 1.0
                )
                return True
            elif self.platform == "linux":
                # Try multiple audio players
                players = ["paplay", "aplay", "sox", "ffplay"]
                for player in players:
                    try:
                        subprocess.run(
                            ["which", player],
                            check=True,
                            capture_output=True
                        )
                        subprocess.run(
                            [player, str(sound_file)],
                            check=True,
                            capture_output=True,
                            timeout=self.max_duration + 1.0
                        )
                        return True
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        continue
            elif self.platform == "windows":
                import os
                os.system(f'start /wait "" "{sound_file}"')
                return True
        except Exception as e:
            self.logger.debug(f"Failed to play sound file {sound_file}: {e}")
        
        return False
    
    def _play_system_sound(self, notification_type: NotificationType) -> bool:
        """Try to play a system sound."""
        config = self.sound_config.get(notification_type, {})
        system_sound = config.get("system_sound")
        
        if not system_sound:
            return False
        
        try:
            if self.platform == "darwin":  # macOS
                subprocess.run(
                    ["afplay", f"/System/Library/Sounds/{system_sound}.aiff"],
                    check=True,
                    capture_output=True,
                    timeout=self.max_duration + 1.0
                )
                return True
            elif self.platform == "linux":
                # Try to use system notification sounds
                sound_paths = [
                    f"/usr/share/sounds/alsa/{system_sound.lower()}.wav",
                    f"/usr/share/sounds/{system_sound.lower()}.ogg",
                    "/usr/share/sounds/alsa/Side_Left.wav",  # Fallback
                ]
                for sound_path in sound_paths:
                    if Path(sound_path).exists():
                        return self._play_sound_file(Path(sound_path))
        except Exception as e:
            self.logger.debug(f"Failed to play system sound {system_sound}: {e}")
        
        return False
    
    def _play_generated_beep(self, notification_type: NotificationType) -> bool:
        """Generate and play a beep sound."""
        config = self.sound_config.get(notification_type, {})
        frequencies = config.get("frequency", [500])
        duration = config.get("duration", 0.2)
        
        try:
            if self.platform == "darwin":  # macOS
                return self._play_macos_beep(frequencies, duration)
            elif self.platform == "linux":
                return self._play_linux_beep(frequencies, duration)
            elif self.platform == "windows":
                return self._play_windows_beep(frequencies, duration)
        except Exception as e:
            self.logger.debug(f"Failed to play generated beep: {e}")
        
        return False
    
    def _play_macos_beep(self, frequencies: List[int], duration: float) -> bool:
        """Play beep on macOS using osascript."""
        try:
            for _ in frequencies:
                # Use osascript to play system beep
                subprocess.run(
                    ["osascript", "-e", "beep"],
                    check=True,
                    capture_output=True,
                    timeout=1.0
                )
                if len(frequencies) > 1:
                    time.sleep(duration / 2)
            return True
        except Exception:
            return False
    
    def _play_linux_beep(self, frequencies: List[int], duration: float) -> bool:
        """Play beep on Linux using various methods."""
        # Try speaker-test
        try:
            for freq in frequencies:
                subprocess.run(
                    ["speaker-test", "-t", "sine", "-f", str(freq), "-l", "1"],
                    check=True,
                    capture_output=True,
                    timeout=duration + 0.5
                )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        # Try pactl with module-sine
        try:
            for freq in frequencies:
                # Load sine module
                result = subprocess.run(
                    ["pactl", "load-module", "module-sine", f"frequency={freq}"],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=1.0
                )
                module_id = result.stdout.strip()
                time.sleep(duration)
                # Unload sine module
                subprocess.run(
                    ["pactl", "unload-module", module_id],
                    check=True,
                    capture_output=True,
                    timeout=1.0
                )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        # Try simple beep command
        try:
            subprocess.run(["beep"], check=True, capture_output=True, timeout=1.0)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        return False
    
    def _play_windows_beep(self, frequencies: List[int], duration: float) -> bool:
        """Play beep on Windows using winsound."""
        if not winsound:
            return False
        
        try:
            for freq in frequencies:
                winsound.Beep(freq, int(duration * 1000))
            return True
        except Exception:
            return False
    
    def enable(self) -> None:
        """Enable audio notifications."""
        self.enabled = True
        self.logger.info("Audio notifications enabled")
    
    def disable(self) -> None:
        """Disable audio notifications."""
        self.enabled = False
        self.logger.info("Audio notifications disabled")
    
    def set_volume(self, volume: float) -> None:
        """Set audio volume (0.0 to 1.0)."""
        self.volume = max(0.0, min(1.0, volume))
        self.logger.info(f"Audio volume set to {self.volume:.1%}")
    
    def play_sequence(
        self,
        sequence: List[NotificationType],
        delay: float = 0.2,
        background: bool = False,
    ) -> None:
        """
        Play a sequence of notifications.
        
        Args:
            sequence: List of notification types to play in order
            delay: Delay between notifications in seconds
            background: Whether to play in background thread
        """
        def _play_sequence():
            for i, notification_type in enumerate(sequence):
                self.play_notification(notification_type)
                if i < len(sequence) - 1:
                    time.sleep(delay)
        
        if background:
            thread = threading.Thread(target=_play_sequence, daemon=True)
            thread.start()
        else:
            _play_sequence()
    
    def get_status(self) -> Dict[str, Any]:
        """Get current system status."""
        return {
            "enabled": self.enabled,
            "platform": self.platform,
            "volume": self.volume,
            "max_duration": self.max_duration,
            "custom_sounds_dir": str(self.custom_sounds_dir) if self.custom_sounds_dir else None,
            "available_notifications": [t.value for t in NotificationType],
        }


# Convenience functions for common use cases
def notify_success(message: str = "Operation completed successfully") -> None:
    """Play success notification."""
    system = AudioNotificationSystem()
    system.play_notification(NotificationType.SUCCESS, message)


def notify_error(message: str = "An error occurred") -> None:
    """Play error notification."""
    system = AudioNotificationSystem()
    system.play_notification(NotificationType.ERROR, message)


def notify_task_complete(message: str = "Task completed") -> None:
    """Play task completion notification."""
    system = AudioNotificationSystem()
    system.play_notification(NotificationType.TASK_COMPLETE, message)


def notify_progress(message: str = "Progress update") -> None:
    """Play progress notification."""
    system = AudioNotificationSystem()
    system.play_notification(NotificationType.PROGRESS, message)


# Global notification system instance
_global_notification_system: Optional[AudioNotificationSystem] = None


def get_notification_system(**kwargs) -> AudioNotificationSystem:
    """Get or create global notification system instance."""
    global _global_notification_system
    if _global_notification_system is None:
        _global_notification_system = AudioNotificationSystem(**kwargs)
    return _global_notification_system


if __name__ == "__main__":
    # Basic test when run directly
    system = AudioNotificationSystem()
    print("Testing notification system...")
    print(f"Status: {system.get_status()}")
    
    for notification_type in NotificationType:
        print(f"Testing {notification_type.value}...")
        system.play_notification(notification_type)
        time.sleep(0.5)
    
    print("Test complete!")