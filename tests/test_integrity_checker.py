#!/usr/bin/env python3
"""integrity_checker テスト"""

import sys
import tempfile
from pathlib import Path

import pytest

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
