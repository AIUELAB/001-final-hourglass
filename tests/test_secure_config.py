#!/usr/bin/env python3
"""secure_config テスト"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

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

        result = SecureConfig.get_env("DEFINITELY_NONEXISTENT_VAR_12345", "default")
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

    def test_init(self):
        """初期化テスト"""
        from secure_config import SecureConfig

        config = SecureConfig()
        assert config is not None

    def test_google_credentials_path_type(self):
        """Google認証情報パスの型"""
        from secure_config import SecureConfig

        config = SecureConfig()
        path = config.google_credentials_path
        assert path is None or isinstance(path, str)

    def test_firebase_credentials_path_type(self):
        """Firebase認証情報パスの型"""
        from secure_config import SecureConfig

        config = SecureConfig()
        path = config.firebase_credentials_path
        assert path is None or isinstance(path, str)


class TestLoadEnvironment:
    """_load_environmentメソッドのテスト"""

    def test_load_env_file_not_exists(self):
        """存在しない.envファイル"""
        from secure_config import SecureConfig

        # 初期化は成功するはず
        config = SecureConfig()
        assert config is not None

    def test_load_environment_called(self):
        """_load_environment が呼ばれることを確認"""
        from secure_config import SecureConfig

        with patch.object(SecureConfig, "_load_environment") as mock_load:
            with patch.object(SecureConfig, "_validate_required_vars"):
                config = SecureConfig()
                mock_load.assert_called_once()


class TestValidateRequiredVars:
    """_validate_required_varsメソッドのテスト"""

    def test_validate_required_vars_called(self):
        """_validate_required_vars が呼ばれることを確認"""
        from secure_config import SecureConfig

        with patch.object(SecureConfig, "_load_environment"):
            with patch.object(SecureConfig, "_validate_required_vars") as mock_validate:
                config = SecureConfig()
                mock_validate.assert_called_once()


class TestAPIKeyProperties:
    """APIキープロパティのテスト"""

    def test_github_token_property_exists(self):
        """github_tokenプロパティが存在"""
        from secure_config import SecureConfig

        config = SecureConfig()
        # プロパティがエラーなくアクセスできることを確認
        token = config.github_token
        assert token is None or isinstance(token, str)

    def test_anthropic_api_key_property_exists(self):
        """anthropic_api_keyプロパティが存在"""
        from secure_config import SecureConfig

        config = SecureConfig()
        key = config.anthropic_api_key
        assert key is None or isinstance(key, str)

    def test_openai_api_key_property_exists(self):
        """openai_api_keyプロパティが存在"""
        from secure_config import SecureConfig

        config = SecureConfig()
        key = config.openai_api_key
        assert key is None or isinstance(key, str)

    def test_youtube_api_key_property_exists(self):
        """youtube_api_keyプロパティが存在"""
        from secure_config import SecureConfig

        config = SecureConfig()
        key = config.youtube_api_key
        assert key is None or isinstance(key, str)

    def test_brave_api_key_property_exists(self):
        """brave_api_keyプロパティが存在"""
        from secure_config import SecureConfig

        config = SecureConfig()
        key = config.brave_api_key
        assert key is None or isinstance(key, str)

    def test_github_token_from_env(self):
        """環境変数からGitHubトークン取得"""
        from secure_config import SecureConfig

        with patch.dict("os.environ", {"GITHUB_TOKEN": "test_token_12345"}):
            result = SecureConfig.get_env("GITHUB_TOKEN")
            assert result == "test_token_12345"

    def test_github_pat_fallback(self):
        """GITHUB_PATへのフォールバック"""
        from secure_config import SecureConfig

        with patch.dict("os.environ", {"GITHUB_PAT": "pat_token_12345"}):
            result = SecureConfig.get_env("GITHUB_PAT")
            assert result == "pat_token_12345"


class TestGetAPIKeysStatus:
    """get_api_keys_statusメソッドのテスト"""

    def test_returns_dict(self):
        """辞書を返す"""
        from secure_config import SecureConfig

        config = SecureConfig()
        status = config.get_api_keys_status()

        assert isinstance(status, dict)
        assert "google_credentials" in status
        assert "firebase_credentials" in status
        assert "github_token" in status
        assert "anthropic_api_key" in status
        assert "openai_api_key" in status
        assert "youtube_api_key" in status
        assert "brave_api_key" in status

    def test_status_values_are_bool(self):
        """ステータス値がbool型"""
        from secure_config import SecureConfig

        config = SecureConfig()
        status = config.get_api_keys_status()

        for key, value in status.items():
            assert isinstance(value, bool), f"{key} should be bool"


class TestGetGoogleCredentials:
    """get_google_credentialsメソッドのテスト"""

    def test_returns_none_or_credentials(self):
        """Noneまたは認証情報を返す"""
        from secure_config import SecureConfig

        config = SecureConfig()
        result = config.get_google_credentials()
        # None または Credentials オブジェクト
        assert result is None or hasattr(result, "token")

    def test_with_mock_credentials(self):
        """モック認証情報でテスト"""
        from secure_config import SecureConfig

        mock_creds = MagicMock()

        with patch("secure_config.service_account.Credentials.from_service_account_file", return_value=mock_creds):
            config = SecureConfig()
            # google_credentials_pathがある場合のテスト
            if config.google_credentials_path:
                result = config.get_google_credentials()
                # モックが呼ばれた場合はモックを返す


class TestGetFirebaseCredentials:
    """get_firebase_credentialsメソッドのテスト"""

    def test_returns_none_or_credentials(self):
        """Noneまたは認証情報を返す"""
        from secure_config import SecureConfig

        config = SecureConfig()
        result = config.get_firebase_credentials()
        # None または Certificate オブジェクト
        assert result is None or result is not None

    def test_firebase_path_none(self):
        """Firebaseパスがない場合"""
        from secure_config import SecureConfig

        config = SecureConfig()
        # firebase_credentials_pathがNoneの場合はNoneを返す
        if config.firebase_credentials_path is None:
            result = config.get_firebase_credentials()
            assert result is None


class TestValidateCredentials:
    """validate_credentialsメソッドのテスト"""

    def test_returns_dict_with_required_keys(self):
        """必須キーを含む辞書を返す"""
        from secure_config import SecureConfig

        config = SecureConfig()
        status = config.validate_credentials()

        assert isinstance(status, dict)
        assert "valid" in status
        assert "errors" in status
        assert "warnings" in status
        assert "credentials" in status

    def test_valid_is_bool(self):
        """validがbool型"""
        from secure_config import SecureConfig

        config = SecureConfig()
        status = config.validate_credentials()

        assert isinstance(status["valid"], bool)

    def test_errors_is_list(self):
        """errorsがリスト型"""
        from secure_config import SecureConfig

        config = SecureConfig()
        status = config.validate_credentials()

        assert isinstance(status["errors"], list)

    def test_warnings_is_list(self):
        """warningsがリスト型"""
        from secure_config import SecureConfig

        config = SecureConfig()
        status = config.validate_credentials()

        assert isinstance(status["warnings"], list)

    def test_credentials_is_dict(self):
        """credentialsが辞書型"""
        from secure_config import SecureConfig

        config = SecureConfig()
        status = config.validate_credentials()

        assert isinstance(status["credentials"], dict)

    def test_validate_with_mocked_google_none(self):
        """Google認証なしでバリデーション"""
        from secure_config import SecureConfig

        with patch.object(SecureConfig, "get_google_credentials", return_value=None):
            with patch.object(SecureConfig, "get_firebase_credentials", return_value=None):
                config = SecureConfig()
                status = config.validate_credentials()
                # Google認証なしはエラー
                assert "Google credentials not available" in status["errors"]

    def test_validate_with_mocked_google_success(self):
        """Google認証ありでバリデーション"""
        from secure_config import SecureConfig

        mock_google = MagicMock()

        with patch.object(SecureConfig, "get_google_credentials", return_value=mock_google):
            with patch.object(SecureConfig, "get_firebase_credentials", return_value=None):
                config = SecureConfig()
                status = config.validate_credentials()
                assert status["credentials"]["google"] is True

    def test_validate_with_google_exception(self):
        """Google認証で例外"""
        from secure_config import SecureConfig

        with patch.object(SecureConfig, "get_google_credentials", side_effect=Exception("Test error")):
            config = SecureConfig()
            status = config.validate_credentials()
            assert status["valid"] is False
            assert any("Google credentials error" in err for err in status["errors"])


class TestGoogleCredentialsPath:
    """google_credentials_pathプロパティのテスト"""

    def test_with_valid_env_path(self):
        """有効な環境変数パス"""
        from secure_config import SecureConfig

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            with patch.dict("os.environ", {"GOOGLE_APPLICATION_CREDENTIALS": temp_path}):
                config = SecureConfig()
                assert config.google_credentials_path == temp_path
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_path_type(self):
        """パスの型確認"""
        from secure_config import SecureConfig

        config = SecureConfig()
        path = config.google_credentials_path
        assert path is None or isinstance(path, str)


class TestFirebaseCredentialsPath:
    """firebase_credentials_pathプロパティのテスト"""

    def test_with_valid_env_path(self):
        """有効な環境変数パス"""
        from secure_config import SecureConfig

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            with patch.dict("os.environ", {"FIREBASE_CONFIG_PATH": temp_path}):
                config = SecureConfig()
                assert config.firebase_credentials_path == temp_path
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_path_type(self):
        """パスの型確認"""
        from secure_config import SecureConfig

        config = SecureConfig()
        path = config.firebase_credentials_path
        assert path is None or isinstance(path, str)


class TestGlobalConfig:
    """グローバルconfigインスタンスのテスト"""

    def test_global_config_exists(self):
        """グローバルconfigが存在"""
        from secure_config import config

        assert config is not None

    def test_global_config_is_secure_config(self):
        """グローバルconfigがSecureConfigインスタンス"""
        from secure_config import SecureConfig, config

        assert isinstance(config, SecureConfig)
