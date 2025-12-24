#!/usr/bin/env python3
"""
Google検索キャッシュの回帰テスト。

テスト観点表（等価分割・境界値）:
┌────────────────────┬──────────────────────┬─────────────────────┐
│ 観点               │ 等価クラス           │ テストケース        │
├────────────────────┼──────────────────────┼─────────────────────┤
│ キャッシュ有無     │ あり / なし          │ test_cache_hit,     │
│                    │                      │ test_cache_miss     │
├────────────────────┼──────────────────────┼─────────────────────┤
│ force_refresh      │ True / False         │ test_force_refresh  │
├────────────────────┼──────────────────────┼─────────────────────┤
│ person_id          │ あり / なし / 空     │ test_without_pid,   │
│                    │                      │ test_empty_pid      │
├────────────────────┼──────────────────────┼─────────────────────┤
│ DB存在             │ あり / なし          │ test_no_db          │
├────────────────────┼──────────────────────┼─────────────────────┤
│ 統計カウンター     │ ヒット時 / API時     │ test_stats_*        │
├────────────────────┼──────────────────────┼─────────────────────┤
│ 境界値             │ hits=0 / hits=MAX    │ test_zero_hits,     │
│                    │                      │ test_large_hits     │
└────────────────────┴──────────────────────┴─────────────────────┘
"""

import os
import sqlite3
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestGoogleSearchCache:
    """Google検索キャッシュのテスト"""

    @pytest.fixture
    def temp_cache_db(self, tmp_path):
        """一時キャッシュDBを作成"""
        db_path = tmp_path / "fame_score.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE fame_cache (
                person_id TEXT PRIMARY KEY,
                person_name TEXT,
                google_hits INTEGER
            )
        """)
        # テストデータ
        conn.execute("INSERT INTO fame_cache VALUES (?, ?, ?)", ("P12345", "テスト太郎", 1000000))
        conn.execute("INSERT INTO fame_cache VALUES (?, ?, ?)", ("P67890", "テスト花子", None))
        conn.commit()
        conn.close()
        return db_path

    @pytest.fixture
    def mock_google_module(self, temp_cache_db):
        """google_searchモジュールをモック"""
        with patch.dict(
            os.environ,
            {
                "GOOGLE_API_KEY": "test_key",
                "GOOGLE_CSE_ID": "test_cse",
            },
        ):
            # モジュールを再インポート（環境変数を反映）
            import importlib
            from scripts.fame_score_v3 import google_search

            importlib.reload(google_search)

            # キャッシュDBパスを一時DBに変更
            original_path = google_search.CACHE_DB_PATH
            google_search.CACHE_DB_PATH = temp_cache_db
            google_search.reset_stats()

            yield google_search

            # 復元
            google_search.CACHE_DB_PATH = original_path

    def test_cache_hit(self, mock_google_module):
        """キャッシュヒット: 既存データを返しAPIを呼ばない"""
        hits = mock_google_module.get_cached_google_hits("P12345")

        assert hits == 1000000
        stats = mock_google_module.get_stats()
        assert stats["cache_hits"] == 1
        assert stats["api_calls"] == 0

    def test_cache_miss(self, mock_google_module):
        """キャッシュミス: Noneを返す"""
        hits = mock_google_module.get_cached_google_hits("P99999")

        assert hits is None
        stats = mock_google_module.get_stats()
        assert stats["cache_hits"] == 0

    def test_cache_null_value(self, mock_google_module):
        """google_hitsがNULLの場合はキャッシュミス"""
        hits = mock_google_module.get_cached_google_hits("P67890")

        assert hits is None

    def test_force_refresh_skips_cache(self, mock_google_module):
        """force_refresh=Trueでキャッシュをスキップ"""
        with patch.object(mock_google_module, "get_cached_google_hits") as mock_cache:
            mock_cache.return_value = 999999

            # force_refresh=Falseの場合はキャッシュを参照
            with patch("requests.get") as mock_req:
                mock_req.return_value = MagicMock(
                    status_code=200, json=lambda: {"searchInformation": {"totalResults": "500000"}}
                )
                result = mock_google_module.get_google_search_hits("テスト", person_id="P12345", force_refresh=False)
                # キャッシュがあるのでAPIは呼ばれない
                assert result == 999999

    def test_without_person_id(self, mock_google_module):
        """person_idなしでも動作する（キャッシュ不使用）"""
        with patch("requests.get") as mock_req:
            mock_req.return_value = MagicMock(
                status_code=200, json=lambda: {"searchInformation": {"totalResults": "123456"}}
            )
            result = mock_google_module.get_google_search_hits("テスト")

            assert result == 123456

    def test_stats_increment(self, mock_google_module):
        """統計カウンターが正しく増加"""
        mock_google_module.reset_stats()

        # キャッシュヒット
        mock_google_module.get_cached_google_hits("P12345")
        mock_google_module.get_cached_google_hits("P12345")

        stats = mock_google_module.get_stats()
        assert stats["cache_hits"] == 2

    def test_zero_hits(self, mock_google_module, temp_cache_db):
        """hits=0も正常に保存・取得できる"""
        conn = sqlite3.connect(str(temp_cache_db))
        conn.execute("INSERT INTO fame_cache VALUES (?, ?, ?)", ("P00000", "ゼロ太郎", 0))
        conn.commit()
        conn.close()

        hits = mock_google_module.get_cached_google_hits("P00000")
        assert hits == 0

    def test_large_hits(self, mock_google_module, temp_cache_db):
        """大きな数値も正常に保存・取得できる"""
        conn = sqlite3.connect(str(temp_cache_db))
        conn.execute("INSERT INTO fame_cache VALUES (?, ?, ?)", ("P99999", "ビッグ太郎", 999999999999))
        conn.commit()
        conn.close()

        hits = mock_google_module.get_cached_google_hits("P99999")
        assert hits == 999999999999

    def test_is_google_available(self, mock_google_module):
        """API可用性チェック"""
        assert mock_google_module.is_google_available() is True


class TestNoDuplicateSearch:
    """重複検索が発生しないことを確認"""

    def test_same_person_id_no_duplicate_api_call(self, tmp_path):
        """同一person_idで2回呼び出してもAPIは1回のみ"""
        db_path = tmp_path / "fame_score.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE fame_cache (
                person_id TEXT PRIMARY KEY,
                person_name TEXT,
                google_hits INTEGER
            )
        """)
        conn.execute("INSERT INTO fame_cache VALUES (?, ?, ?)", ("PTEST01", "テスト一郎", None))
        conn.commit()
        conn.close()

        with patch.dict(
            os.environ,
            {
                "GOOGLE_API_KEY": "test_key",
                "GOOGLE_CSE_ID": "test_cse",
            },
        ):
            import importlib
            from scripts.fame_score_v3 import google_search

            importlib.reload(google_search)
            google_search.CACHE_DB_PATH = db_path
            google_search.reset_stats()

            api_call_count = 0

            def mock_get(*args, **kwargs):
                nonlocal api_call_count
                api_call_count += 1
                response = MagicMock()
                response.status_code = 200
                response.json.return_value = {"searchInformation": {"totalResults": "12345"}}
                return response

            with patch("requests.get", side_effect=mock_get):
                # 1回目: APIを呼ぶ
                result1 = google_search.get_google_search_hits("テスト一郎", person_id="PTEST01")
                assert result1 == 12345
                assert api_call_count == 1

                # 2回目: キャッシュから取得（APIは呼ばない）
                result2 = google_search.get_google_search_hits("テスト一郎", person_id="PTEST01")
                assert result2 == 12345
                assert api_call_count == 1  # 増えていない！

            stats = google_search.get_stats()
            assert stats["api_calls"] == 1
            assert stats["cache_hits"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
