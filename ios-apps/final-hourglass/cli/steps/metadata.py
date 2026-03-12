"""Step 6: Metadata - Update App Store Connect metadata (What's New text)."""

from __future__ import annotations

import traceback
from pathlib import Path

from rich.console import Console

from ..config import ReleaseConfig
from ..utils.asc_api import ASCApiClient, ASCApiError

console = Console()


def run_metadata(
    config: ReleaseConfig,
    *,
    whats_new: str = "",
    release_version: str | None = None,
    dry_run: bool = True,
) -> dict[str, object]:
    """Update App Store Connect metadata (What's New / release notes).

    Args:
        config: Release configuration (contains ASC API key info).
        whats_new: The "What's New" text to set for ja-JP localization.
        release_version: Target version string (informational only).
        dry_run: If True, only read current metadata without making changes.

    Returns:
        Result dict with success status and metadata info.
    """
    errors: list[str] = []

    # ── 1. Resolve .p8 key path ──
    p8_path: Path | None = None
    if config.api_key_path:
        p8_path = Path(config.api_key_path)
        if not p8_path.is_absolute():
            p8_path = config.project_root / p8_path
        if not p8_path.exists():
            errors.append(f"API key file not found: {p8_path}")
    else:
        errors.append("APP_STORE_CONNECT_API_KEY_PATH not configured")

    # ── 2. Validate credentials ──
    if not config.api_key_id:
        errors.append("APP_STORE_CONNECT_API_KEY_ID not configured")
    if not config.api_issuer_id:
        errors.append("APP_STORE_CONNECT_API_ISSUER_ID not configured")

    if errors:
        msg = "Credential validation failed: " + "; ".join(errors)
        if dry_run:
            console.print("  [yellow]DRY-RUN credential check failed:[/yellow]")
            for err in errors:
                console.print(f"    [red]{err}[/red]")
            console.print("  [yellow]These must be resolved before --execute[/yellow]")
        return {"success": False, "error": msg, "dry_run": dry_run}

    # p8_path is guaranteed non-None here
    assert p8_path is not None

    # ── 3. Create ASC API client ──
    try:
        client = ASCApiClient(config.api_key_id, config.api_issuer_id, p8_path)
    except Exception as exc:
        return {
            "success": False,
            "error": f"Failed to create ASC API client: {exc}",
            "traceback": traceback.format_exc(),
        }

    # ── dry-run mode ──
    if dry_run:
        return _dry_run(client, config, release_version)

    # ── execute mode ──
    return _execute(client, config, whats_new, release_version)


def _dry_run(
    client: ASCApiClient,
    config: ReleaseConfig,
    release_version: str | None,
) -> dict[str, object]:
    """Dry-run: read current metadata without making changes."""
    try:
        # Test connection
        console.print("  Testing ASC API connection...")
        if not client.test_connection():
            return {
                "success": False,
                "error": "API authentication failed. Check credentials.",
                "dry_run": True,
            }
        console.print("  [green]API connection OK[/green]")

        # Find app
        console.print(f"  Looking up app: {config.bundle_id}")
        app = client.find_app(config.bundle_id)
        if app is None:
            return {
                "success": False,
                "error": f"App not found for bundle ID: {config.bundle_id}",
                "dry_run": True,
            }
        app_id = app["id"]
        app_name = app.get("attributes", {}).get("name", "Unknown")
        console.print(f"  [green]Found app: {app_name} ({app_id})[/green]")

        # Get editable version
        console.print("  Fetching editable version...")
        version = client.get_editable_version(app_id)
        if version is None:
            console.print("  [yellow]No version in PREPARE_FOR_SUBMISSION state[/yellow]")
            if release_version:
                console.print(f"  [cyan]Would create version: {release_version}[/cyan]")
            else:
                console.print("  [yellow]No release_version specified — cannot create version[/yellow]")
            console.print("  [cyan]Would search and attach build[/cyan]")
            return {
                "success": True,
                "dry_run": True,
                "app_id": app_id,
                "app_name": app_name,
                "warning": "No version in PREPARE_FOR_SUBMISSION state",
                "would_create_version": release_version,
            }
        version_string = version.get("attributes", {}).get("versionString", "Unknown")
        version_state = version.get("attributes", {}).get("appStoreState", "Unknown")
        version_id = version["id"]
        console.print(f"  [green]Editable version: {version_string} ({version_state})[/green]")

        if release_version and version_string != release_version:
            console.print(
                f"  [yellow]Warning: editable version {version_string} "
                f"differs from target {release_version}[/yellow]"
            )

        # Check build attachment
        console.print("  Checking build attachment...")
        existing_build = client.get_version_build(version_id)
        if existing_build is None:
            console.print("  [yellow]No build attached to this version[/yellow]")
            console.print("  [cyan]Would search and attach build[/cyan]")
        else:
            existing_build_version = existing_build.get("attributes", {}).get("version", "Unknown")
            console.print(f"  [green]Build already attached: {existing_build_version}[/green]")

        # Get localizations
        console.print("  Fetching version localizations...")
        localizations = client.get_version_localizations(version_id)

        current_whats_new: str | None = None
        locale_found: str | None = None

        for loc in localizations:
            locale = loc.get("attributes", {}).get("locale", "")
            wn = loc.get("attributes", {}).get("whatsNew", "")
            console.print(f"    Locale: {locale}")
            if locale == "ja-JP" or (locale_found is None and localizations):
                current_whats_new = wn
                locale_found = locale

        if locale_found:
            console.print(f"  [green]Current What's New ({locale_found}):[/green]")
            display = current_whats_new or "(empty)"
            console.print(f"    {display}")
        else:
            console.print("  [yellow]No localizations found[/yellow]")

        return {
            "success": True,
            "dry_run": True,
            "app_id": app_id,
            "app_name": app_name,
            "version_string": version_string,
            "version_state": version_state,
            "current_whats_new": current_whats_new,
            "locale": locale_found,
        }

    except ASCApiError as exc:
        console.print(f"  [red]ASC API error: {exc}[/red]")
        return {"success": False, "error": str(exc), "dry_run": True}
    except Exception as exc:
        console.print(f"  [red]Unexpected error: {exc}[/red]")
        return {
            "success": False,
            "error": f"Unexpected error: {exc}",
            "dry_run": True,
            "traceback": traceback.format_exc(),
        }


def _execute(
    client: ASCApiClient,
    config: ReleaseConfig,
    whats_new: str,
    release_version: str | None,
) -> dict[str, object]:
    """Execute mode: update What's New text."""
    # whats_new is required in execute mode
    if not whats_new:
        return {
            "success": False,
            "error": "whats_new is required in execute mode",
        }

    try:
        # All dry-run checks first
        console.print("  Testing ASC API connection...")
        if not client.test_connection():
            return {
                "success": False,
                "error": "API authentication failed. Check credentials.",
            }
        console.print("  [green]API connection OK[/green]")

        console.print(f"  Looking up app: {config.bundle_id}")
        app = client.find_app(config.bundle_id)
        if app is None:
            return {
                "success": False,
                "error": f"App not found for bundle ID: {config.bundle_id}",
            }
        app_id = app["id"]
        app_name = app.get("attributes", {}).get("name", "Unknown")
        console.print(f"  [green]Found app: {app_name} ({app_id})[/green]")

        console.print("  Fetching editable version...")
        version = client.get_editable_version(app_id)
        if version is None and release_version:
            # No PREPARE_FOR_SUBMISSION version — check if version already exists in another state
            console.print(f"  [yellow]No editable version found. Looking up version {release_version}...[/yellow]")
            existing = client.find_version_by_string(app_id, release_version)
            if existing is not None:
                existing_state = existing.get("attributes", {}).get("appVersionState", "?")
                console.print(f"  [green]Found version {release_version} in state: {existing_state}[/green]")
                version = existing
            else:
                # Delete any DEVELOPER_REJECTED versions that block new version creation
                all_versions = client.get_all_versions(app_id)
                for v in all_versions:
                    v_state = v.get("attributes", {}).get("appVersionState", "")
                    v_string = v.get("attributes", {}).get("versionString", "?")
                    if v_state == "DEVELOPER_REJECTED":
                        console.print(f"  [yellow]Deleting DEVELOPER_REJECTED version {v_string}...[/yellow]")
                        client.delete_version(v["id"])
                        console.print(f"  [green]Deleted version {v_string}[/green]")
                console.print(f"  [yellow]Creating version {release_version}...[/yellow]")
                version = client.create_version(app_id, release_version)
                console.print(f"  [green]Created new version: {release_version}[/green]")
        elif version is None:
            return {
                "success": False,
                "error": "No version in PREPARE_FOR_SUBMISSION state and no release_version specified to create one.",
            }

        version_string = version.get("attributes", {}).get("versionString", "Unknown")
        version_state = version.get("attributes", {}).get("appStoreState", "Unknown")
        version_id = version["id"]
        console.print(f"  [green]Editable version: {version_string} ({version_state})[/green]")

        if release_version and version_string != release_version:
            console.print(
                f"  [yellow]Warning: editable version {version_string} "
                f"differs from target {release_version}[/yellow]"
            )

        # ── Ensure a build is attached to this version ──
        console.print("  Checking build attachment...")
        existing_build = client.get_version_build(version_id)
        if existing_build is None:
            console.print("  [yellow]No build attached. Searching for a processed build...[/yellow]")
            build = client.find_build(app_id, release_version or version_string)
            if build is not None:
                build_id = build["id"]
                build_version = build.get("attributes", {}).get("version", "Unknown")
                client.attach_build(version_id, build_id)
                console.print(f"  [green]Attached build: {build_version}[/green]")
            else:
                console.print(
                    "  [yellow]Warning: No processed build found. "
                    "Build may still be processing in App Store Connect.[/yellow]"
                )
        else:
            existing_build_version = existing_build.get("attributes", {}).get("version", "Unknown")
            console.print(f"  [green]Build already attached: {existing_build_version}[/green]")

        # Get localizations and find ja-JP (or first available)
        console.print("  Fetching version localizations...")
        localizations = client.get_version_localizations(version_id)

        target_loc: dict | None = None
        for loc in localizations:
            locale = loc.get("attributes", {}).get("locale", "")
            if locale == "ja-JP":
                target_loc = loc
                break
        if target_loc is None and localizations:
            target_loc = localizations[0]

        if target_loc is None:
            return {
                "success": False,
                "error": "No localizations found for this version",
            }

        localization_id = target_loc["id"]
        target_locale = target_loc.get("attributes", {}).get("locale", "Unknown")
        old_whats_new = target_loc.get("attributes", {}).get("whatsNew", "")

        console.print(f"  Updating What's New for {target_locale}...")
        console.print(f"    Old: {old_whats_new or '(empty)'}")
        console.print(f"    New: {whats_new}")

        # Update
        client.update_whats_new(localization_id, whats_new)
        console.print(f"  [green]What's New updated successfully for {target_locale}[/green]")

        return {
            "success": True,
            "dry_run": False,
            "app_id": app_id,
            "app_name": app_name,
            "version_string": version_string,
            "locale": target_locale,
            "old_whats_new": old_whats_new,
            "new_whats_new": whats_new,
        }

    except ASCApiError as exc:
        console.print(f"  [red]ASC API error: {exc}[/red]")
        return {"success": False, "error": str(exc)}
    except Exception as exc:
        console.print(f"  [red]Unexpected error: {exc}[/red]")
        return {
            "success": False,
            "error": f"Unexpected error: {exc}",
            "traceback": traceback.format_exc(),
        }
