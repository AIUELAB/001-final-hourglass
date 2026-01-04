#!/usr/bin/env python3
"""
マイルストーン整合性ゲート

同一人物の同一マイルストーン（デビュー、受賞等）が
複数年齢で発生したように書かれている不整合を検出し、
閾値を超える場合はCRITICALを返す品質ゲート。

Usage:
    python scripts/validation/milestone_consistency_gate.py [--threshold N]

Exit codes:
    0: OK (閾値以下)
    1: CRITICAL (閾値超過)
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
MASTER_CSV = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
REPORT_PATH = PROJECT_ROOT / "src/reports/milestone_gate_result.json"

# KNOWN_FACTS from comprehensive_fact_checker.py
KNOWN_FACTS = {
    "尾崎豊": {"events": {"デビュー": {"age": 18}}},
    "宇多田ヒカル": {"events": {"デビュー": {"age": 15}}},
    "葛飾北斎": {"events": {"富嶽三十六景": {"age_range": (71, 73)}}},
    "黒澤明": {"events": {"七人の侍": {"age": 44}}},
}

# マイルストーンキーワード
MILESTONE_KEYWORDS = [
    "デビューを果たし",
    "でデビュー",
    "受賞した",
    "を受賞",
    "就任した",
    "に就任",
    "創業した",
    "を創業",
    "初優勝",
    "金メダルを獲得",
]


def extract_milestone_claims(text: str) -> list[str]:
    """テキストからマイルストーン断定を抽出"""
    claims = []
    for kw in MILESTONE_KEYWORDS:
        if kw in text:
            claims.append(kw)
    return claims


def check_known_fact_violation(person_name: str, age: float, text: str) -> dict | None:
    """KNOWN_FACTSとの矛盾をチェック"""
    if person_name not in KNOWN_FACTS:
        return None

    facts = KNOWN_FACTS[person_name].get("events", {})
    for event_name, event_data in facts.items():
        # イベント名がテキストに含まれているか
        if event_name not in text and "デビュー" not in text:
            continue

        # 年齢チェック
        correct_age = event_data.get("age")
        age_range = event_data.get("age_range")

        if correct_age and abs(age - correct_age) > 2:
            return {
                "person_name": person_name,
                "event": event_name,
                "claimed_age": age,
                "correct_age": correct_age,
                "severity": "CRITICAL",
            }
        elif age_range and (age < age_range[0] - 2 or age > age_range[1] + 2):
            return {
                "person_name": person_name,
                "event": event_name,
                "claimed_age": age,
                "correct_age_range": age_range,
                "severity": "WARNING",
            }

    return None


def scan_milestone_consistency() -> dict:
    """マイルストーン整合性をスキャン"""
    # person_id -> milestone_keyword -> [(age, episode_id)]
    person_milestones = defaultdict(lambda: defaultdict(list))
    known_fact_violations = []

    with open(MASTER_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            person_id = row.get("person_id", "")
            person_name = row.get("person_name", "")
            episode_id = row.get("episode_id", "")
            age = float(row.get("age") or 0)
            text = row.get("episode_text", "")

            # KNOWN_FACTS違反チェック
            violation = check_known_fact_violation(person_name, age, text)
            if violation:
                violation["episode_id"] = episode_id
                known_fact_violations.append(violation)

            # マイルストーン重複チェック
            claims = extract_milestone_claims(text)
            for claim in claims:
                person_milestones[person_id][claim].append(
                    {
                        "age": age,
                        "episode_id": episode_id,
                        "person_name": person_name,
                    }
                )

    # 重複検出（同一マイルストーンが5歳以上離れた年齢で出現）
    duplicates = []
    for person_id, milestones in person_milestones.items():
        for claim, occurrences in milestones.items():
            ages = [o["age"] for o in occurrences]
            if len(set(ages)) > 1:
                age_spread = max(ages) - min(ages)
                if age_spread >= 5:  # 5歳以上の差は問題
                    duplicates.append(
                        {
                            "person_id": person_id,
                            "person_name": occurrences[0]["person_name"],
                            "milestone": claim,
                            "ages": sorted(set(ages)),
                            "age_spread": age_spread,
                            "episodes": [o["episode_id"] for o in occurrences],
                            "severity": "CRITICAL" if age_spread >= 10 else "WARNING",
                        }
                    )

    return {
        "scan_date": datetime.now().isoformat(),
        "known_fact_violations": known_fact_violations,
        "milestone_duplicates": duplicates,
        "summary": {
            "known_fact_violations": len(known_fact_violations),
            "critical_duplicates": sum(1 for d in duplicates if d["severity"] == "CRITICAL"),
            "warning_duplicates": sum(1 for d in duplicates if d["severity"] == "WARNING"),
        },
    }


def main():
    parser = argparse.ArgumentParser(description="マイルストーン整合性ゲート")
    parser.add_argument("--threshold", type=int, default=0, help="許容する重大問題数")
    args = parser.parse_args()

    print("=" * 60)
    print("マイルストーン整合性ゲート")
    print("=" * 60)

    result = scan_milestone_consistency()

    # レポート出力
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # 結果表示
    summary = result["summary"]
    print(f"\nKNOWN_FACTS違反: {summary['known_fact_violations']}件")
    print(f"CRITICAL重複: {summary['critical_duplicates']}件")
    print(f"WARNING重複: {summary['warning_duplicates']}件")

    # サンプル表示
    if result["known_fact_violations"]:
        print("\n--- KNOWN_FACTS違反例 ---")
        for v in result["known_fact_violations"][:3]:
            print(
                f"  {v['person_name']}: {v['event']} claimed at {v['claimed_age']}歳 (correct: {v.get('correct_age', v.get('correct_age_range'))})"
            )

    if result["milestone_duplicates"]:
        print("\n--- 重複例 ---")
        for d in result["milestone_duplicates"][:3]:
            print(f"  {d['person_name']}: {d['milestone']} at ages {d['ages']}")

    print(f"\n✅ レポート: {REPORT_PATH}")

    # 閾値判定
    critical_count = summary["known_fact_violations"] + summary["critical_duplicates"]
    if critical_count > args.threshold:
        print(f"\n❌ CRITICAL: {critical_count}件 > 閾値{args.threshold}")
        return 1
    else:
        print(f"\n✅ OK: {critical_count}件 <= 閾値{args.threshold}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
