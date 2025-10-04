#!/usr/bin/env python3
"""
generate_single_episode_per_person.py - 統一ファクトリv2に移行済み
このスクリプトは統一エピソードファクトリv2を使用します
"""

from unified_episode_factory_v2 import UnifiedEpisodeFactory, EpisodeGenerationRequest
import json

def main():
    """メイン処理"""

    # 統一ファクトリv2を使用（最適化モード）
    factory = UnifiedEpisodeFactory(use_optimized=True)

    # サンプル人物でテスト
    test_persons = [
        ("大谷翔平", 29, "sports"),
        ("新垣結衣", 28, "entertainment"),
        ("山中伸弥", 50, "science")
    ]

    results = []

    for person_name, age, category in test_persons:
        request = EpisodeGenerationRequest(
            person_name=person_name,
            age=age,
            category=category,
            min_quality_score=70.0,
            use_optimized=True
        )

        response = factory.generate(request)

        if response.success:
            results.append({
                "person": person_name,
                "age": age,
                "episode": response.episode,
                "score": response.quality_score
            })
            print(f"✅ {person_name}: スコア {response.quality_score:.1f}")
        else:
            print(f"❌ {person_name}: 生成失敗")

    # 結果を保存
    output_file = "generate_single_episode_per_person_migrated.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n結果を {output_file} に保存しました")
    return results

if __name__ == "__main__":
    main()
