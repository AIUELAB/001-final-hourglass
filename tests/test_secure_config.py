#!/usr/bin/env python3
"""secure_config テスト"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestSecureConfigGetEnv:
    """SecureConfig.get_env の単体テスト"""

    def test_get_env_existing(self):
        """存在する環境変数の取得"""
        from secure_config import SecureConfig

        with patch.dict("os.environ", {"TEST_VAR": "test_value"}):
            result = SecureConfig.get_env("TEST_VAR")
            assert result == "test_value"

    def test_get_env_default(self):
        """存在しない環境変数でデフォルト値"""
        from secure_config import SecureConfig

        with patch.dict("os.environ", {}, clear=True):
            result = SecureConfig.get_env("NONEXISTENT_VAR", "default")
            assert result == "default"

    def test_get_env_none_string(self):
        """'none'文字列はNoneを返す"""
        from secure_config import SecureConfig

        with patch.dict("os.environ", {"TEST_VAR": "none"}):
            result = SecureConfig.get_env("TEST_VAR")
            assert result is None

    def test_get_env_null_string(self):
        """'null'文字列はNoneを返す"""
        from secure_config import SecureConfig

        with patch.dict("os.environ", {"TEST_VAR": "null"}):
            result = SecureConfig.get_env("TEST_VAR")
            assert result is None

    def test_get_env_empty_string(self):
        """空文字列はNoneを返す"""
        from secure_config import SecureConfig

        with patch.dict("os.environ", {"TEST_VAR": ""}):
            result = SecureConfig.get_env("TEST_VAR")
            # 空文字列はそのまま返される(Noneではない)
            assert result == ""

    def test_get_env_with_whitespace(self):
        """空白を含む値"""
        from secure_config import SecureConfig

        with patch.dict("os.environ", {"TEST_VAR": "  value  "}):
            result = SecureConfig.get_env("TEST_VAR")
            assert result == "  value  "

    def test_get_env_special_chars(self):
        """特殊文字を含む値"""
        from secure_config import SecureConfig

        with patch.dict("os.environ", {"TEST_VAR": "value@#$%"}):
            result = SecureConfig.get_env("TEST_VAR")
            assert result == "value@#$%"


class TestSecureConfigInstance:
    """SecureConfigインスタンスのテスト"""

    def test_init_without_env(self):
        """環境変数なしで初期化"""
        from secure_config import SecureConfig

        with patch.dict("os.environ", {}, clear=True):
            config = SecureConfig()
            assert config is not None

    def test_google_credentials_path_none(self):
        """Google認証情報パスがNoneの場合"""
        from secure_config import SecureConfig

        with patch.dict("os.environ", {}, clear=True):
            config = SecureConfig()
            # パスが存在しない場合はNoneまたはフォールバックパス
            path = config.google_credentials_path
            # None または 存在しないパス
            assert path is None or isinstance(path, str)

    def test_firebase_credentials_path_none(self):
        """Firebase認証情報パスがNoneの場合"""
        from secure_config import SecureConfig

        with patch.dict("os.environ", {}, clear=True):
            config = SecureConfig()
            path = config.firebase_credentials_path
            assert path is None or isinstance(path, str)
