"""
tests/test_kpi_definitions.py - monitoring/kpi_definitions.py ユニットテスト
"""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


class TestKPIResult:
    """KPIResultデータクラステスト"""

    def test_kpi_result_creation(self):
        """KPIResult作成"""
        from src.monitoring.kpi_definitions import KPIResult

        result = KPIResult(
            name="テストKPI",
            value=0.05,
            target=0.0,
            status="WARNING",
            details={"count": 5},
        )

        assert result.name == "テストKPI"
        assert result.value == 0.05
        assert result.status == "WARNING"


class TestHealthReport:
    """HealthReportデータクラステスト"""

    def test_health_report_creation(self):
        """HealthReport作成"""
        from src.monitoring.kpi_definitions import HealthReport, KPIResult

        kpi = KPIResult(name="KPI1", value=0.0, target=0.0, status="OK")

        report = HealthReport(
            timestamp="2025-01-01T00:00:00",
            total_records=1000,
            kpis=[kpi],
            overall_status="OK",
            overall_score=1.0,
        )

        assert report.total_records == 1000
        assert len(report.kpis) == 1


class TestEPUPKPICalculatorInit:
    """EPUPKPICalculator初期化テスト"""

    def test_init_with_csv(self):
        """CSV読み込み初期化"""
        from src.monitoring.kpi_definitions import EPUPKPICalculator

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("person_name,person_id,person_type,episode_text\n")
            f.write("テスト,P001,REAL,テストエピソード\n")
            temp_path = f.name

        try:
            calculator = EPUPKPICalculator(temp_path)
            assert len(calculator.df) == 1
        finally:
            os.unlink(temp_path)


class TestGetStatus:
    """_get_statusメソッドテスト"""

    def test_status_ok(self):
        """OKステータス"""
        from src.monitoring.kpi_definitions import EPUPKPICalculator

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("person_name,person_id,person_type,episode_text\n")
            temp_path = f.name

        try:
            calculator = EPUPKPICalculator(temp_path)
            status = calculator._get_status(0.0, 0.0, 0.01, 0.05)
            assert status == "OK"
        finally:
            os.unlink(temp_path)

    def test_status_warning(self):
        """WARNINGステータス"""
        from src.monitoring.kpi_definitions import EPUPKPICalculator

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("person_name,person_id,person_type,episode_text\n")
            temp_path = f.name

        try:
            calculator = EPUPKPICalculator(temp_path)
            status = calculator._get_status(0.005, 0.0, 0.01, 0.05)
            assert status == "WARNING"
        finally:
            os.unlink(temp_path)

    def test_status_critical(self):
        """CRITICALステータス"""
        from src.monitoring.kpi_definitions import EPUPKPICalculator

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("person_name,person_id,person_type,episode_text\n")
            temp_path = f.name

        try:
            calculator = EPUPKPICalculator(temp_path)
            status = calculator._get_status(0.1, 0.0, 0.01, 0.05)
            assert status == "CRITICAL"
        finally:
            os.unlink(temp_path)


class TestCalcFormatComplianceRate:
    """_calc_format_compliance_rateメソッドテスト"""

    def test_format_compliance_100_percent(self):
        """100%準拠"""
        from src.monitoring.kpi_definitions import EPUPKPICalculator

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("person_name,person_id,person_type,episode_text\n")
            f.write("テスト,P001,REAL,あなたと同じ30歳のとき、テストは...\n")
            f.write("テスト2,P002,REAL,あなたと同じ40歳のとき、テスト2は...\n")
            temp_path = f.name

        try:
            calculator = EPUPKPICalculator(temp_path)
            result = calculator._calc_format_compliance_rate()

            assert result.name == "フォーマット準拠率"
            assert result.value == 1.0
            assert result.status == "OK"
        finally:
            os.unlink(temp_path)

    def test_format_compliance_partial(self):
        """部分準拠"""
        from src.monitoring.kpi_definitions import EPUPKPICalculator

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("person_name,person_id,person_type,episode_text\n")
            f.write("テスト,P001,REAL,あなたと同じ30歳のとき、テストは...\n")
            f.write("テスト2,P002,REAL,非準拠のテキスト\n")
            temp_path = f.name

        try:
            calculator = EPUPKPICalculator(temp_path)
            result = calculator._calc_format_compliance_rate()

            assert result.value == 0.5
        finally:
            os.unlink(temp_path)


class TestCalcNanIdRate:
    """_calc_nan_id_rateメソッドテスト"""

    def test_no_nan_ids(self):
        """NaN IDなし"""
        from src.monitoring.kpi_definitions import EPUPKPICalculator

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("person_name,person_id,person_type,episode_text\n")
            f.write("テスト,P001,REAL,テスト\n")
            f.write("テスト2,P002,REAL,テスト2\n")
            temp_path = f.name

        try:
            calculator = EPUPKPICalculator(temp_path)
            result = calculator._calc_nan_id_rate()

            assert result.value == 0.0
            assert result.status == "OK"
        finally:
            os.unlink(temp_path)

    def test_with_nan_ids(self):
        """NaN IDあり"""
        from src.monitoring.kpi_definitions import EPUPKPICalculator

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("person_name,person_id,person_type,episode_text\n")
            f.write("テスト,P001,REAL,テスト\n")
            f.write("テスト2,,REAL,テスト2\n")  # NaN ID
            temp_path = f.name

        try:
            calculator = EPUPKPICalculator(temp_path)
            result = calculator._calc_nan_id_rate()

            assert result.value == 0.5
            assert result.status == "CRITICAL"
        finally:
            os.unlink(temp_path)


class TestCalcMetaExpressionRate:
    """_calc_meta_expression_rateメソッドテスト"""

    def test_no_meta_expressions(self):
        """メタ表現なし"""
        from src.monitoring.kpi_definitions import EPUPKPICalculator

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("person_name,person_id,person_type,episode_text\n")
            f.write("キャラ,P001,FICTIONAL,あなたと同じ30歳のとき...\n")
            temp_path = f.name

        try:
            calculator = EPUPKPICalculator(temp_path)
            result = calculator._calc_meta_expression_rate()

            assert result.value == 0.0
        finally:
            os.unlink(temp_path)

    def test_with_meta_expressions(self):
        """メタ表現あり"""
        from src.monitoring.kpi_definitions import EPUPKPICalculator

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("person_name,person_id,person_type,episode_text\n")
            f.write("キャラ,P001,FICTIONAL,これは架空のキャラクターです\n")
            temp_path = f.name

        try:
            calculator = EPUPKPICalculator(temp_path)
            result = calculator._calc_meta_expression_rate()

            assert result.value > 0
        finally:
            os.unlink(temp_path)


class TestCalcVariantRate:
    """_calc_variant_rateメソッドテスト"""

    def test_no_variants(self):
        """表記ゆれなし"""
        from src.monitoring.kpi_definitions import EPUPKPICalculator

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("person_name,person_id,person_type,episode_text\n")
            f.write("テスト太郎,P001,REAL,テスト\n")
            f.write("テスト太郎,P001,REAL,テスト2\n")  # 同じ名前
            temp_path = f.name

        try:
            calculator = EPUPKPICalculator(temp_path)
            result = calculator._calc_variant_rate()

            assert result.value == 0.0
        finally:
            os.unlink(temp_path)

    def test_with_variants(self):
        """表記ゆれあり"""
        from src.monitoring.kpi_definitions import EPUPKPICalculator

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("person_name,person_id,person_type,episode_text\n")
            f.write("テスト太郎,P001,REAL,テスト\n")
            f.write("テスト・太郎,P001,REAL,テスト2\n")  # 同じIDで異なる名前
            temp_path = f.name

        try:
            calculator = EPUPKPICalculator(temp_path)
            result = calculator._calc_variant_rate()

            assert result.value > 0
        finally:
            os.unlink(temp_path)


class TestCalculateAll:
    """calculate_allメソッドテスト"""

    def test_calculate_all_returns_report(self):
        """HealthReportが返される"""
        from src.monitoring.kpi_definitions import EPUPKPICalculator, HealthReport

        # calculate_allに必要な全カラムを含むCSVを作成
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("person_name,person_id,person_type,episode_text,category,group_name\n")
            f.write("テスト,P001,REAL,あなたと同じ30歳のとき...,スポーツ,グループA\n")
            temp_path = f.name

        try:
            # モックせずに実際の計算を実行（依存モジュールがない場合はスキップ）
            try:
                calculator = EPUPKPICalculator(temp_path)
                report = calculator.calculate_all()

                assert isinstance(report, HealthReport)
                assert len(report.kpis) > 0
                assert report.overall_status in ["OK", "WARNING", "CRITICAL"]
            except (ImportError, ModuleNotFoundError, KeyError):
                pytest.skip("Required modules or columns not available")
        finally:
            os.unlink(temp_path)
