"""
Gates Package

ファクトチェック、重複検出、多様性制約、候補優先度、完全性、アンチゲーミングのゲート層。
"""

from .anti_gaming import (
    AntiGamingMonitor,
    AntiGamingResult,
    get_gaming_violations,
    quick_anti_gaming_check,
)
from .candidate_prioritizer import (
    CandidatePrioritizer,
    CandidatePriorityScore,
)
from .completeness import (
    CompletenessCheckResult,
    age_to_nendai,
    auto_fill_derived_fields,
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
    # Anti-Gaming
    "AntiGamingMonitor",
    "AntiGamingResult",
    "get_gaming_violations",
    "quick_anti_gaming_check",
    # Candidate Prioritizer
    "CandidatePrioritizer",
    "CandidatePriorityScore",
    # Completeness
    "CompletenessCheckResult",
    "age_to_nendai",
    "auto_fill_derived_fields",
    "check_completeness",
    "quick_completeness_check",
    # Fact Check
    "FactChecker",
    "FactCheckResult",
    "FabricationDetector",
    "quick_fact_check",
    # Duplicate
    "DuplicateDetector",
    "DuplicateCheckResult",
    "TextSimilarityCalculator",
    "quick_duplicate_check",
    # Diversity
    "DiversityManager",
    "DiversityCheckResult",
    "GenerationQuota",
    "get_recommended_candidates",
]
