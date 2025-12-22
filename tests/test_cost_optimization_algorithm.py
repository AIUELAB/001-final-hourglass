"""
tests/test_cost_optimization_algorithm.py - cost_optimization_algorithm.py ユニットテスト
"""

import json
import sys
from unittest.mock import MagicMock, patch

import pytest

# database_utilsのモックを設定
mock_database_utils = MagicMock()
mock_database_utils.get_connection = MagicMock()
sys.modules["src.database_utils"] = mock_database_utils


class TestResourceCost:
    """ResourceCostデータクラステスト"""

    def test_resource_cost_creation(self):
        """ResourceCost作成"""
        from src.cost_optimization_algorithm import ResourceCost

        cost = ResourceCost(
            resource_type="CPU",
            current_usage=65.0,
            allocated_capacity=100.0,
            unit_cost=0.05,
            monthly_cost=36.0,
            utilization_rate=65.0,
            waste_percentage=35.0,
        )

        assert cost.resource_type == "CPU"
        assert cost.current_usage == 65.0
        assert cost.allocated_capacity == 100.0
        assert cost.unit_cost == 0.05
        assert cost.monthly_cost == 36.0
        assert cost.utilization_rate == 65.0
        assert cost.waste_percentage == 35.0

    def test_resource_cost_memory(self):
        """MEMORYタイプのResourceCost"""
        from src.cost_optimization_algorithm import ResourceCost

        cost = ResourceCost(
            resource_type="MEMORY",
            current_usage=80.0,
            allocated_capacity=16.0,
            unit_cost=0.01,
            monthly_cost=116.8,
            utilization_rate=80.0,
            waste_percentage=20.0,
        )

        assert cost.resource_type == "MEMORY"
        assert cost.waste_percentage == 20.0

    def test_resource_cost_disk(self):
        """DISKタイプのResourceCost"""
        from src.cost_optimization_algorithm import ResourceCost

        cost = ResourceCost(
            resource_type="DISK",
            current_usage=50.0,
            allocated_capacity=500.0,
            unit_cost=0.001,
            monthly_cost=365.0,
            utilization_rate=50.0,
            waste_percentage=50.0,
        )

        assert cost.resource_type == "DISK"
        assert cost.allocated_capacity == 500.0


class TestOptimizationRecommendation:
    """OptimizationRecommendationデータクラステスト"""

    def test_recommendation_creation(self):
        """OptimizationRecommendation作成"""
        from src.cost_optimization_algorithm import OptimizationRecommendation

        rec = OptimizationRecommendation(
            resource_type="CPU",
            recommendation_type="reduce_capacity",
            current_cost=100.0,
            optimized_cost=70.0,
            monthly_savings=30.0,
            annual_savings=360.0,
            roi_months=2.0,
            implementation_cost=60.0,
            priority="high",
            risk_level="low",
            description="CPU容量を削減",
            action_items=["リソース削減", "モニタリング強化"],
        )

        assert rec.resource_type == "CPU"
        assert rec.recommendation_type == "reduce_capacity"
        assert rec.monthly_savings == 30.0
        assert rec.annual_savings == 360.0
        assert rec.priority == "high"
        assert rec.risk_level == "low"
        assert len(rec.action_items) == 2

    def test_recommendation_increase_efficiency(self):
        """効率化推奨"""
        from src.cost_optimization_algorithm import OptimizationRecommendation

        rec = OptimizationRecommendation(
            resource_type="MEMORY",
            recommendation_type="increase_efficiency",
            current_cost=200.0,
            optimized_cost=160.0,
            monthly_savings=40.0,
            annual_savings=480.0,
            roi_months=1.5,
            implementation_cost=60.0,
            priority="medium",
            risk_level="medium",
            description="メモリ効率化",
            action_items=["パターン最適化", "スケーリング設定"],
        )

        assert rec.recommendation_type == "increase_efficiency"
        assert rec.priority == "medium"

    def test_recommendation_consolidate(self):
        """統合推奨"""
        from src.cost_optimization_algorithm import OptimizationRecommendation

        rec = OptimizationRecommendation(
            resource_type="DISK",
            recommendation_type="consolidate",
            current_cost=500.0,
            optimized_cost=350.0,
            monthly_savings=150.0,
            annual_savings=1800.0,
            roi_months=0.5,
            implementation_cost=75.0,
            priority="high",
            risk_level="low",
            description="ディスク統合",
            action_items=["データ移行", "古いボリューム削除"],
        )

        assert rec.recommendation_type == "consolidate"


class TestCostSimulation:
    """CostSimulationデータクラステスト"""

    def test_simulation_creation(self):
        """CostSimulation作成"""
        from src.cost_optimization_algorithm import CostSimulation

        sim = CostSimulation(
            scenario_name="コスト削減シナリオA",
            current_monthly_cost=1000.0,
            projected_monthly_cost=700.0,
            monthly_savings=300.0,
            annual_savings=3600.0,
            implementation_cost=200.0,
            roi_months=0.67,
            confidence_level=0.85,
            assumptions=["現在の使用パターンが継続"],
            risks=["需要増加のリスク"],
        )

        assert sim.scenario_name == "コスト削減シナリオA"
        assert sim.current_monthly_cost == 1000.0
        assert sim.projected_monthly_cost == 700.0
        assert sim.confidence_level == 0.85
        assert len(sim.assumptions) == 1
        assert len(sim.risks) == 1

    def test_simulation_high_confidence(self):
        """高信頼度シミュレーション"""
        from src.cost_optimization_algorithm import CostSimulation

        sim = CostSimulation(
            scenario_name="保守的シナリオ",
            current_monthly_cost=500.0,
            projected_monthly_cost=450.0,
            monthly_savings=50.0,
            annual_savings=600.0,
            implementation_cost=20.0,
            roi_months=0.4,
            confidence_level=0.95,
            assumptions=["最小限の変更のみ"],
            risks=["特になし"],
        )

        assert sim.confidence_level == 0.95

    def test_simulation_multiple_assumptions(self):
        """複数前提条件のシミュレーション"""
        from src.cost_optimization_algorithm import CostSimulation

        sim = CostSimulation(
            scenario_name="積極的シナリオ",
            current_monthly_cost=2000.0,
            projected_monthly_cost=1200.0,
            monthly_savings=800.0,
            annual_savings=9600.0,
            implementation_cost=500.0,
            roi_months=0.625,
            confidence_level=0.75,
            assumptions=["全推奨事項実装", "リソース使用パターン安定", "追加投資可能"],
            risks=["実装遅延", "予算超過", "パフォーマンス低下"],
        )

        assert len(sim.assumptions) == 3
        assert len(sim.risks) == 3


class TestCostOptimizationAlgorithmInit:
    """CostOptimizationAlgorithm初期化テスト"""

    @patch("src.cost_optimization_algorithm.get_connection")
    def test_init(self, mock_get_conn):
        """初期化"""
        from src.cost_optimization_algorithm import CostOptimizationAlgorithm

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        algo = CostOptimizationAlgorithm(db_path="test.db")

        assert algo.db_path == "test.db"
        assert "CPU" in algo.cost_config
        assert "MEMORY" in algo.cost_config
        assert "DISK" in algo.cost_config
        mock_get_conn.assert_called_once_with("test.db")

    @patch("src.cost_optimization_algorithm.get_connection")
    def test_init_default_path(self, mock_get_conn):
        """デフォルトパスでの初期化"""
        from src.cost_optimization_algorithm import CostOptimizationAlgorithm

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        algo = CostOptimizationAlgorithm()

        assert algo.db_path == "unified_quality.db"

    @patch("src.cost_optimization_algorithm.get_connection")
    def test_cost_config_structure(self, mock_get_conn):
        """コスト設定の構造"""
        from src.cost_optimization_algorithm import CostOptimizationAlgorithm

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        algo = CostOptimizationAlgorithm()

        for resource_type, config in algo.cost_config.items():
            assert "unit_cost" in config
            assert "unit_name" in config
            assert config["unit_cost"] > 0

    @patch("src.cost_optimization_algorithm.get_connection")
    def test_optimization_thresholds(self, mock_get_conn):
        """最適化しきい値"""
        from src.cost_optimization_algorithm import CostOptimizationAlgorithm

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        algo = CostOptimizationAlgorithm()

        assert algo.optimization_thresholds["low_utilization"] == 30
        assert algo.optimization_thresholds["high_waste"] == 40
        assert algo.optimization_thresholds["target_utilization"] == 70


class TestCostConfigValues:
    """コスト設定値テスト"""

    @patch("src.cost_optimization_algorithm.get_connection")
    def test_cpu_cost(self, mock_get_conn):
        """CPU単価"""
        from src.cost_optimization_algorithm import CostOptimizationAlgorithm

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        algo = CostOptimizationAlgorithm()

        assert algo.cost_config["CPU"]["unit_cost"] == 0.05
        assert algo.cost_config["CPU"]["unit_name"] == "vCPU"

    @patch("src.cost_optimization_algorithm.get_connection")
    def test_memory_cost(self, mock_get_conn):
        """メモリ単価"""
        from src.cost_optimization_algorithm import CostOptimizationAlgorithm

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        algo = CostOptimizationAlgorithm()

        assert algo.cost_config["MEMORY"]["unit_cost"] == 0.01
        assert algo.cost_config["MEMORY"]["unit_name"] == "GB"

    @patch("src.cost_optimization_algorithm.get_connection")
    def test_disk_cost(self, mock_get_conn):
        """ディスク単価"""
        from src.cost_optimization_algorithm import CostOptimizationAlgorithm

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        algo = CostOptimizationAlgorithm()

        assert algo.cost_config["DISK"]["unit_cost"] == 0.001
        assert algo.cost_config["DISK"]["unit_name"] == "GB"


class TestAnalyzeResourceCosts:
    """analyze_resource_costsメソッドテスト"""

    @patch("src.cost_optimization_algorithm.get_connection")
    def test_analyze_cpu_costs(self, mock_get_conn):
        """CPUコスト分析"""
        from src.cost_optimization_algorithm import CostOptimizationAlgorithm

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (65.0, "2024-01-01T00:00:00")
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        algo = CostOptimizationAlgorithm()
        cost = algo.analyze_resource_costs("CPU")

        assert cost is not None
        assert cost.resource_type == "CPU"
        assert cost.current_usage == 65.0
        assert cost.utilization_rate == 65.0
        assert cost.waste_percentage == 35.0

    @patch("src.cost_optimization_algorithm.get_connection")
    def test_analyze_memory_costs(self, mock_get_conn):
        """メモリコスト分析"""
        from src.cost_optimization_algorithm import CostOptimizationAlgorithm

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (80.0, "2024-01-01T00:00:00")
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        algo = CostOptimizationAlgorithm()
        cost = algo.analyze_resource_costs("MEMORY")

        assert cost is not None
        assert cost.resource_type == "MEMORY"
        assert cost.current_usage == 80.0

    @patch("src.cost_optimization_algorithm.get_connection")
    def test_analyze_disk_costs(self, mock_get_conn):
        """ディスクコスト分析"""
        from src.cost_optimization_algorithm import CostOptimizationAlgorithm

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (50.0, "2024-01-01T00:00:00")
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        algo = CostOptimizationAlgorithm()
        cost = algo.analyze_resource_costs("DISK")

        assert cost is not None
        assert cost.resource_type == "DISK"

    @patch("src.cost_optimization_algorithm.get_connection")
    def test_analyze_invalid_resource(self, mock_get_conn):
        """無効なリソースタイプ"""
        from src.cost_optimization_algorithm import CostOptimizationAlgorithm

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        algo = CostOptimizationAlgorithm()
        cost = algo.analyze_resource_costs("INVALID")

        assert cost is None

    @patch("src.cost_optimization_algorithm.get_connection")
    def test_analyze_no_data(self, mock_get_conn):
        """データなし"""
        from src.cost_optimization_algorithm import CostOptimizationAlgorithm

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        algo = CostOptimizationAlgorithm()
        cost = algo.analyze_resource_costs("CPU")

        assert cost is None

    @patch("src.cost_optimization_algorithm.get_connection")
    def test_analyze_monthly_cost_calculation(self, mock_get_conn):
        """月間コスト計算"""
        from src.cost_optimization_algorithm import CostOptimizationAlgorithm

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (50.0, "2024-01-01T00:00:00")
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        algo = CostOptimizationAlgorithm()
        cost = algo.analyze_resource_costs("CPU")

        # 100 * 0.05 * 730 = 3650
        assert cost.monthly_cost == 100.0 * 0.05 * 730


class TestAnalyzeCostAndRecommend:
    """_analyze_cost_and_recommendメソッドテスト"""

    @patch("src.cost_optimization_algorithm.get_connection")
    def test_low_utilization_recommendation(self, mock_get_conn):
        """低稼働率の推奨"""
        from src.cost_optimization_algorithm import (
            CostOptimizationAlgorithm,
            ResourceCost,
        )

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        algo = CostOptimizationAlgorithm()

        cost = ResourceCost(
            resource_type="CPU",
            current_usage=20.0,
            allocated_capacity=100.0,
            unit_cost=0.05,
            monthly_cost=3650.0,
            utilization_rate=20.0,
            waste_percentage=80.0,
        )

        rec = algo._analyze_cost_and_recommend(cost)

        assert rec is not None
        assert rec.recommendation_type == "reduce_capacity"
        assert rec.priority == "high"  # waste > 50
        assert rec.monthly_savings > 0

    @patch("src.cost_optimization_algorithm.get_connection")
    def test_high_waste_recommendation(self, mock_get_conn):
        """高無駄率の推奨"""
        from src.cost_optimization_algorithm import (
            CostOptimizationAlgorithm,
            ResourceCost,
        )

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        algo = CostOptimizationAlgorithm()

        cost = ResourceCost(
            resource_type="MEMORY",
            current_usage=55.0,
            allocated_capacity=100.0,
            unit_cost=0.01,
            monthly_cost=730.0,
            utilization_rate=55.0,
            waste_percentage=45.0,
        )

        rec = algo._analyze_cost_and_recommend(cost)

        assert rec is not None
        assert rec.recommendation_type == "increase_efficiency"
        assert rec.priority == "medium"

    @patch("src.cost_optimization_algorithm.get_connection")
    def test_no_recommendation_needed(self, mock_get_conn):
        """推奨不要"""
        from src.cost_optimization_algorithm import (
            CostOptimizationAlgorithm,
            ResourceCost,
        )

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        algo = CostOptimizationAlgorithm()

        cost = ResourceCost(
            resource_type="DISK",
            current_usage=70.0,
            allocated_capacity=100.0,
            unit_cost=0.001,
            monthly_cost=73.0,
            utilization_rate=70.0,
            waste_percentage=30.0,
        )

        rec = algo._analyze_cost_and_recommend(cost)

        assert rec is None

    @patch("src.cost_optimization_algorithm.get_connection")
    def test_roi_calculation(self, mock_get_conn):
        """ROI計算"""
        from src.cost_optimization_algorithm import (
            CostOptimizationAlgorithm,
            ResourceCost,
        )

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        algo = CostOptimizationAlgorithm()

        cost = ResourceCost(
            resource_type="CPU",
            current_usage=15.0,
            allocated_capacity=100.0,
            unit_cost=0.05,
            monthly_cost=3650.0,
            utilization_rate=15.0,
            waste_percentage=85.0,
        )

        rec = algo._analyze_cost_and_recommend(cost)

        assert rec is not None
        assert rec.roi_months > 0
        assert rec.implementation_cost > 0


class TestGenerateCostSimulations:
    """_generate_cost_simulationsメソッドテスト"""

    @patch("src.cost_optimization_algorithm.get_connection")
    def test_generate_simulations_with_recommendations(self, mock_get_conn):
        """推奨事項ありのシミュレーション生成"""
        from src.cost_optimization_algorithm import (
            CostOptimizationAlgorithm,
            OptimizationRecommendation,
            ResourceCost,
        )

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        algo = CostOptimizationAlgorithm()

        costs = [
            ResourceCost(
                resource_type="CPU",
                current_usage=20.0,
                allocated_capacity=100.0,
                unit_cost=0.05,
                monthly_cost=3650.0,
                utilization_rate=20.0,
                waste_percentage=80.0,
            )
        ]

        recommendations = [
            OptimizationRecommendation(
                resource_type="CPU",
                recommendation_type="reduce_capacity",
                current_cost=3650.0,
                optimized_cost=1000.0,
                monthly_savings=2650.0,
                annual_savings=31800.0,
                roi_months=0.14,
                implementation_cost=365.0,
                priority="high",
                risk_level="low",
                description="容量削減",
                action_items=["削減実施"],
            )
        ]

        simulations = algo._generate_cost_simulations(costs, recommendations)

        assert len(simulations) >= 2  # 全実装 + 段階的
        assert any(s.scenario_name == "全推奨事項の実装" for s in simulations)
        assert any(s.scenario_name == "段階的実装（6ヶ月計画）" for s in simulations)

    @patch("src.cost_optimization_algorithm.get_connection")
    def test_generate_simulations_high_priority_only(self, mock_get_conn):
        """高優先度のみシミュレーション"""
        from src.cost_optimization_algorithm import (
            CostOptimizationAlgorithm,
            OptimizationRecommendation,
            ResourceCost,
        )

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        algo = CostOptimizationAlgorithm()

        costs = [
            ResourceCost(
                resource_type="CPU",
                current_usage=20.0,
                allocated_capacity=100.0,
                unit_cost=0.05,
                monthly_cost=3650.0,
                utilization_rate=20.0,
                waste_percentage=80.0,
            )
        ]

        recommendations = [
            OptimizationRecommendation(
                resource_type="CPU",
                recommendation_type="reduce_capacity",
                current_cost=3650.0,
                optimized_cost=1000.0,
                monthly_savings=2650.0,
                annual_savings=31800.0,
                roi_months=0.14,
                implementation_cost=365.0,
                priority="high",
                risk_level="low",
                description="容量削減",
                action_items=["削減実施"],
            )
        ]

        simulations = algo._generate_cost_simulations(costs, recommendations)

        assert any(s.scenario_name == "高優先度のみ実装" for s in simulations)

    @patch("src.cost_optimization_algorithm.get_connection")
    def test_generate_simulations_empty_recommendations(self, mock_get_conn):
        """推奨事項なしのシミュレーション"""
        from src.cost_optimization_algorithm import (
            CostOptimizationAlgorithm,
            ResourceCost,
        )

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        algo = CostOptimizationAlgorithm()

        costs = [
            ResourceCost(
                resource_type="CPU",
                current_usage=70.0,
                allocated_capacity=100.0,
                unit_cost=0.05,
                monthly_cost=3650.0,
                utilization_rate=70.0,
                waste_percentage=30.0,
            )
        ]

        simulations = algo._generate_cost_simulations(costs, [])

        assert len(simulations) == 0


class TestSaveResourceCost:
    """_save_resource_costメソッドテスト"""

    @patch("src.cost_optimization_algorithm.get_connection")
    def test_save_resource_cost(self, mock_get_conn):
        """リソースコスト保存"""
        from src.cost_optimization_algorithm import (
            CostOptimizationAlgorithm,
            ResourceCost,
        )

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        algo = CostOptimizationAlgorithm()

        cost = ResourceCost(
            resource_type="CPU",
            current_usage=65.0,
            allocated_capacity=100.0,
            unit_cost=0.05,
            monthly_cost=3650.0,
            utilization_rate=65.0,
            waste_percentage=35.0,
        )

        algo._save_resource_cost("2024-01-01T00:00:00", cost)

        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called()
        mock_conn.close.assert_called()


class TestSaveOptimizationRecommendation:
    """_save_optimization_recommendationメソッドテスト"""

    @patch("src.cost_optimization_algorithm.get_connection")
    def test_save_recommendation(self, mock_get_conn):
        """推奨事項保存"""
        from src.cost_optimization_algorithm import (
            CostOptimizationAlgorithm,
            OptimizationRecommendation,
        )

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        algo = CostOptimizationAlgorithm()

        rec = OptimizationRecommendation(
            resource_type="CPU",
            recommendation_type="reduce_capacity",
            current_cost=100.0,
            optimized_cost=70.0,
            monthly_savings=30.0,
            annual_savings=360.0,
            roi_months=2.0,
            implementation_cost=60.0,
            priority="high",
            risk_level="low",
            description="CPU容量削減",
            action_items=["削減実施"],
        )

        algo._save_optimization_recommendation("2024-01-01T00:00:00", rec)

        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called()


class TestSaveCostSimulation:
    """_save_cost_simulationメソッドテスト"""

    @patch("src.cost_optimization_algorithm.get_connection")
    def test_save_simulation(self, mock_get_conn):
        """シミュレーション保存"""
        from src.cost_optimization_algorithm import (
            CostOptimizationAlgorithm,
            CostSimulation,
        )

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        algo = CostOptimizationAlgorithm()

        sim = CostSimulation(
            scenario_name="テストシナリオ",
            current_monthly_cost=1000.0,
            projected_monthly_cost=700.0,
            monthly_savings=300.0,
            annual_savings=3600.0,
            implementation_cost=100.0,
            roi_months=0.33,
            confidence_level=0.85,
            assumptions=["仮定1"],
            risks=["リスク1"],
        )

        algo._save_cost_simulation("2024-01-01T00:00:00", sim)

        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called()


class TestSaveOptimizationPlan:
    """_save_optimization_planメソッドテスト"""

    @patch("src.cost_optimization_algorithm.get_connection")
    def test_save_plan(self, mock_get_conn):
        """計画保存"""
        from src.cost_optimization_algorithm import CostOptimizationAlgorithm

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        algo = CostOptimizationAlgorithm()

        plan_data = {
            "timestamp": "2024-01-01T00:00:00",
            "costs": [],
            "recommendations": [],
            "simulations": [],
            "summary": {"total_current_cost": 1000.0},
        }

        algo._save_optimization_plan("2024-01-01T00:00:00", plan_data)

        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called()


class TestShowHistory:
    """show_historyメソッドテスト"""

    @patch("src.cost_optimization_algorithm.get_connection")
    def test_show_history_with_data(self, mock_get_conn, capsys):
        """履歴表示（データあり）"""
        from src.cost_optimization_algorithm import CostOptimizationAlgorithm

        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        plan_data = {
            "summary": {
                "total_current_cost": 1000.0,
                "total_monthly_savings": 200.0,
                "savings_percentage": 20.0,
                "recommendation_count": 2,
            }
        }

        mock_cursor.fetchall.return_value = [("2024-01-01T00:00:00", json.dumps(plan_data))]
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        algo = CostOptimizationAlgorithm()
        algo.show_history(limit=5)

        captured = capsys.readouterr()
        assert "コスト最適化計画の履歴" in captured.out
        assert "$1000.00" in captured.out
        assert "$200.00" in captured.out

    @patch("src.cost_optimization_algorithm.get_connection")
    def test_show_history_no_data(self, mock_get_conn, capsys):
        """履歴表示（データなし）"""
        from src.cost_optimization_algorithm import CostOptimizationAlgorithm

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        algo = CostOptimizationAlgorithm()
        algo.show_history()

        captured = capsys.readouterr()
        assert "履歴がありません" in captured.out


class TestGenerateCostOptimizationPlan:
    """generate_cost_optimization_planメソッドテスト"""

    @patch("src.cost_optimization_algorithm.get_connection")
    def test_generate_plan_with_data(self, mock_get_conn, capsys):
        """計画生成（データあり）"""
        from src.cost_optimization_algorithm import CostOptimizationAlgorithm

        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # 初期化時とanalyze時で異なる結果を返す
        mock_cursor.fetchone.side_effect = [
            (20.0, "2024-01-01T00:00:00"),  # CPU
            (55.0, "2024-01-01T00:00:00"),  # MEMORY
            (70.0, "2024-01-01T00:00:00"),  # DISK
        ]

        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        algo = CostOptimizationAlgorithm()
        plan = algo.generate_cost_optimization_plan()

        assert "timestamp" in plan
        assert "costs" in plan
        assert "recommendations" in plan
        assert "simulations" in plan
        assert "summary" in plan

        captured = capsys.readouterr()
        assert "コスト最適化アルゴリズム" in captured.out
        assert "リソースコストの分析" in captured.out

    @patch("src.cost_optimization_algorithm.get_connection")
    def test_generate_plan_no_data(self, mock_get_conn, capsys):
        """計画生成（データなし）"""
        from src.cost_optimization_algorithm import CostOptimizationAlgorithm

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        algo = CostOptimizationAlgorithm()
        plan = algo.generate_cost_optimization_plan()

        assert len(plan["costs"]) == 0
        assert len(plan["recommendations"]) == 0


class TestMain:
    """main関数テスト"""

    @patch("src.cost_optimization_algorithm.CostOptimizationAlgorithm")
    @patch("sys.argv", ["prog", "--help"])
    def test_main_help(self, mock_algo_class, capsys):
        """ヘルプ表示"""
        from src.cost_optimization_algorithm import main

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0

    @patch("src.cost_optimization_algorithm.get_connection")
    @patch("sys.argv", ["prog"])
    def test_main_no_args(self, mock_get_conn, capsys):
        """引数なし"""
        from src.cost_optimization_algorithm import main

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        main()

        captured = capsys.readouterr()
        assert "usage:" in captured.out.lower() or "--generate" in captured.out

    @patch("src.cost_optimization_algorithm.get_connection")
    @patch("sys.argv", ["prog", "--history", "--limit", "5"])
    def test_main_history(self, mock_get_conn, capsys):
        """履歴表示"""
        from src.cost_optimization_algorithm import main

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        main()

        captured = capsys.readouterr()
        assert "履歴がありません" in captured.out

    @patch("src.cost_optimization_algorithm.get_connection")
    @patch("sys.argv", ["prog", "--generate"])
    def test_main_generate(self, mock_get_conn, capsys):
        """計画生成"""
        from src.cost_optimization_algorithm import main

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        main()

        captured = capsys.readouterr()
        assert "コスト最適化アルゴリズム" in captured.out

    @patch("src.cost_optimization_algorithm.get_connection")
    @patch("sys.argv", ["prog", "--generate", "--save"])
    def test_main_generate_with_save(self, mock_get_conn, capsys, tmp_path, monkeypatch):
        """計画生成＋保存"""
        from src.cost_optimization_algorithm import main

        # 一時ディレクトリに変更
        monkeypatch.chdir(tmp_path)

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        main()

        captured = capsys.readouterr()
        assert "コスト最適化アルゴリズム" in captured.out
        assert "レポート保存" in captured.out

        # ファイルが作成されたか確認
        import os

        reports_dir = tmp_path / "reports" / "cost_optimization"
        assert reports_dir.exists()
        json_files = list(reports_dir.glob("*.json"))
        assert len(json_files) == 1
