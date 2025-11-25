#!/usr/bin/env python3
"""
統合システムのデバッグ
"""

from integrated_optimized_factory import IntegratedOptimizedFactory, OptimizedGenerationRequest
import traceback

def debug_test():
    """詳細なデバッグテスト"""

    factory = IntegratedOptimizedFactory()

    # 1件だけ詳細テスト
    person_name = "大谷翔平"
    age = 29
    category = "sports"

    print(f"テスト: {person_name} ({category})")
    print("=" * 60)

    # データベース確認
    print("\n1. データベース確認:")
    person_facts = factory._get_person_facts(person_name)
    if person_facts:
        print(f"  ✅ データ発見:")
        for key, value in person_facts.items():
            if isinstance(value, list) and value:
                print(f"    {key}: {value[0]}...")
            else:
                print(f"    {key}: {value}")
    else:
        print(f"  ❌ データなし")

    # カテゴリ確認
    print("\n2. カテゴリ確認:")
    detected_category = factory._determine_category(person_name)
    print(f"  検出: {detected_category}")

    # 生成テスト
    print("\n3. エピソード生成:")
    request = OptimizedGenerationRequest(
        person_name=person_name,
        age=age,
        category=category,
        max_attempts=1  # 1回だけ試行
    )

    try:
        # テンプレート生成を直接呼び出し
        if person_facts:
            episode = factory._generate_with_templates(person_name, age, category, person_facts)
            print(f"  生成成功: {episode[:100]}...")
            print(f"  文字数: {len(episode)}")
        else:
            print("  事実データがないため、基本生成を使用")
            episode = factory._generate_basic(person_name, age, category, person_facts)
            print(f"  生成成功: {episode[:100]}...")
            print(f"  文字数: {len(episode)}")

    except Exception as e:
        print(f"  エラー: {e}")
        print(f"  詳細:")
        traceback.print_exc()

    print("\n4. 完全な生成テスト:")
    try:
        response = factory.generate(request)
        if response.success:
            print(f"  ✅ 成功")
            print(f"  文字数: {len(response.episode)}")
            print(f"  スコア: {response.validation_result.score}")
        else:
            print(f"  ❌ 失敗: {response.error_message}")
    except Exception as e:
        print(f"  エラー: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    debug_test()
