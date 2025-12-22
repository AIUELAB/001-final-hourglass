#!/usr/bin/env python3
"""AI推奨システム - データモデル"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class AIRecommendation:
    """AI推奨事項"""

    recommendation_id: str
    timestamp: str
    recommendation_type: str  # capacity/cost/performance/security
    action: str  # scale_up/scale_down/optimize/maintain
    target_resource: str
    priority: str  # critical/high/medium/low
    confidence_score: float  # 0.0-1.0
    estimated_impact: float  # 予測される影響度
    estimated_savings: float  # 予測コスト削減額
    implementation_effort: str  # high/medium/low
    reasoning: str
    supporting_data: Dict[str, Any]
    alternative_actions: List[str]


@dataclass
class RecommendationFeedback:
    """推奨事項のフィードバック"""

    recommendation_id: str
    feedback_timestamp: str
    implemented: bool
    actual_impact: Optional[float]
    actual_savings: Optional[float]
    success_rating: float  # 0.0-1.0
    notes: str


@dataclass
class ModelPerformanceMetrics:
    """モデル性能メトリクス"""

    model_name: str
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    training_date: str
    sample_count: int
