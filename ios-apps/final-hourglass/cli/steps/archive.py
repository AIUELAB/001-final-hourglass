"""Step 3: Archive - xcodebuild archive wrapper."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from ..config import ReleaseConfig
from ..utils.xcodebuild import run_xcodebuild


def _write_signing_xcconfig(
    profile_name: str,
    team_id: str,
) -> Path:
    """Write a temporary xcconfig for app-target signing.

    Using xcconfig avoids the problem where command-line build settings
    (CODE_SIGN_STYLE, PROVISIONING_PROFILE_SPECIFIER) propagate to ALL
    targets including SPM dependencies, which don't support provisioning
    profiles.
    """
    content = (
        f"CODE_SIGN_STYLE = Manual\n"
        f"CODE_SIGN_IDENTITY = Apple Distribution\n"
        f"DEVELOPMENT_TEAM = {team_id}\n"
        f"PROVISIONING_PROFILE_SPECIFIER = {profile_name}\n"
    )
    fd, path = tempfile.mkstemp(suffix=".xcconfig", prefix="ci_signing_")
    os.write(fd, content.encode())
    os.close(fd)
    return Path(path)


def run_archive(
    config: ReleaseConfig,
    *,
    release_version: str | None = None,
    build_number: str | None = None,
    dry_run: bool = True,
) -> dict[str, object]:
    """Run xcodebuild archive.

    In dry-run mode, builds with CODE_SIGNING_ALLOWED=NO to verify
    the project compiles without requiring signing certificates.
    """
    archive_path = config.build_dir / "FinalHourglass.xcarchive"
    xcconfig_path: Path | None = None

    args = [
        "archive",
        "-workspace", str(config.workspace_path),
        "-scheme", "FinalHourglass",
        "-configuration", "Release",
        "-destination", "generic/platform=iOS",
        "-archivePath", str(archive_path),
    ]

    if dry_run:
        args.extend([
            "CODE_SIGNING_ALLOWED=NO",
            "CODE_SIGNING_REQUIRED=NO",
            "CODE_SIGN_IDENTITY=",
        ])

    # In execute mode, pass version via CLI args and signing via xcconfig
    if not dry_run:
        if release_version:
            args.append(f"MARKETING_VERSION={release_version}")
        if build_number:
            args.append(f"CURRENT_PROJECT_VERSION={build_number}")

        # Code signing via xcconfig (avoids SPM target conflicts)
        profile_name = os.environ.get("PROVISIONING_PROFILE_NAME", "")
        if not profile_name:
            return {
                "success": False,
                "archive_path": "",
                "duration": 0.0,
                "error": "PROVISIONING_PROFILE_NAME environment variable is not set. "
                         "Cannot archive without a provisioning profile in execute mode.",
                "return_code": -1,
                "dry_run": dry_run,
            }
        team_id = os.environ.get("APPLE_TEAM_ID", "N4UHXSGNLU")
        xcconfig_path = _write_signing_xcconfig(profile_name, team_id)
        args.extend(["-xcconfig", str(xcconfig_path)])

    try:
        result = run_xcodebuild(args, cwd=config.project_root)
    finally:
        if xcconfig_path and xcconfig_path.exists():
            xcconfig_path.unlink()

    return {
        "success": result.success,
        "archive_path": str(archive_path) if result.success else "",
        "duration": result.duration,
        "error": _extract_error(result.stderr, result.stdout) if not result.success else "",
        "return_code": result.return_code,
        "dry_run": dry_run,
    }


def _extract_error(stderr: str, stdout: str) -> str:
    """Extract meaningful error message from xcodebuild output."""
    # Check stderr first
    for line in stderr.splitlines():
        if "error:" in line.lower():
            return line.strip()

    # Check stdout for error lines
    for line in stdout.splitlines():
        if "error:" in line.lower() and not line.strip().startswith("//"):
            return line.strip()

    # Fallback: include tail of output for context
    tail_lines = (stderr.strip() or stdout.strip()).splitlines()
    tail_text = "\n".join(tail_lines[-10:]) if tail_lines else "(no output)"
    return f"xcodebuild failed. Last output:\n{tail_text}"
