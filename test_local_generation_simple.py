#!/usr/bin/env python3
"""
ローカル生成機能の簡易テスト
"""

# premium_episode_generatorから直接_generate_locallyをテスト
from premium_episode_generator import PremiumEpisodeGenerator

def test_direct_local_generation():
    """直接ローカル生成関数をテスト"""
    print("=" * 60)
    print("ローカル生成関数の直接テスト")
    print("=" * 60)

    generator = PremiumEpisodeGenerator()

    # テスト用プロンプト（異なるカテゴリ）
    test_prompts = [
        {
            'prompt': """【人物情報】
名前: イチロー
年齢: 28歳
生年: 1973年
カテゴリ: スポーツ""",
            'expected_name': 'イチロー',
            'expected_age': 28,
            'expected_category': 'スポーツ'
        },
        {
            'prompt': """【人物情報】
名前: 織田信長
年齢: 35歳
生年: 1534年
カテゴリ: 歴史人物""",
            'expected_name': '織田信長',
            'expected_age': 35,
            'expected_category': '歴史人物'
        },
        {
            'prompt': """【人物情報】
名前: 山中伸弥
年齢: 45歳
生年: 1962年
カテゴリ: 科学者""",
            'expected_name': '山中伸弥',
            'expected_age': 45,
            'expected_category': '科学者'
        },
        {
            'prompt': """【人物情報】
名前: 北野武
年齢: 40歳
生年: 1947年
カテゴリ: エンタメ""",
            'expected_name': '北野武',
            'expected_age': 40,
            'expected_category': 'エンタメ'
        }
    ]

    for i, test in enumerate(test_prompts, 1):
        print(f"\n【テスト {i}】")
        print(f"対象: {test['expected_name']} ({test['expected_category']})")
        print(f"年齢: {test['expected_age']}歳")

        # ローカル生成実行
        episode_text = generator._generate_locally(test['prompt'])

        if episode_text:
            print(f"\n生成されたエピソード:")
            print(f"  {episode_text[:150]}...")

            # 基本チェック
            checks = []
            checks.append(("開始フォーマット", f"あなたと同じ{test['expected_age']}歳のとき、" in episode_text))
            checks.append(("人名含有", test['expected_name'] in episode_text))
            checks.append(("文字数", 100 <= len(episode_text) <= 500))

            print("\n品質チェック:")
            for check_name, result in checks:
                print(f"  {check_name}: {'✅' if result else '❌'}")
        else:
            print(f"❌ エピソード生成失敗")

        print("-" * 60)

if __name__ == "__main__":
    test_direct_local_generation()