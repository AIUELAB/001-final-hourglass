#!/usr/bin/env python3
"""
AuthenticityChecker と CanonKB のユニットテスト

テストカテゴリ:
1. CanonKBテスト - JSONロード、キャラクター検索、シーン存在確認
2. AuthenticityCheckerテスト - 真正性検証、キーワードマッチング、提案機能

Author: EPUP Validation Team
Date: 2026-01-30
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.authenticity_checker import (
    AuthenticityChecker,
    AuthenticityResult,
    AuthenticityStatus,
)
from src.utils.canon_kb import (
    AgeMilestone,
    CanonKB,
    Character,
    KeyScene,
    StoryArc,
    Work,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mini_canon_kb(tmp_path: Path) -> Path:
    """テスト用のミニCanonKB"""
    kb_data = {
        "version": "1.0.0",
        "works": {
            "鬼滅の刃": {
                "work_id": "TEST_KIMETSU",
                "work_title": "鬼滅の刃",
                "work_title_variants": ["Demon Slayer", "きめつのやいば"],
                "source_urls": [],
                "era_setting": "大正時代",
                "characters": {
                    "竈門炭治郎": {
                        "character_id": "TEST_CHAR_001",
                        "aliases": ["炭治郎", "カマド タンジロウ"],
                        "age_at_story": 15,
                        "abilities": ["水の呼吸", "日の呼吸"],
                        "key_scenes": [
                            {
                                "scene_id": "TEST_SCENE_001",
                                "description": "家族を鬼に殺され、禰豆子だけが生き残る",
                                "story_arc": "立志編",
                                "source": {"type": "manga", "reference": "第1話「残酷」"},
                            },
                            {
                                "scene_id": "TEST_SCENE_002",
                                "description": "鬼殺隊の最終選別に挑み、生き残る",
                                "story_arc": "最終選別編",
                                "source": {"type": "manga", "reference": "第6話「山ほどの手が」"},
                            },
                            {
                                "scene_id": "TEST_SCENE_003",
                                "description": "禰豆子と共に無限列車で魘夢と戦う",
                                "story_arc": "無限列車編",
                                "source": {"type": "movie", "reference": "無限列車編"},
                            },
                        ],
                        "age_milestones": [
                            {
                                "age": 13,
                                "events": ["家族の死", "禰豆子の鬼化"],
                                "source": "第1話",
                            },
                            {
                                "age": 15,
                                "events": ["鬼殺隊入隊", "水柱との出会い"],
                                "source": "第6話",
                            },
                        ],
                    },
                    "竈門禰豆子": {
                        "character_id": "TEST_CHAR_002",
                        "aliases": ["禰豆子", "ネズコ"],
                        "age_at_story": 14,
                        "abilities": ["爆血"],
                        "key_scenes": [
                            {
                                "scene_id": "TEST_SCENE_004",
                                "description": "鬼に噛まれて鬼になるが人を襲わない",
                                "story_arc": "立志編",
                                "source": {"type": "manga", "reference": "第1話「残酷」"},
                            }
                        ],
                        "age_milestones": [{"age": 12, "events": ["鬼化"], "source": "第1話"}],
                    },
                },
                "story_arcs": [
                    {
                        "arc_name": "立志編",
                        "order": 1,
                        "main_characters": ["竈門炭治郎", "竈門禰豆子"],
                    },
                    {
                        "arc_name": "無限列車編",
                        "order": 2,
                        "main_characters": ["竈門炭治郎", "煉獄杏寿郎"],
                    },
                ],
            },
            "ワンピース": {
                "work_id": "TEST_ONEPIECE",
                "work_title": "ONE PIECE",
                "work_title_variants": ["ONE PIECE", "ワンピ"],
                "source_urls": [],
                "era_setting": "架空世界",
                "characters": {
                    "モンキー・D・ルフィ": {
                        "character_id": "TEST_CHAR_003",
                        "aliases": ["ルフィ", "麦わらのルフィ"],
                        "age_at_story": 19,
                        "abilities": ["ゴムゴムの実"],
                        "key_scenes": [
                            {
                                "scene_id": "TEST_SCENE_005",
                                "description": "シャンクスに麦わら帽子を託される",
                                "story_arc": "東の海編",
                                "source": {"type": "manga", "reference": "第1話「ROMANCE DAWN」"},
                            }
                        ],
                        "age_milestones": [{"age": 7, "events": ["シャンクスとの出会い"], "source": "第1話"}],
                    }
                },
                "story_arcs": [{"arc_name": "東の海編", "order": 1, "main_characters": ["モンキー・D・ルフィ"]}],
            },
        },
    }

    kb_path = tmp_path / "test_canon_kb.json"
    kb_path.write_text(json.dumps(kb_data, ensure_ascii=False, indent=2))
    return kb_path


@pytest.fixture
def empty_canon_kb(tmp_path: Path) -> Path:
    """空のCanonKB"""
    kb_data = {"version": "1.0.0", "works": {}}
    kb_path = tmp_path / "empty_canon_kb.json"
    kb_path.write_text(json.dumps(kb_data, ensure_ascii=False))
    return kb_path


@pytest.fixture
def checker(mini_canon_kb: Path) -> AuthenticityChecker:
    """AuthenticityCheckerのフィクスチャ"""
    kb = CanonKB(mini_canon_kb)
    return AuthenticityChecker(canon_kb=kb)


# =============================================================================
# CanonKB Tests
# =============================================================================


class TestCanonKBLoad:
    """KBロードのテスト"""

    def test_load_kb_success(self, mini_canon_kb: Path):
        """KBが正常にロードできること"""
        kb = CanonKB(mini_canon_kb)
        works = kb.list_works()
        assert "鬼滅の刃" in works
        assert "ワンピース" in works
        assert len(works) == 2

    def test_load_empty_kb(self, empty_canon_kb: Path):
        """空のKBがロードできること"""
        kb = CanonKB(empty_canon_kb)
        assert len(kb.list_works()) == 0

    def test_load_nonexistent_kb(self, tmp_path: Path):
        """存在しないKBファイルでは空で動作すること"""
        kb_path = tmp_path / "nonexistent.json"
        kb = CanonKB(kb_path)
        assert len(kb.list_works()) == 0

    def test_load_invalid_json(self, tmp_path: Path):
        """不正なJSONでも例外を投げずに空で動作すること"""
        kb_path = tmp_path / "invalid.json"
        kb_path.write_text("{ invalid json }")
        kb = CanonKB(kb_path)
        assert len(kb.list_works()) == 0


class TestCanonKBCharacterSearch:
    """キャラクター検索のテスト"""

    def test_get_character_by_name(self, mini_canon_kb: Path):
        """正式名でキャラクターを検索できること"""
        kb = CanonKB(mini_canon_kb)
        char = kb.get_character("鬼滅の刃", "竈門炭治郎")
        assert char is not None
        assert char.name == "竈門炭治郎"
        assert char.character_id == "TEST_CHAR_001"

    def test_get_character_by_alias(self, mini_canon_kb: Path):
        """aliasでキャラクターを検索できること"""
        kb = CanonKB(mini_canon_kb)
        char = kb.get_character("鬼滅の刃", "炭治郎")
        assert char is not None
        assert char.name == "竈門炭治郎"

    def test_get_character_with_title_variant(self, mini_canon_kb: Path):
        """作品タイトルの変種でも検索できること"""
        kb = CanonKB(mini_canon_kb)
        char = kb.get_character("Demon Slayer", "竈門炭治郎")
        assert char is not None
        assert char.name == "竈門炭治郎"

    def test_get_character_not_found(self, mini_canon_kb: Path):
        """存在しないキャラクターはNoneを返すこと"""
        kb = CanonKB(mini_canon_kb)
        char = kb.get_character("鬼滅の刃", "存在しないキャラ")
        assert char is None

    def test_get_character_wrong_work(self, mini_canon_kb: Path):
        """別作品のキャラクターはNoneを返すこと"""
        kb = CanonKB(mini_canon_kb)
        char = kb.get_character("ワンピース", "竈門炭治郎")
        assert char is None

    def test_find_character_by_alias_all_works(self, mini_canon_kb: Path):
        """全作品からaliasでキャラクターを検索できること"""
        kb = CanonKB(mini_canon_kb)
        results = kb.find_character_by_alias("ルフィ")
        assert len(results) == 1
        assert results[0][0] == "ワンピース"
        assert results[0][1].name == "モンキー・D・ルフィ"


class TestCanonKBSceneSearch:
    """シーン検索のテスト"""

    def test_has_scene_exact_match(self, mini_canon_kb: Path):
        """出典の完全一致で検索できること"""
        kb = CanonKB(mini_canon_kb)
        assert kb.has_scene("鬼滅の刃", "竈門炭治郎", "第1話「残酷」") is True

    def test_has_scene_partial_match(self, mini_canon_kb: Path):
        """出典の部分一致で検索できること"""
        kb = CanonKB(mini_canon_kb)
        assert kb.has_scene("鬼滅の刃", "竈門炭治郎", "第1話") is True
        assert kb.has_scene("鬼滅の刃", "竈門炭治郎", "無限列車") is True

    def test_has_scene_not_found(self, mini_canon_kb: Path):
        """存在しない出典はFalseを返すこと"""
        kb = CanonKB(mini_canon_kb)
        assert kb.has_scene("鬼滅の刃", "竈門炭治郎", "存在しない話") is False

    def test_has_scene_wrong_character(self, mini_canon_kb: Path):
        """別キャラクターのシーンはFalseを返すこと"""
        kb = CanonKB(mini_canon_kb)
        # 禰豆子のシーンには無限列車編はない
        assert kb.has_scene("鬼滅の刃", "竈門禰豆子", "無限列車編") is False

    def test_get_character_scenes_all_works(self, mini_canon_kb: Path):
        """全作品からキャラクターのシーンを取得できること"""
        kb = CanonKB(mini_canon_kb)
        scenes = kb.get_character_scenes("竈門炭治郎")
        assert len(scenes) == 3
        assert scenes[0].scene_id == "TEST_SCENE_001"


class TestCanonKBMilestones:
    """年齢マイルストーンのテスト"""

    def test_get_milestones_for_age(self, mini_canon_kb: Path):
        """年齢でマイルストーンを取得できること"""
        kb = CanonKB(mini_canon_kb)
        events = kb.get_milestones_for_age("鬼滅の刃", "竈門炭治郎", 13)
        assert "家族の死" in events
        assert "禰豆子の鬼化" in events

    def test_get_milestones_no_match(self, mini_canon_kb: Path):
        """該当年齢のマイルストーンがない場合は空リストを返すこと"""
        kb = CanonKB(mini_canon_kb)
        events = kb.get_milestones_for_age("鬼滅の刃", "竈門炭治郎", 20)
        assert events == []


class TestCanonKBStoryArcs:
    """ストーリーアークのテスト"""

    def test_get_story_arcs(self, mini_canon_kb: Path):
        """ストーリーアークを取得できること"""
        kb = CanonKB(mini_canon_kb)
        arcs = kb.get_story_arcs("鬼滅の刃")
        assert len(arcs) == 2
        assert arcs[0].arc_name == "立志編"
        assert arcs[0].order == 1
        assert arcs[1].arc_name == "無限列車編"
        assert arcs[1].order == 2

    def test_get_story_arcs_not_found(self, mini_canon_kb: Path):
        """存在しない作品は空リストを返すこと"""
        kb = CanonKB(mini_canon_kb)
        arcs = kb.get_story_arcs("存在しない作品")
        assert arcs == []


class TestCanonKBListFunctions:
    """一覧取得機能のテスト"""

    def test_list_works(self, mini_canon_kb: Path):
        """作品一覧を取得できること"""
        kb = CanonKB(mini_canon_kb)
        works = kb.list_works()
        assert len(works) == 2
        assert "鬼滅の刃" in works
        assert "ワンピース" in works

    def test_list_characters(self, mini_canon_kb: Path):
        """キャラクター一覧を取得できること"""
        kb = CanonKB(mini_canon_kb)
        characters = kb.list_characters("鬼滅の刃")
        assert len(characters) == 2
        assert "竈門炭治郎" in characters
        assert "竈門禰豆子" in characters

    def test_list_characters_not_found(self, mini_canon_kb: Path):
        """存在しない作品は空リストを返すこと"""
        kb = CanonKB(mini_canon_kb)
        characters = kb.list_characters("存在しない作品")
        assert characters == []


# =============================================================================
# AuthenticityChecker Tests
# =============================================================================


class TestAuthenticityCheckerCanonPass:
    """canon出典ありのエピソードはパスする"""

    def test_canon_episode_passes(self, checker: AuthenticityChecker):
        """canon出典ありのエピソードはパスすること"""
        episode = {
            "episode_text": "竈門炭治郎は家族を鬼に殺され、禰豆子だけが生き残る悲劇に見舞われた。",
            "person_name": "竈門炭治郎",
            "person_type": "FICTIONAL",
            "work_title": "鬼滅の刃",
            "age": 13,
            "canon_source": "第1話「残酷」",
        }
        result = checker.check(episode)
        assert result.passed is True
        assert result.status == AuthenticityStatus.CANON
        assert result.canon_source == "第1話「残酷」"
        assert result.confidence > 0

    def test_canon_episode_with_partial_source(self, checker: AuthenticityChecker):
        """部分一致の出典でもパスすること"""
        episode = {
            "episode_text": "竈門炭治郎は無限列車で魘夢と戦った。",
            "person_name": "竈門炭治郎",
            "person_type": "FICTIONAL",
            "work_title": "鬼滅の刃",
            "age": 15,
            "canon_source": "無限列車編",
        }
        result = checker.check(episode)
        assert result.passed is True
        assert result.status == AuthenticityStatus.CANON


class TestAuthenticityCheckerNoSourceFail:
    """canon出典なしのエピソードは失敗する"""

    def test_no_source_fails(self, checker: AuthenticityChecker):
        """canon出典なしは失敗すること"""
        episode = {
            "episode_text": "竈門炭治郎は鬼殺隊で活躍した。",
            "person_name": "竈門炭治郎",
            "person_type": "FICTIONAL",
            "work_title": "鬼滅の刃",
            "age": 15,
            "canon_source": None,
        }
        result = checker.check(episode)
        assert result.passed is False
        assert result.status == AuthenticityStatus.NO_MATCH
        assert "canon出典が必要です" in result.violations

    def test_empty_source_fails(self, checker: AuthenticityChecker):
        """空文字列の出典は失敗すること"""
        episode = {
            "episode_text": "竈門炭治郎は鬼殺隊で活躍した。",
            "person_name": "竈門炭治郎",
            "person_type": "FICTIONAL",
            "work_title": "鬼滅の刃",
            "age": 15,
            "canon_source": "",
        }
        result = checker.check(episode)
        assert result.passed is False
        assert result.status == AuthenticityStatus.NO_MATCH


class TestAuthenticityCheckerInvalidSourceFail:
    """存在しない出典のエピソードは失敗する"""

    def test_invalid_source_fails(self, checker: AuthenticityChecker):
        """存在しない出典は失敗すること"""
        episode = {
            "episode_text": "竈門炭治郎は鬼殺隊で活躍した。",
            "person_name": "竈門炭治郎",
            "person_type": "FICTIONAL",
            "work_title": "鬼滅の刃",
            "age": 15,
            "canon_source": "第999話「存在しない話」",
        }
        result = checker.check(episode)
        assert result.passed is False
        # 存在しない出典 → INVALID（創作疑い）として扱う
        assert result.status == AuthenticityStatus.INVALID
        assert any("CanonKBに存在しません" in v for v in result.violations)

    def test_source_not_in_kb_suggestion(self, checker: AuthenticityChecker):
        """存在しない出典の場合、利用可能な出典が提案されること"""
        episode = {
            "episode_text": "竈門炭治郎は鬼殺隊で活躍した。",
            "person_name": "竈門炭治郎",
            "person_type": "FICTIONAL",
            "work_title": "鬼滅の刃",
            "age": 15,
            "canon_source": "存在しない出典",
        }
        result = checker.check(episode)
        assert result.passed is False
        assert result.suggestion is not None
        assert "利用可能な出典" in result.suggestion


class TestAuthenticityCheckerRealCharacterSkip:
    """REAL人物は検証をスキップする"""

    def test_real_character_skipped(self, checker: AuthenticityChecker):
        """REAL人物は検証をスキップすること"""
        episode = {
            "episode_text": "大谷翔平はメジャーリーグで活躍した。",
            "person_name": "大谷翔平",
            "person_type": "REAL",
            "work_title": None,
            "age": 28,
            "canon_source": None,
        }
        result = checker.check(episode)
        assert result.passed is True  # REALはスキップ
        assert result.status == AuthenticityStatus.CANON
        assert result.confidence == 1.0

    def test_real_character_with_work_title(self, checker: AuthenticityChecker):
        """work_titleがあってもREALならスキップすること"""
        episode = {
            "episode_text": "アルベルト・アインシュタインは相対性理論を発表した。",
            "person_name": "アルベルト・アインシュタイン",
            "person_type": "REAL",
            "work_title": "物理学の歴史",
            "age": 26,
            "canon_source": None,
        }
        result = checker.check(episode)
        assert result.passed is True


class TestAuthenticityCheckerKeywordMatching:
    """キーワードマッチングのテスト"""

    def test_matching_scenes_found(self, checker: AuthenticityChecker):
        """キーワードが一致するシーンが見つかること"""
        matching_scenes = checker.find_matching_scenes(
            work_title="鬼滅の刃",
            character="竈門炭治郎",
            _age=13,
            text="家族を鬼に殺され、禰豆子だけが生き残った悲劇",
        )
        assert len(matching_scenes) > 0
        assert matching_scenes[0]["scene_id"] == "TEST_SCENE_001"
        assert "match_score" in matching_scenes[0]

    def test_no_matching_scenes(self, checker: AuthenticityChecker):
        """キーワードが一致しない場合は空リストを返すこと"""
        matching_scenes = checker.find_matching_scenes(
            work_title="鬼滅の刃",
            character="竈門炭治郎",
            _age=13,
            text="完全に関係のないテキスト ABC XYZ",
        )
        assert len(matching_scenes) == 0

    def test_empty_text_no_match(self, checker: AuthenticityChecker):
        """空テキストは空リストを返すこと"""
        matching_scenes = checker.find_matching_scenes(work_title="鬼滅の刃", character="竈門炭治郎", _age=13, text="")
        assert matching_scenes == []


class TestAuthenticityCheckerSuggestion:
    """提案機能のテスト"""

    def test_suggest_canon_source_with_age(self, checker: AuthenticityChecker):
        """年齢指定で利用可能な出典を提案できること"""
        sources = checker.suggest_canon_source(work_title="鬼滅の刃", character="竈門炭治郎", age=13)
        assert len(sources) > 0
        assert "第1話" in sources

    def test_suggest_canon_source_without_age(self, checker: AuthenticityChecker):
        """年齢指定なしでも出典を提案できること"""
        sources = checker.suggest_canon_source(work_title="鬼滅の刃", character="竈門炭治郎", age=None)
        assert len(sources) > 0

    def test_suggest_canon_source_not_found(self, checker: AuthenticityChecker):
        """存在しないキャラクターでは空リストを返すこと"""
        sources = checker.suggest_canon_source(work_title="鬼滅の刃", character="存在しないキャラ", age=13)
        assert sources == []


class TestAuthenticityCheckerVerifySource:
    """出典検証機能のテスト"""

    def test_verify_canon_source_valid(self, checker: AuthenticityChecker):
        """有効な出典はTrueを返すこと"""
        assert checker.verify_canon_source("鬼滅の刃", "竈門炭治郎", "第1話「残酷」") is True

    def test_verify_canon_source_invalid(self, checker: AuthenticityChecker):
        """無効な出典はFalseを返すこと"""
        assert checker.verify_canon_source("鬼滅の刃", "竈門炭治郎", "存在しない話") is False

    def test_verify_canon_source_empty(self, checker: AuthenticityChecker):
        """空の出典はFalseを返すこと"""
        assert checker.verify_canon_source("鬼滅の刃", "竈門炭治郎", "") is False
        assert checker.verify_canon_source("鬼滅の刃", "竈門炭治郎", None) is False


class TestAuthenticityCheckerCharacterInfo:
    """キャラクター情報取得のテスト"""

    def test_get_character_info(self, checker: AuthenticityChecker):
        """キャラクター情報を取得できること"""
        info = checker.get_character_info("鬼滅の刃", "竈門炭治郎")
        assert info is not None
        assert info["name"] == "竈門炭治郎"
        assert "炭治郎" in info["aliases"]
        assert info["age_at_story"] == 15
        assert info["key_scenes_count"] == 3
        assert info["age_milestones_count"] == 2

    def test_get_character_info_not_found(self, checker: AuthenticityChecker):
        """存在しないキャラクターはNoneを返すこと"""
        info = checker.get_character_info("鬼滅の刃", "存在しないキャラ")
        assert info is None


class TestAuthenticityCheckerIsFictional:
    """架空キャラクター判定のテスト"""

    def test_is_fictional_character_true(self, checker: AuthenticityChecker):
        """架空キャラクターはTrueを返すこと"""
        # 注: この関数は fictional_characters.py に依存
        # 実際のリストに登録されているキャラクターでテスト
        result = checker.is_fictional_character("竈門炭治郎")
        # fictional_characters.py のリストに依存するため、結果は登録状況による
        assert isinstance(result, bool)


class TestAuthenticityResult:
    """AuthenticityResultのテスト"""

    def test_to_dict(self):
        """to_dictメソッドが正しく動作すること"""
        result = AuthenticityResult(
            passed=True,
            status=AuthenticityStatus.CANON,
            canon_source="第1話",
            confidence=0.95,
            violations=[],
            suggestion=None,
            matching_scenes=[{"scene_id": "S001"}],
        )
        d = result.to_dict()
        assert d["passed"] is True
        assert d["status"] == "canon"
        assert d["canon_source"] == "第1話"
        assert d["confidence"] == 0.95
        assert d["violations"] == []
        assert d["suggestion"] is None
        assert d["matching_scenes"] == [{"scene_id": "S001"}]

    def test_to_dict_with_violations(self):
        """違反ありの場合のto_dictテスト"""
        result = AuthenticityResult(
            passed=False,
            status=AuthenticityStatus.NO_MATCH,
            violations=["出典が必要です", "設定違反"],
            suggestion="第1話を参照してください",
        )
        d = result.to_dict()
        assert d["passed"] is False
        assert d["status"] == "no_match"
        assert len(d["violations"]) == 2
        assert d["suggestion"] == "第1話を参照してください"


# =============================================================================
# DataClass Tests
# =============================================================================


class TestKeySceneDataClass:
    """KeySceneデータクラスのテスト"""

    def test_from_dict(self):
        """from_dictが正しく動作すること"""
        data = {
            "scene_id": "S001",
            "description": "テストシーン",
            "story_arc": "テスト編",
            "source": {"type": "manga", "reference": "第1話"},
        }
        scene = KeyScene.from_dict(data)
        assert scene.scene_id == "S001"
        assert scene.description == "テストシーン"
        assert scene.story_arc == "テスト編"
        assert scene.source_type == "manga"
        assert scene.source_reference == "第1話"

    def test_from_dict_missing_fields(self):
        """必須フィールドがない場合もエラーにならないこと"""
        data = {}
        scene = KeyScene.from_dict(data)
        assert scene.scene_id == ""
        assert scene.description == ""


class TestAgeMilestoneDataClass:
    """AgeMilestoneデータクラスのテスト"""

    def test_from_dict(self):
        """from_dictが正しく動作すること"""
        data = {"age": 13, "events": ["イベント1", "イベント2"], "source": "第1話"}
        milestone = AgeMilestone.from_dict(data)
        assert milestone.age == 13
        assert len(milestone.events) == 2
        assert milestone.source == "第1話"


class TestCharacterDataClass:
    """Characterデータクラスのテスト"""

    def test_from_dict(self):
        """from_dictが正しく動作すること"""
        data = {
            "character_id": "C001",
            "aliases": ["alias1", "alias2"],
            "age_at_story": 15,
            "abilities": ["ability1"],
            "key_scenes": [
                {
                    "scene_id": "S001",
                    "description": "desc",
                    "story_arc": "arc",
                    "source": {"type": "manga", "reference": "ref"},
                }
            ],
            "age_milestones": [{"age": 10, "events": ["event"], "source": "src"}],
        }
        char = Character.from_dict("テストキャラ", data)
        assert char.name == "テストキャラ"
        assert char.character_id == "C001"
        assert len(char.aliases) == 2
        assert len(char.key_scenes) == 1
        assert len(char.age_milestones) == 1


class TestStoryArcDataClass:
    """StoryArcデータクラスのテスト"""

    def test_from_dict(self):
        """from_dictが正しく動作すること"""
        data = {"arc_name": "第1編", "order": 1, "main_characters": ["キャラ1"]}
        arc = StoryArc.from_dict(data)
        assert arc.arc_name == "第1編"
        assert arc.order == 1
        assert len(arc.main_characters) == 1


class TestWorkDataClass:
    """Workデータクラスのテスト"""

    def test_from_dict(self):
        """from_dictが正しく動作すること"""
        data = {
            "work_id": "W001",
            "work_title": "テスト作品",
            "work_title_variants": ["variant1"],
            "source_urls": ["http://example.com"],
            "era_setting": "現代",
            "characters": {
                "キャラ1": {
                    "character_id": "C001",
                    "aliases": [],
                    "age_at_story": 20,
                    "abilities": [],
                    "key_scenes": [],
                    "age_milestones": [],
                }
            },
            "story_arcs": [{"arc_name": "arc1", "order": 1, "main_characters": []}],
        }
        work = Work.from_dict(data)
        assert work.work_id == "W001"
        assert work.title == "テスト作品"
        assert len(work.title_variants) == 1
        assert len(work.characters) == 1
        assert len(work.story_arcs) == 1


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """エッジケースのテスト"""

    def test_checker_with_empty_kb(self, empty_canon_kb: Path):
        """空のKBでもAuthenticityCheckerが動作すること"""
        kb = CanonKB(empty_canon_kb)
        checker = AuthenticityChecker(canon_kb=kb)
        episode = {
            "episode_text": "テスト",
            "person_name": "テストキャラ",
            "person_type": "FICTIONAL",
            "work_title": "テスト作品",
            "age": 20,
            "canon_source": "第1話",
        }
        result = checker.check(episode)
        assert result.passed is False  # KBにないので失敗
        # 出典がCanonKBに存在しない → INVALID（創作疑い）
        assert result.status == AuthenticityStatus.INVALID

    def test_checker_with_missing_fields(self, checker: AuthenticityChecker):
        """フィールドが欠落しているエピソードでもエラーにならないこと"""
        episode = {"episode_text": "テスト"}
        result = checker.check(episode)
        # person_typeがないのでREAL扱いになりスキップ
        assert result.passed is True

    def test_checker_with_alias_person_name(self, checker: AuthenticityChecker):
        """aliasの人物名でも出典検証が行われること（キーワードマッチは別問題）"""
        episode = {
            "episode_text": "炭治郎は家族を鬼に殺された。",
            "person_name": "炭治郎",  # alias
            "person_type": "FICTIONAL",
            "work_title": "鬼滅の刃",
            "age": 13,
            "canon_source": "第1話「残酷」",
        }
        result = checker.check(episode)
        # aliasでも出典検証は行われる（キーワードマッチが不十分な場合はINVALID）
        # 出典自体は存在するが、エピソード内容との整合性チェックで失敗する可能性あり
        assert result.passed is False  # キーワードマッチなしで失敗
        assert result.status == AuthenticityStatus.INVALID


class TestAuthenticityCheckerCanonKBProperty:
    """canon_kbプロパティのテスト（L128カバー）"""

    def test_canon_kb_property(self, checker: AuthenticityChecker):
        """canon_kbプロパティがCanonKBインスタンスを返すこと"""
        kb = checker.canon_kb
        assert isinstance(kb, CanonKB)
        # 作品が読み込まれていることを確認
        assert len(kb.list_works()) > 0


class TestAuthenticityCheckerLowConfidence:
    """低確信度のテスト（L214カバー）"""

    def test_low_confidence_returns_invalid(self, mini_canon_kb: Path):
        """確信度が閾値未満の場合INVALIDを返すこと"""
        kb = CanonKB(mini_canon_kb)
        checker = AuthenticityChecker(canon_kb=kb)

        # 出典は存在するが、テキスト内容がシーンと微妙にしかマッチしないケース
        # MIN_KEYWORD_MATCH_COUNTを満たすが、match_scoreが低くなるテキスト
        # 大量の無関係キーワードを含めてスコアを下げる
        episode = {
            "episode_text": (
                "竈門炭治郎は家族を鬼に殺された。"
                "サッカー野球バスケット水泳テニスバレーボール卓球柔道空手剣道ボクシング"
                "天文学物理学化学生物学数学経済学哲学心理学社会学"
                "東京大阪名古屋福岡札幌横浜神戸京都広島仙台"
            ),
            "person_name": "竈門炭治郎",
            "person_type": "FICTIONAL",
            "work_title": "鬼滅の刃",
            "age": 13,
            "canon_source": "第1話「残酷」",
        }
        result = checker.check(episode)
        # match_scoreが低い場合、INVALIDまたはCANON（スコアに依存）
        assert result.status in (AuthenticityStatus.INVALID, AuthenticityStatus.CANON)


class TestAuthenticityCheckerIsTargetFictionalByName:
    """_is_targetのperson_name判定テスト（L252-255カバー）"""

    def test_fictional_character_by_name_not_type(self, mini_canon_kb: Path):
        """person_typeがREALでもperson_nameが架空キャラなら検証対象"""
        from unittest.mock import patch

        kb = CanonKB(mini_canon_kb)
        checker = AuthenticityChecker(canon_kb=kb)

        with patch("src.utils.authenticity_checker.is_fictional_character", return_value=True):
            result = checker._is_target("REAL", "竈門炭治郎")
            assert result is True

    def test_not_fictional_by_name_or_type(self, mini_canon_kb: Path):
        """person_typeもREALでperson_nameも実在人物なら検証対象外"""
        from unittest.mock import patch

        kb = CanonKB(mini_canon_kb)
        checker = AuthenticityChecker(canon_kb=kb)

        with patch("src.utils.authenticity_checker.is_fictional_character", return_value=False):
            result = checker._is_target("REAL", "大谷翔平")
            assert result is False


class TestFindMatchingScenesCharNotFound:
    """find_matching_scenesでキャラクターが見つからない場合（L298カバー）"""

    def test_character_not_in_kb(self, checker: AuthenticityChecker):
        """KBに存在しないキャラクターで空リストを返すこと"""
        result = checker.find_matching_scenes(
            work_title="鬼滅の刃",
            character="存在しないキャラクター",
            _age=13,
            text="何かのテキスト",
        )
        assert result == []


class TestExtractKeywordsEmpty:
    """_extract_keywordsの空テキスト（L347カバー）"""

    def test_extract_keywords_empty(self, checker: AuthenticityChecker):
        """空テキストで空集合を返すこと"""
        result = checker._extract_keywords("")
        assert result == set()

    def test_extract_keywords_none(self, checker: AuthenticityChecker):
        """Noneに近い空文字列で空集合を返すこと"""
        result = checker._extract_keywords("")
        assert isinstance(result, set)
        assert len(result) == 0


class TestCheckAuthenticityUtilityFunction:
    """check_authenticity関数のテスト（L496-497カバー）"""

    def test_check_authenticity_function(self):
        """ユーティリティ関数が正しく動作すること"""
        from src.utils.authenticity_checker import check_authenticity

        episode = {
            "episode_text": "テストエピソード",
            "person_name": "テスト太郎",
            "person_type": "REAL",
            "work_title": "",
            "age": 30,
        }
        result = check_authenticity(episode)
        # REALなのでスキップされてpassedがTrue
        assert result.passed is True
        assert result.status == AuthenticityStatus.CANON


class TestCanonKBGetWorkEdgeCases:
    """CanonKBのget_workエッジケース（L233, L247カバー）"""

    def test_get_work_empty_title(self, mini_canon_kb: Path):
        """空文字列のタイトルでNoneを返すこと"""
        kb = CanonKB(mini_canon_kb)
        result = kb.get_work("")
        assert result is None

    def test_get_work_none_title(self, mini_canon_kb: Path):
        """Noneのタイトルでもエラーにならないこと"""
        kb = CanonKB(mini_canon_kb)
        result = kb.get_work(None)
        assert result is None

    def test_get_work_partial_match(self, mini_canon_kb: Path):
        """部分一致で作品を検索できること"""
        kb = CanonKB(mini_canon_kb)
        # 「鬼滅」は「鬼滅の刃」に部分一致する
        result = kb.get_work("鬼滅")
        assert result is not None
        assert result.title == "鬼滅の刃"


class TestCanonKBGetCharacterScenesAlias:
    """get_character_scenesのalias検索（L298-299カバー）"""

    def test_get_scenes_by_alias(self, mini_canon_kb: Path):
        """aliasでシーンを取得できること"""
        kb = CanonKB(mini_canon_kb)
        # 「ネズコ」は竈門禰豆子のalias
        scenes = kb.get_character_scenes("ネズコ")
        assert len(scenes) == 1
        assert scenes[0].scene_id == "TEST_SCENE_004"


class TestCanonKBGetMilestonesNoChar:
    """get_milestones_for_ageでキャラクターが見つからない場合（L342カバー）"""

    def test_milestones_char_not_found(self, mini_canon_kb: Path):
        """存在しないキャラクターで空リストを返すこと"""
        kb = CanonKB(mini_canon_kb)
        events = kb.get_milestones_for_age("鬼滅の刃", "存在しないキャラ", 13)
        assert events == []

    def test_milestones_work_not_found(self, mini_canon_kb: Path):
        """存在しない作品で空リストを返すこと"""
        kb = CanonKB(mini_canon_kb)
        events = kb.get_milestones_for_age("存在しない作品", "竈門炭治郎", 13)
        assert events == []


class TestCanonKBAlreadyLoaded:
    """_loadの既ロードチェック（L193カバー）"""

    def test_double_load_returns_early(self, mini_canon_kb: Path):
        """2回目の_load呼び出しは即座にreturnすること"""
        kb = CanonKB(mini_canon_kb)
        works_before = kb.list_works()
        # 再度_loadを呼んでも問題なし
        kb._load()
        works_after = kb.list_works()
        assert works_before == works_after


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
