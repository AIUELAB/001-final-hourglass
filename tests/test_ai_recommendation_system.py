"""
tests/test_ai_recommendation_system.py - ai_recommendation_system.py ユニットテスト
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


class TestAIRecommendation:
    """AIRecommendationデータクラステスト"""

    def test_recommendation_creation(self):
        """AIRecommendation作成"""
        from src.ai_recommendation_system import AIRecommendation

        rec = AIRecommendation(
            recommendation_id="REC001",
            timestamp="2025-01-01T00:00:00",
            recommendation_type="capacity",
            action="scale_up",
            target_resource="CPU",
            priority="high",
            confidence_score=0.85,
            estimated_impact=0.7,
            estimated_savings=100.0,
            implementation_effort="medium",
            reasoning="CPU使用率が高い",
            supporting_data={"avg_cpu": 85.0},
            alternative_actions=["scale_out", "optimize"],
        )

        assert rec.recommendation_id == "REC001"
        assert rec.confidence_score == 0.85
        assert rec.action == "scale_up"


class TestRecommendationFeedback:
    """RecommendationFeedbackデータクラステスト"""

    def test_feedback_creation(self):
        """RecommendationFeedback作成"""
        from src.ai_recommendation_system import RecommendationFeedback

        feedback = RecommendationFeedback(
            recommendation_id="REC001",
            feedback_timestamp="2025-01-02T00:00:00",
            implemented=True,
            actual_impact=0.65,
            actual_savings=95.0,
            success_rating=0.9,
            notes="正常に実装完了",
        )

        assert feedback.implemented is True
        assert feedback.success_rating == 0.9


class TestModelPerformanceMetrics:
    """ModelPerformanceMetricsデータクラステスト"""

    def test_metrics_creation(self):
        """ModelPerformanceMetrics作成"""
        from src.ai_recommendation_system import ModelPerformanceMetrics

        metrics = ModelPerformanceMetrics(
            model_name="RandomForest",
            accuracy=0.92,
            precision=0.90,
            recall=0.88,
            f1_score=0.89,
            training_date="2025-01-01",
            sample_count=1000,
        )

        assert metrics.model_name == "RandomForest"
        assert metrics.accuracy == 0.92
        assert metrics.f1_score == 0.89


class TestAIRecommendationSystemInit:
    """AIRecommendationSystem初期化テスト"""

    @patch("src.ai_recommendation_system.recommender.get_connection")
    def test_init_default(self, mock_get_conn):
        """デフォルト初期化"""
        from src.ai_recommendation_system import AIRecommendationSystem

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        system = AIRecommendationSystem()

        assert system.db_path == "unified_quality.db"

    @patch("src.ai_recommendation_system.recommender.get_connection")
    def test_init_custom_path(self, mock_get_conn):
        """カスタムパスで初期化"""
        from src.ai_recommendation_system import AIRecommendationSystem

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        system = AIRecommendationSystem(db_path="custom.db")

        assert system.db_path == "custom.db"


class TestSklearnAvailability:
    """sklearn可用性テスト"""

    def test_sklearn_flag_exists(self):
        """SKLEARN_AVAILABLEフラグが存在"""
        from src.ai_recommendation_system import SKLEARN_AVAILABLE

        assert isinstance(SKLEARN_AVAILABLE, bool)


class TestRecommendationTypes:
    """推奨タイプテスト"""

    def test_valid_recommendation_types(self):
        """有効な推奨タイプ"""
        from src.ai_recommendation_system import AIRecommendation

        valid_types = ["capacity", "cost", "performance", "security"]

        for rec_type in valid_types:
            rec = AIRecommendation(
                recommendation_id="TEST",
                timestamp="2025-01-01",
                recommendation_type=rec_type,
                action="scale_up",
                target_resource="CPU",
                priority="high",
                confidence_score=0.8,
                estimated_impact=0.5,
                estimated_savings=50.0,
                implementation_effort="low",
                reasoning="Test",
                supporting_data={},
                alternative_actions=[],
            )
            assert rec.recommendation_type == rec_type


class TestActionTypes:
    """アクションタイプテスト"""

    def test_valid_action_types(self):
        """有効なアクションタイプ"""
        from src.ai_recommendation_system import AIRecommendation

        valid_actions = ["scale_up", "scale_down", "optimize", "maintain"]

        for action in valid_actions:
            rec = AIRecommendation(
                recommendation_id="TEST",
                timestamp="2025-01-01",
                recommendation_type="capacity",
                action=action,
                target_resource="CPU",
                priority="high",
                confidence_score=0.8,
                estimated_impact=0.5,
                estimated_savings=50.0,
                implementation_effort="low",
                reasoning="Test",
                supporting_data={},
                alternative_actions=[],
            )
            assert rec.action == action


class TestPriorityLevels:
    """優先度レベルテスト"""

    def test_valid_priority_levels(self):
        """有効な優先度レベル"""
        from src.ai_recommendation_system import AIRecommendation

        valid_priorities = ["critical", "high", "medium", "low"]

        for priority in valid_priorities:
            rec = AIRecommendation(
                recommendation_id="TEST",
                timestamp="2025-01-01",
                recommendation_type="capacity",
                action="scale_up",
                target_resource="CPU",
                priority=priority,
                confidence_score=0.8,
                estimated_impact=0.5,
                estimated_savings=50.0,
                implementation_effort="low",
                reasoning="Test",
                supporting_data={},
                alternative_actions=[],
            )
            assert rec.priority == priority


class TestInitDatabaseTables:
    """_init_database_tablesテスト"""

    @patch("src.ai_recommendation_system.recommender.Path.mkdir")
    @patch("src.ai_recommendation_system.recommender.get_connection")
    def test_creates_tables(self, mock_get_conn, mock_mkdir):
        """テーブル作成を確認"""
        from src.ai_recommendation_system import AIRecommendationSystem

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        AIRecommendationSystem()

        # 4つのCREATE TABLEが実行される
        assert mock_cursor.execute.call_count >= 4
        mock_conn.commit.assert_called()
        mock_conn.close.assert_called()


class TestLoadModels:
    """_load_modelsテスト"""

    @patch("src.ai_recommendation_system.recommender.SKLEARN_AVAILABLE", False)
    @patch("src.ai_recommendation_system.recommender.Path.mkdir")
    @patch("src.ai_recommendation_system.recommender.get_connection")
    def test_skip_when_sklearn_unavailable(self, mock_get_conn, mock_mkdir):
        """sklearn不可時はスキップ"""
        from src.ai_recommendation_system import AIRecommendationSystem

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        system = AIRecommendationSystem()

        assert system.recommendation_model is None
        assert system.priority_model is None
        assert system.scaler is None

    @patch("src.ai_recommendation_system.recommender.SKLEARN_AVAILABLE", True)
    @patch("src.ai_recommendation_system.recommender.Path.mkdir")
    @patch("src.ai_recommendation_system.recommender.get_connection")
    def test_handles_missing_model_files(self, mock_get_conn, mock_mkdir):
        """モデルファイル未存在時のハンドリング"""
        from src.ai_recommendation_system import AIRecommendationSystem

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        system = AIRecommendationSystem()

        # モデルファイルが存在しない場合はNone
        assert system.recommendation_model is None
        assert system.priority_model is None


class TestSaveModels:
    """_save_modelsテスト"""

    @patch("src.ai_recommendation_system.recommender.SKLEARN_AVAILABLE", False)
    @patch("src.ai_recommendation_system.recommender.Path.mkdir")
    @patch("src.ai_recommendation_system.recommender.get_connection")
    def test_skip_when_sklearn_unavailable(self, mock_get_conn, mock_mkdir):
        """sklearn不可時はスキップ"""
        from src.ai_recommendation_system import AIRecommendationSystem

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        system = AIRecommendationSystem()
        # エラーなく完了
        system._save_models()

    @patch("src.ai_recommendation_system.recommender.SKLEARN_AVAILABLE", True)
    @patch("src.ai_recommendation_system.recommender.joblib")
    @patch("src.ai_recommendation_system.recommender.Path.mkdir")
    @patch("src.ai_recommendation_system.recommender.get_connection")
    def test_saves_existing_models(self, mock_get_conn, mock_mkdir, mock_joblib):
        """存在するモデルを保存"""
        from src.ai_recommendation_system import AIRecommendationSystem

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        system = AIRecommendationSystem()
        system.recommendation_model = MagicMock()
        system.priority_model = MagicMock()
        system.scaler = MagicMock()

        system._save_models()

        # 3つのモデルが保存される
        assert mock_joblib.dump.call_count == 3


class TestCollectSystemFeatures:
    """collect_system_featuresテスト"""

    @patch("src.ai_recommendation_system.recommender.Path.mkdir")
    @patch("src.ai_recommendation_system.recommender.get_connection")
    def test_returns_none_when_no_metrics(self, mock_get_conn, mock_mkdir):
        """メトリクスがない場合はNone"""
        from src.ai_recommendation_system import AIRecommendationSystem

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        system = AIRecommendationSystem()
        mock_get_conn.reset_mock()
        mock_get_conn.return_value = mock_conn

        result = system.collect_system_features()

        assert result is None

    @patch("src.ai_recommendation_system.recommender.Path.mkdir")
    @patch("src.ai_recommendation_system.recommender.get_connection")
    def test_returns_features_when_data_exists(self, mock_get_conn, mock_mkdir):
        """データ存在時は特徴量を返す"""
        from src.ai_recommendation_system import AIRecommendationSystem

        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # 各クエリに対する戻り値を設定
        mock_cursor.fetchone.side_effect = [
            (75.0, 60.0, 50.0, 8.0, 100.0),  # system_metrics
            (0.3, 0.9),  # prediction
            (5,),  # quality_events
        ]
        mock_cursor.fetchall.side_effect = [
            [(0.5, 30)],  # capacity_forecasts
            [(20.0,)],  # resource_costs
        ]
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        system = AIRecommendationSystem()
        mock_get_conn.reset_mock()
        mock_get_conn.return_value = mock_conn
        mock_cursor.fetchone.side_effect = [
            (75.0, 60.0, 50.0, 8.0, 100.0),
            (0.3, 0.9),
            (5,),
        ]
        mock_cursor.fetchall.side_effect = [
            [(0.5, 30)],
            [(20.0,)],
        ]

        result = system.collect_system_features()

        assert result is not None
        assert result["cpu_usage"] == 75.0
        assert result["memory_usage"] == 60.0

    @patch("src.ai_recommendation_system.recommender.Path.mkdir")
    @patch("src.ai_recommendation_system.recommender.get_connection")
    def test_handles_missing_prediction_data(self, mock_get_conn, mock_mkdir):
        """予測データがない場合のデフォルト値"""
        from src.ai_recommendation_system import AIRecommendationSystem

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [
            (75.0, 60.0, 50.0, 8.0, 100.0),  # system_metrics
            None,  # prediction - なし
            (0,),  # quality_events
        ]
        mock_cursor.fetchall.side_effect = [
            [],  # capacity_forecasts - なし
            [],  # resource_costs - なし
        ]
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        system = AIRecommendationSystem()
        mock_get_conn.reset_mock()
        mock_get_conn.return_value = mock_conn
        mock_cursor.fetchone.side_effect = [
            (75.0, 60.0, 50.0, 8.0, 100.0),
            None,
            (0,),
        ]
        mock_cursor.fetchall.side_effect = [
            [],
            [],
        ]

        result = system.collect_system_features()

        assert result is not None
        assert result["failure_probability"] == 0.0
        assert result["model_agreement"] == 1.0
        assert result["avg_growth_rate"] == 0.0


class TestGenerateRuleBasedRecommendations:
    """_generate_rule_based_recommendationsテスト"""

    @patch("src.ai_recommendation_system.recommender.Path.mkdir")
    @patch("src.ai_recommendation_system.recommender.get_connection")
    def test_high_cpu_recommendation(self, mock_get_conn, mock_mkdir):
        """高CPU使用率で推奨生成"""
        from src.ai_recommendation_system import AIRecommendationSystem

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        system = AIRecommendationSystem()
        features = {"cpu_usage": 85.0}
        timestamp = "2025-01-01T00:00:00"

        recs = system._generate_rule_based_recommendations(features, timestamp)

        assert len(recs) == 1
        assert recs[0].recommendation_type == "performance"
        assert recs[0].target_resource == "CPU"
        assert recs[0].action == "scale_up"

    @patch("src.ai_recommendation_system.recommender.Path.mkdir")
    @patch("src.ai_recommendation_system.recommender.get_connection")
    def test_high_memory_recommendation(self, mock_get_conn, mock_mkdir):
        """高メモリ使用率で推奨生成"""
        from src.ai_recommendation_system import AIRecommendationSystem

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        system = AIRecommendationSystem()
        features = {"memory_usage": 90.0}
        timestamp = "2025-01-01T00:00:00"

        recs = system._generate_rule_based_recommendations(features, timestamp)

        assert len(recs) == 1
        assert recs[0].target_resource == "MEMORY"

    @patch("src.ai_recommendation_system.recommender.Path.mkdir")
    @patch("src.ai_recommendation_system.recommender.get_connection")
    def test_capacity_threshold_critical(self, mock_get_conn, mock_mkdir):
        """容量閾値接近（クリティカル）"""
        from src.ai_recommendation_system import AIRecommendationSystem

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        system = AIRecommendationSystem()
        features = {"min_days_until_threshold": 5}
        timestamp = "2025-01-01T00:00:00"

        recs = system._generate_rule_based_recommendations(features, timestamp)

        assert len(recs) == 1
        assert recs[0].priority == "critical"
        assert recs[0].target_resource == "STORAGE"

    @patch("src.ai_recommendation_system.recommender.Path.mkdir")
    @patch("src.ai_recommendation_system.recommender.get_connection")
    def test_capacity_threshold_high(self, mock_get_conn, mock_mkdir):
        """容量閾値接近（高）"""
        from src.ai_recommendation_system import AIRecommendationSystem

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        system = AIRecommendationSystem()
        features = {"min_days_until_threshold": 10}
        timestamp = "2025-01-01T00:00:00"

        recs = system._generate_rule_based_recommendations(features, timestamp)

        assert len(recs) == 1
        assert recs[0].priority == "high"

    @patch("src.ai_recommendation_system.recommender.Path.mkdir")
    @patch("src.ai_recommendation_system.recommender.get_connection")
    def test_high_waste_recommendation(self, mock_get_conn, mock_mkdir):
        """高無駄率で推奨生成"""
        from src.ai_recommendation_system import AIRecommendationSystem

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        system = AIRecommendationSystem()
        features = {"avg_waste_percentage": 60.0}
        timestamp = "2025-01-01T00:00:00"

        recs = system._generate_rule_based_recommendations(features, timestamp)

        assert len(recs) == 1
        assert recs[0].recommendation_type == "cost"
        assert recs[0].action == "optimize"
        assert recs[0].estimated_savings > 0

    @patch("src.ai_recommendation_system.recommender.Path.mkdir")
    @patch("src.ai_recommendation_system.recommender.get_connection")
    def test_high_failure_probability(self, mock_get_conn, mock_mkdir):
        """高障害確率で推奨生成"""
        from src.ai_recommendation_system import AIRecommendationSystem

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        system = AIRecommendationSystem()
        features = {"failure_probability": 0.7}
        timestamp = "2025-01-01T00:00:00"

        recs = system._generate_rule_based_recommendations(features, timestamp)

        assert len(recs) == 1
        assert recs[0].recommendation_type == "security"

    @patch("src.ai_recommendation_system.recommender.Path.mkdir")
    @patch("src.ai_recommendation_system.recommender.get_connection")
    def test_no_recommendations_normal_state(self, mock_get_conn, mock_mkdir):
        """正常状態では推奨なし"""
        from src.ai_recommendation_system import AIRecommendationSystem

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        system = AIRecommendationSystem()
        features = {
            "cpu_usage": 50.0,
            "memory_usage": 50.0,
            "min_days_until_threshold": 100,
            "avg_waste_percentage": 20.0,
            "failure_probability": 0.1,
        }
        timestamp = "2025-01-01T00:00:00"

        recs = system._generate_rule_based_recommendations(features, timestamp)

        assert len(recs) == 0

    @patch("src.ai_recommendation_system.recommender.Path.mkdir")
    @patch("src.ai_recommendation_system.recommender.get_connection")
    def test_multiple_recommendations(self, mock_get_conn, mock_mkdir):
        """複数の推奨生成"""
        from src.ai_recommendation_system import AIRecommendationSystem

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        system = AIRecommendationSystem()
        features = {
            "cpu_usage": 90.0,
            "memory_usage": 90.0,
            "min_days_until_threshold": 5,
            "avg_waste_percentage": 60.0,
            "failure_probability": 0.7,
        }
        timestamp = "2025-01-01T00:00:00"

        recs = system._generate_rule_based_recommendations(features, timestamp)

        assert len(recs) == 5


class TestPrepareFeatureVector:
    """_prepare_feature_vectorテスト"""

    @patch("src.ai_recommendation_system.recommender.Path.mkdir")
    @patch("src.ai_recommendation_system.recommender.get_connection")
    def test_creates_ordered_vector(self, mock_get_conn, mock_mkdir):
        """順序付きベクトル生成"""
        from src.ai_recommendation_system import AIRecommendationSystem

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        system = AIRecommendationSystem()
        features = {
            "cpu_usage": 75.0,
            "memory_usage": 60.0,
            "disk_usage": 50.0,
            "memory_used_gb": 8.0,
            "disk_used_gb": 100.0,
            "failure_probability": 0.3,
            "model_agreement": 0.9,
            "avg_growth_rate": 0.5,
            "min_days_until_threshold": 30,
            "avg_waste_percentage": 20.0,
            "recent_incidents": 5,
        }

        vector = system._prepare_feature_vector(features)

        assert len(vector) == 11
        assert vector[0] == 75.0  # cpu_usage
        assert vector[1] == 60.0  # memory_usage

    @patch("src.ai_recommendation_system.recommender.Path.mkdir")
    @patch("src.ai_recommendation_system.recommender.get_connection")
    def test_missing_features_default_zero(self, mock_get_conn, mock_mkdir):
        """欠損特徴量は0でデフォルト"""
        from src.ai_recommendation_system import AIRecommendationSystem

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        system = AIRecommendationSystem()
        features = {"cpu_usage": 75.0}

        vector = system._prepare_feature_vector(features)

        assert len(vector) == 11
        assert vector[0] == 75.0
        assert vector[1] == 0.0  # memory_usage - missing


class TestRankRecommendations:
    """_rank_recommendationsテスト"""

    @patch("src.ai_recommendation_system.recommender.Path.mkdir")
    @patch("src.ai_recommendation_system.recommender.get_connection")
    def test_ranks_by_priority_and_confidence(self, mock_get_conn, mock_mkdir):
        """優先度と信頼度でランク付け"""
        from src.ai_recommendation_system import AIRecommendation, AIRecommendationSystem

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        system = AIRecommendationSystem()

        recs = [
            AIRecommendation(
                recommendation_id="LOW",
                timestamp="2025-01-01",
                recommendation_type="cost",
                action="optimize",
                target_resource="ALL",
                priority="low",
                confidence_score=0.9,
                estimated_impact=0.5,
                estimated_savings=100.0,
                implementation_effort="low",
                reasoning="Low priority",
                supporting_data={},
                alternative_actions=[],
            ),
            AIRecommendation(
                recommendation_id="CRITICAL",
                timestamp="2025-01-01",
                recommendation_type="performance",
                action="scale_up",
                target_resource="CPU",
                priority="critical",
                confidence_score=0.9,
                estimated_impact=0.9,
                estimated_savings=0.0,
                implementation_effort="medium",
                reasoning="Critical priority",
                supporting_data={},
                alternative_actions=[],
            ),
            AIRecommendation(
                recommendation_id="HIGH",
                timestamp="2025-01-01",
                recommendation_type="capacity",
                action="scale_up",
                target_resource="STORAGE",
                priority="high",
                confidence_score=0.8,
                estimated_impact=0.7,
                estimated_savings=0.0,
                implementation_effort="low",
                reasoning="High priority",
                supporting_data={},
                alternative_actions=[],
            ),
        ]

        ranked = system._rank_recommendations(recs)

        assert ranked[0].recommendation_id == "CRITICAL"
        assert ranked[-1].recommendation_id == "LOW"


class TestSaveRecommendation:
    """_save_recommendationテスト"""

    @patch("src.ai_recommendation_system.recommender.Path.mkdir")
    @patch("src.ai_recommendation_system.recommender.get_connection")
    def test_saves_to_database(self, mock_get_conn, mock_mkdir):
        """データベースに保存"""
        from src.ai_recommendation_system import AIRecommendation, AIRecommendationSystem

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        system = AIRecommendationSystem()

        rec = AIRecommendation(
            recommendation_id="REC001",
            timestamp="2025-01-01T00:00:00",
            recommendation_type="capacity",
            action="scale_up",
            target_resource="CPU",
            priority="high",
            confidence_score=0.85,
            estimated_impact=0.7,
            estimated_savings=100.0,
            implementation_effort="medium",
            reasoning="Test",
            supporting_data={"test": 1},
            alternative_actions=["optimize"],
        )

        mock_get_conn.reset_mock()
        mock_get_conn.return_value = mock_conn

        system._save_recommendation(rec)

        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called()
        mock_conn.close.assert_called()

    @patch("src.ai_recommendation_system.recommender.Path.mkdir")
    @patch("src.ai_recommendation_system.recommender.get_connection")
    def test_handles_duplicate_recommendation(self, mock_get_conn, mock_mkdir):
        """重複推奨をハンドリング"""
        import sqlite3

        from src.ai_recommendation_system import AIRecommendation, AIRecommendationSystem

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        system = AIRecommendationSystem()

        rec = AIRecommendation(
            recommendation_id="REC001",
            timestamp="2025-01-01T00:00:00",
            recommendation_type="capacity",
            action="scale_up",
            target_resource="CPU",
            priority="high",
            confidence_score=0.85,
            estimated_impact=0.7,
            estimated_savings=100.0,
            implementation_effort="medium",
            reasoning="Test",
            supporting_data={},
            alternative_actions=[],
        )

        # _save_recommendation呼び出し時のみIntegrityErrorを発生
        mock_get_conn.reset_mock()
        mock_cursor_save = MagicMock()
        mock_cursor_save.execute.side_effect = sqlite3.IntegrityError("UNIQUE constraint")
        mock_conn_save = MagicMock()
        mock_conn_save.cursor.return_value = mock_cursor_save
        mock_get_conn.return_value = mock_conn_save

        # エラーなく完了
        system._save_recommendation(rec)
        mock_conn_save.close.assert_called()


class TestShowRecommendationsHistory:
    """show_recommendations_historyテスト"""

    @patch("src.ai_recommendation_system.recommender.Path.mkdir")
    @patch("src.ai_recommendation_system.recommender.get_connection")
    def test_shows_history(self, mock_get_conn, mock_mkdir, capsys):
        """履歴を表示"""
        from src.ai_recommendation_system import AIRecommendationSystem

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("REC001", "2025-01-01", "capacity", "scale_up", "CPU", "high", 0.85),
        ]
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        system = AIRecommendationSystem()
        mock_get_conn.reset_mock()
        mock_get_conn.return_value = mock_conn

        system.show_recommendations_history(limit=5)

        captured = capsys.readouterr()
        assert "AI推奨履歴" in captured.out
        assert "REC001" in captured.out

    @patch("src.ai_recommendation_system.recommender.Path.mkdir")
    @patch("src.ai_recommendation_system.recommender.get_connection")
    def test_shows_empty_message_when_no_history(self, mock_get_conn, mock_mkdir, capsys):
        """履歴がない場合のメッセージ"""
        from src.ai_recommendation_system import AIRecommendationSystem

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        system = AIRecommendationSystem()
        mock_get_conn.reset_mock()
        mock_get_conn.return_value = mock_conn

        system.show_recommendations_history()

        captured = capsys.readouterr()
        assert "AI推奨履歴がありません" in captured.out


class TestGenerateAIRecommendations:
    """generate_ai_recommendationsテスト"""

    @patch("src.ai_recommendation_system.recommender.Path.mkdir")
    @patch("src.ai_recommendation_system.recommender.get_connection")
    def test_returns_empty_when_no_features(self, mock_get_conn, mock_mkdir, capsys):
        """特徴量がない場合は空リスト"""
        from src.ai_recommendation_system import AIRecommendationSystem

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        system = AIRecommendationSystem()
        mock_get_conn.reset_mock()
        mock_get_conn.return_value = mock_conn

        result = system.generate_ai_recommendations()

        assert result == []
        captured = capsys.readouterr()
        assert "システムデータが不足" in captured.out

    @patch("src.ai_recommendation_system.recommender.Path.mkdir")
    @patch("src.ai_recommendation_system.recommender.get_connection")
    def test_generates_recommendations(self, mock_get_conn, mock_mkdir, capsys):
        """推奨を生成"""
        from src.ai_recommendation_system import AIRecommendationSystem

        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # collect_system_features用のモック
        mock_cursor.fetchone.side_effect = [
            (90.0, 90.0, 50.0, 8.0, 100.0),  # system_metrics - 高CPU/メモリ
            (0.3, 0.9),  # prediction
            (0,),  # quality_events
        ]
        mock_cursor.fetchall.side_effect = [
            [],  # capacity_forecasts
            [],  # resource_costs
        ]
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        system = AIRecommendationSystem()
        mock_get_conn.reset_mock()
        mock_get_conn.return_value = mock_conn
        mock_cursor.fetchone.side_effect = [
            (90.0, 90.0, 50.0, 8.0, 100.0),
            (0.3, 0.9),
            (0,),
        ]
        mock_cursor.fetchall.side_effect = [
            [],
            [],
        ]

        result = system.generate_ai_recommendations()

        assert len(result) >= 1
        captured = capsys.readouterr()
        assert "AI推奨生成完了" in captured.out


class TestGenerateMLRecommendations:
    """_generate_ml_recommendationsテスト"""

    @patch("src.ai_recommendation_system.recommender.SKLEARN_AVAILABLE", False)
    @patch("src.ai_recommendation_system.recommender.Path.mkdir")
    @patch("src.ai_recommendation_system.recommender.get_connection")
    def test_returns_empty_when_sklearn_unavailable(self, mock_get_conn, mock_mkdir):
        """sklearn不可時は空リスト"""
        from src.ai_recommendation_system import AIRecommendationSystem

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        system = AIRecommendationSystem()
        features = {"cpu_usage": 75.0}

        result = system._generate_ml_recommendations(features, "2025-01-01")

        assert result == []

    @patch("src.ai_recommendation_system.recommender.SKLEARN_AVAILABLE", True)
    @patch("src.ai_recommendation_system.recommender.Path.mkdir")
    @patch("src.ai_recommendation_system.recommender.get_connection")
    def test_returns_empty_when_no_model(self, mock_get_conn, mock_mkdir):
        """モデルがない場合は空リスト"""
        from src.ai_recommendation_system import AIRecommendationSystem

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        system = AIRecommendationSystem()
        system.recommendation_model = None
        features = {"cpu_usage": 75.0}

        result = system._generate_ml_recommendations(features, "2025-01-01")

        assert result == []

    @patch("src.ai_recommendation_system.recommender.SKLEARN_AVAILABLE", True)
    @patch("src.ai_recommendation_system.recommender.Path.mkdir")
    @patch("src.ai_recommendation_system.recommender.get_connection")
    def test_generates_ml_recommendation(self, mock_get_conn, mock_mkdir):
        """MLモデルで推奨生成"""
        import numpy as np

        from src.ai_recommendation_system import AIRecommendationSystem

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        system = AIRecommendationSystem()

        # モックモデルを設定
        mock_model = MagicMock()
        mock_model.predict.return_value = ["scale_up"]
        mock_model.predict_proba.return_value = np.array([[0.2, 0.8]])
        system.recommendation_model = mock_model

        mock_priority_model = MagicMock()
        mock_priority_model.predict.return_value = ["high"]
        system.priority_model = mock_priority_model

        mock_scaler = MagicMock()
        mock_scaler.transform.return_value = [[0.5] * 11]
        system.scaler = mock_scaler

        features = {
            "cpu_usage": 75.0,
            "memory_usage": 60.0,
            "disk_usage": 50.0,
        }

        result = system._generate_ml_recommendations(features, "2025-01-01T00:00:00")

        assert len(result) == 1
        assert result[0].recommendation_type == "ml_based"
        assert result[0].action == "scale_up"
        assert result[0].priority == "high"
        assert result[0].confidence_score == 0.8

    @patch("src.ai_recommendation_system.recommender.SKLEARN_AVAILABLE", True)
    @patch("src.ai_recommendation_system.recommender.Path.mkdir")
    @patch("src.ai_recommendation_system.recommender.get_connection")
    def test_handles_ml_error(self, mock_get_conn, mock_mkdir, capsys):
        """MLエラーをハンドリング"""
        from src.ai_recommendation_system import AIRecommendationSystem

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        system = AIRecommendationSystem()

        # エラーを発生させるモック
        mock_model = MagicMock()
        mock_model.predict.side_effect = Exception("Model error")
        system.recommendation_model = mock_model

        features = {"cpu_usage": 75.0}

        result = system._generate_ml_recommendations(features, "2025-01-01")

        assert result == []
        captured = capsys.readouterr()
        assert "ML推奨生成エラー" in captured.out


class TestMainFunction:
    """main関数テスト"""

    @patch("src.ai_recommendation_system.recommender.AIRecommendationSystem")
    @patch("src.ai_recommendation_system.recommender.argparse.ArgumentParser.parse_args")
    def test_generate_flag(self, mock_args, mock_system_class):
        """--generateフラグ"""
        from src.ai_recommendation_system import main

        mock_args.return_value = MagicMock(generate=True, history=False, save=False, limit=10)
        mock_system = MagicMock()
        mock_system.generate_ai_recommendations.return_value = []
        mock_system_class.return_value = mock_system

        main()

        mock_system.generate_ai_recommendations.assert_called_once()

    @patch("src.ai_recommendation_system.recommender.AIRecommendationSystem")
    @patch("src.ai_recommendation_system.recommender.argparse.ArgumentParser.parse_args")
    def test_history_flag(self, mock_args, mock_system_class):
        """--historyフラグ"""
        from src.ai_recommendation_system import main

        mock_args.return_value = MagicMock(generate=False, history=True, save=False, limit=20)
        mock_system = MagicMock()
        mock_system_class.return_value = mock_system

        main()

        mock_system.show_recommendations_history.assert_called_once_with(limit=20)

    @patch("src.ai_recommendation_system.recommender.Path.mkdir")
    @patch("src.ai_recommendation_system.recommender.AIRecommendationSystem")
    @patch("src.ai_recommendation_system.recommender.argparse.ArgumentParser.parse_args")
    def test_generate_and_save(self, mock_args, mock_system_class, mock_mkdir, tmp_path):
        """--generate --saveフラグ"""
        from dataclasses import asdict

        from src.ai_recommendation_system import AIRecommendation, main

        mock_args.return_value = MagicMock(generate=True, history=False, save=True, limit=10)

        rec = AIRecommendation(
            recommendation_id="REC001",
            timestamp="2025-01-01T00:00:00",
            recommendation_type="capacity",
            action="scale_up",
            target_resource="CPU",
            priority="high",
            confidence_score=0.85,
            estimated_impact=0.7,
            estimated_savings=100.0,
            implementation_effort="medium",
            reasoning="Test",
            supporting_data={},
            alternative_actions=[],
        )

        mock_system = MagicMock()
        mock_system.generate_ai_recommendations.return_value = [rec]
        mock_system_class.return_value = mock_system

        # ファイル保存をモック
        with patch("builtins.open", MagicMock()):
            with patch("src.ai_recommendation_system.recommender.json.dump"):
                main()

        mock_system.generate_ai_recommendations.assert_called_once()

    @patch("src.ai_recommendation_system.recommender.AIRecommendationSystem")
    @patch("src.ai_recommendation_system.recommender.argparse.ArgumentParser.parse_args")
    @patch("src.ai_recommendation_system.recommender.argparse.ArgumentParser.print_help")
    def test_no_args_shows_help(self, mock_help, mock_args, mock_system_class):
        """引数なしでヘルプ表示"""
        from src.ai_recommendation_system import main

        mock_args.return_value = MagicMock(generate=False, history=False, save=False, limit=10)
        mock_system = MagicMock()
        mock_system_class.return_value = mock_system

        main()

        mock_help.assert_called_once()


class TestSklearnImportFallback:
    """sklearn ImportError時のフォールバック変数テスト（L25-32）"""

    def test_sklearn_unavailable_flag(self):
        """SKLEARN_AVAILABLE=Falseの場合、フォールバック変数が設定される"""
        from src.ai_recommendation_system import recommender

        original = recommender.SKLEARN_AVAILABLE
        try:
            recommender.SKLEARN_AVAILABLE = False

            with patch("src.ai_recommendation_system.recommender.Path.mkdir"):
                with patch("src.ai_recommendation_system.recommender.get_connection") as mock_conn:
                    mock_conn.return_value = MagicMock()
                    system = recommender.AIRecommendationSystem()
                    assert system.recommendation_model is None
                    assert system.priority_model is None
                    assert system.scaler is None
        finally:
            recommender.SKLEARN_AVAILABLE = original

    def test_sklearn_import_error_sets_fallback_variables(self):
        """sklearn ImportError時にフォールバック変数がNoneに設定される（L25-32）

        subprocessで隔離環境を使い、sklearnのimportを失敗させてカバレッジを検証する。
        """
        import subprocess
        import sys

        # sklearnのimportを妨害するスクリプトをsubprocessで実行
        test_script = """
import sys
# sklearnとjoblibをimport不可にする
import builtins
_original_import = builtins.__import__
def _mock_import(name, *args, **kwargs):
    if name in ('joblib', 'sklearn', 'sklearn.ensemble', 'sklearn.model_selection', 'sklearn.preprocessing'):
        raise ImportError(f"Mocked ImportError for {name}")
    return _original_import(name, *args, **kwargs)
builtins.__import__ = _mock_import

# recommenderモジュールのimportでexcept ImportErrorパスが走る
from unittest.mock import MagicMock, patch
with patch("src.database_utils.get_connection", return_value=MagicMock()):
    with patch("pathlib.Path.mkdir"):
        from src.ai_recommendation_system import recommender
        assert recommender.SKLEARN_AVAILABLE is False, f"Expected False, got {recommender.SKLEARN_AVAILABLE}"
        assert recommender.np is None
        assert recommender.RandomForestClassifier is None
        assert recommender.GradientBoostingClassifier is None
        assert recommender.StandardScaler is None
        assert recommender.train_test_split is None
        assert recommender.joblib is None
        print("ALL_ASSERTIONS_PASSED")
"""
        result = subprocess.run(
            [sys.executable, "-c", test_script],
            capture_output=True,
            text=True,
            cwd="/Users/admin/Documents/AIUELAB/001-final-hourglass",
            timeout=30,
        )
        assert (
            "ALL_ASSERTIONS_PASSED" in result.stdout
        ), f"Subprocess failed.\nstdout: {result.stdout}\nstderr: {result.stderr}"

    def test_sklearn_not_available_save_models_noop(self):
        """SKLEARN_AVAILABLE=Falseの場合、_save_modelsは何もしない"""
        from src.ai_recommendation_system import recommender

        original = recommender.SKLEARN_AVAILABLE
        try:
            recommender.SKLEARN_AVAILABLE = False

            with patch("src.ai_recommendation_system.recommender.Path.mkdir"):
                with patch("src.ai_recommendation_system.recommender.get_connection") as mock_conn:
                    mock_conn.return_value = MagicMock()
                    system = recommender.AIRecommendationSystem()
                    # _save_modelsがNoop（早期リターン）
                    system._save_models()  # エラーが発生しない
        finally:
            recommender.SKLEARN_AVAILABLE = original


class TestSaveModelsPartialModels:
    """_save_models: 一部モデルのみ存在する場合のブランチテスト"""

    @patch("src.ai_recommendation_system.recommender.SKLEARN_AVAILABLE", True)
    @patch("src.ai_recommendation_system.recommender.joblib")
    @patch("src.ai_recommendation_system.recommender.Path.mkdir")
    @patch("src.ai_recommendation_system.recommender.get_connection")
    def test_save_only_recommendation_model(self, mock_get_conn, mock_mkdir, mock_joblib):
        """recommendation_modelのみ存在する場合"""
        from src.ai_recommendation_system import AIRecommendationSystem

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        system = AIRecommendationSystem()
        system.recommendation_model = MagicMock()
        system.priority_model = None  # なし
        system.scaler = None  # なし

        system._save_models()

        # joblib.dumpは1回のみ呼ばれる（recommendation_modelのみ）
        assert mock_joblib.dump.call_count == 1

    @patch("src.ai_recommendation_system.recommender.SKLEARN_AVAILABLE", True)
    @patch("src.ai_recommendation_system.recommender.joblib")
    @patch("src.ai_recommendation_system.recommender.Path.mkdir")
    @patch("src.ai_recommendation_system.recommender.get_connection")
    def test_save_no_models(self, mock_get_conn, mock_mkdir, mock_joblib):
        """全モデルがNoneの場合、joblib.dumpは呼ばれない"""
        from src.ai_recommendation_system import AIRecommendationSystem

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        system = AIRecommendationSystem()
        system.recommendation_model = None
        system.priority_model = None
        system.scaler = None

        system._save_models()

        mock_joblib.dump.assert_not_called()

    @patch("src.ai_recommendation_system.recommender.SKLEARN_AVAILABLE", True)
    @patch("src.ai_recommendation_system.recommender.joblib")
    @patch("src.ai_recommendation_system.recommender.Path.mkdir")
    @patch("src.ai_recommendation_system.recommender.get_connection")
    def test_save_priority_and_scaler_only(self, mock_get_conn, mock_mkdir, mock_joblib):
        """priority_modelとscalerのみ存在する場合"""
        from src.ai_recommendation_system import AIRecommendationSystem

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        system = AIRecommendationSystem()
        system.recommendation_model = None  # なし
        system.priority_model = MagicMock()
        system.scaler = MagicMock()

        system._save_models()

        # joblib.dumpは2回呼ばれる（priority_model + scaler）
        assert mock_joblib.dump.call_count == 2


class TestLoadModelsWithFiles:
    """_load_models: モデルファイルが存在する場合のテスト"""

    @patch("src.ai_recommendation_system.recommender.SKLEARN_AVAILABLE", True)
    @patch("src.ai_recommendation_system.recommender.joblib")
    @patch("src.ai_recommendation_system.recommender.Path.mkdir")
    @patch("src.ai_recommendation_system.recommender.get_connection")
    def test_loads_existing_model_files(self, mock_get_conn, mock_mkdir, mock_joblib):
        """既存モデルファイルをjoblib.loadでロード"""
        from src.ai_recommendation_system import AIRecommendationSystem

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        # Path.exists()をモックしてモデルファイルが存在するように見せる
        mock_rec_model = MagicMock(name="rec_model")
        mock_pri_model = MagicMock(name="pri_model")
        mock_scaler_obj = MagicMock(name="scaler")

        # joblib.loadの戻り値を設定（3回呼ばれる）
        mock_joblib.load.side_effect = [mock_rec_model, mock_pri_model, mock_scaler_obj]

        with patch("src.ai_recommendation_system.recommender.Path.exists", return_value=True):
            system = AIRecommendationSystem()

        # joblib.loadが3回呼ばれることを確認
        assert mock_joblib.load.call_count == 3
        assert system.recommendation_model == mock_rec_model
        assert system.priority_model == mock_pri_model
        assert system.scaler == mock_scaler_obj

    @patch("src.ai_recommendation_system.recommender.SKLEARN_AVAILABLE", True)
    @patch("src.ai_recommendation_system.recommender.joblib")
    @patch("src.ai_recommendation_system.recommender.Path.mkdir")
    @patch("src.ai_recommendation_system.recommender.get_connection")
    def test_handles_load_error(self, mock_get_conn, mock_mkdir, mock_joblib, capsys):
        """モデルロード時のエラーハンドリング"""
        from src.ai_recommendation_system import AIRecommendationSystem

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        mock_joblib.load.side_effect = Exception("Corrupt model file")

        with patch("src.ai_recommendation_system.recommender.Path.exists", return_value=True):
            system = AIRecommendationSystem()

        captured = capsys.readouterr()
        assert "モデルロード失敗" in captured.out


class TestSaveModelsError:
    """_save_models: エラーハンドリングテスト"""

    @patch("src.ai_recommendation_system.recommender.SKLEARN_AVAILABLE", True)
    @patch("src.ai_recommendation_system.recommender.joblib")
    @patch("src.ai_recommendation_system.recommender.Path.mkdir")
    @patch("src.ai_recommendation_system.recommender.get_connection")
    def test_handles_save_error(self, mock_get_conn, mock_mkdir, mock_joblib, capsys):
        """joblib.dump例外時にエラーメッセージ出力"""
        from src.ai_recommendation_system import AIRecommendationSystem

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        system = AIRecommendationSystem()
        system.recommendation_model = MagicMock()
        system.priority_model = MagicMock()
        system.scaler = MagicMock()

        # joblib.dumpで例外発生
        mock_joblib.dump.side_effect = OSError("Disk full")

        system._save_models()

        captured = capsys.readouterr()
        assert "モデル保存失敗" in captured.out


class TestMLRecommendationNoPriorityModel:
    """_generate_ml_recommendations: priority_modelがない場合のテスト"""

    @patch("src.ai_recommendation_system.recommender.SKLEARN_AVAILABLE", True)
    @patch("src.ai_recommendation_system.recommender.Path.mkdir")
    @patch("src.ai_recommendation_system.recommender.get_connection")
    def test_defaults_to_medium_priority(self, mock_get_conn, mock_mkdir):
        """priority_modelがNoneの場合、priorityは'medium'になる"""
        import numpy as np

        from src.ai_recommendation_system import AIRecommendationSystem

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        system = AIRecommendationSystem()

        # recommendation_modelはあるがpriority_modelはない
        mock_model = MagicMock()
        mock_model.predict.return_value = ["optimize"]
        mock_model.predict_proba.return_value = np.array([[0.1, 0.9]])
        system.recommendation_model = mock_model
        system.priority_model = None
        system.scaler = None

        features = {"cpu_usage": 75.0, "memory_usage": 60.0}

        result = system._generate_ml_recommendations(features, "2025-01-01T00:00:00")

        assert len(result) == 1
        assert result[0].priority == "medium"
        assert result[0].action == "optimize"


class TestGenerateAIWithML:
    """generate_ai_recommendations: MLパス統合テスト"""

    @patch("src.ai_recommendation_system.recommender.SKLEARN_AVAILABLE", True)
    @patch("src.ai_recommendation_system.recommender.Path.mkdir")
    @patch("src.ai_recommendation_system.recommender.get_connection")
    def test_generates_with_ml_model(self, mock_get_conn, mock_mkdir, capsys):
        """MLモデルが有効な場合、ml_recsが統合される"""
        import numpy as np

        from src.ai_recommendation_system import AIRecommendationSystem

        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # collect_system_features用のモック
        mock_cursor.fetchone.side_effect = [
            (90.0, 90.0, 50.0, 8.0, 100.0),  # system_metrics
            (0.3, 0.9),  # prediction
            (0,),  # quality_events
        ]
        mock_cursor.fetchall.side_effect = [
            [],  # capacity_forecasts
            [],  # resource_costs
        ]
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        system = AIRecommendationSystem()

        # MLモデルを設定
        mock_model = MagicMock()
        mock_model.predict.return_value = ["scale_down"]
        mock_model.predict_proba.return_value = np.array([[0.15, 0.85]])
        system.recommendation_model = mock_model

        mock_priority_model = MagicMock()
        mock_priority_model.predict.return_value = ["high"]
        system.priority_model = mock_priority_model

        mock_scaler = MagicMock()
        mock_scaler.transform.return_value = [[0.5] * 11]
        system.scaler = mock_scaler

        # generate_ai_recommendations呼び出し用にmockをリセット
        mock_get_conn.reset_mock()
        mock_get_conn.return_value = mock_conn
        mock_cursor.fetchone.side_effect = [
            (90.0, 90.0, 50.0, 8.0, 100.0),
            (0.3, 0.9),
            (0,),
        ]
        mock_cursor.fetchall.side_effect = [
            [],
            [],
        ]

        result = system.generate_ai_recommendations()

        # ルールベース推奨(CPU + メモリ) + ML推奨(1件) が含まれる
        assert len(result) >= 3

        # ML推奨が含まれていることを確認
        ml_recs = [r for r in result if r.recommendation_type == "ml_based"]
        assert len(ml_recs) == 1
        assert ml_recs[0].action == "scale_down"

        captured = capsys.readouterr()
        assert "ML推奨" in captured.out
        assert "AI推奨生成完了" in captured.out
