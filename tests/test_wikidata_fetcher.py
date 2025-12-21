"""
WikidataFetcher テストモジュール

wikidata_fetcher.py の単体テストを提供します。
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.wikidata_fetcher import WikidataFetcher


@pytest.fixture
def mock_overrides(tmp_path):
    """テスト用オーバーライドファイル"""
    overrides = {
        "__comment__": "テスト用オーバーライド",
        "テスト人物": "テストページ",
        "別名人物": "正式ページ名",
    }
    overrides_path = tmp_path / "wikipedia_overrides.json"
    overrides_path.write_text(json.dumps(overrides, ensure_ascii=False), encoding="utf-8")
    return overrides_path


@pytest.fixture
def fetcher(mock_overrides):
    """テスト用フェッチャー（遅延なし）"""
    return WikidataFetcher(delay=0, overrides_path=mock_overrides)


@pytest.fixture
def fetcher_no_overrides(tmp_path):
    """オーバーライドなしフェッチャー"""
    non_existent = tmp_path / "non_existent.json"
    return WikidataFetcher(delay=0, overrides_path=non_existent)


class TestWikidataFetcherInit:
    """初期化テスト"""

    def test_init_default(self, mock_overrides):
        """デフォルト初期化"""
        fetcher = WikidataFetcher(overrides_path=mock_overrides)
        assert fetcher.delay == 0.5
        assert fetcher.stats["wikidata_calls"] == 0

    def test_init_custom_delay(self, mock_overrides):
        """カスタム遅延で初期化"""
        fetcher = WikidataFetcher(delay=1.0, overrides_path=mock_overrides)
        assert fetcher.delay == 1.0

    def test_init_loads_overrides(self, mock_overrides):
        """オーバーライドがロードされる"""
        fetcher = WikidataFetcher(overrides_path=mock_overrides)
        assert "テスト人物" in fetcher.overrides
        assert "__comment__" not in fetcher.overrides  # メタキー除外

    def test_init_no_overrides_file(self, tmp_path):
        """オーバーライドファイルなしでも動作"""
        non_existent = tmp_path / "non_existent.json"
        fetcher = WikidataFetcher(overrides_path=non_existent)
        assert fetcher.overrides == {}


class TestSearchEntity:
    """search_entity メソッドのテスト"""

    @patch("src.wikidata_fetcher.requests.get")
    def test_search_success(self, mock_get, fetcher):
        """検索成功"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"search": [{"id": "Q12345", "label": "テスト人物"}]}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        entity_id = fetcher.search_entity("テスト人物")
        assert entity_id == "Q12345"
        assert fetcher.stats["wikidata_calls"] == 1

    @patch("src.wikidata_fetcher.requests.get")
    def test_search_no_results(self, mock_get, fetcher):
        """検索結果なし"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"search": []}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        entity_id = fetcher.search_entity("存在しない人物")
        assert entity_id is None

    @patch("src.wikidata_fetcher.requests.get")
    def test_search_error(self, mock_get, fetcher):
        """検索エラー"""
        mock_get.side_effect = Exception("Network error")

        entity_id = fetcher.search_entity("テスト人物")
        assert entity_id is None
        assert fetcher.stats["errors"] == 1


class TestGetJawikiTitle:
    """get_jawiki_title メソッドのテスト"""

    @patch("src.wikidata_fetcher.requests.get")
    def test_get_title_success(self, mock_get, fetcher):
        """タイトル取得成功"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "entities": {"Q12345": {"sitelinks": {"jawiki": {"title": "日本語ページタイトル"}}}}
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        title = fetcher.get_jawiki_title("Q12345")
        assert title == "日本語ページタイトル"
        assert fetcher.stats["wikidata_hits"] == 1

    @patch("src.wikidata_fetcher.requests.get")
    def test_get_title_no_jawiki(self, mock_get, fetcher):
        """日本語Wikipediaリンクなし"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"entities": {"Q12345": {"sitelinks": {"enwiki": {"title": "English Page"}}}}}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        title = fetcher.get_jawiki_title("Q12345")
        assert title is None

    @patch("src.wikidata_fetcher.requests.get")
    def test_get_title_error(self, mock_get, fetcher):
        """取得エラー"""
        mock_get.side_effect = Exception("Network error")

        title = fetcher.get_jawiki_title("Q12345")
        assert title is None
        assert fetcher.stats["errors"] == 1


class TestResolvePerson:
    """resolve_person メソッドのテスト"""

    def test_resolve_override(self, fetcher):
        """オーバーライドから解決"""
        title = fetcher.resolve_person("テスト人物")
        assert title == "テストページ"
        assert fetcher.stats["override_hits"] == 1

    @patch("src.wikidata_fetcher.requests.get")
    def test_resolve_wikidata(self, mock_get, fetcher):
        """Wikidata経由で解決"""
        # 2回のAPI呼び出しをシミュレート
        mock_response_search = MagicMock()
        mock_response_search.json.return_value = {"search": [{"id": "Q12345"}]}
        mock_response_search.raise_for_status = MagicMock()

        mock_response_entity = MagicMock()
        mock_response_entity.json.return_value = {
            "entities": {"Q12345": {"sitelinks": {"jawiki": {"title": "Wikidataから取得"}}}}
        }
        mock_response_entity.raise_for_status = MagicMock()

        mock_get.side_effect = [mock_response_search, mock_response_entity]

        title = fetcher.resolve_person("Wikidata人物")
        assert title == "Wikidataから取得"

    @patch("src.wikidata_fetcher.requests.get")
    def test_resolve_not_found(self, mock_get, fetcher):
        """見つからない場合"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"search": []}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        title = fetcher.resolve_person("存在しない人物")
        assert title is None


class TestGetStats:
    """get_stats メソッドのテスト"""

    def test_initial_stats(self, fetcher):
        """初期統計"""
        stats = fetcher.get_stats()
        assert stats["wikidata_calls"] == 0
        assert stats["wikidata_hits"] == 0
        assert stats["override_hits"] == 0
        assert stats["errors"] == 0

    def test_stats_after_override(self, fetcher):
        """オーバーライド後の統計"""
        fetcher.resolve_person("テスト人物")
        stats = fetcher.get_stats()
        assert stats["override_hits"] == 1

    def test_stats_is_copy(self, fetcher):
        """統計のコピーを返す"""
        stats1 = fetcher.get_stats()
        stats1["wikidata_calls"] = 100
        stats2 = fetcher.get_stats()
        assert stats2["wikidata_calls"] == 0  # 元は変更されていない


class TestLoadOverrides:
    """_load_overrides メソッドのテスト"""

    def test_load_valid_json(self, mock_overrides):
        """有効なJSONを読み込む"""
        fetcher = WikidataFetcher(overrides_path=mock_overrides)
        assert "テスト人物" in fetcher.overrides

    def test_load_excludes_meta_keys(self, mock_overrides):
        """メタキーを除外"""
        fetcher = WikidataFetcher(overrides_path=mock_overrides)
        assert "__comment__" not in fetcher.overrides

    def test_load_invalid_json(self, tmp_path):
        """無効なJSONでも動作"""
        invalid_json = tmp_path / "invalid.json"
        invalid_json.write_text("not valid json{{{", encoding="utf-8")

        fetcher = WikidataFetcher(overrides_path=invalid_json)
        assert fetcher.overrides == {}
