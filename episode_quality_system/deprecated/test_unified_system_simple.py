#!/usr/bin/env python3
"""
統合システムの簡単なテスト
エラーの原因を特定するためのミニマル実装
"""

from unified_episode_factory import UnifiedEpisodeFactory, EpisodeGenerationRequest

def test_single_generation():
    """単一エピソード生成テスト"""
    print("=== 統合システムテスト ===\n")

    # ファクトリを初期化
    factory = UnifiedEpisodeFactory()

    # テストケース
    test_cases = [
        {
            'person_name': '大谷翔平',
            'age': 29,
            'category': 'sports'
        },
        {
            'person_name': '村上春樹',
            'age': 38,
            'category': 'literature'
        },
        {
            'person_name': '新海誠',
            'age': 43,
            'category': 'entertainment'
        }
    ]

    success_count = 0

    for test_case in test_cases:
        print(f"テスト: {test_case['person_name']} ({test_case['age']}歳)")

        # リクエスト作成（緩い設定）
        request = EpisodeGenerationRequest(
            person_name=test_case['person_name'],
            age=test_case['age'],
            category=test_case['category'],
            min_quality_score=60.0,  # 低めに設定
            max_attempts=3,
            strict_mode=False  # 厳格モードOFF
        )

        # エピソード生成
        response = factory.generate(request)

        if response.success:
            print(f"  ✅ 成功")
            print(f"     エピソード: {response.episode[:80]}...")
            print(f"     文字数: {len(response.episode)}文字")
            print(f"     品質スコア: {response.quality_score:.1f}")
            success_count += 1
        else:
            print(f"  ❌ 失敗")
            print(f"     エラー: {response.error_message}")

            # デバッグ情報
            if response.improvement_history:
                for i, history in enumerate(response.improvement_history):
                    print(f"     試行{i+1}: {history}")

        print()

    print(f"\n=== 結果: {success_count}/{len(test_cases)} 成功 ===")

    # ファクトリの統計
    print("\n=== ファクトリ統計 ===")
    stats = factory.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")


def test_with_real_facts():
    """実際の事実データを使用したテスト"""
    print("\n\n=== 事実データ使用テスト ===\n")

    factory = UnifiedEpisodeFactory()

    # 事実データを直接指定
    request = EpisodeGenerationRequest(
        person_name='大谷翔平',
        age=29,
        category='sports',
        min_quality_score=70.0,
        max_attempts=1,
        strict_mode=False
    )

    # 生成前に事実データを確認
    person_data = factory.person_facts.get('大谷翔平', {})
    if person_data:
        print("事実データ発見:")
        facts = person_data.get('facts', {})
        for key, value in facts.items():
            print(f"  {key}: {value[:100] if isinstance(value, str) else value}")

    # エピソード生成
    response = factory.generate(request)

    print("\n生成結果:")
    print(f"  成功: {response.success}")
    print(f"  エピソード: {response.episode}")
    print(f"  エラー: {response.error_message}")

    # パイプライン直接テスト
    if response.episode:
        print("\n=== パイプライン直接テスト ===")
        from mandatory_pipeline import MandatoryPipeline

        pipeline = MandatoryPipeline()
        pipeline_result = pipeline.process(
            episode=response.episode,
            person_name='大谷翔平',
            age=29,
            metadata={'category': 'sports'}
        )

        print(f"パイプライン成功: {pipeline_result.success}")
        print(f"パイプラインエラー: {pipeline_result.error_summary}")
        print(f"通過ステージ: {pipeline_result.stages_passed}")
        print(f"失敗ステージ: {pipeline_result.stages_failed}")


if __name__ == "__main__":
    test_single_generation()
    test_with_real_facts()
