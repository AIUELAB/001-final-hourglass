"""
Adapters Package

EPGEN と既存生成器を統一インターフェースで扱うアダプター層。
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

__all__ = [
    "GeneratorAdapter",
    "GeneratorType",
    "GenerationResult",
    "EvaluationResult",
    "AxisScores",
    "Candidate",
    "TokenUsage",
    "PRICING",
    "EPGENAdapter",
    "MockEPGENAdapter",
    "LegacyGeneratorAdapter",
]
