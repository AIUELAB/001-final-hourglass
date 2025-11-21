#!/usr/bin/env python3
"""sync_projects/models テスト"""

import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sync_projects.models import (
    ParseResult,
    ProjectItem,
    ProjectModel,
    ProjectResource,
    _slugify_name,
)


class TestProjectResource:
    """ProjectResourceのテスト"""

    def test_minimal(self):
        """最小構成"""
        resource = ProjectResource(id="res1")
        assert resource.id == "res1"
        assert resource.title is None
        assert resource.url is None

    def test_full(self):
        """フル構成"""
        resource = ProjectResource(
            id="res1", title="Test Resource", url="https://example.com", kind="document", metadata={"key": "value"}
        )
        assert resource.title == "Test Resource"
        assert str(resource.url) == "https://example.com/"


class TestProjectItem:
    """ProjectItemのテスト"""

    def test_minimal(self):
        """最小構成"""
        item = ProjectItem(id="item1", type="note")
        assert item.id == "item1"
        assert item.type == "note"
        assert item.tags == []

    def test_with_tags(self):
        """タグ付き"""
        item = ProjectItem(id="item1", type="task", tags=["urgent", "review"])
        assert len(item.tags) == 2


class TestProjectModel:
    """ProjectModelのテスト"""

    def test_minimal(self):
        """最小構成"""
        project = ProjectModel(id="proj1", name="Test Project")
        assert project.id == "proj1"
        assert project.name == "Test Project"
        assert project.items == []
        assert project.resources == []

    def test_with_items(self):
        """アイテム付き"""
        item = ProjectItem(id="item1", type="note")
        project = ProjectModel(id="proj1", name="Test", items=[item])
        assert len(project.items) == 1


class TestParseResult:
    """ParseResultのテスト"""

    def test_success(self):
        """成功結果"""
        result = ParseResult(success=True)
        assert result.success is True
        assert result.project is None
        assert result.warnings == []

    def test_failure(self):
        """失敗結果"""
        result = ParseResult(success=False, errors=["Error 1"])
        assert result.success is False
        assert len(result.errors) == 1


class TestSlugifyName:
    """_slugify_nameのテスト"""

    def test_empty(self):
        """空文字"""
        assert _slugify_name("") == ""

    def test_simple(self):
        """シンプルな名前"""
        result = _slugify_name("Test Project")
        assert result == "test-project"

    def test_with_spaces(self):
        """スペース付き"""
        result = _slugify_name("My  Project  Name")
        assert result == "my-project-name"

    def test_japanese(self):
        """日本語"""
        result = _slugify_name("テストプロジェクト")
        assert "テストプロジェクト" in result

    def test_special_chars(self):
        """特殊文字"""
        result = _slugify_name("Test@#$Project")
        assert "@" not in result
        assert "#" not in result


class TestExtractFunctions:
    """抽出関数のテスト"""

    def test_extract_name_with_name(self):
        """name属性あり"""
        from sync_projects.models import _extract_name

        result = _extract_name({"name": "Project Name"})
        assert result == "Project Name"

    def test_extract_name_with_title(self):
        """title属性あり"""
        from sync_projects.models import _extract_name

        result = _extract_name({"title": "Project Title"})
        assert result == "Project Title"

    def test_extract_name_fallback(self):
        """フォールバック"""
        from sync_projects.models import _extract_name

        result = _extract_name({})
        assert result == "Untitled Project"

    def test_extract_id_with_id(self):
        """id属性あり"""
        from sync_projects.models import _extract_id

        result = _extract_id({"id": "proj-123"}, "fallback")
        assert result == "proj-123"

    def test_extract_description(self):
        """description抽出"""
        from sync_projects.models import _extract_description

        result = _extract_description({"description": "Test desc"})
        assert result == "Test desc"

    def test_extract_description_none(self):
        """description なし"""
        from sync_projects.models import _extract_description

        result = _extract_description({})
        assert result is None
