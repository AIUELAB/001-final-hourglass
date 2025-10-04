#!/usr/bin/env python3
"""
Phase 7.3: シンプルなLLMテスト（1ケースのみ）
"""

import os
import json
from typing import Dict, Any

from rules.rule_182_llm_improvement_engine import improve_episode_with_llm, get_llm_engine
from rules.rule_179_integrated_evaluation_pipeline import evaluate_episode_integrated


def test_single_case():
    """1つのテストケースでLLM改善を検証"""

    # テストケース
    episode_id = "EP_TEST_001"
    person_name = "大谷翔平"
    episode_text = "あなたと同じ28歳のとき、大谷翔平は素晴らしい業績を残し、多くの人々に影響を与えた。"
    database_age = 28
    birth_year = 1994

    person_context = {
        "person_name": person_name,
        "birth_year": birth_year,
        "category": "プロ野球選手"
    }

    print("🚀 Phase 7.3: OpenAI GPT-4による改善テスト")
    print(f"{'='*80}\n")

    # ステップ1: 元のエピソードを評価
    print("📝 元のエピソード:")
    print(f"   {episode_text}\n")

    print("⚙️  ステップ1: RULE_179で元のエピソードを評価...")
    evaluation_result = evaluate_episode_integrated(
        episode_id=episode_id,
        person_name=person_name,
        episode_text=episode_text,
        database_age=database_age,
        birth_year=birth_year
    )

    score = evaluation_result.total_score
    passed = evaluation_result.passed
    # violationsは直接的な属性ではないため、改善提案を使用
    violations = evaluation_result.improvements

    print(f"   スコア: {score:.1f}点 ({'✅ 合格' if passed else '❌ 不合格'})")
    print(f"   違反数: {len(violations)}件")

    if violations:
        print("   改善提案:")
        for v in violations[:3]:  # 最初の3件のみ表示
            print(f"     - {v}")

    # ステップ2: OpenAI GPT-4で改善
    print(f"\n⚙️  ステップ2: OpenAI GPT-4で改善を試行...")

    try:
        improved_text, improvement_summary = improve_episode_with_llm(
            episode_text,
            evaluation_result,
            person_context,
            provider="openai",
            use_fallback=True
        )

        print(f"   改善方法: {improvement_summary.get('method', 'unknown')}")

        if "llm" in improvement_summary.get('method', ''):
            print(f"   プロバイダー: {improvement_summary.get('provider', 'unknown')}")

        print(f"\n✨ 改善後のエピソード:")
        print(f"   {improved_text}\n")

        # ステップ3: 改善後を再評価
        print("⚙️  ステップ3: 改善後のエピソードを再評価...")
        improved_evaluation = evaluate_episode_integrated(
            episode_id=episode_id,
            person_name=person_name,
            episode_text=improved_text,
            database_age=database_age,
            birth_year=birth_year
        )

        improved_score = improved_evaluation.total_score
        improved_passed = improved_evaluation.passed
        improved_violations = improved_evaluation.improvements

        print(f"   改善後スコア: {improved_score:.1f}点 ({'✅ 合格' if improved_passed else '❌ 不合格'})")
        print(f"   改善後違反数: {len(improved_violations)}件")
        print(f"   スコア変化: {improved_score - score:+.1f}点")

        # 結果サマリー
        print(f"\n{'='*80}")
        print("📊 結果サマリー")
        print(f"{'='*80}\n")

        print(f"元のエピソード:")
        print(f"  {episode_text}")
        print(f"  スコア: {score:.1f}点, 違反: {len(violations)}件\n")

        print(f"改善後:")
        print(f"  {improved_text}")
        print(f"  スコア: {improved_score:.1f}点, 違反: {len(improved_violations)}件")
        print(f"  改善幅: {improved_score - score:+.1f}点\n")

        print(f"改善方法: {improvement_summary.get('method', 'unknown')}")

        if improvement_summary.get('method') == 'llm':
            print("✅ LLMによる改善が成功しました")
        elif 'fallback' in improvement_summary.get('method', ''):
            print("⚠️  LLM改善が失敗し、RULE_180にフォールバックしました")
            if 'validation_errors' in improvement_summary:
                print(f"   理由: {improvement_summary['validation_errors']}")

        # 結果をJSONに保存
        result = {
            "test_case": {
                "person_name": person_name,
                "episode_text": episode_text,
                "age": database_age
            },
            "original_evaluation": {
                "score": score,
                "passed": passed,
                "violations_count": len(violations)
            },
            "improved_text": improved_text,
            "improved_evaluation": {
                "score": improved_score,
                "passed": improved_passed,
                "violations_count": len(improved_violations)
            },
            "improvement_summary": improvement_summary,
            "score_improvement": improved_score - score
        }

        with open("phase7_simple_test_result.json", 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"\n💾 詳細結果を phase7_simple_test_result.json に保存しました")

    except Exception as e:
        print(f"\n❌ エラー発生: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    # OpenAI APIキー確認
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY が設定されていません")
        print("   export OPENAI_API_KEY=your_key を実行してください")
        exit(1)

    success = test_single_case()

    if success:
        print("\n✅ Phase 7.3: シンプルテスト完了")
    else:
        print("\n❌ Phase 7.3: テスト失敗")
        exit(1)
