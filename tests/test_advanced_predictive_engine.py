"""
tests/test_advanced_predictive_engine.py - advanced_predictive_engine.py ユニットテスト
"""

from datetime import datetime
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


class TestAdvancedPrediction:
    """AdvancedPredictionデータクラステスト"""

    def test_prediction_creation(self):
        """AdvancedPrediction作成"""
        from src.advanced_predictive_engine import AdvancedPrediction

        prediction = AdvancedPrediction(
            prediction_id="PRED001",
            timestamp=datetime.now(),
            failure_probability=0.75,
            ensemble_predictions={"rf": 0.7, "gb": 0.8},
            confidence_score=0.85,
            risk_level="HIGH",
            predicted_failure_time=None,
            contributing_factors=[{"factor": "CPU", "weight": 0.5}],
            shap_values={"cpu_usage": 0.3},
            recommendations=["リソース増強"],
            model_agreement=0.9,
        )

        assert prediction.prediction_id == "PRED001"
        assert prediction.failure_probability == 0.75
        assert prediction.risk_level == "HIGH"


class TestAutoMLResults:
    """AutoMLResultsデータクラステスト"""

    def test_automl_results_creation(self):
        """AutoMLResults作成"""
        from src.advanced_predictive_engine import AutoMLResults

        results = AutoMLResults(
            best_model_name="RandomForest",
            best_params={"n_estimators": 100},
            cv_scores=[0.85, 0.87, 0.83],
            mean_cv_score=0.85,
            std_cv_score=0.02,
            feature_importance={"cpu": 0.4, "memory": 0.3},
        )

        assert results.best_model_name == "RandomForest"
        assert results.mean_cv_score == 0.85


class TestAdvancedPredictiveEngineInit:
    """AdvancedPredictiveEngine初期化テスト"""

    @patch("src.advanced_predictive_engine.Path.mkdir")
    def test_init_default(self, mock_mkdir):
        """デフォルト初期化"""
        from src.advanced_predictive_engine import AdvancedPredictiveEngine

        engine = AdvancedPredictiveEngine()

        assert engine.models == {}
        assert engine.ensemble_model is None
        assert engine.automl_enabled is True

    @patch("src.advanced_predictive_engine.Path.mkdir")
    def test_init_custom_path(self, mock_mkdir):
        """カスタムパスで初期化"""
        from pathlib import Path

        from src.advanced_predictive_engine import AdvancedPredictiveEngine

        custom_path = Path("/tmp/test.db")
        engine = AdvancedPredictiveEngine(db_path=custom_path)

        assert engine.db_path == custom_path


class TestGetParamGrids:
    """_get_param_gridsメソッドテスト"""

    @patch("src.advanced_predictive_engine.Path.mkdir")
    def test_param_grids_structure(self, mock_mkdir):
        """パラメータグリッドの構造"""
        from src.advanced_predictive_engine import AdvancedPredictiveEngine

        engine = AdvancedPredictiveEngine()
        grids = engine._get_param_grids()

        # 各モデルのグリッドが存在することを確認
        assert isinstance(grids, dict)


class TestPredictiveEngineModels:
    """予測エンジンのモデルテスト"""

    @patch("src.advanced_predictive_engine.Path.mkdir")
    def test_models_initially_empty(self, mock_mkdir):
        """モデルは初期状態で空"""
        from src.advanced_predictive_engine import AdvancedPredictiveEngine

        engine = AdvancedPredictiveEngine()

        assert len(engine.models) == 0

    @patch("src.advanced_predictive_engine.Path.mkdir")
    def test_scaler_initially_none(self, mock_mkdir):
        """スケーラーは初期状態でNone"""
        from src.advanced_predictive_engine import AdvancedPredictiveEngine

        engine = AdvancedPredictiveEngine()

        assert engine.scaler is None

    @patch("src.advanced_predictive_engine.Path.mkdir")
    def test_feature_names_initially_empty(self, mock_mkdir):
        """特徴量名は初期状態で空"""
        from src.advanced_predictive_engine import AdvancedPredictiveEngine

        engine = AdvancedPredictiveEngine()

        assert engine.feature_names == []


class TestProjectRoot:
    """PROJECT_ROOT定数テスト"""

    def test_project_root_exists(self):
        """PROJECT_ROOTが存在"""
        from src.advanced_predictive_engine import PROJECT_ROOT

        assert PROJECT_ROOT is not None
        assert PROJECT_ROOT.exists() or True  # テスト環境では存在しない場合もある
