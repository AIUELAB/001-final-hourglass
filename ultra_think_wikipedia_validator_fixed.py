#!/usr/bin/env python3
"""
Ultra Think Wikipedia検証システム（修正版）
全人物のWikipedia掲載状況を高精度で並列検証し、非掲載者を自動削除
SQLiteスレッド問題を修正
"""

import pandas as pd
import json
import time
import requests
import concurrent.futures
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set, Any
import hashlib
from urllib.parse import quote
import re
import unicodedata
import traceback
from dataclasses import dataclass
from enum import Enum
import threading

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
    category: Optional[str] = None
    row_index: int = -1


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

        # カッコ内の別名抽出
        for name in [person.person_name, person.person_name_display, person.person_name_ja]:
            if name and '（' in name and '）' in name:
                # カッコ内の抽出
                match = re.search(r'（(.+?)）', name)
                if match:
                    aliases.append(match.group(1))
                # カッコを除去
                aliases.append(re.sub(r'（.+?）', '', name).strip())

        return list(set(filter(None, aliases)))


# グローバルキャッシュ（スレッド間で共有）
cache_lock = threading.Lock()
global_cache = {}


class WikipediaValidator:
    """修正版Wikipedia検証クラス"""

    def __init__(self):
        """初期化（スレッドごとに作成）"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Ultra Think Wikipedia Validator/3.0'
        })
        self.normalizer = NameNormalizer()

    def search_wikipedia(self, query: str, lang: str = 'ja') -> Tuple[bool, float]:
        """
        Wikipedia検索（多言語対応）

        Returns:
            (存在するか, 信頼度)
        """
        if not query:
            return False, 0.0

        # グローバルキャッシュチェック
        with cache_lock:
            if query in global_cache:
                return global_cache[query]

        base_url = f"https://{lang}.wikipedia.org/w/api.php"

        # 1. 完全一致でページが存在するか確認
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
                        with cache_lock:
                            global_cache[query] = result
                        return result

                # 2. 検索API
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
                        for result in search_results:
                            title = result.get('title', '')
                            # 完全一致
                            if title.lower() == query.lower():
                                result = (True, 0.9)
                                with cache_lock:
                                    global_cache[query] = result
                                return result
                            # 部分一致
                            elif query.lower() in title.lower() or title.lower() in query.lower():
                                result = (True, 0.7)
                                with cache_lock:
                                    global_cache[query] = result
                                return result

        except Exception as e:
            # エラーは無視して続行
            pass

        # 見つからなかった
        result = (False, 0.0)
        with cache_lock:
            global_cache[query] = result
        return result

    def validate_person(self, person: PersonInfo) -> ValidationResult:
        """
        人物のWikipedia掲載状況を検証

        Returns:
            ValidationResult: 検証結果
        """
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
            return ValidationResult.FOUND
        else:
            return ValidationResult.NOT_FOUND


def process_batch(persons: List[PersonInfo]) -> List[Tuple[int, ValidationResult]]:
    """バッチ処理（各スレッドで実行）"""
    # スレッドごとにバリデーターを作成
    validator = WikipediaValidator()
    results = []

    for person in persons:
        try:
            result = validator.validate_person(person)
            results.append((person.row_index, result))
        except Exception as e:
            results.append((person.row_index, ValidationResult.ERROR))

    return results


def process_database(csv_file: str, output_file: Optional[str] = None, test_mode: bool = False, test_limit: int = 100) -> pd.DataFrame:
    """
    データベース全体を処理

    Args:
        csv_file: 入力CSVファイル
        output_file: 出力CSVファイル（Noneの場合は自動生成）
        test_mode: テストモード（True時は制限された件数のみ処理）
        test_limit: テストモード時の処理件数上限

    Returns:
        処理済みのDataFrame
    """
    start_time = time.time()

    # データ読み込み
    if USE_RICH:
        test_indicator = "[TEST MODE] " if test_mode else ""
        console.print(Panel.fit(f"[bold cyan]{test_indicator}Ultra Think Wikipedia検証システム[/bold cyan]",
                               subtitle="Fixed Version 3.0"))
        console.print("\n[yellow]📂 データベース読み込み中...[/yellow]")

    df = pd.read_csv(csv_file, encoding='utf-8')
    original_total = len(df)

    # テストモードの場合は指定件数に制限
    if test_mode:
        df = df.head(test_limit)
        total_persons = len(df)
        if USE_RICH:
            console.print(f"[bold yellow]🧪 テストモード: {original_total}件中{total_persons}件を処理[/bold yellow]")
    else:
        total_persons = original_total

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

    # 統計情報
    stats = {
        'total_checked': 0,
        'found_on_wikipedia': 0,
        'not_found': 0,
        'errors': 0,
        'cached_results': 0,
        'deleted_count': 0
    }

    # 削除対象リスト
    persons_to_delete = []

    # 並列処理
    max_workers = 20
    batch_size = max(10, total_persons // (max_workers * 10))
    batches = [persons[i:i+batch_size] for i in range(0, len(persons), batch_size)]

    if USE_RICH:
        console.print(f"\n[cyan]🚀 並列処理開始: {max_workers}個のサブエージェント使用[/cyan]")
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
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_batch = {executor.submit(process_batch, batch): batch
                             for batch in batches}

            for future in concurrent.futures.as_completed(future_to_batch):
                batch = future_to_batch[future]
                try:
                    results = future.result()
                    for row_idx, result in results:
                        stats['total_checked'] += 1

                        if result == ValidationResult.FOUND:
                            stats['found_on_wikipedia'] += 1
                        elif result == ValidationResult.NOT_FOUND:
                            stats['not_found'] += 1
                            persons_to_delete.append(row_idx)
                        else:
                            stats['errors'] += 1

                    progress.update(task, advance=len(batch))
                except Exception as e:
                    stats['errors'] += len(batch)
                    progress.update(task, advance=len(batch))

    # 削除処理
    if persons_to_delete:
        if USE_RICH:
            console.print(f"\n[red]🗑️ {len(persons_to_delete)}件の非掲載人物を削除中...[/red]")

        # 削除前のバックアップ
        deleted_df = df.iloc[persons_to_delete]
        deleted_file = f"deleted_persons_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        deleted_df.to_csv(deleted_file, index=False, encoding='utf-8')

        # 削除実行
        df = df.drop(persons_to_delete)
        df = df.reset_index(drop=True)
        stats['deleted_count'] = len(persons_to_delete)

        if USE_RICH:
            console.print(f"[yellow]💾 削除データをバックアップ: {deleted_file}[/yellow]")

    # 処理時間計算
    processing_time = time.time() - start_time

    # 結果保存
    if output_file is None:
        mode_prefix = "TEST_" if test_mode else ""
        output_file = f"ultra_think_{mode_prefix}WIKIPEDIA_VALIDATED_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    df.to_csv(output_file, index=False, encoding='utf-8')

    # 統計レポート表示
    if USE_RICH:
        # リッチな表示
        table = Table(title="Wikipedia検証レポート", show_header=True, header_style="bold magenta")
        table.add_column("項目", style="cyan", width=30)
        table.add_column("値", justify="right", style="green")

        table.add_row("総検証数", f"{stats['total_checked']:,}")
        table.add_row("Wikipedia掲載", f"{stats['found_on_wikipedia']:,}")
        table.add_row("非掲載", f"{stats['not_found']:,}")
        table.add_row("エラー", f"{stats['errors']:,}")
        table.add_row("削除件数", f"{stats['deleted_count']:,}")
        table.add_row("処理時間", f"{processing_time:.2f}秒")
        table.add_row("出力ファイル", output_file)

        console.print("\n")
        console.print(table)

        if stats['deleted_count'] > 0:
            console.print(f"\n[bold red]⚠️ {stats['deleted_count']}件の非掲載人物を削除しました[/bold red]")

        console.print(f"\n[green]✅ 処理完了！[/green]")
    else:
        # 標準出力
        print("\n" + "="*50)
        print("Wikipedia検証レポート")
        print("="*50)
        print(f"総検証数: {stats['total_checked']}")
        print(f"Wikipedia掲載: {stats['found_on_wikipedia']}")
        print(f"非掲載: {stats['not_found']}")
        print(f"エラー: {stats['errors']}")
        print(f"削除件数: {stats['deleted_count']}")
        print(f"処理時間: {processing_time:.2f}秒")
        print(f"出力ファイル: {output_file}")
        print("="*50)

    return df


def main():
    """メイン実行関数"""
    import sys

    # コマンドライン引数チェック
    test_mode = "--test" in sys.argv

    if test_mode:
        # テストモードの場合はテスト用ファイルを使用
        csv_file = "ultra_think_test_100_records.csv"
        if not Path(csv_file).exists():
            print(f"❌ テスト用ファイル {csv_file} が見つかりません")
            print("先に最初の100件を抽出してください")
            return
    else:
        # 最新のCSVファイルを自動検出
        import glob
        csv_files = glob.glob("ultra_think_*.csv")
        if not csv_files:
            print("❌ ultra_think_*.csvファイルが見つかりません")
            return

        latest_csv = max(csv_files, key=lambda f: Path(f).stat().st_mtime)
        csv_file = latest_csv

    if USE_RICH:
        console.print(f"[cyan]📁 処理対象: {csv_file}[/cyan]")
        if test_mode:
            console.print("[bold yellow]🧪 テストモードで実行中...[/bold yellow]")
    else:
        print(f"処理対象: {csv_file}")
        if test_mode:
            print("🧪 テストモードで実行中...")

    # 処理実行
    result_df = process_database(csv_file, test_mode=test_mode)


if __name__ == "__main__":
    main()
