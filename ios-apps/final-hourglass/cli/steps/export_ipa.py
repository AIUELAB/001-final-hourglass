"""Step 4: Export - exportArchive to generate IPA with TN3110 fix."""
from __future__ import annotations

from pathlib import Path
import subprocess

from rich.console import Console

from ..config import ReleaseConfig
from ..utils.plistbuddy import plist_read, plist_add, validate_plist
from ..utils.xcodebuild import run_xcodebuild

console = Console()

# Keys required by TN3110 in xcarchive Info.plist -> ApplicationProperties
APPLICATION_PROPERTIES_KEYS = [
    "ApplicationPath",
    "CFBundleIdentifier",
    "CFBundleShortVersionString",
    "CFBundleVersion",
    "SigningIdentity",
    "Team",
]


def _inject_application_properties(archive_path: Path, config: ReleaseConfig) -> bool:
    """Inject ApplicationProperties into xcarchive Info.plist if missing (TN3110 fix).

    Returns True if injection was performed or already present, False on error.
    """
    info_plist = archive_path / "Info.plist"
    if not info_plist.exists():
        console.print(f"  [red]Info.plist not found in archive: {info_plist}[/red]")
        return False

    # Check if ApplicationProperties already exists and is complete
    try:
        plist_read(info_plist, ":ApplicationProperties")
        missing_keys = []
        for key in APPLICATION_PROPERTIES_KEYS:
            try:
                plist_read(info_plist, f":ApplicationProperties:{key}")
            except subprocess.CalledProcessError:
                missing_keys.append(key)
        if not missing_keys:
            console.print("  ApplicationProperties already present and complete")
            return True
        console.print(f"  ApplicationProperties incomplete (missing: {', '.join(missing_keys)}), re-injecting...")
    except subprocess.CalledProcessError:
        pass  # Not present, need to inject

    console.print("  Injecting ApplicationProperties (TN3110 fix)...")

    # Find the .app inside the archive
    apps_dir = archive_path / "Products" / "Applications"
    if not apps_dir.exists():
        console.print(f"  [red]Applications dir not found: {apps_dir}[/red]")
        return False

    app_dirs = list(apps_dir.glob("*.app"))
    if not app_dirs:
        console.print("  [red]No .app found in archive[/red]")
        return False

    app_path = app_dirs[0]
    app_info_plist = app_path / "Info.plist"

    try:
        # Read values from the app's Info.plist
        bundle_id = plist_read(app_info_plist, ":CFBundleIdentifier")
        short_version = plist_read(app_info_plist, ":CFBundleShortVersionString")
        bundle_version = plist_read(app_info_plist, ":CFBundleVersion")

        # Get signing identity from codesign
        codesign_result = subprocess.run(
            ["codesign", "-dvv", str(app_path)],
            capture_output=True,
            text=True,
        )
        if codesign_result.returncode != 0:
            console.print(f"  [red]codesign failed: {codesign_result.stderr.strip()}[/red]")
            return False

        signing_identity = ""
        for line in codesign_result.stderr.splitlines():
            if line.startswith("Authority="):
                signing_identity = line.split("=", 1)[1]
                break

        if not signing_identity:
            console.print("  [red]Could not extract SigningIdentity from codesign output[/red]")
            return False

        # Relative app path inside archive
        app_relative = f"Applications/{app_path.name}"

        # Add ApplicationProperties dict
        plist_add(info_plist, ":ApplicationProperties", "dict")
        plist_add(info_plist, ":ApplicationProperties:ApplicationPath", "string", app_relative)
        plist_add(info_plist, ":ApplicationProperties:CFBundleIdentifier", "string", bundle_id)
        plist_add(info_plist, ":ApplicationProperties:CFBundleShortVersionString", "string", short_version)
        plist_add(info_plist, ":ApplicationProperties:CFBundleVersion", "string", bundle_version)
        plist_add(info_plist, ":ApplicationProperties:SigningIdentity", "string", signing_identity)
        plist_add(info_plist, ":ApplicationProperties:Team", "string", config.team_id)

        # Validate the modified plist is structurally sound
        valid, plist_error = validate_plist(info_plist)
        if not valid:
            console.print(f"  [red]Post-injection plist validation failed: {plist_error}[/red]")
            return False

        console.print(f"  Injected ApplicationProperties: {bundle_id} v{short_version}({bundle_version})")
        return True

    except subprocess.CalledProcessError as e:
        stderr_detail = e.stderr.strip() if e.stderr else "(no stderr)"
        console.print(f"  [red]PlistBuddy failed (rc={e.returncode}): {stderr_detail}[/red]")
        return False
    except (OSError, PermissionError) as e:
        console.print(f"  [red]File system error during injection: {e}[/red]")
        return False


def run_export(
    config: ReleaseConfig,
    *,
    archive_path: str = "",
    dry_run: bool = True,
) -> dict[str, object]:
    """Export IPA from xcarchive.

    Args:
        config: Release configuration.
        archive_path: Path to the .xcarchive from the archive step.
        dry_run: If True, only validate ExportOptions.plist.

    Returns:
        Result dict with success, ipa_path, etc.
    """
    # Validate ExportOptions.plist
    export_options = config.export_options_path
    if not export_options.exists():
        return {
            "success": False,
            "error": f"ExportOptions.plist not found: {export_options}",
        }

    valid, plist_error = validate_plist(export_options)
    if not valid:
        return {
            "success": False,
            "error": f"ExportOptions.plist is invalid: {plist_error}",
        }

    console.print(f"  ExportOptions.plist: {export_options} [green]valid[/green]")

    if dry_run:
        console.print("  [yellow]DRY-RUN: Cannot export from unsigned archive[/yellow]")
        return {
            "success": True,
            "export_options": str(export_options),
            "dry_run": True,
        }

    # Execute mode
    if not archive_path:
        return {"success": False, "error": "No archive path provided (archive step may have failed)"}

    xcarchive = Path(archive_path)
    if not xcarchive.exists():
        return {"success": False, "error": f"Archive not found: {xcarchive}"}

    # TN3110 fix: inject ApplicationProperties if missing
    if not _inject_application_properties(xcarchive, config):
        return {"success": False, "error": "Failed to inject ApplicationProperties (TN3110)"}

    # Export
    export_dir = config.build_dir / "export"
    export_dir.mkdir(parents=True, exist_ok=True)

    args = [
        "-exportArchive",
        "-archivePath", str(xcarchive),
        "-exportPath", str(export_dir),
        "-exportOptionsPlist", str(export_options),
    ]

    result = run_xcodebuild(args, cwd=config.project_root)

    if not result.success:
        error_msg = result.stderr.strip() or "exportArchive failed"
        return {
            "success": False,
            "error": error_msg,
            "return_code": result.return_code,
        }

    # Find the generated IPA
    ipa_files = list(export_dir.glob("*.ipa"))
    if not ipa_files:
        return {
            "success": False,
            "error": f"No IPA file found in export directory: {export_dir}",
        }

    ipa_path = ipa_files[0]
    console.print(f"  IPA exported: {ipa_path}")

    return {
        "success": True,
        "ipa_path": str(ipa_path),
        "export_dir": str(export_dir),
        "dry_run": False,
    }
