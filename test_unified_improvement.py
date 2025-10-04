#!/usr/bin/env python3
"""
Phase 7.4: 統合改善システムテスト

RULE_183（統合改善インターフェース）の実戦テスト
"""

import os
import json
import logging
from typing import List, Dict, Any

from rules.unified_improvement_interface import (
    get_unified_interface,
    improve_episode_auto,
    CostManager
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def setup_test_cases() -> List[Dict[str, Any]]:
    """多様なテストケースを準備"""
    return [
        {
            "episode_id": "EP_UNIFIED_001",
            "person_name": "大谷翔平",
            "episode_text": "あなたと同じ28歳のとき、大谷翔平は素晴らしい業績を残し、多くの人々に影響を与えた。",
            "database_age": 28,
            "person_context": {
                "person_name": "大谷翔平",
                "birth_year": 1994,
                "category": "プロ野球選手"
            },
            "expected_strategy": "llm_primary",
            "description": "低スコア・抽象表現 → LLM改善期待"
        },
        {
            "episode_id": "EP_UNIFIED_002",
            "person_name": "イチロー",
            "episode_text": "あなたと同じ30歳のとき、イチローは優れた選手として活躍した。",
            "database_age": 30,
            "person_context": {
                "person_name": "イチロー",
                "birth_year": 1973,
                "category": "プロ野球選手"
            },
            "expected_strategy": "pattern_only",
            "description": "中スコア・簡単な問題 → RULE_180で十分"
        },
        {
            "episode_id": "EP_UNIFIED_003",
            "person_name": "羽生結弦",
            "episode_text": "あなたと同じ25歳のとき、羽生結弦は最高の演技で金メダルを獲得した。",
            "database_age": 25,
            "person_context": {
                "person_name": "羽生結弦",
                "birth_year": 1994,
                "category": "フィギュアスケーター"
            },
            "expected_strategy": "llm_primary",
            "description": "抽象表現・具体性不足 → LLM改善"
        }
    ]


def test_auto_strategy():
    """Auto戦略テスト"""

    print("\n" + "="*80)
    print("🎯 Phase 7.4: 統合改善システムテスト（Auto戦略）")
    print("="*80 + "\n")

    # OpenAI APIキー確認
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  OPENAI_API_KEY未設定 - Mockプロバイダーでテスト")
        provider = "mock"
    else:
        print("✅ OPENAI_API_KEY設定済み - GPT-4でテスト")
        provider = "openai"

    test_cases = setup_test_cases()
    results = []

    interface = get_unified_interface(reset=True)

    for idx, test_case in enumerate(test_cases, 1):
        print(f"\n{'─'*80}")
        print(f"📝 テストケース {idx}/{len(test_cases)}: {test_case['description']}")
        print(f"{'─'*80}")

        print(f"\n元のエピソード:")
        print(f"  {test_case['episode_text']}\n")

        try:
            # Auto戦略で改善
            improved_text, summary = improve_episode_auto(
                test_case["episode_id"],
                test_case["person_name"],
                test_case["episode_text"],
                test_case["database_age"],
                test_case["person_context"],
                llm_provider=provider
            )

            # 結果表示
            print(f"改善結果:")
            print(f"  戦略: {summary.get('method', 'unknown')}")
            print(f"  改善: {'✅' if summary.get('improved') else '❌'}")

            if summary.get("improved"):
                print(f"\n改善後のエピソード:")
                print(f"  {improved_text}\n")

                if "original_score" in summary:
                    print(f"スコア変化:")
                    print(f"  元: {summary['original_score']:.1f}点")
                    if "final_score" in summary:
                        print(f"  後: {summary['final_score']:.1f}点")
                        print(f"  改善: {summary['final_score'] - summary['original_score']:+.1f}点")

            # 結果記録
            results.append({
                "test_case": test_case["description"],
                "episode_id": test_case["episode_id"],
                "original_text": test_case["episode_text"],
                "improved_text": improved_text,
                "summary": summary,
                "expected_strategy": test_case["expected_strategy"]
            })

        except Exception as e:
            print(f"\n❌ エラー発生: {e}")
            import traceback
            traceback.print_exc()

            results.append({
                "test_case": test_case["description"],
                "error": str(e)
            })

    # 統計サマリー
    print("\n" + "="*80)
    print("📊 テスト結果サマリー")
    print("="*80 + "\n")

    stats = interface.get_statistics()

    print("改善統計:")
    print(f"  総改善数: {stats['total_improvements']}件")
    print(f"  RULE_180使用: {stats['rule180_count']}件")
    print(f"  RULE_182使用: {stats['rule182_count']}件")
    print(f"  ハイブリッド: {stats['hybrid_count']}件")
    print(f"  スキップ: {stats['skipped_count']}件")
    print(f"  フォールバック: {stats['fallback_count']}件")

    print(f"\nコスト情報:")
    print(f"  使用額: ${stats['cost_usage']:.3f}")
    print(f"  上限: ${stats['cost_limit']:.2f}")
    print(f"  残予算: ${stats['remaining_budget']:.2f}")

    # 結果保存
    output_file = "phase7_4_unified_test_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "results": results,
            "statistics": stats
        }, f, ensure_ascii=False, indent=2)

    print(f"\n💾 詳細結果を {output_file} に保存しました")

    return results, stats


def test_all_strategies():
    """全戦略モードのテスト"""

    print("\n" + "="*80)
    print("🎯 全戦略モードテスト")
    print("="*80 + "\n")

    # 1つのテストケースで全戦略を試す
    test_case = {
        "episode_id": "EP_STRATEGY_TEST",
        "person_name": "大谷翔平",
        "episode_text": "あなたと同じ28歳のとき、大谷翔平は素晴らしい業績を残し、多くの人々に影響を与えた。",
        "database_age": 28,
        "person_context": {
            "person_name": "大谷翔平",
            "birth_year": 1994,
            "category": "プロ野球選手"
        }
    }

    strategies = ["auto", "force_pattern", "force_llm", "hybrid"]
    provider = "openai" if os.getenv("OPENAI_API_KEY") else "mock"

    results = {}

    for strategy in strategies:
        print(f"\n{'─'*80}")
        print(f"📋 戦略: {strategy}")
        print(f"{'─'*80}")

        interface = get_unified_interface(reset=True)

        try:
            improved_text, summary = interface.improve_episode_unified(
                test_case["episode_id"],
                test_case["person_name"],
                test_case["episode_text"],
                test_case["database_age"],
                test_case["person_context"],
                strategy_mode=strategy,
                llm_provider=provider
            )

            print(f"  実行方法: {summary.get('method', 'unknown')}")
            print(f"  改善: {'✅' if summary.get('improved') else '❌'}")

            if summary.get("improved"):
                print(f"  改善後: {improved_text[:100]}...")

            results[strategy] = {
                "improved_text": improved_text,
                "summary": summary
            }

        except Exception as e:
            print(f"  ❌ エラー: {e}")
            results[strategy] = {"error": str(e)}

    # 比較表示
    print("\n" + "="*80)
    print("📊 戦略比較")
    print("="*80 + "\n")

    for strategy, result in results.items():
        if "error" not in result:
            summary = result["summary"]
            print(f"{strategy:15s}: {summary.get('method', 'unknown'):20s} ", end="")
            if "final_score" in summary and "original_score" in summary:
                improvement = summary["final_score"] - summary["original_score"]
                print(f"({improvement:+.1f}点)")
            else:
                print()

    return results


if __name__ == "__main__":
    print("🚀 Phase 7.4: 統合改善システム 総合テスト開始\n")

    # テスト1: Auto戦略
    results_auto, stats_auto = test_auto_strategy()

    # テスト2: 全戦略比較
    results_all = test_all_strategies()

    print("\n" + "="*80)
    print("✅ Phase 7.4: 統合テスト完了")
    print("="*80)
