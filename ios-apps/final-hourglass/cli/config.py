"""iOS Release CLI configuration loader."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


REQUIRED_KEYS = [
    "APP_STORE_CONNECT_API_KEY_ID",
    "APP_STORE_CONNECT_API_ISSUER_ID",
    "APP_STORE_CONNECT_API_KEY_PATH",
    "APPLE_TEAM_ID",
    "APPLE_BUNDLE_ID",
]

EXPECTED_BUNDLE_ID = "com.AIUELAB.FinalHourglass"
EXPECTED_TEAM_ID = "N4UHXSGNLU"


@dataclass
class ReleaseConfig:
    """Release configuration loaded from .env or environment."""
    api_key_id: str = ""
    api_issuer_id: str = ""
    api_key_path: str = ""
    team_id: str = ""
    bundle_id: str = ""
    project_root: Path = field(default_factory=lambda: Path.cwd())

    @property
    def workspace_path(self) -> Path:
        return self.project_root / "FinalHourglass.xcworkspace"

    @property
    def xcodeproj_path(self) -> Path:
        return self.project_root / "FinalHourglass.xcodeproj"

    @property
    def fastlane_dir(self) -> Path:
        return self.project_root / "fastlane"

    @property
    def export_options_path(self) -> Path:
        return self.project_root / "ExportOptions.plist"

    @property
    def build_dir(self) -> Path:
        return self.project_root / "build"


def load_config(project_root: Path, *, dry_run: bool = True) -> tuple[ReleaseConfig, list[str], list[str]]:
    """Load configuration from .env.ios-release or environment variables.

    Returns:
        Tuple of (config, errors, warnings).
        In dry-run mode, missing values produce warnings instead of errors.
    """
    errors: list[str] = []
    warnings: list[str] = []

    env_file = project_root / ".env.ios-release"
    if env_file.exists():
        load_dotenv(env_file)
    else:
        warnings.append(f".env.ios-release not found at {env_file}, using environment variables")

    config = ReleaseConfig(
        api_key_id=os.getenv("APP_STORE_CONNECT_API_KEY_ID", ""),
        api_issuer_id=os.getenv("APP_STORE_CONNECT_API_ISSUER_ID", ""),
        api_key_path=os.getenv("APP_STORE_CONNECT_API_KEY_PATH", ""),
        team_id=os.getenv("APPLE_TEAM_ID", ""),
        bundle_id=os.getenv("APPLE_BUNDLE_ID", ""),
        project_root=project_root,
    )

    # Check required keys
    key_map = {
        "APP_STORE_CONNECT_API_KEY_ID": config.api_key_id,
        "APP_STORE_CONNECT_API_ISSUER_ID": config.api_issuer_id,
        "APP_STORE_CONNECT_API_KEY_PATH": config.api_key_path,
        "APPLE_TEAM_ID": config.team_id,
        "APPLE_BUNDLE_ID": config.bundle_id,
    }

    missing = [k for k, v in key_map.items() if not v]
    if missing:
        msg = f"Missing configuration: {', '.join(missing)}"
        if dry_run:
            warnings.append(msg)
        else:
            errors.append(msg)

    # Validate values when present
    if config.bundle_id and config.bundle_id != EXPECTED_BUNDLE_ID:
        warnings.append(
            f"Bundle ID mismatch: '{config.bundle_id}' (expected '{EXPECTED_BUNDLE_ID}')"
        )

    if config.team_id and config.team_id != EXPECTED_TEAM_ID:
        warnings.append(
            f"Team ID mismatch: '{config.team_id}' (expected '{EXPECTED_TEAM_ID}')"
        )

    # Check .p8 file exists (execute mode only)
    if not dry_run and config.api_key_path:
        p8_path = Path(config.api_key_path)
        if not p8_path.is_absolute():
            p8_path = project_root / p8_path
        if not p8_path.exists():
            errors.append(f"API key file not found: {p8_path}")

    return config, errors, warnings


def mask_sensitive(value: str) -> str:
    """Mask sensitive values for display (show first 4 chars only)."""
    if len(value) <= 4:
        return "****"
    return value[:4] + "****"
