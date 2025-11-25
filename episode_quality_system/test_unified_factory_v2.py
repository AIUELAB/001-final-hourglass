#!/usr/bin/env python3
"""
統一エピソードファクトリv2のテスト
最適化システムが正常に動作することを確認
"""

from unified_episode_factory_v2 import UnifiedEpisodeFactory, EpisodeGenerationRequest

def test_unified_factory_v2():
    """統一ファクトリv2のテスト"""

    print("=" * 60)
    print("🧪 統一エピソードファクトリ v2 テスト")
    print("=" * 60)

    # 最適化モードでファクトリを初期化
    factory = UnifiedEpisodeFactory(use_optimized=True)

    # テストケース
    test_cases = [
        ("大谷翔平", 29, "sports"),
        ("新垣結衣", 28, "entertainment"),
        ("山中伸弥", 50, "science"),
        ("孫正義", 33, "business"),
        ("村上春樹", 40, "literature")
    ]

    success_count = 0
    total_score = 0

    for person_name, age, category in test_cases:
        print(f"\n▶ {person_name} ({category})")

        request = EpisodeGenerationRequest(
            person_name=person_name,
            age=age,
            category=category,
            min_quality_score=70.0,  # 最適化された基準
            max_attempts=3,
            use_optimized=True  # 最適化システムを使用
        )

        response = factory.generate(request)

        if response.success:
            success_count += 1
            total_score += response.quality_score
            print(f"  ✅ 成功 (試行{response.attempts}回)")
            print(f"  文字数: {len(response.episode)}文字")
            print(f"  スコア: {response.quality_score:.1f}/100")
            print(f"  エピソード: {response.episode[:80]}...")
        else:
            print(f"  ❌ 失敗 (試行{response.attempts}回)")
            if response.error_message:
                print(f"  エラー: {response.error_message}")

    # 結果サマリー
    print("\n" + "=" * 60)
    print("📊 テスト結果サマリー")
    print("=" * 60)

    success_rate = (success_count / len(test_cases)) * 100
    avg_score = total_score / success_count if success_count > 0 else 0

    print(f"成功率: {success_rate:.1f}% ({success_count}/{len(test_cases)})")
    print(f"平均スコア: {avg_score:.1f}/100")

    # 統計情報
    stats = factory.get_stats()
    print(f"\n生成統計:")
    print(f"  総リクエスト: {stats['total_requests']}")
    print(f"  成功: {stats['successful_generations']}")
    print(f"  失敗: {stats['failed_generations']}")
    print(f"  バイパス試行: {stats['bypass_attempts']}")

    # 最適化の効果を確認
    print("\n" + "=" * 60)
    if success_rate >= 80:
        print("🎉 最適化システムが正常に動作しています！")
    else:
        print("📈 さらなる最適化が必要です")

if __name__ == "__main__":
    test_unified_factory_v2()
