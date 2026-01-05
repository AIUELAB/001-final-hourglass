#!/usr/bin/env python3
"""年齢×年号 整合性ゲート v2

v1からの改善点:
- 回顧型言及パターンを除外（「〜以来」「〜から」「後に〜」等）
- 「主題年」のみを検証対象とする

使用方法:
    python scripts/validation/year_age_consistency_gate_v2.py [--threshold N]

終了コード:
    0: PASS（CRITICALが0件）
    1: FAIL（CRITICALがN件以上）
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
YEAR_TOLERANCE_WARNING = 3
YEAR_TOLERANCE_CRITICAL = 5

# デフォルト閾値
DEFAULT_CRITICAL_THRESHOLD = 5

# v2除外パターン（年代・生年等）
EXCLUSION_PATTERNS = [
    re.compile(r"\d{4}年生(?:まれ)?"),
    re.compile(r"\d{4}年創立"),
    re.compile(r"\d{4}年設立"),
    re.compile(r"\d{4}年代"),
    re.compile(r"\d{4}年(?:頃|ころ)"),
]

# 回顧型除外パターン（v3由来）
RETROSPECTIVE_PATTERNS = [
    re.compile(r"\d{4}年の.{0,10}以来"),
    re.compile(r"\d{4}年から"),
    re.compile(r"\d{4}年のデビュー"),
    re.compile(r"\d{4}年の連載"),
    re.compile(r"\d{4}年の結成"),
    re.compile(r"\d{4}年の(?:コンビ|グループ)"),
    re.compile(r"\d{4}年当時"),
    re.compile(r"\d{4}年に.{0,15}(?:した後|してから)"),
    re.compile(r"\d{4}年に(?:始|開始)"),
    re.compile(r"(?:若|幼|少年|少女).{0,5}\d{4}年"),
    re.compile(r"(?:かつて|過去に|昔).{0,10}\d{4}年"),
    re.compile(r"\d{4}年(?:スタート|発売|公開|リリース)"),
    re.compile(r"後に.{0,20}\d{4}年"),
    re.compile(r"この(?:功績|業績|実績).{0,10}\d{4}年"),
    re.compile(r"\d{4}年には"),
    re.compile(r"\d+年(?:以上|後)"),
    re.compile(r"(?:受賞|獲得).{0,5}\d{4}年"),
    re.compile(r"\d{4}年(?:の|に)(?:ノーベル|アカデミー|オリンピック|ワールドカップ)"),
    re.compile(r"\d{4}年(?:の|に)(?:引退|復帰|復活)"),
    re.compile(r"その後.{0,15}\d{4}年"),
    re.compile(r"\d{4}年(?:まで|現在)"),
]


def is_excluded(context: str) -> bool:
    """除外パターンにマッチするか"""
    for pattern in EXCLUSION_PATTERNS:
        if pattern.search(context):
            return True
    return False


def is_retrospective(context: str) -> bool:
    """回顧型言及か"""
    for pattern in RETROSPECTIVE_PATTERNS:
        if pattern.search(context):
            return True
    return False


def extract_subject_years(text: str) -> list[tuple[int, str]]:
    """
    本文から「主題年」を抽出（回顧型・除外パターンを除く）

    Returns:
        list of (year, context)
    """
    results = []

    for match in YEAR_PATTERN.finditer(text):
        year_str = match.group(1)
        year = int(year_str)

        if not (1000 <= year <= 2100):
            continue

        # 周辺文脈を取得
        start = max(0, match.start() - 50)
        end = min(len(text), match.end() + 50)
        context = text[start:end]

        if is_excluded(context):
            continue

        if is_retrospective(context):
            continue

        results.append((year, context))

    return results


def check_episode(row: dict) -> dict | None:
    """単一エピソードの年齢×年号整合性をチェック（v2改良版）"""
    person_name = row.get("person_name", "")
    age_str = row.get("age", "")
    episode_text = row.get("episode_text", "")
    person_type = row.get("person_type", "REAL")

    if person_type == "FICTIONAL":
        return None

    try:
        age = int(float(age_str))
    except (ValueError, TypeError):
        return None

    # 主題年を抽出
    subject_years = extract_subject_years(episode_text)
    if not subject_years:
        return None

    birth_year = get_birth_year(person_name)
    if birth_year is None:
        return None

    expected_year = birth_year + age

    # 最大乖離を検出
    max_diff = 0
    worst_year = None
    worst_context = ""
    for year, context in subject_years:
        diff = abs(year - expected_year)
        if diff > max_diff:
            max_diff = diff
            worst_year = year
            worst_context = context

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
            "context": worst_context[:100],
        }

    return None


def run_gate(critical_threshold: int = DEFAULT_CRITICAL_THRESHOLD) -> tuple[bool, dict]:
    """ゲートを実行"""
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
    parser = argparse.ArgumentParser(description="年齢×年号 整合性ゲート v2")
    parser.add_argument(
        "--threshold",
        type=int,
        default=DEFAULT_CRITICAL_THRESHOLD,
        help=f"CRITICAL件数の閾値（デフォルト: {DEFAULT_CRITICAL_THRESHOLD}）",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="詳細出力")
    args = parser.parse_args()

    print("=" * 60)
    print("年齢×年号 整合性ゲート v2")
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
