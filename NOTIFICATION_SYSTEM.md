# 🎵 Audio Notification System

A comprehensive cross-platform audio notification system for Claude Code that provides audio feedback when tasks complete, errors occur, or progress updates happen.

## ✨ Features

- **Cross-platform support**: Works on macOS, Linux, and Windows
- **Multiple sound types**: System sounds, generated beeps, and custom audio files
- **Notification types**: Success, error, warning, info, task start/complete, progress, waiting
- **Easy integration**: Decorators and context managers for seamless usage
- **Fallback mechanisms**: Graceful degradation when audio is unavailable
- **Configuration**: Extensive customization through environment variables
- **No dependencies**: Uses built-in platform audio capabilities

## 🚀 Quick Start

### 1. Setup

```bash
# Install dependencies and test audio
./scripts/setup_notifications.sh

# Copy configuration template
cp .env.notifications.example .env.notifications

# Test the system
python test_notifications.py
```

### 2. Basic Usage

```python
from src.notification_system import notify_success, notify_error

# Simple notifications
notify_success("Data processing completed!")
notify_error("Failed to connect to database")
```

### 3. Advanced Integration

```python
from src.notification_integration import (
    notify_data_quality_check,
    notification_context,
    quick_notify_progress
)

# Use decorators
@notify_data_quality_check
def run_quality_check():
    # Your quality check code
    return results

# Use context managers
with notification_context(task_name="data migration") as progress:
    progress("Step 1: Backing up data")
    # Migration code
    progress("Step 2: Running migration")
    # More migration code
```

## 📁 File Structure

```
src/
├── notification_system.py      # Core notification system
└── notification_integration.py # Integration utilities

examples/
└── notification_examples.py    # Usage examples and demos

scripts/
├── setup_notifications.sh      # Setup script
└── add_notifications_to_existing.py  # Integration tool

test_notifications.py           # Comprehensive test suite
.env.notifications.example      # Configuration template
NOTIFICATION_SYSTEM.md          # This file
```

## 🔧 Configuration

Edit `.env.notifications` to customize behavior:

```bash
# Enable/disable notifications
NOTIFICATIONS_ENABLED=true

# Set volume (0.0 to 1.0)
NOTIFICATIONS_VOLUME=0.7

# Configure notification types
NOTIFY_SUCCESS=true
NOTIFY_ERROR=true
NOTIFY_WARNING=true
NOTIFY_PROGRESS=false

# Integration settings
INTEGRATE_WITH_DATA_SCRIPTS=true
INTEGRATE_WITH_AUTOMATION=true
```

## 🎯 Notification Types

| Type | Description | Use Case |
|------|-------------|----------|
| `SUCCESS` | ✅ Task completed successfully | Data processing finished |
| `ERROR` | ❌ Error occurred | Script failed, exception thrown |
| `WARNING` | ⚠️ Warning condition | Low disk space, validation issues |
| `INFO` | ℹ️ Information message | Status updates, general info |
| `TASK_START` | 🚀 Task beginning | Script startup, process start |
| `TASK_COMPLETE` | 🏁 Task finished | Process completion |
| `PROGRESS` | 📊 Progress update | Step completion, percentage updates |
| `WAITING` | ⏳ Waiting for input | User interaction needed |

## 🖥️ Platform Support

### macOS
- Uses `afplay` for audio files
- Uses `osascript` for system beeps
- Built-in system sounds available

### Linux
- PulseAudio with `pactl`
- ALSA with `speaker-test` and `aplay`
- System beep command
- Various audio players (sox, ffmpeg)

### Windows
- Windows Sound API via `winsound`
- System sound playback
- Direct frequency generation

## 🎨 Integration Examples

### Decorator Usage

```python
# For data quality checks
@notify_data_quality_check
def audit_data():
    # Plays start sound, runs function, plays success/error
    return audit_results

# For data processing
@notify_data_processing  
def transform_data():
    # Process data with notifications
    return transformed_data

# Custom notifications
@notify_with_sound(NotificationType.INFO, "Starting backup")
def backup_database():
    # Function with custom notification
    pass
```

### Context Manager Usage

```python
# Comprehensive task notification
with notification_context(task_name="database migration") as progress:
    progress("Creating backup")
    create_backup()
    
    progress("Running migration")
    run_migration()
    
    progress("Verifying results")
    verify_migration()
# Automatically plays success or error notification
```

### Manual Notifications

```python
from src.notification_integration import (
    quick_notify_success,
    quick_notify_error,
    quick_notify_progress
)

# Processing loop with progress notifications
for i, item in enumerate(items):
    if i % 100 == 0:  # Every 100 items
        quick_notify_progress(f"Processed {i}/{len(items)} items")
    
    process_item(item)

quick_notify_success(f"Processed all {len(items)} items")
```

## 🎵 Custom Sounds

Add custom sound files to the `sounds/` directory:

```
sounds/
├── success.wav      # Custom success sound
├── error.mp3        # Custom error sound
├── warning.aiff     # Custom warning sound
└── progress.wav     # Custom progress sound
```

Supported formats: WAV, MP3, AIFF, M4A

## 🧪 Testing

```bash
# Run comprehensive tests
python test_notifications.py

# Test specific examples
python examples/notification_examples.py

# Interactive testing
python test_notifications.py
# Choose 'i' for interactive demo
```

## 🔨 Integration Tools

### Automatic Integration

```bash
# Add notifications to existing scripts
python scripts/add_notifications_to_existing.py
```

### Universal Wrapper

```bash
# Run any script with notifications
python run_with_notifications.py your_script.py

# Data quality specific wrapper
python notify_data_quality.py quality_check.py
```

### Bash Wrapper

```bash
# Use the notification wrapper for any command
./scripts/notify_wrapper.sh python your_script.py
./scripts/notify_wrapper.sh npm run build
```

## 📊 Monitoring Integration

```python
# Add to your quality monitor
from src.notification_integration import setup_notification_logging

# Setup logging integration (WARNING level and above)
setup_notification_logging(logging.WARNING)

# Now all log warnings and errors will play sounds
logger.warning("Disk space low")  # Plays warning sound
logger.error("Database connection failed")  # Plays error sound
```

## 🔧 Troubleshooting

### Audio Not Working

1. **Run setup script**: `./scripts/setup_notifications.sh`
2. **Check audio system**: Test with system sounds manually
3. **Check configuration**: Ensure `NOTIFICATIONS_ENABLED=true` in `.env.notifications`
4. **Test notification system**: `python test_notifications.py`
5. **Check volume**: Ensure system and notification volume are not muted

### Linux Audio Issues

```bash
# Check PulseAudio
pulseaudio --check -v

# Start PulseAudio if needed
pulseaudio --start

# Test audio playback
paplay /usr/share/sounds/alsa/Front_Left.wav
```

### macOS Audio Issues

```bash
# Test system audio
afplay /System/Library/Sounds/Tink.aiff

# Check sound preferences
# System Preferences > Sound > Sound Effects
```

### Windows Audio Issues

- Ensure Windows audio service is running
- Check sound settings in Control Panel
- Test with system sounds in Control Panel

## 🎯 Best Practices

1. **Use appropriate notification types** - Don't overwhelm with too many sounds
2. **Configure volume appropriately** - Keep it noticeable but not disruptive
3. **Test before deployment** - Ensure audio works in your environment
4. **Use progress notifications sparingly** - Only for long-running tasks
5. **Customize for your workflow** - Adjust settings in `.env.notifications`

## 🤝 Contributing

To extend the notification system:

1. Add new notification types to `NotificationType` enum
2. Add sound configuration in `_get_default_sound_config()`
3. Create custom integration decorators in `notification_integration.py`
4. Add tests in `test_notifications.py`

## 📝 License

This notification system is part of the Claude Code template and follows the same MIT license.

---

🎵 **Happy coding with audio feedback!** 🎵