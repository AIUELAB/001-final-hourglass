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
    async def generate_async(self, prompt: str) -> str:
        """非同期でテキスト生成"""
        pass

    def generate(self, prompt: str) -> str:
        """同期でテキスト生成"""
        return asyncio.run(self.generate_async(prompt))


class AnthropicClient(BaseLLMClient):
    """Anthropic Claude クライアント"""

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        api_key: Optional[str] = None,
        max_tokens: int = 500,
    ):
        """
        Args:
            model: モデル名
            api_key: APIキー（Noneの場合は環境変数から取得）
            max_tokens: 最大トークン数
        """
        self.model = model
        self.max_tokens = max_tokens
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")

        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY環境変数が設定されていません")

        # 遅延インポート（依存関係軽減）
        try:
            import anthropic

            self.client = anthropic.Anthropic(api_key=self.api_key)
            self.async_client = anthropic.AsyncAnthropic(api_key=self.api_key)
        except ImportError:
            raise ImportError("anthropic パッケージがインストールされていません: pip install anthropic")

    async def generate_async(self, prompt: str) -> str:
        """非同期でテキスト生成"""
        response = await self.async_client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()

    def generate(self, prompt: str) -> str:
        """同期でテキスト生成"""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()


class OpenAIClient(BaseLLMClient):
    """OpenAI GPT クライアント"""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        max_tokens: int = 500,
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

    async def generate_async(self, prompt: str) -> str:
        """非同期でテキスト生成"""
        response = await self.async_client.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content.strip()

    def generate(self, prompt: str) -> str:
        """同期でテキスト生成"""
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[{"role": "user", "content": prompt}],
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
                "google-generativeai パッケージがインストールされていません: " "pip install google-generativeai"
            )

    async def generate_async(self, prompt: str) -> str:
        """非同期でテキスト生成（同期APIをラップ）"""
        # Gemini SDKは完全な非同期をサポートしていないため、
        # イベントループでブロッキング呼び出しを実行
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.generate, prompt)

    def generate(self, prompt: str) -> str:
        """同期でテキスト生成"""
        response = self.client.generate_content(prompt)
        return response.text.strip()


def create_llm_client(
    provider: str = "anthropic",
    model: Optional[str] = None,
    api_key: Optional[str] = None,
) -> BaseLLMClient:
    """
    LLMクライアントファクトリ

    Args:
        provider: プロバイダー名（anthropic, openai, gemini, mock）
        model: モデル名（省略時はデフォルト）
        api_key: APIキー（省略時は環境変数）

    Returns:
        LLMクライアントインスタンス
    """
    if provider == "anthropic":
        return AnthropicClient(
            model=model or "claude-sonnet-4-20250514",
            api_key=api_key,
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
