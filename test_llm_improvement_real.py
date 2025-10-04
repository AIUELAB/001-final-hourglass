#!/usr/bin/env python3
"""
Phase 7.3: 実際のLLMプロバイダーでのRULE_182テスト

目的:
- OpenAI GPT-4での実際の改善品質評価
- プロンプトの有効性検証
- トークン使用量とコスト測定
- RULE_180との品質比較
"""

import os
import sys
import json
from typing import Dict, List, Any, Tuple

# RULE_182とRULE_179のインポート
from rules.rule_182_llm_improvement_engine import improve_episode_with_llm, get_llm_engine
from rules.rule_179_integrated_evaluation_pipeline import evaluate_episode_integrated
from rules.rule_180_automatic_improvement_engine import improve_episode_automatically


def setup_test_cases() -> List[Dict[str, Any]]:
    """テストケースの準備"""
    return [
        {
            "episode_text": "あなたと同じ28歳のとき、大谷翔平は素晴らしい業績を残し、多くの人々に影響を与えた。",
            "person_context": {
                "person_name": "大谷翔平",
                "birth_year": 1994,
                "category": "プロ野球選手"
            },
            "description": "抽象表現・センセーショナル表現のテスト"
        },
        {
            "episode_text": "あなたと同じ30歳のとき、イチローは2004年にメジャーリーグで大活躍した。",
            "person_context": {
                "person_name": "イチロー",
                "birth_year": 1973,
                "category": "プロ野球選手"
            },
            "description": "時系列矛盾のテスト（30歳=2003年なのに2004年と記述）"
        },
        {
            "episode_text": "あなたと同じ25歳のとき、羽生結弦は最高の演技で金メダルを獲得した。",
            "person_context": {
                "person_name": "羽生結弦",
                "birth_year": 1994,
                "category": "フィギュアスケーター"
            },
            "description": "抽象表現のテスト（具体的な大会名・年が不明）"
        }
    ]


def test_llm_provider(provider_name: str, test_cases: List[Dict]) -> Dict[str, Any]:
    """指定したプロバイダーでテスト実行"""

    print(f"\n{'='*80}")
    print(f"🤖 {provider_name.upper()} プロバイダーでのテスト")
    print(f"{'='*80}\n")

    results = {
        "provider": provider_name,
        "test_cases": [],
        "summary": {
            "total": len(test_cases),
            "improved": 0,
            "fallback": 0,
            "errors": 0
        },
        "cost_estimation": {
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "estimated_cost_usd": 0.0
        }
    }

    for idx, test_case in enumerate(test_cases, 1):
        print(f"\n📝 テストケース {idx}/{len(test_cases)}: {test_case['description']}")
        print(f"元のエピソード: {test_case['episode_text']}")

        try:
            # ステップ1: RULE_179で評価
            print("\n⚙️  ステップ1: RULE_179による評価...")
            evaluation_result = evaluate_episode_integrated(test_case['episode_text'], test_case['person_context'])

            passed = evaluation_result.get("passed", False)
            score = evaluation_result.get("final_score", 0)
            print(f"   評価スコア: {score:.1f}点 ({'合格' if passed else '不合格'})")

            # ステップ2: LLMで改善
            print(f"\n⚙️  ステップ2: {provider_name.upper()}による改善...")
            improved_text, improvement_summary = improve_episode_with_llm(
                test_case['episode_text'],
                evaluation_result,
                test_case['person_context'],
                provider=provider_name,
                use_fallback=True
            )

            # ステップ3: 改善後の評価
            print("\n⚙️  ステップ3: 改善後の再評価...")
            improved_evaluation = evaluate_episode_integrated(improved_text, test_case['person_context'])
            improved_score = improved_evaluation.get("final_score", 0)
            improved_passed = improved_evaluation.get("passed", False)

            # 結果表示
            print(f"\n✨ 改善結果:")
            print(f"   改善後: {improved_text}")
            print(f"   改善方法: {improvement_summary.get('method', 'unknown')}")
            print(f"   改善後スコア: {improved_score:.1f}点 ({'合格' if improved_passed else '不合格'})")
            print(f"   スコア変化: {improved_score - score:+.1f}点")

            # 統計更新
            if improvement_summary.get("improved"):
                if improvement_summary.get("method") == "llm":
                    results["summary"]["improved"] += 1
                elif "fallback" in improvement_summary.get("method", ""):
                    results["summary"]["fallback"] += 1

            # テスト結果記録
            test_result = {
                "case_number": idx,
                "description": test_case["description"],
                "original_text": test_case["episode_text"],
                "improved_text": improved_text,
                "original_score": score,
                "improved_score": improved_score,
                "score_improvement": improved_score - score,
                "improvement_summary": improvement_summary,
                "original_passed": passed,
                "improved_passed": improved_passed
            }

            results["test_cases"].append(test_result)

        except Exception as e:
            print(f"\n❌ エラー発生: {str(e)}")
            results["summary"]["errors"] += 1
            results["test_cases"].append({
                "case_number": idx,
                "description": test_case["description"],
                "error": str(e)
            })

    return results


def compare_with_rule180(test_cases: List[Dict]) -> Dict[str, Any]:
    """RULE_180との比較評価"""

    print(f"\n{'='*80}")
    print(f"📊 RULE_180 vs LLM 比較評価")
    print(f"{'='*80}\n")

    comparison_results = []

    for idx, test_case in enumerate(test_cases, 1):
        print(f"\n📝 テストケース {idx}: {test_case['description']}")

        # 元の評価
        evaluation_result = evaluate_episode_integrated(test_case['episode_text'], test_case['person_context'])
        original_score = evaluation_result.get("final_score", 0)

        # RULE_180による改善
        print("   RULE_180による改善...")
        rule180_text, rule180_summary = improve_episode_automatically(
            test_case['episode_text'],
            evaluation_result,
            max_iterations=3
        )
        rule180_evaluation = evaluate_episode_integrated(rule180_text, test_case['person_context'])
        rule180_score = rule180_evaluation.get("final_score", 0)

        # LLMによる改善
        print("   LLMによる改善...")
        llm_text, llm_summary = improve_episode_with_llm(
            test_case['episode_text'],
            evaluation_result,
            test_case['person_context'],
            provider="openai",
            use_fallback=False  # フォールバック無効で純粋なLLM性能を測定
        )
        llm_evaluation = evaluate_episode_integrated(llm_text, test_case['person_context'])
        llm_score = llm_evaluation.get("final_score", 0)

        print(f"\n   📈 スコア比較:")
        print(f"      元のスコア:    {original_score:.1f}点")
        print(f"      RULE_180:     {rule180_score:.1f}点 ({rule180_score - original_score:+.1f})")
        print(f"      LLM:          {llm_score:.1f}点 ({llm_score - original_score:+.1f})")
        print(f"      優位性:        {'LLM' if llm_score > rule180_score else 'RULE_180'} ({abs(llm_score - rule180_score):.1f}点差)")

        comparison_results.append({
            "case_number": idx,
            "description": test_case["description"],
            "original_score": original_score,
            "rule180_score": rule180_score,
            "rule180_improvement": rule180_score - original_score,
            "llm_score": llm_score,
            "llm_improvement": llm_score - original_score,
            "winner": "LLM" if llm_score > rule180_score else "RULE_180",
            "score_difference": abs(llm_score - rule180_score)
        })

    return {
        "test_cases": comparison_results,
        "summary": {
            "llm_wins": sum(1 for r in comparison_results if r["winner"] == "LLM"),
            "rule180_wins": sum(1 for r in comparison_results if r["winner"] == "RULE_180"),
            "average_llm_improvement": sum(r["llm_improvement"] for r in comparison_results) / len(comparison_results),
            "average_rule180_improvement": sum(r["rule180_improvement"] for r in comparison_results) / len(comparison_results)
        }
    }


def main():
    """メインテスト実行"""

    print("🚀 Phase 7.3: 実際のLLMプロバイダーテスト開始")
    print(f"{'='*80}\n")

    # テストケース準備
    test_cases = setup_test_cases()

    # OpenAI APIキーチェック
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY が設定されていません")
        print("   export OPENAI_API_KEY=your_key を実行してください")
        sys.exit(1)

    all_results = {}

    # OpenAIテスト
    print("\n🎯 OpenAI GPT-4でのテスト実行...")
    openai_results = test_llm_provider("openai", test_cases)
    all_results["openai"] = openai_results

    # RULE_180との比較
    print("\n🎯 RULE_180との比較評価...")
    comparison_results = compare_with_rule180(test_cases)
    all_results["comparison"] = comparison_results

    # 結果サマリー
    print(f"\n{'='*80}")
    print("📊 テスト結果サマリー")
    print(f"{'='*80}\n")

    print("OpenAI GPT-4:")
    print(f"  - 成功: {openai_results['summary']['improved']}件")
    print(f"  - フォールバック: {openai_results['summary']['fallback']}件")
    print(f"  - エラー: {openai_results['summary']['errors']}件")

    print(f"\nRULE_180 vs LLM:")
    print(f"  - LLM勝利: {comparison_results['summary']['llm_wins']}件")
    print(f"  - RULE_180勝利: {comparison_results['summary']['rule180_wins']}件")
    print(f"  - LLM平均改善: {comparison_results['summary']['average_llm_improvement']:+.1f}点")
    print(f"  - RULE_180平均改善: {comparison_results['summary']['average_rule180_improvement']:+.1f}点")

    # 結果をJSONファイルに保存
    output_file = "phase7_llm_test_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print(f"\n💾 詳細結果を {output_file} に保存しました")

    # 推奨事項
    print(f"\n{'='*80}")
    print("💡 推奨事項")
    print(f"{'='*80}\n")

    if comparison_results['summary']['llm_wins'] > comparison_results['summary']['rule180_wins']:
        print("✅ LLMベースの改善が優位です")
        print("   - 複雑な文脈理解が必要なケースでLLMを優先使用")
        print("   - RULE_180をフォールバックとして維持")
    else:
        print("✅ RULE_180（パターンベース）が優位です")
        print("   - シンプルな問題はRULE_180で十分")
        print("   - LLMはコスト削減のため限定的に使用")

    print("\n✨ Phase 7.3テスト完了")


if __name__ == "__main__":
    main()
