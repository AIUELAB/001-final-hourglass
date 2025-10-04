#!/usr/bin/env python3
"""
Phase 8.4: 改善結果の評価と分析

改善前後のエピソードをRULE_179で再評価し、
改善効果を定量的に分析する。
"""

import csv
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime

# Phase 7システムのインポート
sys.path.insert(0, str(Path(__file__).parent / "rules"))

from rules.rule_179_integrated_evaluation_pipeline import evaluate_episode_integrated


def load_episodes(csv_path: str) -> List[Dict]:
    """エピソードCSVを読み込み"""
    episodes = []
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            episodes.append(row)
    return episodes


def evaluate_all_episodes(
    episodes: List[Dict],
    output_path: str
) -> Tuple[List[Dict], Dict]:
    """
    全エピソードをRULE_179で評価

    Returns:
        (評価結果リスト, 統計サマリー)
    """

    results = []
    stats = {
        "total_evaluated": 0,
        "passed": 0,
        "failed": 0,
        "total_score_sum": 0.0,
        "social_impact_sum": 0.0,
        "score_distribution": {
            "0-20": 0,
            "20-40": 0,
            "40-60": 0,
            "60-80": 0,
            "80-100": 0
        }
    }

    print(f"\n🔍 RULE_179評価開始: {len(episodes)}エピソード")
    print("=" * 80)

    for idx, episode in enumerate(episodes, 1):
        episode_id = episode['episode_id']
        person_name = episode['person_name']
        episode_text = episode['episode_text']
        database_age = int(episode['episode_age'])

        print(f"\n[{idx}/{len(episodes)}] {episode_id}: {person_name}")

        # RULE_179評価
        try:
            eval_result = evaluate_episode_integrated(
                episode_id=episode_id,
                person_name=person_name,
                episode_text=episode_text,
                database_age=database_age,
                birth_year=None  # CSVから取得可能なら設定
            )

            # social_impactはDict型なのでimpact_scoreを抽出
            social_impact_score = eval_result.social_impact.get("impact_score", 0.0)

            # 結果記録
            result = {
                "episode_id": episode_id,
                "person_name": person_name,
                "episode_age": database_age,
                "total_score": eval_result.total_score,
                "social_impact_score": social_impact_score,
                "passed": eval_result.passed,
                "character_count": len(episode_text)
            }

            results.append(result)

            # 統計更新
            stats["total_evaluated"] += 1
            if eval_result.passed:
                stats["passed"] += 1
            else:
                stats["failed"] += 1

            stats["total_score_sum"] += eval_result.total_score
            stats["social_impact_sum"] += social_impact_score

            # スコア分布
            score = eval_result.total_score
            if score < 20:
                stats["score_distribution"]["0-20"] += 1
            elif score < 40:
                stats["score_distribution"]["20-40"] += 1
            elif score < 60:
                stats["score_distribution"]["40-60"] += 1
            elif score < 80:
                stats["score_distribution"]["60-80"] += 1
            else:
                stats["score_distribution"]["80-100"] += 1

            # 結果表示
            status = "✅ PASS" if eval_result.passed else "❌ FAIL"
            print(f"  {status}: {eval_result.total_score:.1f}点")
            print(f"  - 社会的影響: {social_impact_score:.1f}")

        except Exception as e:
            print(f"  ❌ 評価エラー: {e}")
            continue

    # 平均スコア計算
    if stats["total_evaluated"] > 0:
        stats["average_score"] = stats["total_score_sum"] / stats["total_evaluated"]
        stats["average_social_impact"] = stats["social_impact_sum"] / stats["total_evaluated"]
        stats["pass_rate"] = (stats["passed"] / stats["total_evaluated"]) * 100

    # CSV保存
    with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
        fieldnames = [
            'episode_id', 'person_name', 'episode_age',
            'total_score', 'social_impact_score', 'passed', 'character_count'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"\n✅ 評価完了: {output_path}")

    return results, stats


def compare_before_after(
    before_scores: List[Dict],
    after_scores: List[Dict]
) -> Dict:
    """改善前後の比較分析"""

    # episode_idでマッピング
    before_map = {ep['episode_id']: ep for ep in before_scores}
    after_map = {ep['episode_id']: ep for ep in after_scores}

    comparison = {
        "total_episodes": 0,
        "improved": 0,
        "degraded": 0,
        "unchanged": 0,
        "score_improvements": [],
        "pass_rate_change": {
            "before": 0.0,
            "after": 0.0,
            "delta": 0.0
        },
        "average_score_change": {
            "before": 0.0,
            "after": 0.0,
            "delta": 0.0
        }
    }

    before_total_score = 0.0
    after_total_score = 0.0
    before_passed = 0
    after_passed = 0

    for episode_id in after_map.keys():
        if episode_id not in before_map:
            continue

        before = before_map[episode_id]
        after = after_map[episode_id]

        # 改善前はimpact_keyword_score、改善後はtotal_scoreを使用
        before_score = float(before.get('impact_keyword_score', before.get('total_score', 0)))
        after_score = float(after['total_score'])

        delta = after_score - before_score

        comparison["total_episodes"] += 1
        before_total_score += before_score
        after_total_score += after_score

        # 改善前はoverall_passed、改善後はpassedを使用
        before_pass_value = before.get('overall_passed', before.get('passed', 'False'))
        if before_pass_value == 'True' or before_pass_value is True:
            before_passed += 1
        if after['passed'] == 'True' or after['passed'] is True:
            after_passed += 1

        if delta > 1.0:  # 1点以上の改善
            comparison["improved"] += 1
            comparison["score_improvements"].append({
                "episode_id": episode_id,
                "person_name": after['person_name'],
                "before_score": before_score,
                "after_score": after_score,
                "improvement": delta
            })
        elif delta < -1.0:  # 1点以上の悪化
            comparison["degraded"] += 1
        else:
            comparison["unchanged"] += 1

    # 平均スコア
    if comparison["total_episodes"] > 0:
        comparison["average_score_change"]["before"] = before_total_score / comparison["total_episodes"]
        comparison["average_score_change"]["after"] = after_total_score / comparison["total_episodes"]
        comparison["average_score_change"]["delta"] = (
            comparison["average_score_change"]["after"] -
            comparison["average_score_change"]["before"]
        )

        comparison["pass_rate_change"]["before"] = (before_passed / comparison["total_episodes"]) * 100
        comparison["pass_rate_change"]["after"] = (after_passed / comparison["total_episodes"]) * 100
        comparison["pass_rate_change"]["delta"] = (
            comparison["pass_rate_change"]["after"] -
            comparison["pass_rate_change"]["before"]
        )

    # 改善効果でソート
    comparison["score_improvements"].sort(key=lambda x: x['improvement'], reverse=True)

    return comparison


def main():
    """メイン実行"""

    print("=" * 80)
    print("Phase 8.4: 改善結果の評価と分析")
    print("=" * 80)

    # 改善前のスコアを読み込み
    print("\n📂 改善前のスコアを読み込み中...")
    before_scores_path = "episodes_validated_100_20251001_optimized_evaluation.csv"
    before_scores = load_episodes(before_scores_path)
    print(f"✅ {len(before_scores)}件のスコア読み込み完了")

    # 改善後のエピソードを評価
    print("\n📂 改善後のエピソードを読み込み中...")
    after_episodes_path = "episodes_phase8_complete.csv"
    after_episodes = load_episodes(after_episodes_path)
    print(f"✅ {len(after_episodes)}件のエピソード読み込み完了")

    # 改善後を再評価
    after_scores, after_stats = evaluate_all_episodes(
        after_episodes,
        "episodes_phase8_complete_evaluation.csv"
    )

    # 統計サマリー保存
    stats_path = "episodes_phase8_complete_evaluation_stats.json"
    with open(stats_path, 'w', encoding='utf-8') as f:
        json.dump(after_stats, f, ensure_ascii=False, indent=2)
    print(f"✅ 統計保存: {stats_path}")

    # Before/After比較
    print("\n" + "=" * 80)
    print("📊 改善前後の比較分析")
    print("=" * 80)

    comparison = compare_before_after(before_scores, after_scores)

    # 比較結果保存
    comparison_path = "episodes_phase8_comparison.json"
    with open(comparison_path, 'w', encoding='utf-8') as f:
        json.dump(comparison, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 比較結果保存: {comparison_path}")

    # サマリー表示
    print("\n" + "=" * 80)
    print("📈 Phase 8.4 評価サマリー")
    print("=" * 80)

    print(f"\n改善後の評価結果:")
    print(f"  総エピソード数: {after_stats['total_evaluated']}件")
    print(f"  合格: {after_stats['passed']}件 ({after_stats.get('pass_rate', 0):.1f}%)")
    print(f"  不合格: {after_stats['failed']}件")
    print(f"  平均スコア: {after_stats.get('average_score', 0):.1f}点")
    print(f"  平均社会的影響: {after_stats.get('average_social_impact', 0):.1f}点")

    print(f"\nスコア分布:")
    for range_name, count in after_stats['score_distribution'].items():
        print(f"  {range_name}点: {count}件")

    print(f"\n改善前後の比較:")
    print(f"  比較対象: {comparison['total_episodes']}件")
    print(f"  改善: {comparison['improved']}件")
    print(f"  悪化: {comparison['degraded']}件")
    print(f"  変化なし: {comparison['unchanged']}件")

    print(f"\n合格率の変化:")
    print(f"  改善前: {comparison['pass_rate_change']['before']:.1f}%")
    print(f"  改善後: {comparison['pass_rate_change']['after']:.1f}%")
    print(f"  変化: {comparison['pass_rate_change']['delta']:+.1f}ポイント")

    print(f"\n平均スコアの変化:")
    print(f"  改善前: {comparison['average_score_change']['before']:.1f}点")
    print(f"  改善後: {comparison['average_score_change']['after']:.1f}点")
    print(f"  変化: {comparison['average_score_change']['delta']:+.1f}点")

    # Top 10改善事例
    if comparison['score_improvements']:
        print(f"\nTop 10 改善事例:")
        for i, imp in enumerate(comparison['score_improvements'][:10], 1):
            print(f"  {i}. {imp['episode_id']} ({imp['person_name']})")
            print(f"     {imp['before_score']:.1f} → {imp['after_score']:.1f} (+{imp['improvement']:.1f}点)")

    print("\n" + "=" * 80)
    print("✅ Phase 8.4 評価完了")
    print("=" * 80)


if __name__ == "__main__":
    main()
