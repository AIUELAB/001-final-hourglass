#!/usr/bin/env python3
"""
Phase 9.1: ターゲット分析

Phase 8評価結果から社会的影響改善の対象エピソードを抽出し、
詳細分析を行う。
"""

import csv
import json
from typing import List, Dict
from collections import defaultdict


def load_phase8_evaluation(csv_path: str) -> List[Dict]:
    """Phase 8評価結果を読み込み"""
    episodes = []
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            episodes.append(row)
    return episodes


def extract_target_episodes(episodes: List[Dict]) -> List[Dict]:
    """
    改善対象エピソードを抽出

    条件:
    - 60 <= total_score < 80 (改善可能レンジ)
    - social_impact_score < 50 (社会的影響不足)
    - passed = False (不合格)
    """
    targets = []

    for ep in episodes:
        total_score = float(ep['total_score'])
        social_impact = float(ep['social_impact_score'])
        passed = ep['passed'] == 'True' or ep['passed'] is True

        if 60 <= total_score < 80 and social_impact < 50 and not passed:
            targets.append({
                **ep,
                'total_score': total_score,
                'social_impact_score': social_impact,
                'improvement_potential': 50 - social_impact  # 合格ラインまでの差
            })

    # 社会的影響昇順でソート（低い方が優先度高）
    targets.sort(key=lambda x: x['social_impact_score'])

    return targets


def analyze_targets(targets: List[Dict], all_episodes: List[Dict]) -> Dict:
    """ターゲットエピソードの詳細分析"""

    analysis = {
        "summary": {
            "total_episodes": len(all_episodes),
            "target_episodes": len(targets),
            "target_percentage": (len(targets) / len(all_episodes)) * 100,
        },
        "score_distribution": {
            "social_impact_30_40": 0,
            "social_impact_40_50": 0,
        },
        "total_score_distribution": {
            "60_65": 0,
            "65_70": 0,
            "70_75": 0,
            "75_80": 0,
        },
        "category_breakdown": defaultdict(int),
        "improvement_potential": {
            "total": 0.0,
            "average": 0.0,
            "min": 0.0,
            "max": 0.0,
        },
        "cost_estimate": {
            "total_episodes": len(targets),
            "cost_per_episode": 0.021,
            "total_cost": len(targets) * 0.021,
            "budget_limit": 1.50,
            "within_budget": len(targets) * 0.021 <= 1.50
        },
        "processing_time_estimate": {
            "seconds_per_episode": 10,
            "total_seconds": len(targets) * 10,
            "total_minutes": (len(targets) * 10) / 60
        }
    }

    if not targets:
        return analysis

    # スコア分布
    for target in targets:
        social_impact = target['social_impact_score']
        total_score = target['total_score']

        # 社会的影響分布
        if 30 <= social_impact < 40:
            analysis["score_distribution"]["social_impact_30_40"] += 1
        elif 40 <= social_impact < 50:
            analysis["score_distribution"]["social_impact_40_50"] += 1

        # 総合スコア分布
        if 60 <= total_score < 65:
            analysis["total_score_distribution"]["60_65"] += 1
        elif 65 <= total_score < 70:
            analysis["total_score_distribution"]["65_70"] += 1
        elif 70 <= total_score < 75:
            analysis["total_score_distribution"]["70_75"] += 1
        elif 75 <= total_score < 80:
            analysis["total_score_distribution"]["75_80"] += 1

    # 改善ポテンシャル
    potentials = [t['improvement_potential'] for t in targets]
    analysis["improvement_potential"]["total"] = sum(potentials)
    analysis["improvement_potential"]["average"] = sum(potentials) / len(potentials)
    analysis["improvement_potential"]["min"] = min(potentials)
    analysis["improvement_potential"]["max"] = max(potentials)

    return analysis


def save_targets_csv(targets: List[Dict], output_path: str):
    """ターゲットエピソードをCSV保存"""
    if not targets:
        print("⚠️ ターゲットエピソードが0件のため保存スキップ")
        return

    with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
        fieldnames = [
            'episode_id', 'person_name', 'episode_age',
            'total_score', 'social_impact_score', 'improvement_potential',
            'passed', 'character_count'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(targets)


def main():
    """メイン実行"""

    print("=" * 80)
    print("Phase 9.1: ターゲット分析")
    print("=" * 80)

    # Phase 8評価結果を読み込み
    print("\n📂 Phase 8評価結果を読み込み中...")
    evaluation_path = "episodes_phase8_complete_evaluation.csv"
    all_episodes = load_phase8_evaluation(evaluation_path)
    print(f"✅ {len(all_episodes)}件のエピソード読み込み完了")

    # ターゲット抽出
    print("\n🔍 改善対象エピソードを抽出中...")
    print("   条件: 60 <= スコア < 80 AND 社会的影響 < 50 AND 不合格")
    targets = extract_target_episodes(all_episodes)
    print(f"✅ {len(targets)}件の改善対象を抽出")

    # 分析実行
    print("\n📊 詳細分析中...")
    analysis = analyze_targets(targets, all_episodes)

    # 分析結果表示
    print("\n" + "=" * 80)
    print("📈 Phase 9.1 分析結果")
    print("=" * 80)

    print(f"\n基本統計:")
    print(f"  総エピソード数: {analysis['summary']['total_episodes']}件")
    print(f"  改善対象: {analysis['summary']['target_episodes']}件 "
          f"({analysis['summary']['target_percentage']:.1f}%)")

    print(f"\n社会的影響スコア分布:")
    print(f"  30-40点: {analysis['score_distribution']['social_impact_30_40']}件")
    print(f"  40-50点: {analysis['score_distribution']['social_impact_40_50']}件")

    print(f"\n総合スコア分布:")
    print(f"  60-65点: {analysis['total_score_distribution']['60_65']}件")
    print(f"  65-70点: {analysis['total_score_distribution']['65_70']}件")
    print(f"  70-75点: {analysis['total_score_distribution']['70_75']}件")
    print(f"  75-80点: {analysis['total_score_distribution']['75_80']}件")

    print(f"\n改善ポテンシャル:")
    print(f"  合計: {analysis['improvement_potential']['total']:.1f}点")
    print(f"  平均: {analysis['improvement_potential']['average']:.1f}点/件")
    print(f"  最小: {analysis['improvement_potential']['min']:.1f}点")
    print(f"  最大: {analysis['improvement_potential']['max']:.1f}点")

    print(f"\nコスト見積もり:")
    print(f"  対象件数: {analysis['cost_estimate']['total_episodes']}件")
    print(f"  単価: ${analysis['cost_estimate']['cost_per_episode']}/件")
    print(f"  総コスト: ${analysis['cost_estimate']['total_cost']:.2f}")
    print(f"  予算上限: ${analysis['cost_estimate']['budget_limit']:.2f}")
    budget_status = "✅ 予算内" if analysis['cost_estimate']['within_budget'] else "❌ 予算超過"
    print(f"  判定: {budget_status}")

    print(f"\n処理時間見積もり:")
    print(f"  単価: {analysis['processing_time_estimate']['seconds_per_episode']}秒/件")
    print(f"  総時間: {analysis['processing_time_estimate']['total_seconds']:.0f}秒 "
          f"({analysis['processing_time_estimate']['total_minutes']:.1f}分)")

    # ターゲット上位10件表示
    if targets:
        print(f"\nTop 10 改善優先エピソード（社会的影響が低い順）:")
        for i, target in enumerate(targets[:10], 1):
            print(f"  {i}. {target['episode_id']} ({target['person_name']})")
            print(f"     スコア: {target['total_score']:.1f}点, "
                  f"社会的影響: {target['social_impact_score']:.1f}点, "
                  f"改善余地: +{target['improvement_potential']:.1f}点")

    # CSV保存
    targets_csv_path = "episodes_phase9_targets.csv"
    print(f"\n💾 ターゲットエピソードを保存中...")
    save_targets_csv(targets, targets_csv_path)
    print(f"✅ 保存完了: {targets_csv_path}")

    # JSON保存
    analysis_json_path = "episodes_phase9_analysis.json"
    with open(analysis_json_path, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)
    print(f"✅ 分析結果保存: {analysis_json_path}")

    print("\n" + "=" * 80)
    print("✅ Phase 9.1 分析完了")
    print("=" * 80)

    # 予算チェック
    if not analysis['cost_estimate']['within_budget']:
        print("\n⚠️ 警告: 予算超過が予想されます")
        print(f"   対策: 社会的影響40点未満に絞るか、予算を調整してください")

        # 40点未満のみに絞った場合の再計算
        targets_40 = [t for t in targets if t['social_impact_score'] < 40]
        cost_40 = len(targets_40) * 0.021
        print(f"\n   社会的影響40点未満のみ: {len(targets_40)}件")
        print(f"   コスト: ${cost_40:.2f}")
        if cost_40 <= 1.50:
            print(f"   判定: ✅ 予算内")


if __name__ == "__main__":
    main()
