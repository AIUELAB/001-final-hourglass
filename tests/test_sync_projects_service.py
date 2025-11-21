#!/usr/bin/env python3
"""sync_projects/service テスト"""

import json
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sync_projects.models import ProjectItem, ProjectModel, ProjectResource
from sync_projects.service import load_json, render_markdown


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
