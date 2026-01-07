"""
Multi-Provider Tests - Phase 5 マルチプロバイダのテスト
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.sage.adapters import (
    AutoProviderAdapter,
    Candidate,
    MultiProviderAdapter,
    ProviderConfig,
    ProviderType,
    create_client,
    get_available_providers,
    get_cheapest_provider,
)
from scripts.sage.adapters.providers import (
    PROVIDER_CONFIGS,
    PROVIDER_PRICING,
    AnthropicClient,
    GoogleClient,
    LLMClient,
    OpenAIClient,
)


class TestProviderType:
    """ProviderType のテスト"""

    def test_enum_values(self):
        """Enum値の確認"""
        assert ProviderType.ANTHROPIC.value == "anthropic"
        assert ProviderType.OPENAI.value == "openai"
        assert ProviderType.GOOGLE.value == "google"

    def test_all_providers_have_config(self):
        """全プロバイダに設定がある"""
        for provider in ProviderType:
            assert provider in PROVIDER_CONFIGS


class TestProviderConfig:
    """ProviderConfig のテスト"""

    def test_default_anthropic_config(self):
        """Anthropicデフォルト設定"""
        config = PROVIDER_CONFIGS[ProviderType.ANTHROPIC]
        assert config.provider_type == ProviderType.ANTHROPIC
        assert "claude" in config.model_name
        assert config.api_key_env == "ANTHROPIC_API_KEY"

    def test_default_openai_config(self):
        """OpenAIデフォルト設定"""
        config = PROVIDER_CONFIGS[ProviderType.OPENAI]
        assert config.provider_type == ProviderType.OPENAI
        assert "gpt" in config.model_name
        assert config.api_key_env == "OPENAI_API_KEY"

    def test_default_google_config(self):
        """Googleデフォルト設定"""
        config = PROVIDER_CONFIGS[ProviderType.GOOGLE]
        assert config.provider_type == ProviderType.GOOGLE
        assert "gemini" in config.model_name
        assert config.api_key_env == "GOOGLE_API_KEY"

    def test_api_key_from_env(self):
        """環境変数からAPIキー取得"""
        with patch.dict(os.environ, {"TEST_API_KEY": "test123"}):
            config = ProviderConfig(
                provider_type=ProviderType.ANTHROPIC,
                model_name="test-model",
                api_key_env="TEST_API_KEY",
            )
            assert config.api_key == "test123"


class TestProviderPricing:
    """PROVIDER_PRICING のテスト"""

    def test_all_providers_have_pricing(self):
        """全プロバイダに料金設定がある"""
        for provider in ProviderType:
            assert provider in PROVIDER_PRICING

    def test_pricing_structure(self):
        """料金構造の確認"""
        for provider, models in PROVIDER_PRICING.items():
            for model, prices in models.items():
                assert "input" in prices
                assert "output" in prices
                assert prices["input"] >= 0
                assert prices["output"] >= 0


class TestLLMClient:
    """LLMClient のテスト"""

    def test_anthropic_client_requires_api_key(self):
        """AnthropicClientはAPIキーが必要"""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
                AnthropicClient()

    def test_openai_client_requires_api_key(self):
        """OpenAIClientはAPIキーが必要"""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("OPENAI_API_KEY", None)
            with pytest.raises(ValueError, match="OPENAI_API_KEY"):
                OpenAIClient()

    def test_google_client_requires_api_key(self):
        """GoogleClientはAPIキーが必要"""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("GOOGLE_API_KEY", None)
            with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
                GoogleClient()


class TestCreateClient:
    """create_client のテスト"""

    def test_create_anthropic_client(self):
        """Anthropicクライアント作成"""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test"}):
            client = create_client(ProviderType.ANTHROPIC)
            assert isinstance(client, AnthropicClient)

    def test_create_openai_client(self):
        """OpenAIクライアント作成"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test"}):
            client = create_client(ProviderType.OPENAI)
            assert isinstance(client, OpenAIClient)

    def test_create_google_client(self):
        """Googleクライアント作成"""
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test"}):
            client = create_client(ProviderType.GOOGLE)
            assert isinstance(client, GoogleClient)


class TestGetAvailableProviders:
    """get_available_providers のテスト"""

    def test_returns_providers_with_api_keys(self):
        """APIキーがあるプロバイダを返す"""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test"}, clear=True):
            available = get_available_providers()
            assert ProviderType.ANTHROPIC in available

    def test_excludes_providers_without_api_keys(self):
        """APIキーがないプロバイダは除外"""
        with patch.dict(os.environ, {}, clear=True):
            # 全ての環境変数をクリア
            os.environ.pop("ANTHROPIC_API_KEY", None)
            os.environ.pop("OPENAI_API_KEY", None)
            os.environ.pop("GOOGLE_API_KEY", None)
            available = get_available_providers()
            assert len(available) == 0


class TestGetCheapestProvider:
    """get_cheapest_provider のテスト"""

    def test_returns_cheapest_available(self):
        """最安プロバイダを返す"""
        with patch.dict(
            os.environ,
            {
                "ANTHROPIC_API_KEY": "test",
                "OPENAI_API_KEY": "test",
                "GOOGLE_API_KEY": "test",
            },
        ):
            cheapest = get_cheapest_provider()
            assert cheapest is not None
            assert isinstance(cheapest, ProviderType)

    def test_returns_none_when_no_providers(self):
        """プロバイダがない場合はNone"""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            os.environ.pop("OPENAI_API_KEY", None)
            os.environ.pop("GOOGLE_API_KEY", None)
            cheapest = get_cheapest_provider()
            assert cheapest is None


class TestMultiProviderAdapter:
    """MultiProviderAdapter のテスト"""

    @pytest.fixture
    def mock_candidate(self):
        """テスト用候補"""
        return Candidate(
            person_id="P123456",
            person_name="テスト太郎",
            age=30,
            category="科学",
            person_type="REAL",
        )

    def test_init_with_anthropic(self):
        """Anthropicで初期化"""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test"}):
            adapter = MultiProviderAdapter(provider_type=ProviderType.ANTHROPIC)
            assert adapter.provider_type == ProviderType.ANTHROPIC
            assert "anthropic" in adapter.name

    def test_init_with_openai(self):
        """OpenAIで初期化"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test"}):
            adapter = MultiProviderAdapter(provider_type=ProviderType.OPENAI)
            assert adapter.provider_type == ProviderType.OPENAI
            assert "openai" in adapter.name

    def test_init_with_google(self):
        """Googleで初期化"""
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test"}):
            adapter = MultiProviderAdapter(provider_type=ProviderType.GOOGLE)
            assert adapter.provider_type == ProviderType.GOOGLE
            assert "google" in adapter.name

    def test_parse_evaluation_response_json(self):
        """JSON評価レスポンスのパース"""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test"}):
            adapter = MultiProviderAdapter()
            response = """{
                "memorability": 7.5,
                "empathy": 6.0,
                "surprise": 8.0,
                "generation_quality": 7.0,
                "educational_value": 6.5,
                "story_quality": 7.0,
                "factual_density": 8.5
            }"""
            scores = adapter._parse_evaluation_response(response)
            assert scores["memorability"] == 7.5
            assert scores["factual_density"] == 8.5

    def test_parse_evaluation_response_fallback(self):
        """正規表現フォールバックでのパース"""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test"}):
            adapter = MultiProviderAdapter()
            response = "memorability: 7.5, factual_density: 8.0"
            scores = adapter._parse_evaluation_response(response)
            assert scores.get("memorability") == 7.5
            assert scores.get("factual_density") == 8.0

    def test_extract_evidence(self, mock_candidate):
        """根拠抽出"""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test"}):
            adapter = MultiProviderAdapter()
            text = "1995年に「新世紀プロジェクト」を立ち上げ、100万件のデータを分析。"
            evidence = adapter._extract_evidence(text)
            assert "1995年" in evidence
            assert "「新世紀プロジェクト」" in evidence
            assert "100万" in evidence


class TestAutoProviderAdapter:
    """AutoProviderAdapter のテスト"""

    def test_auto_selects_available_provider(self):
        """利用可能なプロバイダを自動選択"""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test"}):
            adapter = AutoProviderAdapter(prefer_cheapest=False)
            assert adapter.provider_type == ProviderType.ANTHROPIC

    def test_prefers_anthropic_when_available(self):
        """Anthropicを優先"""
        with patch.dict(
            os.environ,
            {
                "ANTHROPIC_API_KEY": "test",
                "OPENAI_API_KEY": "test",
            },
        ):
            adapter = AutoProviderAdapter(prefer_cheapest=False)
            assert adapter.provider_type == ProviderType.ANTHROPIC

    def test_raises_when_no_provider(self):
        """プロバイダがない場合はエラー"""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            os.environ.pop("OPENAI_API_KEY", None)
            os.environ.pop("GOOGLE_API_KEY", None)
            with pytest.raises(ValueError, match="No LLM provider available"):
                AutoProviderAdapter()


class TestMultiProviderIntegration:
    """統合テスト（モックAPI）"""

    @pytest.fixture
    def mock_candidate(self):
        """テスト用候補"""
        return Candidate(
            person_id="P123456",
            person_name="アインシュタイン",
            age=26,
            category="科学",
            person_type="REAL",
        )

    def test_generate_with_mock_anthropic(self, mock_candidate):
        """モックAnthropicでの生成"""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test"}):
            adapter = MultiProviderAdapter(provider_type=ProviderType.ANTHROPIC)

            # クライアントをモック
            mock_client = MagicMock()
            mock_client.config = PROVIDER_CONFIGS[ProviderType.ANTHROPIC]
            mock_client.generate.return_value = (
                "あなたと同じ26歳のとき、アインシュタインは1905年に「特殊相対性理論」を発表しました。"
                "この年は「奇跡の年」と呼ばれ、光電効果の論文でノーベル物理学賞の基礎を築きました。"
                "ベルン特許局で働きながら、時間と空間の革命的な理論を完成させた26歳の青年は、"
                "物理学の歴史を永遠に変えることになります。",
                {"input_tokens": 500, "output_tokens": 200},
            )
            adapter._generation_client = mock_client
            adapter._evaluation_client = mock_client

            result = adapter.generate(mock_candidate)
            assert result.success
            assert "アインシュタイン" in result.episode_text
            assert result.char_count > 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
