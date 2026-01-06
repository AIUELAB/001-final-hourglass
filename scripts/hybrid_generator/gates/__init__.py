"""
Gates Package

ファクトチェック、重複検出、多様性制約、候補優先度、完全性のゲート層。
"""

from .candidate_prioritizer import (
    CandidatePrioritizer,
    CandidatePriorityScore,
)
from .completeness import (
    CompletenessCheckResult,
    check_completeness,
    quick_completeness_check,
)
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
    "CandidatePrioritizer",
    "CandidatePriorityScore",
    "CompletenessCheckResult",
    "check_completeness",
    "quick_completeness_check",
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
