#!/usr/bin/env python3
"""
Phase 10.1: Phase 10ターゲット分析

Phase 9完了後の全エピソードから、Phase 10で改善すべき
40-50点エピソードを抽出し、予算とコスト効率を分析する。
"""

import csv
import json
from typing import List, Dict


def load_phase9_evaluation() -> List[Dict]:
    """Phase 9評価結果を読み込み"""
    episodes = []
    with open("episodes_phase9_evaluation.csv", 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            episodes.append(row)
    return episodes


def extract_target_episodes(episodes: List[Dict]) -> List[Dict]:
    """
    Phase 10改善対象エピソードを抽出

    条件:
    - 40 <= social_impact_score < 50 (合格まであと0-10点)
    - passed = False (不合格)
    - total_score >= 65 (改善可能性が高い)
    """
    targets = []

    for ep in episodes:
        total_score = float(ep['total_score'])
        social_impact = float(ep['social_impact_score'])
        passed = ep['passed'] == 'True' or ep['passed'] is True

        if 40 <= social_impact < 50 and not passed and total_score >= 65:
            targets.append({
                **ep,
                'total_score': total_score,
                'social_impact_score': social_impact,
                'gap_to_pass': 50 - social_impact
            })

    # ギャップが小さい順（合格に近い順）にソート
    targets.sort(key=lambda x: x['gap_to_pass'])
    return targets


def estimate_costs(targets: List[Dict]) -> Dict:
    """コスト推定"""
    # Phase 9実績: 31エピソード = $0.65
    # 1エピソードあたり = $0.021
    per_episode_cost = 0.021

    total_episodes = len(targets)
    estimated_cost = total_episodes * per_episode_cost

    return {
        "total_episodes": total_episodes,
        "per_episode_cost": per_episode_cost,
        "estimated_cost": round(estimated_cost, 2),
        "budget_limit": 1.50,
        "budget_remaining": round(1.50 - estimated_cost, 2)
    }


def analyze_improvement_potential(targets: List[Dict]) -> Dict:
    """改善可能性分析"""
    total = len(targets)

    # ギャップ別分布
    gap_distribution = {
        "0-3点": 0,   # 非常に近い
        "3-6点": 0,   # 近い
        "6-10点": 0   # やや遠い
    }

    for ep in targets:
        gap = ep['gap_to_pass']
        if gap <= 3:
            gap_distribution["0-3点"] += 1
        elif gap <= 6:
            gap_distribution["3-6点"] += 1
        else:
            gap_distribution["6-10点"] += 1

    # 期待される成功率（Phase 9実績: 54.8%）
    expected_success_rate = 0.548
    expected_improvements = int(total * expected_success_rate)

    # 現在の合格数（Phase 9後）
    current_passed = 30

    # Phase 10完了後の予想合格数
    projected_passed = current_passed + expected_improvements
    projected_pass_rate = (projected_passed / 100) * 100

    return {
        "total_targets": total,
        "gap_distribution": gap_distribution,
        "expected_success_rate": expected_success_rate,
        "expected_improvements": expected_improvements,
        "current_pass_rate": 30.0,
        "projected_pass_rate": round(projected_pass_rate, 1),
        "goal_pass_rate": 40.0,
        "goal_achievable": projected_pass_rate >= 40.0
    }


def main():
    """メイン実行"""
    print("=" * 80)
    print("Phase 10.1: ターゲット分析")
    print("=" * 80)

    # Phase 9評価結果を読み込み
    print("\n📂 Phase 9評価結果を読み込み中...")
    episodes = load_phase9_evaluation()
    print(f"✅ {len(episodes)}件のエピソード読み込み完了")

    # ターゲット抽出
    print("\n🎯 Phase 10ターゲットを抽出中...")
    targets = extract_target_episodes(episodes)
    print(f"✅ {len(targets)}件のターゲットエピソード抽出完了")

    # コスト推定
    print("\n💰 コスト推定中...")
    cost_estimate = estimate_costs(targets)

    # 改善可能性分析
    print("\n📊 改善可能性を分析中...")
    potential = analyze_improvement_potential(targets)

    # 結果表示
    print("\n" + "=" * 80)
    print("📈 Phase 10ターゲット分析結果")
    print("=" * 80)

    print(f"\nターゲット概要:")
    print(f"  総対象エピソード数: {len(targets)}件")
    print(f"  条件: 40 <= 社会的影響 < 50 & 不合格 & 総合スコア >= 65")

    print(f"\nギャップ分布:")
    for range_name, count in potential['gap_distribution'].items():
        print(f"  合格まで{range_name}: {count}件")

    print(f"\nコスト推定:")
    print(f"  1エピソードあたり: ${cost_estimate['per_episode_cost']:.3f}")
    print(f"  総コスト見積: ${cost_estimate['estimated_cost']}")
    print(f"  予算上限: ${cost_estimate['budget_limit']}")
    print(f"  予算残余: ${cost_estimate['budget_remaining']}")

    budget_status = "✅ 予算内" if cost_estimate['estimated_cost'] <= cost_estimate['budget_limit'] else "❌ 予算超過"
    print(f"  予算状況: {budget_status}")

    print(f"\n改善予測:")
    print(f"  期待成功率: {potential['expected_success_rate']*100:.1f}%")
    print(f"  予想改善数: {potential['expected_improvements']}件")
    print(f"  現在の合格率: {potential['current_pass_rate']:.1f}%")
    print(f"  Phase 10完了後の予測合格率: {potential['projected_pass_rate']:.1f}%")
    print(f"  目標合格率: {potential['goal_pass_rate']:.1f}%")

    goal_status = "✅ 達成可能" if potential['goal_achievable'] else "⚠️ 要検討"
    print(f"  目標達成可能性: {goal_status}")

    # ターゲットエピソードの詳細表示（上位10件）
    print(f"\n" + "=" * 80)
    print(f"🎯 優先度TOP10エピソード（合格に最も近い）")
    print(f"=" * 80)

    print(f"\n{'順位':<4} {'ID':<8} {'人物名':<20} {'総合':<6} {'社会影響':<8} {'ギャップ':<8}")
    print("-" * 80)

    for i, ep in enumerate(targets[:10], 1):
        print(f"{i:<4} {ep['episode_id']:<8} {ep['person_name']:<20} "
              f"{ep['total_score']:<6.1f} {ep['social_impact_score']:<8.1f} {ep['gap_to_pass']:<8.1f}")

    # CSV保存
    print(f"\n💾 ターゲットエピソードを保存中...")
    with open("episodes_phase10_targets.csv", 'w', encoding='utf-8-sig', newline='') as f:
        fieldnames = ['episode_id', 'person_name', 'episode_age',
                     'total_score', 'social_impact_score', 'gap_to_pass']
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(targets)
    print(f"✅ 保存完了: episodes_phase10_targets.csv")

    # 分析結果JSON保存
    analysis_result = {
        "targets": cost_estimate,
        "potential": potential,
        "top_10_episodes": [
            {
                "episode_id": ep['episode_id'],
                "person_name": ep['person_name'],
                "total_score": ep['total_score'],
                "social_impact_score": ep['social_impact_score'],
                "gap_to_pass": ep['gap_to_pass']
            }
            for ep in targets[:10]
        ]
    }

    with open("episodes_phase10_analysis.json", 'w', encoding='utf-8') as f:
        json.dump(analysis_result, f, ensure_ascii=False, indent=2)
    print(f"✅ 分析結果保存: episodes_phase10_analysis.json")

    print(f"\n" + "=" * 80)
    print(f"✅ Phase 10.1 ターゲット分析完了")
    print(f"=" * 80)


if __name__ == "__main__":
    main()
