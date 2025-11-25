from src.secure_config import config
#!/usr/bin/env python3
"""
Google Sheetsスプレッドシート名自動同期システム
ローカルのultra_think_*.csvファイル名が変更されたら自動的にスプレッドシート名も更新
"""

import os
import sys
import json
import time
import re
from datetime import datetime
from pathlib import Path
import gspread
from google.oauth2.service_account import Credentials
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.text import Text

console = Console()

class SheetNameSyncHandler(FileSystemEventHandler):
    """ファイル変更を監視してスプレッドシート名を自動更新"""

    def __init__(self):
        self.config = self.load_config()
        self.client = None
        self.spreadsheet = None
        self.current_csv_file = None
        self.last_update = None
        self.init_google_client()

    def load_config(self):
        """設定ファイルを読み込み"""
        try:
            with open('sheets_config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            console.print("[yellow]⚠️ sheets_config.jsonが見つかりません。デフォルト設定を使用します。[/yellow]")
            return {
                'spreadsheet_id': '1G0ec3d5DHGiahLetsqey9W23HGFOn2tkEacsFd5ZSps',
                'csv_file': 'ultra_think_CONVERTED_20250827_224054.csv'
            }

    def save_config(self):
        """設定ファイルを保存"""
        with open('sheets_config.json', 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

    def init_google_client(self):
        """Google Sheets APIクライアントを初期化"""
        try:
            scope = ['https://spreadsheets.google.com/feeds',
                     'https://www.googleapis.com/auth/drive']

            creds = Credentials.from_service_account_file(
                config.google_credentials_path,
                scopes=scope
            )

            self.client = gspread.authorize(creds)
            self.spreadsheet = self.client.open_by_key(self.config['spreadsheet_id'])
            self.current_csv_file = self.config.get('csv_file')

            console.print("[green]✅ Google Sheets API接続成功[/green]")
            console.print(f"📊 現在のスプレッドシート: {self.spreadsheet.title}")
            console.print(f"📁 監視対象CSVファイル: {self.current_csv_file}")

        except Exception as e:
            console.print(f"[red]❌ Google Sheets API初期化エラー: {e}[/red]")
            sys.exit(1)

    def format_sheet_name(self, csv_filename):
        """CSVファイル名をスプレッドシート名にフォーマット（永続ルール適用）"""
        # .csv拡張子を削除
        name = csv_filename.replace('.csv', '')

        # アンダースコアをスペースに変換
        name = name.replace('_', ' ')

        # ultra thinkをUltra Thinkに変換（大文字化）
        parts = name.split()
        if len(parts) >= 2 and parts[0].lower() == 'ultra' and parts[1].lower() == 'think':
            parts[0] = 'Ultra'
            parts[1] = 'Think'
            # 残りの部分を適切に大文字化
            for i in range(2, len(parts)):
                # 日付形式（YYYYMMDD）と時刻形式（HHMMSS）はそのまま保持
                if re.match(r'\d{8}', parts[i]) or re.match(r'\d{6}', parts[i]):
                    pass  # 数字はそのまま
                elif parts[i].isupper():
                    pass  # すでに大文字の場合はそのまま
                else:
                    # 各単語の最初を大文字に
                    parts[i] = parts[i].title()

        return ' '.join(parts)

    def update_spreadsheet_name(self, new_csv_file):
        """スプレッドシート名を更新"""
        try:
            # 新しいスプレッドシート名を生成
            new_sheet_name = self.format_sheet_name(new_csv_file)

            # 現在の名前と比較
            current_title = self.spreadsheet.title
            if current_title == new_sheet_name:
                console.print(f"[dim]ℹ️ スプレッドシート名は既に最新です: {new_sheet_name}[/dim]")
                return False

            # スプレッドシート名を更新
            self.spreadsheet.update_title(new_sheet_name)

            # 設定を更新
            self.config['csv_file'] = new_csv_file
            self.config['sheet_name'] = new_sheet_name
            self.save_config()

            self.current_csv_file = new_csv_file
            self.last_update = datetime.now()

            console.print(Panel.fit(
                f"[green]✨ スプレッドシート名を更新しました！[/green]\n"
                f"[yellow]旧名:[/yellow] {current_title}\n"
                f"[green]新名:[/green] {new_sheet_name}\n"
                f"[blue]CSV:[/blue] {new_csv_file}\n"
                f"[dim]URL: https://docs.google.com/spreadsheets/d/{self.config['spreadsheet_id']}[/dim]",
                title="📊 同期完了",
                border_style="green"
            ))

            return True

        except Exception as e:
            console.print(f"[red]❌ スプレッドシート名更新エラー: {e}[/red]")
            return False

    def on_created(self, event):
        """新しいファイルが作成された時"""
        if not event.is_directory and event.src_path.endswith('.csv'):
            filename = os.path.basename(event.src_path)
            if filename.startswith('ultra_think_'):
                console.print(f"[cyan]📝 新しいCSVファイルを検出: {filename}[/cyan]")
                time.sleep(1)  # ファイル書き込み完了を待つ
                self.update_spreadsheet_name(filename)

    def on_moved(self, event):
        """ファイルがリネームされた時"""
        if not event.is_directory and event.dest_path.endswith('.csv'):
            filename = os.path.basename(event.dest_path)
            if filename.startswith('ultra_think_'):
                console.print(f"[cyan]📝 CSVファイルのリネームを検出: {filename}[/cyan]")
                self.update_spreadsheet_name(filename)

    def on_modified(self, event):
        """ファイルが更新された時（最新のultra_think_*.csvを確認）"""
        if not event.is_directory and event.src_path.endswith('.csv'):
            filename = os.path.basename(event.src_path)
            if filename.startswith('ultra_think_'):
                # 最新のultra_think_*.csvファイルを検索
                latest_file = self.find_latest_ultra_think_csv()
                if latest_file and latest_file != self.current_csv_file:
                    console.print(f"[cyan]🔄 最新のCSVファイルに切り替え: {latest_file}[/cyan]")
                    self.update_spreadsheet_name(latest_file)

    def find_latest_ultra_think_csv(self):
        """最新のultra_think_*.csvファイルを検索"""
        try:
            csv_files = list(Path('.').glob('ultra_think_*.csv'))
            if not csv_files:
                return None

            # 更新日時でソート
            latest_file = max(csv_files, key=lambda x: x.stat().st_mtime)
            return latest_file.name

        except Exception as e:
            console.print(f"[red]❌ CSVファイル検索エラー: {e}[/red]")
            return None


def monitor_csv_files():
    """CSVファイルの変更を監視"""
    console.print(Panel.fit(
        "[bold cyan]🔍 Ultra Think CSV ファイル監視システム[/bold cyan]\n"
        "[dim]ローカルのCSVファイル名が変更されると自動的にGoogle Sheetsのスプレッドシート名も更新します[/dim]",
        title="📊 自動同期システム",
        border_style="cyan"
    ))

    event_handler = SheetNameSyncHandler()
    observer = Observer()
    observer.schedule(event_handler, '.', recursive=False)
    observer.start()

    console.print("\n[green]✅ 監視を開始しました。Ctrl+Cで停止できます。[/green]\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        console.print("\n[yellow]⏹️ 監視を停止しました。[/yellow]")

    observer.join()


def manual_sync():
    """手動で最新のCSVファイルと同期"""
    console.print("[cyan]🔄 手動同期を開始します...[/cyan]")

    handler = SheetNameSyncHandler()
    latest_csv = handler.find_latest_ultra_think_csv()

    if latest_csv:
        console.print(f"[green]📁 最新のCSVファイル: {latest_csv}[/green]")
        if handler.update_spreadsheet_name(latest_csv):
            console.print("[green]✅ 同期完了！[/green]")
        else:
            console.print("[yellow]ℹ️ 更新の必要はありませんでした。[/yellow]")
    else:
        console.print("[red]❌ ultra_think_*.csvファイルが見つかりません。[/red]")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Google Sheetsスプレッドシート名自動同期')
    parser.add_argument('--manual', action='store_true', help='手動で一度だけ同期')
    parser.add_argument('--monitor', action='store_true', help='継続的に監視（デフォルト）')

    args = parser.parse_args()

    if args.manual:
        manual_sync()
    else:
        monitor_csv_files()
