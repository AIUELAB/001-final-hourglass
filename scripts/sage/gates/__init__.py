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
from .semantic_gaming_detector import (
    EmotionalBiasDetector,
    SemanticGamingDetector,
    SemanticGamingResult,
    StructuralPatternDetector,
    SynonymRepetitionDetector,
    check_semantic_gaming,
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
from .narrative_diversity import (
    EraTheme,
    EraThemeClassifier,
    NarrativeBalanceResult,
    NarrativeBalancer,
    StoryClassificationResult,
    StoryType,
    StoryTypeClassifier,
    analyze_narrative_balance,
    classify_story,
)
from .duplicate import (
    DuplicateCheckResult,
    DuplicateDetector,
    TextSimilarityCalculator,
    quick_duplicate_check,
)
from .advanced_similarity import (
    AdvancedDuplicateChecker,
    AdvancedDuplicateResult,
    CrossCategoryDuplicateDetector,
    SemanticSimilarity,
    SemanticSimilarityResult,
    TemporalDuplicateDetector,
    TemporalDuplicateResult,
    check_advanced_duplicate,
)
from .fact_check import (
    FabricationDetector,
    FactCheckResult,
    FactChecker,
    quick_fact_check,
)
from .wiki_fact_checker import (
    CategoryFactRules,
    CrossReferenceValidator,
    PersonInfo,
    WikidataClient,
    WikiFactCheckResult,
    WikiFactChecker,
    verify_episode_facts,
)
from .perplexity_fact_checker import (
    HybridFactChecker,
    PerplexityFactCheckResult,
    PerplexityFactChecker,
    perplexity_fact_check,
)

__all__ = [
    # Anti-Gaming
    "AntiGamingMonitor",
    "AntiGamingResult",
    "get_gaming_violations",
    "quick_anti_gaming_check",
    # Semantic Gaming Detector (Phase 6)
    "SemanticGamingDetector",
    "SemanticGamingResult",
    "SynonymRepetitionDetector",
    "StructuralPatternDetector",
    "EmotionalBiasDetector",
    "check_semantic_gaming",
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
    # Wiki Fact Check (Phase 6)
    "WikiFactChecker",
    "WikiFactCheckResult",
    "WikidataClient",
    "CrossReferenceValidator",
    "CategoryFactRules",
    "PersonInfo",
    "verify_episode_facts",
    # Perplexity Fact Check
    "PerplexityFactChecker",
    "PerplexityFactCheckResult",
    "HybridFactChecker",
    "perplexity_fact_check",
    # Duplicate
    "DuplicateDetector",
    "DuplicateCheckResult",
    "TextSimilarityCalculator",
    "quick_duplicate_check",
    # Advanced Similarity (Phase 6)
    "AdvancedDuplicateChecker",
    "AdvancedDuplicateResult",
    "SemanticSimilarity",
    "SemanticSimilarityResult",
    "TemporalDuplicateDetector",
    "TemporalDuplicateResult",
    "CrossCategoryDuplicateDetector",
    "check_advanced_duplicate",
    # Diversity
    "DiversityManager",
    "DiversityCheckResult",
    "GenerationQuota",
    "get_recommended_candidates",
    # Narrative Diversity (Phase 6)
    "StoryType",
    "StoryTypeClassifier",
    "StoryClassificationResult",
    "EraTheme",
    "EraThemeClassifier",
    "NarrativeBalancer",
    "NarrativeBalanceResult",
    "classify_story",
    "analyze_narrative_balance",
]
