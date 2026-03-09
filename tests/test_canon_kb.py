"""
tests/test_canon_kb.py - CanonKB ユニットテスト

CanonKBの未カバー行をカバーするテスト:
- L193: _load の既ロードチェック
- L233: get_work の空文字列タイトル
- L247: get_work の部分一致検索
- L298-299: get_character_scenes の alias 検索
- L342: get_milestones_for_age でキャラクター未発見
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.utils.canon_kb import CanonKB


@pytest.fixture
def mini_kb_path(tmp_path: Path) -> Path:
    """テスト用ミニKBファイルを作成"""
    kb_data = {
        "version": "1.0.0",
        "works": {
            "テスト作品": {
                "work_id": "W001",
                "work_title": "テスト作品",
                "work_title_variants": ["Test Work", "テスト"],
                "source_urls": [],
                "era_setting": "現代",
                "characters": {
                    "主人公太郎": {
                        "character_id": "C001",
                        "aliases": ["太郎", "タロウ"],
                        "age_at_story": 20,
                        "abilities": ["能力A"],
                        "key_scenes": [
                            {
                                "scene_id": "S001",
                                "description": "太郎が旅立つシーン",
                                "story_arc": "序章",
                                "source": {"type": "manga", "reference": "第1話"},
                            }
                        ],
                        "age_milestones": [
                            {
                                "age": 15,
                                "events": ["覚醒イベント"],
                                "source": "第5話",
                            }
                        ],
                    }
                },
                "story_arcs": [
                    {
                        "arc_name": "序章",
                        "order": 1,
                        "main_characters": ["主人公太郎"],
                    }
                ],
            }
        },
    }
    kb_path = tmp_path / "test_kb.json"
    kb_path.write_text(json.dumps(kb_data, ensure_ascii=False, indent=2))
    return kb_path


class TestCanonKBLoadAlreadyLoaded:
    """_load の既ロードチェック（L193カバー）"""

    def test_load_skips_when_already_loaded(self, mini_kb_path: Path):
        """一度ロード済みの場合、再ロードをスキップすること"""
        kb = CanonKB(mini_kb_path)
        assert kb._loaded is True

        # _loadを再度呼び出し
        kb._load()
        # 正常に動作し、データが変わらないこと
        assert len(kb.list_works()) == 1


class TestCanonKBGetWorkEmptyTitle:
    """get_work の空文字列タイトル（L233カバー）"""

    def test_get_work_empty_string(self, mini_kb_path: Path):
        """空文字列でNoneを返すこと"""
        kb = CanonKB(mini_kb_path)
        result = kb.get_work("")
        assert result is None

    def test_get_work_none(self, mini_kb_path: Path):
        """Noneでエラーにならないこと"""
        kb = CanonKB(mini_kb_path)
        result = kb.get_work(None)
        assert result is None


class TestCanonKBGetWorkPartialMatch:
    """get_work の部分一致検索（L247カバー）"""

    def test_get_work_partial_match_title_in_query(self, mini_kb_path: Path):
        """クエリが作品名を含む場合に部分一致で見つかること"""
        kb = CanonKB(mini_kb_path)
        # 「テスト作品改」はDB上の「テスト作品」を含む → 部分一致
        result = kb.get_work("テスト作品改")
        assert result is not None
        assert result.title == "テスト作品"

    def test_get_work_partial_match_query_in_title(self, mini_kb_path: Path):
        """作品名がクエリを含む場合に部分一致で見つかること"""
        kb = CanonKB(mini_kb_path)
        # 「テスト」は variant に登録されているが、完全一致で先にマッチ
        # 別のクエリで部分一致を検証
        result = kb.get_work("作品")
        assert result is not None
        assert result.title == "テスト作品"


class TestCanonKBGetCharacterScenesAlias:
    """get_character_scenes の alias 検索（L298-299カバー）"""

    def test_get_scenes_via_alias(self, mini_kb_path: Path):
        """aliasでシーンを取得できること"""
        kb = CanonKB(mini_kb_path)
        # 「タロウ」は主人公太郎のalias
        scenes = kb.get_character_scenes("タロウ")
        assert len(scenes) == 1
        assert scenes[0].scene_id == "S001"

    def test_get_scenes_no_alias_match(self, mini_kb_path: Path):
        """どのaliasにもマッチしない場合空リストを返すこと"""
        kb = CanonKB(mini_kb_path)
        scenes = kb.get_character_scenes("存在しない名前")
        assert scenes == []


class TestCanonKBMilestonesCharNotFound:
    """get_milestones_for_age でキャラクター未発見（L342カバー）"""

    def test_milestones_character_not_found(self, mini_kb_path: Path):
        """存在しないキャラクターで空リストを返すこと"""
        kb = CanonKB(mini_kb_path)
        events = kb.get_milestones_for_age("テスト作品", "存在しないキャラ", 15)
        assert events == []

    def test_milestones_work_not_found(self, mini_kb_path: Path):
        """存在しない作品で空リストを返すこと"""
        kb = CanonKB(mini_kb_path)
        events = kb.get_milestones_for_age("存在しない作品", "主人公太郎", 15)
        assert events == []
