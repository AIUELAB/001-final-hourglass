"""Step 5: Upload - Upload IPA to TestFlight via xcrun altool."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from rich.console import Console

from ..config import ReleaseConfig

console = Console()


def run_upload(
    config: ReleaseConfig,
    *,
    ipa_path: str = "",
    dry_run: bool = True,
) -> dict[str, object]:
    """Upload IPA to TestFlight using xcrun altool.

    Args:
        config: Release configuration (contains ASC API key info).
        ipa_path: Path to the .ipa file to upload.
        dry_run: If True, only validate credentials exist without uploading.

    Returns:
        Result dict with success status.
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

    if dry_run:
        if errors:
            console.print("  [yellow]DRY-RUN credential check failed:[/yellow]")
            for err in errors:
                console.print(f"    [red]{err}[/red]")
            console.print("  [yellow]These must be resolved before --execute[/yellow]")
            return {
                "success": False,
                "error": "Credential validation failed: " + "; ".join(errors),
                "dry_run": True,
            }
        else:
            console.print("  [green]Credentials validated[/green]")
            console.print(f"    API Key ID: {config.api_key_id[:4]}****")
            console.print(f"    API Key file: {p8_path}")
            return {
                "success": True,
                "dry_run": True,
            }

    # Execute mode - all credentials required
    if errors:
        return {
            "success": False,
            "error": "; ".join(errors),
        }

    # Validate IPA path
    if not ipa_path:
        return {"success": False, "error": "No IPA path provided (export step may have failed)"}

    ipa_file = Path(ipa_path)
    if not ipa_file.exists():
        return {"success": False, "error": f"IPA file not found: {ipa_file}"}

    if p8_path is None:
        return {"success": False, "error": "Internal error: p8_path is None after credential validation"}

    # Set up API_PRIVATE_KEYS_DIR for altool
    api_keys_dir = str(p8_path.parent)

    console.print("  [yellow]Note: xcrun altool is deprecated in Xcode 14+. "
                   "Consider migrating to App Store Connect API.[/yellow]")
    console.print(f"  Uploading {ipa_file.name} to TestFlight...")

    cmd = [
        "xcrun", "altool",
        "--upload-app",
        "--file", str(ipa_file),
        "--type", "ios",
        "--apiKey", config.api_key_id,
        "--apiIssuer", config.api_issuer_id,
    ]

    try:
        env = os.environ.copy()
        env["API_PRIVATE_KEYS_DIR"] = api_keys_dir

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
            env=env,
        )

        if result.returncode == 0:
            console.print("  [green]Upload successful[/green]")
            return {
                "success": True,
                "ipa_path": str(ipa_file),
                "dry_run": False,
            }
        else:
            error_msg = result.stderr.strip() or result.stdout.strip()
            return {
                "success": False,
                "error": f"altool upload failed: {error_msg}",
                "return_code": result.returncode,
            }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Upload timed out after 600s",
        }
    except FileNotFoundError:
        return {
            "success": False,
            "error": "xcrun not found. Is Xcode installed?",
        }
