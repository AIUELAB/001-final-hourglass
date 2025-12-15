#!/usr/bin/env python3
"""
Ultra Think Wikipedia検証システム（強化版）
全人物のWikipedia掲載状況を高精度で並列検証し、非掲載者を自動削除
サブエージェント（並列処理）を活用した超高速処理
"""

import pandas as pd
import json
import time
import requests
import concurrent.futures
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set, Any
import sqlite3
from src.database_utils import get_connection
import hashlib
from urllib.parse import quote
import re
import unicodedata
import traceback
from dataclasses import dataclass
from enum import Enum

# リッチな出力用
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    from rich.table import Table
    from rich.live import Live
    from rich.layout import Layout
    from rich.align import Align
    console = Console()
    USE_RICH = True
except ImportError:
    USE_RICH = False
    print("Rich library not found. Using standard print.")


class ValidationResult(Enum):
    """検証結果の列挙型"""
    FOUND = "found"
    NOT_FOUND = "not_found"
    ERROR = "error"
    CACHED = "cached"


@dataclass
class PersonInfo:
    """人物情報データクラス"""
    person_id: str
    person_name: str
    person_name_display: str
    person_name_ja: str
    occupation: str
    nationality: Optional[str] = None
    birth_year: Optional[int] = None
    death_year: Optional[int] = None
    category: Optional[str] = None
    row_index: int = -1


class WikipediaSearchCache:
    """SQLiteベースの永続キャッシュシステム"""

    def __init__(self, cache_file: str = "wikipedia_cache.db"):
        self.cache_file = cache_file
        self.conn = get_connection(self.cache_file)
        self.create_table()

    def create_table(self):
        """キャッシュテーブルを作成"""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS search_cache (
                query_hash TEXT PRIMARY KEY,
                query TEXT,
                result INTEGER,
                confidence REAL,
                checked_at TIMESTAMP,
                details TEXT
            )
        """)
        self.conn.commit()

    def get(self, query: str, max_age_days: int = 30) -> Optional[Tuple[bool, float]]:
        """キャッシュから検索結果を取得"""
        query_hash = hashlib.md5(query.encode()).hexdigest()
        cursor = self.conn.execute("""
            SELECT result, confidence, checked_at
            FROM search_cache
            WHERE query_hash = ?
        """, (query_hash,))

        result = cursor.fetchone()
        if result:
            result_bool, confidence, checked_at = result
            # 有効期限チェック
            checked_date = datetime.fromisoformat(checked_at)
            age = (datetime.now() - checked_date).days
            if age <= max_age_days:
                return bool(result_bool), confidence
        return None

    def set(self, query: str, result: bool, confidence: float = 1.0, details: str = ""):
        """検索結果をキャッシュに保存"""
        query_hash = hashlib.md5(query.encode()).hexdigest()
        self.conn.execute("""
            INSERT OR REPLACE INTO search_cache
            (query_hash, query, result, confidence, checked_at, details)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (query_hash, query, int(result), confidence, datetime.now().isoformat(), details))
        self.conn.commit()

    def close(self):
        """データベース接続を閉じる"""
        self.conn.close()


class NameNormalizer:
    """名前の正規化と別名生成クラス"""

    @staticmethod
    def normalize_japanese(name: str) -> List[str]:
        """日本語名の正規化と別名生成"""
        if not name:
            return []

        variations = [name]

        # ひらがな・カタカナの相互変換
        hiragana = ''.join([chr(ord(char) - 96) if 'ァ' <= char <= 'ヶ' else char for char in name])
        katakana = ''.join([chr(ord(char) + 96) if 'ぁ' <= char <= 'ゖ' else char for char in name])

        if hiragana != name:
            variations.append(hiragana)
        if katakana != name:
            variations.append(katakana)

        # 長音符の処理
        variations.append(name.replace('ー', ''))
        variations.append(name.replace('ー', '-'))

        # スペースの処理
        variations.append(name.replace(' ', ''))
        variations.append(name.replace('　', ''))
        variations.append(name.replace('　', ' '))

        # 全角・半角の統一
        normalized = unicodedata.normalize('NFKC', name)
        if normalized != name:
            variations.append(normalized)

        # 「・」の処理
        variations.append(name.replace('・', ''))
        variations.append(name.replace('・', ' '))

        # ユニークなリストを返す
        return list(set(filter(None, variations)))

    @staticmethod
    def generate_aliases(person: PersonInfo) -> List[str]:
        """人物情報から別名候補を生成"""
        aliases = []

        # 基本名称
        if person.person_name:
            aliases.extend(NameNormalizer.normalize_japanese(person.person_name))

        if person.person_name_display:
            aliases.extend(NameNormalizer.normalize_japanese(person.person_name_display))

        if person.person_name_ja:
            aliases.extend(NameNormalizer.normalize_japanese(person.person_name_ja))

        # 職業を含む検索（例：「歌手 山田太郎」）
        if person.occupation and person.person_name_ja:
            aliases.append(f"{person.occupation} {person.person_name_ja}")

        # カッコ内の別名抽出（例：「山田太郎（やまだたろう）」）
        for name in [person.person_name, person.person_name_display, person.person_name_ja]:
            if name and '（' in name and '）' in name:
                # カッコ内の抽出
                match = re.search(r'（(.+?)）', name)
                if match:
                    aliases.append(match.group(1))
                # カッコを除去
                aliases.append(re.sub(r'（.+?）', '', name).strip())

        return list(set(filter(None, aliases)))


class EnhancedWikipediaValidator:
    """強化版Wikipedia検証クラス"""

    def __init__(self, use_parallel: bool = True, max_workers: int = 20, use_cache: bool = True):
        """
        Args:
            use_parallel: 並列処理を使用するか
            max_workers: 最大並列数（サブエージェント数）
            use_cache: 永続キャッシュを使用するか
        """
        self.use_parallel = use_parallel
        self.max_workers = max_workers
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Ultra Think Wikipedia Validator Enhanced/2.0'
        })

        # キャッシュシステム
        self.cache = WikipediaSearchCache() if use_cache else None

        # 統計情報
        self.stats = {
            'total_checked': 0,
            'found_on_wikipedia': 0,
            'not_found': 0,
            'errors': 0,
            'cached_results': 0,
            'deleted_count': 0,
            'processing_time': 0
        }

        # 削除対象リスト
        self.persons_to_delete = []

        # エラーログ
        self.error_log = []

        # 名前正規化ツール
        self.normalizer = NameNormalizer()

    def search_wikipedia(self, query: str, lang: str = 'ja') -> Tuple[bool, float]:
        """
        Wikipedia検索（多言語対応）

        Returns:
            (存在するか, 信頼度)
        """
        if not query:
            return False, 0.0

        # キャッシュチェック
        if self.cache:
            cached = self.cache.get(query)
            if cached:
                self.stats['cached_results'] += 1
                return cached

        base_url = f"https://{lang}.wikipedia.org/w/api.php"

        # 1. まず完全一致でページが存在するか確認
        params = {
            'action': 'query',
            'format': 'json',
            'titles': query,
            'prop': 'info'
        }

        try:
            response = self.session.get(base_url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                pages = data.get('query', {}).get('pages', {})

                for page_id, page_info in pages.items():
                    if page_id != '-1':
                        # 完全一致で見つかった
                        result = (True, 1.0)
                        if self.cache:
                            self.cache.set(query, result[0], result[1])
                        return result

                # 2. 完全一致が見つからない場合は検索API
                search_params = {
                    'action': 'query',
                    'format': 'json',
                    'list': 'search',
                    'srsearch': query,
                    'srlimit': 5
                }

                response = self.session.get(base_url, params=search_params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    search_results = data.get('query', {}).get('search', [])

                    if search_results:
                        # タイトルの類似度を計算
                        for result in search_results:
                            title = result.get('title', '')
                            # 完全一致
                            if title.lower() == query.lower():
                                result = (True, 0.9)
                                if self.cache:
                                    self.cache.set(query, result[0], result[1])
                                return result
                            # 部分一致
                            elif query.lower() in title.lower() or title.lower() in query.lower():
                                result = (True, 0.7)
                                if self.cache:
                                    self.cache.set(query, result[0], result[1])
                                return result

        except Exception as e:
            self.error_log.append(f"Error searching '{query}': {str(e)}")

        # 見つからなかった
        result = (False, 0.0)
        if self.cache:
            self.cache.set(query, result[0], result[1])
        return result

    def validate_person(self, person: PersonInfo) -> ValidationResult:
        """
        人物のWikipedia掲載状況を検証

        Returns:
            ValidationResult: 検証結果
        """
        self.stats['total_checked'] += 1

        # 別名候補を生成
        aliases = self.normalizer.generate_aliases(person)

        # すべての名前候補で検索
        best_result = (False, 0.0)

        for alias in aliases[:10]:  # 最大10個の別名で検索
            result = self.search_wikipedia(alias, lang='ja')
            if result[1] > best_result[1]:
                best_result = result

            # 信頼度が高い結果が見つかったら終了
            if best_result[1] >= 0.9:
                break

        # 英語版でも検索（日本語で見つからない場合）
        if best_result[1] < 0.5 and person.person_name:
            en_result = self.search_wikipedia(person.person_name, lang='en')
            if en_result[1] > best_result[1]:
                best_result = en_result

        # 結果の判定
        if best_result[0] and best_result[1] >= 0.5:
            self.stats['found_on_wikipedia'] += 1
            return ValidationResult.FOUND
        else:
            self.stats['not_found'] += 1
            self.persons_to_delete.append(person.row_index)
            return ValidationResult.NOT_FOUND

    def process_batch(self, persons: List[PersonInfo]) -> List[ValidationResult]:
        """バッチ処理（並列処理用）"""
        results = []
        for person in persons:
            try:
                result = self.validate_person(person)
                results.append(result)
            except Exception as e:
                self.stats['errors'] += 1
                self.error_log.append(f"Error processing {person.person_name}: {str(e)}")
                results.append(ValidationResult.ERROR)
        return results

    def process_database(self, csv_file: str, output_file: Optional[str] = None) -> pd.DataFrame:
        """
        データベース全体を処理

        Args:
            csv_file: 入力CSVファイル
            output_file: 出力CSVファイル（Noneの場合は自動生成）

        Returns:
            処理済みのDataFrame
        """
        start_time = time.time()

        # データ読み込み
        if USE_RICH:
            console.print(Panel.fit("[bold cyan]Ultra Think Wikipedia検証システム[/bold cyan]",
                                   subtitle="Enhanced Version 2.0"))
            console.print("\n[yellow]📂 データベース読み込み中...[/yellow]")

        df = pd.read_csv(csv_file, encoding='utf-8')
        total_persons = len(df)

        if USE_RICH:
            console.print(f"[green]✅ {total_persons}件の人物データを読み込みました[/green]")

        # PersonInfoオブジェクトのリストを作成
        persons = []
        for idx, row in df.iterrows():
            person = PersonInfo(
                person_id=str(row.get('person_id', '')),
                person_name=str(row.get('person_name', '')),
                person_name_display=str(row.get('person_name_display', '')),
                person_name_ja=str(row.get('person_name_ja', '')),
                occupation=str(row.get('occupation', '')),
                nationality=str(row.get('nationality', '')),
                birth_year=row.get('birth_year') if pd.notna(row.get('birth_year')) else None,
                category=str(row.get('category', '')),
                row_index=idx
            )
            persons.append(person)

        # 並列処理の設定
        if self.use_parallel:
            # バッチサイズを動的に決定
            batch_size = max(10, total_persons // (self.max_workers * 10))
            batches = [persons[i:i+batch_size] for i in range(0, len(persons), batch_size)]

            if USE_RICH:
                console.print(f"\n[cyan]🚀 並列処理開始: {self.max_workers}個のサブエージェント使用[/cyan]")
                console.print(f"[cyan]   バッチ数: {len(batches)}, バッチサイズ: {batch_size}[/cyan]")

            # プログレスバーの設定
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn()
            ) as progress:

                task = progress.add_task("[cyan]Wikipedia検証中...", total=total_persons)

                # 並列実行
                with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    future_to_batch = {executor.submit(self.process_batch, batch): batch
                                     for batch in batches}

                    for future in concurrent.futures.as_completed(future_to_batch):
                        batch = future_to_batch[future]
                        try:
                            results = future.result()
                            progress.update(task, advance=len(batch))
                        except Exception as e:
                            self.error_log.append(f"Batch processing error: {str(e)}")
                            progress.update(task, advance=len(batch))

        else:
            # 逐次処理
            if USE_RICH:
                console.print("\n[cyan]逐次処理モードで実行中...[/cyan]")

            for person in persons:
                self.validate_person(person)

        # 削除処理
        if self.persons_to_delete:
            if USE_RICH:
                console.print(f"\n[red]🗑️ {len(self.persons_to_delete)}件の非掲載人物を削除中...[/red]")

            # 削除前のバックアップ
            deleted_df = df.iloc[self.persons_to_delete]
            deleted_file = f"deleted_persons_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            deleted_df.to_csv(deleted_file, index=False, encoding='utf-8')

            # 削除実行
            df = df.drop(self.persons_to_delete)
            df = df.reset_index(drop=True)
            self.stats['deleted_count'] = len(self.persons_to_delete)

            if USE_RICH:
                console.print(f"[yellow]💾 削除データをバックアップ: {deleted_file}[/yellow]")

        # 処理時間計算
        self.stats['processing_time'] = time.time() - start_time

        # 結果保存
        if output_file is None:
            output_file = f"ultra_think_WIKIPEDIA_VALIDATED_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        df.to_csv(output_file, index=False, encoding='utf-8')

        # 統計レポート表示
        self.display_report(output_file)

        # キャッシュを閉じる
        if self.cache:
            self.cache.close()

        return df

    def display_report(self, output_file: str):
        """処理結果レポートを表示"""
        if USE_RICH:
            # リッチな表示
            table = Table(title="Wikipedia検証レポート", show_header=True, header_style="bold magenta")
            table.add_column("項目", style="cyan", width=30)
            table.add_column("値", justify="right", style="green")

            table.add_row("総検証数", f"{self.stats['total_checked']:,}")
            table.add_row("Wikipedia掲載", f"{self.stats['found_on_wikipedia']:,}")
            table.add_row("非掲載", f"{self.stats['not_found']:,}")
            table.add_row("キャッシュヒット", f"{self.stats['cached_results']:,}")
            table.add_row("エラー", f"{self.stats['errors']:,}")
            table.add_row("削除件数", f"{self.stats['deleted_count']:,}")
            table.add_row("処理時間", f"{self.stats['processing_time']:.2f}秒")
            table.add_row("出力ファイル", output_file)

            console.print("\n")
            console.print(table)

            if self.stats['deleted_count'] > 0:
                console.print(f"\n[bold red]⚠️ {self.stats['deleted_count']}件の非掲載人物を削除しました[/bold red]")

            console.print(f"\n[green]✅ 処理完了！[/green]")
        else:
            # 標準出力
            print("\n" + "="*50)
            print("Wikipedia検証レポート")
            print("="*50)
            print(f"総検証数: {self.stats['total_checked']}")
            print(f"Wikipedia掲載: {self.stats['found_on_wikipedia']}")
            print(f"非掲載: {self.stats['not_found']}")
            print(f"キャッシュヒット: {self.stats['cached_results']}")
            print(f"エラー: {self.stats['errors']}")
            print(f"削除件数: {self.stats['deleted_count']}")
            print(f"処理時間: {self.stats['processing_time']:.2f}秒")
            print(f"出力ファイル: {output_file}")
            print("="*50)


def main():
    """メイン実行関数"""
    # 最新のCSVファイルを自動検出
    import glob
    csv_files = glob.glob("ultra_think_*.csv")
    if not csv_files:
        print("❌ ultra_think_*.csvファイルが見つかりません")
        return

    latest_csv = max(csv_files, key=lambda f: Path(f).stat().st_mtime)

    if USE_RICH:
        console.print(f"[cyan]📁 処理対象: {latest_csv}[/cyan]")
    else:
        print(f"処理対象: {latest_csv}")

    # バリデーター作成
    validator = EnhancedWikipediaValidator(
        use_parallel=True,
        max_workers=20,  # サブエージェント数
        use_cache=True
    )

    # 処理実行
    result_df = validator.process_database(latest_csv)

    # エラーログ出力
    if validator.error_log:
        error_file = f"wikipedia_validation_errors_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(error_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(validator.error_log))
        if USE_RICH:
            console.print(f"[yellow]⚠️ エラーログ: {error_file}[/yellow]")


if __name__ == "__main__":
    main()
