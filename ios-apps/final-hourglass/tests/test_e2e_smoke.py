# pyright: reportPrivateUsage=false
"""E2E smoke tests for iOS Release CLI using Click's CliRunner."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from cli.ios_release import main


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    ws = tmp_path / "FinalHourglass.xcworkspace"
    ws.mkdir()
    xp = tmp_path / "FinalHourglass.xcodeproj"
    xp.mkdir()
    pbxproj = xp / "project.pbxproj"
    pbxproj.write_text("MARKETING_VERSION = 1.0.10;\nCURRENT_PROJECT_VERSION = 5;\n")
    fl = tmp_path / "fastlane"
    fl.mkdir()
    (fl / "Fastfile").write_text("lane :release do\nend\n")
    (fl / "Appfile").write_text('app_identifier "com.AIUELAB.FinalHourglass"\n' 'team_id "N4UHXSGNLU"\n')
    # Create parent dirs for report output (project_root.parent.parent / src/reports/ios)
    repo_root = tmp_path.parent.parent
    (repo_root / "src" / "reports" / "ios").mkdir(parents=True, exist_ok=True)
    return tmp_path


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def clean_env() -> dict[str, str]:
    env = os.environ.copy()
    for key in [
        "APP_STORE_CONNECT_API_KEY_ID",
        "APP_STORE_CONNECT_API_ISSUER_ID",
        "APP_STORE_CONNECT_API_KEY_PATH",
        "APPLE_TEAM_ID",
        "APPLE_BUNDLE_ID",
    ]:
        env.pop(key, None)
    return env


# ============================================================
# Tests
# ============================================================


class TestValidateReportDryRun:
    def test_validate_and_report_exit_zero(self, runner: CliRunner, project_dir: Path, clean_env: dict[str, str]):
        with patch.dict(os.environ, clean_env, clear=True):
            result = runner.invoke(
                main,
                [
                    "--step",
                    "validate",
                    "--step",
                    "report",
                    "--project-root",
                    str(project_dir),
                ],
            )
        assert result.exit_code == 0, result.output


class TestValidateVersionReportDryRun:
    def test_validate_version_report_with_valid_version(
        self, runner: CliRunner, project_dir: Path, clean_env: dict[str, str]
    ):
        with patch.dict(os.environ, clean_env, clear=True):
            result = runner.invoke(
                main,
                [
                    "--step",
                    "validate",
                    "--step",
                    "version",
                    "--step",
                    "report",
                    "--version",
                    "1.0.11",
                    "--project-root",
                    str(project_dir),
                ],
            )
        assert result.exit_code == 0, result.output
        assert "1.0.11" in result.output


class TestInvalidVersionFails:
    def test_validate_rejects_bad_version_format(self, runner: CliRunner, project_dir: Path, clean_env: dict[str, str]):
        with patch.dict(os.environ, clean_env, clear=True):
            result = runner.invoke(
                main,
                [
                    "--step",
                    "validate",
                    "--version",
                    "abc",
                    "--project-root",
                    str(project_dir),
                ],
            )
        assert result.exit_code != 0
        assert "Invalid version format" in result.output


class TestCiModeOutput:
    def test_ci_flag_suppresses_color(self, runner: CliRunner, project_dir: Path, clean_env: dict[str, str]):
        with patch.dict(os.environ, clean_env, clear=True):
            result = runner.invoke(
                main,
                [
                    "--ci",
                    "--step",
                    "validate",
                    "--step",
                    "report",
                    "--project-root",
                    str(project_dir),
                ],
            )
        assert result.exit_code == 0, result.output
        # CI mode should not contain ANSI escape codes
        assert "\x1b[" not in result.output


class TestStepDataPassthrough:
    def test_report_file_created_after_validate_version(
        self, runner: CliRunner, project_dir: Path, clean_env: dict[str, str]
    ):
        with patch.dict(os.environ, clean_env, clear=True):
            result = runner.invoke(
                main,
                [
                    "--step",
                    "validate",
                    "--step",
                    "version",
                    "--step",
                    "report",
                    "--version",
                    "1.0.11",
                    "--project-root",
                    str(project_dir),
                ],
            )
        assert result.exit_code == 0, result.output
        assert "Report:" in result.output or "report_path" in result.output
        # Verify report file actually exists
        repo_root = project_dir.parent.parent
        report_dir = repo_root / "src" / "reports" / "ios"
        report_files = list(report_dir.glob("release_report_*.md"))
        assert len(report_files) >= 1


class TestNoProjectRootFound:
    def test_fails_when_workspace_missing(self, runner: CliRunner, clean_env: dict[str, str]):
        # tmp_path has no FinalHourglass.xcworkspace, and no --project-root
        with patch.dict(os.environ, clean_env, clear=True):
            with patch("cli.ios_release.resolve_project_root") as mock_resolve:
                from click import UsageError

                mock_resolve.side_effect = UsageError("Could not find FinalHourglass project root.")
                result = runner.invoke(
                    main,
                    ["--step", "validate"],
                )
        assert result.exit_code != 0
        assert "Could not find FinalHourglass project root" in result.output


class TestMultipleStepSelection:
    def test_validate_and_version_both_run(self, runner: CliRunner, project_dir: Path, clean_env: dict[str, str]):
        with patch.dict(os.environ, clean_env, clear=True):
            result = runner.invoke(
                main,
                [
                    "--step",
                    "validate",
                    "--step",
                    "version",
                    "--version",
                    "1.0.11",
                    "--project-root",
                    str(project_dir),
                ],
            )
        assert result.exit_code == 0, result.output
        # Both steps should appear in output
        assert "validate" in result.output.lower()
        assert "version" in result.output.lower()


class TestDryRunIsDefault:
    def test_default_mode_is_dry_run(self, runner: CliRunner, project_dir: Path, clean_env: dict[str, str]):
        with patch.dict(os.environ, clean_env, clear=True):
            result = runner.invoke(
                main,
                [
                    "--step",
                    "validate",
                    "--step",
                    "report",
                    "--project-root",
                    str(project_dir),
                ],
            )
        assert result.exit_code == 0, result.output
        assert "DRY-RUN" in result.output
