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

    def test_atomic_update_without_cache_clear(self, updater_with_mock_api, mock_cache_manager):
        """clear_cache=Falseでキャッシュクリアをスキップ"""
        with patch.object(updater_with_mock_api, "_get_sheet_id", return_value=0):
            with patch.object(updater_with_mock_api, "_prepare_rows_data", return_value=[]):
                with patch.object(updater_with_mock_api, "_create_format_requests", return_value=[]):
                    df = pd.DataFrame({"col1": [1, 2, 3]})
                    updater_with_mock_api.atomic_sheet_update("spreadsheet_id", "sheet_name", df, clear_cache=False)

        # キャッシュクリアが呼ばれない
        mock_cache_manager.purge_all_cache.assert_not_called()


class TestForceFullReplacement:
    """force_full_replacement メソッドのテスト"""

    def test_successful_replacement(self, updater_with_mock_api, mock_google_api):
        """正常な完全置換"""
        # モック設定
        mock_spreadsheet = {
            "sheets": [
                {"properties": {"title": "existing_sheet", "sheetId": 123}},
            ]
        }
        mock_google_api["service"].spreadsheets().get().execute.return_value = mock_spreadsheet
        mock_google_api["service"].spreadsheets().batchUpdate().execute.return_value = {}

        # atomic_sheet_updateをモック
        with patch.object(updater_with_mock_api, "atomic_sheet_update") as mock_atomic:
            mock_atomic.return_value = (True, {"success": True, "rows_updated": 10})

            df = pd.DataFrame({"col1": [1, 2, 3]})
            success, result = updater_with_mock_api.force_full_replacement(
                "spreadsheet_id", df, new_sheet_name="existing_sheet"
            )

            assert success is True
            assert "完全置換成功" in result["message"]

    def test_replacement_without_rename(self, updater_with_mock_api, mock_google_api):
        """リネームなしの完全置換（new_sheet_name=None）"""
        mock_google_api["service"].spreadsheets().batchUpdate().execute.return_value = {}

        with patch.object(updater_with_mock_api, "atomic_sheet_update") as mock_atomic:
            mock_atomic.return_value = (True, {"success": True, "rows_updated": 10})

            df = pd.DataFrame({"col1": [1, 2, 3]})
            success, result = updater_with_mock_api.force_full_replacement("spreadsheet_id", df, new_sheet_name=None)

            assert success is True

    def test_replacement_atomic_update_fails(self, updater_with_mock_api, mock_google_api):
        """atomic_sheet_updateが失敗した場合"""
        mock_google_api["service"].spreadsheets().batchUpdate().execute.return_value = {}

        with patch.object(updater_with_mock_api, "atomic_sheet_update") as mock_atomic:
            mock_atomic.return_value = (False, {"error": "Write failed"})

            df = pd.DataFrame({"col1": [1, 2, 3]})
            success, result = updater_with_mock_api.force_full_replacement(
                "spreadsheet_id", df, new_sheet_name="sheet1"
            )

            assert success is False
            assert "error" in result

    def test_replacement_exception_handling(self, updater_with_mock_api, mock_google_api):
        """例外発生時の処理"""
        mock_google_api["service"].spreadsheets().batchUpdate().execute.side_effect = Exception("API Error")

        df = pd.DataFrame({"col1": [1, 2, 3]})
        success, result = updater_with_mock_api.force_full_replacement("spreadsheet_id", df, new_sheet_name="sheet1")

        assert success is False
        assert "error" in result

    def test_replacement_deletes_old_sheet(self, updater_with_mock_api, mock_google_api):
        """古いシートが存在する場合は削除"""
        mock_spreadsheet = {
            "sheets": [
                {"properties": {"title": "old_sheet", "sheetId": 999}},
                {"properties": {"title": "TEMP_test", "sheetId": 888}},
            ]
        }
        mock_google_api["service"].spreadsheets().get().execute.return_value = mock_spreadsheet
        mock_google_api["service"].spreadsheets().batchUpdate().execute.return_value = {}

        with patch.object(updater_with_mock_api, "atomic_sheet_update") as mock_atomic:
            mock_atomic.return_value = (True, {"success": True, "rows_updated": 10})
            with patch.object(updater_with_mock_api, "_get_sheet_id") as mock_get_id:
                mock_get_id.side_effect = [999, 888]  # old_sheet_id, temp_sheet_id

                df = pd.DataFrame({"col1": [1, 2, 3]})
                success, result = updater_with_mock_api.force_full_replacement(
                    "spreadsheet_id", df, new_sheet_name="old_sheet"
                )

                assert success is True


class TestInitGoogleApiException:
    """_init_google_api 例外処理テスト"""

    def test_api_init_exception(self, mock_cache_manager, tmp_path):
        """API初期化で例外が発生した場合"""
        credentials_file = tmp_path / "credentials.json"
        credentials_file.write_text('{"type": "service_account"}')

        with patch("src.auto_updater.service_account") as mock_sa:
            mock_sa.Credentials.from_service_account_file.side_effect = ValueError("Auth Error")

            updater = AutoUpdater(credentials_path=str(credentials_file))

            # serviceがNoneであることを確認（例外が発生してもクラッシュしない）
            assert updater.service is None


class TestUpdateWithRetryException:
    """update_with_retry 例外処理テスト"""

    def test_exception_during_retry(self, updater_with_mock_api):
        """リトライ中に例外が発生した場合"""
        with patch.object(updater_with_mock_api, "atomic_sheet_update") as mock_update:
            # 最初の呼び出しで例外、2回目で成功
            mock_update.side_effect = [
                Exception("First exception"),
                (True, {"success": True, "rows_updated": 10}),
            ]

            with patch("time.sleep"):
                df = pd.DataFrame({"col1": [1, 2, 3]})
                success, result = updater_with_mock_api.update_with_retry("spreadsheet_id", "sheet_name", df)

            # 例外が発生しても続行し、2回目で成功
            assert success is True
            assert mock_update.call_count == 2

    def test_all_retries_with_exceptions(self, updater_with_mock_api):
        """全リトライで例外が発生した場合"""
        with patch.object(updater_with_mock_api, "atomic_sheet_update") as mock_update:
            mock_update.side_effect = Exception("Persistent error")

            with patch("time.sleep"):
                df = pd.DataFrame({"col1": [1, 2, 3]})
                success, result = updater_with_mock_api.update_with_retry("spreadsheet_id", "sheet_name", df)

            assert success is False
            assert "最大リトライ" in result["error"]


class TestAutoUpdaterImportFallback:
    """CacheManager ImportError時のフォールバックテスト"""

    def test_cache_manager_fallback_import(self):
        """src.cache_manager が失敗した場合に cache_manager にフォールバックすること"""
        import builtins
        import importlib
        import sys
        from types import ModuleType

        original_import = builtins.__import__

        # cache_manager のモックモジュールを作成
        mock_cm_module = ModuleType("cache_manager")
        mock_cm_module.CacheManager = MagicMock()

        def mock_import(name, *args, **kwargs):
            if name == "src.cache_manager":
                raise ImportError(f"No module named '{name}'")
            if name == "cache_manager":
                return mock_cm_module
            return original_import(name, *args, **kwargs)

        mod_name = "src.auto_updater"
        saved_modules = {}
        for key in list(sys.modules.keys()):
            if "cache_manager" in key:
                saved_modules[key] = sys.modules.pop(key)
        if mod_name in sys.modules:
            saved_modules[mod_name] = sys.modules.pop(mod_name)

        # cache_managerモックをsys.modulesに注入
        sys.modules["cache_manager"] = mock_cm_module

        try:
            builtins.__import__ = mock_import
            mod = importlib.import_module(mod_name)
            importlib.reload(mod)

            # フォールバックでインポートされたCacheManagerを確認
            assert mod.CacheManager is mock_cm_module.CacheManager
        finally:
            builtins.__import__ = original_import
            sys.modules.pop("cache_manager", None)
            sys.modules.update(saved_modules)
            if mod_name in sys.modules:
                importlib.reload(sys.modules[mod_name])
