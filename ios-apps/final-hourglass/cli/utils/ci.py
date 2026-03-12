"""CI output helpers for GitHub Actions integration."""

from __future__ import annotations

import os
from pathlib import Path


def is_ci() -> bool:
    """Detect if running in GitHub Actions."""
    return os.getenv("GITHUB_ACTIONS") == "true"


def write_output(key: str, value: str) -> None:
    """Write key=value to $GITHUB_OUTPUT.

    No-op if GITHUB_OUTPUT is not set.
    """
    output_file = os.getenv("GITHUB_OUTPUT")
    if not output_file:
        return
    path = Path(output_file)
    with path.open("a", encoding="utf-8") as f:
        f.write(f"{key}={value}\n")


def annotate(level: str, message: str) -> None:
    """Emit GitHub Actions annotation.

    Args:
        level: One of "error", "warning", "notice".
        message: Annotation message.
    """
    if level not in ("error", "warning", "notice"):
        level = "notice"
    print(f"::{level}::{message}")


def write_step_summary(content: str) -> None:
    """Append content to $GITHUB_STEP_SUMMARY.

    No-op if GITHUB_STEP_SUMMARY is not set.
    """
    summary_file = os.getenv("GITHUB_STEP_SUMMARY")
    if not summary_file:
        return
    path = Path(summary_file)
    with path.open("a", encoding="utf-8") as f:
        f.write(content + "\n")
