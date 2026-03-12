"""Step 7: Submit - Submit app version for App Store review."""

from __future__ import annotations

import traceback
from pathlib import Path

from rich.console import Console

from ..config import ReleaseConfig
from ..utils.asc_api import ASCApiClient, ASCApiError

console = Console()


def run_submit(
    config: ReleaseConfig,
    *,
    dry_run: bool = True,
    release_version: str | None = None,
) -> dict[str, object]:
    """Submit the app version for App Store review.

    Args:
        config: Release configuration (contains ASC API key info).
        dry_run: If True, check readiness without actually submitting.
        release_version: Version string to look up if no editable version found.

    Returns:
        Result dict with success status and submission details.
    """
    errors: list[str] = []

    # Validate credentials
    if not config.api_key_id:
        errors.append("APP_STORE_CONNECT_API_KEY_ID not configured")
    if not config.api_issuer_id:
        errors.append("APP_STORE_CONNECT_API_ISSUER_ID not configured")

    # Resolve .p8 key file
    p8_path: Path | None = None
    if config.api_key_path:
        p8_path = Path(config.api_key_path)
        if not p8_path.is_absolute():
            p8_path = config.project_root / p8_path
        if not p8_path.exists():
            errors.append(f"API key file not found: {p8_path}")
    else:
        errors.append("APP_STORE_CONNECT_API_KEY_PATH not configured")

    if errors:
        if dry_run:
            console.print("  [yellow]DRY-RUN credential check failed:[/yellow]")
            for err in errors:
                console.print(f"    [red]{err}[/red]")
            console.print("  [yellow]These must be resolved before --execute[/yellow]")
        return {
            "success": False,
            "error": "Credential validation failed: " + "; ".join(errors),
            "dry_run": dry_run,
        }

    assert p8_path is not None  # guaranteed by validation above

    # Create API client
    try:
        client = ASCApiClient(
            key_id=config.api_key_id,
            issuer_id=config.api_issuer_id,
            key_path=p8_path,
        )
    except Exception as exc:
        return {
            "success": False,
            "error": f"Failed to create API client: {exc}",
            "dry_run": dry_run,
        }

    try:
        # Test connection
        if not client.test_connection():
            return {
                "success": False,
                "error": "API authentication failed. Check credentials.",
                "dry_run": dry_run,
            }
        console.print("  [green]API connection verified[/green]")

        # Find app
        app = client.find_app(config.bundle_id)
        if app is None:
            return {
                "success": False,
                "error": f"App not found for bundle ID: {config.bundle_id}",
                "dry_run": dry_run,
            }
        app_id = app["id"]
        app_name = app.get("attributes", {}).get("name", "Unknown")
        console.print(f"  App: {app_name} ({config.bundle_id})")

        # Get editable version (or look up by version string)
        version = client.get_editable_version(app_id)
        if version is None and release_version:
            console.print(f"  [yellow]No editable version. Looking up {release_version}...[/yellow]")
            version = client.find_version_by_string(app_id, release_version)
        if version is None:
            msg = "No version in PREPARE_FOR_SUBMISSION state"
            if dry_run:
                console.print(f"  [yellow]{msg}[/yellow]")
                return {
                    "success": True,
                    "dry_run": True,
                    "app_name": app_name,
                    "warning": msg,
                }
            return {
                "success": False,
                "error": msg,
                "dry_run": False,
            }

        version_id = version["id"]
        version_string = version.get("attributes", {}).get("versionString", "?")
        version_state = version.get("attributes", {}).get("appVersionState", "?")
        console.print(f"  Version: {version_string} ({version_state})")

        # Check if build is attached
        build = client.get_version_build(version_id)
        if build is None:
            msg = "No build attached to version. Upload and wait for processing."
            if dry_run:
                console.print(f"  [yellow]Warning: {msg}[/yellow]")
                return {
                    "success": True,
                    "dry_run": True,
                    "app_name": app_name,
                    "version": version_string,
                    "version_state": version_state,
                    "warning": msg,
                }
            return {
                "success": False,
                "error": msg,
                "dry_run": False,
            }

        build_version = build.get("attributes", {}).get("version", "?")
        console.print(f"  Build: {build_version} attached")

        if dry_run:
            console.print("  [green]Ready for submission[/green]")
            return {
                "success": True,
                "dry_run": True,
                "app_name": app_name,
                "version": version_string,
                "version_state": version_state,
                "build_version": build_version,
            }

        # Execute mode - submit for review
        console.print("  Submitting for App Store review...")
        client.submit_for_review(version_id)
        console.print("  [green]Successfully submitted for review[/green]")

        return {
            "success": True,
            "dry_run": False,
            "app_name": app_name,
            "version": version_string,
            "build_version": build_version,
        }

    except ASCApiError as exc:
        return {
            "success": False,
            "error": f"App Store Connect API error: {exc}",
            "dry_run": dry_run,
        }
    except Exception as exc:
        return {
            "success": False,
            "error": f"Unexpected error during submit: {exc}",
            "dry_run": dry_run,
            "traceback": traceback.format_exc(),
        }
