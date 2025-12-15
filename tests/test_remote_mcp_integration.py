#!/usr/bin/env python3
"""remote_mcp_integration テスト"""

import sys
from pathlib import Path


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
