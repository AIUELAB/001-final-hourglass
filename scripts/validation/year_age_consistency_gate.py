#!/usr/bin/env python3
"""年齢×年号 整合性ゲート

本文中の年号（YYYY年）と、年齢から計算した想定年との整合性を検証する。
時系列矛盾（マリー・キュリー問題等）の再発を防止する。

使用方法:
    python scripts/validation/year_age_consistency_gate.py [--threshold N]

終了コード:
    0: PASS（CRITICALが0件）
    1: FAIL（CRITICALがN件以上）

関連スクリプト:
    - detect_year_age_inconsistency.py: 詳細な検出スクリプト（JSON出力）
    - age_event_consistency_gate.py: Wikidataベースのイベント年検証
"""

import argparse
import csv
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from birth_year_database import get_birth_year

MASTER_CSV = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"

# 年号抽出パターン
YEAR_PATTERN = re.compile(r"(\d{4})年")

# 許容差分
YEAR_TOLERANCE_WARNING = 3  # 3年以上で WARNING
YEAR_TOLERANCE_CRITICAL = 5  # 5年以上で CRITICAL

# デフォルト閾値（CRITICAL件数がこれ以上でFAIL）
DEFAULT_CRITICAL_THRESHOLD = 10


def extract_years_from_text(text: str) -> list[int]:
    """本文から年号（YYYY年）を抽出"""
    matches = YEAR_PATTERN.findall(text)
    return [int(y) for y in matches if 1000 <= int(y) <= 2100]


def check_episode(row: dict) -> dict | None:
    """単一エピソードの年齢×年号整合性をチェック"""
    person_name = row.get("person_name", "")
    age_str = row.get("age", "")
    episode_text = row.get("episode_text", "")
    person_type = row.get("person_type", "REAL")

    # 架空キャラクターはスキップ
    if person_type == "FICTIONAL":
        return None

    # 年齢パース
    try:
        age = int(float(age_str))
    except (ValueError, TypeError):
        return None

    # 本文から年号を抽出
    years_in_text = extract_years_from_text(episode_text)
    if not years_in_text:
        return None

    # 生年データを取得
    birth_year = get_birth_year(person_name)
    if birth_year is None:
        return None

    # 想定年を計算
    expected_year = birth_year + age

    # 年号との差分をチェック（最大乖離を検出）
    max_diff = 0
    worst_year = None
    for year in years_in_text:
        diff = abs(year - expected_year)
        if diff > max_diff:
            max_diff = diff
            worst_year = year

    if max_diff >= YEAR_TOLERANCE_WARNING:
        severity = "CRITICAL" if max_diff >= YEAR_TOLERANCE_CRITICAL else "WARNING"
        return {
            "episode_id": row.get("episode_id", ""),
            "person_name": person_name,
            "age": age,
            "birth_year": birth_year,
            "expected_year": expected_year,
            "year_in_text": worst_year,
            "year_diff": max_diff,
            "severity": severity,
        }

    return None


def run_gate(critical_threshold: int = DEFAULT_CRITICAL_THRESHOLD) -> tuple[bool, dict]:
    """
    ゲートを実行

    Returns:
        (pass_result, stats): ゲート合格したか, 統計情報
    """
    stats = {
        "total_episodes": 0,
        "checked_episodes": 0,
        "critical_count": 0,
        "warning_count": 0,
        "issues": [],
    }

    with open(MASTER_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            stats["total_episodes"] += 1
            result = check_episode(row)
            if result:
                stats["checked_episodes"] += 1
                if result["severity"] == "CRITICAL":
                    stats["critical_count"] += 1
                else:
                    stats["warning_count"] += 1
                stats["issues"].append(result)

    passed = stats["critical_count"] < critical_threshold
    return passed, stats


def main():
    parser = argparse.ArgumentParser(description="年齢×年号 整合性ゲート")
    parser.add_argument(
        "--threshold",
        type=int,
        default=DEFAULT_CRITICAL_THRESHOLD,
        help=f"CRITICAL件数の閾値（デフォルト: {DEFAULT_CRITICAL_THRESHOLD}）",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="詳細出力")
    args = parser.parse_args()

    print("=" * 60)
    print("年齢×年号 整合性ゲート")
    print("=" * 60)

    passed, stats = run_gate(args.threshold)

    print(f"総エピソード数: {stats['total_episodes']}")
    print(f"CRITICAL: {stats['critical_count']}件")
    print(f"WARNING: {stats['warning_count']}件")
    print(f"閾値: {args.threshold}件")

    if args.verbose and stats["issues"]:
        print("\n【検出された問題】")
        for issue in stats["issues"][:20]:
            sev = issue["severity"]
            marker = "🔴" if sev == "CRITICAL" else "🟡"
            print(f"  {marker} [{sev}] {issue['episode_id']} - {issue['person_name']} ({issue['age']}歳)")
            print(
                f"      本文年号: {issue['year_in_text']}年, 想定年: {issue['expected_year']}年, 差: {issue['year_diff']}年"
            )

    if passed:
        print("\n✅ PASS: CRITICAL件数が閾値未満")
        return 0
    else:
        print(f"\n❌ FAIL: CRITICAL件数が閾値({args.threshold})以上")
        return 1


if __name__ == "__main__":
    sys.exit(main())
