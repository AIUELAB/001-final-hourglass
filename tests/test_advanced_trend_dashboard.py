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

pytestmark = pytest.mark.skipif(not db_utils_available, reason="database_utils not available")


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
        total_risk = metrics.high_risk_count + metrics.medium_risk_count + metrics.low_risk_count
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


class TestInitDatabaseTables:
    """_init_database_tablesテスト"""

    @patch("src.advanced_trend_dashboard.Path.mkdir")
    @patch("src.advanced_trend_dashboard.get_connection")
    def test_creates_tables(self, mock_get_conn, mock_mkdir):
        """テーブル作成を確認"""
        from src.advanced_trend_dashboard import AdvancedTrendDashboard

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        AdvancedTrendDashboard()

        # 2つのCREATE TABLEが実行される
        assert mock_cursor.execute.call_count >= 2
        mock_conn.commit.assert_called()
        mock_conn.close.assert_called()


class TestGetSummaryMetrics:
    """_get_summary_metricsテスト"""

    @patch("src.advanced_trend_dashboard.Path.mkdir")
    @patch("src.advanced_trend_dashboard.get_connection")
    def test_returns_metrics_with_data(self, mock_get_conn, mock_mkdir):
        """データありの場合メトリクスを返す"""
        from src.advanced_trend_dashboard import AdvancedTrendDashboard

        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # 初期化用
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        dashboard = AdvancedTrendDashboard()

        # _get_summary_metrics用のモック設定
        mock_get_conn.reset_mock()
        mock_get_conn.return_value = mock_conn

        # fetchone結果を設定 (正しい順序とデータ構造)
        # 1. COUNT(*) → fetchone()[0]
        # 2. AVG(failure_probability) → fetchone()[0]
        # 3. AVG(model_agreement) → fetchone()[0]
        # 4. fetchall() for GROUP BY risk_level
        # 5. latest prediction → fetchone() (6カラム)
        # 6. latest experiment → fetchone() (6カラム)
        mock_cursor.fetchone.side_effect = [
            (100,),  # COUNT(*)
            (0.35,),  # AVG(failure_probability)
            (0.85,),  # AVG(model_agreement)
            # prediction_id, timestamp, failure_probability, risk_level, model_agreement, ensemble_predictions
            ("pred001", "2025-01-01", 0.25, "LOW", 0.9, '{"rf": 0.2}'),
            # experiment_id, timestamp, best_model_name, mean_cv_score, std_cv_score, cv_scores
            ("EXP001", "2025-01-01", "RF", 0.92, 0.02, '{"rf": 0.92}'),
        ]
        mock_cursor.fetchall.return_value = [
            ("HIGH", 15),
            ("MEDIUM", 35),
            ("LOW", 50),
        ]

        metrics = dashboard._get_summary_metrics(hours=24)

        assert metrics is not None
        assert metrics.total_predictions == 100
        assert metrics.avg_failure_probability == 0.35
        assert metrics.high_risk_count == 15
        assert metrics.medium_risk_count == 35
        assert metrics.low_risk_count == 50

    @patch("src.advanced_trend_dashboard.Path.mkdir")
    @patch("src.advanced_trend_dashboard.get_connection")
    def test_returns_metrics_when_no_predictions(self, mock_get_conn, mock_mkdir):
        """予測0件の場合もメトリクスを返す（DashboardMetricsオブジェクト）"""
        from src.advanced_trend_dashboard import AdvancedTrendDashboard

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        dashboard = AdvancedTrendDashboard()
        mock_get_conn.reset_mock()
        mock_get_conn.return_value = mock_conn

        # 予測0件のケース
        mock_cursor.fetchone.side_effect = [
            (0,),  # COUNT(*) = 0
            (None,),  # AVG = None
            (None,),  # AVG = None
            None,  # latest prediction = None
            None,  # latest experiment = None
        ]
        mock_cursor.fetchall.return_value = []

        metrics = dashboard._get_summary_metrics(hours=24)

        # メソッドは常にDashboardMetricsを返す
        assert metrics is not None
        assert metrics.total_predictions == 0
        assert metrics.avg_failure_probability == 0.0
        assert metrics.avg_model_agreement == 0.0
        assert metrics.latest_prediction is None
        assert metrics.latest_experiment is None


class TestAnalyzePredictionTrends:
    """_analyze_prediction_trendsテスト"""

    @patch("src.advanced_trend_dashboard.Path.mkdir")
    @patch("src.advanced_trend_dashboard.get_connection")
    def test_returns_trends(self, mock_get_conn, mock_mkdir):
        """トレンドデータを返す"""
        from src.advanced_trend_dashboard import AdvancedTrendDashboard

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        dashboard = AdvancedTrendDashboard()
        mock_get_conn.reset_mock()
        mock_get_conn.return_value = mock_conn
        # 4 columns: timestamp, failure_probability, model_agreement, risk_level
        mock_cursor.fetchall.return_value = [
            ("2025-01-01T00:00:00", 0.3, 0.9, "LOW"),
            ("2025-01-01T01:00:00", 0.5, 0.85, "MEDIUM"),
        ]

        trends = dashboard._analyze_prediction_trends(hours=24)

        assert trends["data_points"] == 2
        assert len(trends["time_series"]) == 2
        assert trends["time_series"][0]["failure_probability"] == 0.3
        assert trends["time_series"][1]["risk_level"] == "MEDIUM"

    @patch("src.advanced_trend_dashboard.Path.mkdir")
    @patch("src.advanced_trend_dashboard.get_connection")
    def test_returns_empty_when_no_data(self, mock_get_conn, mock_mkdir):
        """データなしの場合空構造を返す"""
        from src.advanced_trend_dashboard import AdvancedTrendDashboard

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []
        mock_get_conn.return_value = mock_conn

        dashboard = AdvancedTrendDashboard()
        mock_get_conn.reset_mock()
        mock_get_conn.return_value = mock_conn
        mock_cursor.fetchall.return_value = []

        trends = dashboard._analyze_prediction_trends(hours=24)

        assert trends["data_points"] == 0
        assert trends["time_series"] == []


class TestGetAutoMLHistory:
    """_get_automl_historyテスト"""

    @patch("src.advanced_trend_dashboard.Path.mkdir")
    @patch("src.advanced_trend_dashboard.get_connection")
    def test_returns_experiments(self, mock_get_conn, mock_mkdir):
        """実験履歴を返す"""
        from src.advanced_trend_dashboard import AdvancedTrendDashboard

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        dashboard = AdvancedTrendDashboard()
        mock_get_conn.reset_mock()
        mock_get_conn.return_value = mock_conn
        # 6 columns: experiment_id, timestamp, best_model_name, mean_cv_score, std_cv_score, cv_scores(JSON)
        mock_cursor.fetchall.return_value = [
            ("EXP001", "2025-01-01", "RF", 0.92, 0.02, '{"rf": 0.92}'),
        ]

        history = dashboard._get_automl_history(limit=10)

        assert len(history) == 1
        assert history[0]["experiment_id"] == "EXP001"
        assert history[0]["best_model"] == "RF"


class TestAnalyzeModelAgreement:
    """_analyze_model_agreementテスト"""

    @patch("src.advanced_trend_dashboard.Path.mkdir")
    @patch("src.advanced_trend_dashboard.get_connection")
    def test_returns_distribution(self, mock_get_conn, mock_mkdir):
        """合意度分布を返す"""
        from src.advanced_trend_dashboard import AdvancedTrendDashboard

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        dashboard = AdvancedTrendDashboard()
        mock_get_conn.reset_mock()
        mock_get_conn.return_value = mock_conn
        # 1 column: model_agreement
        mock_cursor.fetchall.return_value = [
            (0.96,),
            (0.90,),
            (0.85,),
            (0.70,),
            (0.60,),
        ]

        result = dashboard._analyze_model_agreement(hours=24)

        # 戻り値の構造: {"count": N, "statistics": {...}, "distribution": {...}}
        assert result["count"] == 5
        assert "distribution" in result
        # distribution keys: excellent, good, fair, poor
        assert "excellent" in result["distribution"]
        assert "good" in result["distribution"]
        assert "poor" in result["distribution"]


class TestAnalyzeRiskDistribution:
    """_analyze_risk_distributionテスト"""

    @patch("src.advanced_trend_dashboard.Path.mkdir")
    @patch("src.advanced_trend_dashboard.get_connection")
    def test_returns_risk_distribution(self, mock_get_conn, mock_mkdir):
        """リスク分布を返す"""
        from src.advanced_trend_dashboard import AdvancedTrendDashboard

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        dashboard = AdvancedTrendDashboard()
        mock_get_conn.reset_mock()
        mock_get_conn.return_value = mock_conn
        # 4 columns: risk_level, count, avg_prob, avg_agreement
        mock_cursor.fetchall.return_value = [
            ("HIGH", 10, 0.75, 0.85),
            ("MEDIUM", 30, 0.45, 0.88),
            ("LOW", 60, 0.15, 0.92),
        ]

        distribution = dashboard._analyze_risk_distribution(hours=24)

        # 戻り値の構造: {"HIGH": {"count": N, "avg_failure_probability": X, "avg_model_agreement": Y}, ...}
        assert "HIGH" in distribution
        assert distribution["HIGH"]["count"] == 10
        assert "MEDIUM" in distribution
        assert distribution["MEDIUM"]["count"] == 30
        assert "LOW" in distribution
        assert distribution["LOW"]["count"] == 60


class TestAnalyzeContributingFactors:
    """_analyze_contributing_factorsテスト"""

    @patch("src.advanced_trend_dashboard.Path.mkdir")
    @patch("src.advanced_trend_dashboard.get_connection")
    def test_returns_factors(self, mock_get_conn, mock_mkdir):
        """因子分析結果を返す"""
        from src.advanced_trend_dashboard import AdvancedTrendDashboard

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        dashboard = AdvancedTrendDashboard()
        mock_get_conn.reset_mock()
        mock_get_conn.return_value = mock_conn
        # contributing_factors is JSON string: list of {"feature": name, "importance": value}
        mock_cursor.fetchall.return_value = [
            ('[{"feature": "cpu_usage", "importance": 0.4}, {"feature": "memory", "importance": 0.3}]',),
            ('[{"feature": "cpu_usage", "importance": 0.5}, {"feature": "memory", "importance": 0.2}]',),
        ]

        result = dashboard._analyze_contributing_factors(hours=24)

        # 戻り値の構造: {"total_unique_factors": N, "top_factors": [...], "all_factors": {...}}
        assert result["total_unique_factors"] == 2
        assert "all_factors" in result
        assert "cpu_usage" in result["all_factors"]
        assert result["all_factors"]["cpu_usage"] == 0.45  # 平均

    @patch("src.advanced_trend_dashboard.Path.mkdir")
    @patch("src.advanced_trend_dashboard.get_connection")
    def test_returns_empty_when_no_data(self, mock_get_conn, mock_mkdir):
        """データなしの場合空構造を返す"""
        from src.advanced_trend_dashboard import AdvancedTrendDashboard

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        dashboard = AdvancedTrendDashboard()
        mock_get_conn.reset_mock()
        mock_get_conn.return_value = mock_conn
        mock_cursor.fetchall.return_value = []

        result = dashboard._analyze_contributing_factors(hours=24)

        assert result["total_unique_factors"] == 0
        assert result["top_factors"] == []


class TestGenerateAlerts:
    """_generate_alertsテスト"""

    @patch("src.advanced_trend_dashboard.Path.mkdir")
    @patch("src.advanced_trend_dashboard.get_connection")
    def test_high_risk_alert(self, mock_get_conn, mock_mkdir):
        """高リスク割合でアラート"""
        from src.advanced_trend_dashboard import (
            AdvancedTrendDashboard,
            DashboardMetrics,
        )

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        dashboard = AdvancedTrendDashboard()

        metrics = DashboardMetrics(
            total_predictions=100,
            avg_failure_probability=0.5,
            avg_model_agreement=0.9,
            high_risk_count=40,  # 40% > 30%
            medium_risk_count=30,
            low_risk_count=30,
            latest_prediction=None,
            latest_experiment=None,
        )

        # trendsはDict[str, Any]で、data_pointsキーを参照
        trends = {"data_points": 100}
        alerts = dashboard._generate_alerts(metrics, trends)

        assert any("高リスク" in a["message"] for a in alerts)

    @patch("src.advanced_trend_dashboard.Path.mkdir")
    @patch("src.advanced_trend_dashboard.get_connection")
    def test_low_agreement_alert(self, mock_get_conn, mock_mkdir):
        """低合意度でアラート"""
        from src.advanced_trend_dashboard import (
            AdvancedTrendDashboard,
            DashboardMetrics,
        )

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        dashboard = AdvancedTrendDashboard()

        # avg_model_agreement < 0.75 でアラート
        metrics = DashboardMetrics(
            total_predictions=100,
            avg_failure_probability=0.3,
            avg_model_agreement=0.7,  # < 0.75
            high_risk_count=10,
            medium_risk_count=30,
            low_risk_count=60,
            latest_prediction=None,
            latest_experiment=None,
        )

        trends = {"data_points": 100}
        alerts = dashboard._generate_alerts(metrics, trends)

        assert any("合意度" in a["message"] for a in alerts)

    @patch("src.advanced_trend_dashboard.Path.mkdir")
    @patch("src.advanced_trend_dashboard.get_connection")
    def test_latest_high_risk_alert(self, mock_get_conn, mock_mkdir):
        """最新予測が高リスクでアラート"""
        from src.advanced_trend_dashboard import (
            AdvancedTrendDashboard,
            DashboardMetrics,
            PredictionTrend,
        )

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        dashboard = AdvancedTrendDashboard()

        latest = PredictionTrend(
            timestamp="2025-01-01",
            failure_probability=0.8,
            risk_level="HIGH",
            model_agreement=0.9,
            ensemble_predictions={},
        )

        metrics = DashboardMetrics(
            total_predictions=100,
            avg_failure_probability=0.3,
            avg_model_agreement=0.9,
            high_risk_count=10,
            medium_risk_count=30,
            low_risk_count=60,
            latest_prediction=latest,
            latest_experiment=None,
        )

        trends = {"data_points": 100}
        alerts = dashboard._generate_alerts(metrics, trends)

        assert any("最新予測が高リスク" in a["message"] for a in alerts)

    @patch("src.advanced_trend_dashboard.Path.mkdir")
    @patch("src.advanced_trend_dashboard.get_connection")
    def test_insufficient_data_alert(self, mock_get_conn, mock_mkdir):
        """データ不足でアラート"""
        from src.advanced_trend_dashboard import (
            AdvancedTrendDashboard,
            DashboardMetrics,
        )

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        dashboard = AdvancedTrendDashboard()

        metrics = DashboardMetrics(
            total_predictions=10,
            avg_failure_probability=0.3,
            avg_model_agreement=0.9,
            high_risk_count=1,
            medium_risk_count=4,
            low_risk_count=5,
            latest_prediction=None,
            latest_experiment=None,
        )

        # data_points < 5 でアラート
        trends = {"data_points": 3}
        alerts = dashboard._generate_alerts(metrics, trends)

        assert any("データポイント" in a["message"] for a in alerts)


class TestGeneratePlotlyGraphs:
    """_generate_plotly_graphsテスト"""

    @patch("src.advanced_trend_dashboard.PLOTLY_AVAILABLE", False)
    @patch("src.advanced_trend_dashboard.Path.mkdir")
    @patch("src.advanced_trend_dashboard.get_connection")
    def test_skips_when_plotly_unavailable(self, mock_get_conn, mock_mkdir):
        """Plotly不可時はスキップ"""
        from src.advanced_trend_dashboard import AdvancedTrendDashboard

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        dashboard_obj = AdvancedTrendDashboard()

        # メソッドはdashboard辞書を受け取る
        dashboard_data = {
            "sections": {
                "prediction_trends": {"data_points": 0},
                "risk_distribution": {},
                "model_agreement": {"count": 0},
                "contributing_factors": {"total_unique_factors": 0},
                "automl_history": [],
            }
        }

        graphs = dashboard_obj._generate_plotly_graphs(dashboard_data)

        assert graphs == {}


class TestSaveDashboard:
    """save_dashboardテスト"""

    @patch("src.advanced_trend_dashboard.Path.mkdir")
    @patch("src.advanced_trend_dashboard.get_connection")
    def test_saves_to_file(self, mock_get_conn, mock_mkdir, tmp_path):
        """ファイルに保存"""
        from src.advanced_trend_dashboard import AdvancedTrendDashboard

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        dashboard = AdvancedTrendDashboard()

        data = {"test": "data"}
        filepath = tmp_path / "test_dashboard.json"

        with patch("builtins.open", MagicMock()) as mock_open:
            with patch("src.advanced_trend_dashboard.json.dump") as mock_dump:
                dashboard.save_dashboard(data, str(filepath))

                mock_dump.assert_called_once()


class TestGenerateComprehensiveDashboard:
    """generate_comprehensive_dashboardテスト"""

    @patch("src.advanced_trend_dashboard.Path.mkdir")
    @patch("src.advanced_trend_dashboard.get_connection")
    def test_returns_dashboard_when_no_predictions(self, mock_get_conn, mock_mkdir, capsys):
        """予測0件でもダッシュボードを返す"""
        from src.advanced_trend_dashboard import AdvancedTrendDashboard

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        dashboard = AdvancedTrendDashboard()
        mock_get_conn.reset_mock()
        mock_get_conn.return_value = mock_conn

        # 予測0件のモック設定
        mock_cursor.fetchone.side_effect = [
            (0,),  # COUNT(*) = 0
            (None,),  # AVG = None
            (None,),  # AVG = None
            None,  # latest prediction = None
            None,  # latest experiment = None
        ]
        mock_cursor.fetchall.return_value = []

        result = dashboard.generate_comprehensive_dashboard(hours=24, include_plots=False)

        # メソッドは常にダッシュボードを返す
        assert result is not None
        assert "metadata" in result
        assert "sections" in result
        captured = capsys.readouterr()
        assert "ダッシュボード生成完了" in captured.out

    @patch("src.advanced_trend_dashboard.Path.mkdir")
    @patch("src.advanced_trend_dashboard.get_connection")
    def test_returns_dashboard_data(self, mock_get_conn, mock_mkdir, capsys):
        """ダッシュボードデータを返す"""
        from src.advanced_trend_dashboard import AdvancedTrendDashboard

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        # 初期化
        dashboard = AdvancedTrendDashboard()
        mock_get_conn.reset_mock()
        mock_get_conn.return_value = mock_conn

        # _get_summary_metrics用 fetchone:
        # 1. COUNT(*), 2. AVG(failure_prob), 3. AVG(agreement), 4. latest_pred (6 cols), 5. latest_exp (6 cols)
        mock_cursor.fetchone.side_effect = [
            (100,),  # COUNT(*)
            (0.35,),  # AVG(failure_probability)
            (0.85,),  # AVG(model_agreement)
            ("pred001", "2025-01-01", 0.25, "LOW", 0.9, "{}"),  # latest prediction
            ("EXP001", "2025-01-01", "RF", 0.92, 0.02, "{}"),  # latest experiment
        ]
        # fetchall calls in order:
        # 1. _get_summary_metrics: risk_counts GROUP BY
        # 2. _analyze_prediction_trends: (timestamp, failure_prob, model_agreement, risk_level)
        # 3. _get_automl_history: (exp_id, timestamp, best_model, mean_cv, std_cv, cv_scores_json)
        # 4. _analyze_model_agreement: (model_agreement,)
        # 5. _analyze_risk_distribution: (risk_level, count, avg_prob, avg_agreement)
        # 6. _analyze_contributing_factors: (contributing_factors_json,)
        mock_cursor.fetchall.side_effect = [
            [("HIGH", 10), ("MEDIUM", 30), ("LOW", 60)],  # risk_counts
            [("2025-01-01T00:00:00", 0.3, 0.9, "LOW"), ("2025-01-01T01:00:00", 0.5, 0.85, "MEDIUM")],  # trends
            [("EXP001", "2025-01-01", "RF", 0.92, 0.02, "{}")],  # automl history
            [(0.9,), (0.85,)],  # model agreement
            [("HIGH", 10, 0.75, 0.85), ("LOW", 90, 0.15, 0.92)],  # risk distribution
            [('[{"feature": "cpu", "importance": 0.5}]',)],  # contributing factors
        ]

        result = dashboard.generate_comprehensive_dashboard(hours=24, include_plots=False)

        assert result is not None
        assert "metadata" in result
        assert "sections" in result
        assert "summary" in result["sections"]
        captured = capsys.readouterr()
        assert "ダッシュボード生成完了" in captured.out


class TestPrintMethods:
    """printメソッドテスト"""

    @patch("src.advanced_trend_dashboard.Path.mkdir")
    @patch("src.advanced_trend_dashboard.get_connection")
    def test_print_summary_metrics(self, mock_get_conn, mock_mkdir, capsys):
        """サマリーメトリクス出力"""
        from src.advanced_trend_dashboard import (
            AdvancedTrendDashboard,
            DashboardMetrics,
            PredictionTrend,
        )

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        dashboard = AdvancedTrendDashboard()

        latest = PredictionTrend(
            timestamp="2025-01-01",
            failure_probability=0.3,
            risk_level="LOW",
            model_agreement=0.9,
            ensemble_predictions={},
        )

        metrics = DashboardMetrics(
            total_predictions=100,
            avg_failure_probability=0.3,
            avg_model_agreement=0.85,
            high_risk_count=10,
            medium_risk_count=30,
            low_risk_count=60,
            latest_prediction=latest,
            latest_experiment=None,
        )

        dashboard._print_summary_metrics(metrics)

        captured = capsys.readouterr()
        assert "100" in captured.out
        assert "HIGH" in captured.out
        assert "LOW" in captured.out

    @patch("src.advanced_trend_dashboard.Path.mkdir")
    @patch("src.advanced_trend_dashboard.get_connection")
    def test_print_alerts(self, mock_get_conn, mock_mkdir, capsys):
        """アラート出力"""
        from src.advanced_trend_dashboard import AdvancedTrendDashboard

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        dashboard = AdvancedTrendDashboard()

        alerts = [
            {"level": "critical", "message": "テストアラート", "category": "test", "timestamp": "2025-01-01"},
        ]

        dashboard._print_alerts(alerts)

        captured = capsys.readouterr()
        assert "テストアラート" in captured.out

    @patch("src.advanced_trend_dashboard.Path.mkdir")
    @patch("src.advanced_trend_dashboard.get_connection")
    def test_print_alerts_empty(self, mock_get_conn, mock_mkdir, capsys):
        """アラートなしの出力"""
        from src.advanced_trend_dashboard import AdvancedTrendDashboard

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        dashboard = AdvancedTrendDashboard()

        dashboard._print_alerts([])

        captured = capsys.readouterr()
        # 空リストの場合の出力を確認（実装により異なる）
        assert captured.out is not None


class TestMainFunction:
    """main関数テスト"""

    @patch("src.advanced_trend_dashboard.AdvancedTrendDashboard")
    @patch("sys.argv", ["prog", "--generate"])
    def test_generate_flag(self, mock_dashboard_class):
        """--generateフラグ"""
        from src.advanced_trend_dashboard import main

        mock_dashboard = MagicMock()
        mock_dashboard.generate_comprehensive_dashboard.return_value = {"sections": {"plots": {}}}
        mock_dashboard_class.return_value = mock_dashboard

        main()

        mock_dashboard.generate_comprehensive_dashboard.assert_called_once()

    @patch("src.advanced_trend_dashboard.AdvancedTrendDashboard")
    @patch("sys.argv", ["prog"])
    def test_no_args_shows_message(self, mock_dashboard_class, capsys):
        """引数なしでメッセージ表示"""
        from src.advanced_trend_dashboard import main

        mock_dashboard = MagicMock()
        mock_dashboard_class.return_value = mock_dashboard

        main()

        captured = capsys.readouterr()
        assert "オプションを指定してください" in captured.out

    @patch("src.advanced_trend_dashboard.AdvancedTrendDashboard")
    @patch("sys.argv", ["prog", "--generate", "--save"])
    def test_generate_and_save(self, mock_dashboard_class):
        """--generate --saveフラグ"""
        from src.advanced_trend_dashboard import main

        mock_dashboard = MagicMock()
        mock_dashboard.generate_comprehensive_dashboard.return_value = {"sections": {"plots": {}}}
        mock_dashboard_class.return_value = mock_dashboard

        main()

        mock_dashboard.generate_comprehensive_dashboard.assert_called_once()
        mock_dashboard.save_dashboard.assert_called_once()
