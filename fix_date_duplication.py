#!/usr/bin/env python3
"""
エピソード内時間情報重複修正システム

エピソード内の西暦年表記（YYYY年）を削除し、
時間情報を年齢のみに統一する

Phase 13: 時間情報重複削除システム
RCA-Kaizen Loop: FAIL_20251008_005 (KA_017)

Usage:
    python fix_date_duplication.py
"""

import re
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Tuple


class DateDuplicationFixer:
    """
    エピソード内時間情報重複修正システム

    修正パターン:
    - 「YYYY年MM月DD日、」→ 削除
    - 「YYYY年MM月、」→ 削除
    - 「YYYY年、」→ 削除
    - 「YYYY年に」→ 削除

    文字数範囲（180-280文字）を維持
    """

    def __init__(self):
        # 削除パターン（優先順位順）
        self.patterns = [
            # パターン1: YYYY年MM月DD日、
            (r'\d{4}年\d{1,2}月\d{1,2}日、', ''),
            # パターン2: YYYY年MM月、
            (r'\d{4}年\d{1,2}月、', ''),
            # パターン3: YYYY年、
            (r'\d{4}年、', ''),
            # パターン4: YYYY年に
            (r'\d{4}年に', ''),
            # パターン5: YYYY年MM月DD日に
            (r'\d{4}年\d{1,2}月\d{1,2}日に', ''),
            # パターン6: YYYY年MM月に
            (r'\d{4}年\d{1,2}月に', ''),
            # パターン7: YYYY年から
            (r'\d{4}年から', 'から'),
            # パターン8: YYYY年 (後ろに文字が続く場合、汎用的に削除)
            (r'\d{4}年', ''),
        ]

    def detect_year_mention(self, episode: str) -> bool:
        """
        西暦年表記の存在を検出

        Args:
            episode: エピソード本文

        Returns:
            西暦年表記があればTrue
        """
        year_pattern = r'\d{4}年'
        return bool(re.search(year_pattern, episode))

    def fix_year_mentions(self, episode: str) -> Tuple[str, int]:
        """
        西暦年表記を削除

        Args:
            episode: エピソード本文

        Returns:
            (修正後エピソード, 削除文字数)
        """
        original_length = len(episode)
        fixed_episode = episode

        # すべてのパターンで置換
        for pattern, replacement in self.patterns:
            fixed_episode = re.sub(pattern, replacement, fixed_episode)

        chars_removed = original_length - len(fixed_episode)

        return fixed_episode, chars_removed

    def validate_char_count(self, episode: str, min_chars: int = 180, max_chars: int = 280) -> bool:
        """
        文字数範囲を検証

        Args:
            episode: エピソード本文
            min_chars: 最小文字数
            max_chars: 最大文字数

        Returns:
            範囲内ならTrue
        """
        char_count = len(episode)
        return min_chars <= char_count <= max_chars

    def process_record(
        self,
        row: pd.Series,
        min_chars: int = 180,
        max_chars: int = 280
    ) -> dict:
        """
        1レコードを処理

        Args:
            row: レコードデータ
            min_chars: 最小文字数
            max_chars: 最大文字数

        Returns:
            処理結果
        """
        episode = str(row['エピソード本文'])
        person_id = str(row['人物ID'])
        person_name = str(row['人物名'])
        age = int(row['年齢'])

        # 西暦年表記の検出
        has_year = self.detect_year_mention(episode)

        if not has_year:
            return {
                'person_id': person_id,
                'person_name': person_name,
                'age': age,
                'status': 'skipped',
                'reason': 'no_year_mention',
                'original_episode': episode,
                'fixed_episode': episode,
                'chars_removed': 0,
                'original_length': len(episode),
                'fixed_length': len(episode),
                'in_range': self.validate_char_count(episode, min_chars, max_chars)
            }

        # 西暦年表記を削除
        fixed_episode, chars_removed = self.fix_year_mentions(episode)

        # 文字数範囲チェック
        in_range = self.validate_char_count(fixed_episode, min_chars, max_chars)

        return {
            'person_id': person_id,
            'person_name': person_name,
            'age': age,
            'status': 'fixed' if in_range else 'out_of_range',
            'reason': 'year_removed' if in_range else 'char_count_violation',
            'original_episode': episode,
            'fixed_episode': fixed_episode,
            'chars_removed': chars_removed,
            'original_length': len(episode),
            'fixed_length': len(fixed_episode),
            'in_range': in_range
        }

    def process_csv(
        self,
        csv_path: Path,
        output_path: Path = None,
        min_chars: int = 180,
        max_chars: int = 280
    ) -> Tuple[pd.DataFrame, dict]:
        """
        CSVファイル全体を処理

        Args:
            csv_path: 入力CSVファイルパス
            output_path: 出力CSVファイルパス（Noneなら自動生成）
            min_chars: 最小文字数
            max_chars: 最大文字数

        Returns:
            (修正後DataFrame, 統計情報)
        """
        print(f"📂 CSVファイル読み込み: {csv_path}")
        df = pd.read_csv(csv_path, encoding='utf-8-sig')

        results = []
        fixed_df = df.copy()

        for idx, row in df.iterrows():
            result = self.process_record(row, min_chars, max_chars)
            results.append(result)

            # 修正適用
            if result['status'] == 'fixed':
                fixed_df.at[idx, 'エピソード本文'] = result['fixed_episode']

        # 統計情報
        total_count = len(results)
        fixed_count = sum(1 for r in results if r['status'] == 'fixed')
        skipped_count = sum(1 for r in results if r['status'] == 'skipped')
        out_of_range_count = sum(1 for r in results if r['status'] == 'out_of_range')
        total_chars_removed = sum(r['chars_removed'] for r in results)

        stats = {
            'total_records': total_count,
            'fixed_count': fixed_count,
            'fixed_rate': f"{fixed_count / total_count * 100:.2f}%",
            'skipped_count': skipped_count,
            'out_of_range_count': out_of_range_count,
            'total_chars_removed': total_chars_removed,
            'avg_chars_removed': f"{total_chars_removed / max(fixed_count, 1):.2f}"
        }

        # 出力パス生成
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = Path(f'final_hourglass_week1_6_date_fixed_{timestamp}.csv')

        # CSV出力（UTF-8 BOM付き）
        print(f"\n💾 修正後CSVを出力: {output_path}")
        fixed_df.to_csv(output_path, index=False, encoding='utf-8-sig')

        return fixed_df, stats, results

    def display_sample_fixes(self, results: list, max_samples: int = 5):
        """
        修正サンプルを表示

        Args:
            results: 処理結果リスト
            max_samples: 最大表示数
        """
        fixed_results = [r for r in results if r['status'] == 'fixed']

        if not fixed_results:
            print("\n✅ 修正対象なし")
            return

        print("\n" + "=" * 80)
        print(f"📝 修正サンプル（最大{max_samples}件表示）")
        print("=" * 80)

        for i, result in enumerate(fixed_results[:max_samples], 1):
            print(f"\n{i}. {result['person_id']} - {result['person_name']} ({result['age']}歳)")
            print(f"   削除文字数: {result['chars_removed']}文字")
            print(f"   文字数: {result['original_length']} → {result['fixed_length']}")
            print(f"\n   【修正前】")
            print(f"   {result['original_episode'][:150]}...")
            print(f"\n   【修正後】")
            print(f"   {result['fixed_episode'][:150]}...")

        if len(fixed_results) > max_samples:
            print(f"\n... 他{len(fixed_results) - max_samples}件")


def main():
    """メイン処理"""
    print("=" * 80)
    print("エピソード内時間情報重複修正システム")
    print("Phase 13: 時間情報重複削除システム")
    print("=" * 80)

    # 最新のCSVファイルを検索
    csv_files = list(Path('.').glob('final_hourglass_week1_6_*.csv'))
    if not csv_files:
        print("❌ CSVファイルが見つかりません")
        return

    # 最新のファイルを選択（age_fixed優先）
    age_fixed_files = [f for f in csv_files if 'age_fixed' in f.name]
    if age_fixed_files:
        csv_path = max(age_fixed_files, key=lambda x: x.stat().st_mtime)
    else:
        csv_path = max(csv_files, key=lambda x: x.stat().st_mtime)

    print(f"\n処理対象: {csv_path}")

    # 修正実行
    fixer = DateDuplicationFixer()
    fixed_df, stats, results = fixer.process_csv(csv_path)

    # 統計表示
    print("\n" + "=" * 80)
    print("📊 修正統計")
    print("=" * 80)
    print(f"総レコード数: {stats['total_records']}")
    print(f"✅ 修正完了: {stats['fixed_count']}件 ({stats['fixed_rate']})")
    print(f"⏭️  スキップ: {stats['skipped_count']}件（西暦表記なし）")
    print(f"⚠️  範囲外: {stats['out_of_range_count']}件（文字数範囲外）")
    print(f"削除文字数合計: {stats['total_chars_removed']}文字")
    print(f"平均削除文字数: {stats['avg_chars_removed']}文字/件")

    # サンプル表示
    fixer.display_sample_fixes(results, max_samples=5)

    print("\n" + "=" * 80)
    print("✅ 修正完了")
    print("=" * 80)
    print(f"次のステップ: pytest tests/test_episode_format.py でテスト実行")

    return fixed_df, stats, results


if __name__ == '__main__':
    main()
