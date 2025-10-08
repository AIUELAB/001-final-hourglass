#!/usr/bin/env python3
"""
エピソード内時間情報重複検出システム

エピソード内の西暦年表記（YYYY年）を検出し、
年齢との整合性をチェックする

Phase 13: 時間情報重複削除システム
RCA-Kaizen Loop: FAIL_20251008_005 (KA_017)

Usage:
    python date_duplication_detector.py
"""

import re
import pandas as pd
from pathlib import Path
from datetime import datetime
import json
from typing import Dict, List, Tuple


class DateDuplicationDetector:
    """
    エピソード内時間情報重複検出システム

    検出パターン:
    - YYYY年
    - YYYY年MM月
    - YYYY年MM月DD日

    チェック項目:
    1. 西暦年表記の存在
    2. 年齢と西暦の整合性
    3. 時間情報の重複（年齢+西暦）
    """

    def __init__(self):
        self.year_pattern = r'(\d{4})年'
        self.year_month_pattern = r'(\d{4})年(\d{1,2})月'
        self.year_month_day_pattern = r'(\d{4})年(\d{1,2})月(\d{1,2})日'

    def detect_year_mentions(self, episode: str) -> List[str]:
        """
        エピソード内の西暦年表記を検出

        Args:
            episode: エピソード本文

        Returns:
            検出された西暦年のリスト（重複あり）
        """
        matches = re.findall(self.year_pattern, episode)
        return matches

    def check_age_year_consistency(
        self,
        mentioned_years: List[str],
        age: int,
        person_name: str,
        person_data: pd.Series = None
    ) -> Dict:
        """
        年齢と西暦の整合性をチェック

        Args:
            mentioned_years: 検出された西暦年
            age: 該当年齢
            person_name: 人物名
            person_data: 人物データ（生年含む）

        Returns:
            整合性チェック結果
        """
        if not mentioned_years:
            return {
                'consistent': True,
                'inconsistencies': []
            }

        # 生年データがあれば詳細チェック
        inconsistencies = []
        if person_data is not None and '生年' in person_data:
            birth_year = person_data['生年']
            if pd.notna(birth_year):
                expected_year_range = (
                    int(birth_year) + age,
                    int(birth_year) + age + 1  # 誕生日前後を考慮
                )

                for year in mentioned_years:
                    year_int = int(year)
                    if not (expected_year_range[0] <= year_int <= expected_year_range[1]):
                        inconsistencies.append({
                            'mentioned_year': year_int,
                            'expected_year_range': expected_year_range,
                            'age': age,
                            'birth_year': int(birth_year),
                            'person_name': person_name
                        })

        return {
            'consistent': len(inconsistencies) == 0,
            'inconsistencies': inconsistencies
        }

    def analyze_episode(
        self,
        episode: str,
        age: int,
        person_name: str,
        person_id: str,
        person_data: pd.Series = None
    ) -> Dict:
        """
        エピソードの時間情報を総合分析

        Args:
            episode: エピソード本文
            age: 該当年齢
            person_name: 人物名
            person_id: 人物ID
            person_data: 人物データ

        Returns:
            分析結果
        """
        # 西暦年表記を検出
        mentioned_years = self.detect_year_mentions(episode)

        # 年齢との整合性チェック
        consistency = self.check_age_year_consistency(
            mentioned_years, age, person_name, person_data
        )

        # 時間情報重複の判定
        has_duplication = len(mentioned_years) > 0  # 年齢表記がある前提

        return {
            'person_id': person_id,
            'person_name': person_name,
            'age': age,
            'has_year_mention': len(mentioned_years) > 0,
            'mentioned_years': mentioned_years,
            'year_mention_count': len(mentioned_years),
            'has_duplication': has_duplication,
            'consistent': consistency['consistent'],
            'inconsistencies': consistency['inconsistencies'],
            'episode_excerpt': episode[:100] + '...' if len(episode) > 100 else episode
        }

    def process_csv(self, csv_path: Path) -> Tuple[pd.DataFrame, Dict]:
        """
        CSVファイル全体を処理

        Args:
            csv_path: CSVファイルパス

        Returns:
            (処理結果DataFrame, 統計情報)
        """
        print(f"📂 CSVファイル読み込み: {csv_path}")
        df = pd.read_csv(csv_path, encoding='utf-8-sig')

        results = []
        for idx, row in df.iterrows():
            episode = str(row['エピソード本文'])
            age = int(row['年齢'])
            person_name = str(row['人物名'])
            person_id = str(row['人物ID'])

            result = self.analyze_episode(
                episode, age, person_name, person_id, row
            )
            results.append(result)

        results_df = pd.DataFrame(results)

        # 統計情報
        total_count = len(results_df)
        year_mention_count = results_df['has_year_mention'].sum()
        duplication_count = results_df['has_duplication'].sum()
        inconsistent_count = len([r for r in results if not r['consistent']])

        stats = {
            'total_records': total_count,
            'year_mention_count': int(year_mention_count),
            'year_mention_rate': f"{year_mention_count / total_count * 100:.2f}%",
            'duplication_count': int(duplication_count),
            'duplication_rate': f"{duplication_count / total_count * 100:.2f}%",
            'inconsistent_count': inconsistent_count,
            'inconsistent_rate': f"{inconsistent_count / total_count * 100:.2f}%"
        }

        return results_df, stats

    def generate_report(
        self,
        results_df: pd.DataFrame,
        stats: Dict,
        output_path: Path
    ):
        """
        検出結果レポートを生成

        Args:
            results_df: 検出結果DataFrame
            stats: 統計情報
            output_path: 出力先パス
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_path = output_path / f'date_duplication_report_{timestamp}.json'

        # 西暦年表記を含むレコードのみ抽出
        violations = results_df[results_df['has_year_mention']].to_dict('records')

        report = {
            'timestamp': timestamp,
            'statistics': stats,
            'violations': violations,
            'summary': {
                'total_violations': len(violations),
                'action_required': len(violations) > 0,
                'recommendation': '西暦年表記を削除し、年齢のみで時間を表現することを推奨'
            }
        }

        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\n📊 レポート出力: {report_path}")

        return report


def main():
    """メイン処理"""
    print("=" * 80)
    print("エピソード内時間情報重複検出システム")
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

    # 検出実行
    detector = DateDuplicationDetector()
    results_df, stats = detector.process_csv(csv_path)

    # 統計表示
    print("\n" + "=" * 80)
    print("📊 検出統計")
    print("=" * 80)
    print(f"合格レコード総数: {stats['total_records']}")
    print(f"西暦年表記を含む: {stats['year_mention_count']}件 ({stats['year_mention_rate']})")
    print(f"時間情報重複: {stats['duplication_count']}件 ({stats['duplication_rate']})")
    print(f"年齢-西暦不整合: {stats['inconsistent_count']}件 ({stats['inconsistent_rate']})")

    # 違反レコード表示（最大10件）
    violations = results_df[results_df['has_year_mention']]
    if len(violations) > 0:
        print("\n" + "=" * 80)
        print("❌ 西暦年表記検出レコード（最大10件表示）")
        print("=" * 80)

        for idx, row in violations.head(10).iterrows():
            print(f"\n{row['person_id']} - {row['person_name']} ({row['age']}歳)")
            print(f"  検出年: {', '.join(row['mentioned_years'])}")
            print(f"  抜粋: {row['episode_excerpt']}")

            if not row['consistent'] and row['inconsistencies']:
                for incon in row['inconsistencies']:
                    print(f"  ⚠️ 不整合: {incon['mentioned_year']}年 (期待: {incon['expected_year_range']})")

        if len(violations) > 10:
            print(f"\n... 他{len(violations) - 10}件")
    else:
        print("\n✅ 西暦年表記なし（完全合格）")

    # レポート生成
    output_dir = Path('.')
    report = detector.generate_report(results_df, stats, output_dir)

    print("\n" + "=" * 80)
    print("✅ 検出完了")
    print("=" * 80)
    print(f"次のステップ: fix_date_duplication.py で西暦年表記を削除")

    return results_df, stats, report


if __name__ == '__main__':
    main()
