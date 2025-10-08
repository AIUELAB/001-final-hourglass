#!/usr/bin/env python3
"""
エピソード内年齢重複削除システム

RCA-Kaizen Loop: FAIL_20251008_004 (KA_013)

問題: 「あなたと同じ66歳のとき、隈研吾（66歳）は」のような年齢重複
解決: 括弧付き年齢を自動削除

Author: Final Hourglass Project
Date: 2025-10-08
Version: 1.0.0
"""

import pandas as pd
import re
from typing import Dict, List
from datetime import datetime
from pathlib import Path


class AgeDuplicationFixer:
    """
    エピソード内年齢重複削除システム

    修正パターン:
    - 「人物名（XX歳）」→「人物名」
    - 文字数範囲（180-280文字）を維持
    """

    def __init__(self):
        self.fixed_count = 0
        self.violations: List[Dict] = []

    def detect_age_duplication(self, episode: str, person_name: str, age: int) -> bool:
        """
        年齢重複を検出

        Args:
            episode: エピソード本文
            person_name: 人物名
            age: 年齢

        Returns:
            年齢重複があればTrue
        """
        # 括弧付き年齢パターン
        pattern = rf'{re.escape(person_name)}（\d+歳）'
        return bool(re.search(pattern, episode))

    def fix_age_duplication(self, episode: str, person_name: str) -> str:
        """
        年齢重複を削除

        Args:
            episode: エピソード本文
            person_name: 人物名

        Returns:
            修正後のエピソード
        """
        # 括弧付き年齢を削除
        pattern = rf'({re.escape(person_name)})（\d+歳）'
        fixed_episode = re.sub(pattern, r'\1', episode)

        return fixed_episode

    def process_csv(self, csv_path: str) -> str:
        """
        CSV全体の年齢重複を検出・修正

        Args:
            csv_path: 入力CSVパス

        Returns:
            出力CSVパス
        """
        df = pd.read_csv(csv_path, encoding='utf-8-sig')

        print(f"📊 読み込み完了: {len(df)} records")

        # 合格レコードのみ
        qualified = df[df['ステータス'] == '合格'].copy()
        print(f"合格レコード: {len(qualified)}")

        # 年齢重複検出
        print("\n🔍 年齢重複を検出中...")

        for idx, row in qualified.iterrows():
            person_id = str(row['人物ID'])
            person_name = str(row['人物名'])
            age = int(row['年齢'])
            episode = str(row['エピソード本文'])

            if self.detect_age_duplication(episode, person_name, age):
                self.violations.append({
                    'index': idx,
                    'person_id': person_id,
                    'person_name': person_name,
                    'age': age,
                    'original_episode': episode
                })

        print(f"検出結果: {len(self.violations)}件の年齢重複")

        if len(self.violations) == 0:
            print("\n✅ 年齢重複なし - 修正不要")
            return csv_path

        # 修正実行
        print("\n" + "="*70)
        print("🔧 年齢重複削除を開始")
        print("="*70)

        for i, violation in enumerate(self.violations, 1):
            idx = violation['index']
            person_id = violation['person_id']
            person_name = violation['person_name']
            age = violation['age']
            original_episode = violation['original_episode']

            print(f"\n[{i}/{len(self.violations)}] {person_id} - {person_name} ({age}歳)")
            print(f"元: {original_episode[:80]}...")

            # 修正
            fixed_episode = self.fix_age_duplication(original_episode, person_name)

            # 文字数チェック
            char_count = len(fixed_episode)
            original_char_count = len(original_episode)

            if not (180 <= char_count <= 280):
                print(f"⚠️ 警告: 文字数範囲外 ({char_count}文字)")
                print(f"   元の文字数: {original_char_count}文字")
            else:
                print(f"✅ 修正完了: {char_count}文字 (元: {original_char_count}文字)")

            print(f"新: {fixed_episode[:80]}...")

            # DataFrameを更新
            df.at[idx, 'エピソード本文'] = fixed_episode
            df.at[idx, '文字数'] = char_count

            self.fixed_count += 1

        # 統計
        print("\n" + "="*70)
        print("📊 修正結果")
        print("="*70)
        print(f"修正完了: {self.fixed_count}/{len(self.violations)}")

        # CSV出力
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"final_hourglass_week1_6_age_fixed_{timestamp}.csv"

        with open(output_path, 'w', encoding='utf-8-sig') as f:
            df.to_csv(f, index=False)

        print(f"\n✅ 修正完了: {output_path}")

        return output_path


if __name__ == "__main__":
    try:
        fixer = AgeDuplicationFixer()

        # 最新のCSVファイルを検索
        csv_files = list(Path(".").glob("final_hourglass_week1_6_*.csv"))
        latest_csv = max(csv_files, key=lambda p: p.stat().st_mtime)

        print(f"📁 入力CSV: {latest_csv}")

        output_path = fixer.process_csv(str(latest_csv))

        print("\n" + "="*70)
        print("🎯 次のステップ")
        print("="*70)
        print("1. test_age_duplication_prohibition テストケース追加")
        print("2. pytest tests/test_episode_format.py -v で全テスト実行")
        print("3. REQUIREMENTS.md v1.3.0更新")
        print("4. RCA-Kaizen Loop統合 (FAIL_20251008_004.json)")
        print("5. 最終CSV→Git コミット")

    except Exception as e:
        print(f"❌ エラー: {e}")
        raise
