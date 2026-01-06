"""
Gates Package

ファクトチェック、重複検出、多様性制約のゲート層。
"""

from .diversity import (
    DiversityCheckResult,
    DiversityManager,
    GenerationQuota,
    get_recommended_candidates,
)
from .duplicate import (
    DuplicateCheckResult,
    DuplicateDetector,
    TextSimilarityCalculator,
    quick_duplicate_check,
)
from .fact_check import (
    FabricationDetector,
    FactCheckResult,
    FactChecker,
    quick_fact_check,
)

__all__ = [
    "FactChecker",
    "FactCheckResult",
    "FabricationDetector",
    "quick_fact_check",
    "DuplicateDetector",
    "DuplicateCheckResult",
    "TextSimilarityCalculator",
    "quick_duplicate_check",
    "DiversityManager",
    "DiversityCheckResult",
    "GenerationQuota",
    "get_recommended_candidates",
]
