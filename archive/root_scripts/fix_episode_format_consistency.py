#!/usr/bin/env python3
"""
エピソード冒頭フォーマット統一修正システム

48件のフォーマット違反を「あなたと同じ◯◯歳のとき、◯◯◯◯は」に統一

Author: Final Hourglass Project
Date: 2025-10-08
Version: 1.0.0
"""

import pandas as pd
import re
from typing import Dict, List
from datetime import datetime
from anthropic import Anthropic


class EpisodeFormatFixer:
    """
    エピソード冒頭フォーマット統一システム
    """

    def __init__(self):
        self.client = Anthropic()
        self.fixed_count = 0
        self.failed_fixes: List[Dict] = []

    def fix_episode_format(
        self,
        person_id: str,
        person_name: str,
        age: int,
        current_episode: str
    ) -> Dict:
        """
        エピソード冒頭を「あなたと同じ◯◯歳のとき、◯◯◯◯は」に統一

        Args:
            person_id: 人物ID
            person_name: 人物名
            age: 年齢
            current_episode: 現在のエピソード

        Returns:
            修正結果
        """
        prompt = f"""
以下のエピソード本文の冒頭部分のみを修正してください。

【必須フォーマット】
あなたと同じ{age}歳のとき、{person_name}は

【重要な制約】
1. 冒頭のみを修正: 最初の一文のみを上記フォーマットに統一
2. 内容は維持: エピソードの事実関係・業績内容は一切変更しない
3. 文字数: 180-280文字厳守（現在: {len(current_episode)}文字）
4. 年齢と人物名: 必ず{age}歳と{person_name}を使用
5. 主観表現禁止: 「画期的な」「革新的な」「伝説的な」等は使わない

【現在のエピソード】
{current_episode}

【出力形式】
修正後のエピソード本文のみを出力してください（説明不要）。
冒頭を「あなたと同じ{age}歳のとき、{person_name}は」に統一し、残りの内容をそのまま接続してください。
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

            # フォーマットチェック
            expected_start = f"あなたと同じ{age}歳のとき、{person_name}は"
            if not fixed_episode.startswith(expected_start):
                # 人物名の別表記をチェック
                pattern = rf'^あなたと同じ{age}歳のとき、.+?は'
                if not re.match(pattern, fixed_episode):
                    return {
                        'success': False,
                        'reason': f'フォーマット不一致: 期待={expected_start}',
                        'fixed_episode': fixed_episode
                    }

            # 主観表現チェック
            subjective_patterns = [
                "画期的な", "革新的な", "伝説的な",
                "素晴らしい", "偉大な", "美しい"
            ]
            detected = [p for p in subjective_patterns if p in fixed_episode]
            if detected:
                return {
                    'success': False,
                    'reason': f'主観表現検出: {detected}',
                    'fixed_episode': fixed_episode
                }

            return {
                'success': True,
                'fixed_episode': fixed_episode,
                'char_count': char_count
            }

        except Exception as e:
            return {
                'success': False,
                'reason': f'API Error: {str(e)}',
                'fixed_episode': current_episode
            }

    def process_all_violations(self, csv_path: str):
        """
        すべてのフォーマット違反を処理

        Args:
            csv_path: 入力CSVパス
        """
        df = pd.read_csv(csv_path, encoding='utf-8-sig')

        print(f"📊 読み込み完了: {len(df)} records")

        # 合格レコードのみ
        qualified = df[df['ステータス'] == '合格'].copy()
        print(f"合格レコード: {len(qualified)}")

        # フォーマット違反を検出
        pattern = r'^あなたと同じ(\d+)歳のとき、(.+?)は'
        violations = []

        for idx, row in qualified.iterrows():
            episode = str(row['エピソード本文'])
            if not re.match(pattern, episode):
                violations.append({
                    'index': idx,
                    'person_id': row['人物ID'],
                    'person_name': row['人物名'],
                    'age': row['年齢'],
                    'current_episode': episode
                })

        print(f"\n🔍 フォーマット違反検出: {len(violations)}件")

        # 修正実行
        print("\n" + "="*60)
        print("🔧 フォーマット統一修正を開始")
        print("="*60)

        for i, violation in enumerate(violations, 1):
            person_id = violation['person_id']
            person_name = violation['person_name']
            age = violation['age']
            current_episode = violation['current_episode']

            print(f"\n[{i}/{len(violations)}] {person_id} - {person_name} ({age}歳)")
            print(f"現状: {current_episode[:60]}...")

            result = self.fix_episode_format(
                person_id, person_name, age, current_episode
            )

            if result['success']:
                # DataFrameを更新
                df.at[violation['index'], 'エピソード本文'] = result['fixed_episode']
                df.at[violation['index'], '文字数'] = result['char_count']

                print(f"✅ 修正完了: {result['char_count']}文字")
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
        print("\n" + "="*60)
        print("📊 修正結果")
        print("="*60)
        print(f"修正成功: {self.fixed_count}/{len(violations)}")
        print(f"修正失敗: {len(self.failed_fixes)}/{len(violations)}")

        if self.failed_fixes:
            print("\n❌ 修正失敗リスト:")
            for fail in self.failed_fixes:
                print(f"  {fail['person_id']} - {fail['person_name']}: {fail['reason']}")

        # CSV出力
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"final_hourglass_week1_6_format_fixed_{timestamp}.csv"

        with open(output_path, 'w', encoding='utf-8-sig') as f:
            df.to_csv(f, index=False)

        print(f"\n✅ 修正完了: {output_path}")

        return output_path, self.fixed_count, len(self.failed_fixes)


if __name__ == "__main__":
    try:
        fixer = EpisodeFormatFixer()
        output_path, fixed, failed = fixer.process_all_violations(
            "final_hourglass_week1_6_final_20251008_075039.csv"
        )

        print("\n" + "="*60)
        print("🎯 次のステップ")
        print("="*60)
        print("1. テスト実行: pytest tests/test_episode_format.py -v")
        print("2. すべてのテストがPASSすることを確認")
        print(f"3. 修正後のCSVを確認: {output_path}")

    except Exception as e:
        print(f"❌ エラー: {e}")
        raise
