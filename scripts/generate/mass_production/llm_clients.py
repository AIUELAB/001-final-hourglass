#!/usr/bin/env python3
"""
LLMクライアントモジュール

Anthropic/OpenAI APIのラッパー（非同期対応）
"""

import asyncio
import os
from abc import ABC, abstractmethod
from typing import Optional


class BaseLLMClient(ABC):
    """LLMクライアント基底クラス"""

    @abstractmethod
    async def generate_async(self, prompt: str, system_prompt: str | None = None) -> str:
        """非同期でテキスト生成"""
        pass

    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        """同期でテキスト生成"""
        return asyncio.run(self.generate_async(prompt, system_prompt))


class AnthropicClient(BaseLLMClient):
    """Anthropic Claude クライアント"""

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        api_key: Optional[str] = None,
        max_tokens: int = 2000,
        enable_cache: bool = False,  # H4: プロンプトキャッシュ
    ):
        """
        Args:
            model: モデル名
            api_key: APIキー（Noneの場合は環境変数から取得）
            max_tokens: 最大トークン数
            enable_cache: プロンプトキャッシュ有効化（H4最適化）
        """
        self.model = model
        self.max_tokens = max_tokens
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.enable_cache = enable_cache

        # H4: キャッシュ統計
        self.cache_stats = {
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
            "total_requests": 0,
        }

        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY環境変数が設定されていません")

        # 遅延インポート（依存関係軽減）
        try:
            import anthropic

            self.client = anthropic.Anthropic(api_key=self.api_key)
            self.async_client = anthropic.AsyncAnthropic(api_key=self.api_key)
        except ImportError:
            raise ImportError("anthropic パッケージがインストールされていません: pip install anthropic")

    async def generate_async(self, prompt: str, system_prompt: str | None = None) -> str:
        """
        非同期でテキスト生成

        Args:
            prompt: ユーザープロンプト
            system_prompt: システムプロンプト（オプション）

        Returns:
            str: 生成テキスト
        """
        kwargs = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        response = await self.async_client.messages.create(**kwargs)
        return response.content[0].text.strip()

    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        """
        同期でテキスト生成

        Args:
            prompt: ユーザープロンプト
            system_prompt: システムプロンプト（オプション）

        Returns:
            str: 生成テキスト
        """
        kwargs = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        response = self.client.messages.create(**kwargs)
        return response.content[0].text.strip()

    async def generate_with_cache_async(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> tuple[str, dict]:
        """
        H4: プロンプトキャッシュ付き非同期生成

        システムプロンプトをキャッシュして、繰り返し呼び出し時のコストを削減。
        - cache_control: {"type": "ephemeral"} で5分間キャッシュ
        - キャッシュヒット時: 入力トークン90%削減

        Args:
            system_prompt: システムプロンプト（キャッシュ対象）
            user_prompt: ユーザープロンプト（リクエストごとに変化）

        Returns:
            tuple[str, dict]: (生成テキスト, キャッシュ統計)
        """
        self.cache_stats["total_requests"] += 1

        # システムプロンプトにキャッシュ制御を追加
        system_content = [
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ]

        response = await self.async_client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system_content,
            messages=[{"role": "user", "content": user_prompt}],
        )

        # キャッシュ統計を更新
        usage = response.usage
        cache_creation = getattr(usage, "cache_creation_input_tokens", 0)
        cache_read = getattr(usage, "cache_read_input_tokens", 0)

        self.cache_stats["cache_creation_input_tokens"] += cache_creation
        self.cache_stats["cache_read_input_tokens"] += cache_read

        return response.content[0].text.strip(), {
            "cache_creation": cache_creation,
            "cache_read": cache_read,
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
        }

    def generate_with_cache(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> tuple[str, dict]:
        """
        H4: プロンプトキャッシュ付き同期生成

        Args:
            system_prompt: システムプロンプト（キャッシュ対象）
            user_prompt: ユーザープロンプト

        Returns:
            tuple[str, dict]: (生成テキスト, キャッシュ統計)
        """
        self.cache_stats["total_requests"] += 1

        system_content = [
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ]

        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system_content,
            messages=[{"role": "user", "content": user_prompt}],
        )

        usage = response.usage
        cache_creation = getattr(usage, "cache_creation_input_tokens", 0)
        cache_read = getattr(usage, "cache_read_input_tokens", 0)

        self.cache_stats["cache_creation_input_tokens"] += cache_creation
        self.cache_stats["cache_read_input_tokens"] += cache_read

        return response.content[0].text.strip(), {
            "cache_creation": cache_creation,
            "cache_read": cache_read,
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
        }

    def get_cache_stats(self) -> dict:
        """H4: キャッシュ統計を取得"""
        total = self.cache_stats["total_requests"]
        cache_read = self.cache_stats["cache_read_input_tokens"]
        cache_creation = self.cache_stats["cache_creation_input_tokens"]

        return {
            "total_requests": total,
            "cache_creation_input_tokens": cache_creation,
            "cache_read_input_tokens": cache_read,
            "cache_hit_rate": (cache_read / (cache_read + cache_creation))
            if (cache_read + cache_creation) > 0
            else 0.0,
            "estimated_savings_pct": (cache_read * 0.9) / (cache_read + cache_creation)
            if (cache_read + cache_creation) > 0
            else 0.0,
        }


class OpenAIClient(BaseLLMClient):
    """OpenAI GPT クライアント"""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        max_tokens: int = 2000,
    ):
        """
        Args:
            model: モデル名
            api_key: APIキー（Noneの場合は環境変数から取得）
            max_tokens: 最大トークン数
        """
        self.model = model
        self.max_tokens = max_tokens
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

        if not self.api_key:
            raise ValueError("OPENAI_API_KEY環境変数が設定されていません")

        # 遅延インポート（依存関係軽減）
        try:
            from openai import AsyncOpenAI, OpenAI

            self.client = OpenAI(api_key=self.api_key)
            self.async_client = AsyncOpenAI(api_key=self.api_key)
        except ImportError:
            raise ImportError("openai パッケージがインストールされていません: pip install openai")

    async def generate_async(self, prompt: str, system_prompt: str | None = None) -> str:
        """非同期でテキスト生成"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await self.async_client.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=messages,
        )
        return response.choices[0].message.content.strip()

    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        """同期でテキスト生成"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=messages,
        )
        return response.choices[0].message.content.strip()


class GeminiClient(BaseLLMClient):
    """Google Gemini クライアント"""

    def __init__(
        self,
        model: str = "gemini-1.5-flash",
        api_key: Optional[str] = None,
    ):
        """
        Args:
            model: モデル名
            api_key: APIキー（Noneの場合は環境変数から取得）
        """
        self.model = model
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")

        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY環境変数が設定されていません")

        # 遅延インポート
        try:
            import google.generativeai as genai

            genai.configure(api_key=self.api_key)
            self.genai = genai
            self.client = genai.GenerativeModel(model)
        except ImportError:
            raise ImportError(
                "google-generativeai パッケージがインストールされていません: pip install google-generativeai"
            )

    async def generate_async(self, prompt: str, system_prompt: str | None = None) -> str:
        """非同期でテキスト生成（同期APIをラップ）"""
        # Gemini SDKは完全な非同期をサポートしていないため、
        # イベントループでブロッキング呼び出しを実行
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.generate, prompt, system_prompt)

    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        """同期でテキスト生成"""
        # Geminiはsystem promptをユーザープロンプトの前に連結
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        response = self.client.generate_content(full_prompt)
        return response.text.strip()


# Phase 3: モデル定数
MODELS = {
    "sonnet": "claude-sonnet-4-20250514",
    "haiku": "claude-3-5-haiku-20241022",
    "sonnet-3.5": "claude-3-5-sonnet-20241022",
}


def create_llm_client(
    provider: str = "anthropic",
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    enable_cache: bool = False,  # H4: プロンプトキャッシュ
) -> BaseLLMClient:
    """
    LLMクライアントファクトリ

    Args:
        provider: プロバイダー名（anthropic, openai, gemini, mock）
        model: モデル名（省略時はデフォルト）。'sonnet', 'haiku'などの短縮名も使用可能
        api_key: APIキー（省略時は環境変数）
        enable_cache: H4 プロンプトキャッシュ有効化（Anthropicのみ対応）

    Returns:
        LLMクライアントインスタンス
    """
    # 短縮名を正式名に変換
    if model and model in MODELS:
        model = MODELS[model]

    if provider == "anthropic":
        return AnthropicClient(
            model=model or "claude-sonnet-4-20250514",
            api_key=api_key,
            enable_cache=enable_cache,
        )
    elif provider == "openai":
        return OpenAIClient(
            model=model or "gpt-4o-mini",
            api_key=api_key,
        )
    elif provider == "gemini":
        return GeminiClient(
            model=model or "gemini-1.5-flash",
            api_key=api_key,
        )
    elif provider == "mock":
        from .generator import MockLLMClient

        return MockLLMClient(delay=0.05)
    else:
        raise ValueError(f"未対応のプロバイダー: {provider}")


def create_evaluation_client(
    use_haiku: bool = True,
    api_key: Optional[str] = None,
) -> BaseLLMClient:
    """
    評価用LLMクライアントを作成（Phase 3最適化）

    Args:
        use_haiku: Haikuを使用するか（True=低コスト, False=Sonnet高精度）
        api_key: APIキー（省略時は環境変数）

    Returns:
        評価用LLMクライアント

    コスト比較:
        Haiku:  $0.25/M in, $1.25/M out（-92%）
        Sonnet: $3.00/M in, $15.00/M out
    """
    model = "haiku" if use_haiku else "sonnet"
    return create_llm_client(provider="anthropic", model=model, api_key=api_key)


def create_generation_client(
    enable_cache: bool = True,
    model: str = "sonnet",
    api_key: Optional[str] = None,
) -> AnthropicClient:
    """
    H4: 生成用LLMクライアントを作成（プロンプトキャッシュ対応）

    Args:
        enable_cache: プロンプトキャッシュ有効化（True=-90%入力トークン）
        model: モデル名（'sonnet', 'haiku'などの短縮名も使用可能）
        api_key: APIキー（省略時は環境変数）

    Returns:
        AnthropicClient: キャッシュ対応クライアント

    キャッシュ効果:
        - システムプロンプトを5分間キャッシュ
        - 2回目以降の呼び出しで入力トークン90%削減
        - 繰り返し生成で大幅なコスト削減

    使用例:
        client = create_generation_client(enable_cache=True)
        # キャッシュ付き生成
        text, stats = client.generate_with_cache(
            system_prompt="あなたはエピソード生成AIです...",
            user_prompt="人物: 大谷翔平, 年齢: 25歳"
        )
        # キャッシュ統計
        print(client.get_cache_stats())
    """
    if model in MODELS:
        model = MODELS[model]

    return AnthropicClient(
        model=model,
        api_key=api_key,
        enable_cache=enable_cache,
    )


def main():
    """デモ実行"""
    print("=== LLMクライアントデモ ===")

    # モッククライアントでテスト
    from .generator import MockLLMClient

    mock = MockLLMClient(delay=0.1)
    result = asyncio.run(mock.generate_async("テストプロンプト"))
    print(f"モック結果: {result[:100]}...")

    # 環境変数があればAnthropicもテスト
    if os.getenv("ANTHROPIC_API_KEY"):
        print("\n--- Anthropic テスト ---")
        client = AnthropicClient()
        result = client.generate("Hello, say 'test successful' in Japanese")
        print(f"Anthropic結果: {result}")


if __name__ == "__main__":
    main()
