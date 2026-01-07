"""
Quality Pipeline Package

7軸評価、超総合スコア計算、改善ループを提供。
"""

from .evaluator import (
    CompositeScoreCalculator,
    GateCheckResult,
    QualityEvaluator,
    create_evaluation_result,
)
from .improvement import (
    ImprovementAction,
    ImprovementFeedback,
    ImprovementLoop,
    should_retry,
)
from .super_total import SuperTotalCalculator, SuperTotalResult, calculate_super_total_for_episode
from .category_evaluator import (
    CategoryEvaluationResult,
    CategoryEvaluator,
    CategoryThreshold,
    CategoryThresholds,
    PersonQualityAnalyzer,
    PersonQualitySignature,
    evaluate_by_category,
    get_category_thresholds,
)

__all__ = [
    "QualityEvaluator",
    "GateCheckResult",
    "CompositeScoreCalculator",
    "create_evaluation_result",
    "SuperTotalCalculator",
    "SuperTotalResult",
    "calculate_super_total_for_episode",
    "ImprovementLoop",
    "ImprovementAction",
    "ImprovementFeedback",
    "should_retry",
    # Category Evaluator (Phase 6)
    "CategoryEvaluator",
    "CategoryEvaluationResult",
    "CategoryThreshold",
    "CategoryThresholds",
    "PersonQualityAnalyzer",
    "PersonQualitySignature",
    "evaluate_by_category",
    "get_category_thresholds",
]
