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
