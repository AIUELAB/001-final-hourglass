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

pytestmark = pytest.mark.skipif(
    not db_utils_available, reason="database_utils not available"
)


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

    @patch("src.ai_recommendation_system.get_connection")
    def test_init_default(self, mock_get_conn):
        """デフォルト初期化"""
        from src.ai_recommendation_system import AIRecommendationSystem

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        system = AIRecommendationSystem()

        assert system.db_path == "unified_quality.db"

    @patch("src.ai_recommendation_system.get_connection")
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
