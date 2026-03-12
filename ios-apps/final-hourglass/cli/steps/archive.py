"""Step 3: Archive - xcodebuild archive wrapper."""
from __future__ import annotations

from ..config import ReleaseConfig
from ..utils.xcodebuild import run_xcodebuild


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

    # In execute mode, pass version to xcodebuild
    if not dry_run:
        if release_version:
            args.append(f"MARKETING_VERSION={release_version}")
        if build_number:
            args.append(f"CURRENT_PROJECT_VERSION={build_number}")

    result = run_xcodebuild(args, cwd=config.project_root)

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
