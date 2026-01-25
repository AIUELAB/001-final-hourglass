"""
migrate_csv_to_supabase.py のユニットテスト

サニタイズ関数のテストを中心に実施
"""

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "scripts" / "supabase"))

from migrate_csv_to_supabase import sanitize_value, sanitize_records, INTEGER_COLUMNS


@pytest.fixture
def mock_migrate_setup(mocker, tmp_path):
    """migrate関数テスト用の共通セットアップ"""
    import migrate_csv_to_supabase

    csv_path = tmp_path / "preserved" / "data"
    csv_path.mkdir(parents=True)
    csv_file = csv_path / "MASTER_EPISODES_CURRENT.csv"
    csv_file.write_text("episode_id,person_name,age\nEP001,Test,30", encoding="utf-8-sig")

    mocker.patch.object(migrate_csv_to_supabase, "PROJECT_ROOT", tmp_path)

    mock_client = mocker.MagicMock()
    mocker.patch.object(migrate_csv_to_supabase, "get_supabase_client", return_value=mock_client)

    # 検証クエリのデフォルトモック
    mock_count_result = mocker.MagicMock()
    mock_count_result.count = 1
    mock_client.table().select().execute.return_value = mock_count_result

    return {
        "client": mock_client,
        "tmp_path": tmp_path,
        "csv_file": csv_file,
        "module": migrate_csv_to_supabase,
    }


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

    def test_integer_column_conversion(self):
        """INTEGERカラムがInt64型に変換される"""
        from migrate_csv_to_supabase import clean_data

        # テスト用DataFrame（INTEGERカラムを含む）
        # pd.to_numeric(errors="coerce")で文字列は変換前にNaNに変換される
        df = pd.DataFrame(
            {
                "age": [30.0, 45.0, None, 50.0],
                "birth_year": [1990.0, 1985.0, np.nan, 2000.0],
                "episode_count": [5, 10, 15, 20],
                "person_name": ["Alice", "Bob", "Charlie", "Diana"],  # 非INTEGERカラム
            }
        )

        result = clean_data(df)

        # INTEGERカラムがInt64型に変換されていること
        assert result["age"].dtype == "Int64"
        assert result["birth_year"].dtype == "Int64"
        assert result["episode_count"].dtype == "Int64"

        # 値の検証（NaNは<NA>に変換）
        assert result["age"].iloc[0] == 30
        assert result["birth_year"].iloc[2] is pd.NA  # NaNはpd.NAに
        assert result["episode_count"].iloc[3] == 20


class TestLoadCsv:
    """load_csv関数のテスト"""

    def test_file_not_found(self, monkeypatch, tmp_path):
        """ファイル不在時にFileNotFoundErrorが発生"""
        from migrate_csv_to_supabase import load_csv

        # PROJECT_ROOTを一時ディレクトリに変更
        import migrate_csv_to_supabase

        monkeypatch.setattr(migrate_csv_to_supabase, "PROJECT_ROOT", tmp_path)

        with pytest.raises(FileNotFoundError, match="マスターCSVが見つかりません"):
            load_csv()

    def test_csv_parse_error_raises_value_error(self, monkeypatch, tmp_path):
        """不正なCSVファイルでValueErrorが発生"""
        from migrate_csv_to_supabase import load_csv
        import migrate_csv_to_supabase

        monkeypatch.setattr(migrate_csv_to_supabase, "PROJECT_ROOT", tmp_path)

        csv_path = tmp_path / "preserved" / "data"
        csv_path.mkdir(parents=True)
        csv_file = csv_path / "MASTER_EPISODES_CURRENT.csv"
        # カラム数不一致の不正CSV
        csv_file.write_text('episode_id,person_name,age\n1,"unclosed quote', encoding="utf-8-sig")

        with pytest.raises(ValueError, match="CSV解析エラー"):
            load_csv()


class TestUpsertBatch:
    """upsert_batch関数のテスト（PRレビューH-5対応）"""

    def test_upsert_batch_success(self, mocker):
        """正常系: バッチupsert成功"""
        from migrate_csv_to_supabase import upsert_batch

        mock_client = mocker.MagicMock()
        mock_result = mocker.MagicMock()
        mock_result.data = [{"episode_id": "1"}, {"episode_id": "2"}]
        mock_client.table().upsert().execute.return_value = mock_result

        result = upsert_batch(mock_client, [{"episode_id": "1"}, {"episode_id": "2"}])

        assert result["success_count"] == 2
        assert len(result["data"]) == 2

    def test_upsert_batch_partial_success(self, mocker):
        """部分成功: 一部のみupsert成功"""
        from migrate_csv_to_supabase import upsert_batch

        mock_client = mocker.MagicMock()
        mock_result = mocker.MagicMock()
        mock_result.data = [{"episode_id": "1"}]  # 2件中1件のみ成功
        mock_client.table().upsert().execute.return_value = mock_result

        result = upsert_batch(mock_client, [{"episode_id": "1"}, {"episode_id": "2"}])

        assert result["success_count"] == 1

    def test_upsert_batch_empty_result(self, mocker):
        """空結果: dataがNoneの場合"""
        from migrate_csv_to_supabase import upsert_batch

        mock_client = mocker.MagicMock()
        mock_result = mocker.MagicMock()
        mock_result.data = None
        mock_client.table().upsert().execute.return_value = mock_result

        result = upsert_batch(mock_client, [{"episode_id": "1"}])

        assert result["success_count"] == 0
        assert result["data"] == []


class TestMigrate:
    """migrate関数のテスト（PRレビューH-6対応）"""

    def test_migrate_dry_run_no_db_call(self, mocker, tmp_path):
        """dry-runモードでDB書き込みなし"""
        from migrate_csv_to_supabase import migrate
        import migrate_csv_to_supabase

        # CSVファイルを一時作成
        csv_path = tmp_path / "preserved" / "data"
        csv_path.mkdir(parents=True)
        csv_file = csv_path / "MASTER_EPISODES_CURRENT.csv"
        csv_file.write_text("episode_id,person_name,age\n1,Test,30", encoding="utf-8-sig")

        # PROJECT_ROOTを一時ディレクトリに変更
        mocker.patch.object(migrate_csv_to_supabase, "PROJECT_ROOT", tmp_path)

        # upsert_batchが呼ばれないことを確認
        mock_upsert = mocker.patch.object(migrate_csv_to_supabase, "upsert_batch")
        mock_client = mocker.patch.object(migrate_csv_to_supabase, "get_supabase_client")

        migrate(dry_run=True)

        mock_upsert.assert_not_called()
        mock_client.assert_not_called()

    def test_migrate_handles_api_error_gracefully(self, mocker, tmp_path, capsys, caplog):
        """APIエラー発生時も例外で終了せず、エラーログが出力される"""
        from migrate_csv_to_supabase import migrate
        from postgrest.exceptions import APIError
        import migrate_csv_to_supabase

        # CSVファイルを一時作成
        csv_path = tmp_path / "preserved" / "data"
        csv_path.mkdir(parents=True)
        csv_file = csv_path / "MASTER_EPISODES_CURRENT.csv"
        csv_file.write_text("episode_id,person_name,age\n1,Test,30", encoding="utf-8-sig")

        mocker.patch.object(migrate_csv_to_supabase, "PROJECT_ROOT", tmp_path)

        mock_client = mocker.MagicMock()
        mocker.patch.object(migrate_csv_to_supabase, "get_supabase_client", return_value=mock_client)

        # upsert_batchでAPIError発生
        mock_error = APIError({"message": "constraint violation"})
        mocker.patch.object(migrate_csv_to_supabase, "upsert_batch", side_effect=mock_error)

        # 検証クエリもモック
        mock_count_result = mocker.MagicMock()
        mock_count_result.count = 0
        mock_client.table().select().execute.return_value = mock_count_result

        # 例外なく完了すること
        with caplog.at_level(logging.ERROR):
            migrate(dry_run=False)

        # H-4対応: エラーログが出力されていることを検証（logger.error使用）
        assert any(record.levelno == logging.ERROR and "APIError" in record.message for record in caplog.records)
        assert "constraint violation" in caplog.text
        # フォーマット済みメッセージの検証（バッチ番号が含まれる）
        assert "Batch 1 APIError:" in caplog.text

        # コンソール出力の検証
        captured = capsys.readouterr()
        assert "[NG] 失敗:" in captured.out

    def test_migrate_batch_size_zero_raises_error(self):
        """batch_size=0でValueError発生（PRレビュー#14指摘）"""
        from migrate_csv_to_supabase import migrate

        with pytest.raises(ValueError, match="batch_size は1以上"):
            migrate(batch_size=0)

    def test_migrate_batch_size_negative_raises_error(self):
        """batch_size=-1でValueError発生（PRレビュー#14指摘）"""
        from migrate_csv_to_supabase import migrate

        with pytest.raises(ValueError, match="batch_size は1以上"):
            migrate(batch_size=-1)

    def test_migrate_batch_size_large_warns(self, mocker, tmp_path, caplog):
        """batch_size>10000で警告ログ出力（PRレビュー#14指摘）"""
        from migrate_csv_to_supabase import migrate
        import migrate_csv_to_supabase

        # CSVファイルを一時作成
        csv_path = tmp_path / "preserved" / "data"
        csv_path.mkdir(parents=True)
        csv_file = csv_path / "MASTER_EPISODES_CURRENT.csv"
        csv_file.write_text("episode_id,person_name,age\n1,Test,30", encoding="utf-8-sig")

        mocker.patch.object(migrate_csv_to_supabase, "PROJECT_ROOT", tmp_path)

        # dry_run=Trueで実際のDB呼び出しを回避
        with caplog.at_level(logging.WARNING):
            migrate(batch_size=10001, dry_run=True)

        # ログレベルがWARNINGであることを検証
        assert any(
            record.levelno == logging.WARNING and "batch_size too large" in record.message for record in caplog.records
        )
        # batch_size値がログに含まれることを検証
        assert "10001" in caplog.text

    def test_migrate_handles_connection_error_gracefully(self, mocker, tmp_path, caplog):
        """接続エラー発生時も例外で終了せず、エラーログが出力される（PRレビュー#22追加）"""
        from migrate_csv_to_supabase import migrate
        import migrate_csv_to_supabase

        # CSVファイルを一時作成
        csv_path = tmp_path / "preserved" / "data"
        csv_path.mkdir(parents=True)
        csv_file = csv_path / "MASTER_EPISODES_CURRENT.csv"
        csv_file.write_text("episode_id,person_name,age\n1,Test,30", encoding="utf-8-sig")

        mocker.patch.object(migrate_csv_to_supabase, "PROJECT_ROOT", tmp_path)

        mock_client = mocker.MagicMock()
        mocker.patch.object(migrate_csv_to_supabase, "get_supabase_client", return_value=mock_client)

        # upsert_batchでConnectionError発生
        mocker.patch.object(migrate_csv_to_supabase, "upsert_batch", side_effect=ConnectionError("Network unreachable"))

        # 検証クエリもモック
        mock_count_result = mocker.MagicMock()
        mock_count_result.count = 0
        mock_client.table().select().execute.return_value = mock_count_result

        # 例外なく完了すること
        with caplog.at_level(logging.ERROR):
            migrate(dry_run=False)

        # 接続エラーがログに出力されていること
        assert any(
            record.levelno == logging.ERROR and "connection error" in record.message for record in caplog.records
        )
        # フォーマット済みメッセージの検証（バッチ番号が含まれる）
        assert "Batch 1 connection error:" in caplog.text

    def test_migrate_handles_unexpected_error_gracefully(self, mocker, tmp_path, caplog):
        """予期しないエラー発生時に調査推奨メッセージが出力される（PRレビュー#22追加）"""
        from migrate_csv_to_supabase import migrate
        import migrate_csv_to_supabase

        # CSVファイルを一時作成
        csv_path = tmp_path / "preserved" / "data"
        csv_path.mkdir(parents=True)
        csv_file = csv_path / "MASTER_EPISODES_CURRENT.csv"
        csv_file.write_text("episode_id,person_name,age\n1,Test,30", encoding="utf-8-sig")

        mocker.patch.object(migrate_csv_to_supabase, "PROJECT_ROOT", tmp_path)

        mock_client = mocker.MagicMock()
        mocker.patch.object(migrate_csv_to_supabase, "get_supabase_client", return_value=mock_client)

        # upsert_batchで予期しないRuntimeError発生
        mocker.patch.object(
            migrate_csv_to_supabase, "upsert_batch", side_effect=RuntimeError("Unexpected internal error")
        )

        # 検証クエリもモック
        mock_count_result = mocker.MagicMock()
        mock_count_result.count = 0
        mock_client.table().select().execute.return_value = mock_count_result

        # 例外なく完了すること
        with caplog.at_level(logging.ERROR):
            migrate(dry_run=False)

        # 調査推奨メッセージがログに出力されていること
        assert any(
            record.levelno == logging.ERROR and "investigation may be required" in record.message
            for record in caplog.records
        )
        # エラー種別がログに含まれることを検証
        assert "RuntimeError" in caplog.text

    def test_migrate_handles_json_decode_error_gracefully(self, mocker, tmp_path, caplog):
        """JSONDecodeError発生時も例外で終了せず、エラーログが出力される（PRレビュー#22追加）"""
        from migrate_csv_to_supabase import migrate
        import migrate_csv_to_supabase
        import json

        # CSVファイルを一時作成
        csv_path = tmp_path / "preserved" / "data"
        csv_path.mkdir(parents=True)
        csv_file = csv_path / "MASTER_EPISODES_CURRENT.csv"
        csv_file.write_text("episode_id,person_name,age\n1,Test,30", encoding="utf-8-sig")

        mocker.patch.object(migrate_csv_to_supabase, "PROJECT_ROOT", tmp_path)

        mock_client = mocker.MagicMock()
        mocker.patch.object(migrate_csv_to_supabase, "get_supabase_client", return_value=mock_client)

        # upsert_batchでJSONDecodeError発生
        mocker.patch.object(
            migrate_csv_to_supabase, "upsert_batch", side_effect=json.JSONDecodeError("Invalid JSON", "doc", 0)
        )

        # 検証クエリもモック
        mock_count_result = mocker.MagicMock()
        mock_count_result.count = 0
        mock_client.table().select().execute.return_value = mock_count_result

        # 例外なく完了すること
        with caplog.at_level(logging.ERROR):
            migrate(dry_run=False)

        # データ変換エラーとしてログに出力されていること（JSONDecodeErrorはValueError継承）
        assert any(
            record.levelno == logging.ERROR and "data conversion error" in record.message for record in caplog.records
        )

    def test_migrate_handles_type_error_gracefully(self, mocker, tmp_path, caplog):
        """TypeError発生時も例外で終了せず、エラーログが出力される（PRレビュー#22追加）"""
        from migrate_csv_to_supabase import migrate
        import migrate_csv_to_supabase

        csv_path = tmp_path / "preserved" / "data"
        csv_path.mkdir(parents=True)
        csv_file = csv_path / "MASTER_EPISODES_CURRENT.csv"
        csv_file.write_text("episode_id,person_name,age\n1,Test,30", encoding="utf-8-sig")

        mocker.patch.object(migrate_csv_to_supabase, "PROJECT_ROOT", tmp_path)

        mock_client = mocker.MagicMock()
        mocker.patch.object(migrate_csv_to_supabase, "get_supabase_client", return_value=mock_client)

        mocker.patch.object(migrate_csv_to_supabase, "upsert_batch", side_effect=TypeError("unsupported operand type"))

        mock_count_result = mocker.MagicMock()
        mock_count_result.count = 0
        mock_client.table().select().execute.return_value = mock_count_result

        with caplog.at_level(logging.ERROR):
            migrate(dry_run=False)

        # データ構造エラーとしてログに出力されていること
        assert any(
            record.levelno == logging.ERROR and "data structure error" in record.message for record in caplog.records
        )
        assert "TypeError" in caplog.text

    def test_migrate_handles_key_error_gracefully(self, mocker, tmp_path, caplog):
        """KeyError発生時も例外で終了せず、エラーログが出力される（PRレビュー#22追加）"""
        from migrate_csv_to_supabase import migrate
        import migrate_csv_to_supabase

        csv_path = tmp_path / "preserved" / "data"
        csv_path.mkdir(parents=True)
        csv_file = csv_path / "MASTER_EPISODES_CURRENT.csv"
        csv_file.write_text("episode_id,person_name,age\n1,Test,30", encoding="utf-8-sig")

        mocker.patch.object(migrate_csv_to_supabase, "PROJECT_ROOT", tmp_path)

        mock_client = mocker.MagicMock()
        mocker.patch.object(migrate_csv_to_supabase, "get_supabase_client", return_value=mock_client)

        mocker.patch.object(migrate_csv_to_supabase, "upsert_batch", side_effect=KeyError("missing_key"))

        mock_count_result = mocker.MagicMock()
        mock_count_result.count = 0
        mock_client.table().select().execute.return_value = mock_count_result

        with caplog.at_level(logging.ERROR):
            migrate(dry_run=False)

        # データ構造エラーとしてログに出力されていること
        assert any(
            record.levelno == logging.ERROR and "data structure error" in record.message for record in caplog.records
        )
        assert "KeyError" in caplog.text

    def test_migrate_propagates_keyboard_interrupt(self, mocker, tmp_path):
        """KeyboardInterrupt発生時は再送出される（ユーザー意図の中断）"""
        from migrate_csv_to_supabase import migrate
        import migrate_csv_to_supabase

        # CSVファイルを一時作成
        csv_path = tmp_path / "preserved" / "data"
        csv_path.mkdir(parents=True)
        csv_file = csv_path / "MASTER_EPISODES_CURRENT.csv"
        csv_file.write_text("episode_id,person_name,age\n1,Test,30", encoding="utf-8-sig")

        mocker.patch.object(migrate_csv_to_supabase, "PROJECT_ROOT", tmp_path)

        mock_client = mocker.MagicMock()
        mocker.patch.object(migrate_csv_to_supabase, "get_supabase_client", return_value=mock_client)

        # upsert_batchでKeyboardInterrupt発生
        mocker.patch.object(migrate_csv_to_supabase, "upsert_batch", side_effect=KeyboardInterrupt())

        # KeyboardInterruptが再送出されること
        with pytest.raises(KeyboardInterrupt):
            migrate(dry_run=False)

    def test_migrate_propagates_system_exit(self, mocker, tmp_path):
        """SystemExit発生時は再送出される（PRレビューW-1対応）"""
        from migrate_csv_to_supabase import migrate
        import migrate_csv_to_supabase

        csv_path = tmp_path / "preserved" / "data"
        csv_path.mkdir(parents=True)
        csv_file = csv_path / "MASTER_EPISODES_CURRENT.csv"
        csv_file.write_text("episode_id,person_name,age\n1,Test,30", encoding="utf-8-sig")

        mocker.patch.object(migrate_csv_to_supabase, "PROJECT_ROOT", tmp_path)

        mock_client = mocker.MagicMock()
        mocker.patch.object(migrate_csv_to_supabase, "get_supabase_client", return_value=mock_client)

        # upsert_batchでSystemExit発生
        mocker.patch.object(migrate_csv_to_supabase, "upsert_batch", side_effect=SystemExit(1))

        # SystemExitが再送出されること
        with pytest.raises(SystemExit):
            migrate(dry_run=False)

    def test_migrate_log_save_failure_fallback(self, mocker, tmp_path, capsys, caplog):
        """ログ保存失敗時にフォールバック出力される"""
        from migrate_csv_to_supabase import migrate
        from postgrest.exceptions import APIError
        import migrate_csv_to_supabase

        csv_path = tmp_path / "preserved" / "data"
        csv_path.mkdir(parents=True)
        csv_file = csv_path / "MASTER_EPISODES_CURRENT.csv"
        csv_file.write_text("episode_id,person_name,age\nEP001,Test,30", encoding="utf-8-sig")

        mocker.patch.object(migrate_csv_to_supabase, "PROJECT_ROOT", tmp_path)

        mock_client = mocker.MagicMock()
        mocker.patch.object(migrate_csv_to_supabase, "get_supabase_client", return_value=mock_client)

        # upsert_batchでAPIError発生（失敗レコードを生成するため）
        mock_error = APIError({"message": "test error"})
        mocker.patch.object(migrate_csv_to_supabase, "upsert_batch", side_effect=mock_error)

        # 検証クエリをモック
        mock_count_result = mocker.MagicMock()
        mock_count_result.count = 0
        mock_client.table().select().execute.return_value = mock_count_result

        # ログ保存時にIOErrorを発生させる
        original_open = open

        def mock_open_error(path, *args, **kwargs):
            if "migration_errors_" in str(path):
                raise IOError("Permission denied")
            return original_open(path, *args, **kwargs)

        mocker.patch("builtins.open", side_effect=mock_open_error)

        with caplog.at_level(logging.ERROR):
            migrate(dry_run=False)

        # フォールバック出力が表示されること
        captured = capsys.readouterr()
        assert "[FALLBACK]" in captured.out
        # ログ保存失敗のエラーログ
        assert "Failed to save log" in caplog.text

    def test_migrate_count_mismatch_logs_error(self, mocker, tmp_path, caplog):
        """件数不一致時にエラーログが出力される"""
        from migrate_csv_to_supabase import migrate
        import migrate_csv_to_supabase

        csv_path = tmp_path / "preserved" / "data"
        csv_path.mkdir(parents=True)
        csv_file = csv_path / "MASTER_EPISODES_CURRENT.csv"
        csv_file.write_text("episode_id,person_name,age\nEP001,Test,30", encoding="utf-8-sig")

        mocker.patch.object(migrate_csv_to_supabase, "PROJECT_ROOT", tmp_path)

        mock_client = mocker.MagicMock()
        mocker.patch.object(migrate_csv_to_supabase, "get_supabase_client", return_value=mock_client)

        # upsert成功
        mock_upsert_result = {"success_count": 1, "data": [{"episode_id": "EP001"}]}
        mocker.patch.object(migrate_csv_to_supabase, "upsert_batch", return_value=mock_upsert_result)

        # 件数不一致: success_count=1 だが DB件数=100
        mock_count_result = mocker.MagicMock()
        mock_count_result.count = 100  # 不一致

        mock_sample_result = mocker.MagicMock()
        mock_sample_result.data = [{"episode_id": "EP001", "person_name": "Test", "super_total_score": 50}]

        mock_table = mocker.MagicMock()

        def select_side_effect(*_args, **kwargs):
            mock_select = mocker.MagicMock()
            if "head" in kwargs and kwargs["head"]:
                mock_select.execute.return_value = mock_count_result
            else:
                mock_in = mocker.MagicMock()
                mock_in.execute.return_value = mock_sample_result
                mock_select.in_.return_value = mock_in
            return mock_select

        mock_table.select.side_effect = select_side_effect
        mock_client.table.return_value = mock_table

        with caplog.at_level(logging.ERROR):
            error_count = migrate(dry_run=False)

        # 件数不一致エラーがログに出力されていること
        assert "Count mismatch" in caplog.text
        # S-6: 件数不一致がerror_countに反映されていること
        assert error_count >= 1


class TestUpsertBatchRetry:
    """upsert_batchのリトライ動作テスト（PRレビューH-3対応）"""

    def test_upsert_batch_retry_on_api_error(self, mocker):
        """APIError発生時にリトライが実行される"""
        from migrate_csv_to_supabase import upsert_batch
        from postgrest.exceptions import APIError

        mock_client = mocker.MagicMock()

        # 1回目: APIError、2回目: 成功
        mock_success_result = mocker.MagicMock()
        mock_success_result.data = [{"episode_id": "1"}]

        mock_table = mocker.MagicMock()
        mock_upsert = mocker.MagicMock()
        mock_table.upsert.return_value = mock_upsert
        mock_upsert.execute.side_effect = [
            APIError({"message": "timeout"}),  # 1回目失敗
            mock_success_result,  # 2回目成功
        ]
        mock_client.table.return_value = mock_table

        result = upsert_batch(mock_client, [{"episode_id": "1"}])

        # リトライ後に成功
        assert result["success_count"] == 1
        assert mock_upsert.execute.call_count == 2

    def test_upsert_batch_max_retries_exceeded(self, mocker):
        """最大リトライ回数超過時にRetryErrorが発生"""
        from migrate_csv_to_supabase import upsert_batch
        from postgrest.exceptions import APIError
        from tenacity import RetryError

        mock_client = mocker.MagicMock()

        # 3回連続でAPIError
        mock_table = mocker.MagicMock()
        mock_upsert = mocker.MagicMock()
        mock_table.upsert.return_value = mock_upsert
        mock_upsert.execute.side_effect = APIError({"message": "persistent error"})
        mock_client.table.return_value = mock_table

        with pytest.raises(RetryError):
            upsert_batch(mock_client, [{"episode_id": "1"}])

        # 3回リトライされた
        assert mock_upsert.execute.call_count == 3


class TestMigrateSampleVerification:
    """migrate関数のサンプル検証テスト（PRレビューW-2対応）"""

    def test_migrate_sample_verification_handles_api_error(self, mocker, tmp_path, caplog):
        """サンプル検証でAPIError発生時にログ出力される"""
        from migrate_csv_to_supabase import migrate
        from postgrest.exceptions import APIError
        import migrate_csv_to_supabase

        csv_path = tmp_path / "preserved" / "data"
        csv_path.mkdir(parents=True)
        csv_file = csv_path / "MASTER_EPISODES_CURRENT.csv"
        csv_file.write_text("episode_id,person_name,age\n1,Test,30", encoding="utf-8-sig")

        mocker.patch.object(migrate_csv_to_supabase, "PROJECT_ROOT", tmp_path)

        mock_client = mocker.MagicMock()
        mocker.patch.object(migrate_csv_to_supabase, "get_supabase_client", return_value=mock_client)

        # upsert_batchは成功
        mock_upsert_result = {"success_count": 1, "data": [{"episode_id": "1"}]}
        mocker.patch.object(migrate_csv_to_supabase, "upsert_batch", return_value=mock_upsert_result)

        # 件数確認は成功
        mock_count_result = mocker.MagicMock()
        mock_count_result.count = 1

        # サンプル検証でAPIError（selectクエリ）
        mock_sample_error = APIError({"message": "sample query failed"})
        mock_table = mocker.MagicMock()

        # select().execute() for count (head=True)
        mock_count_select = mocker.MagicMock()
        mock_count_select.execute.return_value = mock_count_result

        # select().in_().execute() for sample verification
        mock_sample_select = mocker.MagicMock()
        mock_sample_in = mocker.MagicMock()
        mock_sample_in.execute.side_effect = mock_sample_error
        mock_sample_select.in_.return_value = mock_sample_in

        # 呼び出しを区別するためにside_effectでリストを使う
        def select_side_effect(*_args, **kwargs):
            if "head" in kwargs and kwargs["head"]:
                return mock_count_select
            return mock_sample_select

        mock_table.select.side_effect = select_side_effect
        mock_client.table.return_value = mock_table

        with caplog.at_level(logging.ERROR):
            migrate(dry_run=False)

        assert "Sample verification failed" in caplog.text


class TestMigratePartialSuccess:
    """migrate関数の部分成功テスト（PRレビューH-1対応）"""

    def test_migrate_partial_success_tracks_failed_records(self, mocker, tmp_path, caplog):
        """部分成功時に失敗したepisode_idがfailed_recordsに追跡される"""
        from migrate_csv_to_supabase import migrate
        import migrate_csv_to_supabase

        csv_path = tmp_path / "preserved" / "data"
        csv_path.mkdir(parents=True)
        csv_file = csv_path / "MASTER_EPISODES_CURRENT.csv"
        # 2件のレコード
        csv_file.write_text("episode_id,person_name,age\nEP001,Test1,30\nEP002,Test2,40", encoding="utf-8-sig")

        mocker.patch.object(migrate_csv_to_supabase, "PROJECT_ROOT", tmp_path)

        mock_client = mocker.MagicMock()
        mocker.patch.object(migrate_csv_to_supabase, "get_supabase_client", return_value=mock_client)

        # 部分成功: 2件中1件のみ成功
        mock_upsert_result = {"success_count": 1, "data": [{"episode_id": "EP001"}]}
        mocker.patch.object(migrate_csv_to_supabase, "upsert_batch", return_value=mock_upsert_result)

        # 検証クエリをモック
        mock_count_result = mocker.MagicMock()
        mock_count_result.count = 1
        mock_sample_result = mocker.MagicMock()
        mock_sample_result.data = [{"episode_id": "EP001", "person_name": "Test1", "super_total_score": 100}]

        mock_table = mocker.MagicMock()

        def select_side_effect(*_args, **kwargs):
            mock_select = mocker.MagicMock()
            if "head" in kwargs and kwargs["head"]:
                mock_select.execute.return_value = mock_count_result
            else:
                mock_in = mocker.MagicMock()
                mock_in.execute.return_value = mock_sample_result
                mock_select.in_.return_value = mock_in
            return mock_select

        mock_table.select.side_effect = select_side_effect
        mock_client.table.return_value = mock_table

        with caplog.at_level(logging.WARNING):
            migrate(dry_run=False, batch_size=500)

        # 部分成功の警告ログが出力されていること
        assert "Partial success" in caplog.text
        # 失敗したepisode_idがログに含まれていること
        assert "EP002" in caplog.text


class TestSanitizeValueComplexObjects:
    """sanitize_valueの複合オブジェクト処理テスト（PRレビューH-2対応）"""

    def test_dict_returns_none(self):
        """dict型はNoneに変換される"""
        from migrate_csv_to_supabase import sanitize_value

        result = sanitize_value({"key": "value"}, column_name="test_col")
        assert result is None

    def test_list_returns_none(self):
        """list型はNoneに変換される"""
        from migrate_csv_to_supabase import sanitize_value

        result = sanitize_value([1, 2, 3], column_name="test_col")
        assert result is None

    def test_set_returns_none(self):
        """set型はNoneに変換される"""
        from migrate_csv_to_supabase import sanitize_value

        result = sanitize_value({1, 2, 3}, column_name="test_col")
        assert result is None

    def test_tuple_returns_none(self):
        """tuple型はNoneに変換される"""
        from migrate_csv_to_supabase import sanitize_value

        result = sanitize_value((1, 2, 3), column_name="test_col")
        assert result is None

    def test_dict_logs_warning(self, caplog):
        """dict型変換時に警告ログが出力される"""
        from migrate_csv_to_supabase import sanitize_value

        with caplog.at_level(logging.WARNING):
            sanitize_value({"key": "value"}, column_name="test_col")

        assert "Complex object detected" in caplog.text
        assert "test_col" in caplog.text
        assert "dict" in caplog.text
