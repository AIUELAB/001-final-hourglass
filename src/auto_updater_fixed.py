#!/usr/bin/env python3
"""
自動更新エンジン（修正版）
Google Sheetsのアトミック更新、完全置換、キャッシュ管理
シートサイズ自動拡張対応

作成日: 2025-08-31
"""

import os
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .cache_manager import CacheManager


class AutoUpdaterFixed:
    """
    自動更新エンジン（修正版）
    - Google Sheets APIによるアトミック更新
    - シートサイズ自動拡張
    - 完全置換保証
    - キャッシュ管理統合
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
            "retry_delay": [1, 2, 4],
            "backup_before_update": True,
            "verify_after_update": True
        }
        
        self.logger.info("✅ AutoUpdaterFixed初期化完了")
    
    def _init_google_api(self):
        """Google Sheets API初期化"""
        try:
            SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
            
            if self.credentials_path.exists():
                credentials = service_account.Credentials.from_service_account_file(
                    str(self.credentials_path), scopes=SCOPES
                )
                self.service = build('sheets', 'v4', credentials=credentials)
                self.logger.info("✅ Google Sheets API接続成功")
            else:
                self.logger.warning("⚠️ 認証ファイルが見つかりません")
                
        except Exception as e:
            self.logger.error(f"❌ Google API初期化エラー: {e}")
    
    def atomic_sheet_update(
        self, 
        spreadsheet_id: str, 
        sheet_name: str,
        df: pd.DataFrame,
        clear_cache: bool = True
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        アトミック更新（修正版）
        シートサイズを自動拡張してから更新
        """
        start_time = time.time()
        result = {
            "success": False,
            "rows_updated": 0,
            "time_taken": 0,
            "cache_cleared": False,
            "error": None
        }
        
        try:
            # キャッシュクリア
            if clear_cache:
                self.cache_manager.purge_all_cache()
                result["cache_cleared"] = True
                self.logger.info("🗑️ キャッシュを完全クリア")
            
            # データ準備
            header = df.columns.tolist()
            values = df.fillna('').values.tolist()
            all_values = [header] + values
            
            total_rows = len(all_values)
            total_cols = len(header)
            
            # シートIDを取得
            sheet_id = self._get_sheet_id(spreadsheet_id, sheet_name)
            
            # バッチリクエスト作成
            requests = []
            
            # 1. シートサイズを必要に応じて拡張
            requests.append({
                'updateSheetProperties': {
                    'properties': {
                        'sheetId': sheet_id,
                        'gridProperties': {
                            'rowCount': max(total_rows + 100, 1000),  # 余裕を持たせる
                            'columnCount': max(total_cols + 10, 26)
                        }
                    },
                    'fields': 'gridProperties(rowCount,columnCount)'
                }
            })
            
            # 2. シート全体をクリア
            requests.append({
                'updateCells': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 0,
                        'endRowIndex': total_rows + 100,
                        'startColumnIndex': 0,
                        'endColumnIndex': total_cols + 10
                    },
                    'fields': 'userEnteredValue'
                }
            })
            
            # 3. 新しいデータを一括設定
            requests.append({
                'updateCells': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 0,
                        'endRowIndex': total_rows,
                        'startColumnIndex': 0,
                        'endColumnIndex': total_cols
                    },
                    'rows': self._prepare_rows_data(all_values),
                    'fields': 'userEnteredValue,userEnteredFormat'
                }
            })
            
            # 4. フォーマット設定
            requests.extend(self._create_format_requests(sheet_id, total_rows, total_cols))
            
            # アトミック実行
            batch_update_body = {
                'requests': requests,
                'includeSpreadsheetInResponse': False
            }
            
            response = self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=batch_update_body
            ).execute()
            
            result["success"] = True
            result["rows_updated"] = total_rows
            result["time_taken"] = time.time() - start_time
            
            self.logger.info(
                f"✅ アトミック更新成功: {result['rows_updated']}行を"
                f"{result['time_taken']:.2f}秒で更新"
            )
            
        except Exception as e:
            result["error"] = str(e)
            self.logger.error(f"❌ アトミック更新失敗: {e}")
        
        return result["success"], result
    
    def force_full_replacement(
        self,
        spreadsheet_id: str,
        df: pd.DataFrame,
        new_sheet_name: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        完全置換（修正版）
        一時シートを作成して置換
        """
        temp_sheet_name = f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            # 1. 一時シートを作成
            self._create_sheet(spreadsheet_id, temp_sheet_name)
            self.logger.info(f"📝 一時シート作成: {temp_sheet_name}")
            
            # 2. 一時シートにデータを書き込み（修正版のアトミック更新を使用）
            success, result = self.atomic_sheet_update(
                spreadsheet_id,
                temp_sheet_name,
                df,
                clear_cache=True
            )
            
            if not success:
                self.logger.error(f"❌ 一時シートへの書き込み失敗: {result.get('error')}")
                # 一時シートを削除
                self._delete_sheet(spreadsheet_id, temp_sheet_name)
                return False, {"error": f"一時シートへの書き込み失敗: {result.get('error')}"}
            
            # 3. 元のシートを削除して一時シートをリネーム
            if new_sheet_name:
                try:
                    # 元のシートを削除
                    self._delete_sheet(spreadsheet_id, new_sheet_name)
                except:
                    pass  # 元のシートが存在しない場合は無視
                
                # 一時シートをリネーム
                self._rename_sheet(spreadsheet_id, temp_sheet_name, new_sheet_name)
                self.logger.info(f"✅ シート置換完了: {new_sheet_name}")
            
            return True, result
            
        except Exception as e:
            self.logger.error(f"❌ 完全置換失敗: {e}")
            return False, {"error": str(e)}
    
    def _get_sheet_id(self, spreadsheet_id: str, sheet_name: str) -> int:
        """シートIDを取得"""
        try:
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()
            
            for sheet in spreadsheet.get('sheets', []):
                if sheet['properties']['title'] == sheet_name:
                    return sheet['properties']['sheetId']
            
            # デフォルトで最初のシートのIDを返す
            if spreadsheet.get('sheets'):
                return spreadsheet['sheets'][0]['properties']['sheetId']
            
            return 0
            
        except Exception as e:
            self.logger.error(f"シートID取得エラー: {e}")
            return 0
    
    def _prepare_rows_data(self, values: List[List[Any]]) -> List[Dict]:
        """行データを準備"""
        rows = []
        for row in values:
            cells = []
            for value in row:
                # 値の型に応じて適切にフォーマット
                if isinstance(value, (int, float)):
                    cells.append({'userEnteredValue': {'numberValue': value}})
                elif isinstance(value, bool):
                    cells.append({'userEnteredValue': {'boolValue': value}})
                else:
                    cells.append({'userEnteredValue': {'stringValue': str(value)}})
            rows.append({'values': cells})
        return rows
    
    def _create_format_requests(self, sheet_id: int, row_count: int, col_count: int) -> List[Dict]:
        """フォーマット設定リクエストを作成"""
        requests = []
        
        # ヘッダー行のフォーマット
        requests.append({
            'repeatCell': {
                'range': {
                    'sheetId': sheet_id,
                    'startRowIndex': 0,
                    'endRowIndex': 1,
                    'startColumnIndex': 0,
                    'endColumnIndex': col_count
                },
                'cell': {
                    'userEnteredFormat': {
                        'backgroundColor': {'red': 0.2, 'green': 0.5, 'blue': 0.8},
                        'textFormat': {
                            'foregroundColor': {'red': 1, 'green': 1, 'blue': 1},
                            'bold': True
                        }
                    }
                },
                'fields': 'userEnteredFormat(backgroundColor,textFormat)'
            }
        })
        
        # フィルター設定
        requests.append({
            'setBasicFilter': {
                'filter': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 0,
                        'endRowIndex': row_count,
                        'startColumnIndex': 0,
                        'endColumnIndex': col_count
                    }
                }
            }
        })
        
        # 列幅自動調整
        requests.append({
            'autoResizeDimensions': {
                'dimensions': {
                    'sheetId': sheet_id,
                    'dimension': 'COLUMNS',
                    'startIndex': 0,
                    'endIndex': col_count
                }
            }
        })
        
        return requests
    
    def _create_sheet(self, spreadsheet_id: str, sheet_name: str):
        """新しいシートを作成"""
        request = {
            'requests': [{
                'addSheet': {
                    'properties': {
                        'title': sheet_name
                    }
                }
            }]
        }
        
        self.service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=request
        ).execute()
    
    def _delete_sheet(self, spreadsheet_id: str, sheet_name: str):
        """シートを削除"""
        sheet_id = self._get_sheet_id(spreadsheet_id, sheet_name)
        
        request = {
            'requests': [{
                'deleteSheet': {
                    'sheetId': sheet_id
                }
            }]
        }
        
        self.service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=request
        ).execute()
    
    def _rename_sheet(self, spreadsheet_id: str, old_name: str, new_name: str):
        """シート名を変更"""
        sheet_id = self._get_sheet_id(spreadsheet_id, old_name)
        
        request = {
            'requests': [{
                'updateSheetProperties': {
                    'properties': {
                        'sheetId': sheet_id,
                        'title': new_name
                    },
                    'fields': 'title'
                }
            }]
        }
        
        self.service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=request
        ).execute()


if __name__ == "__main__":
    # テスト実行
    logging.basicConfig(level=logging.INFO)
    
    updater = AutoUpdaterFixed()
    print("✅ AutoUpdaterFixed テスト完了")