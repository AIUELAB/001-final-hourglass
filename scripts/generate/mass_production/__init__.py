#!/usr/bin/env python3
"""
EPGEN - Episode Generator

高品質エピソード大量生産システム
並列生成と品質ゲートによる高スループット生成パイプライン
"""

from .config import (
    DEFAULT_CONFIG,
    FORBIDDEN_PATTERNS,
    GenerationConfig,
    MASTER_CSV_PATH,
    MassProductionConfig,
    QualityGateConfig,
    QUALITY_SCORE_WEIGHTS,
    REQUIRED_PATTERNS,
    SelectionConfig,
)
from .deduplicator import (
    ContentSimilarityChecker,
    DuplicateCheckResult,
    FastDeduplicator,
    PersonAgeDeduplicator,
)
from .evaluator import (
    BatchEvaluator,
    EvaluationResult,
    EvaluationScores,
    FinalRanker,
    MockLLMEvaluator,
    StructuralEvaluator,
)
from .generator import (
    GenerationInput,
    GenerationResult,
    MockLLMClient,
    ParallelGenerator,
    PromptBuilder,
    TextValidator,
)
from .llm_clients import (
    AnthropicClient,
    BaseLLMClient,
    GeminiClient,
    OpenAIClient,
    create_llm_client,
)
from .pipeline import (
    DryRunPipeline,
    MassProductionPipeline,
    PipelineResult,
    PipelineStats,
)
from .selector import MassProductionSelector, SelectionCandidate

__all__ = [
    # Config
    "MassProductionConfig",
    "QualityGateConfig",
    "GenerationConfig",
    "SelectionConfig",
    "DEFAULT_CONFIG",
    "MASTER_CSV_PATH",
    "QUALITY_SCORE_WEIGHTS",
    "FORBIDDEN_PATTERNS",
    "REQUIRED_PATTERNS",
    # Selector
    "MassProductionSelector",
    "SelectionCandidate",
    # Generator
    "ParallelGenerator",
    "GenerationInput",
    "GenerationResult",
    "PromptBuilder",
    "TextValidator",
    "MockLLMClient",
    # Evaluator
    "BatchEvaluator",
    "EvaluationResult",
    "EvaluationScores",
    "StructuralEvaluator",
    "FinalRanker",
    "MockLLMEvaluator",
    # Deduplicator
    "FastDeduplicator",
    "PersonAgeDeduplicator",
    "ContentSimilarityChecker",
    "DuplicateCheckResult",
    # Pipeline
    "MassProductionPipeline",
    "DryRunPipeline",
    "PipelineResult",
    "PipelineStats",
    # LLM Clients
    "BaseLLMClient",
    "AnthropicClient",
    "OpenAIClient",
    "GeminiClient",
    "create_llm_client",
]

__version__ = "1.3.0"
