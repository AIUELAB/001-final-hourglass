#!/usr/bin/env python3
"""
拡張データベースを使用したエピソード生成テスト
"""

import json
from pathlib import Path
from unified_episode_factory import UnifiedEpisodeFactory, EpisodeGenerationRequest

def test_expanded_database():
    """拡張データベースのテスト"""

    print("=" * 60)
    print("📚 拡張データベーステスト開始")
    print("=" * 60)

    # ファクトリー初期化
    factory = UnifiedEpisodeFactory()

    # テスト対象（新しく追加した人物を中心に）
    test_persons = [
        ("錦織圭", 24, "sports"),
        ("松本人志", 27, "entertainment"),
        ("安室奈美恵", 25, "entertainment"),
        ("夏目漱石", 40, "literature"),
        ("稲盛和夫", 27, "business"),
        ("湯川秀樹", 28, "science"),
        ("久保建英", 18, "sports"),
        ("鳥山明", 31, "entertainment"),
        ("三浦知良", 30, "sports"),
        ("村上隆", 41, "art")
    ]

    results = []
    success_count = 0

    for person_name, age, category in test_persons:
        print(f"\n[テスト] {person_name} ({age}歳) - {category}")

        # データベースにあるか確認
        if person_name in factory.person_facts:
            print(f"  ✅ 事実データ: あり")
            facts = factory.person_facts[person_name]["facts"]
            print(f"    - 実績: {len(facts.get('achievements', []))}件")
            print(f"    - 数値: {len(facts.get('numbers', []))}件")
            print(f"    - 作品: {len(facts.get('works', []))}件")
        else:
            print(f"  ❌ 事実データ: なし")

        # エピソード生成
        request = EpisodeGenerationRequest(
            person_name=person_name,
            age=age,
            category=category,
            min_quality_score=70.0,
            max_attempts=5,
            strict_mode=True
        )

        response = factory.generate(request)

        if response.success and response.episode:
            print(f"  ✅ 生成成功")
            print(f"    品質: {response.quality_score:.1f}")
            print(f"    文字数: {len(response.episode)}")
            print(f"    試行回数: {response.attempts}")
            print(f"    エピソード: {response.episode[:60]}...")

            results.append({
                'name': person_name,
                'success': True,
                'episode': response.episode,
                'quality': response.quality_score,
                'length': len(response.episode)
            })
            success_count += 1
        else:
            print(f"  ❌ 生成失敗: {response.error_message}")
            results.append({
                'name': person_name,
                'success': False,
                'error': response.error_message
            })

    # 統計表示
    print("\n" + "=" * 60)
    print("📊 テスト結果統計")
    print("=" * 60)
    print(f"テスト人数: {len(test_persons)}人")
    print(f"成功: {success_count}人 ({success_count/len(test_persons)*100:.1f}%)")
    print(f"失敗: {len(test_persons) - success_count}人")

    if success_count > 0:
        successful_results = [r for r in results if r['success']]
        avg_quality = sum(r['quality'] for r in successful_results) / len(successful_results)
        avg_length = sum(r['length'] for r in successful_results) / len(successful_results)
        print(f"\n成功エピソードの統計:")
        print(f"  平均品質スコア: {avg_quality:.1f}")
        print(f"  平均文字数: {avg_length:.1f}")

    # データベースカバレッジ
    print(f"\nデータベースカバレッジ:")
    with_data = sum(1 for p in test_persons if p[0] in factory.person_facts)
    print(f"  事実データあり: {with_data}/{len(test_persons)} ({with_data/len(test_persons)*100:.1f}%)")

    # 結果をJSONで保存
    output_file = "test_expanded_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n✅ テスト結果保存: {output_file}")

if __name__ == "__main__":
    test_expanded_database()
