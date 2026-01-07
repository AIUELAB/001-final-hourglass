"""
Adapters Package

EPGEN と既存生成器を統一インターフェースで扱うアダプター層。
Phase 5: マルチプロバイダ対応 (Claude/OpenAI/Gemini)
"""

from .base import (
    PRICING,
    AxisScores,
    Candidate,
    EvaluationResult,
    GenerationResult,
    GeneratorAdapter,
    GeneratorType,
    TokenUsage,
)
from .epgen_adapter import EPGENAdapter, MockEPGENAdapter
from .legacy_adapter import LegacyGeneratorAdapter
from .multi_provider_adapter import AutoProviderAdapter, MultiProviderAdapter
from .providers import (
    PROVIDER_CONFIGS,
    PROVIDER_PRICING,
    AnthropicClient,
    GoogleClient,
    LLMClient,
    OpenAIClient,
    ProviderConfig,
    ProviderType,
    create_client,
    get_available_providers,
    get_cheapest_provider,
)

__all__ = [
    # Base
    "GeneratorAdapter",
    "GeneratorType",
    "GenerationResult",
    "EvaluationResult",
    "AxisScores",
    "Candidate",
    "TokenUsage",
    "PRICING",
    # Adapters
    "EPGENAdapter",
    "MockEPGENAdapter",
    "LegacyGeneratorAdapter",
    # Phase 5: Multi-Provider
    "MultiProviderAdapter",
    "AutoProviderAdapter",
    # Providers
    "ProviderType",
    "ProviderConfig",
    "PROVIDER_CONFIGS",
    "PROVIDER_PRICING",
    "LLMClient",
    "AnthropicClient",
    "OpenAIClient",
    "GoogleClient",
    "create_client",
    "get_available_providers",
    "get_cheapest_provider",
]
