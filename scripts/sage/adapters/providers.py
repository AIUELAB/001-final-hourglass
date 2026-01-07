"""
Multi-Provider Support

Phase 5: Claude/OpenAI/Gemini マルチプロバイダ対応。
"""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class ProviderType(Enum):
    """LLMプロバイダの種類"""

    ANTHROPIC = "anthropic"  # Claude
    OPENAI = "openai"  # GPT-4
    GOOGLE = "google"  # Gemini


@dataclass
class ProviderConfig:
    """プロバイダ設定"""

    provider_type: ProviderType
    model_name: str
    api_key_env: str  # 環境変数名
    max_tokens: int = 4096
    temperature: float = 0.7

    @property
    def api_key(self) -> Optional[str]:
        """環境変数からAPIキーを取得"""
        return os.environ.get(self.api_key_env)


# デフォルトプロバイダ設定
PROVIDER_CONFIGS = {
    ProviderType.ANTHROPIC: ProviderConfig(
        provider_type=ProviderType.ANTHROPIC,
        model_name="claude-sonnet-4-20250514",
        api_key_env="ANTHROPIC_API_KEY",
        max_tokens=4096,
        temperature=0.7,
    ),
    ProviderType.OPENAI: ProviderConfig(
        provider_type=ProviderType.OPENAI,
        model_name="gpt-4o",
        api_key_env="OPENAI_API_KEY",
        max_tokens=4096,
        temperature=0.7,
    ),
    ProviderType.GOOGLE: ProviderConfig(
        provider_type=ProviderType.GOOGLE,
        model_name="gemini-1.5-pro",
        api_key_env="GOOGLE_API_KEY",
        max_tokens=4096,
        temperature=0.7,
    ),
}

# 料金表 (per 1M tokens, 2026-01時点)
PROVIDER_PRICING = {
    ProviderType.ANTHROPIC: {
        "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
        "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0},
        "claude-3-5-haiku-20241022": {"input": 0.25, "output": 1.25},
    },
    ProviderType.OPENAI: {
        "gpt-4o": {"input": 2.5, "output": 10.0},
        "gpt-4o-mini": {"input": 0.15, "output": 0.6},
        "gpt-4-turbo": {"input": 10.0, "output": 30.0},
    },
    ProviderType.GOOGLE: {
        "gemini-1.5-pro": {"input": 1.25, "output": 5.0},
        "gemini-1.5-flash": {"input": 0.075, "output": 0.3},
    },
}


class LLMClient(ABC):
    """LLMクライアント抽象基底クラス"""

    def __init__(self, config: ProviderConfig):
        self.config = config
        self._validate_api_key()

    def _validate_api_key(self) -> None:
        """APIキーの存在確認"""
        if not self.config.api_key:
            raise ValueError(f"{self.config.api_key_env} environment variable is not set")

    @abstractmethod
    def generate(self, prompt: str, system: str = "") -> tuple[str, dict[str, int]]:
        """
        テキスト生成

        Args:
            prompt: ユーザープロンプト
            system: システムプロンプト

        Returns:
            tuple[str, dict]: (生成テキスト, トークン使用量)
        """
        pass

    def get_pricing(self) -> dict[str, float]:
        """料金情報を取得"""
        provider_prices = PROVIDER_PRICING.get(self.config.provider_type, {})
        return provider_prices.get(
            self.config.model_name,
            {"input": 0.0, "output": 0.0},
        )


class AnthropicClient(LLMClient):
    """Anthropic (Claude) クライアント"""

    def __init__(self, config: Optional[ProviderConfig] = None):
        if config is None:
            config = PROVIDER_CONFIGS[ProviderType.ANTHROPIC]
        super().__init__(config)
        self._client = None

    def _get_client(self):
        """遅延初期化"""
        if self._client is None:
            try:
                import anthropic

                self._client = anthropic.Anthropic(api_key=self.config.api_key)
            except ImportError:
                raise ImportError("anthropic package not installed. Run: pip install anthropic")
        return self._client

    def generate(self, prompt: str, system: str = "") -> tuple[str, dict[str, int]]:
        """Claude API呼び出し"""
        client = self._get_client()

        messages = [{"role": "user", "content": prompt}]

        response = client.messages.create(
            model=self.config.model_name,
            max_tokens=self.config.max_tokens,
            system=system if system else "You are a helpful assistant.",
            messages=messages,
        )

        text = response.content[0].text if response.content else ""
        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }

        return text, usage


class OpenAIClient(LLMClient):
    """OpenAI (GPT) クライアント"""

    def __init__(self, config: Optional[ProviderConfig] = None):
        if config is None:
            config = PROVIDER_CONFIGS[ProviderType.OPENAI]
        super().__init__(config)
        self._client = None

    def _get_client(self):
        """遅延初期化"""
        if self._client is None:
            try:
                from openai import OpenAI

                self._client = OpenAI(api_key=self.config.api_key)
            except ImportError:
                raise ImportError("openai package not installed. Run: pip install openai")
        return self._client

    def generate(self, prompt: str, system: str = "") -> tuple[str, dict[str, int]]:
        """OpenAI API呼び出し"""
        client = self._get_client()

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = client.chat.completions.create(
            model=self.config.model_name,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            messages=messages,
        )

        text = response.choices[0].message.content if response.choices else ""
        usage = {
            "input_tokens": response.usage.prompt_tokens if response.usage else 0,
            "output_tokens": response.usage.completion_tokens if response.usage else 0,
        }

        return text, usage


class GoogleClient(LLMClient):
    """Google (Gemini) クライアント"""

    def __init__(self, config: Optional[ProviderConfig] = None):
        if config is None:
            config = PROVIDER_CONFIGS[ProviderType.GOOGLE]
        super().__init__(config)
        self._model = None

    def _get_model(self):
        """遅延初期化"""
        if self._model is None:
            try:
                import google.generativeai as genai

                genai.configure(api_key=self.config.api_key)
                self._model = genai.GenerativeModel(self.config.model_name)
            except ImportError:
                raise ImportError("google-generativeai package not installed. Run: pip install google-generativeai")
        return self._model

    def generate(self, prompt: str, system: str = "") -> tuple[str, dict[str, int]]:
        """Gemini API呼び出し"""
        model = self._get_model()

        # システムプロンプトを含める
        full_prompt = f"{system}\n\n{prompt}" if system else prompt

        response = model.generate_content(
            full_prompt,
            generation_config={
                "max_output_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
            },
        )

        text = response.text if response.text else ""

        # Geminiはトークン数を直接返さないので推定
        usage = {
            "input_tokens": len(full_prompt) // 4,  # 概算
            "output_tokens": len(text) // 4,  # 概算
        }

        return text, usage


def create_client(provider_type: ProviderType, config: Optional[ProviderConfig] = None) -> LLMClient:
    """
    プロバイダ別クライアントを作成

    Args:
        provider_type: プロバイダの種類
        config: カスタム設定（オプション）

    Returns:
        LLMClient: プロバイダ別クライアント
    """
    if config is None:
        config = PROVIDER_CONFIGS.get(provider_type)
        if config is None:
            raise ValueError(f"Unknown provider type: {provider_type}")

    client_classes = {
        ProviderType.ANTHROPIC: AnthropicClient,
        ProviderType.OPENAI: OpenAIClient,
        ProviderType.GOOGLE: GoogleClient,
    }

    client_class = client_classes.get(provider_type)
    if client_class is None:
        raise ValueError(f"No client implementation for: {provider_type}")

    return client_class(config)


def get_available_providers() -> list[ProviderType]:
    """
    利用可能なプロバイダを取得（APIキーが設定されているもの）

    Returns:
        list[ProviderType]: 利用可能なプロバイダリスト
    """
    available = []
    for provider_type, config in PROVIDER_CONFIGS.items():
        if config.api_key:
            available.append(provider_type)
    return available


def get_cheapest_provider() -> Optional[ProviderType]:
    """
    最も安いプロバイダを取得（利用可能なもの中で）

    Returns:
        ProviderType: 最安プロバイダ、または None
    """
    available = get_available_providers()
    if not available:
        return None

    def get_cost(provider: ProviderType) -> float:
        config = PROVIDER_CONFIGS[provider]
        pricing = PROVIDER_PRICING.get(provider, {}).get(config.model_name, {})
        # input + output の平均コスト
        return (pricing.get("input", 0) + pricing.get("output", 0)) / 2

    return min(available, key=get_cost)
