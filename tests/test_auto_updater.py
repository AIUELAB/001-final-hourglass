"""
AutoUpdater テストモジュール

auto_updater.py の単体テストを提供します。
"""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock
import pandas as pd

from src.auto_updater import AutoUpdater


@pytest.fixture
def mock_cache_manager():
    """モックキャッシュマネージャー"""
    with patch("src.auto_updater.CacheManager") as mock:
        instance = MagicMock()
        mock.return_value = instance
        yield instance


@pytest.fixture
def mock_google_api():
    """Google API モック"""
    with patch("src.auto_updater.service_account") as mock_sa, patch("src.auto_updater.build") as mock_build:
        mock_credentials = MagicMock()
        mock_sa.Credentials.from_service_account_file.return_value = mock_credentials

        mock_service = MagicMock()
        mock_build.return_value = mock_service

        yield {
            "service_account": mock_sa,
            "build": mock_build,
            "service": mock_service,
        }


@pytest.fixture
def updater_no_credentials(mock_cache_manager, tmp_path):
    """認証ファイルなしのUpdater"""
    non_existent = tmp_path / "non_existent.json"
    return AutoUpdater(credentials_path=str(non_existent))


@pytest.fixture
def updater_with_mock_api(mock_cache_manager, mock_google_api, tmp_path):
    """モックAPI付きUpdater"""
    credentials_file = tmp_path / "credentials.json"
    credentials_file.write_text('{"type": "service_account"}')
    return AutoUpdater(credentials_path=str(credentials_file))


class TestAutoUpdaterInit:
    """初期化テスト"""

    def test_init_without_credentials(self, updater_no_credentials):
        """認証ファイルなしで初期化"""
        assert updater_no_credentials.service is None
        assert updater_no_credentials.config["atomic_update"] is True
        assert updater_no_credentials.config["retry_count"] == 3

    def test_init_with_credentials(self, updater_with_mock_api, mock_google_api):
        """認証ファイルありで初期化"""
        assert updater_with_mock_api.service is not None
        mock_google_api["build"].assert_called_once()

    def test_default_config(self, updater_no_credentials):
        """デフォルト設定が正しい"""
        config = updater_no_credentials.config
        assert config["atomic_update"] is True
        assert config["batch_size"] == 10000
        assert config["retry_count"] == 3
        assert config["retry_delay"] == [1, 2, 4]
        assert config["backup_before_update"] is True
        assert config["verify_after_update"] is True

    def test_update_history_initialized(self, updater_no_credentials):
        """更新履歴が初期化される"""
        assert updater_no_credentials.update_history == []


class TestPrepareRowsData:
    """_prepare_rows_data メソッドのテスト"""

    def test_prepare_string_values(self, updater_no_credentials):
        """文字列値の準備"""
        values = [["header1", "header2"], ["value1", "value2"]]
        rows = updater_no_credentials._prepare_rows_data(values)

        assert len(rows) == 2
        assert rows[0]["values"][0]["userEnteredValue"]["stringValue"] == "header1"
        assert rows[1]["values"][0]["userEnteredValue"]["stringValue"] == "value1"

    def test_prepare_numeric_values(self, updater_no_credentials):
        """数値の準備"""
        values = [[1, 2.5, 3]]
        rows = updater_no_credentials._prepare_rows_data(values)

        assert rows[0]["values"][0]["userEnteredValue"]["numberValue"] == 1.0
        assert rows[0]["values"][1]["userEnteredValue"]["numberValue"] == 2.5
        assert rows[0]["values"][2]["userEnteredValue"]["numberValue"] == 3.0

    def test_prepare_boolean_values(self, updater_no_credentials):
        """ブール値の準備（PythonではboolはintのサブクラスなのでnumberValueになる）"""
        values = [[True, False]]
        rows = updater_no_credentials._prepare_rows_data(values)

        # bool is subclass of int in Python, so it becomes numberValue
        assert rows[0]["values"][0]["userEnteredValue"]["numberValue"] == 1.0
        assert rows[0]["values"][1]["userEnteredValue"]["numberValue"] == 0.0

    def test_prepare_mixed_values(self, updater_no_credentials):
        """混合値の準備"""
        values = [["text", 123, "boolean_text", 45.6]]
        rows = updater_no_credentials._prepare_rows_data(values)

        assert rows[0]["values"][0]["userEnteredValue"]["stringValue"] == "text"
        assert rows[0]["values"][1]["userEnteredValue"]["numberValue"] == 123.0
        assert rows[0]["values"][2]["userEnteredValue"]["stringValue"] == "boolean_text"
        assert rows[0]["values"][3]["userEnteredValue"]["numberValue"] == 45.6


class TestCreateFormatRequests:
    """_create_format_requests メソッドのテスト"""

    def test_creates_header_format(self, updater_no_credentials):
        """ヘッダーフォーマットを作成"""
        requests = updater_no_credentials._create_format_requests(sheet_id=0, row_count=10, col_count=5)

        # ヘッダー、列幅、フィルターの3つのリクエスト
        assert len(requests) == 3

        # ヘッダーフォーマット
        header_req = requests[0]
        assert "repeatCell" in header_req
        assert header_req["repeatCell"]["range"]["endRowIndex"] == 1

    def test_creates_auto_resize(self, updater_no_credentials):
        """列幅自動調整を作成"""
        requests = updater_no_credentials._create_format_requests(sheet_id=0, row_count=10, col_count=5)

        auto_resize = requests[1]
        assert "autoResizeDimensions" in auto_resize
        assert auto_resize["autoResizeDimensions"]["dimensions"]["endIndex"] == 5

    def test_creates_filter(self, updater_no_credentials):
        """フィルター設定を作成"""
        requests = updater_no_credentials._create_format_requests(sheet_id=0, row_count=10, col_count=5)

        filter_req = requests[2]
        assert "setBasicFilter" in filter_req
        assert filter_req["setBasicFilter"]["filter"]["range"]["endRowIndex"] == 10


class TestGetSheetId:
    """_get_sheet_id メソッドのテスト"""

    def test_get_sheet_id_found(self, updater_with_mock_api, mock_google_api):
        """シートIDを取得"""
        mock_spreadsheet = {
            "sheets": [
                {"properties": {"title": "Sheet1", "sheetId": 123}},
                {"properties": {"title": "Sheet2", "sheetId": 456}},
            ]
        }
        mock_google_api["service"].spreadsheets().get().execute.return_value = mock_spreadsheet

        sheet_id = updater_with_mock_api._get_sheet_id("spreadsheet_id", "Sheet2")
        assert sheet_id == 456

    def test_get_sheet_id_not_found_uses_first(self, updater_with_mock_api, mock_google_api):
        """シートが見つからない場合は最初のシートを使用"""
        mock_spreadsheet = {
            "sheets": [
                {"properties": {"title": "Sheet1", "sheetId": 123}},
            ]
        }
        mock_google_api["service"].spreadsheets().get().execute.return_value = mock_spreadsheet

        sheet_id = updater_with_mock_api._get_sheet_id("spreadsheet_id", "NonExistent")
        assert sheet_id == 123

    def test_get_sheet_id_error(self, updater_with_mock_api, mock_google_api):
        """エラー時は0を返す"""
        mock_google_api["service"].spreadsheets().get().execute.side_effect = Exception("API Error")

        sheet_id = updater_with_mock_api._get_sheet_id("spreadsheet_id", "Sheet1")
        assert sheet_id == 0


class TestRecordUpdateHistory:
    """_record_update_history メソッドのテスト"""

    def test_records_history(self, updater_no_credentials, tmp_path):
        """履歴を記録"""
        # ログディレクトリを一時ディレクトリに変更
        with patch.object(Path, "parent", new_callable=PropertyMock) as mock_parent:
            mock_parent.return_value = tmp_path

            result = {
                "rows_updated": 100,
                "time_taken": 1.5,
                "success": True,
                "cache_cleared": True,
            }

            updater_no_credentials._record_update_history("spreadsheet_id", "sheet_name", result)

            assert len(updater_no_credentials.update_history) == 1
            assert updater_no_credentials.update_history[0]["rows_updated"] == 100
            assert updater_no_credentials.update_history[0]["success"] is True

    def test_history_limit(self, updater_no_credentials):
        """履歴は50件まで"""
        # 60件追加
        for i in range(60):
            updater_no_credentials.update_history.append({"index": i})

        result = {"rows_updated": 1, "success": True}

        with patch("builtins.open", MagicMock()):
            with patch.object(Path, "mkdir"):
                updater_no_credentials._record_update_history("spreadsheet_id", "sheet_name", result)

        # 50件に制限される
        assert len(updater_no_credentials.update_history) <= 51


class TestGetUpdateStats:
    """get_update_stats メソッドのテスト"""

    def test_no_history(self, updater_no_credentials):
        """履歴なしの場合"""
        stats = updater_no_credentials.get_update_stats()
        assert stats["message"] == "更新履歴なし"

    def test_with_history(self, updater_no_credentials):
        """履歴ありの場合"""
        updater_no_credentials.update_history = [
            {"success": True, "rows_updated": 100, "time_taken": 1.0, "timestamp": "2025-01-01T00:00:00"},
            {"success": True, "rows_updated": 200, "time_taken": 2.0, "timestamp": "2025-01-02T00:00:00"},
            {"success": False, "rows_updated": 0, "time_taken": 0.5, "timestamp": "2025-01-03T00:00:00"},
        ]

        stats = updater_no_credentials.get_update_stats()

        assert stats["total_updates"] == 3
        assert stats["successful_updates"] == 2
        assert stats["success_rate"] == "66.7%"
        assert stats["total_rows_updated"] == 300
        assert stats["average_time_seconds"] == 1.17  # (1+2+0.5)/3


class TestUpdateWithRetry:
    """update_with_retry メソッドのテスト"""

    def test_success_on_first_try(self, updater_with_mock_api):
        """初回成功"""
        with patch.object(updater_with_mock_api, "atomic_sheet_update") as mock_update:
            mock_update.return_value = (True, {"success": True, "rows_updated": 10})

            df = pd.DataFrame({"col1": [1, 2, 3]})
            success, result = updater_with_mock_api.update_with_retry("spreadsheet_id", "sheet_name", df)

            assert success is True
            mock_update.assert_called_once()

    def test_success_after_retry(self, updater_with_mock_api):
        """リトライ後成功"""
        with patch.object(updater_with_mock_api, "atomic_sheet_update") as mock_update:
            mock_update.side_effect = [
                (False, {"error": "First attempt failed"}),
                (True, {"success": True, "rows_updated": 10}),
            ]

            with patch("time.sleep"):  # 待機をスキップ
                df = pd.DataFrame({"col1": [1, 2, 3]})
                success, result = updater_with_mock_api.update_with_retry("spreadsheet_id", "sheet_name", df)

            assert success is True
            assert mock_update.call_count == 2

    def test_fail_after_all_retries(self, updater_with_mock_api):
        """全リトライ失敗"""
        with patch.object(updater_with_mock_api, "atomic_sheet_update") as mock_update:
            mock_update.return_value = (False, {"error": "Failed"})

            with patch("time.sleep"):  # 待機をスキップ
                df = pd.DataFrame({"col1": [1, 2, 3]})
                success, result = updater_with_mock_api.update_with_retry("spreadsheet_id", "sheet_name", df)

            assert success is False
            assert "最大リトライ" in result["error"]
            assert mock_update.call_count == 3


class TestAtomicSheetUpdate:
    """atomic_sheet_update メソッドのテスト"""

    def test_clears_cache_when_requested(self, updater_with_mock_api, mock_cache_manager):
        """キャッシュクリアが要求される"""
        with patch.object(updater_with_mock_api, "_get_sheet_id", return_value=0):
            with patch.object(updater_with_mock_api, "_prepare_rows_data", return_value=[]):
                with patch.object(updater_with_mock_api, "_create_format_requests", return_value=[]):
                    df = pd.DataFrame({"col1": [1, 2, 3]})
                    updater_with_mock_api.atomic_sheet_update("spreadsheet_id", "sheet_name", df, clear_cache=True)

        mock_cache_manager.purge_all_cache.assert_called_once()

    def test_handles_exception(self, updater_with_mock_api):
        """例外処理"""
        # _get_sheet_idで例外を発生させる
        with patch.object(updater_with_mock_api, "_get_sheet_id", side_effect=Exception("API Error")):
            df = pd.DataFrame({"col1": [1, 2, 3]})
            success, result = updater_with_mock_api.atomic_sheet_update("spreadsheet_id", "sheet_name", df)

        assert success is False
        assert result["error"] is not None
