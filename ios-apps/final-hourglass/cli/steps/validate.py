"""Step 1: Validate - Check version format, config consistency, and signing."""
from __future__ import annotations

import re
import subprocess
import sys

from ..config import ReleaseConfig, EXPECTED_BUNDLE_ID, EXPECTED_TEAM_ID


VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


def run_validate(config: ReleaseConfig, *, release_version: str | None = None) -> dict[str, object]:
    """Run validation checks. This step has no side effects."""
    errors: list[str] = []
    warnings: list[str] = []

    # 1. Version format check
    if release_version:
        if not VERSION_PATTERN.match(release_version):
            errors.append(
                f"Invalid version format: '{release_version}' (expected X.Y.Z)"
            )
    else:
        warnings.append("No version specified (--version). Skipping version format check.")

    # 2. Workspace existence
    if not config.workspace_path.exists():
        errors.append(f"Workspace not found: {config.workspace_path}")

    # 3. Xcodeproj existence
    if not config.xcodeproj_path.exists():
        errors.append(f"Xcodeproj not found: {config.xcodeproj_path}")

    # 4. Fastlane existence
    fastfile = config.fastlane_dir / "Fastfile"
    if not fastfile.exists():
        errors.append(f"Fastfile not found: {fastfile}")

    # 5. ExportOptions.plist existence
    if not config.export_options_path.exists():
        warnings.append(f"ExportOptions.plist not found: {config.export_options_path}")

    # 6. Bundle ID consistency check (Appfile)
    appfile = config.fastlane_dir / "Appfile"
    if appfile.exists():
        try:
            appfile_content = appfile.read_text(encoding="utf-8")
        except OSError as e:
            errors.append(f"Cannot read Appfile: {e}")
            appfile_content = ""
        if appfile_content and EXPECTED_BUNDLE_ID not in appfile_content:
            errors.append(
                f"Appfile Bundle ID mismatch: expected '{EXPECTED_BUNDLE_ID}'"
            )
        if appfile_content and EXPECTED_TEAM_ID not in appfile_content:
            errors.append(
                f"Appfile Team ID mismatch: expected '{EXPECTED_TEAM_ID}'"
            )

    # 7. ExportOptions.plist consistency check
    if config.export_options_path.exists():
        try:
            plist_content = config.export_options_path.read_text(encoding="utf-8")
        except OSError as e:
            errors.append(f"Cannot read ExportOptions.plist: {e}")
            plist_content = ""
        if plist_content and EXPECTED_BUNDLE_ID not in plist_content:
            errors.append(
                f"ExportOptions.plist Bundle ID mismatch: expected '{EXPECTED_BUNDLE_ID}'"
            )
        if plist_content and EXPECTED_TEAM_ID not in plist_content:
            errors.append(
                f"ExportOptions.plist Team ID mismatch: expected '{EXPECTED_TEAM_ID}'"
            )

    # 8. Config values consistency
    if config.bundle_id and config.bundle_id != EXPECTED_BUNDLE_ID:
        errors.append(
            f"Config Bundle ID mismatch: '{config.bundle_id}' (expected '{EXPECTED_BUNDLE_ID}')"
        )
    if config.team_id and config.team_id != EXPECTED_TEAM_ID:
        errors.append(
            f"Config Team ID mismatch: '{config.team_id}' (expected '{EXPECTED_TEAM_ID}')"
        )

    # 9. Signing identity check (macOS only)
    signing_info: str = ""
    if sys.platform == "darwin":
        try:
            result = subprocess.run(
                ["security", "find-identity", "-v", "-p", "codesigning"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            signing_info = result.stdout.strip()
            if "0 valid identities found" in result.stdout:
                warnings.append("No valid code signing identities found")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            warnings.append("Could not check signing identities")

    return {
        "success": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "signing_info": signing_info,
        "error": "; ".join(errors) if errors else "",
    }
