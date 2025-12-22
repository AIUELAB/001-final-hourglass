#!/usr/bin/env python3
"""integrity_checker テスト"""

import sys
import tempfile
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from integrity_checker import IntegrityChecker


import pandas as pd
from unittest.mock import patch, mock_open


class TestIntegrityCheckerInit:
    """IntegrityChecker初期化のテスト"""

    def test_init(self):
        """初期化テスト"""
        checker = IntegrityChecker()
        assert checker.error_count == 0
        assert checker.warning_count == 0
        assert checker.check_results == []
        assert checker.repair_history == []

    def test_default_rules(self):
        """デフォルトルールテスト"""
        checker = IntegrityChecker()
        assert "required_columns" in checker.rules
        assert "unique_columns" in checker.rules
        assert "patterns" in checker.rules

    def test_required_columns(self):
        """必須カラムルール"""
        checker = IntegrityChecker()
        required = checker.rules["required_columns"]
        assert "person_id" in required
        assert "person_name" in required

    def test_patterns(self):
        """パターンルール"""
        checker = IntegrityChecker()
        patterns = checker.rules["patterns"]
        assert "person_id" in patterns
        assert "birth_year" in patterns

    def test_value_constraints(self):
        """値制約ルール"""
        checker = IntegrityChecker()
        constraints = checker.rules["value_constraints"]
        assert "birth_year" in constraints
        assert constraints["birth_year"]["min"] == 1900
        assert constraints["birth_year"]["max"] == 2025

    def test_custom_rules_file(self):
        """カスタムルールファイル"""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            checker = IntegrityChecker(rules_file=f.name)
            # ファイルが存在しない場合はデフォルトルールが使われる
            assert checker.rules is not None

    def test_check_data_integrity_valid(self):
        """有効なデータの整合性チェック"""
        import pandas as pd

        checker = IntegrityChecker()
        df = pd.DataFrame(
            {
                "person_id": ["P000001", "P000002"],
                "person_name": ["田中太郎", "山田花子"],
                "person_name_display": ["田中太郎", "山田花子"],
                "person_name_ja": ["タナカタロウ", "ヤマダハナコ"],
                "birth_year": ["1990", "1985"],
            }
        )
        result = checker.check_data_integrity(df)
        assert "timestamp" in result
        assert "total_rows" in result
        assert result["total_rows"] == 2

    def test_check_data_integrity_missing_columns(self):
        """欠損カラムの整合性チェック"""
        import pandas as pd

        checker = IntegrityChecker()
        df = pd.DataFrame(
            {
                "person_id": ["P000001"],
                "person_name": ["田中太郎"],
                # 必須カラムが欠落
            }
        )
        result = checker.check_data_integrity(df)
        # 欠落カラムがあるので、結果が返される（エラーか警告）
        assert result is not None
        assert "checks" in result

    def test_check_data_integrity_duplicate_ids(self):
        """重複IDの整合性チェック"""
        import pandas as pd

        checker = IntegrityChecker()
        df = pd.DataFrame(
            {
                "person_id": ["P000001", "P000001"],  # 重複
                "person_name": ["田中太郎", "山田花子"],
                "person_name_display": ["田中太郎", "山田花子"],
                "person_name_ja": ["タナカタロウ", "ヤマダハナコ"],
                "birth_year": ["1990", "1985"],
            }
        )
        result = checker.check_data_integrity(df)
        assert result is not None

    def test_duplicate_checks_config(self):
        """重複チェック設定"""
        checker = IntegrityChecker()
        dup_checks = checker.rules.get("duplicate_checks", {})
        assert "parentheses" in dup_checks
        assert "spaces" in dup_checks

    def test_consistency_rules_config(self):
        """一貫性ルール設定"""
        checker = IntegrityChecker()
        consistency = checker.rules.get("consistency_rules", {})
        assert "name_match" in consistency
        assert "date_format" in consistency

    def test_error_warning_counters(self):
        """エラー/警告カウンター"""
        checker = IntegrityChecker()
        assert checker.error_count == 0
        assert checker.warning_count == 0
        # チェック後にカウントが更新されることを確認
        df = pd.DataFrame({"col1": [1, 2]})
        checker.check_data_integrity(df)
        # カウンターが存在することを確認
        assert hasattr(checker, "error_count")
        assert hasattr(checker, "warning_count")


class TestLoadRules:
    """_load_rules() メソッドのテスト"""

    def test_loads_from_existing_file(self, tmp_path):
        """存在するルールファイルから読み込み"""
        rules_file = tmp_path / "rules.json"
        custom_rules = {"custom_key": "custom_value"}
        rules_file.write_text('{"custom_key": "custom_value"}', encoding="utf-8")

        checker = IntegrityChecker(rules_file=str(rules_file))
        assert "custom_key" in checker.rules
        assert checker.rules["custom_key"] == "custom_value"

    def test_handles_invalid_json(self, tmp_path):
        """不正なJSONを処理"""
        rules_file = tmp_path / "invalid.json"
        rules_file.write_text("not valid json", encoding="utf-8")

        checker = IntegrityChecker(rules_file=str(rules_file))
        # デフォルトルールが使われる
        assert "required_columns" in checker.rules


class TestCheckDataIntegrityWithAutoRepair:
    """check_data_integrity() のauto_repairオプションテスト"""

    def test_auto_repair_enabled(self):
        """auto_repair=Trueで自動修復"""
        checker = IntegrityChecker()
        df = pd.DataFrame(
            {
                "person_id": ["P000001"],
                "person_name": ["田中  太郎"],  # 連続スペース
                "person_name_display": ["田中 (田中)"],  # 括弧重複
                "person_name_ja": ["タナカタロウ"],
                "birth_year": ["1990"],
            }
        )
        result = checker.check_data_integrity(df, auto_repair=True)
        assert result is not None


class TestCheckDataTypes:
    """_check_data_types() メソッドのテスト"""

    def test_detects_non_numeric_birth_year(self):
        """非数値birth_yearを検出"""
        checker = IntegrityChecker()
        df = pd.DataFrame(
            {
                "person_id": ["P000001"],
                "person_name": ["田中太郎"],
                "person_name_display": ["田中太郎"],
                "person_name_ja": ["タナカタロウ"],
                "birth_year": ["invalid"],
            }
        )
        checker.check_data_integrity(df)
        assert checker.error_count > 0


class TestCheckRequiredFields:
    """_check_required_fields() メソッドのテスト"""

    def test_detects_null_person_id(self):
        """NULLのperson_idを検出"""
        checker = IntegrityChecker()
        df = pd.DataFrame(
            {
                "person_id": [None, "P000001"],
                "person_name": ["田中太郎", "山田花子"],
                "person_name_display": ["田中太郎", "山田花子"],
                "person_name_ja": ["タナカタロウ", "ヤマダハナコ"],
                "birth_year": ["1990", "1985"],
            }
        )
        checker.check_data_integrity(df)
        assert checker.error_count > 0

    def test_detects_empty_person_name(self):
        """空のperson_nameを検出"""
        checker = IntegrityChecker()
        df = pd.DataFrame(
            {
                "person_id": ["P000001", "P000002"],
                "person_name": ["", "山田花子"],
                "person_name_display": ["", "山田花子"],
                "person_name_ja": ["タナカタロウ", "ヤマダハナコ"],
                "birth_year": ["1990", "1985"],
            }
        )
        checker.check_data_integrity(df)
        assert checker.error_count > 0


class TestCheckPatterns:
    """_check_patterns() メソッドのテスト"""

    def test_detects_invalid_person_id_pattern(self):
        """不正なperson_idパターンを検出"""
        checker = IntegrityChecker()
        df = pd.DataFrame(
            {
                "person_id": ["INVALID"],  # Pで始まらない
                "person_name": ["田中太郎"],
                "person_name_display": ["田中太郎"],
                "person_name_ja": ["タナカタロウ"],
                "birth_year": ["1990"],
            }
        )
        checker.check_data_integrity(df)
        assert checker.warning_count > 0


class TestCheckValueConstraints:
    """_check_value_constraints() メソッドのテスト"""

    def test_detects_below_min_birth_year(self):
        """最小値未満のbirth_yearを検出"""
        checker = IntegrityChecker()
        df = pd.DataFrame(
            {
                "person_id": ["P000001"],
                "person_name": ["田中太郎"],
                "person_name_display": ["田中太郎"],
                "person_name_ja": ["タナカタロウ"],
                "birth_year": ["1800"],  # 1900未満
            }
        )
        checker.check_data_integrity(df)
        assert checker.warning_count > 0

    def test_detects_above_max_birth_year(self):
        """最大値超過のbirth_yearを検出"""
        checker = IntegrityChecker()
        df = pd.DataFrame(
            {
                "person_id": ["P000001"],
                "person_name": ["田中太郎"],
                "person_name_display": ["田中太郎"],
                "person_name_ja": ["タナカタロウ"],
                "birth_year": ["2099"],  # 2025超
            }
        )
        checker.check_data_integrity(df)
        assert checker.warning_count > 0


class TestCheckDuplicatePatterns:
    """_check_duplicate_patterns() メソッドのテスト"""

    def test_detects_parentheses_duplicate(self):
        """括弧内重複を検出"""
        checker = IntegrityChecker()
        df = pd.DataFrame(
            {
                "person_id": ["P000001"],
                "person_name": ["田中"],
                "person_name_display": ["田中 (田中)"],  # 括弧重複
                "person_name_ja": ["タナカ"],
                "birth_year": ["1990"],
            }
        )
        checker.check_data_integrity(df)
        assert checker.error_count > 0

    def test_detects_consecutive_spaces(self):
        """連続スペースを検出"""
        checker = IntegrityChecker()
        df = pd.DataFrame(
            {
                "person_id": ["P000001"],
                "person_name": ["田中  太郎"],  # 連続スペース
                "person_name_display": ["田中太郎"],
                "person_name_ja": ["タナカタロウ"],
                "birth_year": ["1990"],
            }
        )
        checker.check_data_integrity(df)
        assert checker.warning_count > 0


class TestCheckConsistency:
    """_check_consistency() メソッドのテスト"""

    def test_detects_name_inconsistency(self):
        """名前の不整合を検出"""
        checker = IntegrityChecker()
        df = pd.DataFrame(
            {
                "person_id": ["P000001"],
                "person_name": ["田中太郎"],
                "person_name_display": ["完全に別の名前"],  # 完全に異なる
                "person_name_ja": ["タナカタロウ"],
                "birth_year": ["1990"],
            }
        )
        checker.check_data_integrity(df)
        assert checker.warning_count > 0


class TestCheckCompleteness:
    """_check_completeness() メソッドのテスト"""

    def test_detects_high_null_ratio(self):
        """高い欠損率を検出"""
        checker = IntegrityChecker()
        df = pd.DataFrame(
            {
                "person_id": ["P000001", "P000002", "P000003", "P000004"],
                "person_name": ["田中", "山田", "佐藤", "鈴木"],
                "person_name_display": ["田中", "山田", "佐藤", "鈴木"],
                "person_name_ja": [None, None, None, "スズキ"],  # 75%欠損
                "birth_year": ["1990", "1990", "1990", "1990"],
            }
        )
        checker.check_data_integrity(df)
        assert checker.warning_count > 0


class TestAutoRepair:
    """_auto_repair() メソッドのテスト"""

    def test_repairs_parentheses_duplicate(self):
        """括弧重複を修復"""
        checker = IntegrityChecker()
        df = pd.DataFrame(
            {
                "person_id": ["P000001"],
                "person_name": ["田中"],
                "person_name_display": ["田中 (田中)"],
                "person_name_ja": ["タナカ"],
                "birth_year": ["1990"],
            }
        )
        # 手動でauto_repairを呼び出し
        repaired = checker._auto_repair(df)
        assert len(checker.repair_history) > 0

    def test_repairs_consecutive_spaces(self):
        """連続スペースを修復"""
        checker = IntegrityChecker()
        df = pd.DataFrame(
            {
                "person_id": ["P000001"],
                "person_name": ["田中  太郎"],
                "person_name_display": ["田中太郎"],
                "person_name_ja": ["タナカタロウ"],
                "birth_year": ["1990"],
            }
        )
        repaired = checker._auto_repair(df)
        assert "  " not in repaired["person_name"].iloc[0]

    def test_removes_special_chars(self):
        """特殊文字を除去"""
        checker = IntegrityChecker()
        df = pd.DataFrame(
            {
                "person_id": ["P000001"],
                "person_name": ["田中<script>"],
                "person_name_display": ["田中太郎"],
                "person_name_ja": ["タナカタロウ"],
                "birth_year": ["1990"],
            }
        )
        repaired = checker._auto_repair(df)
        assert "<" not in repaired["person_name"].iloc[0]


class TestValidateBeforeSync:
    """validate_before_sync() メソッドのテスト"""

    def test_returns_false_on_errors(self):
        """エラー時はFalseを返す"""
        checker = IntegrityChecker()
        df = pd.DataFrame(
            {
                "person_id": ["P000001", "P000001"],  # 重複
                "person_name": ["田中", "山田"],
                "person_name_display": ["田中", "山田"],
                "person_name_ja": ["タナカ", "ヤマダ"],
                "birth_year": ["1990", "1990"],
            }
        )
        is_valid, _ = checker.validate_before_sync(df)
        assert is_valid is False

    def test_returns_true_with_warnings_only(self):
        """警告のみの場合はTrueを返す"""
        checker = IntegrityChecker()
        df = pd.DataFrame(
            {
                "person_id": ["P000001"],
                "person_name": ["田中太郎"],
                "person_name_display": ["田中太郎"],
                "person_name_ja": ["タナカタロウ"],
                "birth_year": ["1800"],  # 警告のみ
            }
        )
        is_valid, _ = checker.validate_before_sync(df)
        assert is_valid is True


class TestGenerateIntegrityReport:
    """generate_integrity_report() メソッドのテスト"""

    def test_generates_report_text(self):
        """レポートテキストを生成"""
        checker = IntegrityChecker()
        df = pd.DataFrame(
            {
                "person_id": ["P000001"],
                "person_name": ["田中太郎"],
                "person_name_display": ["田中太郎"],
                "person_name_ja": ["タナカタロウ"],
                "birth_year": ["1990"],
            }
        )
        report = checker.generate_integrity_report(df)
        assert "データ整合性レポート" in report
        assert "サマリー" in report
        assert "チェック項目" in report

    def test_includes_details_on_errors(self):
        """エラー時は詳細を含む"""
        checker = IntegrityChecker()
        df = pd.DataFrame(
            {
                "person_id": ["P000001", "P000001"],  # 重複エラー
                "person_name": ["田中", "山田"],
                "person_name_display": ["田中", "山田"],
                "person_name_ja": ["タナカ", "ヤマダ"],
                "birth_year": ["1990", "1990"],
            }
        )
        report = checker.generate_integrity_report(df)
        assert "詳細" in report


class TestAddErrorAndWarning:
    """_add_error() / _add_warning() メソッドのテスト"""

    def test_add_error_increments_counter(self):
        """エラー追加でカウンター増加"""
        checker = IntegrityChecker()
        checker._add_error("テストエラー")
        assert checker.error_count == 1
        assert len(checker.check_results) == 1
        assert checker.check_results[0]["level"] == "ERROR"

    def test_add_warning_increments_counter(self):
        """警告追加でカウンター増加"""
        checker = IntegrityChecker()
        checker._add_warning("テスト警告")
        assert checker.warning_count == 1
        assert len(checker.check_results) == 1
        assert checker.check_results[0]["level"] == "WARNING"


class TestCheckStructure:
    """_check_structure() メソッドのテスト"""

    def test_detects_invalid_column_name(self):
        """無効なカラム名を検出"""
        checker = IntegrityChecker()
        df = pd.DataFrame(
            {
                "person_id": ["P000001"],
                "person_name": ["田中"],
                "person_name_display": ["田中"],
                "person_name_ja": ["タナカ"],
                "birth_year": ["1990"],
                "invalid@column": ["test"],  # 無効な文字
            }
        )
        checker.check_data_integrity(df)
        assert checker.warning_count > 0
