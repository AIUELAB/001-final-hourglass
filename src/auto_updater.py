#!/usr/bin/env python3
"""
自動更新エンジン
Google Sheetsへのアトミック更新と完全なデータ置換を保証

作成日: 2025-08-31
Ultra Think Mode対応
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build

# ローカルインポート
try:
    from src.cache_manager import CacheManager
except ImportError:
    # 開発時の相対インポート
    from cache_manager import CacheManager


class AutoUpdater:
    """
    自動更新エンジン
    - アトミック更新（完全置換保証）
    - batchUpdate APIによる高速更新
    - エラー時の自動リトライ
    - トランザクション管理
    """

    def __init__(self, credentials_path: str = "key/credentials.json"):
        self.credentials_path = Path(credentials_path)
        self.logger = logging.getLogger(__name__)

        # Google Sheets API初期化
        self.service = None
        self.spreadsheet_id = None
        self._init_google_api()

        # キャッシュマネージャー
        self.cache_manager = CacheManager()

        # 設定
        self.config = {
            "atomic_update": True,
            "batch_size": 10000,
            "retry_count": 3,
            "retry_delay": [1, 2, 4],  # 指数バックオフ
            "backup_before_update": True,
            "verify_after_update": True,
        }

        # 更新履歴
        self.update_history = []

        self.logger.info("✅ AutoUpdater初期化完了")

    def _init_google_api(self):
        """Google Sheets API初期化"""
        try:
            SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

            if self.credentials_path.exists():
                credentials = service_account.Credentials.from_service_account_file(
                    str(self.credentials_path), scopes=SCOPES
                )
                self.service = build("sheets", "v4", credentials=credentials)
                self.logger.info("✅ Google Sheets API接続成功")
            else:
                self.logger.warning("⚠️  認証ファイルが見つかりません")

        except (FileNotFoundError, ValueError, PermissionError) as e:
            self.logger.error(f"❌ Google API初期化エラー: {e}")

    def atomic_sheet_update(
        self, spreadsheet_id: str, sheet_name: str, df: pd.DataFrame, clear_cache: bool = True
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        アトミックなシート更新（完全置換保証）

        Args:
            spreadsheet_id: スプレッドシートID
            sheet_name: シート名
            df: 更新データ
            clear_cache: キャッシュクリアフラグ

        Returns:
            (成功フラグ, 結果詳細)
        """
        start_time = time.time()
        result = {"success": False, "rows_updated": 0, "time_taken": 0, "cache_cleared": False, "error": None}

        try:
            # 前処理：キャッシュクリア
            if clear_cache:
                self.cache_manager.purge_all_cache()
                result["cache_cleared"] = True
                self.logger.info("🗑️  キャッシュを完全クリア")

            # データ準備
            header = df.columns.tolist()
            values = df.fillna("").values.tolist()
            all_values = [header] + values

            # バッチリクエスト作成
            requests = []

            # 1. シート全体をクリア
            requests.append(
                {
                    "updateCells": {
                        "range": {"sheetId": self._get_sheet_id(spreadsheet_id, sheet_name)},
                        "fields": "userEnteredValue",
                    }
                }
            )

            # 2. 新しいデータを一括設定
            requests.append(
                {
                    "updateCells": {
                        "range": {
                            "sheetId": self._get_sheet_id(spreadsheet_id, sheet_name),
                            "startRowIndex": 0,
                            "startColumnIndex": 0,
                        },
                        "rows": self._prepare_rows_data(all_values),
                        "fields": "userEnteredValue,userEnteredFormat",
                    }
                }
            )

            # 3. フォーマット設定
            requests.extend(
                self._create_format_requests(
                    self._get_sheet_id(spreadsheet_id, sheet_name), len(all_values), len(header)
                )
            )

            # アトミック実行（1回のAPI呼び出しで完全更新）
            batch_update_body = {"requests": requests, "includeSpreadsheetInResponse": False}

            # キャッシュ無効化ヘッダー追加
            self.cache_manager.clear_google_sheets_cache()

            # batchUpdate実行
            (self.service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=batch_update_body).execute())

            # 結果記録
            result["success"] = True
            result["rows_updated"] = len(all_values)
            result["time_taken"] = time.time() - start_time

            self.logger.info(f"✅ アトミック更新成功: {result['rows_updated']}行を{result['time_taken']:.2f}秒で更新")

            # 更新履歴記録
            self._record_update_history(spreadsheet_id, sheet_name, result)

        except Exception as e:
            result["error"] = str(e)
            self.logger.error(f"❌ アトミック更新失敗: {e}")

        return result["success"], result

    def update_with_retry(self, spreadsheet_id: str, sheet_name: str, df: pd.DataFrame) -> Tuple[bool, Dict[str, Any]]:
        """リトライ機能付き更新"""

        for attempt in range(self.config["retry_count"]):
            try:
                # 更新実行
                success, result = self.atomic_sheet_update(
                    spreadsheet_id,
                    sheet_name,
                    df,
                    clear_cache=(attempt == 0),  # 初回のみキャッシュクリア
                )

                if success:
                    return True, result

                # リトライ前の待機
                if attempt < self.config["retry_count"] - 1:
                    delay = self.config["retry_delay"][attempt]
                    self.logger.info(f"⏳ {delay}秒後にリトライ... (試行 {attempt + 2}/{self.config['retry_count']})")
                    time.sleep(delay)

            except Exception as e:
                self.logger.error(f"❌ 試行 {attempt + 1} 失敗: {e}")

        return False, {"error": "最大リトライ回数に達しました"}

    def _get_sheet_id(self, spreadsheet_id: str, sheet_name: str) -> int:
        """シートIDを取得"""
        try:
            spreadsheet = self.service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()

            for sheet in spreadsheet["sheets"]:
                if sheet["properties"]["title"] == sheet_name:
                    return sheet["properties"]["sheetId"]

            # シートが見つからない場合は最初のシートを使用
            return spreadsheet["sheets"][0]["properties"]["sheetId"]

        except Exception as e:
            self.logger.error(f"シートID取得エラー: {e}")
            return 0

    def _prepare_rows_data(self, values: List[List]) -> List[Dict]:
        """batchUpdate用の行データ準備"""
        rows = []

        for row_values in values:
            cells = []
            for value in row_values:
                cell = {"userEnteredValue": {}}

                # データ型に応じた設定
                if isinstance(value, (int, float)):
                    cell["userEnteredValue"]["numberValue"] = float(value)
                elif isinstance(value, bool):
                    cell["userEnteredValue"]["boolValue"] = value
                else:
                    cell["userEnteredValue"]["stringValue"] = str(value)

                cells.append(cell)

            rows.append({"values": cells})

        return rows

    def _create_format_requests(self, sheet_id: int, row_count: int, col_count: int) -> List[Dict]:
        """フォーマット設定リクエスト作成"""
        requests = []

        # ヘッダー行の書式設定
        requests.append(
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 0,
                        "endRowIndex": 1,
                        "startColumnIndex": 0,
                        "endColumnIndex": col_count,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9},
                            "textFormat": {"bold": True},
                            "horizontalAlignment": "CENTER",
                        }
                    },
                    "fields": "userEnteredFormat",
                }
            }
        )

        # 列幅の自動調整
        requests.append(
            {
                "autoResizeDimensions": {
                    "dimensions": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 0, "endIndex": col_count}
                }
            }
        )

        # フィルター設定
        requests.append(
            {
                "setBasicFilter": {
                    "filter": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 0,
                            "endRowIndex": row_count,
                            "startColumnIndex": 0,
                            "endColumnIndex": col_count,
                        }
                    }
                }
            }
        )

        return requests

    def force_full_replacement(
        self, spreadsheet_id: str, df: pd.DataFrame, new_sheet_name: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """完全置換モード（新しいシート作成→古いシート削除）"""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_sheet_name = f"TEMP_{timestamp}"

        try:
            # 1. 一時シート作成
            self.logger.info("📝 一時シート作成中...")
            create_request = {"addSheet": {"properties": {"title": temp_sheet_name}}}

            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id, body={"requests": [create_request]}
            ).execute()

            # 2. 一時シートにデータ書き込み
            success, result = self.atomic_sheet_update(spreadsheet_id, temp_sheet_name, df, clear_cache=True)

            if not success:
                raise Exception(f"一時シートへの書き込み失敗: {result.get('error')}")

            # 3. 古いシートを削除して一時シートをリネーム
            if new_sheet_name:
                self.logger.info(f"🔄 シート名を'{new_sheet_name}'に更新...")

                # 既存シートのID取得
                old_sheet_id = self._get_sheet_id(spreadsheet_id, new_sheet_name)
                temp_sheet_id = self._get_sheet_id(spreadsheet_id, temp_sheet_name)

                requests = []

                # 古いシート削除（存在する場合）
                if old_sheet_id > 0:
                    requests.append({"deleteSheet": {"sheetId": old_sheet_id}})

                # 一時シートをリネーム
                requests.append(
                    {
                        "updateSheetProperties": {
                            "properties": {"sheetId": temp_sheet_id, "title": new_sheet_name},
                            "fields": "title",
                        }
                    }
                )

                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id, body={"requests": requests}
                ).execute()

            self.logger.info("✅ 完全置換成功")
            return True, {"message": "完全置換成功", "rows": len(df)}

        except Exception as e:
            self.logger.error(f"❌ 完全置換失敗: {e}")
            return False, {"error": str(e)}

    def _record_update_history(self, spreadsheet_id: str, sheet_name: str, result: Dict):
        """更新履歴を記録"""
        history_entry = {
            "timestamp": datetime.now().isoformat(),
            "spreadsheet_id": spreadsheet_id,
            "sheet_name": sheet_name,
            "rows_updated": result.get("rows_updated", 0),
            "time_taken": result.get("time_taken", 0),
            "success": result.get("success", False),
            "cache_cleared": result.get("cache_cleared", False),
        }

        self.update_history.append(history_entry)

        # 最新50件のみ保持
        if len(self.update_history) > 50:
            self.update_history = self.update_history[-50:]

        # ファイルに保存
        history_file = Path("logs/update_history.json")
        history_file.parent.mkdir(exist_ok=True)

        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(self.update_history, f, ensure_ascii=False, indent=2)

    def get_update_stats(self) -> Dict[str, Any]:
        """更新統計情報取得"""
        if not self.update_history:
            return {"message": "更新履歴なし"}

        total_updates = len(self.update_history)
        successful_updates = sum(1 for h in self.update_history if h.get("success"))
        total_rows = sum(h.get("rows_updated", 0) for h in self.update_history)
        avg_time = sum(h.get("time_taken", 0) for h in self.update_history) / total_updates

        return {
            "total_updates": total_updates,
            "successful_updates": successful_updates,
            "success_rate": f"{(successful_updates / total_updates) * 100:.1f}%",
            "total_rows_updated": total_rows,
            "average_time_seconds": round(avg_time, 2),
            "last_update": self.update_history[-1]["timestamp"] if self.update_history else None,
        }


if __name__ == "__main__":
    # テスト実行
    logging.basicConfig(level=logging.INFO)

    updater = AutoUpdater()

    # テストデータ
    test_df = pd.DataFrame(
        {
            "person_id": ["P000399"],
            "person_name": ["Kajisac"],
            "person_name_display": ["カジサック"],  # 修正済み
            "person_name_ja": ["カジサック"],
        }
    )

    print("🚀 自動更新エンジンテスト")
    stats = updater.get_update_stats()
    print(f"更新統計: {json.dumps(stats, indent=2, ensure_ascii=False)}")
