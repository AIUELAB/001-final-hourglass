#!/usr/bin/env python3
"""
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
    # Deduplicator
    "FastDeduplicator",
    "PersonAgeDeduplicator",
    "ContentSimilarityChecker",
    "DuplicateCheckResult",
]

__version__ = "1.0.0"
