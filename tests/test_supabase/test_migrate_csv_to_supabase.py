"""
migrate_csv_to_supabase.py のユニットテスト

サニタイズ関数のテストを中心に実施
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "scripts" / "supabase"))

from migrate_csv_to_supabase import sanitize_value, sanitize_records, INTEGER_COLUMNS


class TestSanitizeValue:
    """sanitize_value関数のテスト"""

    def test_none_returns_none(self):
        """Noneは変換されずNoneを返す"""
        assert sanitize_value(None) is None

    def test_nan_returns_none(self):
        """NaNはNoneに変換される"""
        assert sanitize_value(float("nan")) is None
        assert sanitize_value(np.nan) is None

    def test_inf_returns_none(self):
        """Inf/-InfはNoneに変換される"""
        assert sanitize_value(float("inf")) is None
        assert sanitize_value(float("-inf")) is None
        assert sanitize_value(np.inf) is None

    def test_pandas_na_returns_none(self):
        """pandas NAはNoneに変換される"""
        assert sanitize_value(pd.NA) is None
        assert sanitize_value(pd.NaT) is None

    def test_numpy_integer_to_python_int(self):
        """numpy整数型はPython intに変換される"""
        assert sanitize_value(np.int64(42)) == 42
        assert isinstance(sanitize_value(np.int64(42)), int)
        assert sanitize_value(np.int32(100)) == 100

    def test_numpy_float_to_python_float(self):
        """numpy浮動小数点型はPython floatに変換される"""
        result = sanitize_value(np.float64(3.14))
        assert result == 3.14
        assert isinstance(result, float)

    def test_numpy_bool_to_python_bool(self):
        """numpy bool型はPython boolに変換される"""
        assert sanitize_value(np.bool_(True)) is True
        assert sanitize_value(np.bool_(False)) is False

    def test_integer_column_float_to_int(self):
        """INTEGERカラムでfloat値はintに変換される"""
        # birth_year=1890.0 -> 1890
        assert sanitize_value(1890.0, column_name="birth_year") == 1890
        assert isinstance(sanitize_value(1890.0, column_name="birth_year"), int)

        # age=45.0 -> 45
        assert sanitize_value(45.0, column_name="age") == 45

    def test_integer_column_string_to_int(self):
        """INTEGERカラムで文字列数値はintに変換される"""
        assert sanitize_value("1890", column_name="birth_year") == 1890
        assert sanitize_value("45.0", column_name="age") == 45

    def test_integer_column_invalid_string_returns_none(self):
        """INTEGERカラムで無効な文字列はNoneを返す"""
        assert sanitize_value("invalid", column_name="birth_year") is None
        assert sanitize_value("", column_name="age") is None

    def test_non_integer_column_float_stays_float(self):
        """非INTEGERカラムではfloatはfloatのまま"""
        result = sanitize_value(3.14, column_name="composite_score")
        assert result == 3.14
        assert isinstance(result, float)

    def test_regular_string_unchanged(self):
        """通常の文字列は変換されない"""
        assert sanitize_value("テスト文字列") == "テスト文字列"
        assert sanitize_value("episode_001") == "episode_001"


class TestSanitizeRecords:
    """sanitize_records関数のテスト"""

    def test_empty_list(self):
        """空リストは空リストを返す"""
        assert sanitize_records([]) == []

    def test_single_record(self):
        """単一レコードのサニタイズ"""
        records = [
            {
                "episode_id": "EP001",
                "age": 45.0,
                "birth_year": np.float64(1890.0),
                "score": np.nan,
            }
        ]
        result = sanitize_records(records)

        assert len(result) == 1
        assert result[0]["episode_id"] == "EP001"
        assert result[0]["age"] == 45  # int
        assert result[0]["birth_year"] == 1890  # int
        assert result[0]["score"] is None  # NaN -> None

    def test_multiple_records(self):
        """複数レコードのサニタイズ"""
        records = [
            {"episode_id": "EP001", "age": 30.0},
            {"episode_id": "EP002", "age": np.nan},
            {"episode_id": "EP003", "age": np.int64(25)},
        ]
        result = sanitize_records(records)

        assert len(result) == 3
        assert result[0]["age"] == 30
        assert result[1]["age"] is None
        assert result[2]["age"] == 25


class TestIntegerColumns:
    """INTEGER_COLUMNS定数のテスト"""

    def test_expected_columns_present(self):
        """期待されるINTEGERカラムが含まれている"""
        expected = {
            "episode_count",
            "age",
            "wikipedia_pv",
            "birth_year",
            "death_year",
        }
        assert expected.issubset(INTEGER_COLUMNS)

    def test_non_integer_columns_not_present(self):
        """非INTEGERカラムが含まれていない"""
        assert "episode_id" not in INTEGER_COLUMNS
        assert "person_name" not in INTEGER_COLUMNS
        assert "composite_score" not in INTEGER_COLUMNS


class TestGetSupabaseClient:
    """get_supabase_client関数のテスト"""

    def test_missing_env_raises_error(self, monkeypatch):
        """環境変数欠損時にValueErrorが発生"""
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)

        from migrate_csv_to_supabase import get_supabase_client
        import pytest

        with pytest.raises(ValueError, match="SUPABASE_URL と SUPABASE_SERVICE_ROLE_KEY が必要です"):
            get_supabase_client()


class TestCleanData:
    """clean_data関数のテスト"""

    def test_boolean_conversion_true(self):
        """Boolean型TRUEの変換"""
        from migrate_csv_to_supabase import clean_data

        df = pd.DataFrame({"is_group_member": [True, "TRUE", 1], "is_japanese": [True, True, True]})
        result = clean_data(df)
        assert result["is_group_member"].iloc[0] == True  # noqa: E712
        assert result["is_japanese"].iloc[0] == True  # noqa: E712

    def test_boolean_conversion_false(self):
        """Boolean型FALSEの変換"""
        from migrate_csv_to_supabase import clean_data

        df = pd.DataFrame({"is_group_member": [False, "", None], "is_japanese": [False, False, False]})
        result = clean_data(df)
        assert result["is_group_member"].iloc[0] == False  # noqa: E712
        assert result["is_group_member"].iloc[1] is None  # 空文字はNone
        assert result["is_group_member"].iloc[2] is None  # NoneはNone


class TestLoadCsv:
    """load_csv関数のテスト"""

    def test_file_not_found(self, monkeypatch, tmp_path):
        """ファイル不在時にFileNotFoundErrorが発生"""
        from migrate_csv_to_supabase import load_csv
        import pytest

        # PROJECT_ROOTを一時ディレクトリに変更
        import migrate_csv_to_supabase

        monkeypatch.setattr(migrate_csv_to_supabase, "PROJECT_ROOT", tmp_path)

        with pytest.raises(FileNotFoundError, match="マスターCSVが見つかりません"):
            load_csv()
