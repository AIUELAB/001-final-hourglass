"""Comprehensive unit tests for iOS Release CLI Phase 2 modules.

Covers:
- cli.steps.version (run_version)
- cli.steps.export_ipa (run_export)
- cli.steps.upload (run_upload)
- cli.utils.xcodebuild (run_xcodebuild, XcodebuildResult)
- cli.utils.plistbuddy (plist_read, plist_set, plist_add, plist_clear, validate_plist)
"""

# pyright: reportPrivateUsage=false, reportOperatorIssue=false
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cli.config import ReleaseConfig

# ---------------------------------------------------------------------------
# Fixtures & Helpers
# ---------------------------------------------------------------------------

SAMPLE_PBXPROJ = """\
// !$*UTF8*$!
{
	buildSettings = {
		MARKETING_VERSION = 1.0.10;
		CURRENT_PROJECT_VERSION = 5;
		PRODUCT_BUNDLE_IDENTIFIER = com.AIUELAB.FinalHourglass;
	};
	buildSettings = {
		MARKETING_VERSION = 1.0.10;
		CURRENT_PROJECT_VERSION = 5;
	};
}
"""

PBXPROJ_NO_MARKETING = """\
// !$*UTF8*$!
{
	buildSettings = {
		CURRENT_PROJECT_VERSION = 5;
	};
}
"""


def make_config(tmp_path: Path, *, p8_exists: bool = True) -> ReleaseConfig:
    """Build a ReleaseConfig with test values."""
    if p8_exists:
        key_file = tmp_path / "AuthKey_TEST.p8"
        key_file.write_text("-----BEGIN EC PRIVATE KEY-----\ntest\n-----END EC PRIVATE KEY-----\n")
        key_path = str(key_file)
    else:
        key_path = str(tmp_path / "missing.p8")

    return ReleaseConfig(
        api_key_id="TESTKEY123",
        api_issuer_id="test-issuer-uuid",
        api_key_path=key_path,
        team_id="N4UHXSGNLU",
        bundle_id="com.AIUELAB.FinalHourglass",
        project_root=tmp_path,
    )


def make_config_no_credentials(tmp_path: Path) -> ReleaseConfig:
    """Build a ReleaseConfig with missing credentials."""
    return ReleaseConfig(
        api_key_id="",
        api_issuer_id="",
        api_key_path="",
        team_id="N4UHXSGNLU",
        bundle_id="com.AIUELAB.FinalHourglass",
        project_root=tmp_path,
    )


def _setup_pbxproj(tmp_path: Path, content: str = SAMPLE_PBXPROJ) -> Path:
    """Create a fake pbxproj file and return the project root."""
    xcodeproj = tmp_path / "FinalHourglass.xcodeproj"
    xcodeproj.mkdir()
    pbxproj = xcodeproj / "project.pbxproj"
    pbxproj.write_text(content, encoding="utf-8")
    return tmp_path


# ============================================================================
# Tests for cli.steps.version
# ============================================================================


class TestRunVersion:
    """Tests for run_version."""

    # -- release_version not specified → failure ----------------------------

    def test_no_version_specified(self, tmp_path):
        from cli.steps.version import run_version

        config = make_config(tmp_path)
        result = run_version(config, release_version=None, dry_run=True)

        assert result["success"] is False
        assert "No --version specified" in result["error"]

    # -- pbxproj not found → failure ----------------------------------------

    def test_pbxproj_not_found(self, tmp_path):
        from cli.steps.version import run_version

        config = make_config(tmp_path)
        # Don't create xcodeproj directory
        result = run_version(config, release_version="2.0.0", dry_run=True)

        assert result["success"] is False
        assert "project.pbxproj not found" in result["error"]

    # -- OSError reading pbxproj → failure ----------------------------------

    def test_read_oserror(self, tmp_path):
        from cli.steps.version import run_version

        _setup_pbxproj(tmp_path)
        config = make_config(tmp_path)

        with patch.object(Path, "read_text", side_effect=OSError("Permission denied")):
            result = run_version(config, release_version="2.0.0", dry_run=True)

        assert result["success"] is False
        assert "Cannot read pbxproj" in result["error"]

    # -- MARKETING_VERSION not found → failure ------------------------------

    def test_marketing_version_not_found(self, tmp_path):
        from cli.steps.version import run_version

        _setup_pbxproj(tmp_path, content=PBXPROJ_NO_MARKETING)
        config = make_config(tmp_path)

        result = run_version(config, release_version="2.0.0", dry_run=True)

        assert result["success"] is False
        assert "MARKETING_VERSION not found" in result["error"]

    # -- dry_run: auto-increment build number -------------------------------

    def test_dry_run_auto_increment_build(self, tmp_path):
        from cli.steps.version import run_version

        _setup_pbxproj(tmp_path)
        config = make_config(tmp_path)

        result = run_version(config, release_version="2.0.0", build_number=None, dry_run=True)

        assert result["success"] is True
        assert result["dry_run"] is True
        assert result["current_version"] == "1.0.10"
        assert result["new_version"] == "2.0.0"
        assert result["current_build"] == "5"
        assert result["new_build"] == "6"  # auto-incremented

    # -- dry_run: explicit build_number used --------------------------------

    def test_dry_run_explicit_build_number(self, tmp_path):
        from cli.steps.version import run_version

        _setup_pbxproj(tmp_path)
        config = make_config(tmp_path)

        result = run_version(config, release_version="2.0.0", build_number="99", dry_run=True)

        assert result["success"] is True
        assert result["dry_run"] is True
        assert result["new_build"] == "99"

    # -- execute: writes changes to pbxproj ---------------------------------

    def test_execute_writes_changes(self, tmp_path):
        from cli.steps.version import run_version

        _setup_pbxproj(tmp_path)
        config = make_config(tmp_path)

        result = run_version(config, release_version="2.0.0", build_number="10", dry_run=False)

        assert result["success"] is True
        assert result["dry_run"] is False
        assert result["new_version"] == "2.0.0"
        assert result["new_build"] == "10"

        # Verify file was actually updated
        pbxproj = tmp_path / "FinalHourglass.xcodeproj" / "project.pbxproj"
        content = pbxproj.read_text(encoding="utf-8")
        assert "MARKETING_VERSION = 2.0.0;" in content
        assert "CURRENT_PROJECT_VERSION = 10;" in content
        # Original values should be gone
        assert "MARKETING_VERSION = 1.0.10;" not in content

    # -- execute: write OSError → failure -----------------------------------

    def test_execute_write_oserror(self, tmp_path):
        from cli.steps.version import run_version

        _setup_pbxproj(tmp_path)
        config = make_config(tmp_path)

        with patch.object(Path, "write_text", side_effect=OSError("Disk full")):
            result = run_version(config, release_version="2.0.0", build_number="10", dry_run=False)

        assert result["success"] is False
        assert "Failed to write pbxproj" in result["error"]

    # -- execute: multiple MARKETING_VERSION entries replaced ---------------

    def test_execute_multiple_entries_replaced(self, tmp_path):
        from cli.steps.version import run_version

        _setup_pbxproj(tmp_path)
        config = make_config(tmp_path)

        result = run_version(config, release_version="3.0.0", build_number="20", dry_run=False)

        assert result["success"] is True
        assert result["version_replacements"] == 2  # Two MARKETING_VERSION entries
        assert result["build_replacements"] == 2  # Two CURRENT_PROJECT_VERSION entries

        content = (tmp_path / "FinalHourglass.xcodeproj" / "project.pbxproj").read_text()
        assert content.count("MARKETING_VERSION = 3.0.0;") == 2

    # -- empty string release_version → failure ----------------------------

    def test_empty_string_version(self, tmp_path):
        from cli.steps.version import run_version

        config = make_config(tmp_path)
        result = run_version(config, release_version="", dry_run=True)

        assert result["success"] is False
        assert "No --version specified" in result["error"]


# ============================================================================
# Tests for cli.steps.export_ipa
# ============================================================================


class TestRunExport:
    """Tests for run_export."""

    # -- ExportOptions not found → failure ----------------------------------

    def test_export_options_not_found(self, tmp_path):
        from cli.steps.export_ipa import run_export

        config = make_config(tmp_path)
        # No ExportOptions.plist created
        with patch("cli.steps.export_ipa.validate_plist", return_value=(True, "")):
            result = run_export(config, dry_run=True)

        assert result["success"] is False
        assert "ExportOptions.plist not found" in result["error"]

    # -- ExportOptions invalid (validate_plist fails) → failure -------------

    def test_export_options_invalid(self, tmp_path):
        from cli.steps.export_ipa import run_export

        config = make_config(tmp_path)
        export_options = tmp_path / "ExportOptions.plist"
        export_options.write_text("<plist></plist>")

        with patch("cli.steps.export_ipa.validate_plist", return_value=(False, "malformed plist")):
            result = run_export(config, dry_run=True)

        assert result["success"] is False
        assert "ExportOptions.plist is invalid" in result["error"]
        assert "malformed plist" in result["error"]

    # -- dry_run success with valid ExportOptions ---------------------------

    def test_dry_run_success(self, tmp_path):
        from cli.steps.export_ipa import run_export

        config = make_config(tmp_path)
        export_options = tmp_path / "ExportOptions.plist"
        export_options.write_text("<plist></plist>")

        with patch("cli.steps.export_ipa.validate_plist", return_value=(True, "")):
            result = run_export(config, dry_run=True)

        assert result["success"] is True
        assert result["dry_run"] is True
        assert str(export_options) in result["export_options"]

    # -- execute: no archive_path → failure ---------------------------------

    def test_execute_no_archive_path(self, tmp_path):
        from cli.steps.export_ipa import run_export

        config = make_config(tmp_path)
        export_options = tmp_path / "ExportOptions.plist"
        export_options.write_text("<plist></plist>")

        with patch("cli.steps.export_ipa.validate_plist", return_value=(True, "")):
            result = run_export(config, archive_path="", dry_run=False)

        assert result["success"] is False
        assert "No archive path provided" in result["error"]

    # -- execute: archive not found → failure -------------------------------

    def test_execute_archive_not_found(self, tmp_path):
        from cli.steps.export_ipa import run_export

        config = make_config(tmp_path)
        export_options = tmp_path / "ExportOptions.plist"
        export_options.write_text("<plist></plist>")

        with patch("cli.steps.export_ipa.validate_plist", return_value=(True, "")):
            result = run_export(
                config,
                archive_path=str(tmp_path / "nonexistent.xcarchive"),
                dry_run=False,
            )

        assert result["success"] is False
        assert "Archive not found" in result["error"]

    # -- execute: _inject_application_properties fails → failure ------------

    def test_execute_inject_fails(self, tmp_path):
        from cli.steps.export_ipa import run_export

        config = make_config(tmp_path)
        export_options = tmp_path / "ExportOptions.plist"
        export_options.write_text("<plist></plist>")

        archive = tmp_path / "App.xcarchive"
        archive.mkdir()

        with patch("cli.steps.export_ipa.validate_plist", return_value=(True, "")):
            with patch("cli.steps.export_ipa._inject_application_properties", return_value=False):
                result = run_export(
                    config,
                    archive_path=str(archive),
                    dry_run=False,
                )

        assert result["success"] is False
        assert "Failed to inject ApplicationProperties" in result["error"]

    # -- export_options_override used correctly -----------------------------

    def test_export_options_override(self, tmp_path):
        from cli.steps.export_ipa import run_export

        config = make_config(tmp_path)
        # Default ExportOptions.plist does NOT exist
        custom_options = tmp_path / "custom" / "Export.plist"
        custom_options.parent.mkdir()
        custom_options.write_text("<plist></plist>")

        with patch("cli.steps.export_ipa.validate_plist", return_value=(True, "")):
            result = run_export(
                config,
                export_options_override=str(custom_options),
                dry_run=True,
            )

        assert result["success"] is True
        assert result["dry_run"] is True
        assert str(custom_options) in result["export_options"]

    # -- export_options_override not found → failure ------------------------

    def test_export_options_override_not_found(self, tmp_path):
        from cli.steps.export_ipa import run_export

        config = make_config(tmp_path)

        with patch("cli.steps.export_ipa.validate_plist", return_value=(True, "")):
            result = run_export(
                config,
                export_options_override=str(tmp_path / "nonexistent.plist"),
                dry_run=True,
            )

        assert result["success"] is False
        assert "ExportOptions.plist not found" in result["error"]


# ============================================================================
# Tests for cli.steps.upload
# ============================================================================


class TestRunUpload:
    """Tests for run_upload."""

    # -- dry_run: credentials OK → success ----------------------------------

    def test_dry_run_credentials_ok(self, tmp_path):
        from cli.steps.upload import run_upload

        config = make_config(tmp_path)
        result = run_upload(config, dry_run=True)

        assert result["success"] is True
        assert result["dry_run"] is True

    # -- dry_run: missing credentials → failure -----------------------------

    def test_dry_run_missing_credentials(self, tmp_path):
        from cli.steps.upload import run_upload

        config = make_config_no_credentials(tmp_path)
        result = run_upload(config, dry_run=True)

        assert result["success"] is False
        assert "Credential validation failed" in result["error"]
        assert result["dry_run"] is True

    # -- execute: missing credentials → failure -----------------------------

    def test_execute_missing_credentials(self, tmp_path):
        from cli.steps.upload import run_upload

        config = make_config_no_credentials(tmp_path)
        result = run_upload(config, ipa_path="/some/app.ipa", dry_run=False)

        assert result["success"] is False
        assert "API_KEY_ID" in result["error"] or "not configured" in result["error"]

    # -- execute: no ipa_path → failure -------------------------------------

    def test_execute_no_ipa_path(self, tmp_path):
        from cli.steps.upload import run_upload

        config = make_config(tmp_path)
        result = run_upload(config, ipa_path="", dry_run=False)

        assert result["success"] is False
        assert "No IPA path provided" in result["error"]

    # -- execute: ipa_file not found → failure ------------------------------

    def test_execute_ipa_not_found(self, tmp_path):
        from cli.steps.upload import run_upload

        config = make_config(tmp_path)
        result = run_upload(config, ipa_path=str(tmp_path / "missing.ipa"), dry_run=False)

        assert result["success"] is False
        assert "IPA file not found" in result["error"]

    # -- execute: altool success (mock subprocess.run) ----------------------

    def test_execute_altool_success(self, tmp_path):
        from cli.steps.upload import run_upload

        config = make_config(tmp_path)
        ipa = tmp_path / "App.ipa"
        ipa.write_text("fake ipa")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Upload successful"
        mock_result.stderr = ""

        with patch("cli.steps.upload.subprocess.run", return_value=mock_result):
            result = run_upload(config, ipa_path=str(ipa), dry_run=False)

        assert result["success"] is True
        assert result["dry_run"] is False
        assert str(ipa) in result["ipa_path"]

    # -- execute: altool failure (non-zero returncode) ----------------------

    def test_execute_altool_failure(self, tmp_path):
        from cli.steps.upload import run_upload

        config = make_config(tmp_path)
        ipa = tmp_path / "App.ipa"
        ipa.write_text("fake ipa")

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Authentication failed"

        with patch("cli.steps.upload.subprocess.run", return_value=mock_result):
            result = run_upload(config, ipa_path=str(ipa), dry_run=False)

        assert result["success"] is False
        assert "altool upload failed" in result["error"]

    # -- execute: altool timeout (TimeoutExpired) ---------------------------

    def test_execute_altool_timeout(self, tmp_path):
        from cli.steps.upload import run_upload

        config = make_config(tmp_path)
        ipa = tmp_path / "App.ipa"
        ipa.write_text("fake ipa")

        with patch("cli.steps.upload.subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="xcrun", timeout=600)):
            result = run_upload(config, ipa_path=str(ipa), dry_run=False)

        assert result["success"] is False
        assert "timed out" in result["error"]

    # -- execute: xcrun not found (FileNotFoundError) -----------------------

    def test_execute_xcrun_not_found(self, tmp_path):
        from cli.steps.upload import run_upload

        config = make_config(tmp_path)
        ipa = tmp_path / "App.ipa"
        ipa.write_text("fake ipa")

        with patch("cli.steps.upload.subprocess.run", side_effect=FileNotFoundError("xcrun")):
            result = run_upload(config, ipa_path=str(ipa), dry_run=False)

        assert result["success"] is False
        assert "xcrun not found" in result["error"]


# ============================================================================
# Tests for cli.utils.xcodebuild
# ============================================================================


class TestRunXcodebuild:
    """Tests for run_xcodebuild."""

    # -- stream_output=True: success (mock Popen) ---------------------------

    def test_stream_output_success(self):
        from cli.utils.xcodebuild import run_xcodebuild

        mock_process = MagicMock()
        mock_process.stdout = iter(["Build Succeeded\n", "line2\n"])
        mock_process.stderr = MagicMock()
        mock_process.stderr.read.return_value = ""
        mock_process.returncode = 0
        mock_process.wait.return_value = None

        with patch("cli.utils.xcodebuild.subprocess.Popen", return_value=mock_process):
            result = run_xcodebuild(["-version"], stream_output=True)

        assert result.success is True
        assert result.return_code == 0
        assert "Build Succeeded" in result.stdout

    # -- stream_output=False: success (mock subprocess.run) -----------------

    def test_no_stream_success(self):
        from cli.utils.xcodebuild import run_xcodebuild

        mock_completed = MagicMock()
        mock_completed.stdout = "Build ok"
        mock_completed.stderr = ""
        mock_completed.returncode = 0

        with patch("cli.utils.xcodebuild.subprocess.run", return_value=mock_completed):
            result = run_xcodebuild(["-version"], stream_output=False)

        assert result.success is True
        assert result.return_code == 0
        assert result.stdout == "Build ok"

    # -- TimeoutExpired → kills process, returns failure --------------------

    def test_timeout_kills_process(self):
        from cli.utils.xcodebuild import run_xcodebuild

        mock_process = MagicMock()
        mock_process.stdout = iter([])
        mock_process.wait.side_effect = subprocess.TimeoutExpired(cmd="xcodebuild", timeout=5)
        mock_process.kill.return_value = None
        mock_process.communicate.return_value = ("", "")

        with patch("cli.utils.xcodebuild.subprocess.Popen", return_value=mock_process):
            result = run_xcodebuild(["-version"], stream_output=True, timeout=5)

        assert result.success is False
        assert result.return_code == -1
        assert "timed out" in result.stderr
        mock_process.kill.assert_called_once()

    # -- FileNotFoundError → "xcodebuild not found" message -----------------

    def test_file_not_found(self):
        from cli.utils.xcodebuild import run_xcodebuild

        with patch("cli.utils.xcodebuild.subprocess.Popen", side_effect=FileNotFoundError("xcodebuild")):
            result = run_xcodebuild(["-version"], stream_output=True)

        assert result.success is False
        assert result.return_code == -1
        assert "xcodebuild not found" in result.stderr

    # -- General OSError → "OS error running xcodebuild" message ------------

    def test_general_oserror(self):
        from cli.utils.xcodebuild import run_xcodebuild

        with patch("cli.utils.xcodebuild.subprocess.Popen", side_effect=OSError("Resource busy")):
            result = run_xcodebuild(["-version"], stream_output=True)

        assert result.success is False
        assert result.return_code == -1
        assert "OS error running xcodebuild" in result.stderr


# ============================================================================
# Tests for cli.utils.plistbuddy
# ============================================================================


class TestPlistBuddy:
    """Tests for plistbuddy utility functions."""

    # -- plist_read: success returns stripped output -------------------------

    def test_plist_read_success(self):
        from cli.utils.plistbuddy import plist_read

        mock_result = MagicMock()
        mock_result.stdout = "  1.0.10  \n"

        with patch("cli.utils.plistbuddy.subprocess.run", return_value=mock_result) as mock_run:
            value = plist_read(Path("/tmp/Info.plist"), ":CFBundleVersion")

        assert value == "1.0.10"
        mock_run.assert_called_once_with(
            ["/usr/libexec/PlistBuddy", "-c", "Print :CFBundleVersion", "/tmp/Info.plist"],
            capture_output=True,
            text=True,
            check=True,
        )

    # -- plist_read: CalledProcessError raised on failure --------------------

    def test_plist_read_failure(self):
        from cli.utils.plistbuddy import plist_read

        with patch(
            "cli.utils.plistbuddy.subprocess.run",
            side_effect=subprocess.CalledProcessError(1, "PlistBuddy"),
        ):
            with pytest.raises(subprocess.CalledProcessError):
                plist_read(Path("/tmp/Info.plist"), ":MissingKey")

    # -- plist_set: calls correct command -----------------------------------

    def test_plist_set_calls_correct_command(self):
        from cli.utils.plistbuddy import plist_set

        with patch("cli.utils.plistbuddy.subprocess.run") as mock_run:
            plist_set(Path("/tmp/Info.plist"), ":CFBundleVersion", "42")

        mock_run.assert_called_once_with(
            ["/usr/libexec/PlistBuddy", "-c", 'Set :CFBundleVersion "42"', "/tmp/Info.plist"],
            capture_output=True,
            text=True,
            check=True,
        )

    # -- plist_add: with value ----------------------------------------------

    def test_plist_add_with_value(self):
        from cli.utils.plistbuddy import plist_add

        with patch("cli.utils.plistbuddy.subprocess.run") as mock_run:
            plist_add(Path("/tmp/Info.plist"), ":AppPath", "string", "Applications/App.app")

        mock_run.assert_called_once_with(
            ["/usr/libexec/PlistBuddy", "-c", 'Add :AppPath string "Applications/App.app"', "/tmp/Info.plist"],
            capture_output=True,
            text=True,
            check=True,
        )

    # -- plist_add: without value (dict type) -------------------------------

    def test_plist_add_without_value(self):
        from cli.utils.plistbuddy import plist_add

        with patch("cli.utils.plistbuddy.subprocess.run") as mock_run:
            plist_add(Path("/tmp/Info.plist"), ":ApplicationProperties", "dict")

        mock_run.assert_called_once_with(
            ["/usr/libexec/PlistBuddy", "-c", "Add :ApplicationProperties dict", "/tmp/Info.plist"],
            capture_output=True,
            text=True,
            check=True,
        )

    # -- plist_clear: calls correct command ---------------------------------

    def test_plist_clear(self):
        from cli.utils.plistbuddy import plist_clear

        with patch("cli.utils.plistbuddy.subprocess.run") as mock_run:
            plist_clear(Path("/tmp/Info.plist"))

        mock_run.assert_called_once_with(
            ["/usr/libexec/PlistBuddy", "-c", "Clear dict", "/tmp/Info.plist"],
            capture_output=True,
            text=True,
            check=True,
        )

    # -- validate_plist: success returns (True, "") -------------------------

    def test_validate_plist_success(self):
        from cli.utils.plistbuddy import validate_plist

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "OK"
        mock_result.stderr = ""

        with patch("cli.utils.plistbuddy.subprocess.run", return_value=mock_result):
            valid, error = validate_plist(Path("/tmp/Info.plist"))

        assert valid is True
        assert error == ""

    # -- validate_plist: failure returns (False, error_detail) ---------------

    def test_validate_plist_failure(self):
        from cli.utils.plistbuddy import validate_plist

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "Info.plist: Unexpected character at line 3"
        mock_result.stderr = ""

        with patch("cli.utils.plistbuddy.subprocess.run", return_value=mock_result):
            valid, error = validate_plist(Path("/tmp/Info.plist"))

        assert valid is False
        assert "Unexpected character" in error
