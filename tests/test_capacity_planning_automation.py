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

pytestmark = pytest.mark.skipif(not db_utils_available, reason="database_utils not available")


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


class TestCalculateGrowthRate:
    """_calculate_growth_rate メソッドテスト"""

    @patch("src.capacity_planning_automation.Path.mkdir")
    @patch("src.capacity_planning_automation.get_connection")
    def test_growth_rate_positive(self, mock_conn, mock_mkdir):
        """正の成長率"""
        from src.capacity_planning_automation import CapacityPlanningAutomation

        automation = CapacityPlanningAutomation()
        values = [10.0, 20.0, 30.0, 40.0, 50.0]  # 5日間で40増加
        rate = automation._calculate_growth_rate(values)

        assert rate == 8.0  # (50-10) / 5 = 8

    @patch("src.capacity_planning_automation.Path.mkdir")
    @patch("src.capacity_planning_automation.get_connection")
    def test_growth_rate_negative(self, mock_conn, mock_mkdir):
        """負の成長率"""
        from src.capacity_planning_automation import CapacityPlanningAutomation

        automation = CapacityPlanningAutomation()
        values = [50.0, 40.0, 30.0]  # 3日間で20減少
        rate = automation._calculate_growth_rate(values)

        assert rate < 0  # 負の成長率

    @patch("src.capacity_planning_automation.Path.mkdir")
    @patch("src.capacity_planning_automation.get_connection")
    def test_growth_rate_single_value(self, mock_conn, mock_mkdir):
        """単一値の場合は0"""
        from src.capacity_planning_automation import CapacityPlanningAutomation

        automation = CapacityPlanningAutomation()
        values = [50.0]
        rate = automation._calculate_growth_rate(values)

        assert rate == 0.0

    @patch("src.capacity_planning_automation.Path.mkdir")
    @patch("src.capacity_planning_automation.get_connection")
    def test_growth_rate_empty(self, mock_conn, mock_mkdir):
        """空リストの場合は0"""
        from src.capacity_planning_automation import CapacityPlanningAutomation

        automation = CapacityPlanningAutomation()
        values = []
        rate = automation._calculate_growth_rate(values)

        assert rate == 0.0


class TestCalculateDaysUntilThreshold:
    """_calculate_days_until_threshold メソッドテスト"""

    @patch("src.capacity_planning_automation.Path.mkdir")
    @patch("src.capacity_planning_automation.get_connection")
    def test_days_until_threshold_positive(self, mock_conn, mock_mkdir):
        """正の成長率で閾値到達"""
        from src.capacity_planning_automation import CapacityPlanningAutomation

        automation = CapacityPlanningAutomation()
        days = automation._calculate_days_until_threshold(50.0, 1.0, 80.0)

        assert days == 30  # (80-50) / 1 = 30

    @patch("src.capacity_planning_automation.Path.mkdir")
    @patch("src.capacity_planning_automation.get_connection")
    def test_days_until_threshold_zero_growth(self, mock_conn, mock_mkdir):
        """成長率0の場合はNone"""
        from src.capacity_planning_automation import CapacityPlanningAutomation

        automation = CapacityPlanningAutomation()
        days = automation._calculate_days_until_threshold(50.0, 0.0, 80.0)

        assert days is None

    @patch("src.capacity_planning_automation.Path.mkdir")
    @patch("src.capacity_planning_automation.get_connection")
    def test_days_until_threshold_negative_growth(self, mock_conn, mock_mkdir):
        """負の成長率の場合はNone"""
        from src.capacity_planning_automation import CapacityPlanningAutomation

        automation = CapacityPlanningAutomation()
        days = automation._calculate_days_until_threshold(50.0, -1.0, 80.0)

        assert days is None

    @patch("src.capacity_planning_automation.Path.mkdir")
    @patch("src.capacity_planning_automation.get_connection")
    def test_days_until_threshold_already_exceeded(self, mock_conn, mock_mkdir):
        """既に閾値超過の場合は0"""
        from src.capacity_planning_automation import CapacityPlanningAutomation

        automation = CapacityPlanningAutomation()
        days = automation._calculate_days_until_threshold(85.0, 1.0, 80.0)

        assert days == 0


class TestGenerateForecast:
    """_generate_forecast メソッドテスト"""

    @patch("src.capacity_planning_automation.Path.mkdir")
    @patch("src.capacity_planning_automation.get_connection")
    def test_forecast_with_data(self, mock_conn, mock_mkdir):
        """十分なデータでの予測"""
        from src.capacity_planning_automation import CapacityPlanningAutomation

        automation = CapacityPlanningAutomation()
        data = [
            ("2025-01-01T00:00:00", 50.0),
            ("2025-01-02T00:00:00", 51.0),
            ("2025-01-03T00:00:00", 52.0),
        ]

        forecast = automation._generate_forecast("cpu", data, 90)

        assert forecast.resource_type == "cpu"
        assert forecast.current_usage == 52.0
        assert forecast.capacity_threshold == 80.0

    @patch("src.capacity_planning_automation.Path.mkdir")
    @patch("src.capacity_planning_automation.get_connection")
    def test_forecast_insufficient_data(self, mock_conn, mock_mkdir):
        """データ不足の場合"""
        from src.capacity_planning_automation import CapacityPlanningAutomation

        automation = CapacityPlanningAutomation()
        data = [("2025-01-01T00:00:00", 60.0)]

        forecast = automation._generate_forecast("memory", data, 90)

        assert forecast.current_usage == 60.0
        assert forecast.predicted_usage_7d == 60.0
        assert forecast.growth_rate_daily == 0.0

    @patch("src.capacity_planning_automation.Path.mkdir")
    @patch("src.capacity_planning_automation.get_connection")
    def test_forecast_empty_data(self, mock_conn, mock_mkdir):
        """空データの場合"""
        from src.capacity_planning_automation import CapacityPlanningAutomation

        automation = CapacityPlanningAutomation()
        data = []

        forecast = automation._generate_forecast("disk", data, 90)

        assert forecast.current_usage == 0.0


class TestAnalyzeForecastAndRecommend:
    """_analyze_forecast_and_recommend メソッドテスト"""

    @patch("src.capacity_planning_automation.Path.mkdir")
    @patch("src.capacity_planning_automation.get_connection")
    def test_recommend_scale_up_critical(self, mock_conn, mock_mkdir):
        """緊急スケールアップ推奨"""
        from src.capacity_planning_automation import (
            CapacityForecast,
            CapacityPlanningAutomation,
        )

        automation = CapacityPlanningAutomation()
        forecast = CapacityForecast(
            resource_type="cpu",
            current_usage=75.0,
            predicted_usage_7d=82.0,
            predicted_usage_30d=90.0,
            predicted_usage_90d=100.0,
            capacity_threshold=80.0,
            days_until_threshold=5,
            growth_rate_daily=1.0,
        )

        rec = automation._analyze_forecast_and_recommend(forecast)

        assert rec is not None
        assert rec.action == "scale_up"
        assert rec.urgency == "critical"

    @patch("src.capacity_planning_automation.Path.mkdir")
    @patch("src.capacity_planning_automation.get_connection")
    def test_recommend_scale_up_high(self, mock_conn, mock_mkdir):
        """高優先度スケールアップ推奨"""
        from src.capacity_planning_automation import (
            CapacityForecast,
            CapacityPlanningAutomation,
        )

        automation = CapacityPlanningAutomation()
        forecast = CapacityForecast(
            resource_type="cpu",
            current_usage=70.0,
            predicted_usage_7d=78.0,
            predicted_usage_30d=85.0,
            predicted_usage_90d=95.0,
            capacity_threshold=80.0,
            days_until_threshold=10,
            growth_rate_daily=0.8,
        )

        rec = automation._analyze_forecast_and_recommend(forecast)

        assert rec is not None
        assert rec.action == "scale_up"
        assert rec.urgency == "high"

    @patch("src.capacity_planning_automation.Path.mkdir")
    @patch("src.capacity_planning_automation.get_connection")
    def test_recommend_scale_down(self, mock_conn, mock_mkdir):
        """スケールダウン推奨"""
        from src.capacity_planning_automation import (
            CapacityForecast,
            CapacityPlanningAutomation,
        )

        automation = CapacityPlanningAutomation()
        forecast = CapacityForecast(
            resource_type="memory",
            current_usage=20.0,
            predicted_usage_7d=20.5,
            predicted_usage_30d=21.0,
            predicted_usage_90d=22.0,
            capacity_threshold=85.0,
            days_until_threshold=None,
            growth_rate_daily=0.05,
        )

        rec = automation._analyze_forecast_and_recommend(forecast)

        assert rec is not None
        assert rec.action == "scale_down"
        assert rec.urgency == "low"

    @patch("src.capacity_planning_automation.Path.mkdir")
    @patch("src.capacity_planning_automation.get_connection")
    def test_recommend_no_action(self, mock_conn, mock_mkdir):
        """アクション不要"""
        from src.capacity_planning_automation import (
            CapacityForecast,
            CapacityPlanningAutomation,
        )

        automation = CapacityPlanningAutomation()
        forecast = CapacityForecast(
            resource_type="disk",
            current_usage=50.0,
            predicted_usage_7d=52.0,
            predicted_usage_30d=55.0,
            predicted_usage_90d=60.0,
            capacity_threshold=90.0,
            days_until_threshold=None,
            growth_rate_daily=0.2,
        )

        rec = automation._analyze_forecast_and_recommend(forecast)

        assert rec is None


class TestGenerateAlerts:
    """_generate_alerts メソッドテスト"""

    @patch("src.capacity_planning_automation.Path.mkdir")
    @patch("src.capacity_planning_automation.get_connection")
    def test_generate_capacity_shortage_alert(self, mock_conn, mock_mkdir):
        """容量不足アラート生成"""
        from src.capacity_planning_automation import (
            CapacityForecast,
            CapacityPlanningAutomation,
        )

        automation = CapacityPlanningAutomation()
        forecasts = [
            CapacityForecast(
                resource_type="cpu",
                current_usage=75.0,
                predicted_usage_7d=80.0,
                predicted_usage_30d=85.0,
                predicted_usage_90d=90.0,
                capacity_threshold=80.0,
                days_until_threshold=5,
                growth_rate_daily=1.0,
            )
        ]
        recommendations = []

        alerts = automation._generate_alerts(forecasts, recommendations)

        assert len(alerts) >= 1
        assert any(a["category"] == "capacity_shortage" for a in alerts)
        assert any(a["level"] == "critical" for a in alerts)

    @patch("src.capacity_planning_automation.Path.mkdir")
    @patch("src.capacity_planning_automation.get_connection")
    def test_generate_high_growth_rate_alert(self, mock_conn, mock_mkdir):
        """高成長率アラート生成"""
        from src.capacity_planning_automation import (
            CapacityForecast,
            CapacityPlanningAutomation,
        )

        automation = CapacityPlanningAutomation()
        forecasts = [
            CapacityForecast(
                resource_type="memory",
                current_usage=50.0,
                predicted_usage_7d=60.0,
                predicted_usage_30d=70.0,
                predicted_usage_90d=80.0,
                capacity_threshold=85.0,
                days_until_threshold=None,
                growth_rate_daily=1.5,  # 1%以上
            )
        ]
        recommendations = []

        alerts = automation._generate_alerts(forecasts, recommendations)

        assert any(a["category"] == "high_growth_rate" for a in alerts)


class TestGenerateSummary:
    """_generate_summary メソッドテスト"""

    @patch("src.capacity_planning_automation.Path.mkdir")
    @patch("src.capacity_planning_automation.get_connection")
    def test_summary_critical_status(self, mock_conn, mock_mkdir):
        """クリティカルステータスのサマリー"""
        from src.capacity_planning_automation import (
            CapacityForecast,
            CapacityPlanningAutomation,
            ScalingRecommendation,
        )

        automation = CapacityPlanningAutomation()
        forecasts = [
            CapacityForecast(
                resource_type="cpu",
                current_usage=78.0,
                predicted_usage_7d=82.0,
                predicted_usage_30d=90.0,
                predicted_usage_90d=100.0,
                capacity_threshold=80.0,
                days_until_threshold=3,
                growth_rate_daily=1.0,
            )
        ]
        recommendations = [
            ScalingRecommendation(
                resource_type="cpu",
                action="scale_up",
                urgency="critical",
                current_capacity=78.0,
                recommended_capacity=120.0,
                reason="緊急",
                estimated_days_until_needed=3,
            )
        ]
        alerts = []

        summary = automation._generate_summary(forecasts, recommendations, alerts)

        assert summary["overall_status"] == "critical"
        assert summary["most_critical_resource"] == "cpu"
        assert summary["critical_recommendations"] == 1

    @patch("src.capacity_planning_automation.Path.mkdir")
    @patch("src.capacity_planning_automation.get_connection")
    def test_summary_healthy_status(self, mock_conn, mock_mkdir):
        """健全ステータスのサマリー"""
        from src.capacity_planning_automation import (
            CapacityForecast,
            CapacityPlanningAutomation,
        )

        automation = CapacityPlanningAutomation()
        forecasts = [
            CapacityForecast(
                resource_type="cpu",
                current_usage=30.0,
                predicted_usage_7d=32.0,
                predicted_usage_30d=35.0,
                predicted_usage_90d=40.0,
                capacity_threshold=80.0,
                days_until_threshold=None,
                growth_rate_daily=0.1,
            )
        ]
        recommendations = []
        alerts = []

        summary = automation._generate_summary(forecasts, recommendations, alerts)

        assert summary["overall_status"] == "healthy"


class TestPrintMethods:
    """print メソッドテスト"""

    @patch("src.capacity_planning_automation.Path.mkdir")
    @patch("src.capacity_planning_automation.get_connection")
    def test_print_forecast(self, mock_conn, mock_mkdir, capsys):
        """_print_forecast が出力を生成"""
        from src.capacity_planning_automation import (
            CapacityForecast,
            CapacityPlanningAutomation,
        )

        automation = CapacityPlanningAutomation()
        forecast = CapacityForecast(
            resource_type="cpu",
            current_usage=65.0,
            predicted_usage_7d=70.0,
            predicted_usage_30d=75.0,
            predicted_usage_90d=80.0,
            capacity_threshold=80.0,
            days_until_threshold=30,
            growth_rate_daily=0.5,
        )

        automation._print_forecast(forecast)
        captured = capsys.readouterr()

        assert "CPU" in captured.out
        assert "65.0" in captured.out

    @patch("src.capacity_planning_automation.Path.mkdir")
    @patch("src.capacity_planning_automation.get_connection")
    def test_print_recommendation(self, mock_conn, mock_mkdir, capsys):
        """_print_recommendation が出力を生成"""
        from src.capacity_planning_automation import (
            CapacityPlanningAutomation,
            ScalingRecommendation,
        )

        automation = CapacityPlanningAutomation()
        rec = ScalingRecommendation(
            resource_type="memory",
            action="scale_up",
            urgency="high",
            current_capacity=80.0,
            recommended_capacity=100.0,
            reason="テスト理由",
            estimated_days_until_needed=10,
        )

        automation._print_recommendation(rec)
        captured = capsys.readouterr()

        assert "MEMORY" in captured.out
        assert "HIGH" in captured.out

    @patch("src.capacity_planning_automation.Path.mkdir")
    @patch("src.capacity_planning_automation.get_connection")
    def test_print_alert(self, mock_conn, mock_mkdir, capsys):
        """_print_alert が出力を生成"""
        from src.capacity_planning_automation import CapacityPlanningAutomation

        automation = CapacityPlanningAutomation()
        alert = {
            "level": "critical",
            "message": "テストアラート",
        }

        automation._print_alert(alert)
        captured = capsys.readouterr()

        assert "CRITICAL" in captured.out
        assert "テストアラート" in captured.out


class TestSaveCapacityPlanReport:
    """save_capacity_plan_report メソッドテスト"""

    @patch("src.capacity_planning_automation.Path.mkdir")
    @patch("src.capacity_planning_automation.get_connection")
    def test_save_report(self, mock_conn, mock_mkdir, tmp_path):
        """レポート保存"""
        from src.capacity_planning_automation import (
            CapacityForecast,
            CapacityPlan,
            CapacityPlanningAutomation,
        )

        automation = CapacityPlanningAutomation()
        automation.reports_dir = tmp_path

        plan = CapacityPlan(
            generated_at="2025-01-01T00:00:00",
            forecast_period_days=90,
            forecasts=[
                CapacityForecast(
                    resource_type="cpu",
                    current_usage=50.0,
                    predicted_usage_7d=55.0,
                    predicted_usage_30d=60.0,
                    predicted_usage_90d=70.0,
                    capacity_threshold=80.0,
                    days_until_threshold=60,
                    growth_rate_daily=0.3,
                )
            ],
            recommendations=[],
            alerts=[],
            summary={"overall_status": "healthy"},
        )

        output_path = automation.save_capacity_plan_report(plan, "test_report.json")

        assert output_path.exists()
        import json

        with open(output_path) as f:
            saved_data = json.load(f)
        assert saved_data["forecast_period_days"] == 90


class TestCollectResourceData:
    """_collect_resource_data メソッドテスト"""

    @patch("src.capacity_planning_automation.Path.mkdir")
    @patch("src.capacity_planning_automation.get_connection")
    def test_collect_data_with_results(self, mock_conn, mock_mkdir):
        """データ収集（結果あり）"""
        from src.capacity_planning_automation import CapacityPlanningAutomation

        # モックカーソルの設定
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("2025-01-01T00:00:00", 50.0, 60.0, 70.0),
            ("2025-01-02T00:00:00", 51.0, 61.0, 71.0),
        ]
        mock_conn.return_value.cursor.return_value = mock_cursor

        automation = CapacityPlanningAutomation()
        data = automation._collect_resource_data(30)

        assert len(data["cpu"]) == 2
        assert len(data["memory"]) == 2
        assert len(data["disk"]) == 2


class TestGenerateRecommendations:
    """_generate_recommendations メソッドテスト"""

    @patch("src.capacity_planning_automation.Path.mkdir")
    @patch("src.capacity_planning_automation.get_connection")
    def test_generate_recommendations_with_issues(self, mock_conn, mock_mkdir):
        """問題がある場合の推奨事項生成"""
        from src.capacity_planning_automation import (
            CapacityForecast,
            CapacityPlanningAutomation,
        )

        automation = CapacityPlanningAutomation()
        forecasts = [
            CapacityForecast(
                resource_type="cpu",
                current_usage=75.0,
                predicted_usage_7d=82.0,
                predicted_usage_30d=90.0,
                predicted_usage_90d=100.0,
                capacity_threshold=80.0,
                days_until_threshold=5,
                growth_rate_daily=1.0,
            ),
            CapacityForecast(
                resource_type="memory",
                current_usage=50.0,
                predicted_usage_7d=52.0,
                predicted_usage_30d=55.0,
                predicted_usage_90d=60.0,
                capacity_threshold=85.0,
                days_until_threshold=None,
                growth_rate_daily=0.2,
            ),
        ]

        recommendations = automation._generate_recommendations(forecasts)

        assert len(recommendations) >= 1
        assert any(r.resource_type == "cpu" for r in recommendations)


class TestMainFunction:
    """main 関数テスト"""

    @patch("src.capacity_planning_automation.CapacityPlanningAutomation")
    @patch("sys.argv", ["capacity_planning_automation.py"])
    def test_main_no_args(self, mock_class, capsys):
        """引数なしで実行"""
        from src.capacity_planning_automation import main

        main()
        captured = capsys.readouterr()

        assert "オプションを指定してください" in captured.out

    @patch("src.capacity_planning_automation.CapacityPlanningAutomation")
    @patch("sys.argv", ["capacity_planning_automation.py", "--generate"])
    def test_main_with_generate(self, mock_class):
        """--generate オプションで実行"""
        from src.capacity_planning_automation import (
            CapacityForecast,
            CapacityPlan,
            main,
        )

        mock_instance = MagicMock()
        mock_class.return_value = mock_instance

        # モックの戻り値を設定
        mock_plan = CapacityPlan(
            generated_at="2025-01-01T00:00:00",
            forecast_period_days=90,
            forecasts=[],
            recommendations=[],
            alerts=[],
            summary={
                "overall_status": "healthy",
                "status_message": "OK",
                "most_critical_resource": None,
                "days_until_critical": None,
                "total_recommendations": 0,
                "critical_recommendations": 0,
                "high_recommendations": 0,
                "total_alerts": 0,
            },
        )
        mock_instance.generate_capacity_plan.return_value = mock_plan

        main()

        mock_instance.generate_capacity_plan.assert_called_once()

    @patch("src.capacity_planning_automation.CapacityPlanningAutomation")
    @patch("sys.argv", ["capacity_planning_automation.py", "--generate", "--save"])
    def test_main_with_generate_and_save(self, mock_class):
        """--generate --save オプションで実行"""
        from src.capacity_planning_automation import CapacityPlan, main

        mock_instance = MagicMock()
        mock_class.return_value = mock_instance

        mock_plan = CapacityPlan(
            generated_at="2025-01-01T00:00:00",
            forecast_period_days=90,
            forecasts=[],
            recommendations=[],
            alerts=[],
            summary={
                "overall_status": "healthy",
                "status_message": "OK",
                "most_critical_resource": None,
                "days_until_critical": None,
                "total_recommendations": 0,
                "critical_recommendations": 0,
                "high_recommendations": 0,
                "total_alerts": 0,
            },
        )
        mock_instance.generate_capacity_plan.return_value = mock_plan

        main()

        mock_instance.save_capacity_plan_report.assert_called_once()
