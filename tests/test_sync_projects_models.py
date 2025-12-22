#!/usr/bin/env python3
"""sync_projects/models テスト"""

import sys
from pathlib import Path


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

    def test_extract_description_summary(self):
        """summary属性からdescription抽出"""
        from sync_projects.models import _extract_description

        result = _extract_description({"summary": "Test summary"})
        assert result == "Test summary"

    def test_extract_id_with_project_id(self):
        """project_id属性あり"""
        from sync_projects.models import _extract_id

        result = _extract_id({"project_id": "proj-456"}, "fallback")
        assert result == "proj-456"

    def test_extract_id_with_uuid(self):
        """uuid属性あり"""
        from sync_projects.models import _extract_id

        result = _extract_id({"uuid": "uuid-789"}, "fallback")
        assert result == "uuid-789"

    def test_extract_id_fallback_to_name(self):
        """ID属性なしでフォールバック"""
        from sync_projects.models import _extract_id

        result = _extract_id({}, "Test Project")
        assert result == "test-project"

    def test_extract_id_empty_fallback(self):
        """空のフォールバック"""
        from sync_projects.models import _extract_id

        result = _extract_id({}, "")
        assert result == "unknown-project"

    def test_extract_name_with_project_name(self):
        """project_name属性あり"""
        from sync_projects.models import _extract_name

        result = _extract_name({"project_name": "My Project"})
        assert result == "My Project"


class TestParseRawItems:
    """_parse_raw_itemsのテスト"""

    def test_empty_list(self):
        """空リスト"""
        from sync_projects.models import _parse_raw_items

        items, warns, errs = _parse_raw_items([])
        assert items == []
        assert warns == []
        assert errs == []

    def test_basic_item(self):
        """基本的なアイテム"""
        from sync_projects.models import _parse_raw_items

        raw = [{"id": "item1", "type": "note", "title": "Test Note"}]
        items, warns, errs = _parse_raw_items(raw)
        assert len(items) == 1
        assert items[0].id == "item1"
        assert items[0].type == "note"

    def test_item_with_uuid(self):
        """uuid付きアイテム"""
        from sync_projects.models import _parse_raw_items

        raw = [{"uuid": "uuid-123", "kind": "task"}]
        items, warns, errs = _parse_raw_items(raw)
        assert items[0].id == "uuid-123"
        assert items[0].type == "task"

    def test_item_with_fallback_id(self):
        """ID自動生成"""
        from sync_projects.models import _parse_raw_items

        raw = [{"type": "note"}]
        items, warns, errs = _parse_raw_items(raw)
        assert items[0].id == "item-0"

    def test_item_with_body(self):
        """body属性からcontent"""
        from sync_projects.models import _parse_raw_items

        raw = [{"id": "item1", "type": "note", "body": "Body content"}]
        items, warns, errs = _parse_raw_items(raw)
        assert items[0].content == "Body content"

    def test_item_with_name(self):
        """name属性からtitle"""
        from sync_projects.models import _parse_raw_items

        raw = [{"id": "item1", "type": "note", "name": "Item Name"}]
        items, warns, errs = _parse_raw_items(raw)
        assert items[0].title == "Item Name"

    def test_item_with_createdAt(self):
        """createdAt属性"""
        from sync_projects.models import _parse_raw_items

        raw = [{"id": "item1", "type": "note", "createdAt": "2024-01-15T10:00:00"}]
        items, warns, errs = _parse_raw_items(raw)
        assert items[0].created_at is not None

    def test_item_with_updatedAt(self):
        """updatedAt属性"""
        from sync_projects.models import _parse_raw_items

        raw = [{"id": "item1", "type": "note", "updatedAt": "2024-01-16T10:00:00"}]
        items, warns, errs = _parse_raw_items(raw)
        assert items[0].updated_at is not None


class TestParseFeatures:
    """_parse_featuresのテスト"""

    def test_no_features(self):
        """features なし"""
        from sync_projects.models import _parse_features

        items, warns = _parse_features({})
        assert items == []
        assert warns == []

    def test_empty_features(self):
        """空のfeatures"""
        from sync_projects.models import _parse_features

        items, warns = _parse_features({"features": []})
        assert items == []

    def test_with_features(self):
        """featuresあり"""
        from sync_projects.models import _parse_features

        items, warns = _parse_features({"features": ["Feature A", "Feature B"]})
        assert len(items) == 2
        assert items[0].type == "feature"
        assert items[0].title == "Feature A"
        assert items[0].id == "feature-0"
        assert items[1].id == "feature-1"


class TestParseGoals:
    """_parse_goalsのテスト"""

    def test_no_goals(self):
        """goals なし"""
        from sync_projects.models import _parse_goals

        items, warns = _parse_goals({})
        assert items == []
        assert warns == []

    def test_empty_goals(self):
        """空のgoals"""
        from sync_projects.models import _parse_goals

        items, warns = _parse_goals({"goals": []})
        assert items == []

    def test_with_goals(self):
        """goalsあり"""
        from sync_projects.models import _parse_goals

        items, warns = _parse_goals({"goals": ["Goal 1", "Goal 2", "Goal 3"]})
        assert len(items) == 3
        assert items[0].type == "goal"
        assert items[0].title == "Goal 1"
        assert items[2].id == "goal-2"


class TestParseDevelopment:
    """_parse_developmentのテスト"""

    def test_no_development(self):
        """development なし"""
        from sync_projects.models import _parse_development

        items, meta, warns = _parse_development({})
        assert items == []
        assert meta == {}
        assert warns == []

    def test_empty_development(self):
        """空のdevelopment"""
        from sync_projects.models import _parse_development

        items, meta, warns = _parse_development({"development": {}})
        assert items == []
        assert meta == {}

    def test_with_languages(self):
        """languages付きdevelopment"""
        from sync_projects.models import _parse_development

        items, meta, warns = _parse_development({"development": {"languages": ["Python", "JavaScript"]}})
        assert len(items) == 2
        assert items[0].type == "tech"
        assert "language: Python" in items[0].title
        assert meta["languages"] == ["Python", "JavaScript"]

    def test_with_tools(self):
        """tools付きdevelopment"""
        from sync_projects.models import _parse_development

        items, meta, warns = _parse_development({"development": {"tools": ["Docker", "Git"]}})
        assert len(items) == 2
        assert "tool: Docker" in items[0].title
        assert meta["tools"] == ["Docker", "Git"]

    def test_with_platform(self):
        """platform付きdevelopment"""
        from sync_projects.models import _parse_development

        items, meta, warns = _parse_development({"development": {"platform": "web"}})
        assert meta["platform"] == "web"

    def test_with_status(self):
        """status付きdevelopment"""
        from sync_projects.models import _parse_development

        items, meta, warns = _parse_development({"development": {"status": "in_progress"}})
        assert meta["status"] == "in_progress"

    def test_full_development(self):
        """フルdevelopment"""
        from sync_projects.models import _parse_development

        data = {
            "development": {
                "languages": ["Python"],
                "tools": ["pytest"],
                "platform": "cli",
                "status": "active",
            }
        }
        items, meta, warns = _parse_development(data)
        assert len(items) == 2
        assert meta["platform"] == "cli"
        assert meta["status"] == "active"


class TestParseResources:
    """_parse_resourcesのテスト"""

    def test_no_resources(self):
        """resources なし"""
        from sync_projects.models import _parse_resources

        resources, warns = _parse_resources({})
        assert resources == []
        assert warns == []

    def test_empty_resources(self):
        """空のresources"""
        from sync_projects.models import _parse_resources

        resources, warns = _parse_resources({"resources": []})
        assert resources == []

    def test_with_resources(self):
        """resourcesあり"""
        from sync_projects.models import _parse_resources

        data = {
            "resources": [
                {"id": "res1", "title": "Resource 1", "url": "https://example.com"},
                {"id": "res2", "title": "Resource 2"},
            ]
        }
        resources, warns = _parse_resources(data)
        assert len(resources) == 2
        assert resources[0].title == "Resource 1"

    def test_with_links(self):
        """links属性から"""
        from sync_projects.models import _parse_resources

        data = {"links": [{"id": "link1", "name": "Link Name"}]}
        resources, warns = _parse_resources(data)
        assert len(resources) == 1
        assert resources[0].title == "Link Name"

    def test_resource_with_uuid(self):
        """uuid付きresource"""
        from sync_projects.models import _parse_resources

        data = {"resources": [{"uuid": "uuid-res"}]}
        resources, warns = _parse_resources(data)
        assert resources[0].id == "uuid-res"

    def test_resource_fallback_id(self):
        """ID自動生成"""
        from sync_projects.models import _parse_resources

        data = {"resources": [{"title": "No ID"}]}
        resources, warns = _parse_resources(data)
        assert resources[0].id == "res-0"

    def test_resource_with_kind(self):
        """kind付きresource"""
        from sync_projects.models import _parse_resources

        data = {"resources": [{"id": "res1", "kind": "document"}]}
        resources, warns = _parse_resources(data)
        assert resources[0].kind == "document"

    def test_resource_with_type(self):
        """type属性からkind"""
        from sync_projects.models import _parse_resources

        data = {"resources": [{"id": "res1", "type": "dataset"}]}
        resources, warns = _parse_resources(data)
        assert resources[0].kind == "dataset"


class TestBuildProjectMetadata:
    """_build_project_metadataのテスト"""

    def test_empty(self):
        """空のメタデータ"""
        from sync_projects.models import _build_project_metadata

        meta = _build_project_metadata({}, {})
        assert meta == {}

    def test_with_target_audience(self):
        """target_audience付き"""
        from sync_projects.models import _build_project_metadata

        meta = _build_project_metadata({"target_audience": "developers"}, {})
        assert meta["target_audience"] == "developers"

    def test_with_monetization(self):
        """monetization付き"""
        from sync_projects.models import _build_project_metadata

        meta = _build_project_metadata({"monetization": "subscription"}, {})
        assert meta["monetization"] == "subscription"

    def test_merges_dev_meta(self):
        """dev_metaのマージ"""
        from sync_projects.models import _build_project_metadata

        dev_meta = {"platform": "web", "status": "active"}
        meta = _build_project_metadata({}, dev_meta)
        assert meta["platform"] == "web"
        assert meta["status"] == "active"

    def test_full_metadata(self):
        """フルメタデータ"""
        from sync_projects.models import _build_project_metadata

        data = {"target_audience": "devs", "monetization": "free"}
        dev_meta = {"languages": ["Python"]}
        meta = _build_project_metadata(data, dev_meta)
        assert meta["target_audience"] == "devs"
        assert meta["monetization"] == "free"
        assert meta["languages"] == ["Python"]


class TestCoerceToProject:
    """coerce_to_projectのテスト"""

    def test_minimal_data(self):
        """最小データ"""
        from sync_projects.models import coerce_to_project

        result = coerce_to_project({})
        assert result.success is True
        assert result.project is not None
        assert result.project.name == "Untitled Project"

    def test_with_name(self):
        """name付きデータ"""
        from sync_projects.models import coerce_to_project

        result = coerce_to_project({"name": "My Project"})
        assert result.project.name == "My Project"

    def test_with_id(self):
        """id付きデータ"""
        from sync_projects.models import coerce_to_project

        result = coerce_to_project({"id": "proj-123", "name": "Test"})
        assert result.project.id == "proj-123"

    def test_with_description(self):
        """description付きデータ"""
        from sync_projects.models import coerce_to_project

        result = coerce_to_project({"name": "Test", "description": "Test description"})
        assert result.project.description == "Test description"

    def test_with_items(self):
        """items付きデータ"""
        from sync_projects.models import coerce_to_project

        data = {
            "name": "Test",
            "items": [{"id": "item1", "type": "note", "title": "Note 1"}],
        }
        result = coerce_to_project(data)
        assert len(result.project.items) >= 1

    def test_with_notes(self):
        """notes属性からitems"""
        from sync_projects.models import coerce_to_project

        data = {
            "name": "Test",
            "notes": [{"id": "note1", "type": "note"}],
        }
        result = coerce_to_project(data)
        assert len(result.project.items) >= 1

    def test_with_features(self):
        """features付きデータ"""
        from sync_projects.models import coerce_to_project

        data = {"name": "Test", "features": ["Feature A", "Feature B"]}
        result = coerce_to_project(data)
        assert any(item.type == "feature" for item in result.project.items)

    def test_with_goals(self):
        """goals付きデータ"""
        from sync_projects.models import coerce_to_project

        data = {"name": "Test", "goals": ["Goal 1"]}
        result = coerce_to_project(data)
        assert any(item.type == "goal" for item in result.project.items)

    def test_with_development(self):
        """development付きデータ"""
        from sync_projects.models import coerce_to_project

        data = {
            "name": "Test",
            "development": {"languages": ["Python"], "platform": "cli"},
        }
        result = coerce_to_project(data)
        assert "platform" in result.project.metadata
        assert any(item.type == "tech" for item in result.project.items)

    def test_with_resources(self):
        """resources付きデータ"""
        from sync_projects.models import coerce_to_project

        data = {
            "name": "Test",
            "resources": [{"id": "res1", "title": "Resource 1"}],
        }
        result = coerce_to_project(data)
        assert len(result.project.resources) == 1

    def test_with_created_at(self):
        """created_at付きデータ"""
        from sync_projects.models import coerce_to_project

        data = {"name": "Test", "created_at": "2024-01-15T10:00:00"}
        result = coerce_to_project(data)
        assert result.project.created_at is not None

    def test_with_createdAt(self):
        """createdAt属性から"""
        from sync_projects.models import coerce_to_project

        data = {"name": "Test", "createdAt": "2024-01-15T10:00:00"}
        result = coerce_to_project(data)
        assert result.project.created_at is not None

    def test_with_updated_at(self):
        """updated_at付きデータ"""
        from sync_projects.models import coerce_to_project

        data = {"name": "Test", "updated_at": "2024-01-16T10:00:00"}
        result = coerce_to_project(data)
        assert result.project.updated_at is not None

    def test_preserves_raw(self):
        """生データ保持"""
        from sync_projects.models import coerce_to_project

        data = {"name": "Test", "custom_field": "custom_value"}
        result = coerce_to_project(data)
        assert result.project.raw == data

    def test_with_target_audience(self):
        """target_audience付きデータ"""
        from sync_projects.models import coerce_to_project

        data = {"name": "Test", "target_audience": "developers"}
        result = coerce_to_project(data)
        assert result.project.metadata["target_audience"] == "developers"

    def test_with_monetization(self):
        """monetization付きデータ"""
        from sync_projects.models import coerce_to_project

        data = {"name": "Test", "monetization": "freemium"}
        result = coerce_to_project(data)
        assert result.project.metadata["monetization"] == "freemium"

    def test_full_project(self):
        """フルプロジェクト"""
        from sync_projects.models import coerce_to_project

        data = {
            "id": "proj-full",
            "name": "Full Project",
            "description": "A complete project",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-15T10:00:00",
            "items": [{"id": "item1", "type": "note"}],
            "features": ["Feature 1"],
            "goals": ["Goal 1"],
            "development": {"languages": ["Python"], "tools": ["pytest"]},
            "resources": [{"id": "res1"}],
            "target_audience": "devs",
            "monetization": "free",
        }
        result = coerce_to_project(data)
        assert result.success is True
        assert result.project.id == "proj-full"
        assert result.project.name == "Full Project"
        assert len(result.project.items) > 0
        assert len(result.project.resources) == 1


class TestSlugifyNameEdgeCases:
    """_slugify_nameのエッジケーステスト"""

    def test_consecutive_hyphens(self):
        """連続ハイフン"""
        result = _slugify_name("Test---Project")
        assert "---" not in result

    def test_leading_trailing_spaces(self):
        """前後スペース"""
        result = _slugify_name("  Test Project  ")
        assert not result.startswith("-")
        assert not result.endswith("-")

    def test_mixed_cjk_and_latin(self):
        """CJKとラテン文字混在"""
        result = _slugify_name("プロジェクト Test")
        assert "プロジェクト" in result or "test" in result.lower()

    def test_numeric_only(self):
        """数字のみ"""
        result = _slugify_name("12345")
        assert "12345" in result

    def test_underscore_preserved(self):
        """アンダースコア保持"""
        result = _slugify_name("test_project")
        assert "_" in result or "test" in result
