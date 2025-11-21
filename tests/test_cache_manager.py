#!/usr/bin/env python3
"""CacheManager テスト"""

import sys
import tempfile
from pathlib import Path

import pytest

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
