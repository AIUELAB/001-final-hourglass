#!/bin/bash

# Audio Notification System Setup Script
# Installs dependencies and tests audio functionality

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Detect operating system
detect_os() {
    case "$(uname -s)" in
        Darwin*)
            OS="macos"
            log_info "Detected macOS"
            ;;
        Linux*)
            OS="linux"
            log_info "Detected Linux"
            ;;
        CYGWIN*|MINGW32*|MINGW64*|MSYS*)
            OS="windows"
            log_info "Detected Windows"
            ;;
        *)
            OS="unknown"
            log_warning "Unknown operating system"
            ;;
    esac
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Install audio dependencies based on OS
install_audio_deps() {
    log_info "Installing audio dependencies for $OS..."

    case "$OS" in
        "macos")
            # macOS has built-in audio support
            log_success "macOS has built-in audio support"
            ;;
        "linux")
            install_linux_audio_deps
            ;;
        "windows")
            log_info "Windows audio dependencies are handled by Python winsound module"
            ;;
        *)
            log_warning "Cannot install dependencies for unknown OS"
            ;;
    esac
}

# Install Linux audio dependencies
install_linux_audio_deps() {
    # Detect Linux distribution
    if [ -f /etc/debian_version ]; then
        # Debian/Ubuntu
        log_info "Detected Debian/Ubuntu system"
        if command_exists apt; then
            log_info "Installing audio packages with apt..."
            sudo apt update
            sudo apt install -y \
                pulseaudio \
                pulseaudio-utils \
                alsa-utils \
                sox \
                ffmpeg
        elif command_exists apt-get; then
            log_info "Installing audio packages with apt-get..."
            sudo apt-get update
            sudo apt-get install -y \
                pulseaudio \
                pulseaudio-utils \
                alsa-utils \
                sox \
                ffmpeg
        fi
    elif [ -f /etc/redhat-release ]; then
        # Red Hat/CentOS/Fedora
        log_info "Detected Red Hat/CentOS/Fedora system"
        if command_exists dnf; then
            log_info "Installing audio packages with dnf..."
            sudo dnf install -y \
                pulseaudio \
                pulseaudio-utils \
                alsa-utils \
                sox \
                ffmpeg
        elif command_exists yum; then
            log_info "Installing audio packages with yum..."
            sudo yum install -y \
                pulseaudio \
                pulseaudio-utils \
                alsa-utils \
                sox \
                ffmpeg
        fi
    elif [ -f /etc/arch-release ]; then
        # Arch Linux
        log_info "Detected Arch Linux system"
        if command_exists pacman; then
            log_info "Installing audio packages with pacman..."
            sudo pacman -S --noconfirm \
                pulseaudio \
                pulseaudio-alsa \
                alsa-utils \
                sox \
                ffmpeg
        fi
    else
        log_warning "Unknown Linux distribution. Please install audio packages manually:"
        log_info "Required packages: pulseaudio, alsa-utils, sox, ffmpeg"
    fi

    # Start PulseAudio if not running
    if ! pgrep -x pulseaudio > /dev/null; then
        log_info "Starting PulseAudio..."
        pulseaudio --start || log_warning "Failed to start PulseAudio"
    fi
}

# Test audio functionality
test_audio() {
    log_info "Testing audio functionality..."

    case "$OS" in
        "macos")
            test_macos_audio
            ;;
        "linux")
            test_linux_audio
            ;;
        "windows")
            test_windows_audio
            ;;
        *)
            log_warning "Cannot test audio for unknown OS"
            ;;
    esac
}

# Test macOS audio
test_macos_audio() {
    log_info "Testing macOS audio..."

    # Test afplay with system sound
    if [ -f "/System/Library/Sounds/Tink.aiff" ]; then
        log_info "Testing afplay with system sound..."
        if afplay /System/Library/Sounds/Tink.aiff; then
            log_success "afplay test successful"
        else
            log_warning "afplay test failed"
        fi
    else
        log_warning "System sound file not found"
    fi

    # Test osascript beep
    log_info "Testing osascript beep..."
    if osascript -e "beep"; then
        log_success "osascript beep test successful"
    else
        log_warning "osascript beep test failed"
    fi
}

# Test Linux audio
test_linux_audio() {
    log_info "Testing Linux audio..."

    # Test PulseAudio
    if command_exists pactl; then
        log_info "Testing PulseAudio..."
        if pactl info >/dev/null 2>&1; then
            log_success "PulseAudio is running"

            # Test sine wave generation
            log_info "Testing sine wave generation (3 seconds)..."
            MODULE_ID=$(pactl load-module module-sine frequency=500 2>/dev/null || echo "")
            if [ -n "$MODULE_ID" ]; then
                sleep 1
                pactl unload-module "$MODULE_ID" 2>/dev/null || true
                log_success "Sine wave test successful"
            else
                log_warning "Sine wave test failed"
            fi
        else
            log_warning "PulseAudio is not running properly"
        fi
    else
        log_warning "pactl not found"
    fi

    # Test ALSA
    if command_exists speaker-test; then
        log_info "Testing ALSA speaker-test (1 second)..."
        if timeout 2 speaker-test -t sine -f 1000 -l 1 -s 1 >/dev/null 2>&1; then
            log_success "ALSA speaker-test successful"
        else
            log_warning "ALSA speaker-test failed"
        fi
    else
        log_warning "speaker-test not found"
    fi

    # Test beep command
    if command_exists beep; then
        log_info "Testing beep command..."
        if beep >/dev/null 2>&1; then
            log_success "beep command successful"
        else
            log_warning "beep command failed (may require root privileges)"
        fi
    else
        log_info "beep command not found (optional)"
    fi
}

# Test Windows audio
test_windows_audio() {
    log_info "Testing Windows audio..."
    log_info "Windows audio testing requires Python winsound module"
    log_info "This will be tested by the Python notification system"
}

# Create notification hooks
create_notification_hooks() {
    log_info "Creating notification hooks..."

    # Create sounds directory
    SOUNDS_DIR="sounds"
    mkdir -p "$SOUNDS_DIR"
    log_success "Created sounds directory: $SOUNDS_DIR"

    # Create environment file template
    if [ ! -f ".env.notifications" ]; then
        cat > .env.notifications << EOF
# Audio Notification System Configuration

# Enable/disable notifications (true/false)
NOTIFICATIONS_ENABLED=true

# Audio volume (0.0 to 1.0)
NOTIFICATIONS_VOLUME=0.7

# Maximum notification duration in seconds
NOTIFICATIONS_MAX_DURATION=2.0

# Custom sounds directory (relative to project root)
NOTIFICATIONS_SOUNDS_DIR=sounds

# Notification preferences for different events
NOTIFY_TASK_START=true
NOTIFY_TASK_COMPLETE=true
NOTIFY_SUCCESS=true
NOTIFY_ERROR=true
NOTIFY_WARNING=false
NOTIFY_PROGRESS=false

# Integration settings
INTEGRATE_WITH_DATA_SCRIPTS=true
INTEGRATE_WITH_AUTOMATION=true
EOF
        log_success "Created notification configuration: .env.notifications"
    else
        log_info "Notification configuration already exists: .env.notifications"
    fi

    # Create sample notification wrapper script
    cat > scripts/notify_wrapper.sh << 'EOF'
#!/bin/bash

# Notification Wrapper Script
# Usage: ./scripts/notify_wrapper.sh <command> [args...]
# Plays notifications before and after command execution

source .env.notifications 2>/dev/null || true

NOTIFICATIONS_ENABLED=${NOTIFICATIONS_ENABLED:-true}

if [ "$NOTIFICATIONS_ENABLED" = "true" ]; then
    # Play start notification
    python -c "
from src.notification_system import notify_progress
notify_progress('Starting: $*')
" 2>/dev/null || true
fi

# Execute the command
"$@"
EXIT_CODE=$?

if [ "$NOTIFICATIONS_ENABLED" = "true" ]; then
    if [ $EXIT_CODE -eq 0 ]; then
        # Play success notification
        python -c "
from src.notification_system import notify_success
notify_success('Completed successfully: $*')
" 2>/dev/null || true
    else
        # Play error notification
        python -c "
from src.notification_system import notify_error
notify_error('Failed with exit code $EXIT_CODE: $*')
" 2>/dev/null || true
    fi
fi

exit $EXIT_CODE
EOF
    chmod +x scripts/notify_wrapper.sh
    log_success "Created notification wrapper: scripts/notify_wrapper.sh"
}

# Setup Python dependencies
setup_python_deps() {
    log_info "Setting up Python dependencies..."

    # Check if we're in a virtual environment
    if [ -z "$VIRTUAL_ENV" ] && [ ! -f "venv/bin/activate" ]; then
        log_warning "No virtual environment detected"
        log_info "It's recommended to use a virtual environment"
        read -p "Create virtual environment? [y/N] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            python3 -m venv venv
            source venv/bin/activate
            log_success "Created and activated virtual environment"
        fi
    elif [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
        log_info "Activated existing virtual environment"
    fi

    # Install Python packages if requirements exist
    if [ -f "requirements.txt" ]; then
        log_info "Installing Python requirements..."
        pip install -r requirements.txt
        log_success "Python requirements installed"
    else
        log_warning "requirements.txt not found"
    fi
}

# Run notification system test
test_notification_system() {
    log_info "Testing notification system..."

    if python -c "
import sys
sys.path.append('src')
from notification_system import AudioNotificationSystem, NotificationType
import time

system = AudioNotificationSystem()
print(f'Notification system status: {system.get_status()}')

# Test basic notifications
test_types = [
    NotificationType.INFO,
    NotificationType.SUCCESS,
    NotificationType.WARNING,
    NotificationType.ERROR
]

for notification_type in test_types:
    print(f'Testing {notification_type.value}...')
    success = system.play_notification(notification_type)
    if success:
        print(f'✓ {notification_type.value} notification played successfully')
    else:
        print(f'✗ {notification_type.value} notification failed')
    time.sleep(0.3)

print('Notification system test completed')
"; then
        log_success "Notification system test passed"
    else
        log_error "Notification system test failed"
        exit 1
    fi
}

# Main setup function
main() {
    echo "=========================================="
    echo "  Audio Notification System Setup"
    echo "=========================================="
    echo

    # Detect OS
    detect_os
    echo

    # Setup Python dependencies
    setup_python_deps
    echo

    # Install audio dependencies
    install_audio_deps
    echo

    # Test audio functionality
    test_audio
    echo

    # Create notification hooks
    create_notification_hooks
    echo

    # Test notification system
    test_notification_system
    echo

    log_success "Audio notification system setup completed!"
    echo
    log_info "Usage examples:"
    log_info "  # Use wrapper script for any command:"
    log_info "  ./scripts/notify_wrapper.sh python your_script.py"
    echo
    log_info "  # Use in Python code:"
    log_info "  from src.notification_system import notify_success"
    log_info "  notify_success('Task completed!')"
    echo
    log_info "Configuration file: .env.notifications"
    log_info "Custom sounds directory: sounds/"
    echo
}

# Run main function
main "$@"
