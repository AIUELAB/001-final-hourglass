"""
QualityGateChecker テストモジュール

quality_gate_checker.py の単体テストを提供します。
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.quality_gate_checker import QualityGateChecker


@pytest.fixture
def temp_report_dir(tmp_path: Path) -> Path:
    """テスト用のレポートディレクトリ"""
    report_dir = tmp_path / "reports"
    report_dir.mkdir(parents=True)
    return report_dir


@pytest.fixture
def checker(temp_report_dir: Path) -> QualityGateChecker:
    """テスト用のQualityGateCheckerインスタンス"""
    return QualityGateChecker(report_dir=temp_report_dir)


class TestQualityGateCheckerInit:
    """初期化テスト"""

    def test_init_with_custom_dir(self, temp_report_dir: Path) -> None:
        """カスタムディレクトリで初期化できる"""
        checker = QualityGateChecker(report_dir=temp_report_dir)
        assert checker.report_dir == temp_report_dir

    def test_init_creates_directory(self, tmp_path: Path) -> None:
        """存在しないディレクトリは自動作成される"""
        new_dir = tmp_path / "new_reports"
        assert not new_dir.exists()

        checker = QualityGateChecker(report_dir=new_dir)
        assert new_dir.exists()

    def test_init_with_default_dir(self) -> None:
        """デフォルトディレクトリで初期化できる"""
        with patch("src.quality_gate_checker.get_project_root") as mock_root:
            mock_root.return_value = Path("/mock/project")
            with patch.object(Path, "mkdir"):
                checker = QualityGateChecker()
                assert checker.report_dir == Path("/mock/project/reports")


class TestEvaluateKpis:
    """_evaluate_kpis メソッドのテスト"""

    def test_pass_status_with_ok_kpis(self, checker: QualityGateChecker) -> None:
        """全てのKPIがOKならPASSステータス"""
        kpis = [
            {"name": "meta_expression_rate", "value": 0.1, "status": "OK"},
            {"name": "placeholder_rate", "value": 0.2, "status": "OK"},
        ]
        status, violations = checker._evaluate_kpis(kpis)

        assert status == "PASS"
        assert violations == []

    def test_warning_status_with_warning_kpis(self, checker: QualityGateChecker) -> None:
        """WARNING KPIがあればWARNINGステータス"""
        kpis = [
            {"name": "meta_expression_rate", "value": 0.6, "status": "WARNING"},
            {"name": "placeholder_rate", "value": 0.2, "status": "OK"},
        ]
        status, violations = checker._evaluate_kpis(kpis)

        assert status == "WARNING"
        assert len(violations) == 1
        assert "WARNING" in violations[0]
        assert "meta_expression_rate" in violations[0]

    def test_critical_status_with_critical_kpis(self, checker: QualityGateChecker) -> None:
        """CRITICAL KPIがあればCRITICALステータス"""
        kpis = [
            {"name": "meta_expression_rate", "value": 1.5, "status": "CRITICAL"},
            {"name": "placeholder_rate", "value": 0.2, "status": "OK"},
        ]
        status, violations = checker._evaluate_kpis(kpis)

        assert status == "CRITICAL"
        assert len(violations) == 1
        assert "CRITICAL" in violations[0]

    def test_critical_trumps_warning(self, checker: QualityGateChecker) -> None:
        """CRITICALとWARNINGが混在する場合はCRITICALが優先"""
        kpis = [
            {"name": "meta_expression_rate", "value": 0.6, "status": "WARNING"},
            {"name": "placeholder_rate", "value": 1.5, "status": "CRITICAL"},
        ]
        status, violations = checker._evaluate_kpis(kpis)

        assert status == "CRITICAL"
        assert len(violations) == 2

    def test_empty_kpis_returns_pass(self, checker: QualityGateChecker) -> None:
        """KPIが空の場合はPASS"""
        status, violations = checker._evaluate_kpis([])

        assert status == "PASS"
        assert violations == []

    def test_kpi_with_missing_fields(self, checker: QualityGateChecker) -> None:
        """必須フィールドが欠けているKPIも処理できる"""
        kpis = [
            {"name": "test_kpi"},  # value, status がない
        ]
        status, violations = checker._evaluate_kpis(kpis)

        assert status == "PASS"  # status が "OK" として扱われる
        assert violations == []


class TestGetRollbackRecommendation:
    """get_rollback_recommendation メソッドのテスト"""

    def test_recommends_rollback_for_critical(self, checker: QualityGateChecker) -> None:
        """CRITICALステータスではロールバック推奨"""
        result = {"status": "CRITICAL", "kpis": {}, "violations": []}
        assert checker.get_rollback_recommendation(result) is True

    def test_no_rollback_for_warning(self, checker: QualityGateChecker) -> None:
        """WARNINGステータスではロールバック非推奨"""
        result = {"status": "WARNING", "kpis": {}, "violations": []}
        assert checker.get_rollback_recommendation(result) is False

    def test_no_rollback_for_pass(self, checker: QualityGateChecker) -> None:
        """PASSステータスではロールバック非推奨"""
        result = {"status": "PASS", "kpis": {}, "violations": []}
        assert checker.get_rollback_recommendation(result) is False

    def test_no_rollback_for_missing_status(self, checker: QualityGateChecker) -> None:
        """ステータスがない場合はロールバック非推奨"""
        result = {"kpis": {}, "violations": []}
        assert checker.get_rollback_recommendation(result) is False


class TestRunPostIntegrationCheck:
    """run_post_integration_check メソッドのテスト"""

    def test_timeout_returns_critical(self, checker: QualityGateChecker, tmp_path: Path) -> None:
        """タイムアウト時はCRITICALを返す"""
        import subprocess

        csv_path = tmp_path / "test.csv"
        csv_path.write_text("col1,col2\nval1,val2")

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=300)
            result = checker.run_post_integration_check(csv_path)

        assert result["status"] == "CRITICAL"
        assert "timed out" in result["error"]
        assert result["kpis"] == {}

    def test_exception_returns_critical(self, checker: QualityGateChecker, tmp_path: Path) -> None:
        """例外発生時はCRITICALを返す"""
        csv_path = tmp_path / "test.csv"
        csv_path.write_text("col1,col2\nval1,val2")

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = OSError("Command not found")
            result = checker.run_post_integration_check(csv_path)

        assert result["status"] == "CRITICAL"
        assert "error" in result["error"].lower()

    def test_missing_report_returns_critical(self, checker: QualityGateChecker, tmp_path: Path) -> None:
        """レポートが生成されない場合はCRITICALを返す"""
        csv_path = tmp_path / "test.csv"
        csv_path.write_text("col1,col2\nval1,val2")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            result = checker.run_post_integration_check(csv_path)

        assert result["status"] == "CRITICAL"
        assert "not generated" in result["error"]

    def test_invalid_json_returns_critical(self, checker: QualityGateChecker, tmp_path: Path) -> None:
        """無効なJSONレポートはCRITICALを返す"""
        csv_path = tmp_path / "test.csv"
        csv_path.write_text("col1,col2\nval1,val2")

        report_path = checker.report_dir / "epup_post_integration.json"
        report_path.write_text("invalid json{{{")

        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            result = checker.run_post_integration_check(csv_path)

        assert result["status"] == "CRITICAL"
        assert "Failed to read" in result["error"]

    def test_successful_check_with_pass(self, checker: QualityGateChecker, tmp_path: Path) -> None:
        """正常な品質チェック（PASS）"""
        csv_path = tmp_path / "test.csv"
        csv_path.write_text("col1,col2\nval1,val2")

        # レポートJSONを準備
        report_path = checker.report_dir / "epup_post_integration.json"
        report_data = {
            "kpis": [
                {"name": "meta_expression_rate", "value": 0.1, "status": "OK"},
                {"name": "placeholder_rate", "value": 0.2, "status": "OK"},
            ]
        }
        report_path.write_text(json.dumps(report_data))

        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            result = checker.run_post_integration_check(csv_path)

        assert result["status"] == "PASS"
        assert result["violations"] == []
        assert len(result["kpis"]) == 2
        assert result["report_path"] == report_path

    def test_successful_check_with_warning(self, checker: QualityGateChecker, tmp_path: Path) -> None:
        """正常な品質チェック（WARNING）"""
        csv_path = tmp_path / "test.csv"
        csv_path.write_text("col1,col2\nval1,val2")

        report_path = checker.report_dir / "epup_post_integration.json"
        report_data = {
            "kpis": [
                {"name": "meta_expression_rate", "value": 0.6, "status": "WARNING"},
            ]
        }
        report_path.write_text(json.dumps(report_data))

        mock_result = MagicMock()
        mock_result.returncode = 1  # WARNING でも exit code 1

        with patch("subprocess.run", return_value=mock_result):
            result = checker.run_post_integration_check(csv_path)

        assert result["status"] == "WARNING"
        assert len(result["violations"]) == 1

    def test_successful_check_with_critical(self, checker: QualityGateChecker, tmp_path: Path) -> None:
        """正常な品質チェック（CRITICAL）"""
        csv_path = tmp_path / "test.csv"
        csv_path.write_text("col1,col2\nval1,val2")

        report_path = checker.report_dir / "epup_post_integration.json"
        report_data = {
            "kpis": [
                {"name": "meta_expression_rate", "value": 1.5, "status": "CRITICAL"},
            ]
        }
        report_path.write_text(json.dumps(report_data))

        mock_result = MagicMock()
        mock_result.returncode = 1

        with patch("subprocess.run", return_value=mock_result):
            result = checker.run_post_integration_check(csv_path)

        assert result["status"] == "CRITICAL"
        assert len(result["violations"]) == 1

    def test_empty_kpis_list(self, checker: QualityGateChecker, tmp_path: Path) -> None:
        """KPIリストが空の場合"""
        csv_path = tmp_path / "test.csv"
        csv_path.write_text("col1,col2\nval1,val2")

        report_path = checker.report_dir / "epup_post_integration.json"
        report_data = {"kpis": []}
        report_path.write_text(json.dumps(report_data))

        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            result = checker.run_post_integration_check(csv_path)

        assert result["status"] == "PASS"
        assert result["kpis"] == {}


class TestThresholds:
    """閾値定義のテスト"""

    def test_warning_thresholds_defined(self) -> None:
        """WARNING閾値が定義されている"""
        assert hasattr(QualityGateChecker, "WARNING_THRESHOLDS")
        thresholds = QualityGateChecker.WARNING_THRESHOLDS

        assert "meta_expression_rate" in thresholds
        assert "placeholder_rate" in thresholds
        assert thresholds["meta_expression_rate"] == 0.5

    def test_critical_thresholds_defined(self) -> None:
        """CRITICAL閾値が定義されている"""
        assert hasattr(QualityGateChecker, "CRITICAL_THRESHOLDS")
        thresholds = QualityGateChecker.CRITICAL_THRESHOLDS

        assert "meta_expression_rate" in thresholds
        assert thresholds["meta_expression_rate"] == 1.0

    def test_critical_thresholds_higher_than_warning(self) -> None:
        """CRITICAL閾値はWARNING閾値より大きい"""
        warning = QualityGateChecker.WARNING_THRESHOLDS
        critical = QualityGateChecker.CRITICAL_THRESHOLDS

        for key in warning:
            if key in critical:
                assert critical[key] >= warning[key], f"{key}: {critical[key]} < {warning[key]}"
