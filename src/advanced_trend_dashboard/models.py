#!/usr/bin/env python3
"""高度トレンドダッシュボード - データモデル"""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class PredictionTrend:
    """予測トレンドデータ"""

    timestamp: str
    failure_probability: float
    risk_level: str
    model_agreement: float
    ensemble_predictions: Dict[str, float]


@dataclass
class AutoMLExperiment:
    """AutoML実験データ"""

    experiment_id: str
    timestamp: str
    best_model: str
    best_score: float
    cv_mean: float
    cv_std: float
    model_scores: Dict[str, float]


@dataclass
class DashboardMetrics:
    """ダッシュボードメトリクス"""

    total_predictions: int
    avg_failure_probability: float
    avg_model_agreement: float
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    latest_prediction: Optional[PredictionTrend]
    latest_experiment: Optional[AutoMLExperiment]
