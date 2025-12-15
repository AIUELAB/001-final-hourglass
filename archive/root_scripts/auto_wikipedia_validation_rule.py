#!/usr/bin/env python3
"""
Ultra Think Wikipedia自動検証ルール
新規追加人物に対してWikipedia検証を自動適用
"""

import pandas as pd
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import sys

# 強化版検証システムをインポート
from ultra_think_wikipedia_validator_enhanced import (
    EnhancedWikipediaValidator,
    PersonInfo,
    ValidationResult
)

# リッチな出力用
try:
    from rich.console import Console
    from rich.panel import Panel
    console = Console()
    USE_RICH = True
except ImportError:
    USE_RICH = False


class AutoWikipediaValidationRule:
    """Wikipedia自動検証ルールクラス"""

    def __init__(self):
        self.rule_name = "Wikipedia掲載確認ルール"
        self.rule_version = "2.0"
        self.enabled = True
        self.config_file = "auto_rules_config.json"
        self.load_config()

    def load_config(self):
        """設定ファイルを読み込み"""
        if Path(self.config_file).exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.enabled = config.get('wikipedia_validation', {}).get('enabled', True)
        else:
            # デフォルト設定を作成
            self.save_config()

    def save_config(self):
        """設定ファイルを保存"""
        config = {}
        if Path(self.config_file).exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

        config['wikipedia_validation'] = {
            'enabled': self.enabled,
            'rule_version': self.rule_version,
            'last_applied': datetime.now().isoformat()
        }

        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

    def validate_new_person(self, person_data: Dict) -> bool:
        """
        新規人物のWikipedia検証

        Args:
            person_data: 人物データ辞書

        Returns:
            bool: Wikipedia掲載があればTrue
        """
        if not self.enabled:
            return True  # ルールが無効の場合は通過

        # PersonInfoオブジェクトを作成
        person = PersonInfo(
            person_id=str(person_data.get('person_id', '')),
            person_name=str(person_data.get('person_name', '')),
            person_name_display=str(person_data.get('person_name_display', '')),
            person_name_ja=str(person_data.get('person_name_ja', '')),
            occupation=str(person_data.get('occupation', '')),
            nationality=str(person_data.get('nationality', '')),
            birth_year=person_data.get('birth_year'),
            category=str(person_data.get('category', ''))
        )

        # バリデーター作成（キャッシュ利用）
        validator = EnhancedWikipediaValidator(
            use_parallel=False,  # 単一検証なので並列不要
            use_cache=True
        )

        # 検証実行
        result = validator.validate_person(person)

        # キャッシュを閉じる
        if validator.cache:
            validator.cache.close()

        return result == ValidationResult.FOUND

    def apply_to_dataframe(self, df: pd.DataFrame, inplace: bool = True) -> pd.DataFrame:
        """
        DataFrameに対してルールを適用

        Args:
            df: 処理対象のDataFrame
            inplace: 元のDataFrameを変更するか

        Returns:
            処理済みのDataFrame
        """
        if not self.enabled:
            return df

        if not inplace:
            df = df.copy()

        if USE_RICH:
            console.print(Panel.fit(f"[bold cyan]{self.rule_name}[/bold cyan]",
                                   subtitle=f"Version {self.rule_version}"))
            console.print("[yellow]🔍 Wikipedia検証を実行中...[/yellow]")

        # バリデーター作成
        validator = EnhancedWikipediaValidator(
            use_parallel=True,
            max_workers=10,
            use_cache=True
        )

        # 削除対象リスト
        rows_to_delete = []

        # 各人物を検証
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

            result = validator.validate_person(person)

            if result == ValidationResult.NOT_FOUND:
                rows_to_delete.append(idx)

        # 削除実行
        if rows_to_delete:
            deleted_count = len(rows_to_delete)
            df = df.drop(rows_to_delete)
            df = df.reset_index(drop=True)

            if USE_RICH:
                console.print(f"[red]🗑️ {deleted_count}件の非掲載人物を削除しました[/red]")
            else:
                print(f"削除: {deleted_count}件")

        # キャッシュを閉じる
        if validator.cache:
            validator.cache.close()

        return df

    def apply_to_csv(self, input_file: str, output_file: Optional[str] = None) -> str:
        """
        CSVファイルに対してルールを適用

        Args:
            input_file: 入力CSVファイル
            output_file: 出力CSVファイル（Noneの場合は自動生成）

        Returns:
            出力ファイル名
        """
        if not self.enabled:
            return input_file

        # データ読み込み
        df = pd.read_csv(input_file, encoding='utf-8')
        original_count = len(df)

        # ルール適用
        df = self.apply_to_dataframe(df)

        # 出力ファイル名生成
        if output_file is None:
            output_file = f"ultra_think_WIKIPEDIA_VALIDATED_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        # 保存
        df.to_csv(output_file, index=False, encoding='utf-8')

        # レポート表示
        deleted_count = original_count - len(df)
        if USE_RICH:
            console.print(f"[green]✅ 処理完了[/green]")
            console.print(f"   元データ: {original_count}件")
            console.print(f"   削除: {deleted_count}件")
            console.print(f"   結果: {len(df)}件")
            console.print(f"   出力: {output_file}")
        else:
            print(f"処理完了: {original_count} → {len(df)} ({deleted_count}件削除)")
            print(f"出力: {output_file}")

        # 設定を更新
        self.save_config()

        return output_file


def integrate_with_auto_rules():
    """既存の自動ルールシステムに統合"""
    config_file = "auto_rules_config.json"

    # 設定読み込み
    config = {}
    if Path(config_file).exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)

    # Wikipedia検証ルールを追加
    config['wikipedia_validation'] = {
        'enabled': True,
        'rule_version': '2.0',
        'description': 'Wikipedia掲載確認ルール - 非掲載人物を自動削除',
        'created_at': datetime.now().isoformat(),
        'priority': 100  # 高優先度
    }

    # 設定保存
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    if USE_RICH:
        console.print("[green]✅ Wikipedia検証ルールを自動ルールシステムに統合しました[/green]")
    else:
        print("✅ Wikipedia検証ルールを統合完了")


def main():
    """メイン実行関数"""
    import argparse

    parser = argparse.ArgumentParser(description='Ultra Think Wikipedia自動検証ルール')
    parser.add_argument('input', nargs='?', help='入力CSVファイル')
    parser.add_argument('-o', '--output', help='出力CSVファイル')
    parser.add_argument('--integrate', action='store_true',
                       help='自動ルールシステムに統合')
    parser.add_argument('--disable', action='store_true',
                       help='ルールを無効化')
    parser.add_argument('--enable', action='store_true',
                       help='ルールを有効化')

    args = parser.parse_args()

    if args.integrate:
        integrate_with_auto_rules()
        return

    # ルールインスタンス作成
    rule = AutoWikipediaValidationRule()

    if args.disable:
        rule.enabled = False
        rule.save_config()
        print("Wikipedia検証ルールを無効化しました")
        return

    if args.enable:
        rule.enabled = True
        rule.save_config()
        print("Wikipedia検証ルールを有効化しました")
        return

    if args.input:
        # CSVファイルに適用
        rule.apply_to_csv(args.input, args.output)
    else:
        # 最新のファイルを自動検出
        import glob
        csv_files = glob.glob("ultra_think_*.csv")
        if csv_files:
            latest = max(csv_files, key=lambda f: Path(f).stat().st_mtime)
            rule.apply_to_csv(latest, args.output)
        else:
            print("CSVファイルが見つかりません")


if __name__ == "__main__":
    main()
