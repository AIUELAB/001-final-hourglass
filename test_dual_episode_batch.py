#!/usr/bin/env python3
"""
デュアルエピソード生成システム - バッチ処理テスト
複数の有名人に対してエピソード生成を実行
"""

from dual_episode_generator import DualEpisodeGenerator, EpisodeRequest
from dotenv import load_dotenv

# 環境変数読み込み
load_dotenv()


def main():
    """バッチ処理テスト"""

    # テスト対象の有名人データ
    test_persons = [
        EpisodeRequest(
            person_id="P000001",
            person_name="イチロー",
            display_name="イチロー",
            user_age=35,
            occupation="プロ野球選手",
            category="スポーツ",
            google_search_count=5000000,
            birth_year=1973,
            wikipedia_url="https://ja.wikipedia.org/wiki/イチロー"
        ),
        EpisodeRequest(
            person_id="P000002",
            person_name="大谷翔平",
            display_name="大谷翔平",
            user_age=28,
            occupation="プロ野球選手",
            category="スポーツ",
            google_search_count=8000000,
            birth_year=1994,
            wikipedia_url="https://ja.wikipedia.org/wiki/大谷翔平"
        ),
        EpisodeRequest(
            person_id="P000003",
            person_name="村上春樹",
            display_name="村上春樹",
            user_age=50,
            occupation="小説家",
            category="文化",
            google_search_count=3000000,
            birth_year=1949,
            wikipedia_url="https://ja.wikipedia.org/wiki/村上春樹"
        ),
    ]

    # ジェネレーター初期化
    generator = DualEpisodeGenerator(
        auto_correct=True,
        reject_on_failure=False  # 失敗してもCSVに記録
    )

    # バッチ生成実行
    results = generator.generate_batch(
        requests=test_persons,
        output_csv_path="dual_episodes_test_output.csv"
    )

    # 詳細結果表示
    print("\n" + "="*80)
    print("詳細結果")
    print("="*80 + "\n")

    for i, (iconic, unexpected) in enumerate(results, 1):
        person = test_persons[i-1]
        print(f"[{i}] {person.display_name}")
        print("-" * 80)

        if iconic:
            print("\n【定番エピソード】")
            print(f"テキスト: {iconic.episode_text}")
            print(f"年齢: {iconic.episode_age}歳")
            print(f"文字数: {len(iconic.episode_text)}文字")
            print(f"検証: {'✅ 合格' if iconic.is_valid else '❌ 不合格'}")
            if not iconic.is_valid:
                print(f"違反数: {len(iconic.validation_result.violations)}")
                for violation in iconic.validation_result.violations:
                    print(f"  - {violation.message}")
        else:
            print("\n【定番エピソード】: ❌ 生成失敗")

        if unexpected:
            print("\n【意外性エピソード】")
            print(f"テキスト: {unexpected.episode_text}")
            print(f"年齢: {unexpected.episode_age}歳")
            print(f"文字数: {len(unexpected.episode_text)}文字")
            print(f"検証: {'✅ 合格' if unexpected.is_valid else '❌ 不合格'}")
            if not unexpected.is_valid:
                print(f"違反数: {len(unexpected.validation_result.violations)}")
                for violation in unexpected.validation_result.violations:
                    print(f"  - {violation.message}")
        else:
            print("\n【意外性エピソード】: ❌ 生成失敗")

        print("\n")


if __name__ == "__main__":
    main()
