"""
SafeCSVWriter Supabase同期機能のユニットテスト

テスト対象: scripts/sage/persistence/csv_writer.py の Supabase同期関連メソッド
- _sanitize_for_supabase(row)
- _get_supabase_client()
- _upsert_batch(supabase, batch)
- _sync_to_supabase(new_rows)
- write() / replace_episode() の Supabase同期部分
"""

# === 標準ライブラリ ===
import logging
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

# === サードパーティ ===
import httpx
import numpy as np
import pandas as pd
import pytest
from postgrest.exceptions import APIError
from tenacity import RetryError

# === ローカル ===
from scripts.sage.persistence.csv_writer import SafeCSVWriter


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_supabase_client(mocker):
    """Supabaseクライアントのモック"""
    mock_client = mocker.MagicMock()
    mock_result = mocker.MagicMock()
    mock_result.data = [{"episode_id": "1"}]
    mock_client.table.return_value.upsert.return_value.execute.return_value = mock_result
    return mock_client


@pytest.fixture
def csv_writer(tmp_path):
    """テスト用SafeCSVWriter"""
    csv_path = tmp_path / "test_episodes.csv"
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    # ヘッダー付きCSVを作成
    csv_path.write_text(
        "episode_id,person_id,person_name,age,episode_text,category,person_type\n",
        encoding="utf-8-sig",
    )
    return SafeCSVWriter(master_csv=csv_path, logs_dir=logs_dir)


@pytest.fixture
def sample_row():
    """テスト用サンプル行"""
    return {
        "episode_id": "EP-001",
        "person_id": "P001",
        "person_name": "Test Person",
        "age": 30,
        "episode_text": "This is a test episode text." * 10,
        "category": "test",
        "person_type": "REAL",
    }


# ============================================================================
# TestSanitizeForSupabase (18 cases)
# ============================================================================


class TestSanitizeForSupabase:
    """_sanitize_for_supabase(row) のテスト"""

    def test_none_value(self, csv_writer):
        """None値はNoneのまま"""
        row = {"field": None}
        result = csv_writer._sanitize_for_supabase(row)
        assert result["field"] is None

    def test_pandas_na(self, csv_writer):
        """pd.NAはNoneに変換"""
        row = {"field": pd.NA}
        result = csv_writer._sanitize_for_supabase(row)
        assert result["field"] is None

    def test_pandas_nat(self, csv_writer):
        """pd.NaTはNoneに変換"""
        row = {"field": pd.NaT}
        result = csv_writer._sanitize_for_supabase(row)
        assert result["field"] is None

    def test_float_nan(self, csv_writer):
        """float('nan')はNoneに変換"""
        row = {"field": float("nan")}
        result = csv_writer._sanitize_for_supabase(row)
        assert result["field"] is None

    def test_float_inf(self, csv_writer):
        """float('inf')はNoneに変換される（PRレビュー#14修正後）"""
        # float('inf')はJSONでシリアライズできないためNoneに変換
        row = {"field": float("inf")}
        result = csv_writer._sanitize_for_supabase(row)
        assert result["field"] is None

        # 負のfloat('-inf')もNoneに変換
        row_neg_float = {"field": float("-inf")}
        result_neg_float = csv_writer._sanitize_for_supabase(row_neg_float)
        assert result_neg_float["field"] is None

        # np.float64のinfもNoneに変換される
        row_np = {"field": np.float64("inf")}
        result_np = csv_writer._sanitize_for_supabase(row_np)
        assert result_np["field"] is None

        # 負のinfも確認（np.float64）
        row_neg = {"field": np.float64("-inf")}
        result_neg = csv_writer._sanitize_for_supabase(row_neg)
        assert result_neg["field"] is None

    def test_numpy_integer(self, csv_writer):
        """np.int64はPython intに変換"""
        row = {"field": np.int64(42)}
        result = csv_writer._sanitize_for_supabase(row)
        assert result["field"] == 42
        assert isinstance(result["field"], int)

    def test_numpy_floating(self, csv_writer):
        """np.float64はPython floatに変換"""
        row = {"field": np.float64(3.14)}
        result = csv_writer._sanitize_for_supabase(row)
        assert result["field"] == 3.14
        assert isinstance(result["field"], float)

    def test_numpy_floating_nan(self, csv_writer):
        """np.float64('nan')はNoneに変換"""
        row = {"field": np.float64("nan")}
        result = csv_writer._sanitize_for_supabase(row)
        assert result["field"] is None

    def test_numpy_bool(self, csv_writer):
        """np.bool_はPython boolに変換"""
        row = {"field_true": np.bool_(True), "field_false": np.bool_(False)}
        result = csv_writer._sanitize_for_supabase(row)
        assert result["field_true"] is True
        assert result["field_false"] is False

    def test_numpy_str(self, csv_writer):
        """np.str_はPython strに変換"""
        row = {"field": np.str_("text")}
        result = csv_writer._sanitize_for_supabase(row)
        assert result["field"] == "text"
        assert isinstance(result["field"], str)

    def test_numpy_ndarray_logs_warning(self, csv_writer, caplog):
        """np.arrayはNoneに変換され警告ログが出力される"""
        row = {"field": np.array([1, 2, 3])}
        with caplog.at_level(logging.WARNING):
            result = csv_writer._sanitize_for_supabase(row)
        assert result["field"] is None
        assert "配列型は未サポート" in caplog.text

    def test_integer_columns_float_to_int(self, csv_writer):
        """INTEGER_COLUMNSのfloat値はintに変換"""
        row = {"age": 25.0, "birth_year": 1990.0}
        result = csv_writer._sanitize_for_supabase(row)
        assert result["age"] == 25
        assert isinstance(result["age"], int)
        assert result["birth_year"] == 1990
        assert isinstance(result["birth_year"], int)

    def test_integer_columns_string_to_int(self, csv_writer):
        """INTEGER_COLUMNSの文字列数値はintに変換"""
        row = {"age": "30", "birth_year": "1985"}
        result = csv_writer._sanitize_for_supabase(row)
        assert result["age"] == 30
        assert isinstance(result["age"], int)
        assert result["birth_year"] == 1985

    def test_integer_columns_invalid_to_none(self, csv_writer, caplog):
        """INTEGER_COLUMNSの無効値はNoneに変換"""
        row = {"age": "invalid", "birth_year": "not_a_number"}
        with caplog.at_level(logging.DEBUG):
            result = csv_writer._sanitize_for_supabase(row)
        assert result["age"] is None
        assert result["birth_year"] is None

    def test_normal_string_unchanged(self, csv_writer):
        """通常の文字列はそのまま"""
        row = {"person_name": "Test Person", "episode_text": "Normal text content."}
        result = csv_writer._sanitize_for_supabase(row)
        assert result["person_name"] == "Test Person"
        assert result["episode_text"] == "Normal text content."

    def test_empty_string_unchanged(self, csv_writer):
        """空文字列はそのまま保持"""
        row = {"field": ""}
        result = csv_writer._sanitize_for_supabase(row)
        assert result["field"] == ""

    def test_dict_value_unchanged(self, csv_writer):
        """dict値はそのまま保持"""
        row = {"metadata": {"key": "value"}}
        result = csv_writer._sanitize_for_supabase(row)
        assert result["metadata"] == {"key": "value"}

    def test_list_value_unchanged(self, csv_writer):
        """list値はそのまま保持"""
        row = {"tags": ["a", "b"]}
        result = csv_writer._sanitize_for_supabase(row)
        assert result["tags"] == ["a", "b"]


# ============================================================================
# TestGetSupabaseClient (5 cases)
# ============================================================================


class TestGetSupabaseClient:
    """_get_supabase_client() のテスト"""

    def test_both_env_vars_missing_returns_none(self, csv_writer, monkeypatch, caplog):
        """両方の環境変数未設定時はNoneを返す"""
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)

        with caplog.at_level(logging.DEBUG):
            result = csv_writer._get_supabase_client()

        assert result is None
        assert "環境変数未設定" in caplog.text

    def test_url_missing_returns_none_with_warning(self, csv_writer, monkeypatch, caplog):
        """SUPABASE_URL未設定時はNone + WARNING"""
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-key")

        with caplog.at_level(logging.WARNING):
            result = csv_writer._get_supabase_client()

        assert result is None
        assert "SUPABASE_URL未設定" in caplog.text

    def test_key_missing_returns_none_with_warning(self, csv_writer, monkeypatch, caplog):
        """SUPABASE_SERVICE_ROLE_KEY未設定時はNone + WARNING"""
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)

        with caplog.at_level(logging.WARNING):
            result = csv_writer._get_supabase_client()

        assert result is None
        assert "SUPABASE_SERVICE_ROLE_KEY未設定" in caplog.text

    def test_both_env_vars_set_returns_client(self, csv_writer, monkeypatch, mocker):
        """両方の環境変数設定時はクライアントを返す"""
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-key")

        mock_client = mocker.MagicMock()
        mocker.patch(
            "scripts.sage.persistence.csv_writer.create_client",
            return_value=mock_client,
        )

        result = csv_writer._get_supabase_client()

        assert result is mock_client

    def test_create_client_exception_returns_none(self, csv_writer, monkeypatch, mocker, caplog):
        """create_client例外時はNoneを返す"""
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-key")

        mocker.patch(
            "scripts.sage.persistence.csv_writer.create_client",
            side_effect=Exception("Connection failed"),
        )

        with caplog.at_level(logging.ERROR):
            result = csv_writer._get_supabase_client()

        assert result is None
        assert "Supabaseクライアント作成失敗" in caplog.text


# ============================================================================
# TestUpsertBatch (7 cases)
# ============================================================================


class TestUpsertBatch:
    """@retry付き_upsert_batch(supabase, batch) のテスト"""

    def test_successful_upsert(self, csv_writer, mock_supabase_client):
        """正常upsert"""
        batch = [{"episode_id": "1"}, {"episode_id": "2"}]
        mock_supabase_client.table.return_value.upsert.return_value.execute.return_value.data = batch

        result = csv_writer._upsert_batch(mock_supabase_client, batch)

        assert result == 2
        mock_supabase_client.table.assert_called_with("episodes")

    def test_api_error_retry_then_success(self, csv_writer, mocker):
        """APIError後リトライ成功"""
        mock_client = mocker.MagicMock()
        mock_result = mocker.MagicMock()
        mock_result.data = [{"episode_id": "1"}]

        # 1回目: APIError, 2回目: 成功
        mock_client.table.return_value.upsert.return_value.execute.side_effect = [
            APIError({"message": "temporary error"}),
            mock_result,
        ]

        result = csv_writer._upsert_batch(mock_client, [{"episode_id": "1"}])

        assert result == 1
        assert mock_client.table.return_value.upsert.return_value.execute.call_count == 2

    def test_connection_error_triggers_retry(self, csv_writer, mocker):
        """ConnectionErrorでリトライ"""
        mock_client = mocker.MagicMock()
        mock_result = mocker.MagicMock()
        mock_result.data = [{"episode_id": "1"}]

        mock_client.table.return_value.upsert.return_value.execute.side_effect = [
            ConnectionError("Network error"),
            mock_result,
        ]

        result = csv_writer._upsert_batch(mock_client, [{"episode_id": "1"}])

        assert result == 1
        assert mock_client.table.return_value.upsert.return_value.execute.call_count == 2

    def test_timeout_error_triggers_retry(self, csv_writer, mocker):
        """TimeoutErrorでリトライ"""
        mock_client = mocker.MagicMock()
        mock_result = mocker.MagicMock()
        mock_result.data = [{"episode_id": "1"}]

        mock_client.table.return_value.upsert.return_value.execute.side_effect = [
            TimeoutError("Request timed out"),
            mock_result,
        ]

        result = csv_writer._upsert_batch(mock_client, [{"episode_id": "1"}])

        assert result == 1
        assert mock_client.table.return_value.upsert.return_value.execute.call_count == 2

    def test_max_retries_exceeded_raises(self, csv_writer, mocker):
        """3回失敗でRetryError"""
        mock_client = mocker.MagicMock()

        # 3回連続でAPIError
        mock_client.table.return_value.upsert.return_value.execute.side_effect = APIError(
            {"message": "persistent error"}
        )

        with pytest.raises(RetryError):
            csv_writer._upsert_batch(mock_client, [{"episode_id": "1"}])

        assert mock_client.table.return_value.upsert.return_value.execute.call_count == 3

    def test_empty_data_returns_zero(self, csv_writer, mocker):
        """空データの場合は0を返す"""
        mock_client = mocker.MagicMock()
        mock_result = mocker.MagicMock()
        mock_result.data = None  # 空結果

        mock_client.table.return_value.upsert.return_value.execute.return_value = mock_result

        result = csv_writer._upsert_batch(mock_client, [{"episode_id": "1"}])

        assert result == 0

    def test_http_status_error_triggers_retry(self, csv_writer, mocker):
        """httpx.HTTPStatusErrorでリトライ"""
        mock_client = mocker.MagicMock()
        mock_result = mocker.MagicMock()
        mock_result.data = [{"episode_id": "1"}]
        mock_response = mocker.MagicMock()
        mock_response.status_code = 503
        mock_client.table.return_value.upsert.return_value.execute.side_effect = [
            httpx.HTTPStatusError("Service Unavailable", request=mocker.MagicMock(), response=mock_response),
            mock_result,
        ]
        result = csv_writer._upsert_batch(mock_client, [{"episode_id": "1"}])
        assert result == 1
        assert mock_client.table.return_value.upsert.return_value.execute.call_count == 2


# ============================================================================
# TestSyncToSupabase (8 cases)
# ============================================================================


class TestSyncToSupabase:
    """_sync_to_supabase(new_rows) のテスト"""

    def test_empty_list_returns_true_zero(self, csv_writer):
        """空リストは(True, 0)を返す"""
        result = csv_writer._sync_to_supabase([])
        assert result == (True, 0)

    def test_no_client_returns_false_zero(self, csv_writer, monkeypatch, caplog):
        """クライアントなしは(False, 0)を返す"""
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)

        with caplog.at_level(logging.WARNING):
            result = csv_writer._sync_to_supabase([{"episode_id": "1"}])

        assert result == (False, 0)
        assert "環境変数未設定" in caplog.text

    def test_sanitize_error_returns_false_zero(self, csv_writer, mocker, caplog):
        """サニタイズ例外は(False, 0)を返す"""
        mock_client = mocker.MagicMock()
        mocker.patch.object(csv_writer, "_get_supabase_client", return_value=mock_client)

        # _sanitize_for_supabaseで例外を発生させる
        mocker.patch.object(
            csv_writer,
            "_sanitize_for_supabase",
            side_effect=Exception("Sanitize failed"),
        )

        with caplog.at_level(logging.ERROR):
            result = csv_writer._sync_to_supabase([{"episode_id": "1"}])

        assert result == (False, 0)
        assert "データ変換中に予期しないエラー" in caplog.text

    def test_single_batch_success(self, csv_writer, mocker, caplog):
        """単一バッチ成功"""
        mock_client = mocker.MagicMock()
        mocker.patch.object(csv_writer, "_get_supabase_client", return_value=mock_client)

        # _upsert_batchをモック
        mocker.patch.object(csv_writer, "_upsert_batch", return_value=3)

        rows = [{"episode_id": f"EP-{i}"} for i in range(3)]

        with caplog.at_level(logging.INFO):
            result = csv_writer._sync_to_supabase(rows)

        assert result == (True, 3)
        assert "Supabase同期完了" in caplog.text

    def test_multiple_batches_success(self, csv_writer, mocker, caplog):
        """複数バッチ成功"""
        mock_client = mocker.MagicMock()
        mocker.patch.object(csv_writer, "_get_supabase_client", return_value=mock_client)

        # 150件 = 2バッチ（100件バッチサイズ）
        # 各バッチで100件、50件成功
        mocker.patch.object(csv_writer, "_upsert_batch", side_effect=[100, 50])

        rows = [{"episode_id": f"EP-{i}"} for i in range(150)]

        with caplog.at_level(logging.INFO):
            result = csv_writer._sync_to_supabase(rows)

        assert result == (True, 150)
        assert "Supabase同期完了: 150/150件" in caplog.text

    def test_partial_batch_failure(self, csv_writer, mocker, caplog):
        """部分バッチ失敗"""
        mock_client = mocker.MagicMock()
        mocker.patch.object(csv_writer, "_get_supabase_client", return_value=mock_client)

        # 1バッチ目成功、2バッチ目失敗
        mocker.patch.object(
            csv_writer,
            "_upsert_batch",
            side_effect=[100, APIError({"message": "batch 2 failed"})],
        )

        rows = [{"episode_id": f"EP-{i}"} for i in range(150)]

        with caplog.at_level(logging.WARNING):
            result = csv_writer._sync_to_supabase(rows)

        assert result == (False, 100)
        assert "部分成功" in caplog.text

    def test_all_batches_fail(self, csv_writer, mocker, caplog):
        """全バッチ失敗"""
        mock_client = mocker.MagicMock()
        mocker.patch.object(csv_writer, "_get_supabase_client", return_value=mock_client)

        # 全バッチ失敗
        mocker.patch.object(
            csv_writer,
            "_upsert_batch",
            side_effect=APIError({"message": "all batches failed"}),
        )

        rows = [{"episode_id": f"EP-{i}"} for i in range(50)]

        with caplog.at_level(logging.WARNING):
            result = csv_writer._sync_to_supabase(rows)

        assert result == (False, 0)

    def test_exact_batch_size_success(self, csv_writer, mocker, caplog):
        """ちょうど100件（1バッチ）の処理"""
        mock_client = mocker.MagicMock()
        mocker.patch.object(csv_writer, "_get_supabase_client", return_value=mock_client)
        mocker.patch.object(csv_writer, "_upsert_batch", return_value=100)
        rows = [{"episode_id": f"EP-{i}"} for i in range(100)]
        with caplog.at_level(logging.INFO):
            result = csv_writer._sync_to_supabase(rows)
        assert result == (True, 100)
        assert csv_writer._upsert_batch.call_count == 1


# ============================================================================
# TestWriteWithSupabaseSync (4 cases)
# ============================================================================


class TestWriteWithSupabaseSync:
    """write() の Supabase同期部分のテスト"""

    @pytest.fixture
    def mock_generation_result(self, mocker):
        """GenerationResultのモック"""
        result = mocker.MagicMock()
        result.success = True
        result.to_csv_row.return_value = {
            "person_id": "P001",
            "person_name": "Test Person",
            "age": 30,
            "episode_text": "This is a test episode with enough content. " * 10,
            "category": "test",
            "person_type": "REAL",
            "episode_type": "normal",
            "slot": 1,
            "tier": 1,
            "memorability_score": 0.8,
            "empathy_score": 0.7,
            "surprise_score": 0.6,
            "generation_quality_score": 0.85,
            "educational_value": 0.75,
            "story_quality": 0.8,
            "factual_density": 0.7,
            "iconic_score": 0.5,
            "composite_score": 0.75,
            "super_total_score": 100000,
        }
        return result

    @pytest.fixture
    def mock_write_dependencies(self, mocker):
        """write()メソッド用の共通モック設定"""
        mocker.patch(
            "scripts.sage.persistence.csv_writer.create_pre_operation_backup",
            return_value=mocker.MagicMock(path=Path("/tmp/backup")),
        )
        mocker.patch(
            "scripts.sage.persistence.csv_writer.check_fictional_lead_row",
            return_value=(True, ""),
        )
        mocker.patch(
            "scripts.sage.persistence.csv_writer.auto_fill_all_derived_fields",
            side_effect=lambda x: x,
        )
        mocker.patch(
            "scripts.sage.persistence.csv_writer.check_completeness_extended",
            return_value=mocker.MagicMock(passed=True),
        )
        mock_unified_result = mocker.MagicMock()
        mock_unified_result.is_valid = True
        mocker.patch(
            "scripts.sage.persistence.csv_writer.UnifiedGate",
            return_value=mocker.MagicMock(validate=mocker.MagicMock(return_value=mock_unified_result)),
        )

    def test_supabase_sync_success(self, csv_writer, mock_generation_result, mock_write_dependencies, mocker, caplog):
        """同期成功"""
        _ = mock_write_dependencies  # fixture適用
        # Supabase同期をモック
        mocker.patch.object(csv_writer, "_sync_to_supabase", return_value=(True, 1))

        with caplog.at_level(logging.INFO):
            result = csv_writer.write([mock_generation_result])

        assert result.success is True
        assert result.supabase_synced is True
        assert result.supabase_sync_count == 1

    def test_supabase_sync_partial_failure(self, csv_writer, mock_generation_result, mock_write_dependencies, mocker):
        """部分失敗でも全体は成功"""
        _ = mock_write_dependencies  # fixture適用
        # 部分成功
        mocker.patch.object(csv_writer, "_sync_to_supabase", return_value=(False, 0))

        result = csv_writer.write([mock_generation_result])

        assert result.success is True  # CSV書き込みは成功
        assert result.supabase_synced is False
        assert result.supabase_sync_count == 0

    def test_supabase_sync_complete_failure(self, csv_writer, mock_generation_result, mock_write_dependencies, mocker):
        """完全失敗でもCSV書き込みは成功"""
        _ = mock_write_dependencies  # fixture適用
        # 完全失敗
        mocker.patch.object(csv_writer, "_sync_to_supabase", return_value=(False, 0))

        result = csv_writer.write([mock_generation_result])

        assert result.success is True  # CSV書き込みは成功
        assert result.added_count == 1

    def test_no_new_rows_no_sync(self, csv_writer, mocker):
        """新規行なしの場合は同期なし"""
        mocker.patch(
            "scripts.sage.persistence.csv_writer.create_pre_operation_backup",
            return_value=mocker.MagicMock(path=Path("/tmp/backup")),
        )

        # 失敗したGenerationResult
        failed_result = mocker.MagicMock()
        failed_result.success = False

        mock_sync = mocker.patch.object(csv_writer, "_sync_to_supabase")

        result = csv_writer.write([failed_result])

        assert result.success is True
        assert result.added_count == 0
        mock_sync.assert_not_called()


# ============================================================================
# TestReplaceEpisodeWithSupabaseSync (3 cases)
# ============================================================================


class TestReplaceEpisodeWithSupabaseSync:
    """replace_episode() の Supabase同期部分のテスト"""

    @pytest.fixture
    def existing_csv(self, tmp_path):
        """既存データを持つCSV"""
        csv_path = tmp_path / "test_episodes.csv"
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        # pandasでCSVを正しく作成
        episode_text = "This is an old episode text that needs to be replaced. " * 5
        df = pd.DataFrame(
            [
                {
                    "episode_id": "EP-OLD-001",
                    "person_id": "P001",
                    "person_name": "Test Person",
                    "age": 30,
                    "episode_text": episode_text,
                    "category": "test",
                    "person_type": "REAL",
                    "super_total_score": 50000,
                }
            ]
        )
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        return SafeCSVWriter(master_csv=csv_path, logs_dir=logs_dir)

    @pytest.fixture
    def new_generation_result(self, mocker):
        """新しいGenerationResult"""
        result = mocker.MagicMock()
        result.success = True
        result.to_csv_row.return_value = {
            "person_id": "P001",
            "person_name": "Test Person",
            "age": 30,
            "episode_text": "This is a new improved episode text. " * 10,
            "category": "test",
            "person_type": "REAL",
            "super_total_score": 100000,
        }
        return result

    @pytest.fixture
    def mock_replace_dependencies(self, mocker):
        """replace_episode()メソッド用の共通モック設定"""
        mocker.patch(
            "scripts.sage.persistence.csv_writer.create_pre_operation_backup",
            return_value=mocker.MagicMock(path=Path("/tmp/backup")),
        )
        mocker.patch(
            "scripts.sage.persistence.csv_writer.check_fictional_lead_row",
            return_value=(True, ""),
        )
        mock_unified_result = mocker.MagicMock()
        mock_unified_result.is_valid = True
        mocker.patch(
            "scripts.sage.persistence.csv_writer.UnifiedGate",
            return_value=mocker.MagicMock(validate=mocker.MagicMock(return_value=mock_unified_result)),
        )

    def test_supabase_sync_success(self, existing_csv, new_generation_result, mock_replace_dependencies, mocker):
        """同期成功"""
        _ = mock_replace_dependencies  # fixture適用
        # Supabase同期成功
        mocker.patch.object(existing_csv, "_sync_to_supabase", return_value=(True, 1))

        result = existing_csv.replace_episode("EP-OLD-001", new_generation_result, dry_run=False)

        assert result.success is True
        assert result.replaced_count == 1
        assert result.supabase_synced is True
        assert result.supabase_sync_count == 1

    def test_supabase_sync_failure(self, existing_csv, new_generation_result, mock_replace_dependencies, mocker):
        """同期失敗でもCSV置換は成功"""
        _ = mock_replace_dependencies  # fixture適用
        # Supabase同期失敗
        mocker.patch.object(existing_csv, "_sync_to_supabase", return_value=(False, 0))

        result = existing_csv.replace_episode("EP-OLD-001", new_generation_result, dry_run=False)

        assert result.success is True  # CSV置換は成功
        assert result.replaced_count == 1
        assert result.supabase_synced is False

    def test_dry_run_no_sync(self, existing_csv, new_generation_result, mocker):
        """dry_run時は同期なし"""
        mocker.patch(
            "scripts.sage.persistence.csv_writer.check_fictional_lead_row",
            return_value=(True, ""),
        )

        mock_unified_result = mocker.MagicMock()
        mock_unified_result.is_valid = True
        mocker.patch(
            "scripts.sage.persistence.csv_writer.UnifiedGate",
            return_value=mocker.MagicMock(validate=mocker.MagicMock(return_value=mock_unified_result)),
        )

        mock_sync = mocker.patch.object(existing_csv, "_sync_to_supabase")

        result = existing_csv.replace_episode("EP-OLD-001", new_generation_result, dry_run=True)

        assert result.success is True
        assert result.replaced_count == 1
        mock_sync.assert_not_called()
