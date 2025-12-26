"""
Episode Fame Score v2

感銘重視のエピソードランキングシステム
"""

from .config import (
    ANCHOR_PATTERNS,
    HISTORICAL_IMPACT_KEYWORDS,
    INSPIRATION_AXES,
    INSPIRATION_KEYWORDS,
    MAX_SAME_PERSON_IN_TOP_N,
    QUALITY_GATE,
    TIER_THRESHOLDS,
    WEIGHTS,
)
from .inspiration_scorer import (
    calculate_axis_score,
    calculate_inspiration_score,
    get_inspiration_tier,
)
from .quality_gate import (
    apply_quality_gate,
    calculate_quality_score,
    check_age_contradiction,
    check_meta_expressions,
    check_specificity,
)
from .scorer import (
    apply_bias_control,
    calculate_episode_fame_v2,
    calculate_historical_impact,
    calculate_person_fame_score,
    get_tier,
    rank_episodes,
)

__all__ = [
    # Config
    "WEIGHTS",
    "INSPIRATION_AXES",
    "INSPIRATION_KEYWORDS",
    "QUALITY_GATE",
    "HISTORICAL_IMPACT_KEYWORDS",
    "MAX_SAME_PERSON_IN_TOP_N",
    "TIER_THRESHOLDS",
    "ANCHOR_PATTERNS",
    # Inspiration
    "calculate_inspiration_score",
    "calculate_axis_score",
    "get_inspiration_tier",
    # Quality
    "calculate_quality_score",
    "check_specificity",
    "check_meta_expressions",
    "check_age_contradiction",
    "apply_quality_gate",
    # Scorer
    "calculate_episode_fame_v2",
    "calculate_historical_impact",
    "calculate_person_fame_score",
    "get_tier",
    "apply_bias_control",
    "rank_episodes",
]
