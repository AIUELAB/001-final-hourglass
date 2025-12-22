#!/usr/bin/env python3
"""sync_projects/service テスト"""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sync_projects.models import ProjectItem, ProjectModel, ProjectResource
from sync_projects.models import ParseResult, coerce_to_project
from sync_projects.service import load_json, render_markdown, save_outputs, sync_from_json


class TestLoadJson:
    """load_jsonのテスト"""

    def test_load_valid_json(self):
        """有効なJSONの読み込み"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"key": "value"}, f)
            f.flush()
            result = load_json(Path(f.name))
            assert result == {"key": "value"}

    def test_load_nonexistent_file(self):
        """存在しないファイル"""
        with pytest.raises(FileNotFoundError):
            load_json(Path("/nonexistent/path.json"))

    def test_load_complex_json(self):
        """複雑なJSONの読み込み"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            data = {"items": [1, 2, 3], "nested": {"a": "b"}}
            json.dump(data, f)
            f.flush()
            result = load_json(Path(f.name))
            assert result["items"] == [1, 2, 3]
            assert result["nested"]["a"] == "b"


class TestRenderMarkdown:
    """render_markdownのテスト"""

    def test_minimal_project(self):
        """最小プロジェクト"""
        project = ProjectModel(id="p1", name="Test Project")
        md = render_markdown(project)
        assert "# Test Project" in md
        assert "## Items" in md

    def test_with_description(self):
        """説明付きプロジェクト"""
        project = ProjectModel(id="p1", name="Test", description="Project description")
        md = render_markdown(project)
        assert "Project description" in md

    def test_with_items(self):
        """アイテム付きプロジェクト"""
        item = ProjectItem(id="i1", type="note", title="Test Note")
        project = ProjectModel(id="p1", name="Test", items=[item])
        md = render_markdown(project)
        assert "[note] Test Note" in md

    def test_with_resources(self):
        """リソース付きプロジェクト"""
        resource = ProjectResource(id="r1", title="Resource 1", url="https://example.com")
        project = ProjectModel(id="p1", name="Test", resources=[resource])
        md = render_markdown(project)
        assert "## Resources" in md
        assert "Resource 1" in md


class TestSaveOutputs:
    """save_outputsのテスト"""

    def test_save_outputs_creates_files(self, tmp_path):
        """ファイルが作成される"""
        project = ProjectModel(
            id="test-project",
            name="Test Project",
            description="Description",
            raw={"original": "data"},
        )
        normalized_path, markdown_path, raw_path = save_outputs(project, tmp_path)

        assert normalized_path.exists()
        assert markdown_path.exists()
        assert raw_path.exists()
        assert normalized_path.name == "test-project__normalized.json"
        assert markdown_path.name == "test-project.md"
        assert raw_path.name == "test-project__raw.json"

    def test_save_outputs_creates_directory(self, tmp_path):
        """出力ディレクトリが自動作成される"""
        nested_dir = tmp_path / "nested" / "output"
        project = ProjectModel(id="p1", name="Test", raw={})

        normalized_path, markdown_path, raw_path = save_outputs(project, nested_dir)

        assert nested_dir.exists()
        assert normalized_path.exists()

    def test_save_outputs_content(self, tmp_path):
        """ファイル内容が正しい"""
        project = ProjectModel(
            id="content-test",
            name="Content Test Project",
            description="Test description",
            raw={"key": "value"},
        )
        normalized_path, markdown_path, raw_path = save_outputs(project, tmp_path)

        # Normalized JSON の確認
        normalized_content = json.loads(normalized_path.read_text(encoding="utf-8"))
        assert normalized_content["id"] == "content-test"
        assert normalized_content["name"] == "Content Test Project"

        # Markdown の確認
        md_content = markdown_path.read_text(encoding="utf-8")
        assert "# Content Test Project" in md_content

        # Raw JSON の確認
        raw_content = json.loads(raw_path.read_text(encoding="utf-8"))
        assert raw_content["key"] == "value"

    def test_save_outputs_with_items(self, tmp_path):
        """アイテム付きプロジェクトの保存"""
        item = ProjectItem(id="i1", type="note", title="Note 1")
        project = ProjectModel(id="p1", name="With Items", items=[item], raw={})

        normalized_path, markdown_path, raw_path = save_outputs(project, tmp_path)

        normalized_content = json.loads(normalized_path.read_text(encoding="utf-8"))
        assert len(normalized_content["items"]) == 1
        assert normalized_content["items"][0]["id"] == "i1"


class TestSyncFromJson:
    """sync_from_jsonのテスト"""

    @patch("sync_projects.service.console")
    def test_sync_from_json_success(self, mock_console, tmp_path):
        """成功ケース"""
        # 入力 JSON を作成
        input_data = {"name": "Test Project", "id": "test-123"}
        input_path = tmp_path / "input.json"
        input_path.write_text(json.dumps(input_data), encoding="utf-8")

        out_dir = tmp_path / "output"
        result = sync_from_json(input_path, out_dir)

        assert result.success is True
        assert result.project is not None
        assert result.project.name == "Test Project"
        assert (out_dir / "test-123__normalized.json").exists()
        assert (out_dir / "test-123.md").exists()
        assert (out_dir / "test-123__raw.json").exists()

    @patch("sync_projects.service.console")
    def test_sync_from_json_with_warnings(self, mock_console, tmp_path):
        """警告ありのケース"""
        # items に invalid な項目を含める
        input_data = {
            "name": "Warning Project",
            "id": "warn-proj",
            "items": [
                {"id": "i1", "type": "note", "title": "Valid Note"},
                {},  # 無効な項目
            ],
        }
        input_path = tmp_path / "input.json"
        input_path.write_text(json.dumps(input_data), encoding="utf-8")

        out_dir = tmp_path / "output"
        result = sync_from_json(input_path, out_dir)

        assert result.success is True
        # warnings は coerce_to_project の実装による

    @patch("sync_projects.service.console")
    @patch("sync_projects.service.coerce_to_project")
    def test_sync_from_json_parse_failure(self, mock_coerce, mock_console, tmp_path):
        """パース失敗ケース"""
        mock_coerce.return_value = ParseResult(
            success=False,
            project=None,
            errors=["Parse error occurred"],
        )

        input_data = {"invalid": "data"}
        input_path = tmp_path / "input.json"
        input_path.write_text(json.dumps(input_data), encoding="utf-8")

        out_dir = tmp_path / "output"
        result = sync_from_json(input_path, out_dir)

        assert result.success is False
        assert result.project is None
        assert "Parse error occurred" in result.errors

    @patch("sync_projects.service.console")
    def test_sync_from_json_file_not_found(self, mock_console, tmp_path):
        """存在しないファイル"""
        nonexistent = tmp_path / "nonexistent.json"
        out_dir = tmp_path / "output"

        with pytest.raises(FileNotFoundError):
            sync_from_json(nonexistent, out_dir)
