#!/usr/bin/env python3
"""
エピソード時系列バランス分析システム

該当年齢時のエピソードが全体の2/3以上を占めることを検証

Author: Final Hourglass Project
Date: 2025-10-08
Version: 1.0.0
"""

import re
from typing import Dict, List, Tuple
import pandas as pd


class TimelineBalanceAnalyzer:
    """
    エピソード時系列バランス分析システム

    該当年齢時のエピソード: 最低66.7% (2/3)
    その後のエピソード: 最大33.3% (1/3)
    """

    # 後続イベントを示す時系列マーカー
    SUBSEQUENT_MARKERS = [
        # 明示的な後続表現
        r'その後',
        r'翌年',
        r'後に',
        r'のちに',
        r'以降',
        r'最終的に',

        # 年数経過表現
        r'\d+年後',
        r'\d+か月後',
        r'\d+日後',

        # 同年内の後続イベント
        r'同年\d+月',
        r'同年.*?に(?:は|も)',

        # 年齢進行表現
        r'\d+歳(?:時|の(?:時|とき))に(?:は|も)',
        r'\d+歳(?:で|には)',

        # 現在・結果表現
        r'現在',
        r'今日(?:では|まで)',
        r'累計',
        r'総計',

        # 受賞・評価の後日談
        r'(?:受賞|表彰|授章)(?:した|され)',
        r'(?:認定|指定)(?:された|を受け)'
    ]

    def __init__(self):
        self.markers_pattern = '|'.join([f'({m})' for m in self.SUBSEQUENT_MARKERS])

    def split_into_sentences(self, text: str) -> List[str]:
        """
        テキストを文単位に分割
        """
        # 句点で分割（ただし数値の小数点は除外）
        sentences = re.split(r'(?<!\d)。', text)
        return [s.strip() + '。' if s.strip() and not s.endswith('。') else s.strip()
                for s in sentences if s.strip()]

    def is_subsequent_event(self, sentence: str, target_age: int) -> bool:
        """
        文が後続イベント（該当年齢時以降）を示すかを判定

        Args:
            sentence: 判定対象の文
            target_age: 該当年齢

        Returns:
            True: 後続イベント
            False: 該当年齢時のイベント
        """
        # 時系列マーカーの検出
        if re.search(self.markers_pattern, sentence):
            return True

        # 年齢表記の検出（該当年齢より後の年齢）
        age_matches = re.findall(r'(\d+)歳', sentence)
        for age_str in age_matches:
            age = int(age_str)
            if age > target_age:
                return True

        return False

    def analyze_episode_timeline(
        self,
        episode: str,
        age: int,
        person_id: str = "",
        person_name: str = ""
    ) -> Dict:
        """
        エピソードの時系列構造を分析

        Args:
            episode: エピソード本文
            age: 該当年齢
            person_id: 人物ID（デバッグ用）
            person_name: 人物名（デバッグ用）

        Returns:
            {
                'person_id': str,
                'person_name': str,
                'age': int,
                'total_chars': int,
                'main_age_content': List[str],  # 該当年齢時の文リスト
                'subsequent_content': List[str],  # その後の文リスト
                'main_age_chars': int,
                'subsequent_chars': int,
                'balance_ratio': float,  # 該当年齢時の比率
                'verdict': str,  # PASS / WARNING / FAIL
                'violation_details': List[str]  # 違反詳細
            }
        """
        sentences = self.split_into_sentences(episode)

        main_age_sentences = []
        subsequent_sentences = []

        # 各文を分類
        for sentence in sentences:
            if self.is_subsequent_event(sentence, age):
                subsequent_sentences.append(sentence)
            else:
                main_age_sentences.append(sentence)

        # 文字数カウント
        main_age_chars = sum(len(s) for s in main_age_sentences)
        subsequent_chars = sum(len(s) for s in subsequent_sentences)
        total_chars = len(episode)

        # バランス比率計算
        balance_ratio = main_age_chars / total_chars if total_chars > 0 else 0.0

        # 判定
        if balance_ratio >= 0.667:  # 66.7%以上
            verdict = "PASS"
            violation_details = []
        elif balance_ratio >= 0.5:  # 50-66.7%
            verdict = "WARNING"
            violation_details = [
                f"該当年齢時の比率が基準値(66.7%)を下回る: {balance_ratio*100:.1f}%",
                f"その後の情報: {subsequent_chars}文字 ({subsequent_chars/total_chars*100:.1f}%)"
            ]
        else:  # 50%未満
            verdict = "FAIL"
            violation_details = [
                f"該当年齢時の比率が50%未満: {balance_ratio*100:.1f}%",
                f"その後の情報が過多: {subsequent_chars}文字 ({subsequent_chars/total_chars*100:.1f}%)",
                "エピソードの本質が該当年齢時にない"
            ]

        return {
            'person_id': person_id,
            'person_name': person_name,
            'age': age,
            'total_chars': total_chars,
            'main_age_content': main_age_sentences,
            'subsequent_content': subsequent_sentences,
            'main_age_chars': main_age_chars,
            'subsequent_chars': subsequent_chars,
            'balance_ratio': balance_ratio,
            'verdict': verdict,
            'violation_details': violation_details
        }

    def analyze_csv(self, csv_path: str) -> Tuple[pd.DataFrame, Dict]:
        """
        CSVファイルの全レコードを分析

        Args:
            csv_path: CSVファイルパス

        Returns:
            (analysis_df, statistics)
        """
        df = pd.read_csv(csv_path, encoding='utf-8-sig')
        qualified = df[df['ステータス'] == '合格'].copy()

        results = []

        for idx, row in qualified.iterrows():
            result = self.analyze_episode_timeline(
                episode=str(row['エピソード本文']),
                age=int(row['年齢']),
                person_id=str(row['人物ID']),
                person_name=str(row['人物名'])
            )
            results.append(result)

        # 統計情報
        total_count = len(results)
        pass_count = sum(1 for r in results if r['verdict'] == 'PASS')
        warning_count = sum(1 for r in results if r['verdict'] == 'WARNING')
        fail_count = sum(1 for r in results if r['verdict'] == 'FAIL')

        avg_balance_ratio = sum(r['balance_ratio'] for r in results) / total_count

        statistics = {
            'total_count': total_count,
            'pass_count': pass_count,
            'warning_count': warning_count,
            'fail_count': fail_count,
            'pass_rate': (pass_count / total_count) * 100,
            'warning_rate': (warning_count / total_count) * 100,
            'fail_rate': (fail_count / total_count) * 100,
            'avg_balance_ratio': avg_balance_ratio,
            'violations': [r for r in results if r['verdict'] != 'PASS']
        }

        return pd.DataFrame(results), statistics


if __name__ == "__main__":
    analyzer = TimelineBalanceAnalyzer()

    # 分析実行
    analysis_df, stats = analyzer.analyze_csv(
        "final_hourglass_week1_6_final_format_unified.csv"
    )

    print("=" * 70)
    print("📊 エピソード時系列バランス分析結果")
    print("=" * 70)
    print(f"総レコード数: {stats['total_count']}")
    print(f"✅ PASS: {stats['pass_count']} ({stats['pass_rate']:.1f}%)")
    print(f"⚠️ WARNING: {stats['warning_count']} ({stats['warning_rate']:.1f}%)")
    print(f"❌ FAIL: {stats['fail_count']} ({stats['fail_rate']:.1f}%)")
    print(f"平均バランス比率: {stats['avg_balance_ratio']*100:.1f}%")

    if stats['violations']:
        print(f"\n🔍 違反レコード詳細: {len(stats['violations'])}件")
        print("-" * 70)

        for v in stats['violations'][:10]:  # 最初の10件を表示
            print(f"\n[{v['person_id']}] {v['person_name']} ({v['age']}歳) - {v['verdict']}")
            print(f"  該当年齢時: {v['main_age_chars']}文字 ({v['balance_ratio']*100:.1f}%)")
            print(f"  その後: {v['subsequent_chars']}文字 ({(1-v['balance_ratio'])*100:.1f}%)")

            if v['violation_details']:
                for detail in v['violation_details']:
                    print(f"  - {detail}")

        if len(stats['violations']) > 10:
            print(f"\n... 他 {len(stats['violations']) - 10}件の違反あり")

    # CSV出力
    analysis_df.to_csv('timeline_balance_analysis_results.csv',
                       index=False, encoding='utf-8-sig')

    print(f"\n✅ 分析結果を保存: timeline_balance_analysis_results.csv")
