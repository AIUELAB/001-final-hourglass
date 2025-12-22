#!/usr/bin/env python3
"""コスト最適化アルゴリズム - データモデル"""

from dataclasses import dataclass
from typing import List


@dataclass
class ResourceCost:
    """リソースコスト情報"""

    resource_type: str
    current_usage: float  # 現在の使用量（%）
    allocated_capacity: float  # 割り当て容量
    unit_cost: float  # 単価（$/unit/hour）
    monthly_cost: float  # 月間コスト
    utilization_rate: float  # 稼働率（%）
    waste_percentage: float  # 無駄な割合（%）


@dataclass
class OptimizationRecommendation:
    """コスト最適化推奨事項"""

    resource_type: str
    recommendation_type: str  # reduce_capacity/increase_efficiency/consolidate/terminate
    current_cost: float
    optimized_cost: float
    monthly_savings: float
    annual_savings: float
    roi_months: float  # 投資回収期間（月）
    implementation_cost: float  # 実装コスト
    priority: str  # high/medium/low
    risk_level: str  # low/medium/high
    description: str
    action_items: List[str]


@dataclass
class CostSimulation:
    """コスト削減シミュレーション"""

    scenario_name: str
    current_monthly_cost: float
    projected_monthly_cost: float
    monthly_savings: float
    annual_savings: float
    implementation_cost: float
    roi_months: float
    confidence_level: float  # 0.0-1.0
    assumptions: List[str]
    risks: List[str]
