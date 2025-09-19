"""
Notification Integration Module

Provides easy integration of audio notifications into existing data quality scripts
and automation tasks. Includes decorators and context managers for seamless usage.
"""

import functools
import logging
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Dict, Generator, Optional, TypeVar, Union

from dotenv import load_dotenv

from .notification_system import (
    AudioNotificationSystem,
    NotificationType,
    get_notification_system,
)

# Type variable for decorated functions
F = TypeVar('F', bound=Callable[..., Any])

# Load notification configuration
load_dotenv('.env.notifications')


class NotificationConfig:
    """Configuration manager for notification integration."""

    def __init__(self) -> None:
        """Initialize configuration from environment variables."""
        self.enabled = self._get_bool_env('NOTIFICATIONS_ENABLED', True)
        self.volume = self._get_float_env('NOTIFICATIONS_VOLUME', 0.7)
        self.max_duration = self._get_float_env('NOTIFICATIONS_MAX_DURATION', 2.0)
        self.sounds_dir = self._get_str_env('NOTIFICATIONS_SOUNDS_DIR', 'sounds')

        # Notification type preferences
        self.notify_task_start = self._get_bool_env('NOTIFY_TASK_START', True)
        self.notify_task_complete = self._get_bool_env('NOTIFY_TASK_COMPLETE', True)
        self.notify_progress = self._get_bool_env('NOTIFY_PROGRESS', False)
        self.notify_success = self._get_bool_env('NOTIFY_SUCCESS', True)
        self.notify_error = self._get_bool_env('NOTIFY_ERROR', True)
        self.notify_warning = self._get_bool_env('NOTIFY_WARNING', True)
        self.notify_info = self._get_bool_env('NOTIFY_INFO', False)
        self.notify_waiting = self._get_bool_env('NOTIFY_WAITING', True)

        # Integration settings
        self.integrate_data_scripts = self._get_bool_env('INTEGRATE_WITH_DATA_SCRIPTS', True)
        self.integrate_automation = self._get_bool_env('INTEGRATE_WITH_AUTOMATION', True)
        self.integrate_tests = self._get_bool_env('INTEGRATE_WITH_TESTS', True)
        self.integrate_builds = self._get_bool_env('INTEGRATE_WITH_BUILDS', True)

        # Advanced settings
        self.repeat_error = self._get_int_env('REPEAT_ERROR_NOTIFICATIONS', 2)
        self.repeat_success = self._get_int_env('REPEAT_SUCCESS_NOTIFICATIONS', 1)
        self.repeat_warning = self._get_int_env('REPEAT_WARNING_NOTIFICATIONS', 1)
        self.repeat_delay = self._get_float_env('REPEAT_DELAY', 0.5)

        # Debug settings
        self.debug = self._get_bool_env('NOTIFICATIONS_DEBUG', False)
        self.log_file = self._get_str_env('NOTIFICATIONS_LOG_FILE', '')
        self.verbose = self._get_bool_env('NOTIFICATIONS_VERBOSE', False)

    def _get_bool_env(self, key: str, default: bool) -> bool:
        """Get boolean environment variable."""
        value = os.getenv(key, str(default)).lower()
        return value in ('true', '1', 'yes', 'on')

    def _get_float_env(self, key: str, default: float) -> float:
        """Get float environment variable."""
        try:
            return float(os.getenv(key, str(default)))
        except ValueError:
            return default

    def _get_int_env(self, key: str, default: int) -> int:
        """Get integer environment variable."""
        try:
            return int(os.getenv(key, str(default)))
        except ValueError:
            return default

    def _get_str_env(self, key: str, default: str) -> str:
        """Get string environment variable."""
        return os.getenv(key, default)


# Global configuration instance
config = NotificationConfig()

# Global notification system
notification_system: Optional[AudioNotificationSystem] = None


def get_configured_notification_system() -> AudioNotificationSystem:
    """Get a notification system configured with current settings."""
    global notification_system
    if notification_system is None:
        sounds_dir = Path(config.sounds_dir) if config.sounds_dir else None
        notification_system = AudioNotificationSystem(
            enabled=config.enabled,
            custom_sounds_dir=sounds_dir,
            volume=config.volume,
            max_duration=config.max_duration,
        )
    return notification_system


def should_notify(notification_type: NotificationType) -> bool:
    """Check if a notification type should be played based on configuration."""
    if not config.enabled:
        return False

    type_mapping = {
        NotificationType.TASK_START: config.notify_task_start,
        NotificationType.TASK_COMPLETE: config.notify_task_complete,
        NotificationType.PROGRESS: config.notify_progress,
        NotificationType.SUCCESS: config.notify_success,
        NotificationType.ERROR: config.notify_error,
        NotificationType.WARNING: config.notify_warning,
        NotificationType.INFO: config.notify_info,
        NotificationType.WAITING: config.notify_waiting,
    }

    return type_mapping.get(notification_type, True)


def play_notification(
    notification_type: NotificationType,
    message: Optional[str] = None,
    repeat: Optional[int] = None,
) -> bool:
    """Play a notification with configuration-aware settings."""
    if not should_notify(notification_type):
        return True

    # Determine repeat count based on type and configuration
    if repeat is None:
        if notification_type == NotificationType.ERROR:
            repeat = config.repeat_error
        elif notification_type == NotificationType.SUCCESS:
            repeat = config.repeat_success
        elif notification_type == NotificationType.WARNING:
            repeat = config.repeat_warning
        else:
            repeat = 1

    system = get_configured_notification_system()
    return system.play_notification(notification_type, message, repeat)


def notify_with_sound(
    notification_type: NotificationType,
    message: Optional[str] = None,
) -> Callable[[F], F]:
    """
    Decorator to add audio notification to function calls.

    Args:
        notification_type: Type of notification to play
        message: Optional custom message

    Returns:
        Decorated function
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            func_name = func.__name__
            custom_msg = message or f"Executing {func_name}"

            try:
                if config.verbose:
                    print(f"🔊 {custom_msg}")

                play_notification(notification_type, custom_msg)
                result = func(*args, **kwargs)

                success_msg = f"Completed {func_name}"
                play_notification(NotificationType.SUCCESS, success_msg)

                return result
            except Exception as e:
                error_msg = f"Error in {func_name}: {str(e)[:50]}..."
                play_notification(NotificationType.ERROR, error_msg)
                raise

        return wrapper
    return decorator


def notify_task_progress(
    total_steps: int,
) -> Callable[[F], F]:
    """
    Decorator to add progress notifications to functions with step counts.

    Args:
        total_steps: Total number of steps in the task

    Returns:
        Decorated function
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            func_name = func.__name__

            # Start notification
            play_notification(
                NotificationType.TASK_START,
                f"Starting {func_name} ({total_steps} steps)"
            )

            try:
                # Execute function with progress tracking
                result = func(*args, **kwargs)

                # Completion notification
                play_notification(
                    NotificationType.TASK_COMPLETE,
                    f"Completed {func_name}"
                )

                return result
            except Exception as e:
                error_msg = f"Failed {func_name}: {str(e)[:50]}..."
                play_notification(NotificationType.ERROR, error_msg)
                raise

        return wrapper
    return decorator


@contextmanager
def notification_context(
    start_type: NotificationType = NotificationType.TASK_START,
    success_type: NotificationType = NotificationType.SUCCESS,
    error_type: NotificationType = NotificationType.ERROR,
    task_name: str = "operation",
) -> Generator[Callable[[str], None], None, None]:
    """
    Context manager for notifications around a block of code.

    Args:
        start_type: Notification type for start
        success_type: Notification type for success
        error_type: Notification type for error
        task_name: Name of the task for messages

    Yields:
        Function to send progress notifications
    """
    def progress(message: str) -> None:
        """Send a progress notification."""
        play_notification(NotificationType.PROGRESS, f"{task_name}: {message}")

    # Start notification
    play_notification(start_type, f"Starting {task_name}")

    try:
        yield progress
        # Success notification
        play_notification(success_type, f"Completed {task_name}")
    except Exception as e:
        # Error notification
        error_msg = f"Failed {task_name}: {str(e)[:50]}..."
        play_notification(error_type, error_msg)
        raise


class NotificationLogger(logging.Handler):
    """Custom logging handler that plays audio notifications for log messages."""

    def __init__(self, level: int = logging.WARNING) -> None:
        """Initialize the notification logger."""
        super().__init__(level)
        self.system = get_configured_notification_system()

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record as an audio notification."""
        if record.levelno >= logging.ERROR:
            notification_type = NotificationType.ERROR
        elif record.levelno >= logging.WARNING:
            notification_type = NotificationType.WARNING
        elif record.levelno >= logging.INFO:
            notification_type = NotificationType.INFO
        else:
            return  # Skip DEBUG and below

        message = f"{record.levelname}: {record.getMessage()[:50]}..."
        play_notification(notification_type, message)


def setup_notification_logging(level: int = logging.WARNING) -> None:
    """Setup logging integration with notifications."""
    handler = NotificationLogger(level)
    logging.getLogger().addHandler(handler)


# Integration helper functions for common data scripts
def notify_data_quality_check(func: F) -> F:
    """Decorator specifically for data quality check functions."""
    return notify_with_sound(
        NotificationType.TASK_START,
        "Running data quality check"
    )(func)


def notify_data_processing(func: F) -> F:
    """Decorator specifically for data processing functions."""
    return notify_with_sound(
        NotificationType.TASK_START,
        "Processing data"
    )(func)


def notify_automation_task(func: F) -> F:
    """Decorator specifically for automation tasks."""
    return notify_with_sound(
        NotificationType.TASK_START,
        "Running automation task"
    )(func)


# Quick notification functions with configuration awareness
def quick_notify_success(message: Optional[str] = None) -> None:
    """Quick success notification."""
    play_notification(NotificationType.SUCCESS, message)


def quick_notify_error(message: Optional[str] = None) -> None:
    """Quick error notification."""
    play_notification(NotificationType.ERROR, message)


def quick_notify_warning(message: Optional[str] = None) -> None:
    """Quick warning notification."""
    play_notification(NotificationType.WARNING, message)


def quick_notify_info(message: Optional[str] = None) -> None:
    """Quick info notification."""
    play_notification(NotificationType.INFO, message)


def quick_notify_progress(message: Optional[str] = None) -> None:
    """Quick progress notification."""
    play_notification(NotificationType.PROGRESS, message)


# Status and configuration functions
def get_notification_status() -> Dict[str, Any]:
    """Get current notification system status."""
    system = get_configured_notification_system()
    status = system.get_status()
    status.update({
        "config_enabled": config.enabled,
        "config_volume": config.volume,
        "integration_data_scripts": config.integrate_data_scripts,
        "integration_automation": config.integrate_automation,
    })
    return status


def print_notification_status() -> None:
    """Print notification system status."""
    status = get_notification_status()
    print("🎵 Audio Notification System Status")
    print("=" * 40)
    for key, value in status.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    # Test the integration module
    print_notification_status()

    # Test decorators
    @notify_with_sound(NotificationType.INFO, "Testing decorator")
    def test_function() -> str:
        """Test function for decorator."""
        return "Hello, World!"

    # Test context manager
    with notification_context(task_name="integration test") as progress:
        progress("Step 1: Setting up")
        progress("Step 2: Processing")
        progress("Step 3: Cleaning up")

    print("Integration module test completed!")
