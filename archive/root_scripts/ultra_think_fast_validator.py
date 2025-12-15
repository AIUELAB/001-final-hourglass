#!/usr/bin/env python3
"""
Ultra Think 高速ローカル辞書ベース検証システム
Wikipedia API不要で超高速検証を実現
"""

import pandas as pd
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
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


class ValidationDecision(Enum):
    """検証判定結果"""
    KEEP = "keep"           # 維持（有名人）
    DELETE = "delete"       # 削除（非有名人）
    REVIEW = "review"       # 要確認
    WHITELIST = "whitelist" # ホワイトリスト該当
    BLACKLIST = "blacklist" # ブラックリスト該当


@dataclass
class PersonValidation:
    """人物検証結果"""
    person_id: str
    person_name: str
    decision: ValidationDecision
    confidence: float
    reason: str
    row_index: int


class UltraThinkFastValidator:
    """超高速ローカル辞書ベース検証エンジン"""

    def __init__(self):
        """初期化"""
        self.whitelist = {}
        self.blacklist_patterns = {}
        self.load_dictionaries()

        # 統計情報
        self.stats = {
            'total_processed': 0,
            'whitelist_hits': 0,
            'blacklist_hits': 0,
            'pattern_matches': 0,
            'reviews_needed': 0,
            'kept': 0,
            'deleted': 0,
            'processing_time': 0
        }

    def load_dictionaries(self):
        """辞書ファイルを読み込み"""
        # ホワイトリストを読み込み
        whitelist_file = "famous_persons_whitelist.json"
        if Path(whitelist_file).exists():
            with open(whitelist_file, 'r', encoding='utf-8') as f:
                self.whitelist = json.load(f)
            if USE_RICH:
                console.print(f"[green]✅ ホワイトリスト読み込み: {len(self.whitelist)}件[/green]")
        else:
            if USE_RICH:
                console.print(f"[yellow]⚠️ ホワイトリストが見つかりません[/yellow]")

        # ブラックパターンを読み込み
        blacklist_file = "blacklist_patterns.json"
        if Path(blacklist_file).exists():
            with open(blacklist_file, 'r', encoding='utf-8') as f:
                self.blacklist_patterns = json.load(f)
            if USE_RICH:
                console.print(f"[green]✅ ブラックパターン読み込み完了[/green]")
        else:
            if USE_RICH:
                console.print(f"[yellow]⚠️ ブラックパターンが見つかりません[/yellow]")

    def normalize_name(self, name: str) -> List[str]:
        """名前を正規化して複数のバリエーションを生成"""
        if not name or name == 'nan':
            return []

        variations = [name]

        # スペースの除去
        variations.append(name.replace(' ', ''))
        variations.append(name.replace('　', ''))

        # カッコの処理
        if '（' in name and '）' in name:
            # カッコ内を抽出
            match = re.search(r'（(.+?)）', name)
            if match:
                variations.append(match.group(1))
            # カッコを除去
            variations.append(re.sub(r'（.+?）', '', name).strip())

        # 「・」の処理
        variations.append(name.replace('・', ''))
        variations.append(name.replace('・', ' '))

        return list(set(filter(None, variations)))

    def check_whitelist(self, person_names: List[str]) -> Tuple[bool, float, str]:
        """ホワイトリストチェック"""
        for name in person_names:
            if name in self.whitelist:
                entry = self.whitelist[name]
                confidence = 1.0  # ホワイトリストは確実
                reason = f"Wikipedia掲載確認済み（{name}）"
                return True, confidence, reason
        return False, 0.0, ""

    def check_blacklist_patterns(self, occupation: str, category: str) -> Tuple[bool, float, str]:
        """ブラックパターンチェック"""
        if not self.blacklist_patterns:
            return False, 0.0, ""

        rules = self.blacklist_patterns.get('rules', {})
        auto_delete = rules.get('auto_delete', {})

        # 職業による自動削除
        if occupation in auto_delete.get('occupations', []):
            return True, 0.9, f"削除対象職業: {occupation}"

        # 職業パターンマッチング
        for pattern in auto_delete.get('patterns', []):
            if pattern['type'] == 'suffix' and occupation.endswith(pattern['value']):
                return True, pattern['confidence'], f"削除パターン: *{pattern['value']}"
            elif pattern['type'] == 'contains' and pattern['value'] in occupation:
                return True, pattern['confidence'], f"削除パターン: *{pattern['value']}*"

        # カテゴリによる判定
        category_patterns = self.blacklist_patterns.get('category_patterns', {})
        if category in category_patterns:
            cat_info = category_patterns[category]
            if cat_info.get('rate', 0) > 0.3:  # 30%以上削除されたカテゴリ
                return True, 0.7, f"高削除率カテゴリ: {category}"

        return False, 0.0, ""

    def validate_person(self, row: pd.Series, row_index: int) -> PersonValidation:
        """個別人物の検証"""
        self.stats['total_processed'] += 1

        # 名前の取得と正規化
        person_names = []
        if pd.notna(row.get('person_name_ja')):
            person_names.extend(self.normalize_name(str(row['person_name_ja'])))
        if pd.notna(row.get('person_name_display')):
            person_names.extend(self.normalize_name(str(row['person_name_display'])))
        if pd.notna(row.get('person_name')):
            person_names.extend(self.normalize_name(str(row['person_name'])))

        person_names = list(set(filter(None, person_names)))

        # 職業とカテゴリ
        occupation = str(row.get('occupation', '')) if pd.notna(row.get('occupation')) else ''
        category = str(row.get('category', '')) if pd.notna(row.get('category')) else ''

        # 1. ホワイトリストチェック（最優先）
        is_whitelist, confidence, reason = self.check_whitelist(person_names)
        if is_whitelist:
            self.stats['whitelist_hits'] += 1
            self.stats['kept'] += 1
            return PersonValidation(
                person_id=str(row.get('person_id', '')),
                person_name=person_names[0] if person_names else '',
                decision=ValidationDecision.WHITELIST,
                confidence=confidence,
                reason=reason,
                row_index=row_index
            )

        # 2. ブラックパターンチェック
        is_blacklist, confidence, reason = self.check_blacklist_patterns(occupation, category)
        if is_blacklist and confidence >= 0.8:
            self.stats['blacklist_hits'] += 1
            self.stats['deleted'] += 1
            return PersonValidation(
                person_id=str(row.get('person_id', '')),
                person_name=person_names[0] if person_names else '',
                decision=ValidationDecision.BLACKLIST,
                confidence=confidence,
                reason=reason,
                row_index=row_index
            )

        # 3. 認知度による判定
        name_recognition = float(row.get('name_recognition', 0)) if pd.notna(row.get('name_recognition')) else 0

        if name_recognition >= 60:
            # 高認知度は維持
            self.stats['kept'] += 1
            return PersonValidation(
                person_id=str(row.get('person_id', '')),
                person_name=person_names[0] if person_names else '',
                decision=ValidationDecision.KEEP,
                confidence=0.8,
                reason=f"高認知度: {name_recognition:.1f}%",
                row_index=row_index
            )
        elif name_recognition <= 20:
            # 低認知度は削除
            self.stats['deleted'] += 1
            return PersonValidation(
                person_id=str(row.get('person_id', '')),
                person_name=person_names[0] if person_names else '',
                decision=ValidationDecision.DELETE,
                confidence=0.7,
                reason=f"低認知度: {name_recognition:.1f}%",
                row_index=row_index
            )

        # 4. その他は要確認
        self.stats['reviews_needed'] += 1
        return PersonValidation(
            person_id=str(row.get('person_id', '')),
            person_name=person_names[0] if person_names else '',
            decision=ValidationDecision.REVIEW,
            confidence=0.5,
            reason="追加検証が必要",
            row_index=row_index
        )

    def process_database(self, csv_file: str, output_file: Optional[str] = None) -> pd.DataFrame:
        """データベース全体を処理"""
        start_time = time.time()

        # データ読み込み
        if USE_RICH:
            console.print(Panel.fit("[bold cyan]Ultra Think 高速検証システム[/bold cyan]",
                                   subtitle="Local Dictionary Based v1.0"))
            console.print("\n[yellow]📂 データベース読み込み中...[/yellow]")

        df = pd.read_csv(csv_file, encoding='utf-8')
        total_persons = len(df)

        if USE_RICH:
            console.print(f"[green]✅ {total_persons}件の人物データを読み込みました[/green]")

        # 検証結果リスト
        validations = []
        rows_to_delete = []

        # プログレスバーの設定
        if USE_RICH:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn()
            ) as progress:

                task = progress.add_task("[cyan]高速検証中...", total=total_persons)

                for idx, row in df.iterrows():
                    validation = self.validate_person(row, idx)
                    validations.append(validation)

                    if validation.decision in [ValidationDecision.DELETE, ValidationDecision.BLACKLIST]:
                        rows_to_delete.append(idx)

                    progress.update(task, advance=1)
        else:
            # プログレスバーなし
            for idx, row in df.iterrows():
                validation = self.validate_person(row, idx)
                validations.append(validation)

                if validation.decision in [ValidationDecision.DELETE, ValidationDecision.BLACKLIST]:
                    rows_to_delete.append(idx)

        # 削除処理
        if rows_to_delete:
            if USE_RICH:
                console.print(f"\n[red]🗑️ {len(rows_to_delete)}件の人物を削除中...[/red]")

            # 削除前のバックアップ
            deleted_df = df.iloc[rows_to_delete]
            deleted_file = f"fast_deleted_persons_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            deleted_df.to_csv(deleted_file, index=False, encoding='utf-8')

            # 削除実行
            df = df.drop(rows_to_delete)
            df = df.reset_index(drop=True)

            if USE_RICH:
                console.print(f"[yellow]💾 削除データをバックアップ: {deleted_file}[/yellow]")

        # 処理時間計算
        self.stats['processing_time'] = time.time() - start_time

        # 結果保存
        if output_file is None:
            output_file = f"ultra_think_FAST_VALIDATED_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        df.to_csv(output_file, index=False, encoding='utf-8')

        # 統計レポート表示
        self.display_report(output_file, validations)

        return df

    def display_report(self, output_file: str, validations: List[PersonValidation]):
        """処理結果レポートを表示"""
        if USE_RICH:
            # リッチな表示
            table = Table(title="高速検証レポート", show_header=True, header_style="bold magenta")
            table.add_column("項目", style="cyan", width=30)
            table.add_column("値", justify="right", style="green")

            table.add_row("総処理数", f"{self.stats['total_processed']:,}")
            table.add_row("ホワイトリストヒット", f"{self.stats['whitelist_hits']:,}")
            table.add_row("ブラックリストヒット", f"{self.stats['blacklist_hits']:,}")
            table.add_row("維持", f"{self.stats['kept']:,}")
            table.add_row("削除", f"{self.stats['deleted']:,}")
            table.add_row("要確認", f"{self.stats['reviews_needed']:,}")
            table.add_row("処理時間", f"{self.stats['processing_time']:.2f}秒")
            table.add_row("処理速度", f"{self.stats['total_processed']/self.stats['processing_time']:.0f}件/秒")
            table.add_row("出力ファイル", output_file)

            console.print("\n")
            console.print(table)

            # 決定内訳
            decision_counts = {}
            for v in validations:
                decision_counts[v.decision.value] = decision_counts.get(v.decision.value, 0) + 1

            console.print("\n[bold cyan]決定内訳:[/bold cyan]")
            for decision, count in decision_counts.items():
                percentage = (count / len(validations)) * 100
                console.print(f"  {decision}: {count:,}件 ({percentage:.1f}%)")

            console.print(f"\n[green]✅ 高速検証完了！[/green]")

            # APIとの比較
            api_time = 574.63  # Wikipedia API検証の実際の時間
            speedup = api_time / self.stats['processing_time']
            console.print(f"\n[bold yellow]⚡ 性能比較:[/bold yellow]")
            console.print(f"  API検証: {api_time:.0f}秒")
            console.print(f"  高速検証: {self.stats['processing_time']:.2f}秒")
            console.print(f"  高速化: [bold green]{speedup:.0f}倍[/bold green]")
        else:
            # 標準出力
            print("\n" + "="*50)
            print("高速検証レポート")
            print("="*50)
            print(f"総処理数: {self.stats['total_processed']}")
            print(f"ホワイトリストヒット: {self.stats['whitelist_hits']}")
            print(f"ブラックリストヒット: {self.stats['blacklist_hits']}")
            print(f"維持: {self.stats['kept']}")
            print(f"削除: {self.stats['deleted']}")
            print(f"要確認: {self.stats['reviews_needed']}")
            print(f"処理時間: {self.stats['processing_time']:.2f}秒")
            print(f"処理速度: {self.stats['total_processed']/self.stats['processing_time']:.0f}件/秒")
            print(f"出力ファイル: {output_file}")
            print("="*50)


def main():
    """メイン実行関数"""
    import argparse

    parser = argparse.ArgumentParser(description='Ultra Think 高速検証システム')
    parser.add_argument('input', nargs='?', help='入力CSVファイル')
    parser.add_argument('-o', '--output', help='出力CSVファイル')
    parser.add_argument('--original', action='store_true',
                       help='オリジナルデータ（5558件）を処理')

    args = parser.parse_args()

    # 入力ファイルの決定
    if args.original:
        input_file = "ultra_think_COMPLETE_FIXED_20250828_003356.csv"
    elif args.input:
        input_file = args.input
    else:
        # 最新のファイルを自動検出
        import glob
        csv_files = glob.glob("ultra_think_*.csv")
        if csv_files:
            input_file = max(csv_files, key=lambda f: Path(f).stat().st_mtime)
        else:
            print("CSVファイルが見つかりません")
            return

    if USE_RICH:
        console.print(f"[cyan]📁 処理対象: {input_file}[/cyan]")
    else:
        print(f"処理対象: {input_file}")

    # バリデーター作成
    validator = UltraThinkFastValidator()

    # 処理実行
    result_df = validator.process_database(input_file, args.output)


if __name__ == "__main__":
    main()
