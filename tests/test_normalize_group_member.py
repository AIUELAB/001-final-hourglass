#!/usr/bin/env python3
"""
normalize_group_member_field.py のテストコード

テスト対象:
1. normalize_value() - 型正規化
2. check_group_consistency() - 整合性チェック
3. fix_group_consistency() - 整合性修正
"""

import pytest
import pandas as pd
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.data.normalize_group_member_field import (
    normalize_value,
    check_group_consistency,
    fix_group_consistency,
    analyze_current_state,
    normalize_dataframe,
)


class TestNormalizeValue:
    """型正規化のテスト"""

    def test_float_zero_to_false(self):
        """0.0 → False"""
        assert not normalize_value(0.0)

    def test_float_one_to_true(self):
        """1.0 → True"""
        assert normalize_value(1.0)

    def test_string_false_uppercase(self):
        """'FALSE' → False"""
        assert not normalize_value("FALSE")

    def test_string_false_lowercase(self):
        """'false' → False"""
        assert not normalize_value("false")

    def test_string_false_mixed_case(self):
        """'False' → False"""
        assert not normalize_value("False")

    def test_string_true_uppercase(self):
        """'TRUE' → True"""
        assert normalize_value("TRUE")

    def test_string_true_lowercase(self):
        """'true' → True"""
        assert normalize_value("true")

    def test_string_true_mixed_case(self):
        """'TrUe' → True"""
        assert normalize_value("TrUe")

    def test_string_yes_to_true(self):
        """'YES' → True"""
        assert normalize_value("YES")

    def test_string_one_to_true(self):
        """'1' → True"""
        assert normalize_value("1")

    def test_string_one_float_to_true(self):
        """'1.0' → True"""
        assert normalize_value("1.0")

    def test_string_zero_to_false(self):
        """'0' → False"""
        assert not normalize_value("0")

    def test_string_zero_float_to_false(self):
        """'0.0' → False"""
        assert not normalize_value("0.0")

    def test_bool_true(self):
        """True → True"""
        assert normalize_value(True)

    def test_bool_false(self):
        """False → False"""
        assert not normalize_value(False)

    def test_none_to_false(self):
        """None → False"""
        assert not normalize_value(None)

    def test_empty_string_to_false(self):
        """'' → False"""
        assert not normalize_value("")

    def test_nan_to_false(self):
        """NaN → False"""
        import numpy as np

        assert not normalize_value(np.nan)

    def test_int_zero_to_false(self):
        """0 (int) → False"""
        assert not normalize_value(0)

    def test_int_one_to_true(self):
        """1 (int) → True"""
        assert normalize_value(1)

    def test_int_two_to_false(self):
        """2 (int) → False (1以外の数値)"""
        assert not normalize_value(2)

    def test_random_string_to_false(self):
        """'random' → False"""
        assert not normalize_value("random")


class TestGroupConsistency:
    """整合性チェックのテスト"""

    def test_empty_group_with_true_is_inconsistent(self):
        """group_name が空で is_group_member = True → 不整合"""
        df = pd.DataFrame([{"person_name": "太郎", "group_name": "", "is_group_member": True}])

        result = check_group_consistency(df)
        assert result["inconsistency_count"] == 1
        assert not result["inconsistencies"][0]["expected"]

    def test_empty_group_with_false_is_consistent(self):
        """group_name が空で is_group_member = False → 整合"""
        df = pd.DataFrame([{"person_name": "太郎", "group_name": "", "is_group_member": False}])

        result = check_group_consistency(df)
        assert result["inconsistency_count"] == 0

    def test_unregistered_group_with_true_is_inconsistent(self):
        """group_name = '未登録' で is_group_member = True → 不整合"""
        df = pd.DataFrame([{"person_name": "次郎", "group_name": "未登録", "is_group_member": True}])

        result = check_group_consistency(df)
        assert result["inconsistency_count"] == 1
        assert not result["inconsistencies"][0]["expected"]

    def test_concrete_group_with_false_is_inconsistent(self):
        """group_name = '嵐' で is_group_member = False → 不整合"""
        df = pd.DataFrame([{"person_name": "三郎", "group_name": "嵐", "is_group_member": False}])

        result = check_group_consistency(df)
        assert result["inconsistency_count"] == 1
        assert result["inconsistencies"][0]["expected"]

    def test_concrete_group_with_true_is_consistent(self):
        """group_name = '嵐' で is_group_member = True → 整合"""
        df = pd.DataFrame([{"person_name": "三郎", "group_name": "嵐", "is_group_member": True}])

        result = check_group_consistency(df)
        assert result["inconsistency_count"] == 0

    def test_nan_group_with_true_is_inconsistent(self):
        """group_name = NaN で is_group_member = True → 不整合"""
        import numpy as np

        df = pd.DataFrame([{"person_name": "四郎", "group_name": np.nan, "is_group_member": True}])

        result = check_group_consistency(df)
        assert result["inconsistency_count"] == 1

    def test_multiple_inconsistencies(self):
        """複数の不整合を検出"""
        df = pd.DataFrame(
            [
                {"person_name": "太郎", "group_name": "", "is_group_member": True},
                {"person_name": "次郎", "group_name": "嵐", "is_group_member": False},
                {"person_name": "三郎", "group_name": "未登録", "is_group_member": True},
                {"person_name": "四郎", "group_name": "EXILE", "is_group_member": True},  # OK
            ]
        )

        result = check_group_consistency(df)
        assert result["inconsistency_count"] == 3
        assert result["total_checked"] == 4


class TestGroupConsistencyFix:
    """整合性修正のテスト"""

    def test_fix_empty_group_to_false(self):
        """group_name が空 → is_group_member を False に修正"""
        df = pd.DataFrame([{"person_name": "太郎", "group_name": "", "is_group_member": True}])

        df_fixed, stats = fix_group_consistency(df)
        assert not df_fixed.loc[0, "is_group_member"]
        assert stats["fixed"] == 1
        assert stats["unchanged"] == 0

    def test_fix_concrete_group_to_true(self):
        """group_name = '嵐' → is_group_member を True に修正"""
        df = pd.DataFrame([{"person_name": "次郎", "group_name": "嵐", "is_group_member": False}])

        df_fixed, stats = fix_group_consistency(df)
        assert df_fixed.loc[0, "is_group_member"]
        assert stats["fixed"] == 1

    def test_fix_unregistered_to_false(self):
        """group_name = '未登録' → is_group_member を False に修正"""
        df = pd.DataFrame([{"person_name": "三郎", "group_name": "未登録", "is_group_member": True}])

        df_fixed, stats = fix_group_consistency(df)
        assert not df_fixed.loc[0, "is_group_member"]
        assert stats["fixed"] == 1

    def test_no_change_when_consistent(self):
        """整合している場合は変更なし"""
        df = pd.DataFrame(
            [
                {"person_name": "太郎", "group_name": "", "is_group_member": False},
                {"person_name": "次郎", "group_name": "嵐", "is_group_member": True},
            ]
        )

        df_fixed, stats = fix_group_consistency(df)
        assert stats["fixed"] == 0
        assert stats["unchanged"] == 2

    def test_fix_multiple_rows(self):
        """複数行を一度に修正"""
        df = pd.DataFrame(
            [
                {"person_name": "太郎", "group_name": "", "is_group_member": True},
                {"person_name": "次郎", "group_name": "嵐", "is_group_member": False},
                {"person_name": "三郎", "group_name": "EXILE", "is_group_member": True},  # OK
                {"person_name": "四郎", "group_name": "未登録", "is_group_member": True},
            ]
        )

        df_fixed, stats = fix_group_consistency(df)
        assert stats["fixed"] == 3
        assert stats["unchanged"] == 1
        assert not df_fixed.loc[0, "is_group_member"]
        assert df_fixed.loc[1, "is_group_member"]
        assert df_fixed.loc[2, "is_group_member"]
        assert not df_fixed.loc[3, "is_group_member"]

    def test_fix_does_not_modify_original(self):
        """元のDataFrameを変更しない（コピーを返す）"""
        df = pd.DataFrame([{"person_name": "太郎", "group_name": "", "is_group_member": True}])

        df_original_value = df.loc[0, "is_group_member"]
        df_fixed, _ = fix_group_consistency(df)

        # 元のDataFrameは変更されていない
        assert df.loc[0, "is_group_member"] == df_original_value
        # 返されたDataFrameは修正されている
        assert not df_fixed.loc[0, "is_group_member"]


class TestAnalyzeCurrentState:
    """現状分析のテスト"""

    def test_analyze_mixed_types(self):
        """混在型の分析"""
        df = pd.DataFrame({"is_group_member": [False, 0.0, True, "FALSE", 1.0]})

        result = analyze_current_state(df)
        assert result["total_rows"] == 5
        assert result["unique_types"] >= 2  # float, bool, str
        assert "value_distribution" in result

    def test_analyze_missing_column(self):
        """カラムが存在しない場合"""
        df = pd.DataFrame({"other_column": [1, 2, 3]})

        result = analyze_current_state(df)
        assert "error" in result


class TestNormalizeDataframe:
    """DataFrame正規化のテスト"""

    def test_normalize_mixed_values(self):
        """混在値を正規化"""
        df = pd.DataFrame({"is_group_member": [False, 0.0, True, "FALSE", 1.0, "true"]})

        df_normalized, stats = normalize_dataframe(df)

        # 正規化後はすべてbool型
        assert all(isinstance(v, bool) for v in df_normalized["is_group_member"])

        # 値の確認
        assert not df_normalized.loc[0, "is_group_member"]
        assert not df_normalized.loc[1, "is_group_member"]  # 0.0 → False
        assert df_normalized.loc[2, "is_group_member"]
        assert not df_normalized.loc[3, "is_group_member"]  # "FALSE" → False
        assert df_normalized.loc[4, "is_group_member"]  # 1.0 → True
        assert df_normalized.loc[5, "is_group_member"]  # "true" → True

    def test_normalize_stats(self):
        """統計情報が正しく返される"""
        df = pd.DataFrame({"is_group_member": [False, 0.0, True, "FALSE"]})

        df_normalized, stats = normalize_dataframe(df)

        assert stats["total_rows"] == 4
        assert stats["to_false"] >= 1  # 0.0, "FALSE" のいずれか
        assert "to_true" in stats
        assert "unchanged_true" in stats
        assert "unchanged_false" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
