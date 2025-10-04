#!/usr/bin/env python3
"""
Phase 8.1: 既存100エピソードの分析と改善対象選定

既存の100エピソードを分析し、Phase 8での改善優先度を決定する。
"""

import csv
import json
from typing import Dict, List, Tuple
from collections import defaultdict
import sys

def load_episodes_with_evaluation(
    episodes_path: str,
    evaluation_path: str
) -> List[Dict]:
    """エピソードと評価データを統合"""

    # エピソードデータ読み込み
    episodes = {}
    with open(episodes_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            episodes[row['episode_id']] = row

    # 評価データ読み込み
    evaluations = {}
    with open(evaluation_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            evaluations[row['episode_id']] = row

    # 統合
    combined = []
    for episode_id, episode in episodes.items():
        if episode_id in evaluations:
            combined.append({
                **episode,
                'evaluation': evaluations[episode_id]
            })

    return combined

def analyze_score_distribution(episodes: List[Dict]) -> Dict:
    """スコア分布を分析"""

    distribution = {
        "0-10": [],
        "10-20": [],
        "20-30": [],
        "30-40": [],
        "40-50": [],
        "50-60": [],
        "60-70": [],
        "70+": []
    }

    for ep in episodes:
        score = float(ep['evaluation']['impact_keyword_score'])

        if score < 10:
            distribution["0-10"].append(ep)
        elif score < 20:
            distribution["10-20"].append(ep)
        elif score < 30:
            distribution["20-30"].append(ep)
        elif score < 40:
            distribution["30-40"].append(ep)
        elif score < 50:
            distribution["40-50"].append(ep)
        elif score < 60:
            distribution["50-60"].append(ep)
        elif score < 70:
            distribution["60-70"].append(ep)
        else:
            distribution["70+"].append(ep)

    return distribution

def classify_improvement_needs(episodes: List[Dict]) -> Dict[str, List[Dict]]:
    """改善必要度で分類"""

    categories = {
        "critical": [],      # 0-30点: LLM必須
        "high": [],          # 30-60点: LLM推奨
        "medium": [],        # 60-70点: パターンで十分
        "skip": []           # 70点以上: 改善不要
    }

    for ep in episodes:
        score = float(ep['evaluation']['impact_keyword_score'])
        passed = ep['evaluation']['overall_passed'] == 'True'

        if score < 30:
            categories["critical"].append(ep)
        elif score < 60:
            categories["high"].append(ep)
        elif score < 70:
            categories["medium"].append(ep)
        else:
            categories["skip"].append(ep)

    return categories

def estimate_costs(categories: Dict[str, List[Dict]]) -> Dict:
    """コスト見積もり"""

    # コスト単価
    LLM_COST = 0.021  # OpenAI GPT-4
    PATTERN_COST = 0.0

    estimates = {
        "critical": {
            "count": len(categories["critical"]),
            "strategy": "auto (LLM優先)",
            "estimated_llm_usage": len(categories["critical"]),
            "cost": len(categories["critical"]) * LLM_COST
        },
        "high": {
            "count": len(categories["high"]),
            "strategy": "auto (パターン優先)",
            "estimated_llm_usage": int(len(categories["high"]) * 0.3),  # 30%がLLM
            "cost": int(len(categories["high"]) * 0.3) * LLM_COST
        },
        "medium": {
            "count": len(categories["medium"]),
            "strategy": "force_pattern",
            "estimated_llm_usage": 0,
            "cost": 0.0
        },
        "skip": {
            "count": len(categories["skip"]),
            "strategy": "skip",
            "estimated_llm_usage": 0,
            "cost": 0.0
        }
    }

    total_cost = sum(cat["cost"] for cat in estimates.values())
    total_llm = sum(cat["estimated_llm_usage"] for cat in estimates.values())

    estimates["total"] = {
        "episodes": len(categories["critical"]) + len(categories["high"]) + len(categories["medium"]),
        "llm_calls": total_llm,
        "estimated_cost": total_cost
    }

    return estimates

def analyze_problem_patterns(episodes: List[Dict]) -> Dict:
    """問題パターンを分析"""

    patterns = {
        "distribution_violation": [],  # 配分違反
        "impact_insufficient": [],     # インパクト不足
        "both": [],                    # 両方
        "passed": []                   # 合格
    }

    for ep in episodes:
        eval_data = ep['evaluation']
        passed = eval_data['overall_passed'] == 'True'
        dist_passed = eval_data['distribution_passed'] == 'True'
        impact_passed = eval_data['impact_passed'] == 'True'

        if passed:
            patterns["passed"].append(ep)
        elif not dist_passed and not impact_passed:
            patterns["both"].append(ep)
        elif not dist_passed:
            patterns["distribution_violation"].append(ep)
        elif not impact_passed:
            patterns["impact_insufficient"].append(ep)

    return patterns

def main():
    episodes_path = "episodes_validated_100_20251001.csv"
    evaluation_path = "episodes_validated_100_20251001_optimized_evaluation.csv"

    print("Phase 8.1: 既存100エピソード分析")
    print("=" * 60)

    # データ読み込み
    print("\n📂 データ読み込み中...")
    episodes = load_episodes_with_evaluation(episodes_path, evaluation_path)
    print(f"✅ {len(episodes)}エピソード読み込み完了")

    # スコア分布分析
    print("\n📊 スコア分布分析:")
    distribution = analyze_score_distribution(episodes)
    for range_name, eps in distribution.items():
        print(f"  {range_name}点: {len(eps)}件")

    # 改善必要度分類
    print("\n🎯 改善必要度分類:")
    categories = classify_improvement_needs(episodes)
    for category, eps in categories.items():
        print(f"  {category}: {len(eps)}件")

    # コスト見積もり
    print("\n💰 コスト見積もり:")
    estimates = estimate_costs(categories)
    for cat_name, est in estimates.items():
        if cat_name == "total":
            print(f"\n  【合計】")
            print(f"    対象エピソード: {est['episodes']}件")
            print(f"    LLM呼び出し: {est['llm_calls']}回")
            print(f"    推定コスト: ${est['estimated_cost']:.2f}")
        else:
            print(f"  {cat_name}: {est['count']}件")
            print(f"    戦略: {est['strategy']}")
            print(f"    LLM使用: {est['estimated_llm_usage']}回")
            print(f"    コスト: ${est['cost']:.2f}")

    # 問題パターン分析
    print("\n🔍 問題パターン分析:")
    patterns = analyze_problem_patterns(episodes)
    for pattern_name, eps in patterns.items():
        print(f"  {pattern_name}: {len(eps)}件")

    # 現在の合格率
    passed_count = len(patterns["passed"])
    pass_rate = (passed_count / len(episodes)) * 100
    print(f"\n📈 現在の合格率: {pass_rate:.1f}% ({passed_count}/{len(episodes)}件)")

    # 改善目標
    target_pass_rate = 30.0
    target_passed = int(len(episodes) * target_pass_rate / 100)
    needed_improvement = target_passed - passed_count

    print(f"\n🎯 Phase 8目標:")
    print(f"  目標合格率: {target_pass_rate}%")
    print(f"  目標合格数: {target_passed}件")
    print(f"  必要改善数: {needed_improvement}件")

    # 詳細データ保存
    analysis_result = {
        "summary": {
            "total_episodes": len(episodes),
            "current_pass_rate": pass_rate,
            "current_passed": passed_count,
            "target_pass_rate": target_pass_rate,
            "target_passed": target_passed,
            "needed_improvement": needed_improvement
        },
        "score_distribution": {
            range_name: len(eps) for range_name, eps in distribution.items()
        },
        "improvement_categories": {
            cat: len(eps) for cat, eps in categories.items()
        },
        "cost_estimates": estimates,
        "problem_patterns": {
            pattern: len(eps) for pattern, eps in patterns.items()
        },
        "priority_episodes": {
            "critical": [
                {
                    "episode_id": ep['episode_id'],
                    "person_name": ep['person_name'],
                    "score": float(ep['evaluation']['impact_keyword_score']),
                    "text": ep['episode_text']
                }
                for ep in categories["critical"][:10]  # 最優先10件
            ],
            "high": [
                {
                    "episode_id": ep['episode_id'],
                    "person_name": ep['person_name'],
                    "score": float(ep['evaluation']['impact_keyword_score']),
                    "text": ep['episode_text']
                }
                for ep in categories["high"][:10]  # 次優先10件
            ]
        }
    }

    output_path = "episodes_analysis_phase8.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(analysis_result, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 分析結果を {output_path} に保存しました")

    # 推奨アクション
    print("\n💡 推奨アクション:")
    print(f"  1. Critical（0-30点）{len(categories['critical'])}件 → Auto戦略（LLM優先）")
    print(f"  2. High（30-60点）{len(categories['high'])}件 → Auto戦略（パターン優先）")
    print(f"  3. Medium（60-70点）{len(categories['medium'])}件 → Force_Pattern戦略")
    print(f"  4. 推定総コスト: ${estimates['total']['estimated_cost']:.2f}")

    if estimates['total']['estimated_cost'] > 2.50:
        print("\n⚠️  推定コストが予算($2.50)を超過しています")
        print("   → Criticalのみに絞る、またはAnthropicプロバイダーを検討")
    else:
        print(f"\n✅ 予算内（${estimates['total']['estimated_cost']:.2f} < $2.50）")

if __name__ == "__main__":
    main()
