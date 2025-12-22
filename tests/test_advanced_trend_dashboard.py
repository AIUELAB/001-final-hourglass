"""
tests/test_advanced_trend_dashboard.py - advanced_trend_dashboard.py ユニットテスト
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


class TestPredictionTrend:
    """PredictionTrendデータクラステスト"""

    def test_trend_creation(self):
        """PredictionTrend作成"""
        from src.advanced_trend_dashboard import PredictionTrend

        trend = PredictionTrend(
            timestamp="2025-01-01T00:00:00",
            failure_probability=0.35,
            risk_level="MEDIUM",
            model_agreement=0.85,
            ensemble_predictions={"rf": 0.3, "gb": 0.4},
        )

        assert trend.failure_probability == 0.35
        assert trend.risk_level == "MEDIUM"
        assert trend.model_agreement == 0.85


class TestAutoMLExperiment:
    """AutoMLExperimentデータクラステスト"""

    def test_experiment_creation(self):
        """AutoMLExperiment作成"""
        from src.advanced_trend_dashboard import AutoMLExperiment

        experiment = AutoMLExperiment(
            experiment_id="EXP001",
            timestamp="2025-01-01T00:00:00",
            best_model="RandomForest",
            best_score=0.92,
            cv_mean=0.90,
            cv_std=0.02,
            model_scores={"rf": 0.92, "gb": 0.88},
        )

        assert experiment.experiment_id == "EXP001"
        assert experiment.best_model == "RandomForest"
        assert experiment.best_score == 0.92


class TestDashboardMetrics:
    """DashboardMetricsデータクラステスト"""

    def test_metrics_creation(self):
        """DashboardMetrics作成"""
        from src.advanced_trend_dashboard import (
            DashboardMetrics,
            PredictionTrend,
        )

        latest_prediction = PredictionTrend(
            timestamp="2025-01-01T00:00:00",
            failure_probability=0.25,
            risk_level="LOW",
            model_agreement=0.9,
            ensemble_predictions={},
        )

        metrics = DashboardMetrics(
            total_predictions=100,
            avg_failure_probability=0.30,
            avg_model_agreement=0.85,
            high_risk_count=10,
            medium_risk_count=30,
            low_risk_count=60,
            latest_prediction=latest_prediction,
            latest_experiment=None,
        )

        assert metrics.total_predictions == 100
        assert metrics.high_risk_count == 10
        assert metrics.low_risk_count == 60


class TestAdvancedTrendDashboardInit:
    """AdvancedTrendDashboard初期化テスト"""

    @patch("src.advanced_trend_dashboard.get_connection")
    @patch("src.advanced_trend_dashboard.Path.mkdir")
    def test_init_default(self, mock_mkdir, mock_get_conn):
        """デフォルト初期化"""
        from src.advanced_trend_dashboard import AdvancedTrendDashboard

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        dashboard = AdvancedTrendDashboard()

        assert dashboard.db_path is not None
        mock_mkdir.assert_called()


class TestPlotlyAvailability:
    """Plotly可用性テスト"""

    def test_plotly_flag_exists(self):
        """PLOTLY_AVAILABLEフラグが存在"""
        from src.advanced_trend_dashboard import PLOTLY_AVAILABLE

        assert isinstance(PLOTLY_AVAILABLE, bool)


class TestRiskLevels:
    """リスクレベルテスト"""

    def test_valid_risk_levels(self):
        """有効なリスクレベル"""
        from src.advanced_trend_dashboard import PredictionTrend

        valid_levels = ["HIGH", "MEDIUM", "LOW"]

        for level in valid_levels:
            trend = PredictionTrend(
                timestamp="2025-01-01",
                failure_probability=0.5,
                risk_level=level,
                model_agreement=0.8,
                ensemble_predictions={},
            )
            assert trend.risk_level == level


class TestModelAgreementRange:
    """モデル合意度範囲テスト"""

    def test_model_agreement_valid_range(self):
        """モデル合意度の有効範囲"""
        from src.advanced_trend_dashboard import PredictionTrend

        # 0.0から1.0の範囲
        for agreement in [0.0, 0.5, 1.0]:
            trend = PredictionTrend(
                timestamp="2025-01-01",
                failure_probability=0.3,
                risk_level="LOW",
                model_agreement=agreement,
                ensemble_predictions={},
            )
            assert 0.0 <= trend.model_agreement <= 1.0


class TestFailureProbabilityRange:
    """失敗確率範囲テスト"""

    def test_failure_probability_valid_range(self):
        """失敗確率の有効範囲"""
        from src.advanced_trend_dashboard import PredictionTrend

        # 0.0から1.0の範囲
        for prob in [0.0, 0.25, 0.5, 0.75, 1.0]:
            trend = PredictionTrend(
                timestamp="2025-01-01",
                failure_probability=prob,
                risk_level="MEDIUM",
                model_agreement=0.8,
                ensemble_predictions={},
            )
            assert 0.0 <= trend.failure_probability <= 1.0


class TestDashboardMetricsCalculations:
    """ダッシュボードメトリクス計算テスト"""

    def test_risk_count_sum(self):
        """リスクカウントの合計"""
        from src.advanced_trend_dashboard import DashboardMetrics

        metrics = DashboardMetrics(
            total_predictions=100,
            avg_failure_probability=0.30,
            avg_model_agreement=0.85,
            high_risk_count=10,
            medium_risk_count=30,
            low_risk_count=60,
            latest_prediction=None,
            latest_experiment=None,
        )

        # 合計が total_predictions と一致
        total_risk = (
            metrics.high_risk_count + metrics.medium_risk_count + metrics.low_risk_count
        )
        assert total_risk == metrics.total_predictions

    def test_metrics_with_no_predictions(self):
        """予測なしのメトリクス"""
        from src.advanced_trend_dashboard import DashboardMetrics

        metrics = DashboardMetrics(
            total_predictions=0,
            avg_failure_probability=0.0,
            avg_model_agreement=0.0,
            high_risk_count=0,
            medium_risk_count=0,
            low_risk_count=0,
            latest_prediction=None,
            latest_experiment=None,
        )

        assert metrics.total_predictions == 0
        assert metrics.latest_prediction is None
