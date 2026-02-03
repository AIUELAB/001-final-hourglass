#!/usr/bin/env python3
"""
上位独占検出ゲート

特定の人物がTop N内で過剰に多くのエピソードを占有している場合に検出。

ルール:
- Top20: 同一person_id 最大1件
- Top100: 同一person_id 最大2件
- Top1000: 同一person_id 最大3件

Usage:
    python scripts/validation/top_monopoly_gate.py --csv PATH [--top-n N] [--dry-run]

Exit codes:
    0: OK
    1: 違反あり
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
DEFAULT_CSV = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
REPORT_PATH = PROJECT_ROOT / "src/reports/top_monopoly_gate_result.json"

# 上位N件ごとの最大許容件数
MONOPOLY_LIMITS = {
    20: 1,    # Top20: 最大1件
    100: 2,   # Top100: 最大2件
    1000: 3,  # Top1000: 最大3件
}


@dataclass
class MonopolyViolation:
    """独占違反"""

    person_id: str
    person_name: str
    tier: str  # "Top20", "Top100", "Top1000"
    count: int
    limit: int
    excess: int
    episode_ids: list  # 全エピソードID（スコア降順）
    removal_candidates: list  # 削除候補（上限超過分のID）


def detect_monopoly_violations(csv_path: Path, top_n: int = 1000) -> dict:
    """
    上位独占違反を検出

    Args:
        csv_path: CSVファイルパス
        top_n: 検査対象の上位N件

    Returns:
        検出結果の辞書
    """
    # エピソードを読み込みしてスコア降順でソート
    episodes = []
    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            person_id = row.get("person_id", "")
            person_name = row.get("person_name", "")
            episode_id = row.get("episode_id", "")
            score_str = row.get("super_total_score", "")

            if not (person_id and episode_id and score_str):
                continue

            try:
                score = float(score_str)
            except (ValueError, TypeError):
                continue

            episodes.append({
                "person_id": person_id,
                "person_name": person_name,
                "episode_id": episode_id,
                "super_total_score": score,
            })

    # スコア降順でソート
    episodes.sort(key=lambda x: x["super_total_score"], reverse=True)

    # 上位N件に限定
    top_episodes = episodes[:top_n]

    # 各Tierで独占をチェック
    violations = []
    tiers_to_check = [(k, v) for k, v in MONOPOLY_LIMITS.items() if k <= top_n]

    for tier_n, limit in sorted(tiers_to_check):
        tier_episodes = top_episodes[:tier_n]
        tier_name = f"Top{tier_n}"

        # person_idごとにグループ化
        person_groups = defaultdict(list)
        for ep in tier_episodes:
            person_groups[ep["person_id"]].append(ep)

        # 上限超過チェック
        for person_id, person_eps in person_groups.items():
            if len(person_eps) > limit:
                # スコア降順でソート済み
                person_eps_sorted = sorted(
                    person_eps,
                    key=lambda x: x["super_total_score"],
                    reverse=True
                )
                person_name = person_eps_sorted[0]["person_name"]
                all_ids = [ep["episode_id"] for ep in person_eps_sorted]
                # 上限超過分が削除候補（スコア低い方から）
                removal_ids = all_ids[limit:]

                violations.append(
                    MonopolyViolation(
                        person_id=person_id,
                        person_name=person_name,
                        tier=tier_name,
                        count=len(person_eps),
                        limit=limit,
                        excess=len(person_eps) - limit,
                        episode_ids=all_ids,
                        removal_candidates=removal_ids,
                    )
                )

    # Tier優先度でソート（Top20 > Top100 > Top1000）
    tier_order = {"Top20": 0, "Top100": 1, "Top1000": 2}
    violations.sort(key=lambda x: (tier_order.get(x.tier, 99), -x.excess))

    return {
        "scan_date": datetime.now().isoformat(),
        "csv_path": str(csv_path),
        "top_n": top_n,
        "total_episodes_scanned": len(top_episodes),
        "total_violations": len(violations),
        "violations": [asdict(v) for v in violations],
    }


def get_violation_summary(result: dict) -> dict:
    """
    違反サマリーを取得

    Args:
        result: detect_monopoly_violationsの結果

    Returns:
        サマリー辞書
    """
    violations = result.get("violations", [])

    # Tierごとの集計
    tier_summary = defaultdict(lambda: {"violation_count": 0, "excess_total": 0})
    unique_persons = set()

    for v in violations:
        tier = v["tier"]
        tier_summary[tier]["violation_count"] += 1
        tier_summary[tier]["excess_total"] += v["excess"]
        unique_persons.add(v["person_id"])

    return {
        "total_violation_persons": len(unique_persons),
        "total_excess_episodes": sum(v["excess"] for v in violations),
        "by_tier": dict(tier_summary),
    }


def suggest_removals(result: dict) -> list:
    """
    削除候補を提案

    Args:
        result: detect_monopoly_violationsの結果

    Returns:
        削除候補リスト
    """
    removals = []
    seen_ids = set()

    for v in result.get("violations", []):
        for ep_id in v["removal_candidates"]:
            if ep_id not in seen_ids:
                removals.append({
                    "episode_id": ep_id,
                    "person_name": v["person_name"],
                    "tier": v["tier"],
                    "reason": f"{v['tier']}で{v['person_name']}が{v['count']}件占有（上限{v['limit']}件）",
                })
                seen_ids.add(ep_id)

    return removals


def main():
    parser = argparse.ArgumentParser(description="上位独占検出ゲート")
    parser.add_argument(
        "--csv",
        type=Path,
        default=DEFAULT_CSV,
        help=f"検査対象CSV（デフォルト: {DEFAULT_CSV}）",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=1000,
        help="検査対象の上位N件（デフォルト: 1000）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="違反があってもexit code 0で終了",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("上位独占検出ゲート")
    print("=" * 60)
    print(f"CSV: {args.csv}")
    print(f"検査範囲: Top{args.top_n}")
    print(f"ルール: Top20≤1件, Top100≤2件, Top1000≤3件")
    print("=" * 60)

    if not args.csv.exists():
        print(f"\n[ERROR] CSVファイルが見つかりません: {args.csv}")
        return 1

    result = detect_monopoly_violations(args.csv, args.top_n)
    summary = get_violation_summary(result)
    removals = suggest_removals(result)

    # レポート出力
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    report_data = {
        **result,
        "summary": summary,
        "removal_suggestions": removals,
    }
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)

    # 結果表示
    print(f"\n総違反人物数: {summary['total_violation_persons']}")
    print(f"総超過件数: {summary['total_excess_episodes']}")

    if summary["by_tier"]:
        print("\n--- Tier別集計 ---")
        for tier, stats in sorted(summary["by_tier"].items()):
            print(f"  {tier}: {stats['violation_count']}人物, 超過{stats['excess_total']}件")

    if result["violations"]:
        print("\n--- 検出された違反 (上位10件) ---")
        for v in result["violations"][:10]:
            print(f"\n  [{v['tier']}] {v['person_name']}")
            print(f"    件数: {v['count']}件 (上限{v['limit']}件, 超過{v['excess']}件)")
            print(f"    全EP: {v['episode_ids']}")
            print(f"    削除候補: {v['removal_candidates']}")

    if removals:
        print(f"\n--- 削除候補 (計{len(removals)}件) ---")
        for r in removals[:10]:
            print(f"  - {r['episode_id']}: {r['reason']}")
        if len(removals) > 10:
            print(f"  ... 他{len(removals) - 10}件")

    print(f"\nレポート: {REPORT_PATH}")

    # 終了判定
    if result["total_violations"] > 0:
        print(f"\n{'[DRY-RUN] ' if args.dry_run else ''}違反: {result['total_violations']}件検出")
        if not args.dry_run:
            return 1

    if result["total_violations"] == 0:
        print("\nOK: 上位独占なし")

    return 0


if __name__ == "__main__":
    sys.exit(main())
