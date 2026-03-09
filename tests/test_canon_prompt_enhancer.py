"""
Tests for src/utils/canon_prompt_enhancer.py - CanonPromptEnhancer

TDD: 原作情報ベースのプロンプト強化システムのテスト
- EnhancedPrompt dataclass
- CanonPromptEnhancer の全メソッド
- CanonKB は完全モック（外部JSON読み込み回避）
"""

from unittest.mock import MagicMock, patch

import pytest

from src.utils.canon_kb import AgeMilestone, Character, KeyScene
from src.utils.canon_prompt_enhancer import CanonPromptEnhancer, EnhancedPrompt


# =============================================================================
# Helpers - テスト用データ生成
# =============================================================================


def _make_key_scene(
    scene_id: str = "SC001",
    description: str = "テストシーン",
    story_arc: str = "テスト編",
    source_type: str = "manga",
    source_reference: str = "第1巻",
) -> KeyScene:
    return KeyScene(
        scene_id=scene_id,
        description=description,
        story_arc=story_arc,
        source_type=source_type,
        source_reference=source_reference,
    )


def _make_milestone(
    age: int = 15,
    events: list[str] | None = None,
    source: str = "第1巻",
) -> AgeMilestone:
    return AgeMilestone(
        age=age,
        events=events if events is not None else ["イベント1"],
        source=source,
    )


def _make_character(
    name: str = "テストキャラ",
    age_at_story: int | None = 15,
    key_scenes: list[KeyScene] | None = None,
    age_milestones: list[AgeMilestone] | None = None,
) -> Character:
    return Character(
        name=name,
        character_id="CH001",
        aliases=[],
        age_at_story=age_at_story,
        abilities=[],
        key_scenes=key_scenes or [],
        age_milestones=age_milestones or [],
    )


def _make_mock_kb(character: Character | None = None) -> MagicMock:
    """CanonKBのモックを生成"""
    mock_kb = MagicMock()
    mock_kb.get_character.return_value = character
    return mock_kb


# =============================================================================
# EnhancedPrompt Tests
# =============================================================================


class TestEnhancedPrompt:
    """EnhancedPrompt dataclass のテスト"""

    def test_instantiation(self):
        ep = EnhancedPrompt(
            prompt="test prompt",
            canon_events=["event1", "event2"],
            has_canon_data=True,
            suggested_source="第1巻",
        )
        assert ep.prompt == "test prompt"
        assert len(ep.canon_events) == 2
        assert ep.has_canon_data is True
        assert ep.suggested_source == "第1巻"

    def test_instantiation_empty(self):
        ep = EnhancedPrompt(
            prompt="",
            canon_events=[],
            has_canon_data=False,
            suggested_source=None,
        )
        assert ep.canon_events == []
        assert ep.suggested_source is None


# =============================================================================
# __init__ Tests
# =============================================================================


class TestCanonPromptEnhancerInit:
    """__init__ のテスト"""

    def test_init_with_canon_kb(self):
        mock_kb = MagicMock()
        enhancer = CanonPromptEnhancer(canon_kb=mock_kb)
        assert enhancer._canon_kb is mock_kb

    def test_init_without_canon_kb_creates_default(self):
        with patch("src.utils.canon_prompt_enhancer.CanonKB") as mock_cls:
            mock_instance = MagicMock()
            mock_cls.return_value = mock_instance

            enhancer = CanonPromptEnhancer()

            mock_cls.assert_called_once()
            assert enhancer._canon_kb is mock_instance


# =============================================================================
# enhance Tests
# =============================================================================


class TestEnhance:
    """enhance メソッドのテスト"""

    def test_enhance_no_character_data(self):
        """CanonKBにキャラがない場合はNO_DATA_TEMPLATE"""
        mock_kb = _make_mock_kb(character=None)
        enhancer = CanonPromptEnhancer(canon_kb=mock_kb)

        result = enhancer.enhance("不明キャラ", "不明作品", 20, "ベースプロンプト")

        assert result.has_canon_data is False
        assert result.canon_events == []
        assert result.suggested_source is None
        assert "不明キャラ" in result.prompt
        assert "原作情報がデータベースに登録されていません" in result.prompt
        assert "ベースプロンプト" in result.prompt

    def test_enhance_with_events(self):
        """原作イベントがある場合はENHANCED_TEMPLATE"""
        scene = _make_key_scene(description="最終選別に合格")
        milestone = _make_milestone(age=15, events=["鬼殺隊に入隊"], source="第1巻")
        char = _make_character(
            name="竈門炭治郎",
            age_at_story=15,
            key_scenes=[scene],
            age_milestones=[milestone],
        )
        mock_kb = _make_mock_kb(character=char)
        enhancer = CanonPromptEnhancer(canon_kb=mock_kb)

        result = enhancer.enhance("竈門炭治郎", "鬼滅の刃", 15, "生成してください")

        assert result.has_canon_data is True
        assert len(result.canon_events) > 0
        assert "竈門炭治郎" in result.prompt
        assert "鬼滅の刃" in result.prompt
        assert "15" in result.prompt
        assert "禁止事項" in result.prompt
        assert "生成してください" in result.prompt

    def test_enhance_character_exists_but_no_events_for_age(self):
        """キャラはあるが年齢に該当イベントがない"""
        milestone = _make_milestone(age=15, events=["イベント"])
        char = _make_character(
            age_at_story=15,
            age_milestones=[milestone],
        )
        mock_kb = _make_mock_kb(character=char)
        enhancer = CanonPromptEnhancer(canon_kb=mock_kb)

        # age=30 にはイベントなし
        result = enhancer.enhance("テスト", "テスト作品", 30, "base")

        assert result.has_canon_data is False
        assert result.canon_events == []
        assert "原作情報がデータベースに登録されていません" in result.prompt


# =============================================================================
# _get_events_for_age Tests
# =============================================================================


class TestGetEventsForAge:
    """_get_events_for_age のテスト"""

    def test_events_from_milestones(self):
        milestone = _make_milestone(age=15, events=["イベントA", "イベントB"])
        char = _make_character(age_at_story=20, age_milestones=[milestone])

        enhancer = CanonPromptEnhancer(canon_kb=_make_mock_kb())
        events = enhancer._get_events_for_age(char, 15)

        assert events == ["イベントA", "イベントB"]

    def test_events_from_key_scenes_at_story_age(self):
        """age_at_storyと一致する場合key_scenesも追加"""
        scene = _make_key_scene(description="重要シーン")
        char = _make_character(
            age_at_story=15,
            key_scenes=[scene],
            age_milestones=[],
        )

        enhancer = CanonPromptEnhancer(canon_kb=_make_mock_kb())
        events = enhancer._get_events_for_age(char, 15)

        assert "重要シーン" in events

    def test_events_combines_milestones_and_scenes(self):
        """milestoneとkey_scenesの両方から取得"""
        milestone = _make_milestone(age=15, events=["マイルストーンイベント"])
        scene = _make_key_scene(description="シーンイベント")
        char = _make_character(
            age_at_story=15,
            key_scenes=[scene],
            age_milestones=[milestone],
        )

        enhancer = CanonPromptEnhancer(canon_kb=_make_mock_kb())
        events = enhancer._get_events_for_age(char, 15)

        assert "マイルストーンイベント" in events
        assert "シーンイベント" in events

    def test_events_no_duplicates(self):
        """milestoneとsceneで同じ内容なら重複しない"""
        milestone = _make_milestone(age=15, events=["共通イベント"])
        scene = _make_key_scene(description="共通イベント")
        char = _make_character(
            age_at_story=15,
            key_scenes=[scene],
            age_milestones=[milestone],
        )

        enhancer = CanonPromptEnhancer(canon_kb=_make_mock_kb())
        events = enhancer._get_events_for_age(char, 15)

        assert events.count("共通イベント") == 1

    def test_events_empty_for_non_matching_age(self):
        milestone = _make_milestone(age=15, events=["イベント"])
        char = _make_character(age_at_story=15, age_milestones=[milestone])

        enhancer = CanonPromptEnhancer(canon_kb=_make_mock_kb())
        events = enhancer._get_events_for_age(char, 99)

        assert events == []


# =============================================================================
# _get_scenes_for_age Tests
# =============================================================================


class TestGetScenesForAge:
    """_get_scenes_for_age のテスト"""

    def test_scenes_matching_age(self):
        scene = _make_key_scene()
        char = _make_character(age_at_story=15, key_scenes=[scene])

        enhancer = CanonPromptEnhancer(canon_kb=_make_mock_kb())
        scenes = enhancer._get_scenes_for_age(char, 15)

        assert len(scenes) == 1
        assert scenes[0] is scene

    def test_scenes_non_matching_age(self):
        scene = _make_key_scene()
        char = _make_character(age_at_story=15, key_scenes=[scene])

        enhancer = CanonPromptEnhancer(canon_kb=_make_mock_kb())
        scenes = enhancer._get_scenes_for_age(char, 30)

        assert scenes == []


# =============================================================================
# get_canon_events_text Tests
# =============================================================================


class TestGetCanonEventsText:
    """get_canon_events_text のテスト"""

    def test_with_events_and_scenes(self):
        milestone = _make_milestone(age=15, events=["入隊", "修行開始"])
        scene = _make_key_scene(
            description="別のシーン",
            story_arc="入隊編",
            source_type="manga",
            source_reference="第1巻第1話",
        )
        char = _make_character(
            age_at_story=15,
            key_scenes=[scene],
            age_milestones=[milestone],
        )
        mock_kb = _make_mock_kb(character=char)
        enhancer = CanonPromptEnhancer(canon_kb=mock_kb)

        text = enhancer.get_canon_events_text("テスト", "テスト作品", 15)

        assert "1. 入隊" in text
        assert "2. 修行開始" in text
        assert "出典詳細" in text
        assert "入隊編" in text

    def test_with_events_no_scenes(self):
        milestone = _make_milestone(age=15, events=["イベント1"])
        char = _make_character(
            age_at_story=20,  # ageと異なる -> scenesなし
            age_milestones=[milestone],
        )
        mock_kb = _make_mock_kb(character=char)
        enhancer = CanonPromptEnhancer(canon_kb=mock_kb)

        text = enhancer.get_canon_events_text("テスト", "テスト作品", 15)

        assert "1. イベント1" in text
        assert "出典詳細" not in text

    def test_no_events(self):
        char = _make_character(age_at_story=20, age_milestones=[])
        mock_kb = _make_mock_kb(character=char)
        enhancer = CanonPromptEnhancer(canon_kb=mock_kb)

        text = enhancer.get_canon_events_text("テスト", "テスト作品", 30)

        assert "登録されていません" in text

    def test_no_character(self):
        mock_kb = _make_mock_kb(character=None)
        enhancer = CanonPromptEnhancer(canon_kb=mock_kb)

        text = enhancer.get_canon_events_text("不明", "不明作品", 15)

        assert "データなし" in text


# =============================================================================
# get_suggested_source Tests
# =============================================================================


class TestGetSuggestedSource:
    """get_suggested_source のテスト"""

    def test_from_milestone_source(self):
        milestone = _make_milestone(age=15, events=["イベント"], source="第3巻第15話")
        char = _make_character(age_at_story=20, age_milestones=[milestone])
        mock_kb = _make_mock_kb(character=char)
        enhancer = CanonPromptEnhancer(canon_kb=mock_kb)

        source = enhancer.get_suggested_source("テスト", "テスト作品", 15)

        assert source == "第3巻第15話"

    def test_from_key_scenes_when_no_milestone(self):
        scene = _make_key_scene(source_reference="アニメ第5話")
        char = _make_character(
            age_at_story=15,
            key_scenes=[scene],
            age_milestones=[],
        )
        mock_kb = _make_mock_kb(character=char)
        enhancer = CanonPromptEnhancer(canon_kb=mock_kb)

        source = enhancer.get_suggested_source("テスト", "テスト作品", 15)

        assert source == "アニメ第5話"

    def test_no_source_data(self):
        char = _make_character(age_at_story=20, age_milestones=[], key_scenes=[])
        mock_kb = _make_mock_kb(character=char)
        enhancer = CanonPromptEnhancer(canon_kb=mock_kb)

        source = enhancer.get_suggested_source("テスト", "テスト作品", 30)

        assert source is None

    def test_no_character(self):
        mock_kb = _make_mock_kb(character=None)
        enhancer = CanonPromptEnhancer(canon_kb=mock_kb)

        source = enhancer.get_suggested_source("不明", "不明作品", 15)

        assert source is None

    def test_milestone_without_source_falls_through(self):
        """milestoneのsourceが空文字の場合、key_scenesにフォールバック"""
        milestone = _make_milestone(age=15, events=["イベント"], source="")
        scene = _make_key_scene(source_reference="フォールバック出典")
        char = _make_character(
            age_at_story=15,
            key_scenes=[scene],
            age_milestones=[milestone],
        )
        mock_kb = _make_mock_kb(character=char)
        enhancer = CanonPromptEnhancer(canon_kb=mock_kb)

        source = enhancer.get_suggested_source("テスト", "テスト作品", 15)

        # source="" is falsy, so milestone branch skipped -> falls to key_scenes
        assert source == "フォールバック出典"


# =============================================================================
# should_skip_generation Tests
# =============================================================================


class TestShouldSkipGeneration:
    """should_skip_generation のテスト"""

    def test_skip_when_no_events(self):
        char = _make_character(age_at_story=15, age_milestones=[])
        mock_kb = _make_mock_kb(character=char)
        enhancer = CanonPromptEnhancer(canon_kb=mock_kb)

        assert enhancer.should_skip_generation("テスト", "テスト作品", 30) is True

    def test_no_skip_when_events_exist(self):
        milestone = _make_milestone(age=15, events=["イベント"])
        char = _make_character(age_at_story=15, age_milestones=[milestone])
        mock_kb = _make_mock_kb(character=char)
        enhancer = CanonPromptEnhancer(canon_kb=mock_kb)

        assert enhancer.should_skip_generation("テスト", "テスト作品", 15) is False

    def test_no_skip_when_no_character_data(self):
        """キャラデータがない場合はスキップしない（LLMに判断させる）"""
        mock_kb = _make_mock_kb(character=None)
        enhancer = CanonPromptEnhancer(canon_kb=mock_kb)

        assert enhancer.should_skip_generation("不明", "不明作品", 15) is False


# =============================================================================
# get_available_ages Tests
# =============================================================================


class TestGetAvailableAges:
    """get_available_ages のテスト"""

    def test_ages_from_milestones_and_story(self):
        milestones = [
            _make_milestone(age=13, events=["幼少期"]),
            _make_milestone(age=15, events=["修行開始"]),
        ]
        char = _make_character(
            age_at_story=15,
            age_milestones=milestones,
        )
        mock_kb = _make_mock_kb(character=char)
        enhancer = CanonPromptEnhancer(canon_kb=mock_kb)

        ages = enhancer.get_available_ages("テスト", "テスト作品")

        assert ages == [13, 15]  # ソート済み、age_at_story=15は重複なし

    def test_ages_only_from_story_age(self):
        char = _make_character(age_at_story=20, age_milestones=[])
        mock_kb = _make_mock_kb(character=char)
        enhancer = CanonPromptEnhancer(canon_kb=mock_kb)

        ages = enhancer.get_available_ages("テスト", "テスト作品")

        assert ages == [20]

    def test_ages_no_character(self):
        mock_kb = _make_mock_kb(character=None)
        enhancer = CanonPromptEnhancer(canon_kb=mock_kb)

        ages = enhancer.get_available_ages("不明", "不明作品")

        assert ages == []

    def test_ages_milestone_without_events_excluded(self):
        """eventsが空のmilestoneはagesに含まれない"""
        milestones = [
            _make_milestone(age=10, events=[]),  # 空 -> 除外
            _make_milestone(age=15, events=["イベント"]),
        ]
        char = _make_character(
            age_at_story=None,
            age_milestones=milestones,
        )
        mock_kb = _make_mock_kb(character=char)
        enhancer = CanonPromptEnhancer(canon_kb=mock_kb)

        ages = enhancer.get_available_ages("テスト", "テスト作品")

        assert ages == [15]

    def test_ages_no_story_age(self):
        """age_at_storyがNoneの場合"""
        milestones = [_make_milestone(age=25, events=["偉業"])]
        char = _make_character(age_at_story=None, age_milestones=milestones)
        mock_kb = _make_mock_kb(character=char)
        enhancer = CanonPromptEnhancer(canon_kb=mock_kb)

        ages = enhancer.get_available_ages("テスト", "テスト作品")

        assert ages == [25]
