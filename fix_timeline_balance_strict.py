#!/usr/bin/env python3
"""
エピソード時系列バランス厳格再修正システム

残存14件を絶対基準（該当年齢時 ≥ 150文字、後続 ≤ 70文字）で修正

RCA-Kaizen Loop: FAIL_20251008_003 (KA_011)

Author: Final Hourglass Project
Date: 2025-10-08
Version: 2.0.0
"""

import pandas as pd
from typing import Dict, List
from datetime import datetime
from anthropic import Anthropic
from timeline_balance_analyzer import TimelineBalanceAnalyzer


class StrictTimelineBalanceFixer:
    """
    厳格時系列バランス修正システム

    絶対基準:
    - 該当年齢時: 最低150文字（68.2%相当）
    - その後: 最大70文字（31.8%相当）
    """

    REMAINING_VIOLATIONS = [
        'P013', 'P019', 'P021', 'P031', 'P039',
        'P064', 'P082', 'P089', 'P095', 'P098',
        'P106', 'P110', 'P112', 'P129'
    ]

    def __init__(self):
        self.client = Anthropic()
        self.analyzer = TimelineBalanceAnalyzer()
        self.fixed_count = 0
        self.failed_fixes: List[Dict] = []

    def fix_timeline_balance_strict(
        self,
        person_id: str,
        person_name: str,
        age: int,
        current_episode: str,
        current_ratio: float
    ) -> Dict:
        """
        絶対基準で時系列バランスを修正

        Args:
            person_id: 人物ID
            person_name: 人物名
            age: 年齢
            current_episode: 現在のエピソード
            current_ratio: 現在のバランス比率

        Returns:
            修正結果
        """
        prompt = f"""
以下のエピソード本文を**絶対基準**で修正してください。

【深刻な問題】
- 現在のバランス比率: {current_ratio*100:.1f}% （基準: 66.7%以上）
- 後続情報が多すぎて該当年齢時の本質が失われている

【絶対基準（厳守）】
1. **該当年齢時の内容**: **最低150文字**（68.2%）
   - {age}歳時の業績・活動を具体的に記述
   - 日付、場所、数値、記録、具体的状況を必ず含める
   - 客観的事実のみ（主観表現一切禁止）
   - 時系列順に整理

2. **その後の情報**: **最大70文字**（31.8%）まで
   - 「その後」「翌年」「現在」等の後続マーカーを含む文は最小限
   - 後日の受賞歴・累計記録は削除または該当年齢時に組み込む
   - 完全削除を検討（該当年齢時だけで十分な場合）

3. **総文字数**: 220-280文字推奨（180-280文字厳守）

4. **冒頭維持**: 「あなたと同じ{age}歳のとき、{person_name}は」

5. **主観表現禁止**: 画期的、革新的、伝説的、素晴らしい等

【修正戦略】
- 該当年齢時の内容を拡充（時間、場所、状況、背景、詳細数値）
- 後続情報は容赦なく削除（TIPSに過ぎない）
- 該当年齢時だけで完結したエピソードを作成

【現在のエピソード】
{current_episode}

【出力】
修正後のエピソード本文のみを出力（説明不要）。
該当年齢時 ≥ 150文字、後続 ≤ 70文字を厳守。
"""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                temperature=0.2,  # より決定的な出力
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            fixed_episode = response.content[0].text.strip()

            # 文字数チェック
            char_count = len(fixed_episode)
            if not (180 <= char_count <= 280):
                return {
                    'success': False,
                    'reason': f'文字数範囲外: {char_count}文字',
                    'fixed_episode': fixed_episode
                }

            # 時系列バランスチェック
            analysis = self.analyzer.analyze_episode_timeline(
                fixed_episode, age, person_id, person_name
            )

            # 厳格チェック: 該当年齢時 ≥ 150文字
            if analysis['main_age_chars'] < 150:
                return {
                    'success': False,
                    'reason': f'該当年齢時文字数不足: {analysis["main_age_chars"]}文字（必須: 150文字以上）',
                    'fixed_episode': fixed_episode,
                    'new_ratio': analysis['balance_ratio']
                }

            # 後続情報 ≤ 70文字
            if analysis['subsequent_chars'] > 70:
                return {
                    'success': False,
                    'reason': f'後続情報過多: {analysis["subsequent_chars"]}文字（上限: 70文字）',
                    'fixed_episode': fixed_episode,
                    'new_ratio': analysis['balance_ratio']
                }

            # バランス比率 ≥ 66.7%
            if analysis['balance_ratio'] < 0.667:
                return {
                    'success': False,
                    'reason': f'バランス比率不足: {analysis["balance_ratio"]*100:.1f}%',
                    'fixed_episode': fixed_episode,
                    'new_ratio': analysis['balance_ratio']
                }

            # フォーマットチェック
            import re
            pattern = rf'^あなたと同じ{age}歳のとき、.+?は'
            if not re.match(pattern, fixed_episode):
                return {
                    'success': False,
                    'reason': 'フォーマット不一致',
                    'fixed_episode': fixed_episode
                }

            return {
                'success': True,
                'fixed_episode': fixed_episode,
                'char_count': char_count,
                'new_ratio': analysis['balance_ratio'],
                'main_age_chars': analysis['main_age_chars'],
                'subsequent_chars': analysis['subsequent_chars'],
                'improvement': analysis['balance_ratio'] - current_ratio
            }

        except Exception as e:
            return {
                'success': False,
                'reason': f'API Error: {str(e)}',
                'fixed_episode': current_episode
            }

    def process_remaining_violations(self, csv_path: str):
        """
        残存14件の違反を厳格基準で修正

        Args:
            csv_path: 前回修正済みCSVパス
        """
        df = pd.read_csv(csv_path, encoding='utf-8-sig')

        print(f"📊 読み込み完了: {len(df)} records")

        # 合格レコードのみ
        qualified = df[df['ステータス'] == '合格'].copy()
        print(f"合格レコード: {len(qualified)}")

        # 残存違反のみ抽出
        violations = []

        for idx, row in qualified.iterrows():
            person_id = str(row['人物ID'])

            if person_id not in self.REMAINING_VIOLATIONS:
                continue

            episode = str(row['エピソード本文'])
            age = int(row['年齢'])
            person_name = str(row['人物名'])

            analysis = self.analyzer.analyze_episode_timeline(
                episode, age, person_id, person_name
            )

            violations.append({
                'index': idx,
                'person_id': person_id,
                'person_name': person_name,
                'age': age,
                'current_episode': episode,
                'current_ratio': analysis['balance_ratio'],
                'main_age_chars': analysis['main_age_chars'],
                'subsequent_chars': analysis['subsequent_chars']
            })

        # バランス比率順にソート
        violations.sort(key=lambda x: x['current_ratio'])

        print(f"\n🔍 厳格再修正対象: {len(violations)}件")

        # 修正実行
        print("\n" + "="*70)
        print("🔧 厳格時系列バランス再修正を開始")
        print("="*70)

        for i, violation in enumerate(violations, 1):
            person_id = violation['person_id']
            person_name = violation['person_name']
            age = violation['age']
            current_episode = violation['current_episode']
            current_ratio = violation['current_ratio']
            main_age_chars = violation['main_age_chars']
            subsequent_chars = violation['subsequent_chars']

            print(f"\n[{i}/{len(violations)}] {person_id} - {person_name} ({age}歳)")
            print(f"現状: バランス比率 {current_ratio*100:.1f}%")
            print(f"   該当年齢時: {main_age_chars}文字、後続: {subsequent_chars}文字")

            result = self.fix_timeline_balance_strict(
                person_id, person_name, age, current_episode, current_ratio
            )

            if result['success']:
                # DataFrameを更新
                df.at[violation['index'], 'エピソード本文'] = result['fixed_episode']
                df.at[violation['index'], '文字数'] = result['char_count']

                print(f"✅ 修正完了: {result['char_count']}文字")
                print(f"   バランス比率: {current_ratio*100:.1f}% → {result['new_ratio']*100:.1f}%")
                print(f"   該当年齢時: {result['main_age_chars']}文字 (基準: ≥150)")
                print(f"   後続: {result['subsequent_chars']}文字 (基準: ≤70)")
                self.fixed_count += 1
            else:
                print(f"❌ 修正失敗: {result['reason']}")
                self.failed_fixes.append({
                    'person_id': person_id,
                    'person_name': person_name,
                    'reason': result['reason']
                })

        # 統計
        print("\n" + "="*70)
        print("📊 厳格再修正結果")
        print("="*70)
        print(f"修正成功: {self.fixed_count}/{len(violations)}")
        print(f"修正失敗: {len(self.failed_fixes)}/{len(violations)}")

        if self.failed_fixes:
            print("\n❌ 修正失敗リスト:")
            for fail in self.failed_fixes:
                print(f"  {fail['person_id']} - {fail['person_name']}: {fail['reason']}")

        # 最終検証
        print("\n" + "="*70)
        print("🔍 最終検証: 全145件の時系列バランス")
        print("="*70)

        final_violations = []
        for idx, row in df[df['ステータス'] == '合格'].iterrows():
            analysis = self.analyzer.analyze_episode_timeline(
                str(row['エピソード本文']),
                int(row['年齢']),
                str(row['人物ID']),
                str(row['人物名'])
            )

            if analysis['balance_ratio'] < 0.667:
                final_violations.append({
                    'person_id': analysis['person_id'],
                    'person_name': analysis['person_name'],
                    'ratio': analysis['balance_ratio']
                })

        total_pass = 145 - len(final_violations)
        pass_rate = (total_pass / 145) * 100

        print(f"✅ PASS: {total_pass}/145 ({pass_rate:.1f}%)")
        print(f"❌ FAIL: {len(final_violations)}/145 ({(100-pass_rate):.1f}%)")

        if final_violations:
            print(f"\n⚠️ 残存違反: {len(final_violations)}件")
            for v in final_violations:
                print(f"   {v['person_id']} - {v['person_name']}: {v['ratio']*100:.1f}%")
        else:
            print("\n🎉 すべてのレコードが基準を満たしています（100% PASS）")

        # CSV出力
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"final_hourglass_week1_6_timeline_strict_{timestamp}.csv"

        with open(output_path, 'w', encoding='utf-8-sig') as f:
            df.to_csv(f, index=False)

        print(f"\n✅ 厳格修正完了: {output_path}")

        return output_path, self.fixed_count, len(self.failed_fixes), final_violations


if __name__ == "__main__":
    try:
        fixer = StrictTimelineBalanceFixer()
        output_path, fixed, failed, remaining = fixer.process_remaining_violations(
            "final_hourglass_week1_6_timeline_fixed_20251008_100331.csv"
        )

        print("\n" + "="*70)
        print("🎯 次のステップ")
        print("="*70)
        if len(remaining) == 0:
            print("1. test_timeline_balance テストケース追加")
            print("2. pytest tests/test_episode_format.py -v で全テスト実行")
            print("3. RCA-Kaizen Loop統合 (FAIL_20251008_003.json)")
            print("4. REQUIREMENTS.md更新 (v1.2.0)")
            print("5. 最終CSV→Git コミット")
        else:
            print(f"1. 残存{len(remaining)}件の手動レビュー・修正")
            print("2. 厳格修正スクリプトの再実行")

    except Exception as e:
        print(f"❌ エラー: {e}")
        raise
