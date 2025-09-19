from src.secure_config import config
#!/usr/bin/env python3
"""
Ultra Think 統合自動適用システム（マスター）
全ルールを並列適用し、新規データ追加時にも自動実行
サブエージェント（Taskツール）を活用した高速処理
"""

import pandas as pd
import json
import time
import concurrent.futures
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import gspread
from google.oauth2.service_account import Credentials
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table
import traceback

# 個別ルールモジュールをインポート
from ultra_think_foreign_name_converter import ForeignNameConverter, apply_to_new_data as apply_foreign_rules
from ultra_think_fictional_character_enhancer import FictionalCharacterEnhancer, apply_to_new_data as apply_fictional_rules
from ultra_think_group_name_enhancer import GroupNameEnhancer, apply_to_new_data as apply_group_rules

console = Console()

# Google Sheets設定
SPREADSHEET_ID = "1G0ec3d5DHGiahLetsqey9W23HGFOn2tkEacsFd5ZSps"

class UltraThinkRulesMaster:
    """Ultra Think ルール統合マスタークラス"""
    
    def __init__(self, use_parallel: bool = True):
        """
        Args:
            use_parallel: 並列処理を使用するか（サブエージェント相当）
        """
        self.use_parallel = use_parallel
        self.client = None
        self.spreadsheet = None
        self.sheet = None
        
        # 処理統計
        self.master_stats = {
            'total_rows': 0,
            'rules_applied': [],
            'processing_time': 0,
            'errors': []
        }
        
        # ルール適用履歴
        self.rule_history = []
        
        # 初期化
        self.init_google_client()
    
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
            self.spreadsheet = self.client.open_by_key(SPREADSHEET_ID)
            self.sheet = self.spreadsheet.sheet1
            
            console.print("[green]✅ Google Sheets API接続成功[/green]")
            
        except Exception as e:
            console.print(f"[red]❌ Google Sheets API初期化エラー: {e}[/red]")
            self.master_stats['errors'].append(str(e))
    
    def apply_rule_batch(self, df: pd.DataFrame, rule_name: str, rule_func: callable) -> pd.DataFrame:
        """個別ルールをバッチ適用"""
        console.print(f"\n[cyan]📌 {rule_name}を適用中...[/cyan]")
        
        try:
            start_time = time.time()
            
            # ルールを適用
            df_processed = rule_func(df.copy())
            
            elapsed = time.time() - start_time
            
            self.rule_history.append({
                'rule': rule_name,
                'status': 'success',
                'time': elapsed,
                'timestamp': datetime.now().isoformat()
            })
            
            console.print(f"[green]✅ {rule_name} 完了 ({elapsed:.2f}秒)[/green]")
            return df_processed
            
        except Exception as e:
            error_msg = f"{rule_name}エラー: {e}"
            console.print(f"[red]❌ {error_msg}[/red]")
            self.master_stats['errors'].append(error_msg)
            self.rule_history.append({
                'rule': rule_name,
                'status': 'failed',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
            return df
    
    def apply_rules_parallel(self, df: pd.DataFrame) -> pd.DataFrame:
        """全ルールを並列適用（サブエージェント方式）"""
        console.print(Panel.fit(
            "[bold cyan]🚀 Ultra Think 並列ルール適用（サブエージェント）[/bold cyan]",
            title="並列処理開始",
            border_style="cyan"
        ))
        
        # データフレームをコピー
        df_results = {}
        
        # ThreadPoolExecutorで並列実行
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            # 各ルールを並列実行
            futures = {
                executor.submit(
                    self.apply_rule_batch, 
                    df.copy(), 
                    "外国語名日本語変換",
                    lambda x: ForeignNameConverter().process_dataframe(x)
                ): "foreign_name",
                
                executor.submit(
                    self.apply_rule_batch,
                    df.copy(),
                    "架空キャラクター作品名追加",
                    lambda x: FictionalCharacterEnhancer().process_dataframe(x)
                ): "fictional_character",
                
                executor.submit(
                    self.apply_rule_batch,
                    df.copy(),
                    "グループ名追加",
                    lambda x: GroupNameEnhancer().process_dataframe(x)
                ): "group_name"
            }
            
            # 結果を収集
            for future in concurrent.futures.as_completed(futures):
                rule_key = futures[future]
                try:
                    df_results[rule_key] = future.result()
                    self.master_stats['rules_applied'].append(rule_key)
                except Exception as e:
                    console.print(f"[red]並列処理エラー ({rule_key}): {e}[/red]")
                    df_results[rule_key] = df.copy()
        
        # 結果をマージ（各ルールの変更を統合）
        df_final = df.copy()
        
        # person_name_display列の更新を統合
        for rule_key in ['foreign_name', 'fictional_character', 'group_name']:
            if rule_key in df_results:
                # 変更があった行のみを更新
                changed_mask = df_results[rule_key]['person_name_display'] != df['person_name_display']
                df_final.loc[changed_mask, 'person_name_display'] = df_results[rule_key].loc[changed_mask, 'person_name_display']
        
        return df_final
    
    def apply_rules_sequential(self, df: pd.DataFrame) -> pd.DataFrame:
        """全ルールを順次適用（従来方式）"""
        console.print(Panel.fit(
            "[bold yellow]📋 Ultra Think 順次ルール適用[/bold yellow]",
            title="順次処理開始",
            border_style="yellow"
        ))
        
        # 1. 外国語名の日本語変換
        df = self.apply_rule_batch(
            df, 
            "外国語名日本語変換",
            lambda x: ForeignNameConverter().process_dataframe(x)
        )
        
        # 2. 架空キャラクター作品名追加
        df = self.apply_rule_batch(
            df,
            "架空キャラクター作品名追加",
            lambda x: FictionalCharacterEnhancer().process_dataframe(x)
        )
        
        # 3. グループ名追加
        df = self.apply_rule_batch(
            df,
            "グループ名追加",
            lambda x: GroupNameEnhancer().process_dataframe(x)
        )
        
        return df
    
    def process_database(self, csv_file: str = None) -> pd.DataFrame:
        """データベース全体を処理"""
        start_time = time.time()
        
        # CSVファイルの読み込み
        if csv_file is None:
            csv_file = "ultra_think_CONVERTED_20250827_224054.csv"
        
        console.print(f"\n📂 データベース読み込み: {csv_file}")
        df = pd.read_csv(csv_file, encoding='utf-8')
        self.master_stats['total_rows'] = len(df)
        console.print(f"   総データ数: {self.master_stats['total_rows']}行")
        
        # バックアップ作成
        backup_file = f"backup_{csv_file}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        df.to_csv(backup_file, index=False, encoding='utf-8')
        console.print(f"💾 バックアップ作成: {backup_file}")
        
        # ルール適用（並列または順次）
        if self.use_parallel:
            df_processed = self.apply_rules_parallel(df)
        else:
            df_processed = self.apply_rules_sequential(df)
        
        # 処理時間を記録
        self.master_stats['processing_time'] = time.time() - start_time
        
        return df_processed
    
    def sync_to_google_sheets(self, df: pd.DataFrame):
        """Google Sheetsに同期"""
        if not self.sheet:
            console.print("[yellow]⚠️ Google Sheets接続なし[/yellow]")
            return
        
        console.print("\n[cyan]📤 Google Sheetsへの同期を開始...[/cyan]")
        
        try:
            # NaNを空文字列に置換
            df = df.fillna('')
            
            # プログレスバーを表示
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                console=console
            ) as progress:
                task = progress.add_task("アップロード中...", total=100)
                
                # 既存データをクリア
                self.sheet.clear()
                progress.update(task, advance=30)
                
                # ヘッダーとデータを準備
                data = [df.columns.tolist()] + df.values.tolist()
                progress.update(task, advance=40)
                
                # バッチ更新
                self.sheet.update('A1', data)
                progress.update(task, advance=30)
            
            # スプレッドシート名を更新
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            new_title = f"Ultra Think RULES_APPLIED {timestamp}"
            self.spreadsheet.update_title(new_title)
            
            console.print(f"[green]✅ Google Sheets同期完了[/green]")
            console.print(f"   URL: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")
            
        except Exception as e:
            error_msg = f"Google Sheets同期エラー: {e}"
            console.print(f"[red]❌ {error_msg}[/red]")
            self.master_stats['errors'].append(error_msg)
    
    def generate_master_report(self) -> str:
        """統合レポートを生成"""
        report = []
        report.append("# Ultra Think ルール統合適用レポート")
        report.append(f"\n生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        report.append("\n## 📊 処理統計")
        report.append(f"- 総データ数: {self.master_stats['total_rows']}行")
        report.append(f"- 処理時間: {self.master_stats['processing_time']:.2f}秒")
        report.append(f"- 処理方式: {'並列処理（サブエージェント）' if self.use_parallel else '順次処理'}")
        
        report.append("\n## ✅ 適用済みルール")
        for rule in self.master_stats['rules_applied']:
            report.append(f"- {rule}")
        
        if self.rule_history:
            report.append("\n## 📝 処理履歴")
            for history in self.rule_history:
                status = "✅" if history['status'] == 'success' else "❌"
                report.append(f"- {status} {history['rule']}")
                if 'time' in history:
                    report.append(f"  処理時間: {history['time']:.2f}秒")
                if 'error' in history:
                    report.append(f"  エラー: {history['error']}")
        
        if self.master_stats['errors']:
            report.append("\n## ⚠️ エラー")
            for error in self.master_stats['errors']:
                report.append(f"- {error}")
        
        report.append("\n## 🎯 処理完了")
        report.append("全ルールの適用が完了しました。")
        
        return '\n'.join(report)
    
    def save_results(self, df: pd.DataFrame, output_file: str = None):
        """結果を保存"""
        if output_file is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"ultra_think_RULES_APPLIED_{timestamp}.csv"
        
        df.to_csv(output_file, index=False, encoding='utf-8')
        console.print(f"💾 処理済みデータを保存: {output_file}")
        
        # レポート生成
        report = self.generate_master_report()
        report_file = f"MASTER_RULES_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        console.print(f"📋 統合レポート生成: {report_file}")
        
        return output_file


def apply_all_rules_to_new_data(new_data: pd.DataFrame, sync_to_sheets: bool = True) -> pd.DataFrame:
    """新規追加データに全ルールを自動適用"""
    console.print("\n[cyan]🆕 新規データへのルール自動適用[/cyan]")
    
    master = UltraThinkRulesMaster(use_parallel=True)
    
    # 並列でルール適用
    if master.use_parallel:
        df_processed = master.apply_rules_parallel(new_data)
    else:
        df_processed = master.apply_rules_sequential(new_data)
    
    # Google Sheetsに同期
    if sync_to_sheets:
        master.sync_to_google_sheets(df_processed)
    
    return df_processed


def main():
    """メイン処理"""
    console.print(Panel.fit(
        "[bold magenta]🏆 Ultra Think ルール統合マスターシステム[/bold magenta]\n"
        "[dim]全ルールを自動適用してデータ品質を向上[/dim]",
        title="Ultra Think Rules Master",
        border_style="magenta"
    ))
    
    # パラメータ設定
    use_parallel = console.input("\n並列処理を使用しますか？ (y/n) [y]: ").lower() != 'n'
    sync_to_sheets = console.input("Google Sheetsに同期しますか？ (y/n) [y]: ").lower() != 'n'
    
    # マスターインスタンスを作成
    master = UltraThinkRulesMaster(use_parallel=use_parallel)
    
    # データベース処理
    df_processed = master.process_database()
    
    # 結果を保存
    output_file = master.save_results(df_processed)
    
    # Google Sheetsに同期
    if sync_to_sheets:
        master.sync_to_google_sheets(df_processed)
    
    # 統計表示
    table = Table(title="処理結果サマリー")
    table.add_column("項目", style="cyan")
    table.add_column("値", style="green")
    
    table.add_row("総データ数", f"{master.master_stats['total_rows']}行")
    table.add_row("処理時間", f"{master.master_stats['processing_time']:.2f}秒")
    table.add_row("適用ルール数", f"{len(master.master_stats['rules_applied'])}個")
    table.add_row("エラー数", f"{len(master.master_stats['errors'])}件")
    table.add_row("出力ファイル", output_file)
    
    console.print("\n")
    console.print(table)
    
    console.print("\n[green]✨ 全処理が完了しました！[/green]")


if __name__ == "__main__":
    main()