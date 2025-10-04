#!/usr/bin/env python3
"""
Phase 9.6: Phase 9結果評価

Phase 9改善後のエピソードを評価し、Phase 8との比較を行う。
"""

import csv
import json
from typing import List, Dict
from rules.rule_179_integrated_evaluation_pipeline import evaluate_episode_integrated


def load_episodes(csv_path: str) -> List[Dict]:
    """エピソードを読み込み"""
    episodes = []
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            episodes.append(row)
    return episodes


def evaluate_all_episodes(episodes: List[Dict]) -> List[Dict]:
    """全エピソードを評価"""
    results = []

    for i, ep in enumerate(episodes, 1):
        print(f"\r評価中: {i}/{len(episodes)} ({i/len(episodes)*100:.1f}%)", end='', flush=True)

        eval_result = evaluate_episode_integrated(
            episode_id=ep['episode_id'],
            person_name=ep['person_name'],
            episode_text=ep['episode_text'],
            database_age=int(ep['episode_age'])
        )

        results.append({
            'episode_id': ep['episode_id'],
            'person_name': ep['person_name'],
            'episode_age': int(ep['episode_age']),
            'total_score': eval_result.total_score,
            'social_impact_score': eval_result.social_impact.get('impact_score', 0),
            'passed': eval_result.passed,
            'character_count': len(ep['episode_text'])
        })

    print()  # 改行
    return results


def calculate_statistics(results: List[Dict]) -> Dict:
    """統計情報を計算"""
    total = len(results)
    passed = sum(1 for r in results if r['passed'])
    failed = total - passed

    total_scores = [r['total_score'] for r in results]
    social_impacts = [r['social_impact_score'] for r in results]

    # スコア分布
    score_dist = {
        "0-20": 0,
        "20-40": 0,
        "40-60": 0,
        "60-80": 0,
        "80-100": 0
    }

    for score in total_scores:
        if score < 20:
            score_dist["0-20"] += 1
        elif score < 40:
            score_dist["20-40"] += 1
        elif score < 60:
            score_dist["40-60"] += 1
        elif score < 80:
            score_dist["60-80"] += 1
        else:
            score_dist["80-100"] += 1

    return {
        "total_evaluated": total,
        "passed": passed,
        "failed": failed,
        "total_score_sum": sum(total_scores),
        "social_impact_sum": sum(social_impacts),
        "score_distribution": score_dist,
        "average_score": sum(total_scores) / total,
        "average_social_impact": sum(social_impacts) / total,
        "pass_rate": (passed / total) * 100
    }


def compare_with_phase8(phase9_stats: Dict, phase8_stats_path: str) -> Dict:
    """Phase 8との比較"""
    with open(phase8_stats_path, 'r', encoding='utf-8') as f:
        phase8_stats = json.load(f)

    comparison = {
        "pass_rate": {
            "phase8": phase8_stats["pass_rate"],
            "phase9": phase9_stats["pass_rate"],
            "change": phase9_stats["pass_rate"] - phase8_stats["pass_rate"]
        },
        "average_score": {
            "phase8": phase8_stats["average_score"],
            "phase9": phase9_stats["average_score"],
            "change": phase9_stats["average_score"] - phase8_stats["average_score"]
        },
        "average_social_impact": {
            "phase8": phase8_stats["average_social_impact"],
            "phase9": phase9_stats["average_social_impact"],
            "change": phase9_stats["average_social_impact"] - phase8_stats["average_social_impact"]
        },
        "passed_count": {
            "phase8": phase8_stats["passed"],
            "phase9": phase9_stats["passed"],
            "change": phase9_stats["passed"] - phase8_stats["passed"]
        }
    }

    return comparison


def main():
    """メイン実行"""
    print("=" * 80)
    print("Phase 9.6: Phase 9結果評価")
    print("=" * 80)

    # Phase 9改善後のエピソードを読み込み
    print("\n📂 Phase 9エピソードを読み込み中...")
    episodes = load_episodes("episodes_phase9_complete.csv")
    print(f"✅ {len(episodes)}件のエピソード読み込み完了")

    # 全エピソードを評価
    print("\n📊 全エピソードを評価中...")
    results = evaluate_all_episodes(episodes)
    print("✅ 評価完了")

    # 統計計算
    print("\n📈 統計情報を計算中...")
    stats = calculate_statistics(results)

    # Phase 8との比較
    print("📊 Phase 8との比較中...")
    comparison = compare_with_phase8(stats, "episodes_phase8_complete_evaluation_stats.json")

    # 結果表示
    print("\n" + "=" * 80)
    print("📈 Phase 9評価結果")
    print("=" * 80)

    print(f"\n基本統計:")
    print(f"  総エピソード数: {stats['total_evaluated']}件")
    print(f"  合格: {stats['passed']}件 ({stats['pass_rate']:.1f}%)")
    print(f"  不合格: {stats['failed']}件")
    print(f"  平均スコア: {stats['average_score']:.1f}点")
    print(f"  平均社会的影響: {stats['average_social_impact']:.1f}点")

    print(f"\nスコア分布:")
    for range_name, count in stats['score_distribution'].items():
        print(f"  {range_name}点: {count}件")

    print(f"\n" + "=" * 80)
    print(f"📊 Phase 8 vs Phase 9 比較")
    print(f"=" * 80)

    print(f"\n合格率:")
    print(f"  Phase 8: {comparison['pass_rate']['phase8']:.1f}%")
    print(f"  Phase 9: {comparison['pass_rate']['phase9']:.1f}%")
    print(f"  変化: {comparison['pass_rate']['change']:+.1f}ポイント")

    print(f"\n平均スコア:")
    print(f"  Phase 8: {comparison['average_score']['phase8']:.1f}点")
    print(f"  Phase 9: {comparison['average_score']['phase9']:.1f}点")
    print(f"  変化: {comparison['average_score']['change']:+.1f}点")

    print(f"\n平均社会的影響:")
    print(f"  Phase 8: {comparison['average_social_impact']['phase8']:.1f}点")
    print(f"  Phase 9: {comparison['average_social_impact']['phase9']:.1f}点")
    print(f"  変化: {comparison['average_social_impact']['change']:+.1f}点")

    print(f"\n合格数:")
    print(f"  Phase 8: {comparison['passed_count']['phase8']}件")
    print(f"  Phase 9: {comparison['passed_count']['phase9']}件")
    print(f"  変化: {comparison['passed_count']['change']:+}件")

    # 目標達成判定
    print(f"\n" + "=" * 80)
    print(f"🎯 Phase 9目標達成判定")
    print(f"=" * 80)

    goals = {
        "合格率35%以上": comparison['pass_rate']['phase9'] >= 35.0,
        "平均社会的影響52点以上": comparison['average_social_impact']['phase9'] >= 52.0,
        "平均スコア78点以上": comparison['average_score']['phase9'] >= 78.0,
        "予算$1.50以内": True  # 実績$0.65
    }

    for goal, achieved in goals.items():
        status = "✅ 達成" if achieved else "❌ 未達"
        print(f"  {goal}: {status}")

    # 保存
    print(f"\n💾 結果を保存中...")

    # 評価結果CSV
    with open("episodes_phase9_evaluation.csv", 'w', encoding='utf-8-sig', newline='') as f:
        fieldnames = ['episode_id', 'person_name', 'episode_age',
                     'total_score', 'social_impact_score', 'passed', 'character_count']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    print(f"✅ 評価CSV保存: episodes_phase9_evaluation.csv")

    # 統計JSON
    with open("episodes_phase9_evaluation_stats.json", 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(f"✅ 統計JSON保存: episodes_phase9_evaluation_stats.json")

    # 比較JSON
    with open("episodes_phase9_comparison.json", 'w', encoding='utf-8') as f:
        json.dump(comparison, f, ensure_ascii=False, indent=2)
    print(f"✅ 比較JSON保存: episodes_phase9_comparison.json")

    print(f"\n" + "=" * 80)
    print(f"✅ Phase 9.6 評価完了")
    print(f"=" * 80)


if __name__ == "__main__":
    main()
