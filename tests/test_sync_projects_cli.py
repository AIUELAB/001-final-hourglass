#!/usr/bin/env python3
"""sync_projects/cli テスト"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sync_projects.cli import cli_sync_projects
from sync_projects.models import ParseResult, ProjectModel


class TestCliSyncProjects:
    """cli_sync_projectsのテスト"""

    def test_cli_sync_projects_success(self, tmp_path):
        """成功ケース"""
        # 入力ファイルを作成
        input_data = {"name": "CLI Test Project", "id": "cli-test"}
        input_path = tmp_path / "input.json"
        input_path.write_text(json.dumps(input_data), encoding="utf-8")

        out_dir = tmp_path / "output"

        runner = CliRunner()
        result = runner.invoke(
            cli_sync_projects,
            ["--input", str(input_path), "--out-dir", str(out_dir)],
        )

        assert result.exit_code == 0
        assert (out_dir / "cli-test__normalized.json").exists()
        assert (out_dir / "cli-test.md").exists()
        assert (out_dir / "cli-test__raw.json").exists()

    def test_cli_sync_projects_missing_input(self, tmp_path):
        """入力ファイル未指定"""
        out_dir = tmp_path / "output"

        runner = CliRunner()
        result = runner.invoke(
            cli_sync_projects,
            ["--out-dir", str(out_dir)],
        )

        assert result.exit_code != 0
        assert "Missing option '--input'" in result.output

    def test_cli_sync_projects_missing_output(self, tmp_path):
        """出力ディレクトリ未指定"""
        input_path = tmp_path / "input.json"
        input_path.write_text("{}", encoding="utf-8")

        runner = CliRunner()
        result = runner.invoke(
            cli_sync_projects,
            ["--input", str(input_path)],
        )

        assert result.exit_code != 0
        assert "Missing option '--out-dir'" in result.output

    def test_cli_sync_projects_input_not_found(self, tmp_path):
        """存在しない入力ファイル"""
        nonexistent = tmp_path / "nonexistent.json"
        out_dir = tmp_path / "output"

        runner = CliRunner()
        result = runner.invoke(
            cli_sync_projects,
            ["--input", str(nonexistent), "--out-dir", str(out_dir)],
        )

        assert result.exit_code != 0
        # Click は存在チェックでエラーを出す
        assert "does not exist" in result.output or "Error" in result.output

    @patch("sync_projects.cli.sync_from_json")
    def test_cli_sync_projects_sync_failure(self, mock_sync, tmp_path):
        """同期失敗ケース"""
        mock_sync.return_value = ParseResult(
            success=False,
            project=None,
            errors=["Sync failed"],
        )

        input_path = tmp_path / "input.json"
        input_path.write_text("{}", encoding="utf-8")
        out_dir = tmp_path / "output"

        runner = CliRunner()
        result = runner.invoke(
            cli_sync_projects,
            ["--input", str(input_path), "--out-dir", str(out_dir)],
        )

        assert result.exit_code != 0
        assert "同期に失敗しました" in result.output or "Error" in result.output

    @patch("sync_projects.cli.sync_from_json")
    def test_cli_sync_projects_exception(self, mock_sync, tmp_path):
        """例外発生ケース"""
        mock_sync.side_effect = RuntimeError("Unexpected error")

        input_path = tmp_path / "input.json"
        input_path.write_text("{}", encoding="utf-8")
        out_dir = tmp_path / "output"

        runner = CliRunner()
        result = runner.invoke(
            cli_sync_projects,
            ["--input", str(input_path), "--out-dir", str(out_dir)],
        )

        assert result.exit_code != 0
        assert "Unexpected error" in result.output

    def test_cli_sync_projects_with_items(self, tmp_path):
        """アイテム付きプロジェクトの同期"""
        input_data = {
            "name": "Project With Items",
            "id": "items-proj",
            "items": [
                {"id": "i1", "type": "note", "title": "Note 1", "content": "Content 1"},
            ],
        }
        input_path = tmp_path / "input.json"
        input_path.write_text(json.dumps(input_data), encoding="utf-8")

        out_dir = tmp_path / "output"

        runner = CliRunner()
        result = runner.invoke(
            cli_sync_projects,
            ["--input", str(input_path), "--out-dir", str(out_dir)],
        )

        assert result.exit_code == 0

        # 出力ファイルの内容を確認
        normalized_path = out_dir / "items-proj__normalized.json"
        normalized_content = json.loads(normalized_path.read_text(encoding="utf-8"))
        assert len(normalized_content["items"]) == 1
        assert normalized_content["items"][0]["id"] == "i1"

    def test_cli_sync_projects_with_resources(self, tmp_path):
        """リソース付きプロジェクトの同期"""
        input_data = {
            "name": "Project With Resources",
            "id": "res-proj",
            "resources": [
                {"id": "r1", "title": "Resource 1", "url": "https://example.com"},
            ],
        }
        input_path = tmp_path / "input.json"
        input_path.write_text(json.dumps(input_data), encoding="utf-8")

        out_dir = tmp_path / "output"

        runner = CliRunner()
        result = runner.invoke(
            cli_sync_projects,
            ["--input", str(input_path), "--out-dir", str(out_dir)],
        )

        assert result.exit_code == 0

        # Markdown に Resources セクションがあることを確認
        md_path = out_dir / "res-proj.md"
        md_content = md_path.read_text(encoding="utf-8")
        assert "## Resources" in md_content
