"""Step 2: Version - Update MARKETING_VERSION and CURRENT_PROJECT_VERSION in pbxproj."""
from __future__ import annotations

import re

from rich.console import Console

from ..config import ReleaseConfig

console = Console()

MARKETING_VERSION_RE = re.compile(r"(MARKETING_VERSION\s*=\s*)\d+(?:\.\d+)*(;)")
PROJECT_VERSION_RE = re.compile(r"(CURRENT_PROJECT_VERSION\s*=\s*)\d+(;)")


def run_version(
    config: ReleaseConfig,
    *,
    release_version: str | None = None,
    build_number: str | None = None,
    dry_run: bool = True,
) -> dict[str, object]:
    """Update version numbers in the Xcode project.

    Args:
        config: Release configuration.
        release_version: New marketing version (e.g., "1.0.11"). Required.
        build_number: New build number. If None, auto-increments current value.
        dry_run: If True, show changes without writing.

    Returns:
        Result dict with success, new_version, new_build, etc.
    """
    if not release_version:
        return {"success": False, "error": "No --version specified. Required for version step."}

    pbxproj_path = config.xcodeproj_path / "project.pbxproj"
    if not pbxproj_path.exists():
        return {"success": False, "error": f"project.pbxproj not found: {pbxproj_path}"}

    try:
        content = pbxproj_path.read_text(encoding="utf-8")
    except OSError as e:
        return {"success": False, "error": f"Cannot read pbxproj: {e}"}

    # Read current version
    current_match = MARKETING_VERSION_RE.search(content)
    if not current_match:
        return {"success": False, "error": "MARKETING_VERSION not found in pbxproj"}

    current_version = current_match.group(0).split("=")[1].strip().rstrip(";").strip()

    # Read current build number
    build_match = PROJECT_VERSION_RE.search(content)
    current_build = "1"
    if build_match:
        current_build = build_match.group(0).split("=")[1].strip().rstrip(";").strip()

    # Determine new build number
    if build_number is None:
        try:
            new_build = str(int(current_build) + 1)
        except ValueError:
            new_build = "1"
    else:
        new_build = build_number

    console.print(f"  Version: {current_version} -> {release_version}")
    console.print(f"  Build:   {current_build} -> {new_build}")

    if dry_run:
        console.print("  [yellow]DRY-RUN: No changes written[/yellow]")
        return {
            "success": True,
            "current_version": current_version,
            "new_version": release_version,
            "current_build": current_build,
            "new_build": new_build,
            "dry_run": True,
        }

    # Verify replacement targets exist before modifying
    version_count = len(MARKETING_VERSION_RE.findall(content))
    build_count = len(PROJECT_VERSION_RE.findall(content))

    if version_count == 0:
        return {"success": False, "error": "MARKETING_VERSION regex matched 0 entries in pbxproj"}
    if build_count == 0:
        return {"success": False, "error": "CURRENT_PROJECT_VERSION regex matched 0 entries in pbxproj"}

    # Apply changes
    new_content = MARKETING_VERSION_RE.sub(
        rf"\g<1>{release_version}\2", content
    )
    new_content = PROJECT_VERSION_RE.sub(
        rf"\g<1>{new_build}\2", new_content
    )

    try:
        pbxproj_path.write_text(new_content, encoding="utf-8")
    except OSError as e:
        return {"success": False, "error": f"Failed to write pbxproj: {e}"}

    console.print(f"  Updated {version_count} MARKETING_VERSION entries")
    console.print(f"  Updated {build_count} CURRENT_PROJECT_VERSION entries")

    return {
        "success": True,
        "current_version": current_version,
        "new_version": release_version,
        "current_build": current_build,
        "new_build": new_build,
        "version_replacements": version_count,
        "build_replacements": build_count,
        "dry_run": False,
    }
