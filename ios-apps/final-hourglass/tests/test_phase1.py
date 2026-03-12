# pyright: reportPrivateUsage=false, reportOperatorIssue=false, reportGeneralTypeIssues=false, reportArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cli.config import ReleaseConfig, EXPECTED_BUNDLE_ID, EXPECTED_TEAM_ID

MOCK_P8_KEY = """\
-----BEGIN EC PRIVATE KEY-----
MHQCAQEEIBkg4LVWM9buwBsxAkOL6MFHV1MkzCZ0wKqmLEUN0JzoAcGBSuBBAAi
oWQDYgAE2a2gLqdjJxp4dD3VRyFaFnYBKBDqHQdrPelAs+gI+bSuEVBFMqbfPKSC
cJIXKn6qRU7t5JAy1VkMGKwT3bKCERxmHxZC8BjTUvJnVEHKmyWQz3EKkBmZiR1j
vReJ2RPs
-----END EC PRIVATE KEY-----
"""


def make_config(tmp_path: Path, *, p8_exists: bool = True) -> ReleaseConfig:
    if p8_exists:
        key_file = tmp_path / "AuthKey_TEST.p8"
        key_file.write_text(MOCK_P8_KEY)
        key_path = str(key_file)
    else:
        key_path = str(tmp_path / "missing.p8")

    return ReleaseConfig(
        api_key_id="TESTKEY123",
        api_issuer_id="test-issuer-uuid",
        api_key_path=key_path,
        team_id=EXPECTED_TEAM_ID,
        bundle_id=EXPECTED_BUNDLE_ID,
        project_root=tmp_path,
    )


def _setup_project_files(
    tmp_path: Path,
    *,
    workspace: bool = True,
    xcodeproj: bool = True,
    fastfile: bool = True,
    export_options: bool = False,
    appfile_content: str | None = None,
    plist_content: str | None = None,
) -> None:
    if workspace:
        (tmp_path / "FinalHourglass.xcworkspace").mkdir()
    if xcodeproj:
        (tmp_path / "FinalHourglass.xcodeproj").mkdir()
    if fastfile:
        (tmp_path / "fastlane").mkdir(exist_ok=True)
        (tmp_path / "fastlane" / "Fastfile").write_text("lane :release do\nend\n")
    if appfile_content is not None:
        (tmp_path / "fastlane").mkdir(exist_ok=True)
        (tmp_path / "fastlane" / "Appfile").write_text(appfile_content)
    if export_options:
        content = (
            plist_content
            or f"<plist><dict><key>teamID</key><string>{EXPECTED_TEAM_ID}</string><key>bundleID</key><string>{EXPECTED_BUNDLE_ID}</string></dict></plist>"
        )
        (tmp_path / "ExportOptions.plist").write_text(content)


# ============================================================================
# Tests for cli.config
# ============================================================================


class TestLoadConfig:
    @patch("cli.config.load_dotenv")
    def test_env_file_exists_calls_load_dotenv(self, mock_dotenv, tmp_path):
        from cli.config import load_config

        env_file = tmp_path / ".env.ios-release"
        env_file.write_text("APPLE_TEAM_ID=X\n")
        with patch.dict(os.environ, {}, clear=True):
            load_config(tmp_path, dry_run=True)
        mock_dotenv.assert_called_once_with(env_file)

    @patch("cli.config.load_dotenv")
    def test_env_file_not_exists_warns(self, mock_dotenv, tmp_path):
        from cli.config import load_config

        with patch.dict(os.environ, {}, clear=True):
            _, _, warnings = load_config(tmp_path, dry_run=True)
        mock_dotenv.assert_not_called()
        assert any(".env.ios-release not found" in w for w in warnings)

    @patch("cli.config.load_dotenv")
    def test_dry_run_missing_keys_warns(self, _mock_dotenv, tmp_path):
        from cli.config import load_config

        with patch.dict(os.environ, {}, clear=True):
            _, errors, warnings = load_config(tmp_path, dry_run=True)
        assert len(errors) == 0
        assert any("Missing configuration" in w for w in warnings)

    @patch("cli.config.load_dotenv")
    def test_execute_missing_keys_errors(self, _mock_dotenv, tmp_path):
        from cli.config import load_config

        with patch.dict(os.environ, {}, clear=True):
            _, errors, warnings = load_config(tmp_path, dry_run=False)
        assert any("Missing configuration" in e for e in errors)

    @patch("cli.config.load_dotenv")
    def test_bundle_id_mismatch_warns(self, _mock_dotenv, tmp_path):
        from cli.config import load_config

        env = {
            "APP_STORE_CONNECT_API_KEY_ID": "K",
            "APP_STORE_CONNECT_API_ISSUER_ID": "I",
            "APP_STORE_CONNECT_API_KEY_PATH": "/tmp/k.p8",
            "APPLE_TEAM_ID": EXPECTED_TEAM_ID,
            "APPLE_BUNDLE_ID": "com.other.App",
        }
        with patch.dict(os.environ, env, clear=True):
            _, _, warnings = load_config(tmp_path, dry_run=True)
        assert any("Bundle ID mismatch" in w for w in warnings)

    @patch("cli.config.load_dotenv")
    def test_team_id_mismatch_warns(self, _mock_dotenv, tmp_path):
        from cli.config import load_config

        env = {
            "APP_STORE_CONNECT_API_KEY_ID": "K",
            "APP_STORE_CONNECT_API_ISSUER_ID": "I",
            "APP_STORE_CONNECT_API_KEY_PATH": "/tmp/k.p8",
            "APPLE_TEAM_ID": "WRONGTEAM",
            "APPLE_BUNDLE_ID": EXPECTED_BUNDLE_ID,
        }
        with patch.dict(os.environ, env, clear=True):
            _, _, warnings = load_config(tmp_path, dry_run=True)
        assert any("Team ID mismatch" in w for w in warnings)

    @patch("cli.config.load_dotenv")
    def test_p8_file_exists_no_error(self, _mock_dotenv, tmp_path):
        from cli.config import load_config

        p8 = tmp_path / "key.p8"
        p8.write_text(MOCK_P8_KEY)
        env = {
            "APP_STORE_CONNECT_API_KEY_ID": "K",
            "APP_STORE_CONNECT_API_ISSUER_ID": "I",
            "APP_STORE_CONNECT_API_KEY_PATH": str(p8),
            "APPLE_TEAM_ID": EXPECTED_TEAM_ID,
            "APPLE_BUNDLE_ID": EXPECTED_BUNDLE_ID,
        }
        with patch.dict(os.environ, env, clear=True):
            _, errors, _ = load_config(tmp_path, dry_run=False)
        assert not any("API key file not found" in e for e in errors)

    @patch("cli.config.load_dotenv")
    def test_p8_file_missing_execute_errors(self, _mock_dotenv, tmp_path):
        from cli.config import load_config

        env = {
            "APP_STORE_CONNECT_API_KEY_ID": "K",
            "APP_STORE_CONNECT_API_ISSUER_ID": "I",
            "APP_STORE_CONNECT_API_KEY_PATH": str(tmp_path / "nonexistent.p8"),
            "APPLE_TEAM_ID": EXPECTED_TEAM_ID,
            "APPLE_BUNDLE_ID": EXPECTED_BUNDLE_ID,
        }
        with patch.dict(os.environ, env, clear=True):
            _, errors, _ = load_config(tmp_path, dry_run=False)
        assert any("API key file not found" in e for e in errors)

    @patch("cli.config.load_dotenv")
    def test_relative_p8_path_resolved(self, _mock_dotenv, tmp_path):
        from cli.config import load_config

        (tmp_path / "keys").mkdir()
        p8 = tmp_path / "keys" / "auth.p8"
        p8.write_text(MOCK_P8_KEY)
        env = {
            "APP_STORE_CONNECT_API_KEY_ID": "K",
            "APP_STORE_CONNECT_API_ISSUER_ID": "I",
            "APP_STORE_CONNECT_API_KEY_PATH": "keys/auth.p8",
            "APPLE_TEAM_ID": EXPECTED_TEAM_ID,
            "APPLE_BUNDLE_ID": EXPECTED_BUNDLE_ID,
        }
        with patch.dict(os.environ, env, clear=True):
            _, errors, _ = load_config(tmp_path, dry_run=False)
        assert not any("API key file not found" in e for e in errors)


class TestMaskSensitive:
    def test_short_string_returns_stars(self):
        from cli.config import mask_sensitive

        assert mask_sensitive("abc") == "****"
        assert mask_sensitive("abcd") == "****"

    def test_longer_string_shows_prefix(self):
        from cli.config import mask_sensitive

        assert mask_sensitive("TESTKEY123") == "TEST****"

    def test_exactly_five_chars(self):
        from cli.config import mask_sensitive

        assert mask_sensitive("12345") == "1234****"


# ============================================================================
# Tests for cli.steps.validate
# ============================================================================


class TestRunValidate:
    def test_valid_version_format(self, tmp_path):
        from cli.steps.validate import run_validate

        config = make_config(tmp_path)
        _setup_project_files(tmp_path)
        result = run_validate(config, release_version="1.0.1")
        assert "Invalid version format" not in str(result["errors"])

    def test_invalid_version_format(self, tmp_path):
        from cli.steps.validate import run_validate

        config = make_config(tmp_path)
        _setup_project_files(tmp_path)
        result = run_validate(config, release_version="abc")
        assert result["success"] is False
        assert any("Invalid version format" in e for e in result["errors"])

    def test_no_version_warns(self, tmp_path):
        from cli.steps.validate import run_validate

        config = make_config(tmp_path)
        _setup_project_files(tmp_path)
        result = run_validate(config)
        assert any("No version specified" in w for w in result["warnings"])

    def test_workspace_not_found(self, tmp_path):
        from cli.steps.validate import run_validate

        config = make_config(tmp_path)
        _setup_project_files(tmp_path, workspace=False)
        result = run_validate(config, release_version="1.0.0")
        assert any("Workspace not found" in e for e in result["errors"])

    def test_xcodeproj_not_found(self, tmp_path):
        from cli.steps.validate import run_validate

        config = make_config(tmp_path)
        _setup_project_files(tmp_path, xcodeproj=False)
        result = run_validate(config, release_version="1.0.0")
        assert any("Xcodeproj not found" in e for e in result["errors"])

    def test_fastfile_not_found(self, tmp_path):
        from cli.steps.validate import run_validate

        config = make_config(tmp_path)
        _setup_project_files(tmp_path, fastfile=False)
        result = run_validate(config, release_version="1.0.0")
        assert any("Fastfile not found" in e for e in result["errors"])

    def test_export_options_missing_warns(self, tmp_path):
        from cli.steps.validate import run_validate

        config = make_config(tmp_path)
        _setup_project_files(tmp_path, export_options=False)
        result = run_validate(config, release_version="1.0.0")
        assert any("ExportOptions.plist not found" in w for w in result["warnings"])

    def test_appfile_bundle_id_mismatch(self, tmp_path):
        from cli.steps.validate import run_validate

        config = make_config(tmp_path)
        _setup_project_files(
            tmp_path, appfile_content=f'app_identifier("com.wrong.id")\nteam_id("{EXPECTED_TEAM_ID}")\n'
        )
        result = run_validate(config, release_version="1.0.0")
        assert any("Appfile Bundle ID mismatch" in e for e in result["errors"])

    def test_appfile_team_id_mismatch(self, tmp_path):
        from cli.steps.validate import run_validate

        config = make_config(tmp_path)
        _setup_project_files(
            tmp_path, appfile_content=f'app_identifier("{EXPECTED_BUNDLE_ID}")\nteam_id("WRONGTEAM")\n'
        )
        result = run_validate(config, release_version="1.0.0")
        assert any("Appfile Team ID mismatch" in e for e in result["errors"])

    def test_export_options_content_mismatch(self, tmp_path):
        from cli.steps.validate import run_validate

        config = make_config(tmp_path)
        _setup_project_files(
            tmp_path,
            export_options=True,
            plist_content="<plist><dict><key>teamID</key><string>WRONG</string></dict></plist>",
        )
        result = run_validate(config, release_version="1.0.0")
        assert any("ExportOptions.plist" in e and "mismatch" in e for e in result["errors"])

    def test_config_values_mismatch(self, tmp_path):
        from cli.steps.validate import run_validate

        config = ReleaseConfig(
            api_key_id="K",
            api_issuer_id="I",
            api_key_path="/tmp/k.p8",
            team_id="WRONGTEAM",
            bundle_id="com.wrong.id",
            project_root=tmp_path,
        )
        _setup_project_files(tmp_path)
        result = run_validate(config, release_version="1.0.0")
        assert any("Config Bundle ID mismatch" in e for e in result["errors"])
        assert any("Config Team ID mismatch" in e for e in result["errors"])

    @patch("cli.steps.validate.sys")
    @patch("cli.steps.validate.subprocess.run")
    def test_signing_identity_check(self, mock_run, mock_sys, tmp_path):
        from cli.steps.validate import run_validate

        mock_sys.platform = "darwin"
        mock_run.return_value = MagicMock(stdout='1 valid identities found\n  1) ABCDEF "Apple Distribution"')
        config = make_config(tmp_path)
        _setup_project_files(tmp_path)
        result = run_validate(config, release_version="1.0.0")
        assert result["signing_info"] != ""
        assert "No valid code signing" not in str(result["warnings"])


# ============================================================================
# Tests for cli.steps.archive
# ============================================================================


class TestRunArchive:
    def test_dry_run_includes_code_signing_disabled(self, tmp_path):
        from cli.steps.archive import run_archive
        from cli.utils.xcodebuild import XcodebuildResult

        config = make_config(tmp_path)
        mock_result = XcodebuildResult(success=True, return_code=0, duration=10.0)
        with patch("cli.steps.archive.run_xcodebuild", return_value=mock_result) as mock_xb:
            run_archive(config, dry_run=True)
        args = mock_xb.call_args[0][0]
        assert "CODE_SIGNING_ALLOWED=NO" in args

    def test_execute_passes_version(self, tmp_path):
        from cli.steps.archive import run_archive
        from cli.utils.xcodebuild import XcodebuildResult

        config = make_config(tmp_path)
        mock_result = XcodebuildResult(success=True, return_code=0, duration=5.0)
        with patch("cli.steps.archive.run_xcodebuild", return_value=mock_result) as mock_xb:
            run_archive(config, release_version="2.0.0", build_number="99", dry_run=False)
        args = mock_xb.call_args[0][0]
        assert "MARKETING_VERSION=2.0.0" in args
        assert "CURRENT_PROJECT_VERSION=99" in args
        assert "CODE_SIGNING_ALLOWED=NO" not in args

    def test_success_returns_archive_path(self, tmp_path):
        from cli.steps.archive import run_archive
        from cli.utils.xcodebuild import XcodebuildResult

        config = make_config(tmp_path)
        mock_result = XcodebuildResult(success=True, return_code=0, duration=8.0)
        with patch("cli.steps.archive.run_xcodebuild", return_value=mock_result):
            result = run_archive(config, dry_run=True)
        assert result["success"] is True
        assert "FinalHourglass.xcarchive" in result["archive_path"]

    def test_failure_returns_error(self, tmp_path):
        from cli.steps.archive import run_archive
        from cli.utils.xcodebuild import XcodebuildResult

        config = make_config(tmp_path)
        mock_result = XcodebuildResult(
            success=False, return_code=65, stderr="error: Build input file cannot be found", duration=3.0
        )
        with patch("cli.steps.archive.run_xcodebuild", return_value=mock_result):
            result = run_archive(config, dry_run=True)
        assert result["success"] is False
        assert result["archive_path"] == ""
        assert "error:" in result["error"].lower()


class TestExtractError:
    def test_stderr_with_error_line(self):
        from cli.steps.archive import _extract_error

        result = _extract_error("some output\nerror: undefined symbol\nmore", "")
        assert "undefined symbol" in result

    def test_stdout_error_not_comment(self):
        from cli.steps.archive import _extract_error

        result = _extract_error("", "// error: this is a comment\nerror: real problem here\n")
        assert "real problem here" in result

    def test_stdout_comment_only_falls_through(self):
        from cli.steps.archive import _extract_error

        result = _extract_error("", "// error: this is a comment\nno errors here\n")
        assert "xcodebuild failed" in result

    def test_fallback_tail_output(self):
        from cli.steps.archive import _extract_error

        result = _extract_error("", "line1\nline2\nline3\n")
        assert "xcodebuild failed" in result
        assert "line3" in result

    def test_empty_output(self):
        from cli.steps.archive import _extract_error

        result = _extract_error("", "")
        assert "(no output)" in result


# ============================================================================
# Tests for cli.steps.report
# ============================================================================


class TestRunReport:
    def test_all_success_report(self, tmp_path):
        from cli.steps.report import run_report

        config = make_config(tmp_path)
        results = {"validate": {"success": True, "duration": 1.0, "errors": [], "warnings": []}}
        result = run_report(config, results=results, release_version="1.0.0", dry_run=True, total_duration=5.0)
        assert result["success"] is True
        content = Path(result["report_path"]).read_text()
        assert "All steps completed successfully" in content
        assert "DRY-RUN" in content

    def test_report_with_errors(self, tmp_path):
        from cli.steps.report import run_report

        config = make_config(tmp_path)
        results = {
            "archive": {
                "success": False,
                "duration": 2.0,
                "errors": ["Build failed"],
                "error": "exit 65",
                "warnings": [],
            }
        }
        result = run_report(config, results=results, release_version="1.0.0", dry_run=False, total_duration=3.0)
        content = Path(result["report_path"]).read_text()
        assert "## Errors" in content
        assert "Build failed" in content
        assert "Some steps failed" in content

    def test_report_with_warnings(self, tmp_path):
        from cli.steps.report import run_report

        config = make_config(tmp_path)
        results = {"validate": {"success": True, "duration": 0.5, "errors": [], "warnings": ["No signing identity"]}}
        result = run_report(config, results=results, release_version="1.0.0", dry_run=True)
        content = Path(result["report_path"]).read_text()
        assert "## Warnings" in content
        assert "No signing identity" in content

    def test_version_not_specified(self, tmp_path):
        from cli.steps.report import run_report

        config = make_config(tmp_path)
        results = {"validate": {"success": True, "duration": 0.1, "errors": [], "warnings": []}}
        result = run_report(config, results=results, release_version=None, dry_run=True)
        content = Path(result["report_path"]).read_text()
        assert "not specified" in content

    def test_report_file_created(self, tmp_path):
        from cli.steps.report import run_report

        config = make_config(tmp_path)
        results = {"validate": {"success": True, "duration": 0.1, "errors": [], "warnings": []}}
        result = run_report(config, results=results, dry_run=True)
        assert Path(result["report_path"]).exists()

    def test_duration_formatting(self, tmp_path):
        from cli.steps.report import run_report

        config = make_config(tmp_path)
        results = {"validate": {"success": True, "duration": 12.345, "errors": [], "warnings": []}}
        result = run_report(config, results=results, total_duration=99.9, dry_run=True)
        content = Path(result["report_path"]).read_text()
        assert "99.9s" in content

    def test_execute_mode_label(self, tmp_path):
        from cli.steps.report import run_report

        config = make_config(tmp_path)
        results = {"validate": {"success": True, "duration": 0.1, "errors": [], "warnings": []}}
        result = run_report(config, results=results, dry_run=False)
        content = Path(result["report_path"]).read_text()
        assert "EXECUTE" in content
        assert "DRY-RUN" not in content
