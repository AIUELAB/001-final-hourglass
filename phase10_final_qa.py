#!/usr/bin/env python3
"""
Phase 10: Week 1-6最終品質監査

全142件の合格レコードに対して最終品質チェックを実施：
- 主観表現の完全チェック
- 数値・年齢整合性の検証
- 文字数範囲の再確認（180-280文字）

Author: Final Hourglass Project
Date: 2025-10-08
Version: 1.0.0
"""

import pandas as pd
import re
from typing import List, Dict
from datetime import datetime


class Phase10FinalQA:
    """
    Phase 10: 最終品質監査システム
    """

    # Layer 1絶対禁止表現（Phase 7-9で削除済みだが再確認）
    ABSOLUTE_FORBIDDEN = [
        "素晴らしい", "偉大な", "美しい", "感動的な",
        "希望を与え", "勇気を与え", "驚くべき", "圧倒的な",
        "快挙", "傑作", "絶賛", "不屈", "常識を覆し",
        "革命をもたらし", "透明感", "見習った",
        "画期的な", "革新的な", "卓越した", "類まれな",
        "伝説的な", "歴史的な"
    ]

    def __init__(self):
        self.qa_results: List[Dict] = []

    def check_subjective_expressions(self, episode: str, person_name: str) -> Dict:
        """
        主観表現チェック

        Args:
            episode: エピソード本文
            person_name: 人物名

        Returns:
            チェック結果
        """
        detected = []
        for pattern in self.ABSOLUTE_FORBIDDEN:
            if pattern in episode:
                detected.append(pattern)

        return {
            'check': 'subjective_expression',
            'person_name': person_name,
            'passed': len(detected) == 0,
            'detected': detected
        }

    def check_character_count(self, episode: str, person_name: str) -> Dict:
        """
        文字数チェック

        Args:
            episode: エピソード本文
            person_name: 人物名

        Returns:
            チェック結果
        """
        char_count = len(episode)
        passed = 180 <= char_count <= 280

        return {
            'check': 'character_count',
            'person_name': person_name,
            'char_count': char_count,
            'passed': passed,
            'issue': None if passed else (
                f"文字数不足（{char_count}文字）" if char_count < 180
                else f"文字数超過（{char_count}文字）"
            )
        }

    def check_age_consistency(
        self,
        episode: str,
        person_name: str,
        age: int
    ) -> Dict:
        """
        年齢整合性チェック

        Args:
            episode: エピソード本文
            person_name: 人物名
            age: 年齢

        Returns:
            チェック結果
        """
        # エピソード内の年齢パターン検出
        age_patterns = re.findall(r'(\d+)歳', episode)

        issues = []
        for found_age_str in age_patterns:
            found_age = int(found_age_str)
            if found_age != age:
                issues.append(f"不一致: {found_age}歳（正: {age}歳）")

        return {
            'check': 'age_consistency',
            'person_name': person_name,
            'expected_age': age,
            'found_ages': age_patterns,
            'passed': len(issues) == 0,
            'issues': issues
        }

    def check_numeric_values(self, episode: str, person_name: str) -> Dict:
        """
        数値整合性チェック

        Args:
            episode: エピソード本文
            person_name: 人物名

        Returns:
            チェック結果
        """
        # 不自然な数値パターン検出
        issues = []

        # パターン1: 100万人以上に影響（検証困難な主張）
        if "100万人以上に影響" in episode or "1000万人" in episode:
            issues.append("検証困難な影響人数")

        # パターン2: 異常に大きい数値
        large_numbers = re.findall(r'(\d{7,})', episode)  # 7桁以上の数値
        for num_str in large_numbers:
            num = int(num_str)
            if num > 10000000:  # 1000万超
                issues.append(f"異常に大きい数値: {num:,}")

        return {
            'check': 'numeric_values',
            'person_name': person_name,
            'passed': len(issues) == 0,
            'issues': issues
        }

    def audit_record(self, row: pd.Series) -> Dict:
        """
        1レコードの完全監査

        Args:
            row: pandasシリーズ（1レコード）

        Returns:
            監査結果
        """
        person_id = row['人物ID']
        person_name = row['人物名']
        age = int(row['年齢'])
        episode = str(row['エピソード本文'])

        # 各種チェック実行
        subjective_result = self.check_subjective_expressions(episode, person_name)
        char_count_result = self.check_character_count(episode, person_name)
        age_consistency_result = self.check_age_consistency(episode, person_name, age)
        numeric_result = self.check_numeric_values(episode, person_name)

        # 総合判定
        all_passed = all([
            subjective_result['passed'],
            char_count_result['passed'],
            age_consistency_result['passed'],
            numeric_result['passed']
        ])

        return {
            'person_id': person_id,
            'person_name': person_name,
            'age': age,
            'char_count': len(episode),
            'all_passed': all_passed,
            'subjective': subjective_result,
            'char_count_check': char_count_result,
            'age_consistency': age_consistency_result,
            'numeric': numeric_result
        }

    def audit_all(self, input_csv: str):
        """
        全レコード監査

        Args:
            input_csv: 入力CSVパス
        """
        print(f"\n{'='*60}")
        print(f"Phase 10: Week 1-6最終品質監査")
        print(f"{'='*60}")
        print(f"入力: {input_csv}")

        # データ読み込み
        df = pd.read_csv(input_csv, encoding='utf-8-sig')
        print(f"\n総レコード数: {len(df)}件")

        # 合格レコードのみ監査
        qualified = df[df['ステータス'] == '合格'].copy()
        print(f"監査対象（合格レコード）: {len(qualified)}件")

        print(f"\n{'='*60}")
        print(f"品質監査開始")
        print(f"{'='*60}")

        # 全レコード監査
        for i, (idx, row) in enumerate(qualified.iterrows(), 1):
            result = self.audit_record(row)
            self.qa_results.append(result)

            # 問題があれば表示
            if not result['all_passed']:
                print(f"\n⚠️  {i}/{len(qualified)} - {result['person_id']} - {result['person_name']}")

                if not result['subjective']['passed']:
                    print(f"   主観表現: {', '.join(result['subjective']['detected'])}")

                if not result['char_count_check']['passed']:
                    print(f"   文字数: {result['char_count_check']['issue']}")

                if not result['age_consistency']['passed']:
                    print(f"   年齢: {'; '.join(result['age_consistency']['issues'])}")

                if not result['numeric']['passed']:
                    print(f"   数値: {'; '.join(result['numeric']['issues'])}")

        # 統計表示
        passed_count = len([r for r in self.qa_results if r['all_passed']])
        failed_count = len(self.qa_results) - passed_count

        print(f"\n{'='*60}")
        print(f"品質監査完了")
        print(f"{'='*60}")
        print(f"監査件数: {len(self.qa_results)}件")
        print(f"合格: {passed_count}件")
        print(f"要修正: {failed_count}件")
        if len(self.qa_results) > 0:
            pass_rate = passed_count / len(self.qa_results) * 100
            print(f"合格率: {pass_rate:.1f}%")

        # カテゴリー別問題集計
        subjective_issues = len([r for r in self.qa_results if not r['subjective']['passed']])
        char_count_issues = len([r for r in self.qa_results if not r['char_count_check']['passed']])
        age_issues = len([r for r in self.qa_results if not r['age_consistency']['passed']])
        numeric_issues = len([r for r in self.qa_results if not r['numeric']['passed']])

        print(f"\n【問題内訳】")
        print(f"主観表現残存: {subjective_issues}件")
        print(f"文字数範囲外: {char_count_issues}件")
        print(f"年齢不整合: {age_issues}件")
        print(f"数値異常: {numeric_issues}件")

        print(f"{'='*60}\n")

        return self.qa_results


def main():
    """メイン処理"""
    # 入力ファイル（Phase 9最終出力）
    input_csv = "final_hourglass_master_v10_phase9_complete_20251008_065554.csv"

    # Phase 10監査実行
    qa_system = Phase10FinalQA()
    results = qa_system.audit_all(input_csv)

    # 結果保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_json = f"phase10_qa_results_{timestamp}.json"

    import json
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"✅ 監査結果JSON保存: {output_json}")


if __name__ == "__main__":
    main()
