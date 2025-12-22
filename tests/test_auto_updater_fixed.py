"""
tests/test_auto_updater_fixed.py - auto_updater_fixed.py ユニットテスト
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


class TestAutoUpdaterFixedInit:
    """AutoUpdaterFixed初期化テスト"""

    @patch("src.auto_updater_fixed.CacheManager")
    @patch("src.auto_updater_fixed.build")
    @patch("src.auto_updater_fixed.service_account.Credentials.from_service_account_file")
    def test_init_with_credentials(self, mock_creds, mock_build, mock_cache):
        """認証ファイルありで初期化"""
        from src.auto_updater_fixed import AutoUpdaterFixed

        with patch("pathlib.Path.exists", return_value=True):
            updater = AutoUpdaterFixed(credentials_path="key/credentials.json")

        assert updater.service is not None
        assert updater.config["atomic_update"] is True
        mock_cache.assert_called_once()

    @patch("src.auto_updater_fixed.CacheManager")
    @patch("src.auto_updater_fixed.build")
    @patch("src.auto_updater_fixed.service_account.Credentials.from_service_account_file")
    def test_init_without_credentials(self, mock_creds, mock_build, mock_cache):
        """認証ファイルなしで初期化"""
        from src.auto_updater_fixed import AutoUpdaterFixed

        with patch("pathlib.Path.exists", return_value=False):
            updater = AutoUpdaterFixed(credentials_path="nonexistent.json")

        mock_creds.assert_not_called()


class TestPrepareRowsData:
    """_prepare_rows_dataメソッドテスト"""

    @patch("src.auto_updater_fixed.CacheManager")
    @patch("src.auto_updater_fixed.build")
    @patch("src.auto_updater_fixed.service_account.Credentials.from_service_account_file")
    def test_prepare_rows_number(self, mock_creds, mock_build, mock_cache):
        """数値データの準備"""
        from src.auto_updater_fixed import AutoUpdaterFixed

        with patch("pathlib.Path.exists", return_value=False):
            updater = AutoUpdaterFixed()

        values = [[1, 2.5, "text"]]
        result = updater._prepare_rows_data(values)

        assert len(result) == 1
        assert result[0]["values"][0]["userEnteredValue"]["numberValue"] == 1
        assert result[0]["values"][1]["userEnteredValue"]["numberValue"] == 2.5
        assert result[0]["values"][2]["userEnteredValue"]["stringValue"] == "text"

    @patch("src.auto_updater_fixed.CacheManager")
    @patch("src.auto_updater_fixed.build")
    @patch("src.auto_updater_fixed.service_account.Credentials.from_service_account_file")
    def test_prepare_rows_boolean(self, mock_creds, mock_build, mock_cache):
        """ブール値データの準備"""
        from src.auto_updater_fixed import AutoUpdaterFixed

        with patch("pathlib.Path.exists", return_value=False):
            updater = AutoUpdaterFixed()

        values = [[True, False]]
        result = updater._prepare_rows_data(values)

        # boolValueまたはstringValueで確認
        assert len(result) == 1
        assert len(result[0]["values"]) == 2


class TestCreateFormatRequests:
    """_create_format_requestsメソッドテスト"""

    @patch("src.auto_updater_fixed.CacheManager")
    @patch("src.auto_updater_fixed.build")
    @patch("src.auto_updater_fixed.service_account.Credentials.from_service_account_file")
    def test_format_requests(self, mock_creds, mock_build, mock_cache):
        """フォーマットリクエストの作成"""
        from src.auto_updater_fixed import AutoUpdaterFixed

        with patch("pathlib.Path.exists", return_value=False):
            updater = AutoUpdaterFixed()

        requests = updater._create_format_requests(sheet_id=0, row_count=100, col_count=10)

        assert len(requests) == 3  # ヘッダー、フィルター、列幅
        assert "repeatCell" in requests[0]
        assert "setBasicFilter" in requests[1]
        assert "autoResizeDimensions" in requests[2]


class TestAtomicSheetUpdate:
    """atomic_sheet_updateメソッドテスト"""

    @patch("src.auto_updater_fixed.CacheManager")
    @patch("src.auto_updater_fixed.build")
    @patch("src.auto_updater_fixed.service_account.Credentials.from_service_account_file")
    def test_atomic_update_success(self, mock_creds, mock_build, mock_cache):
        """アトミック更新成功"""
        from src.auto_updater_fixed import AutoUpdaterFixed

        mock_service = MagicMock()
        mock_build.return_value = mock_service
        mock_service.spreadsheets.return_value.get.return_value.execute.return_value = {
            "sheets": [{"properties": {"sheetId": 0, "title": "Sheet1"}}]
        }
        mock_service.spreadsheets.return_value.batchUpdate.return_value.execute.return_value = {}

        with patch("pathlib.Path.exists", return_value=True):
            updater = AutoUpdaterFixed()

        df = pd.DataFrame({"col1": [1, 2], "col2": ["a", "b"]})
        success, result = updater.atomic_sheet_update(
            spreadsheet_id="test_id", sheet_name="Sheet1", df=df
        )

        assert success is True
        assert result["rows_updated"] == 3  # ヘッダー + 2行

    @patch("src.auto_updater_fixed.CacheManager")
    @patch("src.auto_updater_fixed.build")
    @patch("src.auto_updater_fixed.service_account.Credentials.from_service_account_file")
    def test_atomic_update_failure(self, mock_creds, mock_build, mock_cache):
        """アトミック更新失敗"""
        from src.auto_updater_fixed import AutoUpdaterFixed

        mock_service = MagicMock()
        mock_build.return_value = mock_service
        # batchUpdateで例外を発生させる
        mock_service.spreadsheets.return_value.get.return_value.execute.return_value = {
            "sheets": [{"properties": {"sheetId": 0, "title": "Sheet1"}}]
        }
        mock_service.spreadsheets.return_value.batchUpdate.return_value.execute.side_effect = Exception(
            "API Error"
        )

        with patch("pathlib.Path.exists", return_value=True):
            updater = AutoUpdaterFixed()

        df = pd.DataFrame({"col1": [1]})
        success, result = updater.atomic_sheet_update(
            spreadsheet_id="test_id", sheet_name="Sheet1", df=df
        )

        assert success is False
        assert "error" in result


class TestGetSheetId:
    """_get_sheet_idメソッドテスト"""

    @patch("src.auto_updater_fixed.CacheManager")
    @patch("src.auto_updater_fixed.build")
    @patch("src.auto_updater_fixed.service_account.Credentials.from_service_account_file")
    def test_get_sheet_id_found(self, mock_creds, mock_build, mock_cache):
        """シートID取得成功"""
        from src.auto_updater_fixed import AutoUpdaterFixed

        mock_service = MagicMock()
        mock_build.return_value = mock_service
        mock_service.spreadsheets.return_value.get.return_value.execute.return_value = {
            "sheets": [
                {"properties": {"sheetId": 123, "title": "MySheet"}},
                {"properties": {"sheetId": 456, "title": "OtherSheet"}},
            ]
        }

        with patch("pathlib.Path.exists", return_value=True):
            updater = AutoUpdaterFixed()

        sheet_id = updater._get_sheet_id("spreadsheet_id", "MySheet")
        assert sheet_id == 123

    @patch("src.auto_updater_fixed.CacheManager")
    @patch("src.auto_updater_fixed.build")
    @patch("src.auto_updater_fixed.service_account.Credentials.from_service_account_file")
    def test_get_sheet_id_not_found(self, mock_creds, mock_build, mock_cache):
        """シートID取得（デフォルト）"""
        from src.auto_updater_fixed import AutoUpdaterFixed

        mock_service = MagicMock()
        mock_build.return_value = mock_service
        mock_service.spreadsheets.return_value.get.return_value.execute.return_value = {
            "sheets": [{"properties": {"sheetId": 999, "title": "Default"}}]
        }

        with patch("pathlib.Path.exists", return_value=True):
            updater = AutoUpdaterFixed()

        sheet_id = updater._get_sheet_id("spreadsheet_id", "NonExistent")
        assert sheet_id == 999  # デフォルトで最初のシート


class TestForceFullReplacement:
    """force_full_replacementメソッドテスト"""

    @patch("src.auto_updater_fixed.CacheManager")
    @patch("src.auto_updater_fixed.build")
    @patch("src.auto_updater_fixed.service_account.Credentials.from_service_account_file")
    def test_full_replacement_success(self, mock_creds, mock_build, mock_cache):
        """完全置換成功"""
        from src.auto_updater_fixed import AutoUpdaterFixed

        mock_service = MagicMock()
        mock_build.return_value = mock_service
        mock_service.spreadsheets.return_value.get.return_value.execute.return_value = {
            "sheets": [{"properties": {"sheetId": 0, "title": "Sheet1"}}]
        }
        mock_service.spreadsheets.return_value.batchUpdate.return_value.execute.return_value = {}

        with patch("pathlib.Path.exists", return_value=True):
            updater = AutoUpdaterFixed()

        df = pd.DataFrame({"col1": [1, 2]})
        success, result = updater.force_full_replacement(
            spreadsheet_id="test_id", df=df, new_sheet_name="NewSheet"
        )

        assert success is True
