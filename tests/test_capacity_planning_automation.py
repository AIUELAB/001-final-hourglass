"""
tests/test_capacity_planning_automation.py - capacity_planning_automation.py ユニットテスト
"""

from unittest.mock import MagicMock, patch

import pytest

# database_utilsが利用できない場合はスキップ
try:
    from src.database_utils import get_connection

    db_utils_available = True
except (ImportError, ModuleNotFoundError):
    db_utils_available = False

pytestmark = pytest.mark.skipif(
    not db_utils_available, reason="database_utils not available"
)


class TestResourceMetrics:
    """ResourceMetricsデータクラステスト"""

    def test_metrics_creation(self):
        """ResourceMetrics作成"""
        from src.capacity_planning_automation import ResourceMetrics

        metrics = ResourceMetrics(
            timestamp="2025-01-01T00:00:00",
            cpu_percent=65.0,
            memory_percent=70.0,
            disk_percent=45.0,
        )

        assert metrics.cpu_percent == 65.0
        assert metrics.memory_percent == 70.0
        assert metrics.disk_percent == 45.0


class TestCapacityForecast:
    """CapacityForecastデータクラステスト"""

    def test_forecast_creation(self):
        """CapacityForecast作成"""
        from src.capacity_planning_automation import CapacityForecast

        forecast = CapacityForecast(
            resource_type="CPU",
            current_usage=65.0,
            predicted_usage_7d=70.0,
            predicted_usage_30d=75.0,
            predicted_usage_90d=85.0,
            capacity_threshold=80.0,
            days_until_threshold=45,
            growth_rate_daily=0.3,
        )

        assert forecast.resource_type == "CPU"
        assert forecast.predicted_usage_90d == 85.0
        assert forecast.days_until_threshold == 45


class TestScalingRecommendation:
    """ScalingRecommendationデータクラステスト"""

    def test_recommendation_creation(self):
        """ScalingRecommendation作成"""
        from src.capacity_planning_automation import ScalingRecommendation

        rec = ScalingRecommendation(
            resource_type="MEMORY",
            action="scale_up",
            urgency="high",
            current_capacity=16.0,
            recommended_capacity=32.0,
            reason="メモリ使用率が閾値に近づいている",
            estimated_days_until_needed=14,
        )

        assert rec.action == "scale_up"
        assert rec.urgency == "high"
        assert rec.recommended_capacity == 32.0


class TestCapacityPlan:
    """CapacityPlanデータクラステスト"""

    def test_plan_creation(self):
        """CapacityPlan作成"""
        from src.capacity_planning_automation import (
            CapacityForecast,
            CapacityPlan,
            ScalingRecommendation,
        )

        forecast = CapacityForecast(
            resource_type="CPU",
            current_usage=65.0,
            predicted_usage_7d=70.0,
            predicted_usage_30d=75.0,
            predicted_usage_90d=85.0,
            capacity_threshold=80.0,
            days_until_threshold=45,
            growth_rate_daily=0.3,
        )

        rec = ScalingRecommendation(
            resource_type="CPU",
            action="scale_up",
            urgency="medium",
            current_capacity=100.0,
            recommended_capacity=150.0,
            reason="成長予測に基づく",
            estimated_days_until_needed=45,
        )

        plan = CapacityPlan(
            generated_at="2025-01-01T00:00:00",
            forecast_period_days=90,
            forecasts=[forecast],
            recommendations=[rec],
            alerts=[],
            summary={"status": "OK"},
        )

        assert plan.forecast_period_days == 90
        assert len(plan.forecasts) == 1
        assert len(plan.recommendations) == 1


class TestCapacityPlanningAutomationInit:
    """CapacityPlanningAutomation初期化テスト"""

    @patch("src.capacity_planning_automation.Path.mkdir")
    def test_init_default(self, mock_mkdir):
        """デフォルト初期化"""
        from src.capacity_planning_automation import CapacityPlanningAutomation

        automation = CapacityPlanningAutomation()

        assert automation.capacity_thresholds["cpu"] == 80.0
        assert automation.capacity_thresholds["memory"] == 85.0
        assert automation.capacity_thresholds["disk"] == 90.0

    @patch("src.capacity_planning_automation.Path.mkdir")
    def test_init_models_empty(self, mock_mkdir):
        """モデルは初期状態で空"""
        from src.capacity_planning_automation import CapacityPlanningAutomation

        automation = CapacityPlanningAutomation()

        assert automation.models == {}


class TestSklearnAvailability:
    """sklearn可用性テスト"""

    def test_sklearn_flag_exists(self):
        """SKLEARN_AVAILABLEフラグが存在"""
        from src.capacity_planning_automation import SKLEARN_AVAILABLE

        assert isinstance(SKLEARN_AVAILABLE, bool)


class TestCapacityThresholds:
    """容量閾値テスト"""

    @patch("src.capacity_planning_automation.Path.mkdir")
    def test_threshold_values(self, mock_mkdir):
        """閾値の値"""
        from src.capacity_planning_automation import CapacityPlanningAutomation

        automation = CapacityPlanningAutomation()

        # CPU閾値は80%
        assert automation.capacity_thresholds["cpu"] == 80.0

        # メモリ閾値は85%
        assert automation.capacity_thresholds["memory"] == 85.0

        # ディスク閾値は90%
        assert automation.capacity_thresholds["disk"] == 90.0


class TestActionTypes:
    """アクションタイプテスト"""

    def test_valid_actions(self):
        """有効なアクション"""
        from src.capacity_planning_automation import ScalingRecommendation

        valid_actions = ["scale_up", "scale_down", "no_action"]

        for action in valid_actions:
            rec = ScalingRecommendation(
                resource_type="CPU",
                action=action,
                urgency="low",
                current_capacity=100.0,
                recommended_capacity=100.0,
                reason="テスト",
                estimated_days_until_needed=None,
            )
            assert rec.action == action


class TestUrgencyLevels:
    """緊急度レベルテスト"""

    def test_valid_urgency_levels(self):
        """有効な緊急度レベル"""
        from src.capacity_planning_automation import ScalingRecommendation

        valid_urgency = ["critical", "high", "medium", "low"]

        for urgency in valid_urgency:
            rec = ScalingRecommendation(
                resource_type="CPU",
                action="scale_up",
                urgency=urgency,
                current_capacity=100.0,
                recommended_capacity=150.0,
                reason="テスト",
                estimated_days_until_needed=None,
            )
            assert rec.urgency == urgency
