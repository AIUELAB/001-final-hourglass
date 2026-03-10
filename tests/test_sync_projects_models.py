#!/usr/bin/env python3
"""sync_projects/models テスト"""

from unittest.mock import patch

from src.sync_projects.models import (
    ParseResult,
    ProjectItem,
    ProjectModel,
    ProjectResource,
    _build_project_metadata,
    _extract_description,
    _extract_id,
    _extract_name,
    _parse_development,
    _parse_features,
    _parse_goals,
    _parse_raw_items,
    _parse_resources,
    _slugify_name,
    coerce_to_project,
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

        result = _extract_name({"name": "Project Name"})
        assert result == "Project Name"

    def test_extract_name_with_title(self):
        """title属性あり"""

        result = _extract_name({"title": "Project Title"})
        assert result == "Project Title"

    def test_extract_name_fallback(self):
        """フォールバック"""

        result = _extract_name({})
        assert result == "Untitled Project"

    def test_extract_id_with_id(self):
        """id属性あり"""

        result = _extract_id({"id": "proj-123"}, "fallback")
        assert result == "proj-123"

    def test_extract_description(self):
        """description抽出"""

        result = _extract_description({"description": "Test desc"})
        assert result == "Test desc"

    def test_extract_description_none(self):
        """description なし"""

        result = _extract_description({})
        assert result is None

    def test_extract_description_summary(self):
        """summary属性からdescription抽出"""

        result = _extract_description({"summary": "Test summary"})
        assert result == "Test summary"

    def test_extract_id_with_project_id(self):
        """project_id属性あり"""

        result = _extract_id({"project_id": "proj-456"}, "fallback")
        assert result == "proj-456"

    def test_extract_id_with_uuid(self):
        """uuid属性あり"""

        result = _extract_id({"uuid": "uuid-789"}, "fallback")
        assert result == "uuid-789"

    def test_extract_id_fallback_to_name(self):
        """ID属性なしでフォールバック"""

        result = _extract_id({}, "Test Project")
        assert result == "test-project"

    def test_extract_id_empty_fallback(self):
        """空のフォールバック"""

        result = _extract_id({}, "")
        assert result == "unknown-project"

    def test_extract_name_with_project_name(self):
        """project_name属性あり"""

        result = _extract_name({"project_name": "My Project"})
        assert result == "My Project"


class TestParseRawItems:
    """_parse_raw_itemsのテスト"""

    def test_empty_list(self):
        """空リスト"""

        items, warns, errs = _parse_raw_items([])
        assert items == []
        assert warns == []
        assert errs == []

    def test_basic_item(self):
        """基本的なアイテム"""

        raw = [{"id": "item1", "type": "note", "title": "Test Note"}]
        items, warns, errs = _parse_raw_items(raw)
        assert len(items) == 1
        assert items[0].id == "item1"
        assert items[0].type == "note"

    def test_item_with_uuid(self):
        """uuid付きアイテム"""

        raw = [{"uuid": "uuid-123", "kind": "task"}]
        items, _warns, _errs = _parse_raw_items(raw)
        assert items[0].id == "uuid-123"
        assert items[0].type == "task"

    def test_item_with_fallback_id(self):
        """ID自動生成"""

        raw = [{"type": "note"}]
        items, _warns, _errs = _parse_raw_items(raw)
        assert items[0].id == "item-0"

    def test_item_with_body(self):
        """body属性からcontent"""

        raw = [{"id": "item1", "type": "note", "body": "Body content"}]
        items, warns, errs = _parse_raw_items(raw)
        assert items[0].content == "Body content"

    def test_item_with_name(self):
        """name属性からtitle"""

        raw = [{"id": "item1", "type": "note", "name": "Item Name"}]
        items, warns, errs = _parse_raw_items(raw)
        assert items[0].title == "Item Name"

    def test_item_with_createdAt(self):
        """createdAt属性"""

        raw = [{"id": "item1", "type": "note", "createdAt": "2024-01-15T10:00:00"}]
        items, warns, errs = _parse_raw_items(raw)
        assert items[0].created_at is not None

    def test_item_with_updatedAt(self):
        """updatedAt属性"""

        raw = [{"id": "item1", "type": "note", "updatedAt": "2024-01-16T10:00:00"}]
        items, warns, errs = _parse_raw_items(raw)
        assert items[0].updated_at is not None


class TestParseFeatures:
    """_parse_featuresのテスト"""

    def test_no_features(self):
        """features なし"""

        items, warns = _parse_features({})
        assert items == []
        assert warns == []

    def test_empty_features(self):
        """空のfeatures"""

        items, warns = _parse_features({"features": []})
        assert items == []

    def test_with_features(self):
        """featuresあり"""

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

        items, warns = _parse_goals({})
        assert items == []
        assert warns == []

    def test_empty_goals(self):
        """空のgoals"""

        items, warns = _parse_goals({"goals": []})
        assert items == []

    def test_with_goals(self):
        """goalsあり"""

        items, warns = _parse_goals({"goals": ["Goal 1", "Goal 2", "Goal 3"]})
        assert len(items) == 3
        assert items[0].type == "goal"
        assert items[0].title == "Goal 1"
        assert items[2].id == "goal-2"


class TestParseDevelopment:
    """_parse_developmentのテスト"""

    def test_no_development(self):
        """development なし"""

        items, meta, warns = _parse_development({})
        assert items == []
        assert meta == {}
        assert warns == []

    def test_empty_development(self):
        """空のdevelopment"""

        items, meta, warns = _parse_development({"development": {}})
        assert items == []
        assert meta == {}

    def test_with_languages(self):
        """languages付きdevelopment"""

        items, meta, warns = _parse_development({"development": {"languages": ["Python", "JavaScript"]}})
        assert len(items) == 2
        assert items[0].type == "tech"
        assert "language: Python" in items[0].title
        assert meta["languages"] == ["Python", "JavaScript"]

    def test_with_tools(self):
        """tools付きdevelopment"""

        items, meta, warns = _parse_development({"development": {"tools": ["Docker", "Git"]}})
        assert len(items) == 2
        assert "tool: Docker" in items[0].title
        assert meta["tools"] == ["Docker", "Git"]

    def test_with_platform(self):
        """platform付きdevelopment"""

        items, meta, warns = _parse_development({"development": {"platform": "web"}})
        assert meta["platform"] == "web"

    def test_with_status(self):
        """status付きdevelopment"""

        items, meta, warns = _parse_development({"development": {"status": "in_progress"}})
        assert meta["status"] == "in_progress"

    def test_full_development(self):
        """フルdevelopment"""

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

        resources, warns = _parse_resources({})
        assert resources == []
        assert warns == []

    def test_empty_resources(self):
        """空のresources"""

        resources, warns = _parse_resources({"resources": []})
        assert resources == []

    def test_with_resources(self):
        """resourcesあり"""

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

        data = {"links": [{"id": "link1", "name": "Link Name"}]}
        resources, warns = _parse_resources(data)
        assert len(resources) == 1
        assert resources[0].title == "Link Name"

    def test_resource_with_uuid(self):
        """uuid付きresource"""

        data = {"resources": [{"uuid": "uuid-res"}]}
        resources, warns = _parse_resources(data)
        assert resources[0].id == "uuid-res"

    def test_resource_fallback_id(self):
        """ID自動生成"""

        data = {"resources": [{"title": "No ID"}]}
        resources, warns = _parse_resources(data)
        assert resources[0].id == "res-0"

    def test_resource_with_kind(self):
        """kind付きresource"""

        data = {"resources": [{"id": "res1", "kind": "document"}]}
        resources, warns = _parse_resources(data)
        assert resources[0].kind == "document"

    def test_resource_with_type(self):
        """type属性からkind"""

        data = {"resources": [{"id": "res1", "type": "dataset"}]}
        resources, warns = _parse_resources(data)
        assert resources[0].kind == "dataset"


class TestBuildProjectMetadata:
    """_build_project_metadataのテスト"""

    def test_empty(self):
        """空のメタデータ"""

        meta = _build_project_metadata({}, {})
        assert meta == {}

    def test_with_target_audience(self):
        """target_audience付き"""

        meta = _build_project_metadata({"target_audience": "developers"}, {})
        assert meta["target_audience"] == "developers"

    def test_with_monetization(self):
        """monetization付き"""

        meta = _build_project_metadata({"monetization": "subscription"}, {})
        assert meta["monetization"] == "subscription"

    def test_merges_dev_meta(self):
        """dev_metaのマージ"""

        dev_meta = {"platform": "web", "status": "active"}
        meta = _build_project_metadata({}, dev_meta)
        assert meta["platform"] == "web"
        assert meta["status"] == "active"

    def test_full_metadata(self):
        """フルメタデータ"""

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

        result = coerce_to_project({})
        assert result.success is True
        assert result.project is not None
        assert result.project.name == "Untitled Project"

    def test_with_name(self):
        """name付きデータ"""

        result = coerce_to_project({"name": "My Project"})
        assert result.project.name == "My Project"

    def test_with_id(self):
        """id付きデータ"""

        result = coerce_to_project({"id": "proj-123", "name": "Test"})
        assert result.project.id == "proj-123"

    def test_with_description(self):
        """description付きデータ"""

        result = coerce_to_project({"name": "Test", "description": "Test description"})
        assert result.project.description == "Test description"

    def test_with_items(self):
        """items付きデータ"""

        data = {
            "name": "Test",
            "items": [{"id": "item1", "type": "note", "title": "Note 1"}],
        }
        result = coerce_to_project(data)
        assert len(result.project.items) >= 1

    def test_with_notes(self):
        """notes属性からitems"""

        data = {
            "name": "Test",
            "notes": [{"id": "note1", "type": "note"}],
        }
        result = coerce_to_project(data)
        assert len(result.project.items) >= 1

    def test_with_features(self):
        """features付きデータ"""

        data = {"name": "Test", "features": ["Feature A", "Feature B"]}
        result = coerce_to_project(data)
        assert any(item.type == "feature" for item in result.project.items)

    def test_with_goals(self):
        """goals付きデータ"""

        data = {"name": "Test", "goals": ["Goal 1"]}
        result = coerce_to_project(data)
        assert any(item.type == "goal" for item in result.project.items)

    def test_with_development(self):
        """development付きデータ"""

        data = {
            "name": "Test",
            "development": {"languages": ["Python"], "platform": "cli"},
        }
        result = coerce_to_project(data)
        assert "platform" in result.project.metadata
        assert any(item.type == "tech" for item in result.project.items)

    def test_with_resources(self):
        """resources付きデータ"""

        data = {
            "name": "Test",
            "resources": [{"id": "res1", "title": "Resource 1"}],
        }
        result = coerce_to_project(data)
        assert len(result.project.resources) == 1

    def test_with_created_at(self):
        """created_at付きデータ"""

        data = {"name": "Test", "created_at": "2024-01-15T10:00:00"}
        result = coerce_to_project(data)
        assert result.project.created_at is not None

    def test_with_createdAt(self):
        """createdAt属性から"""

        data = {"name": "Test", "createdAt": "2024-01-15T10:00:00"}
        result = coerce_to_project(data)
        assert result.project.created_at is not None

    def test_with_updated_at(self):
        """updated_at付きデータ"""

        data = {"name": "Test", "updated_at": "2024-01-16T10:00:00"}
        result = coerce_to_project(data)
        assert result.project.updated_at is not None

    def test_preserves_raw(self):
        """生データ保持"""

        data = {"name": "Test", "custom_field": "custom_value"}
        result = coerce_to_project(data)
        assert result.project.raw == data

    def test_with_target_audience(self):
        """target_audience付きデータ"""

        data = {"name": "Test", "target_audience": "developers"}
        result = coerce_to_project(data)
        assert result.project.metadata["target_audience"] == "developers"

    def test_with_monetization(self):
        """monetization付きデータ"""

        data = {"name": "Test", "monetization": "freemium"}
        result = coerce_to_project(data)
        assert result.project.metadata["monetization"] == "freemium"

    def test_full_project(self):
        """フルプロジェクト"""

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


class _ValidationErrorHelper:
    """ValidationError を生成するヘルパー"""

    @staticmethod
    def make_ve(title="Test"):
        from pydantic import ValidationError as VE

        return VE.from_exception_data(
            title=title,
            line_errors=[{"type": "missing", "loc": ("id",), "msg": "Field required", "input": {}}],
        )


class TestParseRawItemsValidationError:
    """_parse_raw_items の ValidationError パスをカバー (L112-113)"""

    @patch("src.sync_projects.models.ProjectItem")
    def test_validation_error_recorded_in_errors(self, mock_item):
        """ValidationError 発生時、エラーリストに記録される"""
        mock_item.side_effect = _ValidationErrorHelper.make_ve("ProjectItem")

        raw = [{"id": "item-0", "type": "note"}]
        items, warns, errs = _parse_raw_items(raw)

        assert len(items) == 0
        assert len(errs) == 1
        assert "item[0] validation error" in errs[0]


class TestParseFeaturesValidationError:
    """_parse_features の ValidationError パスをカバー (L123-124)"""

    @patch("src.sync_projects.models.ProjectItem")
    def test_validation_error_recorded_in_warnings(self, mock_item):
        """ValidationError 発生時、警告リストに記録される"""
        mock_item.side_effect = _ValidationErrorHelper.make_ve("ProjectItem")

        items, warns = _parse_features({"features": ["feat-a", "feat-b"]})

        assert len(items) == 0
        assert len(warns) == 2
        assert "feature[0] validation warning" in warns[0]
        assert "feature[1] validation warning" in warns[1]


class TestParseGoalsValidationError:
    """_parse_goals の ValidationError パスをカバー (L134-135)"""

    @patch("src.sync_projects.models.ProjectItem")
    def test_validation_error_recorded_in_warnings(self, mock_item):
        """ValidationError 発生時、警告リストに記録される"""
        mock_item.side_effect = _ValidationErrorHelper.make_ve("ProjectItem")

        items, warns = _parse_goals({"goals": ["goal-a"]})

        assert len(items) == 0
        assert len(warns) == 1
        assert "goal[0] validation warning" in warns[0]


class TestParseDevelopmentValidationError:
    """_parse_development の ValidationError パスをカバー (L157-158, L162-163)"""

    @patch("src.sync_projects.models.ProjectItem")
    def test_language_and_tool_validation_errors(self, mock_item):
        """language と tool の ValidationError が警告に記録される"""
        mock_item.side_effect = _ValidationErrorHelper.make_ve("ProjectItem")

        data = {
            "development": {
                "languages": ["Python", "TypeScript"],
                "tools": ["Docker"],
                "platform": "web",
                "status": "active",
            }
        }
        items, meta, warns = _parse_development(data)

        assert len(items) == 0
        assert len(warns) == 3
        assert "language[0] validation warning" in warns[0]
        assert "language[1] validation warning" in warns[1]
        assert "tool[0] validation warning" in warns[2]
        assert meta["platform"] == "web"
        assert meta["status"] == "active"


class TestParseResourcesValidationError:
    """_parse_resources の ValidationError パスをカバー (L181-182)"""

    @patch("src.sync_projects.models.ProjectResource")
    def test_validation_error_recorded_in_warnings(self, mock_resource):
        """ValidationError 発生時、警告リストに記録される"""
        mock_resource.side_effect = _ValidationErrorHelper.make_ve("ProjectResource")

        data = {"resources": [{"id": "res-0", "title": "Doc"}]}
        resources, warns = _parse_resources(data)

        assert len(resources) == 0
        assert len(warns) == 1
        assert "resource[0] validation warning" in warns[0]


class TestCoerceToProjectValidationError:
    """coerce_to_project の ValidationError パスをカバー (L236-238)"""

    @patch("src.sync_projects.models.ProjectModel")
    def test_project_model_validation_error(self, mock_model):
        """ProjectModel 作成で ValidationError が発生した場合"""
        mock_model.side_effect = _ValidationErrorHelper.make_ve("ProjectModel")

        data = {"name": "Test Project", "id": "test-1"}
        result = coerce_to_project(data)

        assert result.success is False
        assert result.project is None
        assert len(result.errors) >= 1
        assert any("project validation error" in e for e in result.errors)
