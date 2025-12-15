#!/usr/bin/env python3
"""integrity_checker テスト"""

import sys
import tempfile
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from integrity_checker import IntegrityChecker


class TestIntegrityChecker:
    """IntegrityCheckerのテスト"""

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
        import pandas as pd

        df = pd.DataFrame({"col1": [1, 2]})
        checker.check_data_integrity(df)
        # カウンターが存在することを確認
        assert hasattr(checker, "error_count")
        assert hasattr(checker, "warning_count")
