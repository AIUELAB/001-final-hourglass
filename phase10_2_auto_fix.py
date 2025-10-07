#!/usr/bin/env python3
"""
Phase 10-2: 監査問題23件の自動修正

主観表現残存6件 + 年齢不整合13件 + 数値異常8件の完全修正

Author: Final Hourglass Project
Date: 2025-10-08
Version: 1.0.0
"""

import pandas as pd
import json
import re
from typing import Dict, List
from datetime import datetime
from anthropic import Anthropic


class Phase10AutoFixer:
    """
    Phase 10-2: 監査問題の自動修正システム
    """

    def __init__(self):
        self.client = Anthropic()
        self.fixed_count = 0
        self.failed_fixes: List[Dict] = []

    def fix_subjective_expression(
        self,
        person_id: str,
        person_name: str,
        age: int,
        current_episode: str
    ) -> Dict:
        """
        主観表現を客観的事実に置き換え

        Args:
            person_id: 人物ID
            person_name: 人物名
            age: 年齢
            current_episode: 現在のエピソード

        Returns:
            修正結果
        """
        prompt = f"""
以下のエピソードから主観表現（画期的な、革新的な、伝説的な）を完全に削除し、客観的事実のみに置き換えてください。

【重要な制約】
1. 文字数: 180-280文字厳守（現在: {len(current_episode)}文字）
2. 主観表現の完全削除: "画期的な"、"革新的な"、"伝説的な"等は絶対に使わない
3. 客観的事実のみ: 受賞歴、数値データ、公式記録で置き換え
4. 年齢整合性: エピソード内の年齢は必ず{age}歳で統一
5. 数値の検証可能性: 具体的な年月日、受賞名、公式統計のみ使用

【現在のエピソード】
{current_episode}

【人物情報】
- 人物名: {person_name}
- 年齢: {age}歳

【出力形式】
修正後のエピソードのみを出力してください（説明不要）。
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

            # 主観表現チェック
            subjective_patterns = [
                "画期的な", "革新的な", "伝説的な",
                "素晴らしい", "偉大な", "美しい"
            ]
            detected = [p for p in subjective_patterns if p in fixed_episode]
            if detected:
                return {
                    'success': False,
                    'reason': f'主観表現残存: {", ".join(detected)}',
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
                'reason': f'API呼び出しエラー: {str(e)}',
                'fixed_episode': current_episode
            }

    def fix_age_inconsistency(
        self,
        person_id: str,
        person_name: str,
        age: int,
        current_episode: str
    ) -> Dict:
        """
        年齢不整合を修正

        Args:
            person_id: 人物ID
            person_name: 人物名
            age: 正しい年齢
            current_episode: 現在のエピソード

        Returns:
            修正結果
        """
        # エピソード内の年齢パターン検出
        age_patterns = re.findall(r'(\d+)歳', current_episode)

        prompt = f"""
以下のエピソードの年齢を正しい年齢に統一してください。

【重要な制約】
1. 文字数: 180-280文字厳守（現在: {len(current_episode)}文字）
2. 年齢統一: すべての年齢表現を{age}歳に統一
3. 客観的事実維持: 受賞歴、年月日、公式記録は変更しない
4. 主観表現禁止: 主観的評価は一切使わない

【現在のエピソード】
{current_episode}

【検出された年齢】
{', '.join([f'{a}歳' for a in age_patterns])}

【正しい年齢】
{age}歳

【出力形式】
修正後のエピソードのみを出力してください（説明不要）。
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

            # 年齢整合性チェック
            new_age_patterns = re.findall(r'(\d+)歳', fixed_episode)
            inconsistent = [a for a in new_age_patterns if int(a) != age]
            if inconsistent:
                return {
                    'success': False,
                    'reason': f'年齢不整合残存: {", ".join([f"{a}歳" for a in inconsistent])}',
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
                'reason': f'API呼び出しエラー: {str(e)}',
                'fixed_episode': current_episode
            }

    def fix_numeric_anomaly(
        self,
        person_id: str,
        person_name: str,
        age: int,
        current_episode: str
    ) -> Dict:
        """
        検証困難な数値を具体的事実に置き換え

        Args:
            person_id: 人物ID
            person_name: 人物名
            age: 年齢
            current_episode: 現在のエピソード

        Returns:
            修正結果
        """
        prompt = f"""
以下のエピソードから検証困難な数値表現（"100万人以上に影響"等）を削除し、具体的な事実に置き換えてください。

【重要な制約】
1. 文字数: 180-280文字厳守（現在: {len(current_episode)}文字）
2. 数値の検証可能性: 公式統計、年月日、受賞記録等の確認可能な事実のみ
3. 曖昧な影響主張の削除: "〜に影響を与え"、"〜万人"等は使わない
4. 年齢整合性: {age}歳で統一
5. 主観表現禁止: 評価語は一切使わない

【現在のエピソード】
{current_episode}

【人物情報】
- 人物名: {person_name}
- 年齢: {age}歳

【出力形式】
修正後のエピソードのみを出力してください（説明不要）。
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

            # 数値異常チェック
            if "100万人以上に影響" in fixed_episode or "1000万人" in fixed_episode:
                return {
                    'success': False,
                    'reason': '検証困難な数値残存',
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
                'reason': f'API呼び出しエラー: {str(e)}',
                'fixed_episode': current_episode
            }

    def process_fixes(self, qa_results_path: str, input_csv: str):
        """
        監査結果から問題レコードを修正

        Args:
            qa_results_path: 監査結果JSONパス
            input_csv: 入力CSVパス
        """
        print(f"\n{'='*60}")
        print(f"Phase 10-2: 監査問題の自動修正")
        print(f"{'='*60}")

        # 監査結果読み込み
        with open(qa_results_path, 'r', encoding='utf-8') as f:
            qa_results = json.load(f)

        # CSV読み込み
        df = pd.read_csv(input_csv, encoding='utf-8-sig')

        # 問題レコードの抽出
        failed_records = [r for r in qa_results if not r['all_passed']]
        print(f"\n修正対象: {len(failed_records)}件")

        # カテゴリー別修正
        for i, record in enumerate(failed_records, 1):
            person_id = record['person_id']
            person_name = record['person_name']
            age = record['age']

            # 現在のエピソード取得
            idx = df[df['人物ID'] == person_id].index[0]
            current_episode = str(df.loc[idx, 'エピソード本文'])

            print(f"\n{'='*60}")
            print(f"{i}/{len(failed_records)} - {person_id} - {person_name}")
            print(f"{'='*60}")

            # 問題カテゴリーの判定と修正
            if not record['subjective']['passed']:
                print(f"主観表現修正: {', '.join(record['subjective']['detected'])}")
                result = self.fix_subjective_expression(
                    person_id, person_name, age, current_episode
                )

            elif not record['age_consistency']['passed']:
                print(f"年齢不整合修正: {'; '.join(record['age_consistency']['issues'])}")
                result = self.fix_age_inconsistency(
                    person_id, person_name, age, current_episode
                )

            elif not record['numeric']['passed']:
                print(f"数値異常修正: {'; '.join(record['numeric']['issues'])}")
                result = self.fix_numeric_anomaly(
                    person_id, person_name, age, current_episode
                )

            else:
                print("⚠️ 修正不要（他の問題のみ）")
                continue

            # 修正結果の適用
            if result['success']:
                df.loc[idx, 'エピソード本文'] = result['fixed_episode']
                print(f"✅ 修正成功 ({result['char_count']}文字)")
                self.fixed_count += 1
            else:
                print(f"❌ 修正失敗: {result['reason']}")
                self.failed_fixes.append({
                    'person_id': person_id,
                    'person_name': person_name,
                    'reason': result['reason'],
                    'episode': current_episode
                })

        # 結果保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_csv = f"final_hourglass_master_v10_phase10_2_fixed_{timestamp}.csv"
        df.to_csv(output_csv, index=False, encoding='utf-8-sig')

        print(f"\n{'='*60}")
        print(f"Phase 10-2修正完了")
        print(f"{'='*60}")
        print(f"修正成功: {self.fixed_count}件")
        print(f"修正失敗: {len(self.failed_fixes)}件")
        print(f"\n✅ 出力CSV: {output_csv}")

        if self.failed_fixes:
            failed_json = f"phase10_2_failed_fixes_{timestamp}.json"
            with open(failed_json, 'w', encoding='utf-8') as f:
                json.dump(self.failed_fixes, f, ensure_ascii=False, indent=2)
            print(f"⚠️ 失敗詳細JSON: {failed_json}")

        return output_csv


def main():
    """メイン処理"""
    qa_results_path = "phase10_qa_results_20251008_071956.json"
    input_csv = "final_hourglass_master_v10_phase9_complete_20251008_065554.csv"

    fixer = Phase10AutoFixer()
    output_csv = fixer.process_fixes(qa_results_path, input_csv)

    print(f"\n{'='*60}")
    print(f"Phase 10-2完了: {output_csv}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
