#!/usr/bin/env python3
"""
ローカル生成機能のテスト
"""

import os
import json
from dotenv import load_dotenv

# .envファイルを読み込み
load_dotenv()

# 環境変数を一時的に削除してローカル生成を強制
original_openai = os.environ.get("OPENAI_API_KEY")
original_anthropic = os.environ.get("ANTHROPIC_API_KEY")

# APIキーを一時的に無効化
os.environ.pop("OPENAI_API_KEY", None)
os.environ.pop("ANTHROPIC_API_KEY", None)

# ローカルインポート
from premium_episode_generator import PremiumEpisodeGenerator

def test_local_generation():
    """ローカル生成のテスト"""
    print("=" * 60)
    print("ローカル生成機能テスト（API無効化）")
    print("=" * 60)

    # テスト用の人物データ（複数カテゴリ）
    test_persons = [
        {
            'person_id': 'P000263',
            'person_name_ja': 'イチロー',
            'birth_year': 1973,
            'category': 'スポーツ',
            'occupation': '元プロ野球選手',
            'recognition_score': 10.0
        },
        {
            'person_id': 'P001234',
            'person_name_ja': '織田信長',
            'birth_year': 1534,
            'category': '歴史人物',
            'occupation': '戦国武将',
            'recognition_score': 10.0
        },
        {
            'person_id': 'P002345',
            'person_name_ja': '松本人志',
            'birth_year': 1963,
            'category': 'エンタメ',
            'occupation': 'お笑い芸人',
            'recognition_score': 9.0
        },
        {
            'person_id': 'P003456',
            'person_name_ja': '山中伸弥',
            'birth_year': 1962,
            'category': '科学者',
            'occupation': '医学者',
            'recognition_score': 8.5
        }
    ]

    # エピソード生成器の初期化
    try:
        generator = PremiumEpisodeGenerator()
        print("\n✅ Generator初期化成功")
        print(f"  OpenAI: {'利用可能' if generator.openai_client else '利用不可'}")
        print(f"  Anthropic: {'利用可能' if generator.anthropic_client else '利用不可'}")

        if generator.openai_client or generator.anthropic_client:
            print("\n⚠️ APIが有効になっています。環境変数を確認してください。")
        else:
            print("\n✅ API無効確認：ローカル生成を使用します")

        # 各人物でテスト
        for person in test_persons:
            print(f"\n{'='*60}")
            print(f"テスト対象: {person['person_name_ja']} ({person['category']})")
            print(f"  生年: {person['birth_year']}年")

            # ターゲット年齢
            if person['birth_year'] < 1900:
                target_ages = [25, 35, 45]  # 歴史人物
            else:
                target_ages = [20, 30, 40]  # 現代人

            # エピソード生成
            episodes = generator.generate_premium_episodes(
                person_data=person,
                target_ages=target_ages
            )

            print(f"\n✅ {len(episodes)}件のエピソード生成")

            # エピソードの表示
            for episode in episodes:
                print(f"\n【{episode.age}歳のエピソード】")
                print(f"  {episode.episode_text[:100]}...")
                print(f"  品質スコア: {episode.quality_score:.1f}")
                print(f"  グレード: {episode.grade}")
                print(f"  戦略: {episode.strategy.value}")

    except Exception as e:
        print(f"\n❌ エラー発生: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # 環境変数を復元
        if original_openai:
            os.environ["OPENAI_API_KEY"] = original_openai
        if original_anthropic:
            os.environ["ANTHROPIC_API_KEY"] = original_anthropic

if __name__ == "__main__":
    test_local_generation()