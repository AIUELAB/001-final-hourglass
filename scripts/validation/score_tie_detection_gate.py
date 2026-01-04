#!/usr/bin/env python3
"""
スコア同率検出ゲート

episode_fame_v6 の同率（タイ）を検出し、閾値を超える場合にCRITICAL/WARNINGを返す。

監視KPI:
1. 特定スコア（デフォルト: 100.00）の件数
2. 上位N件内の同率数（同一スコアの塊の数）
3. 最大同率サイズ（同一スコアの最大件数）

Usage:
    python scripts/validation/score_tie_detection_gate.py [--threshold N]

Exit codes:
    0: OK
    1: CRITICAL（閾値超過）
"""

import argparse
import csv
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
MASTER_CSV = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
REPORT_PATH = PROJECT_ROOT / "src/reports/score_tie_gate_result.json"

# デフォルト閾値
DEFAULT_THRESHOLDS = {
    "score_100_max": 0,  # 100.00同率は0件を目標
    "top200_max_tie_size": 5,  # 上位200件内の最大同率サイズ
    "total_max_tie_size": 50,  # 全体の最大同率サイズ
}


def scan_score_ties(decimal_places: int = 2) -> dict:
    """スコア同率をスキャン"""
    scores = []
    score_episodes = {}  # score -> [episode_id, ...]

    with open(MASTER_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            v6 = row.get("episode_fame_v6", "")
            if v6:
                score = round(float(v6), decimal_places)
                ep_id = row.get("episode_id", "")
                scores.append(score)
                if score not in score_episodes:
                    score_episodes[score] = []
                score_episodes[score].append(ep_id)

    # スコア分布
    score_counts = Counter(scores)

    # 100.00の件数
    score_100_count = score_counts.get(100.0, 0)

    # 上位200件の分析
    sorted_scores = sorted(scores, reverse=True)
    top200_scores = sorted_scores[:200]
    top200_counts = Counter(top200_scores)
    top200_max_tie = max(top200_counts.values()) if top200_counts else 0

    # 全体の最大同率サイズ
    total_max_tie = max(score_counts.values()) if score_counts else 0
    total_max_tie_score = max(score_counts, key=score_counts.get) if score_counts else None

    # 同率スコア一覧（サイズ順）
    ties = [
        {"score": s, "count": c, "episodes": score_episodes[s][:5]} for s, c in score_counts.most_common(20) if c > 1
    ]

    return {
        "scan_date": datetime.now().isoformat(),
        "total_episodes": len(scores),
        "unique_scores": len(set(scores)),
        "score_100_count": score_100_count,
        "top200_max_tie_size": top200_max_tie,
        "total_max_tie_size": total_max_tie,
        "total_max_tie_score": total_max_tie_score,
        "score_max": max(scores) if scores else 0,
        "score_min": min(scores) if scores else 0,
        "top_ties": ties,
    }


def evaluate_thresholds(result: dict, thresholds: dict) -> list:
    """閾値判定"""
    violations = []

    if result["score_100_count"] > thresholds["score_100_max"]:
        violations.append(
            {
                "type": "score_100",
                "severity": "CRITICAL",
                "value": result["score_100_count"],
                "threshold": thresholds["score_100_max"],
                "message": f"100.00同率: {result['score_100_count']}件 > 閾値{thresholds['score_100_max']}",
            }
        )

    if result["top200_max_tie_size"] > thresholds["top200_max_tie_size"]:
        violations.append(
            {
                "type": "top200_tie",
                "severity": "WARNING",
                "value": result["top200_max_tie_size"],
                "threshold": thresholds["top200_max_tie_size"],
                "message": f"上位200件の最大同率: {result['top200_max_tie_size']}件 > 閾値{thresholds['top200_max_tie_size']}",
            }
        )

    if result["total_max_tie_size"] > thresholds["total_max_tie_size"]:
        violations.append(
            {
                "type": "total_tie",
                "severity": "WARNING",
                "value": result["total_max_tie_size"],
                "threshold": thresholds["total_max_tie_size"],
                "message": f"全体の最大同率: {result['total_max_tie_size']}件 > 閾値{thresholds['total_max_tie_size']}",
            }
        )

    return violations


def main():
    parser = argparse.ArgumentParser(description="スコア同率検出ゲート")
    parser.add_argument(
        "--score-100-max", type=int, default=DEFAULT_THRESHOLDS["score_100_max"], help="100.00同率の最大許容件数"
    )
    parser.add_argument(
        "--top200-max-tie",
        type=int,
        default=DEFAULT_THRESHOLDS["top200_max_tie_size"],
        help="上位200件内の最大同率サイズ",
    )
    parser.add_argument(
        "--total-max-tie", type=int, default=DEFAULT_THRESHOLDS["total_max_tie_size"], help="全体の最大同率サイズ"
    )
    args = parser.parse_args()

    thresholds = {
        "score_100_max": args.score_100_max,
        "top200_max_tie_size": args.top200_max_tie,
        "total_max_tie_size": args.total_max_tie,
    }

    print("=" * 60)
    print("スコア同率検出ゲート")
    print("=" * 60)

    result = scan_score_ties()
    violations = evaluate_thresholds(result, thresholds)

    # レポート出力
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    report = {
        **result,
        "thresholds": thresholds,
        "violations": violations,
    }
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 結果表示
    print(f"\n総エピソード数: {result['total_episodes']}")
    print(f"ユニークスコア数: {result['unique_scores']}")
    print(f"スコア範囲: {result['score_min']:.2f} - {result['score_max']:.2f}")
    print(f"\n100.00同率: {result['score_100_count']}件")
    print(f"上位200件の最大同率: {result['top200_max_tie_size']}件")
    print(f"全体の最大同率: {result['total_max_tie_size']}件 (スコア: {result['total_max_tie_score']})")

    if result["top_ties"]:
        print("\n--- 同率Top5 ---")
        for tie in result["top_ties"][:5]:
            print(f"  {tie['score']:.2f}: {tie['count']}件")

    print(f"\n✅ レポート: {REPORT_PATH}")

    # 閾値判定
    if violations:
        critical_count = sum(1 for v in violations if v["severity"] == "CRITICAL")
        warning_count = sum(1 for v in violations if v["severity"] == "WARNING")

        print(f"\n⚠️ 違反: CRITICAL={critical_count}, WARNING={warning_count}")
        for v in violations:
            icon = "❌" if v["severity"] == "CRITICAL" else "⚠️"
            print(f"  {icon} {v['message']}")

        if critical_count > 0:
            return 1

    print("\n✅ OK: 全ての閾値をクリア")
    return 0


if __name__ == "__main__":
    sys.exit(main())
