#!/usr/bin/env python3
"""容量計画自動化 - データモデル"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ResourceMetrics:
    """リソースメトリクス"""

    timestamp: str
    cpu_percent: float
    memory_percent: float
    disk_percent: float


@dataclass
class CapacityForecast:
    """容量予測"""

    resource_type: str
    current_usage: float
    predicted_usage_7d: float
    predicted_usage_30d: float
    predicted_usage_90d: float
    capacity_threshold: float
    days_until_threshold: Optional[int]
    growth_rate_daily: float


@dataclass
class ScalingRecommendation:
    """スケーリング推奨事項"""

    resource_type: str
    action: str  # "scale_up", "scale_down", "no_action"
    urgency: str  # "critical", "high", "medium", "low"
    current_capacity: float
    recommended_capacity: float
    reason: str
    estimated_days_until_needed: Optional[int]


@dataclass
class CapacityPlan:
    """容量計画"""

    generated_at: str
    forecast_period_days: int
    forecasts: List[CapacityForecast]
    recommendations: List[ScalingRecommendation]
    alerts: List[Dict[str, Any]]
    summary: Dict[str, Any]
