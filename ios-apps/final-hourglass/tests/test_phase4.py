"""Tests for Phase 4: CI/CD integration (GitHub Actions × iOS Release CLI)."""

from __future__ import annotations

import os
from unittest.mock import patch

from cli.utils.ci import annotate, is_ci, write_output, write_step_summary


# ============================================================
# ci.py tests
# ============================================================


class TestIsCi:
    """Tests for is_ci() detection."""

    def test_returns_true_when_github_actions_set(self):
        with patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}):
            assert is_ci() is True

    def test_returns_false_when_not_set(self):
        env = os.environ.copy()
        env.pop("GITHUB_ACTIONS", None)
        with patch.dict(os.environ, env, clear=True):
            assert is_ci() is False

    def test_returns_false_for_non_true_value(self):
        with patch.dict(os.environ, {"GITHUB_ACTIONS": "false"}):
            assert is_ci() is False


class TestWriteOutput:
    """Tests for write_output() GitHub Actions output."""

    def test_writes_key_value_to_file(self, tmp_path):
        output_file = tmp_path / "github_output"
        output_file.touch()
        with patch.dict(os.environ, {"GITHUB_OUTPUT": str(output_file)}):
            write_output("archive_path", "/tmp/build/FinalHourglass.xcarchive")
        content = output_file.read_text()
        assert "archive_path=/tmp/build/FinalHourglass.xcarchive\n" in content

    def test_appends_multiple_outputs(self, tmp_path):
        output_file = tmp_path / "github_output"
        output_file.touch()
        with patch.dict(os.environ, {"GITHUB_OUTPUT": str(output_file)}):
            write_output("key1", "value1")
            write_output("key2", "value2")
        content = output_file.read_text()
        assert "key1=value1\n" in content
        assert "key2=value2\n" in content

    def test_noop_when_github_output_not_set(self):
        env = os.environ.copy()
        env.pop("GITHUB_OUTPUT", None)
        with patch.dict(os.environ, env, clear=True):
            # Should not raise
            write_output("key", "value")


class TestAnnotate:
    """Tests for annotate() GitHub Actions annotations."""

    def test_error_annotation(self, capsys):
        annotate("error", "Build failed")
        captured = capsys.readouterr()
        assert captured.out == "::error::Build failed\n"

    def test_warning_annotation(self, capsys):
        annotate("warning", "Deprecated API")
        captured = capsys.readouterr()
        assert captured.out == "::warning::Deprecated API\n"

    def test_notice_annotation(self, capsys):
        annotate("notice", "Build succeeded")
        captured = capsys.readouterr()
        assert captured.out == "::notice::Build succeeded\n"

    def test_invalid_level_defaults_to_notice(self, capsys):
        annotate("debug", "Some message")
        captured = capsys.readouterr()
        assert captured.out == "::notice::Some message\n"


class TestWriteStepSummary:
    """Tests for write_step_summary()."""

    def test_writes_markdown_to_summary_file(self, tmp_path):
        summary_file = tmp_path / "step_summary"
        summary_file.touch()
        with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(summary_file)}):
            write_step_summary("## Build Results\n| Step | Status |\n|---|---|\n| archive | OK |")
        content = summary_file.read_text()
        assert "## Build Results" in content

    def test_noop_when_summary_not_set(self):
        env = os.environ.copy()
        env.pop("GITHUB_STEP_SUMMARY", None)
        with patch.dict(os.environ, env, clear=True):
            write_step_summary("content")


# ============================================================
# CLI option integration tests
# ============================================================


class TestExportOptionsOverride:
    """Tests for --export-options-plist override propagation."""

    def test_override_path_used_in_run_export(self, tmp_path):
        """Verify export_options_override overrides config.export_options_path."""
        from cli.config import ReleaseConfig

        config = ReleaseConfig(
            project_root=tmp_path,
            team_id="N4UHXSGNLU",
            bundle_id="com.AIUELAB.FinalHourglass",
        )

        # Create a custom ExportOptions.plist
        custom_plist = tmp_path / "Custom.plist"
        custom_plist.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
            '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
            '<plist version="1.0"><dict>'
            "<key>method</key><string>app-store-connect</string>"
            "</dict></plist>"
        )

        from cli.steps.export_ipa import run_export

        result = run_export(
            config,
            export_options_override=str(custom_plist),
            dry_run=True,
        )
        assert result["success"] is True
        assert str(custom_plist) in str(result.get("export_options", ""))


class TestBuildNumberOption:
    """Tests for --build-number propagation."""

    def test_build_number_passed_to_version_step(self, tmp_path):
        """Verify build_number from CLI is used in run_version."""
        from cli.config import ReleaseConfig

        config = ReleaseConfig(project_root=tmp_path)

        # Create a minimal pbxproj
        xcodeproj = tmp_path / "FinalHourglass.xcodeproj"
        xcodeproj.mkdir()
        pbxproj = xcodeproj / "project.pbxproj"
        pbxproj.write_text("MARKETING_VERSION = 1.0.10;\n" "CURRENT_PROJECT_VERSION = 1;\n")

        from cli.steps.version import run_version

        result = run_version(
            config,
            release_version="1.0.11",
            build_number="42",
            dry_run=True,
        )
        assert result["success"] is True
        assert result["new_build"] == "42"


class TestCiModeFlag:
    """Tests for --ci flag behavior."""

    def testemit_ci_outputs_version(self, tmp_path):
        """Verify emit_ci_outputs writes version outputs."""
        from cli.ios_release import emit_ci_outputs

        output_file = tmp_path / "github_output"
        output_file.touch()

        with patch.dict(os.environ, {"GITHUB_OUTPUT": str(output_file)}):
            emit_ci_outputs("version", {"new_version": "1.0.11", "new_build": "42"})

        content = output_file.read_text()
        assert "new_version=1.0.11" in content
        assert "new_build=42" in content

    def testemit_ci_outputs_archive(self, tmp_path):
        """Verify emit_ci_outputs writes archive path."""
        from cli.ios_release import emit_ci_outputs

        output_file = tmp_path / "github_output"
        output_file.touch()

        with patch.dict(os.environ, {"GITHUB_OUTPUT": str(output_file)}):
            emit_ci_outputs("archive", {"archive_path": "/tmp/FH.xcarchive"})

        content = output_file.read_text()
        assert "archive_path=/tmp/FH.xcarchive" in content

    def testemit_ci_outputs_export(self, tmp_path):
        """Verify emit_ci_outputs writes IPA path."""
        from cli.ios_release import emit_ci_outputs

        output_file = tmp_path / "github_output"
        output_file.touch()

        with patch.dict(os.environ, {"GITHUB_OUTPUT": str(output_file)}):
            emit_ci_outputs("export", {"ipa_path": "/tmp/Export/FH.ipa", "export_dir": "/tmp/Export"})

        content = output_file.read_text()
        assert "ipa_path=/tmp/Export/FH.ipa" in content
        assert "export_dir=/tmp/Export" in content

    def testemit_ci_outputs_unknown_step_no_error(self, tmp_path):
        """Unknown steps should not cause errors."""
        from cli.ios_release import emit_ci_outputs

        output_file = tmp_path / "github_output"
        output_file.touch()

        with patch.dict(os.environ, {"GITHUB_OUTPUT": str(output_file)}):
            emit_ci_outputs("report", {"report_path": "/tmp/report.md"})

        content = output_file.read_text()
        assert content == ""  # report is not in output_map

    def testemit_ci_outputs_skips_none_values(self, tmp_path):
        """None values should not be written."""
        from cli.ios_release import emit_ci_outputs

        output_file = tmp_path / "github_output"
        output_file.touch()

        with patch.dict(os.environ, {"GITHUB_OUTPUT": str(output_file)}):
            emit_ci_outputs("archive", {"archive_path": None})

        content = output_file.read_text()
        assert content == ""
