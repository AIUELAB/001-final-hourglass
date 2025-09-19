from src.secure_config import config
#!/usr/bin/env python3
"""
Google Sheets リアルタイム同期システム
人物データベースをGoogle Sheetsと双方向同期
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import threading
import hashlib

import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout
from dotenv import load_dotenv

load_dotenv()
console = Console()

class GoogleSheetsSync:
    """Google Sheets同期クラス"""
    
    def __init__(self, config_file: str = "sheets_config.json"):
        self.config_file = config_file
        self.config = self.load_config()
        self.credentials = None
        self.client = None
        self.sheet = None
        self.csv_file = self.config.get("csv_file", "ultra_think_NO_FAKE_RESEARCHERS_20250827_143418.csv")
        self.sheet_name = self.config.get("sheet_name", "Ultra Think Database")
        self.spreadsheet_id = self.config.get("spreadsheet_id", None)
        self.last_sync = None
        self.sync_lock = threading.Lock()
        
    def load_config(self) -> Dict:
        """設定ファイルを読み込む"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def save_config(self):
        """設定を保存"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
    
    def setup_credentials(self):
        """Google API認証をセットアップ"""
        console.print("[bold blue]Google Sheets API認証セットアップ[/bold blue]")
        
        # 認証ファイルを探す
        cred_files = [
            config.google_credentials_path,
            "credentials.json",
            "google_credentials.json",
            "service_account.json",
            os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
        ]
        
        cred_file = None
        for file in cred_files:
            if file and os.path.exists(file):
                cred_file = file
                break
        
        if not cred_file:
            console.print("[bold red]認証ファイルが見つかりません！[/bold red]")
            console.print("\n以下の手順で認証ファイルを作成してください：")
            console.print("1. https://console.cloud.google.com にアクセス")
            console.print("2. 新しいプロジェクトを作成または既存のプロジェクトを選択")
            console.print("3. Google Sheets APIとGoogle Drive APIを有効化")
            console.print("4. サービスアカウントを作成")
            console.print("5. JSONキーファイルをダウンロード")
            console.print("6. ファイルを 'credentials.json' として保存")
            return False
        
        try:
            SCOPES = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            
            self.credentials = Credentials.from_service_account_file(
                cred_file, scopes=SCOPES
            )
            self.client = gspread.authorize(self.credentials)
            
            console.print(f"[green]✓ 認証成功: {cred_file}[/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]認証エラー: {e}[/red]")
            return False
    
    def create_or_get_spreadsheet(self):
        """スプレッドシートを作成または取得"""
        try:
            if self.spreadsheet_id:
                # 既存のスプレッドシートを開く
                self.sheet = self.client.open_by_key(self.spreadsheet_id)
                console.print(f"[green]✓ 既存のスプレッドシートを開きました[/green]")
            else:
                # 新しいスプレッドシートを作成
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                title = f"{self.sheet_name}_{timestamp}"
                self.sheet = self.client.create(title)
                self.spreadsheet_id = self.sheet.id
                
                # 設定を保存
                self.config["spreadsheet_id"] = self.spreadsheet_id
                self.save_config()
                
                # 共有設定（任意のメールアドレスと共有可能）
                self.sheet.share('', perm_type='anyone', role='writer')
                
                console.print(f"[green]✓ 新しいスプレッドシートを作成しました[/green]")
            
            console.print(f"[bold cyan]スプレッドシートURL:[/bold cyan]")
            console.print(f"[link]{self.sheet.url}[/link]")
            
            return True
            
        except Exception as e:
            console.print(f"[red]スプレッドシート作成/取得エラー: {e}[/red]")
            return False
    
    def upload_csv_to_sheets(self):
        """CSVファイルをGoogle Sheetsにアップロード"""
        try:
            console.print(f"\n[bold blue]CSVファイルをアップロード中...[/bold blue]")
            
            # CSVを読み込み
            df = pd.read_csv(self.csv_file, encoding='utf-8')
            console.print(f"[green]✓ CSVファイル読み込み完了: {len(df)}行 x {len(df.columns)}列[/green]")
            
            # NaN値を空文字列に置換
            df = df.fillna('')
            
            # データを文字列に変換
            df = df.astype(str)
            
            # ワークシートを取得または作成
            try:
                worksheet = self.sheet.worksheet("データ")
            except:
                worksheet = self.sheet.add_worksheet(title="データ", rows=len(df)+1, cols=len(df.columns))
            
            # プログレスバーを表示
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                console=console
            ) as progress:
                
                # ヘッダーをアップロード
                task = progress.add_task("ヘッダーアップロード...", total=1)
                worksheet.update([df.columns.tolist()], range_name='A1')
                progress.update(task, completed=1)
                
                # データをバッチでアップロード（高速化）
                batch_size = 1000
                total_batches = (len(df) - 1) // batch_size + 1
                task = progress.add_task("データアップロード...", total=total_batches)
                
                for i in range(0, len(df), batch_size):
                    batch = df.iloc[i:i+batch_size]
                    values = batch.values.tolist()
                    start_row = i + 2  # ヘッダーの次の行から
                    range_name = f'A{start_row}'
                    worksheet.update(values, range_name=range_name)
                    progress.update(task, advance=1)
            
            # フォーマット設定
            self.format_sheet(worksheet, df)
            
            console.print("[green]✓ アップロード完了！[/green]")
            self.last_sync = datetime.now()
            
            return True
            
        except Exception as e:
            console.print(f"[red]アップロードエラー: {e}[/red]")
            return False
    
    def format_sheet(self, worksheet, df):
        """シートのフォーマットを設定"""
        try:
            console.print("[blue]フォーマット設定中...[/blue]")
            
            # ヘッダー行を固定
            worksheet.freeze(rows=1)
            
            # 列幅を自動調整（簡易版）
            worksheet.columns_auto_resize(0, len(df.columns)-1)
            
            # 条件付き書式を設定（エラー値のハイライトなど）
            # ここは必要に応じてカスタマイズ
            
            console.print("[green]✓ フォーマット設定完了[/green]")
            
        except Exception as e:
            console.print(f"[yellow]フォーマット設定警告: {e}[/yellow]")
    
    def download_from_sheets(self):
        """Google Sheetsからデータをダウンロード"""
        try:
            with self.sync_lock:
                worksheet = self.sheet.worksheet("データ")
                values = worksheet.get_all_values()
                
                if len(values) > 1:
                    df = pd.DataFrame(values[1:], columns=values[0])
                    
                    # バックアップを作成
                    backup_file = f"{self.csv_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    if os.path.exists(self.csv_file):
                        pd.read_csv(self.csv_file).to_csv(backup_file, index=False)
                    
                    # CSVを更新
                    df.to_csv(self.csv_file, index=False, encoding='utf-8')
                    
                    console.print(f"[green]✓ Sheetsからダウンロード完了: {len(df)}行[/green]")
                    self.last_sync = datetime.now()
                    
                    return True
                    
        except Exception as e:
            console.print(f"[red]ダウンロードエラー: {e}[/red]")
            return False
    
    def watch_changes(self):
        """変更を監視"""
        console.print("\n[bold blue]リアルタイム同期を開始します...[/bold blue]")
        console.print("[yellow]Ctrl+C で停止[/yellow]\n")
        
        class ChangeHandler(FileSystemEventHandler):
            def __init__(self, sync_instance):
                self.sync = sync_instance
                self.last_modified = {}
                
            def on_modified(self, event):
                if event.src_path.endswith('.csv'):
                    # 重複イベントを防ぐ
                    current_time = time.time()
                    if event.src_path in self.last_modified:
                        if current_time - self.last_modified[event.src_path] < 2:
                            return
                    self.last_modified[event.src_path] = current_time
                    
                    console.print(f"[yellow]ローカルファイルが変更されました: {event.src_path}[/yellow]")
                    self.sync.upload_csv_to_sheets()
        
        # ファイル監視を開始
        event_handler = ChangeHandler(self)
        observer = Observer()
        observer.schedule(event_handler, path='.', recursive=False)
        observer.start()
        
        # Google Sheets側の変更も定期的にチェック
        try:
            while True:
                time.sleep(30)  # 30秒ごとにチェック
                self.check_remote_changes()
                
        except KeyboardInterrupt:
            observer.stop()
            console.print("\n[yellow]同期を停止しました[/yellow]")
        
        observer.join()
    
    def check_remote_changes(self):
        """リモート（Google Sheets）の変更をチェック"""
        try:
            worksheet = self.sheet.worksheet("データ")
            
            # 最終更新時刻をチェック（簡易版）
            # より高度な実装では、チェックサムやタイムスタンプを使用
            current_data = worksheet.get_all_values()
            
            if current_data:
                # ローカルファイルと比較
                local_df = pd.read_csv(self.csv_file, encoding='utf-8')
                remote_df = pd.DataFrame(current_data[1:], columns=current_data[0])
                
                # データが異なる場合
                if not local_df.equals(remote_df):
                    console.print("[yellow]Google Sheetsに変更を検出[/yellow]")
                    self.download_from_sheets()
                    
        except Exception as e:
            console.print(f"[red]リモートチェックエラー: {e}[/red]")
    
    def show_status(self):
        """現在のステータスを表示"""
        table = Table(title="同期ステータス", box=None)
        table.add_column("項目", style="cyan", no_wrap=True)
        table.add_column("値", style="green")
        
        table.add_row("CSVファイル", self.csv_file)
        table.add_row("スプレッドシートID", self.spreadsheet_id or "未設定")
        table.add_row("最終同期", str(self.last_sync) if self.last_sync else "未同期")
        
        if self.sheet:
            table.add_row("スプレッドシートURL", self.sheet.url)
        
        console.print(table)
    
    def run(self, args):
        """メイン実行"""
        if args.setup or not self.credentials:
            if not self.setup_credentials():
                return
            if not self.create_or_get_spreadsheet():
                return
        
        if args.upload:
            self.upload_csv_to_sheets()
        
        if args.download:
            self.download_from_sheets()
        
        if args.sync:
            self.upload_csv_to_sheets()
            self.download_from_sheets()
        
        if args.watch:
            self.watch_changes()
        
        if args.status:
            self.show_status()
        
        if not any([args.setup, args.upload, args.download, args.sync, args.watch, args.status]):
            # デフォルト動作：セットアップとアップロード
            if not self.credentials:
                if not self.setup_credentials():
                    return
            if not self.sheet:
                if not self.create_or_get_spreadsheet():
                    return
            self.upload_csv_to_sheets()
            self.show_status()


def main():
    parser = argparse.ArgumentParser(description="Google Sheets同期システム")
    parser.add_argument("--setup", action="store_true", help="初期セットアップ")
    parser.add_argument("--upload", action="store_true", help="CSVをSheetsにアップロード")
    parser.add_argument("--download", action="store_true", help="SheetsからCSVにダウンロード")
    parser.add_argument("--sync", action="store_true", help="双方向同期")
    parser.add_argument("--watch", action="store_true", help="リアルタイム監視モード")
    parser.add_argument("--status", action="store_true", help="ステータス表示")
    parser.add_argument("--config", default="sheets_config.json", help="設定ファイル")
    
    args = parser.parse_args()
    
    # バナーを表示
    console.print(Panel.fit(
        "[bold cyan]Google Sheets リアルタイム同期システム[/bold cyan]\n" +
        "[yellow]Ultra Think Database Manager v1.0[/yellow]",
        border_style="blue"
    ))
    
    sync = GoogleSheetsSync(config_file=args.config)
    sync.run(args)


if __name__ == "__main__":
    main()