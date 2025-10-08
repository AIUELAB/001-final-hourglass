#!/usr/bin/env python3
"""
エピソード時系列バランス自動修正システム

32件の違反レコードを該当年齢時 ≥ 66.7%に修正

RCA-Kaizen Loop: FAIL_20251008_003 (KA_010)

Author: Final Hourglass Project
Date: 2025-10-08
Version: 1.0.0
"""

import pandas as pd
from typing import Dict, List
from datetime import datetime
from anthropic import Anthropic
from timeline_balance_analyzer import TimelineBalanceAnalyzer


class TimelineBalanceFixer:
    """
    時系列バランス自動修正システム

    LLMを使用して該当年齢時の比率を66.7%以上に修正
    """

    def __init__(self):
        self.client = Anthropic()
        self.analyzer = TimelineBalanceAnalyzer()
        self.fixed_count = 0
        self.failed_fixes: List[Dict] = []

    def fix_timeline_balance(
        self,
        person_id: str,
        person_name: str,
        age: int,
        current_episode: str,
        current_ratio: float
    ) -> Dict:
        """
        エピソードの時系列バランスを修正

        Args:
            person_id: 人物ID
            person_name: 人物名
            age: 年齢
            current_episode: 現在のエピソード
            current_ratio: 現在のバランス比率

        Returns:
            修正結果
        """
        # 該当年齢時の最低文字数（66.7%）
        min_main_age_chars = 120  # 180文字 × 0.667
        max_subsequent_chars = 60  # 180文字 × 0.333

        prompt = f"""
以下のエピソード本文の時系列バランスを修正してください。

【現状の問題】
- 該当年齢時の比率: {current_ratio*100:.1f}% (基準: 66.7%以上)
- その後の情報が多すぎる

【必須制約】
1. **該当年齢時の内容**: 最低{min_main_age_chars}文字（66.7%以上）
   - {age}歳時の具体的な業績・活動を詳細に記述
   - 日付、数値、記録、具体的なエピソードを追加
   - 客観的事実のみ使用

2. **その後の情報**: 最大{max_subsequent_chars}文字（33.3%以下）
   - 「その後」「翌年」「現在」等の後続情報は最小限に
   - 受賞歴や累計記録は該当年齢時の業績に焦点を当てる
   - 不要な後日談は削除

3. **文字数**: 180-280文字厳守（現在: {len(current_episode)}文字）

4. **冒頭フォーマット維持**: 「あなたと同じ{age}歳のとき、{person_name}は」

5. **主観表現禁止**: 画期的な、革新的な、伝説的な等は使わない

【現在のエピソード】
{current_episode}

【出力形式】
修正後のエピソード本文のみを出力してください（説明不要）。
該当年齢時の業績を詳細に記述し、後続情報を最小化してください。
"""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1500,
                temperature=0.3,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            fixed_episode = response.content[0].text.strip()

            # バリデーション
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

            if analysis['balance_ratio'] < 0.667:
                return {
                    'success': False,
                    'reason': f'バランス比率不足: {analysis["balance_ratio"]*100:.1f}%',
                    'fixed_episode': fixed_episode,
                    'new_ratio': analysis['balance_ratio']
                }

            # フォーマットチェック
            expected_start = f"あなたと同じ{age}歳のとき、{person_name}は"
            if not fixed_episode.startswith(expected_start):
                # 人物名の別表記を許容
                import re
                pattern = rf'^あなたと同じ{age}歳のとき、.+?は'
                if not re.match(pattern, fixed_episode):
                    return {
                        'success': False,
                        'reason': f'フォーマット不一致',
                        'fixed_episode': fixed_episode
                    }

            return {
                'success': True,
                'fixed_episode': fixed_episode,
                'char_count': char_count,
                'new_ratio': analysis['balance_ratio'],
                'improvement': analysis['balance_ratio'] - current_ratio
            }

        except Exception as e:
            return {
                'success': False,
                'reason': f'API Error: {str(e)}',
                'fixed_episode': current_episode
            }

    def process_all_violations(self, csv_path: str):
        """
        すべての時系列バランス違反を処理

        Args:
            csv_path: 入力CSVパス
        """
        df = pd.read_csv(csv_path, encoding='utf-8-sig')

        print(f"📊 読み込み完了: {len(df)} records")

        # 合格レコードのみ
        qualified = df[df['ステータス'] == '合格'].copy()
        print(f"合格レコード: {len(qualified)}")

        # 時系列バランス違反を検出
        violations = []

        for idx, row in qualified.iterrows():
            episode = str(row['エピソード本文'])
            age = int(row['年齢'])
            person_id = str(row['人物ID'])
            person_name = str(row['人物名'])

            analysis = self.analyzer.analyze_episode_timeline(
                episode, age, person_id, person_name
            )

            if analysis['balance_ratio'] < 0.667:
                violations.append({
                    'index': idx,
                    'person_id': person_id,
                    'person_name': person_name,
                    'age': age,
                    'current_episode': episode,
                    'current_ratio': analysis['balance_ratio'],
                    'verdict': analysis['verdict']
                })

        # 違反をFAIL → WARNING順にソート
        violations.sort(key=lambda x: (
            0 if x['verdict'] == 'FAIL' else 1,
            x['current_ratio']
        ))

        print(f"\n🔍 時系列バランス違反検出: {len(violations)}件")
        fail_count = sum(1 for v in violations if v['verdict'] == 'FAIL')
        warning_count = sum(1 for v in violations if v['verdict'] == 'WARNING')
        print(f"   FAIL: {fail_count}件、WARNING: {warning_count}件")

        # 修正実行
        print("\n" + "="*70)
        print("🔧 時系列バランス修正を開始")
        print("="*70)

        for i, violation in enumerate(violations, 1):
            person_id = violation['person_id']
            person_name = violation['person_name']
            age = violation['age']
            current_episode = violation['current_episode']
            current_ratio = violation['current_ratio']
            verdict = violation['verdict']

            print(f"\n[{i}/{len(violations)}] {person_id} - {person_name} ({age}歳) - {verdict}")
            print(f"現状バランス: {current_ratio*100:.1f}%")
            print(f"現エピソード: {current_episode[:60]}...")

            result = self.fix_timeline_balance(
                person_id, person_name, age, current_episode, current_ratio
            )

            if result['success']:
                # DataFrameを更新
                df.at[violation['index'], 'エピソード本文'] = result['fixed_episode']
                df.at[violation['index'], '文字数'] = result['char_count']

                print(f"✅ 修正完了: {result['char_count']}文字")
                print(f"   バランス比率: {current_ratio*100:.1f}% → {result['new_ratio']*100:.1f}%")
                print(f"   改善度: +{result['improvement']*100:.1f}%")
                print(f"修正後: {result['fixed_episode'][:60]}...")
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
        print("📊 修正結果")
        print("="*70)
        print(f"修正成功: {self.fixed_count}/{len(violations)}")
        print(f"修正失敗: {len(self.failed_fixes)}/{len(violations)}")

        if self.failed_fixes:
            print("\n❌ 修正失敗リスト:")
            for fail in self.failed_fixes:
                print(f"  {fail['person_id']} - {fail['person_name']}: {fail['reason']}")

        # 最終検証
        print("\n" + "="*70)
        print("🔍 最終検証: 全レコードの時系列バランス再チェック")
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

        if final_violations:
            print(f"⚠️ 残存違反: {len(final_violations)}件")
            for v in final_violations:
                print(f"   {v['person_id']} - {v['person_name']}: {v['ratio']*100:.1f}%")
        else:
            print("✅ すべてのレコードが基準を満たしています（100% PASS）")

        # CSV出力
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"final_hourglass_week1_6_timeline_fixed_{timestamp}.csv"

        with open(output_path, 'w', encoding='utf-8-sig') as f:
            df.to_csv(f, index=False)

        print(f"\n✅ 修正完了: {output_path}")

        return output_path, self.fixed_count, len(self.failed_fixes), final_violations


if __name__ == "__main__":
    try:
        fixer = TimelineBalanceFixer()
        output_path, fixed, failed, remaining = fixer.process_all_violations(
            "final_hourglass_week1_6_final_format_unified.csv"
        )

        print("\n" + "="*70)
        print("🎯 次のステップ")
        print("="*70)
        print("1. テスト実行: pytest tests/test_episode_format.py -v")
        print("2. test_timeline_balance テストケース追加")
        print("3. RCA-Kaizen Loop統合 (FAIL_20251008_003.json)")
        print("4. REQUIREMENTS.md更新 (v1.2.0)")
        print(f"5. 修正後のCSVを確認: {output_path}")

    except Exception as e:
        print(f"❌ エラー: {e}")
        raise
