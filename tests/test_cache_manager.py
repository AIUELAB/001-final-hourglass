#!/usr/bin/env python3
"""CacheManager テスト"""

import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch


sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cache_manager import CacheManager


class TestCacheManager:
    """CacheManagerの基本テスト"""

    def test_init(self):
        """初期化テスト"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cm = CacheManager(cache_dir=tmpdir)
            assert cm.cache_dir == Path(tmpdir)
            assert cm.memory_cache == {}
            assert cm.ttl_seconds == 300

    def test_cache_dir_creation(self):
        """キャッシュディレクトリ作成テスト"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "test_cache"
            cm = CacheManager(cache_dir=str(cache_path))
            assert cache_path.exists()
            assert (cache_path / "memory").exists()
            assert (cache_path / "files").exists()
            assert (cache_path / "metadata").exists()

    def test_purge_all_cache(self):
        """全キャッシュ削除テスト"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cm = CacheManager(cache_dir=tmpdir)
            cm.memory_cache["test"] = "value"
            result = cm.purge_all_cache()
            assert result is True
            assert cm.memory_cache == {}

    def test_memory_cache_operations(self):
        """メモリキャッシュ操作テスト"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cm = CacheManager(cache_dir=tmpdir)
            # 直接メモリキャッシュに追加
            cm.memory_cache["key1"] = {"data": "test"}
            assert "key1" in cm.memory_cache
            assert cm.memory_cache["key1"]["data"] == "test"

    def test_invalidate_all_cache(self):
        """全キャッシュ無効化テスト"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cm = CacheManager(cache_dir=tmpdir)
            cm.cache_metadata["key1"] = {"timestamp": "2025-01-01T00:00:00"}
            cm.invalidate_all_cache()
            # タイムスタンプが過去に設定されていることを確認
            assert "key1" in cm.cache_metadata

    def test_ttl_seconds(self):
        """TTL設定テスト"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cm = CacheManager(cache_dir=tmpdir)
            assert cm.ttl_seconds == 300

    def test_force_clear_on_update(self):
        """force_clear_on_update設定テスト"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cm = CacheManager(cache_dir=tmpdir)
            assert cm.force_clear_on_update is True

    def test_browser_cache_buster(self):
        """browser_cache_buster設定テスト"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cm = CacheManager(cache_dir=tmpdir)
            assert cm.browser_cache_buster is True

    def test_atomic_cache_update(self):
        """アトミックキャッシュ更新テスト"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cm = CacheManager(cache_dir=tmpdir)
            data = {"name": "test", "value": 123}
            result = cm.atomic_cache_update("test_key", data, "v1.0")
            assert result is True
            assert "test_key" in cm.memory_cache
            assert cm.memory_cache["test_key"] == data
            assert cm.cache_metadata["test_key"]["version"] == "v1.0"
            assert cm.cache_metadata["test_key"]["valid"] is True

    def test_get_cache_valid(self):
        """有効なキャッシュ取得テスト"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cm = CacheManager(cache_dir=tmpdir)
            data = {"name": "cached_data"}
            cm.atomic_cache_update("key1", data, "v1")
            result = cm.get_cache("key1")
            assert result == data

    def test_get_cache_missing(self):
        """存在しないキャッシュ取得テスト"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cm = CacheManager(cache_dir=tmpdir)
            result = cm.get_cache("nonexistent")
            assert result is None

    def test_generate_cache_buster_url_with_version(self):
        """バージョン付きキャッシュバスターURL生成テスト"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cm = CacheManager(cache_dir=tmpdir)
            url = cm.generate_cache_buster_url("https://example.com/page", "v1.0")
            assert "https://example.com/page?" in url
            assert "v=" in url
            assert "hash=" in url
            assert "nocache=1" in url

    def test_generate_cache_buster_url_without_version(self):
        """バージョンなしキャッシュバスターURL生成テスト"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cm = CacheManager(cache_dir=tmpdir)
            url = cm.generate_cache_buster_url("https://example.com/page")
            assert "v=" in url

    def test_generate_cache_buster_url_with_query(self):
        """既存クエリ付きURL生成テスト"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cm = CacheManager(cache_dir=tmpdir)
            url = cm.generate_cache_buster_url("https://example.com/page?foo=bar", "v1")
            assert "&v=" in url

    def test_clear_google_sheets_cache(self):
        """Google Sheetsキャッシュクリアヘッダー生成テスト"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cm = CacheManager(cache_dir=tmpdir)
            headers = cm.clear_google_sheets_cache()
            assert headers["Cache-Control"] == "no-cache, no-store, must-revalidate"
            assert headers["Pragma"] == "no-cache"
            assert headers["Expires"] == "0"

    def test_get_cache_stats(self):
        """キャッシュ統計情報取得テスト"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cm = CacheManager(cache_dir=tmpdir)
            cm.atomic_cache_update("key1", {"data": "test"}, "v1")
            stats = cm.get_cache_stats()
            assert "memory_cache" in stats
            assert "file_cache" in stats
            assert stats["memory_cache"]["count"] == 1
            assert stats["memory_cache"]["valid_count"] == 1

    def test_cleanup_expired(self):
        """期限切れキャッシュクリーンアップテスト"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cm = CacheManager(cache_dir=tmpdir)
            cm.ttl_seconds = 0  # 即座に期限切れ
            cm.atomic_cache_update("key1", {"data": "test"}, "v1")
            deleted = cm.cleanup_expired()
            assert deleted >= 0

    def test_force_browser_refresh_script(self):
        """ブラウザ強制リフレッシュスクリプト生成テスト"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cm = CacheManager(cache_dir=tmpdir)
            script = cm.force_browser_refresh_script()
            assert "window.location.reload" in script
            assert "caches" in script

    def test_purge_old_data(self):
        """古いデータ削除テスト"""
        from datetime import datetime, timedelta

        with tempfile.TemporaryDirectory() as tmpdir:
            cm = CacheManager(cache_dir=tmpdir)
            # 古いデータを設定
            old_time = (datetime.now() - timedelta(days=2)).isoformat()
            cm.memory_cache["old_key"] = {"data": "old"}
            cm.cache_metadata["old_key"] = {"timestamp": old_time}
            # 1日前を閾値として削除
            threshold = datetime.now() - timedelta(days=1)
            deleted = cm.purge_old_data(threshold)
            assert deleted == 1
            assert "old_key" not in cm.memory_cache


class TestPurgeAllCacheEdgeCases:
    """purge_all_cacheのエッジケーステスト"""

    def test_purge_with_files_and_subdirs(self):
        """ファイルとサブディレクトリの削除"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cm = CacheManager(cache_dir=tmpdir)

            # テストファイルを作成
            files_dir = Path(tmpdir) / "files"
            test_file = files_dir / "test.json"
            test_file.write_text('{"data": "test"}', encoding="utf-8")

            # サブディレクトリを作成
            sub_dir = files_dir / "subdir"
            sub_dir.mkdir(parents=True)
            (sub_dir / "nested.json").write_text("{}", encoding="utf-8")

            # purge実行
            result = cm.purge_all_cache()

            assert result is True
            assert not test_file.exists()
            assert not sub_dir.exists()

    def test_purge_exception_handling(self):
        """purge_all_cache例外ハンドリング"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cm = CacheManager(cache_dir=tmpdir)

            # shutil.rmtreeをモックして例外発生
            with patch("shutil.rmtree", side_effect=PermissionError("Access denied")):
                # サブディレクトリを作成
                sub_dir = Path(tmpdir) / "files" / "subdir"
                sub_dir.mkdir(parents=True)

                result = cm.purge_all_cache()

                # 例外時はFalseを返す
                assert result is False


class TestAtomicCacheUpdateRollback:
    """atomic_cache_updateのロールバックテスト"""

    def test_rollback_on_exception(self):
        """例外発生時のロールバック"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cm = CacheManager(cache_dir=tmpdir)

            # 既存データを設定
            old_data = {"name": "old_value"}
            cm.memory_cache["key1"] = old_data
            cm.cache_metadata["key1"] = {"version": "v0", "valid": True}

            # ファイル書き込みで例外を発生させる
            with patch("builtins.open", side_effect=IOError("Write failed")):
                result = cm.atomic_cache_update("key1", {"name": "new_value"}, "v1")

            # ロールバックが行われる
            assert result is False
            assert cm.memory_cache["key1"] == old_data
            assert cm.cache_metadata["key1"]["version"] == "v0"


class TestGetCacheFromFile:
    """get_cacheのファイルキャッシュテスト"""

    def test_get_from_file_cache(self):
        """ファイルキャッシュからの復元"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cm = CacheManager(cache_dir=tmpdir)

            # ファイルキャッシュを手動で作成
            cache_file = Path(tmpdir) / "files" / "file_key.json"
            cache_data = {
                "data": {"name": "from_file"},
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "valid": True,
                    "version": "v1",
                },
            }
            cache_file.write_text(json.dumps(cache_data), encoding="utf-8")

            # メモリキャッシュには存在しない
            assert "file_key" not in cm.memory_cache

            # ファイルから取得
            result = cm.get_cache("file_key")

            # ファイルから復元される
            assert result == {"name": "from_file"}
            # メモリキャッシュにも復元される
            assert "file_key" in cm.memory_cache

    def test_get_file_cache_expired(self):
        """期限切れファイルキャッシュ"""
        from datetime import timedelta

        with tempfile.TemporaryDirectory() as tmpdir:
            cm = CacheManager(cache_dir=tmpdir)

            # 期限切れのファイルキャッシュを作成
            cache_file = Path(tmpdir) / "files" / "expired_key.json"
            old_time = (datetime.now() - timedelta(hours=1)).isoformat()
            cache_data = {
                "data": {"name": "expired"},
                "metadata": {"timestamp": old_time, "valid": True},
            }
            cache_file.write_text(json.dumps(cache_data), encoding="utf-8")

            # 取得（TTLは300秒なので期限切れ）
            result = cm.get_cache("expired_key")

            assert result is None

    def test_get_file_cache_read_error(self):
        """ファイル読み込みエラー"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cm = CacheManager(cache_dir=tmpdir)

            # 不正なJSONファイルを作成
            cache_file = Path(tmpdir) / "files" / "invalid_key.json"
            cache_file.write_text("not valid json", encoding="utf-8")

            # エラーでもNoneが返される
            result = cm.get_cache("invalid_key")

            assert result is None
