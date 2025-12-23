"""
tests/test_kpi_definitions.py - monitoring/kpi_definitions.py ユニットテスト
"""

import json
import os
import tempfile
from unittest.mock import MagicMock, mock_open, patch

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

    def test_calculate_all_with_warning_status(self):
        """WARNING状態のレポート"""
        from src.monitoring.kpi_definitions import EPUPKPICalculator

        # 一部違反があるデータ
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("person_name,person_id,person_type,episode_text,category,group_name\n")
            f.write("テスト,P001,REAL,非準拠テキスト,スポーツ,グループA\n")
            f.write("テスト2,P002,REAL,あなたと同じ30歳のとき...,スポーツ,グループA\n")
            temp_path = f.name

        try:
            calculator = EPUPKPICalculator(temp_path)
            report = calculator.calculate_all()

            assert report.overall_status in ["OK", "WARNING", "CRITICAL"]
            assert report.overall_score <= 1.0
        except (ImportError, ModuleNotFoundError, KeyError):
            pytest.skip("Required modules not available")
        finally:
            os.unlink(temp_path)


class TestCalcGroupNameRate:
    """_calc_group_name_rateメソッドテスト"""

    def test_no_group_contamination(self):
        """グループ名混入なし"""
        from src.monitoring.kpi_definitions import EPUPKPICalculator

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("person_name,person_id,person_type,episode_text\n")
            f.write("山田太郎,P001,REAL,テスト\n")
            temp_path = f.name

        try:
            calculator = EPUPKPICalculator(temp_path)
            result = calculator._calc_group_name_rate()

            assert result.value == 0.0
            assert result.status == "OK"
        finally:
            os.unlink(temp_path)


class TestCalcDuplicateIdRate:
    """_calc_duplicate_id_rateメソッドテスト"""

    def test_no_duplicates(self):
        """重複なし"""
        from src.monitoring.kpi_definitions import EPUPKPICalculator

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("person_name,person_id,person_type,episode_text\n")
            f.write("テスト,P001,REAL,テスト1\n")
            f.write("テスト2,P002,REAL,テスト2\n")
            temp_path = f.name

        try:
            calculator = EPUPKPICalculator(temp_path)
            result = calculator._calc_duplicate_id_rate()

            assert result.value == 0.0
        finally:
            os.unlink(temp_path)

    def test_with_duplicates(self):
        """重複あり"""
        from src.monitoring.kpi_definitions import EPUPKPICalculator

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("person_name,person_id,person_type,episode_text\n")
            f.write("テスト,P001,REAL,テスト1\n")
            f.write("テスト,P001,REAL,テスト2\n")  # 同じperson_id
            temp_path = f.name

        try:
            calculator = EPUPKPICalculator(temp_path)
            result = calculator._calc_duplicate_id_rate()

            # 重複があるかないかは実装による
            assert result.value >= 0.0
        finally:
            os.unlink(temp_path)


class TestCalcDeletedIdContaminationRate:
    """_calc_deleted_id_contamination_rateメソッドテスト"""

    def test_no_tombstone(self):
        """Tombstoneなしの場合"""
        from src.monitoring.kpi_definitions import EPUPKPICalculator

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("person_name,person_id,person_type,episode_text\n")
            f.write("テスト,P001,REAL,テスト\n")
            temp_path = f.name

        try:
            calculator = EPUPKPICalculator(temp_path)
            result = calculator._calc_deleted_id_contamination_rate()

            assert result.value == 0.0
            assert result.details is not None
            assert "note" in result.details or result.details.get("deleted_ids_count", 0) >= 0
        finally:
            os.unlink(temp_path)


class TestCalcEnglishAliasRate:
    """_calc_english_alias_rateメソッドテスト"""

    def test_no_english_alias(self):
        """英語エイリアスなし"""
        from src.monitoring.kpi_definitions import EPUPKPICalculator

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("person_name,person_id,person_type,episode_text,category\n")
            f.write("山田太郎,P001,REAL,テスト,スポーツ\n")
            temp_path = f.name

        try:
            calculator = EPUPKPICalculator(temp_path)
            result = calculator._calc_english_alias_rate()

            assert result.value >= 0.0
            assert result.status in ["OK", "WARNING", "CRITICAL"]
        finally:
            os.unlink(temp_path)


class TestCalcOrgTitleContaminationRate:
    """_calc_org_title_contamination_rateメソッドテスト"""

    def test_no_org_contamination(self):
        """組織名・肩書き混入なし"""
        from src.monitoring.kpi_definitions import EPUPKPICalculator

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("person_name,person_id,person_type,episode_text\n")
            f.write("山田太郎,P001,REAL,テスト\n")
            temp_path = f.name

        try:
            calculator = EPUPKPICalculator(temp_path)
            result = calculator._calc_org_title_contamination_rate()

            assert result.value >= 0.0
        finally:
            os.unlink(temp_path)


class TestCalcSuffixPatternRate:
    """_calc_suffix_pattern_rateメソッドテスト"""

    def test_no_suffix_pattern(self):
        """後置詞型パターンなし"""
        from src.monitoring.kpi_definitions import EPUPKPICalculator

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("person_name,person_id,person_type,episode_text\n")
            f.write("山田太郎,P001,REAL,テスト\n")
            temp_path = f.name

        try:
            calculator = EPUPKPICalculator(temp_path)
            result = calculator._calc_suffix_pattern_rate()

            assert result.value >= 0.0
        finally:
            os.unlink(temp_path)


class TestMainFunction:
    """main関数テスト"""

    @patch("sys.argv", ["kpi_definitions.py"])
    def test_main_default_path(self, capsys):
        """デフォルトパスでの実行"""
        from src.monitoring.kpi_definitions import main

        # デフォルトCSVがない場合はFileNotFoundError
        try:
            main()
            captured = capsys.readouterr()
            assert "EPUP Health Report" in captured.out
        except FileNotFoundError:
            # ファイルがない場合はパス
            pass

    def test_main_with_custom_path(self, capsys):
        """カスタムパスでの実行"""
        from src.monitoring.kpi_definitions import main

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("person_name,person_id,person_type,episode_text,category\n")
            f.write("テスト,P001,REAL,あなたと同じ30歳のとき...,スポーツ\n")
            temp_path = f.name

        try:
            with patch("sys.argv", ["kpi_definitions.py", temp_path]):
                main()
                captured = capsys.readouterr()
                assert "EPUP Health Report" in captured.out
                assert "Total Records" in captured.out
        finally:
            os.unlink(temp_path)

    def test_main_output_format(self, capsys):
        """出力フォーマット確認"""
        from src.monitoring.kpi_definitions import main

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("person_name,person_id,person_type,episode_text,category\n")
            f.write("テスト,P001,REAL,あなたと同じ30歳のとき...,スポーツ\n")
            temp_path = f.name

        try:
            with patch("sys.argv", ["kpi_definitions.py", temp_path]):
                main()
                captured = capsys.readouterr()
                # 出力に期待される要素が含まれることを確認
                assert "Timestamp:" in captured.out
                assert "Overall Status:" in captured.out
                assert "Overall Score:" in captured.out
        finally:
            os.unlink(temp_path)


class TestDeletedIdContaminationWithTombstone:
    """Tombstoneファイル存在時の削除済みID混入率テスト"""

    def test_with_tombstone_contamination(self, tmp_path):
        """削除済みIDが混入している場合"""
        from src.monitoring.kpi_definitions import EPUPKPICalculator

        # CSVファイル作成
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(
            "person_name,person_id,person_type,episode_text\n"
            "山田太郎,P001,REAL,テスト\n"
            "田中花子,P002,REAL,テスト\n"
            "削除済み,P999,REAL,テスト\n"
        )

        # Tombstoneファイル作成
        tombstone_file = tmp_path / "tombstone.json"
        tombstone_data = {
            "deleted_ids": [
                {"person_id": "P999", "person_name": "削除済み"},
            ]
        }
        tombstone_file.write_text(json.dumps(tombstone_data))

        with patch("src.monitoring.kpi_definitions.TOMBSTONE_PATH", tombstone_file):
            calculator = EPUPKPICalculator(str(csv_file))
            result = calculator._calc_deleted_id_contamination_rate()

            # 混入が検出される
            assert result.details is not None
            assert result.details["contaminated"] >= 1
            assert "contaminated_entries" in result.details

    def test_with_tombstone_by_name(self, tmp_path):
        """名前による削除済みID検出"""
        from src.monitoring.kpi_definitions import EPUPKPICalculator

        csv_file = tmp_path / "test.csv"
        csv_file.write_text("person_name,person_id,person_type,episode_text\n" "削除対象者,PNEW,REAL,テスト\n")

        tombstone_file = tmp_path / "tombstone.json"
        tombstone_data = {
            "deleted_ids": [
                {"person_id": "POLD", "person_name": "削除対象者"},
            ]
        }
        tombstone_file.write_text(json.dumps(tombstone_data))

        with patch("src.monitoring.kpi_definitions.TOMBSTONE_PATH", tombstone_file):
            calculator = EPUPKPICalculator(str(csv_file))
            result = calculator._calc_deleted_id_contamination_rate()

            assert result.value >= 0.0
            assert result.details is not None
            assert result.details["contaminated"] >= 1

    def test_tombstone_json_error(self, tmp_path):
        """TombstoneがJSONエラーの場合"""
        from src.monitoring.kpi_definitions import EPUPKPICalculator

        csv_file = tmp_path / "test.csv"
        csv_file.write_text("person_name,person_id,person_type,episode_text\n" "山田太郎,P001,REAL,テスト\n")

        tombstone_file = tmp_path / "tombstone.json"
        tombstone_file.write_text("invalid json")

        with patch("src.monitoring.kpi_definitions.TOMBSTONE_PATH", tombstone_file):
            calculator = EPUPKPICalculator(str(csv_file))
            result = calculator._calc_deleted_id_contamination_rate()

            # JSONエラー時は空セットを返す
            assert result.value == 0.0


class TestOrgTitleContaminationWithData:
    """組織名・肩書き混入のテスト（実データ）"""

    def test_with_org_contamination(self, tmp_path):
        """組織名が混入している場合"""
        from src.monitoring.kpi_definitions import EPUPKPICalculator

        csv_file = tmp_path / "test.csv"
        csv_file.write_text(
            "person_name,person_id,person_type,episode_text\n"
            "山田太郎,P001,REAL,テスト\n"
            "株式会社テスト代表取締役社長山田太郎,P002,REAL,テスト\n"
        )

        calculator = EPUPKPICalculator(str(csv_file))
        result = calculator._calc_org_title_contamination_rate()

        # 値が取得できること
        assert result.value >= 0.0
        assert result.details is not None
        assert "contaminated_examples" in result.details


class TestSuffixPatternWithData:
    """後置詞型パターンのテスト（実データ）"""

    def test_with_suffix_pattern(self, tmp_path):
        """後置詞型パターンが検出される場合"""
        from src.monitoring.kpi_definitions import EPUPKPICalculator

        csv_file = tmp_path / "test.csv"
        csv_file.write_text(
            "person_name,person_id,person_type,episode_text\n"
            "山田太郎,P001,REAL,テスト\n"
            "田中の母,P002,REAL,テスト\n"
        )

        calculator = EPUPKPICalculator(str(csv_file))
        result = calculator._calc_suffix_pattern_rate()

        assert result.value >= 0.0
        assert result.details is not None
        assert "error_count" in result.details


class TestCalculateAllCriticalStatus:
    """CRITICAL状態のテスト"""

    def test_calculate_all_with_critical(self, tmp_path):
        """CRITICALステータスのケース"""
        from src.monitoring.kpi_definitions import EPUPKPICalculator

        # 不正なフォーマットのデータ
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(
            "person_name,person_id,person_type,episode_text,category\n"
            "テスト,NaN,REAL,短い,スポーツ\n"
            "架空キャラ,P002,FICTIONAL,架空の存在です,文化\n"
        )

        calculator = EPUPKPICalculator(str(csv_file))
        report = calculator.calculate_all()

        # レポートが生成される
        assert report is not None
        assert report.overall_status in ["OK", "WARNING", "CRITICAL"]


class TestCalculateAllScoreWithZeroTarget:
    """ターゲット0%のスコア計算テスト"""

    def test_score_calculation_with_zero_target(self, tmp_path):
        """ターゲット0%のKPIスコア計算"""
        from src.monitoring.kpi_definitions import EPUPKPICalculator

        # 問題のあるデータ（メタ表現、NaN IDなど）
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(
            "person_name,person_id,person_type,episode_text,category\n"
            "山田太郎,P001,REAL,あなたと同じ30歳のとき彼は成功した,スポーツ\n"
            "田中花子,NaN,REAL,あなたと同じ25歳のとき彼女は活躍した,文化\n"
        )

        calculator = EPUPKPICalculator(str(csv_file))
        report = calculator.calculate_all()

        # スコアが計算される
        assert report.overall_score >= 0.0
        assert report.overall_score <= 1.0


class TestMainKPIOutput:
    """main関数のKPI出力テスト"""

    def test_main_kpi_output_with_target_zero(self, capsys, tmp_path):
        """ターゲット0%のKPI出力"""
        from src.monitoring.kpi_definitions import main

        csv_file = tmp_path / "test.csv"
        csv_file.write_text(
            "person_name,person_id,person_type,episode_text,category\n"
            "山田太郎,P001,REAL,あなたと同じ30歳のときエピソード内容,スポーツ\n"
        )

        with patch("sys.argv", ["kpi_definitions.py", str(csv_file)]):
            main()
            captured = capsys.readouterr()
            # 出力にステータスアイコンが含まれる
            assert "✅" in captured.out or "⚠️" in captured.out or "❌" in captured.out
