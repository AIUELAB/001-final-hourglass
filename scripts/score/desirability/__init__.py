"""
desirability計算モジュール

エピソードの「望ましさ」を評価するための各種スコア計算を提供する。
"""

from .config import (
    DESIRABILITY_WEIGHTS,
    DIVERSITY_PENALTY,
    EVENT_TYPE_WEIGHTS,
    MULTI_TIER_BONUS,
    RECENCY_BOOST,
    SUPERSTARS,
    TIER_A_KEYWORDS,
    TIER_B_KEYWORDS,
    TIER_C_KEYWORDS,
    TIER_MAGNITUDE,
    TIER_S_KEYWORDS,
)
from .event_magnitude import calculate_event_magnitude, normalize_magnitude
from .scorer import (
    NormalizationParams,
    calculate_desirability_score,
    calculate_quality_factor,
    calculate_recency_boost,
    calculate_what_factor,
    calculate_when_factor,
    calculate_who_factor,
    get_top_episodes,
    robust_normalize,
    score_all_episodes,
)

__all__ = [
    # 設定
    "TIER_S_KEYWORDS",
    "TIER_A_KEYWORDS",
    "TIER_B_KEYWORDS",
    "TIER_C_KEYWORDS",
    "TIER_MAGNITUDE",
    "SUPERSTARS",
    "DESIRABILITY_WEIGHTS",
    "RECENCY_BOOST",
    "DIVERSITY_PENALTY",
    "MULTI_TIER_BONUS",
    "EVENT_TYPE_WEIGHTS",
    # 関数
    "calculate_event_magnitude",
    "normalize_magnitude",
    # scorer
    "NormalizationParams",
    "calculate_desirability_score",
    "calculate_who_factor",
    "calculate_what_factor",
    "calculate_when_factor",
    "calculate_quality_factor",
    "calculate_recency_boost",
    "robust_normalize",
    "score_all_episodes",
    "get_top_episodes",
]
