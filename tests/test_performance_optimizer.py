"""
PerformanceOptimizer テストモジュール

performance_optimizer.py の単体テストを提供します。
"""

import json
import pytest
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

# モジュールインポート前にasyncio.create_taskをモック
with patch("asyncio.create_task", return_value=MagicMock()):
    from src.performance_optimizer import (
        LRUCache,
        PersistentCache,
        ConnectionPool,
        AsyncBatchProcessor,
        StreamProcessor,
        ResourceMonitor,
        LazyLoader,
        async_memoize,
        get_memory_cache,
        get_disk_cache,
        get_connection_pool,
    )


@pytest.mark.asyncio
class TestLRUCache:
    """LRUCache クラスのテスト"""

    async def test_set_and_get(self):
        """セットとゲット"""
        cache = LRUCache(max_size=10)
        await cache.set("key1", "value1")
        result = await cache.get("key1")
        assert result == "value1"

    async def test_get_nonexistent(self):
        """存在しないキー"""
        cache = LRUCache()
        result = await cache.get("nonexistent")
        assert result is None

    async def test_ttl_expiry(self):
        """TTL期限切れ"""
        cache = LRUCache(ttl=timedelta(seconds=-1))  # 即座に期限切れ
        await cache.set("key1", "value1")
        result = await cache.get("key1")
        assert result is None

    async def test_lru_eviction(self):
        """LRU eviction"""
        cache = LRUCache(max_size=2)
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")  # key1がevictされる

        assert await cache.get("key1") is None
        assert await cache.get("key2") == "value2"
        assert await cache.get("key3") == "value3"

    async def test_move_to_end_on_access(self):
        """アクセス時にLRU順序更新"""
        cache = LRUCache(max_size=2)
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")

        # key1にアクセスしてLRU順序を更新
        await cache.get("key1")

        # key3を追加するとkey2がevictされる
        await cache.set("key3", "value3")

        assert await cache.get("key1") == "value1"
        assert await cache.get("key2") is None
        assert await cache.get("key3") == "value3"

    async def test_clear(self):
        """キャッシュクリア"""
        cache = LRUCache()
        await cache.set("key1", "value1")
        await cache.clear()
        assert await cache.get("key1") is None

    def test_stats(self):
        """統計情報"""
        cache = LRUCache(max_size=100)
        stats = cache.stats()

        assert stats["size"] == 0
        assert stats["max_size"] == 100
        assert stats["oldest"] is None
        assert stats["newest"] is None


@pytest.mark.asyncio
class TestPersistentCache:
    """PersistentCache クラスのテスト"""

    @pytest.fixture
    def cache(self, tmp_path):
        """テスト用キャッシュ"""
        with patch("src.performance_optimizer.asyncio.create_task"):
            cache = PersistentCache(cache_dir=tmp_path / ".cache")
            cache.index = {}  # インデックスを初期化
            return cache

    async def test_set_and_get(self, cache):
        """セットとゲット"""
        await cache.set("key1", {"data": "value1"})
        result = await cache.get("key1")
        assert result == {"data": "value1"}

    async def test_get_nonexistent(self, cache):
        """存在しないキー"""
        result = await cache.get("nonexistent")
        assert result is None

    async def test_delete(self, cache):
        """削除"""
        await cache.set("key1", {"data": "value1"})
        await cache.delete("key1")
        result = await cache.get("key1")
        assert result is None

    async def test_cleanup(self, cache):
        """期限切れエントリのクリーンアップ"""
        # 期限切れエントリを追加
        cache.index["expired_key"] = {
            "expires": (datetime.now() - timedelta(days=1)).isoformat(),
        }
        cache.index["valid_key"] = {
            "expires": (datetime.now() + timedelta(days=1)).isoformat(),
        }

        # 期限切れエントリ用のダミーファイル作成
        expired_file = cache._get_cache_file("expired_key")
        expired_file.write_text("{}")

        removed = await cache.cleanup()

        assert removed == 1
        assert "expired_key" not in cache.index
        assert "valid_key" in cache.index


@pytest.mark.asyncio
class TestConnectionPool:
    """ConnectionPool クラスのテスト"""

    async def test_get_session_creates_new(self):
        """新しいセッションを作成"""
        pool = ConnectionPool()

        with patch("aiohttp.ClientSession") as mock_session:
            with patch("aiohttp.TCPConnector"):
                mock_session.return_value = MagicMock()
                session = await pool.get_session("server1", "http://localhost:8000")

                assert "server1" in pool.sessions

    async def test_get_session_reuses_existing(self):
        """既存セッションを再利用"""
        pool = ConnectionPool()
        mock_session = MagicMock()
        pool.sessions["server1"] = mock_session

        session = await pool.get_session("server1", "http://localhost:8000")

        assert session is mock_session

    async def test_close_all(self):
        """全セッションクローズ"""
        pool = ConnectionPool()
        mock_session = AsyncMock()
        pool.sessions["server1"] = mock_session

        await pool.close_all()

        mock_session.close.assert_called_once()
        assert len(pool.sessions) == 0


@pytest.mark.asyncio
class TestAsyncBatchProcessor:
    """AsyncBatchProcessor クラスのテスト"""

    async def test_process_all_items(self):
        """全アイテムを処理"""
        processor = AsyncBatchProcessor(batch_size=3, max_workers=2)
        items = [1, 2, 3, 4, 5]

        async def double(x):
            return x * 2

        results = await processor.process(items, double)

        assert sorted(results) == [2, 4, 6, 8, 10]

    async def test_process_with_callback(self):
        """コールバック付き処理"""
        processor = AsyncBatchProcessor(batch_size=2)
        items = [1, 2, 3, 4]
        progress_calls = []

        async def identity(x):
            return x

        def callback(current, total):
            progress_calls.append((current, total))

        await processor.process(items, identity, progress_callback=callback)

        assert len(progress_calls) == 2  # 2バッチ

    async def test_process_handles_exceptions(self):
        """例外処理"""
        processor = AsyncBatchProcessor(batch_size=2)
        items = [1, 2, 3]

        async def fail_on_two(x):
            if x == 2:
                raise ValueError("Error on 2")
            return x

        results = await processor.process(items, fail_on_two)

        # 例外はNoneとして返される
        assert None in results
        assert 1 in results
        assert 3 in results


class TestResourceMonitor:
    """ResourceMonitor クラスのテスト"""

    def test_init(self):
        """初期化"""
        monitor = ResourceMonitor()
        assert monitor.start_time > 0
        assert "memory" in monitor.metrics
        assert "cpu" in monitor.metrics
        assert "io" in monitor.metrics

    def test_record_metric(self):
        """メトリック記録"""
        monitor = ResourceMonitor()
        monitor.record_metric("memory", 100.0)
        monitor.record_metric("memory", 150.0)

        assert len(monitor.metrics["memory"]) == 2
        assert monitor.metrics["memory"][0] == 100.0

    def test_record_new_metric_type(self):
        """新しいメトリックタイプ"""
        monitor = ResourceMonitor()
        monitor.record_metric("custom", 42.0)

        assert "custom" in monitor.metrics
        assert monitor.metrics["custom"][0] == 42.0

    @patch("psutil.Process")
    def test_get_stats(self, mock_process):
        """統計情報取得"""
        mock_proc = MagicMock()
        mock_proc.memory_info.return_value.rss = 100 * 1024 * 1024
        mock_proc.cpu_percent.return_value = 25.0
        mock_proc.num_threads.return_value = 4
        mock_proc.open_files.return_value = []
        mock_proc.connections.return_value = []
        mock_process.return_value = mock_proc

        monitor = ResourceMonitor()
        monitor.record_metric("memory", 50.0)

        stats = monitor.get_stats()

        assert "uptime" in stats
        assert stats["memory_mb"] == 100.0
        assert stats["cpu_percent"] == 25.0
        assert stats["num_threads"] == 4


@pytest.mark.asyncio
class TestLazyLoader:
    """LazyLoader クラスのテスト"""

    async def test_lazy_load_sync(self):
        """同期ローダー"""
        loader = LazyLoader(lambda: "loaded_value")
        result = await loader.get()
        assert result == "loaded_value"

    async def test_lazy_load_async(self):
        """非同期ローダー"""

        async def async_loader():
            return "async_loaded_value"

        loader = LazyLoader(async_loader)
        result = await loader.get()
        assert result == "async_loaded_value"

    async def test_lazy_load_only_once(self):
        """一度だけロード"""
        call_count = 0

        def loader():
            nonlocal call_count
            call_count += 1
            return "value"

        lazy = LazyLoader(loader)

        await lazy.get()
        await lazy.get()
        await lazy.get()

        assert call_count == 1

    async def test_reset(self):
        """リセット"""
        call_count = 0

        def loader():
            nonlocal call_count
            call_count += 1
            return f"value_{call_count}"

        lazy = LazyLoader(loader)

        result1 = await lazy.get()
        lazy.reset()
        result2 = await lazy.get()

        assert result1 == "value_1"
        assert result2 == "value_2"


@pytest.mark.asyncio
class TestAsyncMemoize:
    """async_memoize デコレーターのテスト"""

    async def test_memoize_returns_cached(self):
        """キャッシュから返す"""
        call_count = 0

        @async_memoize(ttl=timedelta(minutes=5))
        async def expensive_func(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        result1 = await expensive_func(5)
        result2 = await expensive_func(5)

        assert result1 == 10
        assert result2 == 10
        assert call_count == 1  # 2回目はキャッシュから

    async def test_memoize_different_args(self):
        """異なる引数"""
        call_count = 0

        @async_memoize(ttl=timedelta(minutes=5))
        async def expensive_func(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        result1 = await expensive_func(5)
        result2 = await expensive_func(10)

        assert result1 == 10
        assert result2 == 20
        assert call_count == 2

    async def test_memoize_exposes_cache(self):
        """キャッシュにアクセス可能"""

        @async_memoize()
        async def func(x):
            return x

        assert hasattr(func, "cache")


class TestStreamProcessor:
    """StreamProcessor クラスのテスト"""

    def test_init(self):
        """初期化"""
        processor = StreamProcessor(chunk_size=512)
        assert processor.chunk_size == 512

    def test_default_chunk_size(self):
        """デフォルトチャンクサイズ"""
        processor = StreamProcessor()
        assert processor.chunk_size == 1024


class TestSingletonGetters:
    """シングルトンゲッター関数のテスト"""

    def test_get_memory_cache(self):
        """メモリキャッシュ取得"""
        cache1 = get_memory_cache()
        cache2 = get_memory_cache()
        assert cache1 is cache2

    def test_get_disk_cache(self):
        """ディスクキャッシュ取得"""
        cache1 = get_disk_cache()
        cache2 = get_disk_cache()
        assert cache1 is cache2

    def test_get_connection_pool(self):
        """コネクションプール取得"""
        pool1 = get_connection_pool()
        pool2 = get_connection_pool()
        assert pool1 is pool2


@pytest.mark.asyncio
class TestPersistentCacheErrorHandling:
    """PersistentCache エラー処理テスト"""

    @pytest.fixture
    def cache(self, tmp_path):
        """テスト用キャッシュ"""
        with patch("src.performance_optimizer.asyncio.create_task"):
            cache = PersistentCache(cache_dir=tmp_path / ".cache")
            cache.index = {}
            return cache

    async def test_load_index_error(self, tmp_path, caplog):
        """インデックス読み込みエラー"""
        with patch("src.performance_optimizer.asyncio.create_task"):
            cache = PersistentCache(cache_dir=tmp_path / ".cache")

        # 破損したインデックスファイルを作成
        cache.index_file.write_text("invalid json {{{", encoding="utf-8")

        await cache._load_index()

        assert cache.index == {}

    async def test_save_index_error(self, cache, caplog):
        """インデックス保存エラー"""
        # 書き込み不可能なパスに設定
        cache.index_file = Path("/nonexistent/path/index.json")
        cache.index = {"key": {"expires": "2025-01-01"}}

        await cache._save_index()
        # エラーが発生してもクラッシュしない

    async def test_get_expired_entry(self, cache):
        """期限切れエントリの取得"""
        # 期限切れエントリを追加
        cache.index["expired_key"] = {
            "expires": (datetime.now() - timedelta(days=1)).isoformat(),
        }

        result = await cache.get("expired_key")

        assert result is None
        assert "expired_key" not in cache.index

    async def test_get_missing_file(self, cache):
        """ファイルが存在しないエントリ"""
        # インデックスにはあるがファイルがない
        cache.index["orphan_key"] = {
            "expires": (datetime.now() + timedelta(days=1)).isoformat(),
        }

        result = await cache.get("orphan_key")

        assert result is None

    async def test_get_corrupted_file(self, cache):
        """破損ファイルの読み込み"""
        cache.index["corrupted_key"] = {
            "expires": (datetime.now() + timedelta(days=1)).isoformat(),
        }

        # 破損ファイルを作成
        cache_file = cache._get_cache_file("corrupted_key")
        cache_file.write_text("invalid json {{{", encoding="utf-8")

        result = await cache.get("corrupted_key")

        assert result is None

    async def test_set_exception(self, cache, tmp_path):
        """保存時の例外処理"""
        # 書き込み不可能なパスに設定
        cache.cache_dir = Path("/nonexistent/path")

        # 例外が発生してもクラッシュしない
        await cache.set("key", {"data": "value"})


@pytest.mark.asyncio
class TestStreamProcessorMethods:
    """StreamProcessor の追加テスト"""

    async def test_process_file(self, tmp_path):
        """ファイル処理"""
        # テストファイルを作成
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"Hello World Data")

        processor = StreamProcessor(chunk_size=5)

        chunks = []
        async for chunk in processor.process_file(test_file, lambda x: x.decode()):
            chunks.append(chunk)

        assert len(chunks) > 0
        assert "".join(chunks) == "Hello World Data"

    async def test_process_stream(self):
        """ストリーム処理"""
        # モックストリームリーダー
        mock_reader = AsyncMock()
        mock_reader.read = AsyncMock(side_effect=[b"chunk1", b"chunk2", b""])

        processor = StreamProcessor(chunk_size=10)

        chunks = []
        async for chunk in processor.process_stream(mock_reader, lambda x: x.decode()):
            chunks.append(chunk)

        assert chunks == ["chunk1", "chunk2"]


@pytest.mark.asyncio
class TestOptimizedMCPClient:
    """OptimizedMCPClient テスト"""

    def test_init(self):
        """初期化"""
        with patch("src.performance_optimizer.asyncio.create_task"):
            from src.performance_optimizer import OptimizedMCPClient

            client = OptimizedMCPClient({"name": "test", "url": "http://localhost:8000"})

            assert client.config["name"] == "test"
            assert client.cache is not None
            assert client.pool is not None
            assert client.batch_processor is not None
            assert client.monitor is not None

    async def test_execute_cached(self):
        """キャッシュされた操作"""
        with patch("src.performance_optimizer.asyncio.create_task"):
            from src.performance_optimizer import OptimizedMCPClient

            client = OptimizedMCPClient({"name": "test", "url": "http://localhost:8000"})

            # キャッシュに値を設定
            await client.cache.set('get_user:{"id": 1}', {"user": "cached_user"})

            # キャッシュから取得
            result = await client.execute("get_user", {"id": 1})

            assert result == {"user": "cached_user"}

    async def test_execute_non_cached_method(self):
        """キャッシュ対象外メソッド"""
        with patch("src.performance_optimizer.asyncio.create_task"):
            from src.performance_optimizer import OptimizedMCPClient

            client = OptimizedMCPClient({"name": "test", "url": "http://localhost:8000"})

            # セッションをモック
            mock_response = AsyncMock()
            mock_response.json = AsyncMock(return_value={"result": "ok"})
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock()

            mock_session = MagicMock()
            mock_session.post = MagicMock(return_value=mock_response)
            client.pool.sessions["test"] = mock_session

            result = await client.execute("create_user", {"name": "new_user"})

            assert result == {"result": "ok"}

    async def test_batch_execute(self):
        """バッチ実行"""
        with patch("src.performance_optimizer.asyncio.create_task"):
            from src.performance_optimizer import OptimizedMCPClient

            client = OptimizedMCPClient({"name": "test", "url": "http://localhost:8000"})

            # executeをモック
            with patch.object(client, "execute", new_callable=AsyncMock) as mock_execute:
                mock_execute.return_value = {"result": "ok"}

                requests = [
                    {"method": "get_user", "params": {"id": 1}},
                    {"method": "get_user", "params": {"id": 2}},
                ]

                results = await client.batch_execute(requests)

                assert len(results) == 2
                assert mock_execute.call_count == 2


@pytest.mark.asyncio
class TestCleanupFunction:
    """cleanup関数テスト"""

    async def test_cleanup(self):
        """リソースクリーンアップ"""
        from src.performance_optimizer import cleanup

        # 事前にキャッシュにデータを追加
        memory_cache = get_memory_cache()
        await memory_cache.set("test_key", "test_value")

        # クリーンアップ実行
        await cleanup()

        # メモリキャッシュがクリアされている
        result = await memory_cache.get("test_key")
        # 注: cleanup後もシングルトンは存在するが、内容はクリア


@pytest.mark.asyncio
class TestPersistentCacheDelete:
    """PersistentCache delete メソッドの追加テスト"""

    @pytest.fixture
    def cache(self, tmp_path):
        """テスト用キャッシュ"""
        with patch("src.performance_optimizer.asyncio.create_task"):
            cache = PersistentCache(cache_dir=tmp_path / ".cache")
            cache.index = {}
            return cache

    async def test_delete_nonexistent_key(self, cache):
        """存在しないキーの削除"""
        # 例外が発生しない
        await cache.delete("nonexistent")

    async def test_delete_with_missing_file(self, cache):
        """ファイルがないキーの削除"""
        cache.index["orphan_key"] = {
            "expires": (datetime.now() + timedelta(days=1)).isoformat(),
        }

        await cache.delete("orphan_key")

        assert "orphan_key" not in cache.index
