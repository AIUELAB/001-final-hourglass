from src.secure_config import config
#!/usr/bin/env python3
"""
Ultra Think Wikipedia検証システム
全人物のWikipedia掲載状況を並列検証し、非掲載者を自動削除
サブエージェント（並列処理）を活用した高速処理
"""

import pandas as pd
import json
import time
import requests
import concurrent.futures
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
import gspread
from google.oauth2.service_account import Credentials
import traceback
import hashlib
from urllib.parse import quote
import re

# リッチな出力用
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    from rich.table import Table
    console = Console()
    USE_RICH = True
except ImportError:
    USE_RICH = False
    print("Rich library not found. Using standard print.")


class WikipediaValidator:
    """Wikipedia検証クラス"""
    
    def __init__(self, use_parallel: bool = True, max_workers: int = 10):
        """
        Args:
            use_parallel: 並列処理を使用するか
            max_workers: 最大並列数（サブエージェント数）
        """
        self.use_parallel = use_parallel
        self.max_workers = max_workers
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Ultra Think Wikipedia Validator/1.0 (Educational Purpose)'
        })
        
        # キャッシュ（同じ名前を何度も検索しないため）
        self.search_cache = {}
        
        # 統計情報
        self.stats = {
            'total_checked': 0,
            'found_on_wikipedia': 0,
            'not_found': 0,
            'errors': 0,
            'deleted_count': 0,
            'processing_time': 0
        }
        
        # プレースホルダー候補
        self.placeholder_candidates = []
        
        # エラーログ
        self.error_log = []
        
    def search_wikipedia_ja(self, query: str) -> bool:
        """日本語Wikipediaで検索（完全一致優先）"""
        if query in self.search_cache:
            return self.search_cache[query]
        
        # まず完全一致でページが存在するか確認
        url = "https://ja.wikipedia.org/w/api.php"
        params = {
            'action': 'query',
            'format': 'json',
            'titles': query,
            'prop': 'info'
        }
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                pages = data.get('query', {}).get('pages', {})
                
                # ページIDが-1でなければ存在する
                for page_id, page_info in pages.items():
                    if page_id != '-1':
                        self.search_cache[query] = True
                        return True
                
                # 完全一致が見つからない場合は、検索APIでタイトル部分一致を確認
                params = {
                    'action': 'query',
                    'format': 'json',
                    'list': 'search',
                    'srsearch': f'intitle:{query}',  # タイトルに含まれる場合のみ
                    'srlimit': 5
                }
                
                response = self.session.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    results = data.get('query', {}).get('search', [])
                    
                    # 検索結果のタイトルに検索クエリが含まれているかチェック
                    for result in results:
                        title = result.get('title', '')
                        # タイトルに検索クエリが含まれている場合のみ有効
                        if query.lower() in title.lower():
                            self.search_cache[query] = True
                            return True
                
                self.search_cache[query] = False
                return False
                
        except Exception as e:
            self.error_log.append(f"JA Wikipedia error for '{query}': {str(e)}")
            return False
    
    def search_wikipedia_en(self, query: str) -> bool:
        """英語Wikipediaで検索（完全一致優先）"""
        cache_key = f"en_{query}"
        if cache_key in self.search_cache:
            return self.search_cache[cache_key]
        
        # まず完全一致でページが存在するか確認
        url = "https://en.wikipedia.org/w/api.php"
        params = {
            'action': 'query',
            'format': 'json',
            'titles': query,
            'prop': 'info'
        }
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                pages = data.get('query', {}).get('pages', {})
                
                # ページIDが-1でなければ存在する
                for page_id, page_info in pages.items():
                    if page_id != '-1':
                        self.search_cache[cache_key] = True
                        return True
                
                # 完全一致が見つからない場合は、検索APIでタイトル部分一致を確認
                params = {
                    'action': 'query',
                    'format': 'json',
                    'list': 'search',
                    'srsearch': f'intitle:{query}',  # タイトルに含まれる場合のみ
                    'srlimit': 5
                }
                
                response = self.session.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    results = data.get('query', {}).get('search', [])
                    
                    # 検索結果のタイトルに検索クエリが含まれているかチェック
                    for result in results:
                        title = result.get('title', '')
                        # タイトルに検索クエリが含まれている場合のみ有効
                        if query.lower() in title.lower():
                            self.search_cache[cache_key] = True
                            return True
                
                self.search_cache[cache_key] = False
                return False
                
        except Exception as e:
            self.error_log.append(f"EN Wikipedia error for '{query}': {str(e)}")
            return False
    
    def verify_person(self, person_data: Dict) -> Dict:
        """個人をWikipediaで検証"""
        result = {
            'person_id': person_data.get('person_id', ''),
            'person_name': person_data.get('person_name', ''),
            'occupation': person_data.get('occupation', ''),
            'found_on_wikipedia': False,
            'search_patterns': [],
            'verification_time': datetime.now().isoformat()
        }
        
        # 検索パターンを生成
        search_patterns = []
        
        # person_name
        if person_data.get('person_name'):
            search_patterns.append(person_data['person_name'])
            
        # person_name_display
        if person_data.get('person_name_display'):
            display_name = person_data['person_name_display']
            if display_name and display_name != person_data.get('person_name'):
                search_patterns.append(display_name)
                
        # person_name_ja
        if person_data.get('person_name_ja'):
            ja_name = person_data['person_name_ja']
            if ja_name and ja_name not in search_patterns:
                search_patterns.append(ja_name)
                
        # occupation付きの検索
        occupation = person_data.get('occupation', '')
        if occupation and len(search_patterns) > 0:
            search_patterns.append(f"{search_patterns[0]} {occupation}")
            
        result['search_patterns'] = search_patterns
        
        # 各パターンで検索
        for pattern in search_patterns:
            if not pattern:
                continue
                
            # 日本語Wikipediaで検索
            if self.search_wikipedia_ja(pattern):
                result['found_on_wikipedia'] = True
                result['found_pattern'] = pattern
                result['found_source'] = 'ja.wikipedia'
                break
                
            # 英語Wikipediaでも検索（グローバルな人物の場合）
            if self.search_wikipedia_en(pattern):
                result['found_on_wikipedia'] = True
                result['found_pattern'] = pattern
                result['found_source'] = 'en.wikipedia'
                break
            
            # APIレート制限対策
            time.sleep(0.1)
        
        return result
    
    def verify_batch(self, persons_batch: List[Dict]) -> List[Dict]:
        """バッチ単位で検証（サブエージェント用）"""
        results = []
        for person in persons_batch:
            try:
                result = self.verify_person(person)
                results.append(result)
                self.stats['total_checked'] += 1
                
                if result['found_on_wikipedia']:
                    self.stats['found_on_wikipedia'] += 1
                else:
                    self.stats['not_found'] += 1
                    self.placeholder_candidates.append(person)
                    
            except Exception as e:
                self.stats['errors'] += 1
                self.error_log.append(f"Error verifying {person.get('person_name', 'Unknown')}: {str(e)}")
                
        return results
    
    def verify_all_persons(self, df: pd.DataFrame, dry_run: bool = False) -> Tuple[pd.DataFrame, List[Dict]]:
        """全人物を検証"""
        start_time = time.time()
        
        if USE_RICH:
            console.print(Panel.fit(
                f"🔍 Wikipedia検証開始\n"
                f"対象: {len(df)}人\n"
                f"並列数: {self.max_workers if self.use_parallel else 1}\n"
                f"モード: {'ドライラン' if dry_run else '本番実行'}",
                title="Ultra Think Wikipedia Validator"
            ))
        else:
            print(f"\n=== Wikipedia検証開始 ===")
            print(f"対象: {len(df)}人")
        
        # データをリストに変換
        persons_data = df.to_dict('records')
        
        if self.use_parallel and len(persons_data) > 100:
            # 並列処理（サブエージェント活用）
            batch_size = len(persons_data) // self.max_workers + 1
            batches = [persons_data[i:i+batch_size] for i in range(0, len(persons_data), batch_size)]
            
            all_results = []
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                if USE_RICH:
                    with Progress(
                        SpinnerColumn(),
                        TextColumn("[progress.description]{task.description}"),
                        BarColumn(),
                        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                        TimeElapsedColumn(),
                        console=console
                    ) as progress:
                        task = progress.add_task(
                            f"[cyan]検証中...", 
                            total=len(persons_data)
                        )
                        
                        # 並列実行
                        futures = [executor.submit(self.verify_batch, batch) for batch in batches]
                        
                        for future in concurrent.futures.as_completed(futures):
                            try:
                                batch_results = future.result()
                                all_results.extend(batch_results)
                                progress.update(task, advance=len(batch_results))
                            except Exception as e:
                                self.error_log.append(f"Batch processing error: {str(e)}")
                else:
                    # Rich無しの場合
                    futures = [executor.submit(self.verify_batch, batch) for batch in batches]
                    for i, future in enumerate(concurrent.futures.as_completed(futures)):
                        batch_results = future.result()
                        all_results.extend(batch_results)
                        print(f"Progress: {len(all_results)}/{len(persons_data)}")
        else:
            # 逐次処理
            all_results = self.verify_batch(persons_data)
        
        # プレースホルダー（削除対象）の特定
        placeholder_ids = {p['person_id'] for p in self.placeholder_candidates}
        
        if dry_run:
            # ドライラン: 削除せずに結果を表示
            if USE_RICH:
                console.print(f"\n[yellow]ドライラン結果:[/yellow]")
                console.print(f"削除対象: {len(self.placeholder_candidates)}人")
            else:
                print(f"\nドライラン結果:")
                print(f"削除対象: {len(self.placeholder_candidates)}人")
                
            df_clean = df.copy()
        else:
            # 本番実行: 実際に削除
            df_clean = df[~df['person_id'].isin(placeholder_ids)].reset_index(drop=True)
            self.stats['deleted_count'] = len(self.placeholder_candidates)
        
        self.stats['processing_time'] = time.time() - start_time
        
        return df_clean, self.placeholder_candidates
    
    def generate_report(self) -> str:
        """検証レポートを生成"""
        report = []
        report.append("# Wikipedia検証レポート")
        report.append(f"\n生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"\n## 📊 統計情報")
        report.append(f"- 総検証数: {self.stats['total_checked']:,}人")
        report.append(f"- Wikipedia掲載: {self.stats['found_on_wikipedia']:,}人")
        report.append(f"- 非掲載（削除対象）: {self.stats['not_found']:,}人")
        report.append(f"- エラー: {self.stats['errors']:,}件")
        report.append(f"- 処理時間: {self.stats['processing_time']:.1f}秒")
        
        if self.stats['total_checked'] > 0:
            coverage = (self.stats['found_on_wikipedia'] / self.stats['total_checked']) * 100
            report.append(f"- Wikipedia掲載率: {coverage:.1f}%")
        
        report.append(f"\n## 🗑️ 削除対象（上位20件）")
        for i, person in enumerate(self.placeholder_candidates[:20], 1):
            report.append(f"{i}. {person.get('person_name', 'N/A')} - {person.get('occupation', 'N/A')}")
        
        if len(self.placeholder_candidates) > 20:
            report.append(f"\n... 他 {len(self.placeholder_candidates) - 20}件")
        
        if self.error_log:
            report.append(f"\n## ⚠️ エラーログ（最初の10件）")
            for error in self.error_log[:10]:
                report.append(f"- {error}")
        
        return "\n".join(report)


class GoogleSheetsSync:
    """Google Sheets同期クラス"""
    
    def __init__(self):
        self.client = None
        self.spreadsheet = None
        self.sheet = None
        self.init_client()
    
    def init_client(self):
        """Google Sheets APIクライアントを初期化"""
        try:
            scope = ['https://spreadsheets.google.com/feeds',
                     'https://www.googleapis.com/auth/drive']
            
            creds = Credentials.from_service_account_file(
                config.google_credentials_path,
                scopes=scope
            )
            
            self.client = gspread.authorize(creds)
            
            # sheets_config.jsonから設定を読み込み
            config_file = Path('sheets_config.json')
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    spreadsheet_id = config.get('spreadsheet_id')
                    
                    if spreadsheet_id:
                        self.spreadsheet = self.client.open_by_key(spreadsheet_id)
                        self.sheet = self.spreadsheet.sheet1
                        
                        if USE_RICH:
                            console.print("[green]✅ Google Sheets接続成功[/green]")
                        else:
                            print("Google Sheets接続成功")
                            
        except Exception as e:
            print(f"Google Sheets初期化エラー: {e}")
    
    def sync_data(self, df: pd.DataFrame, sheet_name: str = None):
        """データをGoogle Sheetsに同期"""
        if not self.sheet:
            print("Google Sheetsが初期化されていません")
            return
            
        try:
            # スプレッドシート名を更新
            if sheet_name:
                self.spreadsheet.update_title(sheet_name)
            
            # データを更新
            self.sheet.clear()
            data = [df.columns.tolist()] + df.values.tolist()
            self.sheet.update('A1', data)
            
            # 設定ファイルを更新
            config_file = Path('sheets_config.json')
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                config['last_sync'] = datetime.now().isoformat()
                config['sheet_name'] = sheet_name or config.get('sheet_name', '')
                
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
                    
            if USE_RICH:
                console.print(f"[green]✅ Google Sheets同期完了: {len(df)}行[/green]")
            else:
                print(f"Google Sheets同期完了: {len(df)}行")
                
        except Exception as e:
            print(f"同期エラー: {e}")


def main():
    """メイン処理"""
    # コマンドライン引数を処理
    import argparse
    parser = argparse.ArgumentParser(description='Ultra Think Wikipedia Validator')
    parser.add_argument('--dry-run', action='store_true', help='削除せずに結果のみ表示')
    parser.add_argument('--parallel', type=int, default=10, help='並列数（デフォルト: 10）')
    parser.add_argument('--input', type=str, help='入力CSVファイル（デフォルト: 最新のultra_think_*.csv）')
    parser.add_argument('--sync-sheets', action='store_true', default=True, help='Google Sheetsに同期')
    args = parser.parse_args()
    
    # 入力ファイルを決定
    if args.input:
        csv_file = args.input
    else:
        # 最新のultra_think_*.csvを自動検出
        csv_files = list(Path('.').glob('ultra_think_*.csv'))
        if not csv_files:
            print("ultra_think_*.csvファイルが見つかりません")
            return
        csv_file = max(csv_files, key=lambda p: p.stat().st_mtime)
    
    if USE_RICH:
        console.print(f"[cyan]入力ファイル: {csv_file}[/cyan]")
    else:
        print(f"入力ファイル: {csv_file}")
    
    # データ読み込み
    try:
        df = pd.read_csv(csv_file)
        print(f"データ読み込み完了: {len(df)}行")
    except Exception as e:
        print(f"CSVファイル読み込みエラー: {e}")
        return
    
    # バックアップ作成
    if not args.dry_run:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"backup_{csv_file}_{timestamp}"
        df.to_csv(backup_file, index=False)
        print(f"バックアップ作成: {backup_file}")
    
    # Wikipedia検証実行
    validator = WikipediaValidator(use_parallel=True, max_workers=args.parallel)
    df_clean, removed_persons = validator.verify_all_persons(df, dry_run=args.dry_run)
    
    # レポート生成
    report = validator.generate_report()
    
    # レポートを保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"wikipedia_verification_report_{timestamp}.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"\nレポート保存: {report_file}")
    
    if not args.dry_run and removed_persons:
        # 削除リストを保存
        removed_df = pd.DataFrame(removed_persons)
        removed_file = f"removed_placeholders_{timestamp}.csv"
        removed_df.to_csv(removed_file, index=False)
        print(f"削除リスト保存: {removed_file}")
        
        # クリーンなデータを保存
        output_file = f"ultra_think_VERIFIED_{timestamp}.csv"
        df_clean.to_csv(output_file, index=False)
        print(f"検証済みデータ保存: {output_file}")
        
        # Google Sheetsに同期
        if args.sync_sheets:
            sync = GoogleSheetsSync()
            sheet_name = f"Ultra Think VERIFIED {timestamp}"
            sync.sync_data(df_clean, sheet_name)
        
        # sheets_config.jsonを更新
        config_file = Path('sheets_config.json')
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            config['csv_file'] = output_file
            config['sheet_name'] = sheet_name
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
    
    # サマリー表示
    if USE_RICH:
        # 結果テーブル
        table = Table(title="検証結果サマリー")
        table.add_column("項目", style="cyan")
        table.add_column("値", style="green")
        
        table.add_row("総検証数", f"{validator.stats['total_checked']:,}人")
        table.add_row("Wikipedia掲載", f"{validator.stats['found_on_wikipedia']:,}人")
        table.add_row("削除対象", f"{validator.stats['not_found']:,}人")
        table.add_row("削除済み", f"{validator.stats['deleted_count']:,}人" if not args.dry_run else "0人（ドライラン）")
        table.add_row("処理時間", f"{validator.stats['processing_time']:.1f}秒")
        
        console.print(table)
    else:
        print("\n=== 検証結果サマリー ===")
        print(f"総検証数: {validator.stats['total_checked']:,}人")
        print(f"Wikipedia掲載: {validator.stats['found_on_wikipedia']:,}人")
        print(f"削除対象: {validator.stats['not_found']:,}人")
        print(f"処理時間: {validator.stats['processing_time']:.1f}秒")


if __name__ == "__main__":
    main()