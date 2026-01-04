#!/usr/bin/env python3
"""
寄せ集めエピソード品質ゲート

生成されたエピソードが「寄せ集め」パターンに該当するかをチェックし、
問題があれば生成をブロックする。

使用方法:
    from scripts.validation.hodgepodge_quality_gate import check_episode_quality

    result = check_episode_quality(episode_text, target_age)
    if not result["passed"]:
        # 再生成または修正が必要
        print(result["reason"])

終了コード（スタンドアロン実行時）:
    0: 問題なし
    1: 寄せ集め検出
"""

import re
import sys
from typing import TypedDict


class QualityResult(TypedDict):
    passed: bool
    score: int
    reason: str
    details: dict


# 閾値
SCORE_THRESHOLD = 10  # このスコア以上で不合格
AGE_DIFF_THRESHOLD = 10  # 年齢差がこれ以上で問題
YEAR_RANGE_THRESHOLD = 5  # 年号差がこれ以上で問題


def extract_ages(text: str) -> list[int]:
    """本文中の年齢を抽出"""
    return [int(m) for m in re.findall(r"(\d+)歳", text)]


def extract_years(text: str) -> list[int]:
    """本文中の年号を抽出（1800-2100年の範囲）"""
    years = [int(m) for m in re.findall(r"(\d{4})年", text)]
    return [y for y in years if 1800 <= y <= 2100]


def count_works(text: str) -> int:
    """作品名の数をカウント"""
    works = re.findall(r"『[^』]+』", text)
    return len(works)


def count_time_jumps(text: str) -> int:
    """時系列ジャンプ語の数をカウント"""
    patterns = [
        r"その後",
        r"翌年",
        r"数年後",
        r"数年前",
        r"\d+年後",
        r"\d+年前",
        r"後に",
        r"かつて",
        r"当時",
        r"以前に",
        r"以降",
        r"やがて",
    ]
    count = 0
    for pattern in patterns:
        count += len(re.findall(pattern, text))
    return count


def check_episode_quality(episode_text: str, target_age: int) -> QualityResult:
    """
    エピソードの品質をチェック

    Args:
        episode_text: エピソード本文
        target_age: 対象年齢（CSVのageフィールド）

    Returns:
        QualityResult: passed=True なら合格
    """
    score = 0
    issues = []

    # 1. 年齢チェック
    ages = extract_ages(episode_text)
    other_ages = [a for a in ages if abs(a - target_age) > AGE_DIFF_THRESHOLD]

    if other_ages:
        score += len(other_ages) * 3
        issues.append(f"他年齢言及: {other_ages}")

    # 2. 年号チェック
    years = extract_years(episode_text)
    if len(years) >= 2:
        year_range = max(years) - min(years)
        if year_range > YEAR_RANGE_THRESHOLD:
            score += year_range // 2
            issues.append(f"年号スパン: {year_range}年 ({min(years)}-{max(years)})")

    # 3. 作品数チェック
    works_count = count_works(episode_text)
    if works_count >= 3:
        score += (works_count - 2) * 2
        issues.append(f"作品列挙: {works_count}作品")

    # 4. 時系列ジャンプチェック
    time_jumps = count_time_jumps(episode_text)
    if time_jumps >= 3:
        score += time_jumps
        issues.append(f"時系列ジャンプ: {time_jumps}回")

    # 結果判定
    passed = score < SCORE_THRESHOLD

    return QualityResult(
        passed=passed,
        score=score,
        reason="; ".join(issues) if issues else "OK",
        details={
            "ages": ages,
            "other_ages": other_ages,
            "years": years,
            "works_count": works_count,
            "time_jumps": time_jumps,
        },
    )


def main():
    """スタンドアロン実行用"""
    import argparse
    import csv
    from pathlib import Path

    parser = argparse.ArgumentParser(description="寄せ集めエピソード品質ゲート")
    parser.add_argument("--episode-id", help="チェックするエピソードID")
    parser.add_argument("--all", action="store_true", help="全エピソードをチェック")
    args = parser.parse_args()

    csv_path = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    failed_count = 0

    for row in rows:
        if args.episode_id and row.get("episode_id") != args.episode_id:
            continue

        text = row.get("episode_text", "")
        age_str = row.get("age", "")

        try:
            age = int(float(age_str))
        except (ValueError, TypeError):
            continue

        result = check_episode_quality(text, age)

        if not result["passed"]:
            failed_count += 1
            if not args.all or failed_count <= 10:
                print(f"❌ {row['episode_id']} ({row['person_name']} {age}歳)")
                print(f"   score={result['score']}: {result['reason']}")

    if args.all:
        print(f"\n不合格: {failed_count}件 / {len(rows)}件")

    return 1 if failed_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
