#!/usr/bin/env python3
"""
Phase 7.5: RULE_180 vs RULE_182 大規模比較評価

20件のテストケースで4つの改善方法を比較:
- RULE_180のみ
- RULE_182のみ
- Auto戦略
- Hybrid戦略
"""

import os
import json
import time
import logging
from typing import List, Dict, Any, Tuple
from datetime import datetime

from rules.unified_improvement_interface import get_unified_interface, CostManager
from rules.rule_179_integrated_evaluation_pipeline import evaluate_episode_integrated

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def setup_20_test_cases() -> List[Dict[str, Any]]:
    """20件の多様なテストケースを準備"""

    test_cases = [
        # 低スコア（50-60点）: 8件 - LLM改善の効果測定
        {
            "id": "TC01_LOW",
            "person_name": "大谷翔平",
            "episode_text": "あなたと同じ28歳のとき、大谷翔平は素晴らしい業績を残し、多くの人々に影響を与えた。",
            "age": 28,
            "birth_year": 1994,
            "category": "プロ野球選手",
            "expected_score_range": (50, 60),
            "problem_type": "抽象表現・センセーショナル"
        },
        {
            "id": "TC02_LOW",
            "person_name": "羽生結弦",
            "episode_text": "あなたと同じ25歳のとき、羽生結弦は最高の演技で金メダルを獲得した。",
            "age": 25,
            "birth_year": 1994,
            "category": "フィギュアスケーター",
            "expected_score_range": (55, 65),
            "problem_type": "抽象表現"
        },
        {
            "id": "TC03_LOW",
            "person_name": "イチロー",
            "episode_text": "あなたと同じ30歳のとき、イチローは2004年にメジャーリーグで大活躍した。",
            "age": 30,
            "birth_year": 1973,
            "category": "プロ野球選手",
            "expected_score_range": (50, 60),
            "problem_type": "時系列矛盾"
        },
        {
            "id": "TC04_LOW",
            "person_name": "本田圭佑",
            "episode_text": "あなたと同じ27歳のとき、本田圭佑は優れた成績を収め、チームに貢献した。",
            "age": 27,
            "birth_year": 1986,
            "category": "サッカー選手",
            "expected_score_range": (50, 60),
            "problem_type": "抽象表現"
        },
        {
            "id": "TC05_LOW",
            "person_name": "錦織圭",
            "episode_text": "あなたと同じ28歳のとき、錦織圭は素晴らしいプレーで観客を魅了した。",
            "age": 28,
            "birth_year": 1989,
            "category": "テニス選手",
            "expected_score_range": (50, 60),
            "problem_type": "抽象表現・センセーショナル"
        },
        {
            "id": "TC06_LOW",
            "person_name": "浅田真央",
            "episode_text": "あなたと同じ23歳のとき、浅田真央は最悪の状態から見事に復活した。",
            "age": 23,
            "birth_year": 1990,
            "category": "フィギュアスケーター",
            "expected_score_range": (40, 50),
            "problem_type": "センセーショナル表現"
        },
        {
            "id": "TC07_LOW",
            "person_name": "松井秀喜",
            "episode_text": "あなたと同じ29歳のとき、松井秀喜は圧倒的な実力で多くの記録を塗り替えた。",
            "age": 29,
            "birth_year": 1974,
            "category": "プロ野球選手",
            "expected_score_range": (50, 60),
            "problem_type": "抽象表現・センセーショナル"
        },
        {
            "id": "TC08_LOW",
            "person_name": "内村航平",
            "episode_text": "あなたと同じ27歳のとき、内村航平は最高の技術で金メダルを獲得した。",
            "age": 27,
            "birth_year": 1989,
            "category": "体操選手",
            "expected_score_range": (55, 65),
            "problem_type": "抽象表現"
        },

        # 中スコア（60-70点）: 8件 - RULE_180との比較
        {
            "id": "TC09_MID",
            "person_name": "北島康介",
            "episode_text": "あなたと同じ25歳のとき、北島康介は2008年北京オリンピックで金メダルを獲得した。",
            "age": 25,
            "birth_year": 1982,
            "category": "競泳選手",
            "expected_score_range": (65, 75),
            "problem_type": "具体性あり"
        },
        {
            "id": "TC10_MID",
            "person_name": "吉田沙保里",
            "episode_text": "あなたと同じ30歳のとき、吉田沙保里はオリンピックで優れた成績を収めた。",
            "age": 30,
            "birth_year": 1982,
            "category": "レスリング選手",
            "expected_score_range": (60, 70),
            "problem_type": "やや抽象的"
        },
        {
            "id": "TC11_MID",
            "person_name": "高橋尚子",
            "episode_text": "あなたと同じ28歳のとき、高橋尚子はマラソンで日本記録を更新した。",
            "age": 28,
            "birth_year": 1972,
            "category": "マラソン選手",
            "expected_score_range": (65, 75),
            "problem_type": "具体性あり"
        },
        {
            "id": "TC12_MID",
            "person_name": "野茂英雄",
            "episode_text": "あなたと同じ31歳のとき、野茂英雄はメジャーリーグで活躍した。",
            "age": 31,
            "birth_year": 1968,
            "category": "プロ野球選手",
            "expected_score_range": (60, 70),
            "problem_type": "やや抽象的"
        },
        {
            "id": "TC13_MID",
            "person_name": "長嶋茂雄",
            "episode_text": "あなたと同じ32歳のとき、長嶋茂雄は優れた打撃で活躍した。",
            "age": 32,
            "birth_year": 1936,
            "category": "プロ野球選手",
            "expected_score_range": (60, 70),
            "problem_type": "抽象表現"
        },
        {
            "id": "TC14_MID",
            "person_name": "室伏広治",
            "episode_text": "あなたと同じ30歳のとき、室伏広治はハンマー投げで金メダルを獲得した。",
            "age": 30,
            "birth_year": 1974,
            "category": "陸上選手",
            "expected_score_range": (65, 75),
            "problem_type": "具体性あり"
        },
        {
            "id": "TC15_MID",
            "person_name": "柔道選手A",
            "episode_text": "あなたと同じ26歳のとき、柔道選手Aはオリンピックで良い成績を残した。",
            "age": 26,
            "birth_year": 1985,
            "category": "柔道選手",
            "expected_score_range": (55, 65),
            "problem_type": "抽象表現"
        },
        {
            "id": "TC16_MID",
            "person_name": "卓球選手B",
            "episode_text": "あなたと同じ24歳のとき、卓球選手Bは世界大会で活躍した。",
            "age": 24,
            "birth_year": 1995,
            "category": "卓球選手",
            "expected_score_range": (60, 70),
            "problem_type": "やや抽象的"
        },

        # 高スコア（70点以上）: 4件 - 改善不要の確認
        {
            "id": "TC17_HIGH",
            "person_name": "大谷翔平",
            "episode_text": "あなたと同じ28歳のとき、大谷翔平は2022年シーズンにMLBロサンゼルス・エンゼルスで投手として9勝、打者として46本塁打を記録した。",
            "age": 28,
            "birth_year": 1994,
            "category": "プロ野球選手",
            "expected_score_range": (70, 80),
            "problem_type": "高品質"
        },
        {
            "id": "TC18_HIGH",
            "person_name": "イチロー",
            "episode_text": "あなたと同じ30歳のとき、イチローは2004年MLBシーズンで262安打のメジャーリーグ新記録を樹立した。",
            "age": 30,
            "birth_year": 1973,
            "category": "プロ野球選手",
            "expected_score_range": (75, 85),
            "problem_type": "高品質"
        },
        {
            "id": "TC19_HIGH",
            "person_name": "羽生結弦",
            "episode_text": "あなたと同じ23歳のとき、羽生結弦は2018年平昌オリンピックで66年ぶりとなるフィギュアスケート男子シングル連覇を達成した。",
            "age": 23,
            "birth_year": 1994,
            "category": "フィギュアスケーター",
            "expected_score_range": (75, 85),
            "problem_type": "高品質"
        },
        {
            "id": "TC20_HIGH",
            "person_name": "北島康介",
            "episode_text": "あなたと同じ25歳のとき、北島康介は2008年北京オリンピックで100m平泳ぎと200m平泳ぎの2種目で金メダルを獲得し、2大会連続2冠を達成した。",
            "age": 25,
            "birth_year": 1982,
            "category": "競泳選手",
            "expected_score_range": (75, 85),
            "problem_type": "高品質"
        }
    ]

    return test_cases


def evaluate_with_method(
    test_cases: List[Dict],
    method_name: str,
    strategy_mode: str,
    llm_provider: str = "openai"
) -> List[Dict[str, Any]]:
    """指定した方法で全テストケースを評価"""

    logger.info(f"\n{'='*80}")
    logger.info(f"🎯 {method_name}による評価開始")
    logger.info(f"{'='*80}\n")

    interface = get_unified_interface(reset=True)
    results = []

    for idx, test_case in enumerate(test_cases, 1):
        logger.info(f"📝 {idx}/{len(test_cases)}: {test_case['id']} - {test_case['person_name']}")

        try:
            start_time = time.time()

            # 元の評価
            original_eval = evaluate_episode_integrated(
                episode_id=test_case['id'],
                person_name=test_case['person_name'],
                episode_text=test_case['episode_text'],
                database_age=test_case['age'],
                birth_year=test_case['birth_year']
            )
            original_score = original_eval.total_score

            # 改善実行
            improved_text, summary = interface.improve_episode_unified(
                episode_id=test_case['id'],
                person_name=test_case['person_name'],
                episode_text=test_case['episode_text'],
                database_age=test_case['age'],
                person_context={
                    "person_name": test_case['person_name'],
                    "birth_year": test_case['birth_year'],
                    "category": test_case['category']
                },
                strategy_mode=strategy_mode,
                llm_provider=llm_provider
            )

            # 改善後の評価
            if summary.get("improved"):
                improved_eval = evaluate_episode_integrated(
                    episode_id=test_case['id'],
                    person_name=test_case['person_name'],
                    episode_text=improved_text,
                    database_age=test_case['age'],
                    birth_year=test_case['birth_year']
                )
                final_score = improved_eval.total_score
            else:
                final_score = original_score

            processing_time = time.time() - start_time

            # 結果記録
            result = {
                "test_case_id": test_case['id'],
                "person_name": test_case['person_name'],
                "problem_type": test_case['problem_type'],
                "original_text": test_case['episode_text'],
                "original_score": original_score,
                "improved_text": improved_text,
                "final_score": final_score,
                "score_improvement": final_score - original_score,
                "improved": summary.get("improved", False),
                "method_used": summary.get("method", "unknown"),
                "processing_time": processing_time,
                "char_count": len(improved_text)
            }

            results.append(result)

            logger.info(f"   元: {original_score:.1f}点 → 後: {final_score:.1f}点 ({final_score - original_score:+.1f}点)")

        except Exception as e:
            logger.error(f"   ❌ エラー: {e}")
            results.append({
                "test_case_id": test_case['id'],
                "error": str(e)
            })

    # 統計取得
    stats = interface.get_statistics()

    return results, stats


def analyze_results(all_results: Dict[str, Tuple[List, Dict]]) -> Dict[str, Any]:
    """結果を統計分析"""

    analysis = {}

    for method_name, (results, stats) in all_results.items():
        # エラー除外
        valid_results = [r for r in results if "error" not in r]

        if not valid_results:
            continue

        # スコア統計
        score_improvements = [r["score_improvement"] for r in valid_results]
        original_scores = [r["original_score"] for r in valid_results]
        final_scores = [r["final_score"] for r in valid_results]

        analysis[method_name] = {
            "total_cases": len(valid_results),
            "improved_cases": sum(1 for r in valid_results if r["improved"]),
            "average_original_score": sum(original_scores) / len(original_scores),
            "average_final_score": sum(final_scores) / len(final_scores),
            "average_improvement": sum(score_improvements) / len(score_improvements),
            "max_improvement": max(score_improvements),
            "min_improvement": min(score_improvements),
            "pass_rate_original": sum(1 for s in original_scores if s >= 60) / len(original_scores),
            "pass_rate_final": sum(1 for s in final_scores if s >= 60) / len(final_scores),
            "total_processing_time": sum(r.get("processing_time", 0) for r in valid_results),
            "average_processing_time": sum(r.get("processing_time", 0) for r in valid_results) / len(valid_results),
            "cost": stats.get("cost_usage", 0.0),
            "cost_per_episode": stats.get("cost_usage", 0.0) / len(valid_results) if valid_results else 0
        }

    return analysis


def main():
    """メイン実行"""

    print("🚀 Phase 7.5: RULE_180 vs RULE_182 大規模比較評価\n")

    # OpenAI APIキー確認
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  OPENAI_API_KEY未設定 - Mockプロバイダーでテスト")
        provider = "mock"
    else:
        print("✅ OPENAI_API_KEY設定済み - GPT-4でテスト\n")
        provider = "openai"

    # テストケース準備
    test_cases = setup_20_test_cases()
    print(f"📋 テストケース: {len(test_cases)}件準備完了\n")

    # 4つの方法で評価
    all_results = {}

    # 1. RULE_180のみ
    print("\n" + "="*80)
    print("1/4: RULE_180による評価")
    print("="*80)
    results_180, stats_180 = evaluate_with_method(
        test_cases, "RULE_180", "force_pattern", provider
    )
    all_results["RULE_180"] = (results_180, stats_180)

    # 2. RULE_182のみ
    print("\n" + "="*80)
    print("2/4: RULE_182による評価")
    print("="*80)
    results_182, stats_182 = evaluate_with_method(
        test_cases, "RULE_182", "force_llm", provider
    )
    all_results["RULE_182"] = (results_182, stats_182)

    # 3. Auto戦略
    print("\n" + "="*80)
    print("3/4: Auto戦略による評価")
    print("="*80)
    results_auto, stats_auto = evaluate_with_method(
        test_cases, "Auto", "auto", provider
    )
    all_results["Auto"] = (results_auto, stats_auto)

    # 4. Hybrid戦略
    print("\n" + "="*80)
    print("4/4: Hybrid戦略による評価")
    print("="*80)
    results_hybrid, stats_hybrid = evaluate_with_method(
        test_cases, "Hybrid", "hybrid", provider
    )
    all_results["Hybrid"] = (results_hybrid, stats_hybrid)

    # 統計分析
    analysis = analyze_results(all_results)

    # 結果表示
    print("\n" + "="*80)
    print("📊 比較評価結果サマリー")
    print("="*80 + "\n")

    for method_name, metrics in analysis.items():
        print(f"{method_name}:")
        print(f"  平均スコア向上: {metrics['average_improvement']:+.1f}点")
        print(f"  最大改善: {metrics['max_improvement']:+.1f}点")
        print(f"  合格率: {metrics['pass_rate_original']:.1%} → {metrics['pass_rate_final']:.1%}")
        print(f"  平均処理時間: {metrics['average_processing_time']:.2f}秒")
        print(f"  コスト: ${metrics['cost']:.3f}\n")

    # 結果保存
    output_data = {
        "evaluation_date": datetime.now().isoformat(),
        "test_cases_count": len(test_cases),
        "llm_provider": provider,
        "detailed_results": {
            method: results for method, (results, _) in all_results.items()
        },
        "statistics": {
            method: stats for method, (_, stats) in all_results.items()
        },
        "analysis": analysis
    }

    output_file = "phase7_5_comparison_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"💾 詳細結果を {output_file} に保存しました\n")

    print("✅ Phase 7.5: 大規模比較評価完了")

    return analysis


if __name__ == "__main__":
    analysis = main()
