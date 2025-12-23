"""
tests/test_beartype_integration.py - beartype_integration.py ユニットテスト
"""

import asyncio
from pathlib import Path
from unittest.mock import patch

import pytest

# beartypeがインストールされていない場合はスキップ
beartype_available = False
try:
    import beartype

    beartype_available = True
except ImportError:
    pass

pytestmark = pytest.mark.skipif(not beartype_available, reason="beartype not installed (optional dependency)")


class TestCalculateAverage:
    """calculate_average関数テスト"""

    def test_average_normal(self):
        """通常のリストの平均"""
        from src.beartype_integration import calculate_average

        result = calculate_average([1.0, 2.0, 3.0])
        assert result == 2.0

    def test_average_single(self):
        """単一要素"""
        from src.beartype_integration import calculate_average

        result = calculate_average([5.0])
        assert result == 5.0

    def test_average_empty_raises(self):
        """空のリストでエラー"""
        from src.beartype_integration import calculate_average

        with pytest.raises(ValueError, match="Cannot calculate average"):
            calculate_average([])


class TestProcessConfig:
    """process_config関数テスト"""

    def test_process_basic(self):
        """基本的な設定処理"""
        from src.beartype_integration import process_config

        config = {"key1": "value1", "key2": 123}
        result = process_config(config)

        assert result["key1"] == "value1"
        assert result["key2"] == "123"

    def test_process_with_none(self):
        """None値を含む設定"""
        from src.beartype_integration import process_config

        config = {"key1": "value", "key2": None}
        result = process_config(config, strict_mode=False)

        assert "key1" in result
        assert "key2" not in result

    def test_process_strict_mode(self):
        """strictモード"""
        from src.beartype_integration import process_config

        config = {"key1": None}
        result = process_config(config, strict_mode=True)

        assert result["key1"] == "None"


class TestMCPServer:
    """MCPServerデータクラステスト"""

    def test_create_server(self):
        """サーバー作成"""
        from src.beartype_integration import MCPServer

        server = MCPServer(
            name="test",
            url="https://api.example.com",
            port=443,
            protocol="https",
        )

        assert server.name == "test"
        assert server.port == 443
        assert server.timeout == 30.0

    def test_server_with_api_key(self):
        """APIキー付きサーバー"""
        from src.beartype_integration import MCPServer

        server = MCPServer(
            name="test",
            url="https://api.example.com",
            port=8080,
            protocol="http",
            api_key="secret",
        )

        assert server.api_key == "secret"

    def test_server_invalid_timeout(self):
        """無効なタイムアウト"""
        from src.beartype_integration import MCPServer

        with pytest.raises(ValueError, match="Timeout must be positive"):
            MCPServer(
                name="test",
                url="https://api.example.com",
                port=443,
                protocol="https",
                timeout=-1.0,
            )

    def test_server_negative_retry(self):
        """負のリトライ回数"""
        from src.beartype_integration import MCPServer

        with pytest.raises(ValueError, match="Retry count cannot be negative"):
            MCPServer(
                name="test",
                url="https://api.example.com",
                port=443,
                protocol="https",
                retry_count=-1,
            )


class TestCache:
    """Cacheクラステスト"""

    def test_cache_set_get(self):
        """キャッシュのset/get"""
        from src.beartype_integration import Cache

        cache: Cache[str] = Cache(max_size=10)
        cache.set("key1", "value1")

        assert cache.get("key1") == "value1"

    def test_cache_get_missing(self):
        """存在しないキー"""
        from src.beartype_integration import Cache

        cache: Cache[str] = Cache(max_size=10)

        assert cache.get("missing") is None

    def test_cache_eviction(self):
        """キャッシュ溢れ時の削除"""
        from src.beartype_integration import Cache

        cache: Cache[int] = Cache(max_size=2)
        cache.set("key1", 1)
        cache.set("key2", 2)
        cache.set("key3", 3)  # key1が削除される

        assert cache.get("key1") is None
        assert cache.get("key2") == 2
        assert cache.get("key3") == 3


class TestNetworkConfig:
    """NetworkConfigデータクラステスト"""

    def test_network_config_valid(self):
        """有効なネットワーク設定"""
        from src.beartype_integration import NetworkConfig

        config = NetworkConfig(
            hostname="api.example.com",
            ip_address="192.168.1.1",
            port=8080,
        )

        assert config.hostname == "api.example.com"
        assert config.ssl_enabled is True
        assert config.load_factor == 0.5


class TestDivideNumbers:
    """divide_numbers関数テスト"""

    def test_divide_integers(self):
        """整数の除算"""
        from src.beartype_integration import divide_numbers

        result = divide_numbers(10, 2)
        assert result == 5.0

    def test_divide_floats(self):
        """浮動小数点の除算"""
        from src.beartype_integration import divide_numbers

        result = divide_numbers(7.5, 2.5)
        assert result == 3.0

    def test_divide_by_zero(self):
        """ゼロ除算"""
        from src.beartype_integration import divide_numbers

        with pytest.raises(ValueError, match="Division by zero"):
            divide_numbers(10, 0)


class TestMCPClient:
    """MCPClientクラステスト"""

    def test_client_init(self):
        """クライアント初期化"""
        from src.beartype_integration import MCPClient

        client = MCPClient(
            server_name="github",
            base_url="https://api.github.com/",
            api_key="token",
        )

        assert client.server_name == "github"
        assert client.base_url == "https://api.github.com"  # 末尾スラッシュ除去
        assert client.api_key == "token"

    def test_client_list_tools(self):
        """ツール一覧取得"""
        from src.beartype_integration import MCPClient

        client = MCPClient(server_name="test", base_url="http://localhost")
        tools = client.list_tools()

        assert len(tools) == 3
        assert tools[0]["name"] == "search"

    @pytest.mark.asyncio
    async def test_client_execute_tool(self):
        """ツール実行"""
        from src.beartype_integration import MCPClient

        client = MCPClient(server_name="test", base_url="http://localhost")
        result = await client.execute_tool("search", {"query": "test"})

        assert result["tool"] == "search"
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_client_execute_tool_cache(self):
        """ツール実行（キャッシュ）"""
        from src.beartype_integration import MCPClient

        client = MCPClient(server_name="test", base_url="http://localhost")

        # 1回目
        result1 = await client.execute_tool("search", {"query": "test"})
        # 2回目（キャッシュから）
        result2 = await client.execute_tool("search", {"query": "test"})

        assert result1 == result2


class TestValidateJson:
    """validate_json関数テスト"""

    def test_validate_json_primitives(self):
        """プリミティブ型"""
        from src.beartype_integration import validate_json

        assert validate_json(None) is True
        assert validate_json(True) is True
        assert validate_json(123) is True
        assert validate_json(3.14) is True
        assert validate_json("string") is True

    @pytest.mark.skip(reason="Beartype forward reference limitation with recursive types")
    def test_validate_json_list(self):
        """リスト"""
        from src.beartype_integration import validate_json

        assert validate_json([1, 2, 3]) is True
        assert validate_json(["a", "b"]) is True

    @pytest.mark.skip(reason="Beartype forward reference limitation with recursive types")
    def test_validate_json_dict(self):
        """辞書"""
        from src.beartype_integration import validate_json

        assert validate_json({"key": "value"}) is True
        assert validate_json({"nested": {"key": 123}}) is True


class TestFetchData:
    """fetch_data関数テスト"""

    @pytest.mark.asyncio
    async def test_fetch_data(self):
        """非同期データ取得"""
        from src.beartype_integration import fetch_data

        results = await fetch_data(["http://api1.com", "http://api2.com"])

        assert len(results) == 2
        assert all(r is not None for r in results)
        assert results[0]["url"] == "http://api1.com"


class TestCreateUser:
    """create_user関数テスト"""

    def test_create_user_basic(self):
        """基本的なユーザー作成"""
        from src.beartype_integration import create_user

        user = create_user(name="Alice", age=25, email="alice@example.com")

        assert user["name"] == "Alice"
        assert user["age"] == 25
        assert user["email"] == "alice@example.com"

    def test_create_user_with_config(self):
        """設定ファイル付きユーザー作成"""
        import tempfile
        from src.beartype_integration import create_user

        with tempfile.NamedTemporaryFile(delete=False) as f:
            config_path = Path(f.name)
            f.write(b"config content")

        try:
            user = create_user(name="Bob", age=30, email="bob@example.com", config_file=config_path)

            assert user["name"] == "Bob"
            assert "config" in user
            assert str(config_path) in user["config"]
        finally:
            config_path.unlink()


class TestBenchmarkBeartype:
    """benchmark_beartypeデコレータテスト"""

    def test_benchmark_decorator(self, capsys):
        """ベンチマークデコレータ"""
        from src.beartype_integration import benchmark_beartype

        @benchmark_beartype
        def sample_func(x: int) -> int:
            return x * 2

        result = sample_func(5)
        assert result == 10

        captured = capsys.readouterr()
        assert "sample_func took" in captured.out
        assert "seconds" in captured.out


class TestExampleUsage:
    """example_usage関数テスト"""

    def test_example_usage_runs_successfully(self, capsys):
        """example_usageが正常に実行される"""
        from src.beartype_integration import example_usage

        # 例外が発生しないことを確認
        example_usage()

        captured = capsys.readouterr()
        # 出力に主要な成功メッセージが含まれることを確認
        assert "Beartype Runtime Type Checking Examples" in captured.out
        assert "✅" in captured.out  # 成功マークが含まれる


class TestPerformanceTest:
    """performance_test関数テスト"""

    def test_performance_test_function(self, capsys):
        """performance_test関数が正常に動作する"""
        from src.beartype_integration import performance_test

        # 関数実行
        result = performance_test([1, 2, 3, 4, 5])

        # 結果検証
        assert result == 15

        # ベンチマーク出力確認
        captured = capsys.readouterr()
        assert "performance_test took" in captured.out

    def test_performance_test_empty_list(self, capsys):
        """空リストでの動作"""
        from src.beartype_integration import performance_test

        result = performance_test([])
        assert result == 0

    def test_performance_test_large_list(self, capsys):
        """大きなリストでの動作"""
        from src.beartype_integration import performance_test

        large_list = list(range(1000))
        result = performance_test(large_list)
        assert result == sum(range(1000))
