#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
エピソード生成テスト - 実際のエピソード内容を表示
"""

import os
import sys
from datetime import datetime
import pandas as pd
from pathlib import Path

# 環境変数
from dotenv import load_dotenv
load_dotenv()

# 必要なモジュール
from premium_episode_generator import PremiumEpisodeGenerator
from episode_quality_evaluator import EpisodeQualityEvaluator

def main():
    # CSVファイル読み込み
    csv_files = list(Path('.').glob('ultra_think_*.csv'))
    if not csv_files:
        print("❌ CSVファイルが見つかりません")
        return

    latest_csv = max(csv_files, key=lambda f: f.stat().st_mtime)
    df = pd.read_csv(str(latest_csv), encoding='utf-8')

    # 高認知度の人物を選択
    test_persons = df[
        (df['birth_year_int'].notna()) &
        (df['recognition_score'] >= 8.0)
    ].sort_values('recognition_score', ascending=False).head(3)

    print("=" * 60)
    print("✨ 高品質エピソード生成デモ")
    print("=" * 60)

    # エピソード生成器初期化
    generator = PremiumEpisodeGenerator()
    evaluator = EpisodeQualityEvaluator()

    for idx, person in test_persons.iterrows():
        print(f"\n👤 {person.get('person_name_ja', 'Unknown')}")
        print(f"   生年: {person.get('birth_year_int', 'Unknown')}")
        print(f"   カテゴリ: {person.get('category', 'Unknown')}")
        print(f"   認知度スコア: {person.get('recognition_score', 0.0):.1f}")
        print("-" * 50)

        # 人物データ準備
        person_data = {
            'person_id': person.get('person_id', ''),
            'person_name_ja': person.get('person_name_ja', ''),
            'birth_year': int(person.get('birth_year_int')) if pd.notna(person.get('birth_year_int')) else None,
            'category': person.get('category', ''),
            'occupation': person.get('occupation', ''),
            'recognition_score': float(person.get('recognition_score', 0.0))
        }

        # 年齢を設定（25歳と40歳）
        target_ages = [25, 40]

        try:
            # エピソード生成
            episodes = generator.generate_premium_episodes(
                person_data=person_data,
                target_ages=target_ages
            )

            if episodes:
                for episode in episodes:
                    print(f"\n📝 【{episode.age}歳のエピソード】")
                    print(f"   {episode.episode_text}")
                    print(f"   品質スコア: {episode.quality_score:.1f}")

                    # 品質評価
                    quality = evaluator.evaluate_episode({
                        'age': episode.age,
                        'episode_text': episode.episode_text,
                        'person_name_ja': person_data['person_name_ja']
                    }, person_data)

                    print(f"   評価グレード: {quality['grade']}")
                    if quality.get('violations'):
                        print(f"   ⚠️ 違反: {', '.join(quality['violations'])}")
            else:
                print("   ❌ エピソード生成に失敗しました")

        except Exception as e:
            print(f"   ❌ エラー: {e}")

        # 最初の1人のみ
        break

    print("\n" + "=" * 60)
    print("完了")

if __name__ == "__main__":
    main()
