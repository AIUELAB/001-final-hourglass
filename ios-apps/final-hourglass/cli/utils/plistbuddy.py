"""PlistBuddy and plutil subprocess wrappers."""
from __future__ import annotations

import subprocess
from pathlib import Path

PLISTBUDDY = "/usr/libexec/PlistBuddy"


def plist_read(path: Path, key: str) -> str:
    """Read a value from a plist file using PlistBuddy.

    Args:
        path: Path to the plist file.
        key: Key to read (e.g., ":CFBundleVersion" or ":ApplicationProperties:CFBundleIdentifier").

    Returns:
        The value as a string.

    Raises:
        subprocess.CalledProcessError: If the key doesn't exist or PlistBuddy fails.
    """
    result = subprocess.run(
        [PLISTBUDDY, "-c", f"Print {key}", str(path)],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def plist_set(path: Path, key: str, value: str) -> None:
    """Set a value in a plist file."""
    subprocess.run(
        [PLISTBUDDY, "-c", f"Set {key} \"{value}\"", str(path)],
        capture_output=True,
        text=True,
        check=True,
    )


def plist_add(path: Path, key: str, plist_type: str, value: str = "") -> None:
    """Add a new key-value pair to a plist file.

    Args:
        path: Path to the plist file.
        key: Key path (e.g., ":ApplicationProperties:CFBundleIdentifier").
        plist_type: Plist type (string, integer, bool, dict, array).
        value: Value to set (empty string for dict/array types).
    """
    cmd = f"Add {key} {plist_type}"
    if value:
        cmd += f" \"{value}\""
    subprocess.run(
        [PLISTBUDDY, "-c", cmd, str(path)],
        capture_output=True,
        text=True,
        check=True,
    )


def plist_clear(path: Path) -> None:
    """Clear all contents of a plist file."""
    subprocess.run(
        [PLISTBUDDY, "-c", "Clear dict", str(path)],
        capture_output=True,
        text=True,
        check=True,
    )


def validate_plist(path: Path) -> tuple[bool, str]:
    """Validate a plist file using plutil.

    Returns:
        Tuple of (is_valid, error_message). error_message is empty on success.
    """
    result = subprocess.run(
        ["plutil", "-lint", str(path)],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return True, ""
    error_detail = result.stdout.strip() or result.stderr.strip() or "plutil returned non-zero"
    return False, error_detail
