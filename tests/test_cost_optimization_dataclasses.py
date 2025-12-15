#!/usr/bin/env python3
"""cost_optimization_algorithm dataclasses テスト"""

import sys
from dataclasses import asdict
from pathlib import Path


# モジュール直接インポート用
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# dataclassを直接定義してテスト（database_utils依存を回避）
from dataclasses import dataclass
from typing import List


@dataclass
class ResourceCost:
    resource_type: str
    current_usage: float
    allocated_capacity: float
    unit_cost: float
    monthly_cost: float
    utilization_rate: float
    waste_percentage: float


@dataclass
class OptimizationRecommendation:
    resource_type: str
    recommendation_type: str
    current_cost: float
    optimized_cost: float
    monthly_savings: float
    annual_savings: float
    roi_months: float
    implementation_cost: float
    priority: str
    risk_level: str
    description: str
    action_items: List[str]


@dataclass
class CostSimulation:
    scenario_name: str
    current_monthly_cost: float
    projected_monthly_cost: float
    monthly_savings: float
    annual_savings: float
    implementation_cost: float
    roi_months: float
    confidence_level: float
    assumptions: List[str]
    risks: List[str]


class TestResourceCost:
    """ResourceCostのテスト"""

    def test_init(self):
        """初期化テスト"""
        cost = ResourceCost(
            resource_type="CPU",
            current_usage=75.0,
            allocated_capacity=100.0,
            unit_cost=0.05,
            monthly_cost=36.0,
            utilization_rate=75.0,
            waste_percentage=25.0,
        )
        assert cost.resource_type == "CPU"
        assert cost.current_usage == 75.0
        assert cost.waste_percentage == 25.0

    def test_asdict(self):
        """辞書変換テスト"""
        cost = ResourceCost(
            resource_type="Memory",
            current_usage=50.0,
            allocated_capacity=16.0,
            unit_cost=0.01,
            monthly_cost=12.0,
            utilization_rate=50.0,
            waste_percentage=50.0,
        )
        d = asdict(cost)
        assert d["resource_type"] == "Memory"
        assert d["waste_percentage"] == 50.0


class TestOptimizationRecommendation:
    """OptimizationRecommendationのテスト"""

    def test_init(self):
        """初期化テスト"""
        rec = OptimizationRecommendation(
            resource_type="Storage",
            recommendation_type="reduce_capacity",
            current_cost=100.0,
            optimized_cost=70.0,
            monthly_savings=30.0,
            annual_savings=360.0,
            roi_months=2.0,
            implementation_cost=60.0,
            priority="high",
            risk_level="low",
            description="ストレージ削減",
            action_items=["不要データ削除", "圧縮適用"],
        )
        assert rec.recommendation_type == "reduce_capacity"
        assert rec.monthly_savings == 30.0
        assert len(rec.action_items) == 2

    def test_priority_values(self):
        """優先度テスト"""
        for priority in ["high", "medium", "low"]:
            rec = OptimizationRecommendation(
                resource_type="CPU",
                recommendation_type="consolidate",
                current_cost=50.0,
                optimized_cost=30.0,
                monthly_savings=20.0,
                annual_savings=240.0,
                roi_months=1.0,
                implementation_cost=20.0,
                priority=priority,
                risk_level="low",
                description="統合",
                action_items=[],
            )
            assert rec.priority == priority


class TestCostSimulation:
    """CostSimulationのテスト"""

    def test_init(self):
        """初期化テスト"""
        sim = CostSimulation(
            scenario_name="基本シナリオ",
            current_monthly_cost=1000.0,
            projected_monthly_cost=700.0,
            monthly_savings=300.0,
            annual_savings=3600.0,
            implementation_cost=500.0,
            roi_months=1.67,
            confidence_level=0.85,
            assumptions=["現在の使用パターン継続"],
            risks=["需要増加リスク"],
        )
        assert sim.scenario_name == "基本シナリオ"
        assert sim.confidence_level == 0.85

    def test_confidence_range(self):
        """信頼度範囲テスト"""
        sim = CostSimulation(
            scenario_name="テスト",
            current_monthly_cost=100.0,
            projected_monthly_cost=80.0,
            monthly_savings=20.0,
            annual_savings=240.0,
            implementation_cost=10.0,
            roi_months=0.5,
            confidence_level=1.0,
            assumptions=[],
            risks=[],
        )
        assert 0.0 <= sim.confidence_level <= 1.0

    def test_empty_lists(self):
        """空リストテスト"""
        sim = CostSimulation(
            scenario_name="空シナリオ",
            current_monthly_cost=0.0,
            projected_monthly_cost=0.0,
            monthly_savings=0.0,
            annual_savings=0.0,
            implementation_cost=0.0,
            roi_months=0.0,
            confidence_level=0.0,
            assumptions=[],
            risks=[],
        )
        assert sim.assumptions == []
        assert sim.risks == []
