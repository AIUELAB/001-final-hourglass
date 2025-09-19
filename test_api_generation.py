#!/usr/bin/env python3
"""
API生成のダイレクトテスト
"""

import os
import json
from dotenv import load_dotenv

# .envファイルを読み込み
load_dotenv()

# ローカルインポート
from premium_episode_generator import PremiumEpisodeGenerator

def test_generate_episode():
    """エピソード生成のダイレクトテスト"""
    print("=" * 60)
    print("エピソード生成ダイレクトテスト")
    print("=" * 60)

    # テスト用の人物データ
    test_person = {
        'person_id': 'P000263',
        'person_name_ja': 'イチロー',
        'birth_year': 1973,
        'category': 'スポーツ',
        'occupation': '元プロ野球選手',
        'recognition_score': 10.0,
        'wikipedia_url': 'https://ja.wikipedia.org/wiki/イチロー'
    }

    print(f"\nテスト対象: {test_person['person_name_ja']}")
    print(f"  生年: {test_person['birth_year']}年")
    print(f"  カテゴリ: {test_person['category']}")

    # エピソード生成器の初期化
    try:
        generator = PremiumEpisodeGenerator()
        print("\n✅ Generator初期化成功")
        print(f"  OpenAI: {'利用可能' if generator.openai_client else '利用不可'}")
        print(f"  Anthropic: {'利用可能' if generator.anthropic_client else '利用不可'}")

        # エピソード生成
        print("\n=== エピソード生成開始 ===")

        # ターゲット年齢（20歳、30歳、40歳）
        target_ages = [20, 30, 40]

        episodes = generator.generate_premium_episodes(
            person_data=test_person,
            target_ages=target_ages
        )

        print(f"\n✅ {len(episodes)}件のエピソード生成完了")

        # エピソードの表示
        for episode in episodes:
            print(f"\n【{episode.age}歳のエピソード】")
            print(f"  {episode.episode_text}")
            print(f"  品質スコア: {episode.quality_score:.1f}")
            print(f"  グレード: {episode.grade}")
            print(f"  戦略: {episode.strategy.value}")
            print(f"  キーワード: {', '.join(episode.keywords[:3])}")

    except Exception as e:
        print(f"\n❌ エラー発生: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_generate_episode()