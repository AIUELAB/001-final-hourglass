"""
Episode Fame Score v4

LLM 7軸評価スコアを統合したエピソード有名度スコア計算モジュール

計算式:
  episode_fame_score_v4 =
      LLMコンポーネント × 0.45 +
      歴史的キーワード × 0.25 +
      タイプボーナス × 0.15 +
      人物知名度 × 0.15
"""

from .scorer import (
    EpisodeFameSignals,
    EpisodeFameResult,
    calculate_episode_fame_v4,
    calculate_tier,
)
from .config import (
    WEIGHTS,
    LLM_WEIGHTS,
    TYPE_BONUS,
    HISTORICAL_KEYWORDS,
    PERSONAL_KEYWORDS,
    TIER_THRESHOLDS,
)

__all__ = [
    "EpisodeFameSignals",
    "EpisodeFameResult",
    "calculate_episode_fame_v4",
    "calculate_tier",
    "WEIGHTS",
    "LLM_WEIGHTS",
    "TYPE_BONUS",
    "HISTORICAL_KEYWORDS",
    "PERSONAL_KEYWORDS",
    "TIER_THRESHOLDS",
]
