#!/usr/bin/env python3
"""remote_mcp_integration テスト"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from remote_mcp_integration import AuthType, RemoteServerConfig, TransportType


class TestTransportType:
    """TransportTypeのテスト"""

    def test_sse(self):
        assert TransportType.SSE.value == "sse"

    def test_http(self):
        assert TransportType.HTTP.value == "http"

    def test_stdio(self):
        assert TransportType.STDIO.value == "stdio"

    def test_count(self):
        assert len(TransportType) == 3


class TestAuthType:
    """AuthTypeのテスト"""

    def test_none(self):
        assert AuthType.NONE.value == "none"

    def test_api_key(self):
        assert AuthType.API_KEY.value == "api_key"

    def test_bearer(self):
        assert AuthType.BEARER.value == "bearer"

    def test_oauth2(self):
        assert AuthType.OAUTH2.value == "oauth2"

    def test_custom(self):
        assert AuthType.CUSTOM.value == "custom"


class TestRemoteServerConfig:
    """RemoteServerConfigのテスト"""

    def test_minimal(self):
        """最小構成"""
        config = RemoteServerConfig(
            name="test-server", transport=TransportType.SSE, url="https://example.com/mcp", auth_type=AuthType.NONE
        )
        assert config.name == "test-server"
        assert config.transport == TransportType.SSE
        assert config.auth_type == AuthType.NONE

    def test_defaults(self):
        """デフォルト値"""
        config = RemoteServerConfig(
            name="test", transport=TransportType.HTTP, url="https://example.com", auth_type=AuthType.API_KEY
        )
        assert config.timeout == 30000
        assert config.retry_attempts == 3
        assert config.tls_verify is True
        assert config.headers is None
        assert config.oauth_config is None

    def test_with_headers(self):
        """ヘッダー付き"""
        config = RemoteServerConfig(
            name="test",
            transport=TransportType.HTTP,
            url="https://example.com",
            auth_type=AuthType.BEARER,
            headers={"Authorization": "Bearer token123"},
        )
        assert config.headers["Authorization"] == "Bearer token123"

    def test_custom_timeout(self):
        """カスタムタイムアウト"""
        config = RemoteServerConfig(
            name="test", transport=TransportType.SSE, url="https://example.com", auth_type=AuthType.NONE, timeout=60000
        )
        assert config.timeout == 60000

    def test_tls_verify_disabled(self):
        """TLS検証無効"""
        config = RemoteServerConfig(
            name="test",
            transport=TransportType.HTTP,
            url="https://example.com",
            auth_type=AuthType.NONE,
            tls_verify=False,
        )
        assert config.tls_verify is False

    def test_retry_attempts(self):
        """リトライ回数設定"""
        config = RemoteServerConfig(
            name="test",
            transport=TransportType.HTTP,
            url="https://example.com",
            auth_type=AuthType.NONE,
            retry_attempts=5,
        )
        assert config.retry_attempts == 5


class TestOAuthToken:
    """OAuthTokenのテスト"""

    def test_token_creation(self):
        """トークン作成"""
        from datetime import datetime, timedelta

        from remote_mcp_integration import OAuthToken

        future_time = datetime.now() + timedelta(hours=1)
        token = OAuthToken(
            access_token="test_token",
            token_type="Bearer",
            expires_at=future_time,
        )
        assert token.access_token == "test_token"
        assert token.token_type == "Bearer"

    def test_token_not_expired(self):
        """有効期限内トークン"""
        from datetime import datetime, timedelta

        from remote_mcp_integration import OAuthToken

        future_time = datetime.now() + timedelta(hours=1)
        token = OAuthToken(
            access_token="test_token",
            token_type="Bearer",
            expires_at=future_time,
        )
        assert token.is_expired is False

    def test_token_expired(self):
        """期限切れトークン"""
        from datetime import datetime, timedelta

        from remote_mcp_integration import OAuthToken

        past_time = datetime.now() - timedelta(hours=1)
        token = OAuthToken(
            access_token="test_token",
            token_type="Bearer",
            expires_at=past_time,
        )
        assert token.is_expired is True

    def test_token_needs_refresh(self):
        """リフレッシュ必要トークン"""
        from datetime import datetime, timedelta

        from remote_mcp_integration import OAuthToken

        almost_expired = datetime.now() + timedelta(minutes=3)
        token = OAuthToken(
            access_token="test_token",
            token_type="Bearer",
            expires_at=almost_expired,
        )
        assert token.needs_refresh is True

    def test_token_no_refresh_needed(self):
        """リフレッシュ不要トークン"""
        from datetime import datetime, timedelta

        from remote_mcp_integration import OAuthToken

        future_time = datetime.now() + timedelta(hours=1)
        token = OAuthToken(
            access_token="test_token",
            token_type="Bearer",
            expires_at=future_time,
        )
        assert token.needs_refresh is False

    def test_token_with_refresh_token(self):
        """リフレッシュトークン付き"""
        from datetime import datetime, timedelta

        from remote_mcp_integration import OAuthToken

        token = OAuthToken(
            access_token="test_token",
            token_type="Bearer",
            expires_at=datetime.now() + timedelta(hours=1),
            refresh_token="refresh_token",
        )
        assert token.refresh_token == "refresh_token"

    def test_token_with_scope(self):
        """スコープ付きトークン"""
        from datetime import datetime, timedelta

        from remote_mcp_integration import OAuthToken

        token = OAuthToken(
            access_token="test_token",
            token_type="Bearer",
            expires_at=datetime.now() + timedelta(hours=1),
            scope="read write",
        )
        assert token.scope == "read write"


class TestRemoteMCPClient:
    """RemoteMCPClientのテスト"""

    def test_client_init(self):
        """クライアント初期化"""
        from remote_mcp_integration import RemoteMCPClient

        config = RemoteServerConfig(
            name="test",
            transport=TransportType.HTTP,
            url="https://example.com",
            auth_type=AuthType.NONE,
        )
        client = RemoteMCPClient(config)
        assert client.config == config
        assert client.session is None
        assert client.token is None


class TestRemoteMCPClientAsync:
    """RemoteMCPClient非同期メソッドテスト"""

    @pytest.fixture
    def http_config(self):
        """HTTP設定フィクスチャ"""
        return RemoteServerConfig(
            name="test-http",
            transport=TransportType.HTTP,
            url="https://example.com/mcp",
            auth_type=AuthType.NONE,
        )

    @pytest.fixture
    def sse_config(self):
        """SSE設定フィクスチャ"""
        return RemoteServerConfig(
            name="test-sse",
            transport=TransportType.SSE,
            url="https://example.com/sse",
            auth_type=AuthType.NONE,
        )

    @pytest.fixture
    def api_key_config(self):
        """API Key認証設定"""
        return RemoteServerConfig(
            name="test-api",
            transport=TransportType.HTTP,
            url="https://example.com/mcp",
            auth_type=AuthType.API_KEY,
            headers={"X-API-Key": "test-key-123"},
        )

    @pytest.fixture
    def bearer_config(self):
        """Bearer認証設定"""
        return RemoteServerConfig(
            name="test-bearer",
            transport=TransportType.HTTP,
            url="https://example.com/mcp",
            auth_type=AuthType.BEARER,
            headers={"Authorization": "Bearer token123"},
        )

    @pytest.fixture
    def oauth_config(self):
        """OAuth2設定フィクスチャ"""
        return RemoteServerConfig(
            name="test-oauth",
            transport=TransportType.HTTP,
            url="https://example.com/mcp",
            auth_type=AuthType.OAUTH2,
            oauth_config={
                "tokenEndpoint": "https://auth.example.com/token",
                "clientId": "client123",
                "clientSecret": "secret456",
                "scope": "read write",
            },
        )

    @pytest.mark.asyncio
    async def test_connect_http_success(self, http_config):
        """HTTP接続成功"""
        from contextlib import asynccontextmanager
        from unittest.mock import AsyncMock, MagicMock, patch

        from remote_mcp_integration import RemoteMCPClient

        client = RemoteMCPClient(http_config)

        mock_response = MagicMock()
        mock_response.status = 200

        @asynccontextmanager
        async def mock_get(*args, **kwargs):
            yield mock_response

        mock_session = MagicMock()
        mock_session.get = mock_get
        mock_session.close = AsyncMock()

        with patch("aiohttp.ClientSession", return_value=mock_session), patch("aiohttp.TCPConnector"):
            await client.connect()

            assert client.session is not None

    @pytest.mark.asyncio
    async def test_connect_sse_success(self, sse_config):
        """SSE接続成功"""
        from unittest.mock import AsyncMock, patch

        from remote_mcp_integration import RemoteMCPClient

        client = RemoteMCPClient(sse_config)

        mock_session = AsyncMock()

        with patch("aiohttp.ClientSession", return_value=mock_session), patch("aiohttp.TCPConnector"):
            await client.connect()

            assert client.session is not None

    @pytest.mark.asyncio
    async def test_disconnect(self, http_config):
        """切断テスト"""
        from unittest.mock import AsyncMock, patch

        from remote_mcp_integration import RemoteMCPClient

        client = RemoteMCPClient(http_config)

        mock_session = AsyncMock()
        mock_session.close = AsyncMock()

        client.session = mock_session

        await client.disconnect()

        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_auth_headers_api_key(self, api_key_config):
        """API Key認証ヘッダー取得"""
        from remote_mcp_integration import RemoteMCPClient

        client = RemoteMCPClient(api_key_config)
        headers = await client._get_auth_headers()

        assert headers.get("X-API-Key") == "test-key-123"

    @pytest.mark.asyncio
    async def test_get_auth_headers_bearer(self, bearer_config):
        """Bearer認証ヘッダー取得"""
        from remote_mcp_integration import RemoteMCPClient

        client = RemoteMCPClient(bearer_config)
        headers = await client._get_auth_headers()

        assert headers.get("Authorization") == "Bearer token123"

    @pytest.mark.asyncio
    async def test_get_auth_headers_none(self, http_config):
        """認証なしヘッダー"""
        from remote_mcp_integration import RemoteMCPClient

        client = RemoteMCPClient(http_config)
        headers = await client._get_auth_headers()

        assert headers == {}

    @pytest.mark.asyncio
    async def test_send_request_http_success(self, http_config):
        """HTTPリクエスト送信成功"""
        from contextlib import asynccontextmanager
        from unittest.mock import AsyncMock, MagicMock

        from remote_mcp_integration import RemoteMCPClient

        client = RemoteMCPClient(http_config)

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"result": {"data": "test"}})

        @asynccontextmanager
        async def mock_post(*args, **kwargs):
            yield mock_response

        mock_session = MagicMock()
        mock_session.post = mock_post
        mock_session.headers = MagicMock()

        client.session = mock_session

        result = await client.send_request("testMethod", {"param": "value"})

        assert result == {"data": "test"}

    @pytest.mark.asyncio
    async def test_send_request_not_connected(self, http_config):
        """未接続時のリクエストエラー"""
        from remote_mcp_integration import RemoteMCPClient

        client = RemoteMCPClient(http_config)

        with pytest.raises(RuntimeError, match="Not connected"):
            await client.send_request("testMethod")

    @pytest.mark.asyncio
    async def test_send_http_request_retry(self, http_config):
        """HTTPリクエストリトライ"""
        from contextlib import asynccontextmanager
        from unittest.mock import AsyncMock, MagicMock

        from remote_mcp_integration import RemoteMCPClient

        http_config.retry_attempts = 3
        client = RemoteMCPClient(http_config)

        # 最初の2回は500エラー、3回目は成功
        mock_responses = []
        for i in range(2):
            r = MagicMock()
            r.status = 500
            mock_responses.append(r)

        success_response = MagicMock()
        success_response.status = 200
        success_response.json = AsyncMock(return_value={"result": "success"})
        mock_responses.append(success_response)

        call_count = [0]

        @asynccontextmanager
        async def mock_post(*args, **kwargs):
            response = mock_responses[min(call_count[0], len(mock_responses) - 1)]
            call_count[0] += 1
            yield response

        mock_session = MagicMock()
        mock_session.post = mock_post

        client.session = mock_session

        result = await client._send_http_request({"method": "test"})

        assert result == "success"

    @pytest.mark.asyncio
    async def test_context_manager(self, http_config):
        """コンテキストマネージャーテスト"""
        from contextlib import asynccontextmanager
        from unittest.mock import AsyncMock, MagicMock, patch

        from remote_mcp_integration import RemoteMCPClient

        mock_response = MagicMock()
        mock_response.status = 200

        @asynccontextmanager
        async def mock_get(*args, **kwargs):
            yield mock_response

        mock_session = MagicMock()
        mock_session.get = mock_get
        mock_session.close = AsyncMock()

        with patch("aiohttp.ClientSession", return_value=mock_session), patch("aiohttp.TCPConnector"):
            async with RemoteMCPClient(http_config) as client:
                assert client.session is not None

    @pytest.mark.asyncio
    async def test_connect_sse_configures_endpoint(self, sse_config):
        """SSE接続でエンドポイント設定"""
        from unittest.mock import AsyncMock, patch

        from remote_mcp_integration import RemoteMCPClient

        client = RemoteMCPClient(sse_config)

        mock_session = AsyncMock()

        with patch("aiohttp.ClientSession", return_value=mock_session), patch("aiohttp.TCPConnector"):
            await client.connect()
            # SSE接続ではセッションが作成される
            assert client.session is mock_session

    @pytest.mark.asyncio
    async def test_test_connection_404_allowed(self, http_config):
        """接続テストで404は許可"""
        from contextlib import asynccontextmanager
        from unittest.mock import MagicMock

        from remote_mcp_integration import RemoteMCPClient

        client = RemoteMCPClient(http_config)

        mock_response = MagicMock()
        mock_response.status = 404

        @asynccontextmanager
        async def mock_get(*args, **kwargs):
            yield mock_response

        mock_session = MagicMock()
        mock_session.get = mock_get

        client.session = mock_session

        # 404は例外を発生させない
        await client._test_connection()

    @pytest.mark.asyncio
    async def test_get_oauth_token_new(self, oauth_config):
        """新規OAuthトークン取得"""
        from contextlib import asynccontextmanager
        from datetime import datetime, timedelta
        from unittest.mock import AsyncMock, MagicMock, patch

        from remote_mcp_integration import RemoteMCPClient

        client = RemoteMCPClient(oauth_config)

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "access_token": "new_token",
                "token_type": "Bearer",
                "expires_in": 3600,
            }
        )

        @asynccontextmanager
        async def mock_post(*args, **kwargs):
            yield mock_response

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session_instance = MagicMock()
            mock_session_instance.post = mock_post
            mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
            mock_session_instance.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session_instance

            token = await client._request_oauth_token()

            assert token.access_token == "new_token"
            assert token.token_type == "Bearer"

    @pytest.mark.asyncio
    async def test_get_oauth_token_missing_config(self):
        """OAuth設定なしでエラー"""
        from remote_mcp_integration import RemoteMCPClient

        config = RemoteServerConfig(
            name="no-oauth",
            transport=TransportType.HTTP,
            url="https://example.com",
            auth_type=AuthType.OAUTH2,
            oauth_config=None,
        )

        client = RemoteMCPClient(config)

        with pytest.raises(ValueError, match="OAuth config missing"):
            await client._request_oauth_token()

    @pytest.mark.asyncio
    async def test_get_oauth_token_missing_credentials(self):
        """OAuth認証情報不足でエラー"""
        from remote_mcp_integration import RemoteMCPClient

        config = RemoteServerConfig(
            name="partial-oauth",
            transport=TransportType.HTTP,
            url="https://example.com",
            auth_type=AuthType.OAUTH2,
            oauth_config={
                "tokenEndpoint": "https://auth.example.com/token",
                # clientId と clientSecret がない
            },
        )

        client = RemoteMCPClient(config)

        with pytest.raises(ValueError, match="Missing OAuth credentials"):
            await client._request_oauth_token()

    @pytest.mark.asyncio
    async def test_get_oauth_token_cached(self, oauth_config):
        """キャッシュ済みトークン取得"""
        from datetime import datetime, timedelta

        from remote_mcp_integration import OAuthToken, RemoteMCPClient

        client = RemoteMCPClient(oauth_config)

        # 有効なトークンをセット
        client.token = OAuthToken(
            access_token="cached_token",
            token_type="Bearer",
            expires_at=datetime.now() + timedelta(hours=1),
        )

        token = await client._get_oauth_token()

        assert token.access_token == "cached_token"

    @pytest.mark.asyncio
    async def test_send_request_sse(self, sse_config):
        """SSEリクエスト送信"""
        from contextlib import asynccontextmanager
        from unittest.mock import AsyncMock, MagicMock

        from remote_mcp_integration import RemoteMCPClient

        client = RemoteMCPClient(sse_config)

        # SSEレスポンスをシミュレート
        async def mock_iter_lines():
            yield b'data: {"id": "test123", "result": "sse_data"}\n'

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.content = mock_iter_lines()

        @asynccontextmanager
        async def mock_post(*args, **kwargs):
            yield mock_response

        mock_session = MagicMock()
        mock_session.post = mock_post
        mock_session.headers = MagicMock()

        client.session = mock_session

        # send_requestを直接呼び出すとIDが生成されるので、_send_sse_requestを呼ぶ
        result = await client._send_sse_request({"id": "test123", "method": "test"})

        assert result == "sse_data"

    @pytest.mark.asyncio
    async def test_disconnect_with_sse_client(self, sse_config):
        """SSEクライアント付き切断"""
        from unittest.mock import AsyncMock, MagicMock

        from remote_mcp_integration import RemoteMCPClient

        client = RemoteMCPClient(sse_config)

        mock_session = AsyncMock()
        mock_session.close = AsyncMock()

        mock_sse = MagicMock()
        mock_sse.close = MagicMock()

        client.session = mock_session
        client.sse_client = mock_sse

        await client.disconnect()

        mock_sse.close.assert_called_once()
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_sse_no_session_error(self, sse_config):
        """セッションなしでSSE接続エラー"""
        from remote_mcp_integration import RemoteMCPClient

        client = RemoteMCPClient(sse_config)
        client.session = None

        with pytest.raises(RuntimeError, match="Session not initialized"):
            client._connect_sse()

    @pytest.mark.asyncio
    async def test_test_connection_no_session_error(self, http_config):
        """セッションなしで接続テストエラー"""
        from remote_mcp_integration import RemoteMCPClient

        client = RemoteMCPClient(http_config)
        client.session = None

        with pytest.raises(RuntimeError, match="Session not initialized"):
            await client._test_connection()


class TestRemoteMCPManager:
    """RemoteMCPManagerのテスト"""

    def test_init_no_config_file(self):
        """設定ファイルなしで初期化"""
        from unittest.mock import patch

        from remote_mcp_integration import RemoteMCPManager

        with patch("os.path.exists", return_value=False):
            manager = RemoteMCPManager("nonexistent.json")

            assert manager.servers == {}

    def test_init_with_config_file(self, tmp_path):
        """設定ファイルありで初期化"""
        import json

        from remote_mcp_integration import RemoteMCPManager

        config_file = tmp_path / "remote-servers.json"
        config_data = {
            "remoteMcpServers": {
                "test-server": {
                    "url": "https://example.com/mcp",
                    "transport": "http",
                }
            }
        }
        with open(config_file, "w") as f:
            json.dump(config_data, f)

        manager = RemoteMCPManager(str(config_file))

        assert "test-server" in manager.servers

    def test_add_server(self):
        """サーバー追加"""
        from unittest.mock import patch

        from remote_mcp_integration import RemoteMCPManager

        with patch("os.path.exists", return_value=False):
            manager = RemoteMCPManager()

            manager.add_server(
                "new-server",
                {
                    "url": "https://new.example.com",
                    "transport": "http",
                },
            )

            assert "new-server" in manager.servers

    def test_determine_auth_type_oauth2(self):
        """OAuth2認証タイプ判定"""
        from unittest.mock import patch

        from remote_mcp_integration import RemoteMCPManager

        with patch("os.path.exists", return_value=False):
            manager = RemoteMCPManager()

            auth_type = manager._determine_auth_type({"authentication": {"type": "oauth2"}})

            assert auth_type == AuthType.OAUTH2

    def test_determine_auth_type_bearer(self):
        """Bearer認証タイプ判定"""
        from unittest.mock import patch

        from remote_mcp_integration import RemoteMCPManager

        with patch("os.path.exists", return_value=False):
            manager = RemoteMCPManager()

            auth_type = manager._determine_auth_type({"authentication": {"type": "bearer"}})

            assert auth_type == AuthType.BEARER

    def test_determine_auth_type_api_key(self):
        """API Key認証タイプ判定"""
        from unittest.mock import patch

        from remote_mcp_integration import RemoteMCPManager

        with patch("os.path.exists", return_value=False):
            manager = RemoteMCPManager()

            auth_type = manager._determine_auth_type({"authentication": {"type": "api_key"}})

            assert auth_type == AuthType.API_KEY

    def test_determine_auth_type_from_headers_bearer(self):
        """ヘッダーからBearer認証判定"""
        from unittest.mock import patch

        from remote_mcp_integration import RemoteMCPManager

        with patch("os.path.exists", return_value=False):
            manager = RemoteMCPManager()

            auth_type = manager._determine_auth_type({"headers": {"Authorization": "Bearer token"}})

            assert auth_type == AuthType.BEARER

    def test_determine_auth_type_from_headers_api_key(self):
        """ヘッダーからAPI Key認証判定"""
        from unittest.mock import patch

        from remote_mcp_integration import RemoteMCPManager

        with patch("os.path.exists", return_value=False):
            manager = RemoteMCPManager()

            auth_type = manager._determine_auth_type({"headers": {"X-API-Key": "key123"}})

            assert auth_type == AuthType.API_KEY

    def test_determine_auth_type_none(self):
        """認証なし判定"""
        from unittest.mock import patch

        from remote_mcp_integration import RemoteMCPManager

        with patch("os.path.exists", return_value=False):
            manager = RemoteMCPManager()

            auth_type = manager._determine_auth_type({})

            assert auth_type == AuthType.NONE

    def test_expand_env_vars(self):
        """環境変数展開"""
        import os
        from unittest.mock import patch

        from remote_mcp_integration import RemoteMCPManager

        with patch("os.path.exists", return_value=False):
            manager = RemoteMCPManager()

            with patch.dict(os.environ, {"TEST_VAR": "expanded_value"}):
                result = manager._expand_env_vars("prefix_${TEST_VAR}_suffix")

                assert result == "prefix_expanded_value_suffix"

    def test_expand_env_vars_no_var(self):
        """環境変数なしの場合"""
        from unittest.mock import patch

        from remote_mcp_integration import RemoteMCPManager

        with patch("os.path.exists", return_value=False):
            manager = RemoteMCPManager()

            result = manager._expand_env_vars("no_variables_here")

            assert result == "no_variables_here"

    def test_expand_env_vars_missing_var(self):
        """未定義環境変数"""
        from unittest.mock import patch

        from remote_mcp_integration import RemoteMCPManager

        with patch("os.path.exists", return_value=False):
            manager = RemoteMCPManager()

            result = manager._expand_env_vars("${UNDEFINED_VAR}")

            assert result == "${UNDEFINED_VAR}"

    def test_expand_headers(self):
        """ヘッダー内環境変数展開"""
        import os
        from unittest.mock import patch

        from remote_mcp_integration import RemoteMCPManager

        with patch("os.path.exists", return_value=False):
            manager = RemoteMCPManager()

            with patch.dict(os.environ, {"API_KEY": "secret123"}):
                result = manager._expand_headers({"X-API-Key": "${API_KEY}"})

                assert result["X-API-Key"] == "secret123"

    def test_get_server_exists(self):
        """存在するサーバー取得"""
        from unittest.mock import patch

        from remote_mcp_integration import RemoteMCPManager

        with patch("os.path.exists", return_value=False):
            manager = RemoteMCPManager()
            manager.add_server("test", {"url": "https://example.com", "transport": "http"})

            server = manager.get_server("test")

            assert server is not None

    def test_get_server_not_exists(self):
        """存在しないサーバー取得"""
        from unittest.mock import patch

        from remote_mcp_integration import RemoteMCPManager

        with patch("os.path.exists", return_value=False):
            manager = RemoteMCPManager()

            server = manager.get_server("nonexistent")

            assert server is None

    @pytest.mark.asyncio
    async def test_connect_all(self):
        """全サーバー接続"""
        from unittest.mock import AsyncMock, patch

        from remote_mcp_integration import RemoteMCPManager

        with patch("os.path.exists", return_value=False):
            manager = RemoteMCPManager()

            # モックサーバーを追加
            mock_server1 = AsyncMock()
            mock_server1.connect = AsyncMock()
            mock_server2 = AsyncMock()
            mock_server2.connect = AsyncMock()

            manager.servers = {"server1": mock_server1, "server2": mock_server2}

            await manager.connect_all()

            mock_server1.connect.assert_called_once()
            mock_server2.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_all(self):
        """全サーバー切断"""
        from unittest.mock import AsyncMock, patch

        from remote_mcp_integration import RemoteMCPManager

        with patch("os.path.exists", return_value=False):
            manager = RemoteMCPManager()

            mock_server = AsyncMock()
            mock_server.disconnect = AsyncMock()

            manager.servers = {"server1": mock_server}

            await manager.disconnect_all()

            mock_server.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_test_connectivity_success(self):
        """接続テスト成功"""
        from unittest.mock import AsyncMock, patch

        from remote_mcp_integration import RemoteMCPManager

        with patch("os.path.exists", return_value=False):
            manager = RemoteMCPManager()

            mock_server = AsyncMock()
            mock_server.connect = AsyncMock()
            mock_server.disconnect = AsyncMock()

            manager.servers = {"server1": mock_server}

            results = await manager.test_connectivity()

            assert results["server1"] is True

    @pytest.mark.asyncio
    async def test_test_connectivity_failure(self):
        """接続テスト失敗"""
        from unittest.mock import AsyncMock, patch

        from remote_mcp_integration import RemoteMCPManager

        with patch("os.path.exists", return_value=False):
            manager = RemoteMCPManager()

            mock_server = AsyncMock()
            mock_server.connect = AsyncMock(side_effect=Exception("Connection failed"))

            manager.servers = {"server1": mock_server}

            results = await manager.test_connectivity()

            assert results["server1"] is False
