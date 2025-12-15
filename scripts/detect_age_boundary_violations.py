#!/usr/bin/env python3
"""
年齢境界違反エピソード検出スクリプト

CSVメタデータ（birth_year, death_year, award_year, age）をチェックし、
物理的に不可能な年齢設定のエピソードを検出する。

検出パターン：
1. Pattern A: award_year > death_year（死後の業績年）
2. Pattern B: age > (death_year - birth_year)（享年超過）
3. Pattern C: age > (current_year - birth_year)（未来年齢）

出力：
- 検出されたエピソードのリスト（episode_id, person_name, 違反理由）
- 削除用IDリスト（delete_problematic_phase8.py 互換形式）
- サマリーレポート（JSON形式）
"""

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

PROJECT_ROOT = Path(__file__).parent.parent
MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
REPORTS_DIR = PROJECT_ROOT / "reports"


def check_award_year_violation(row: Dict) -> Optional[Dict]:
    """
    award_year と death_year の矛盾をチェック

    Args:
        row: CSVの行データ

    Returns:
        違反情報 or None
    """
    try:
        award_year_str = row.get("award_year", "")
        death_year_str = row.get("death_year", "")

        if not award_year_str or not death_year_str:
            return None

        award_year = int(float(award_year_str))
        death_year = int(float(death_year_str))

        if award_year > death_year:
            return {
                "violation_type": "award_year_violation",
                "details": f"award_year({award_year}) > death_year({death_year})",
                "award_year": award_year,
                "death_year": death_year,
            }
    except (ValueError, TypeError):
        pass

    return None


def check_age_boundary_violation(row: Dict) -> Optional[Dict]:
    """
    age と (death_year - birth_year) の矛盾をチェック

    Args:
        row: CSVの行データ

    Returns:
        違反情報 or None
    """
    try:
        age_str = row.get("age", "")
        birth_year_str = row.get("birth_year", "")
        death_year_str = row.get("death_year", "")

        if not age_str or not birth_year_str or not death_year_str:
            return None

        age = int(float(age_str))
        birth_year = int(float(birth_year_str))
        death_year = int(float(death_year_str))

        max_age = death_year - birth_year

        if age > max_age:
            return {
                "violation_type": "age_boundary_violation",
                "details": f"age({age}) > max_age({max_age})",
                "age": age,
                "max_age": max_age,
                "birth_year": birth_year,
                "death_year": death_year,
            }
    except (ValueError, TypeError):
        pass

    return None


def check_future_age_violation(row: Dict) -> Optional[Dict]:
    """
    age と (current_year - birth_year) の矛盾をチェック

    Args:
        row: CSVの行データ

    Returns:
        違反情報 or None
    """
    try:
        age_str = row.get("age", "")
        birth_year_str = row.get("birth_year", "")
        death_year_str = row.get("death_year", "")

        # death_yearがある場合はチェック不要（故人）
        if death_year_str:
            return None

        if not age_str or not birth_year_str:
            return None

        age = int(float(age_str))
        birth_year = int(float(birth_year_str))
        current_year = datetime.now().year
        current_age = current_year - birth_year

        if age > current_age:
            return {
                "violation_type": "future_age_violation",
                "details": f"age({age}) > current_age({current_age})",
                "age": age,
                "current_age": current_age,
                "birth_year": birth_year,
                "current_year": current_year,
            }
    except (ValueError, TypeError):
        pass

    return None


def detect_violations(csv_path: Path) -> List[Dict]:
    """
    CSVを読み込み、全パターンをチェック

    Args:
        csv_path: CSVファイルパス

    Returns:
        違反エピソードのリスト
    """
    violations = []

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        for row in reader:
            episode_id = row.get("episode_id", "")
            person_name = row.get("person_name", "")

            if not episode_id or not person_name:
                continue

            # 3つのパターンをチェック
            violation = None

            # Pattern A: award_year > death_year
            violation = check_award_year_violation(row)
            if violation:
                violations.append(
                    {
                        "episode_id": episode_id,
                        "person_name": person_name,
                        **violation,
                        "age": row.get("age", ""),
                        "birth_year": row.get("birth_year", ""),
                    }
                )
                continue

            # Pattern B: age > (death_year - birth_year)
            violation = check_age_boundary_violation(row)
            if violation:
                violations.append(
                    {
                        "episode_id": episode_id,
                        "person_name": person_name,
                        **violation,
                    }
                )
                continue

            # Pattern C: age > (current_year - birth_year)
            violation = check_future_age_violation(row)
            if violation:
                violations.append(
                    {
                        "episode_id": episode_id,
                        "person_name": person_name,
                        **violation,
                    }
                )

    return violations


def generate_delete_list(violations: List[Dict]) -> List[str]:
    """
    episode_id のリストを生成（削除スクリプト用）

    Args:
        violations: 違反エピソードのリスト

    Returns:
        episode_id のリスト
    """
    return [v["episode_id"] for v in violations]


def main():
    parser = argparse.ArgumentParser(description="年齢境界違反エピソード検出")
    parser.add_argument("--analyze", action="store_true", help="分析のみ（削除なし）")
    parser.add_argument("--generate-delete-list", action="store_true", help="削除IDリスト生成")
    parser.add_argument("--report", type=str, help="レポート出力パス（JSON形式）")
    parser.add_argument("--csv", type=str, default=str(MASTER_CSV), help="CSVファイルパス")
    args = parser.parse_args()

    csv_path = Path(args.csv)

    if not csv_path.exists():
        print(f"❌ CSVファイルが見つかりません: {csv_path}")
        return 1

    print("=" * 70)
    print("🔍 年齢境界違反エピソード検出")
    print("=" * 70)
    print(f"対象: {csv_path}")
    print()

    # 検出実行
    violations = detect_violations(csv_path)

    # エピソード総数
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        total_episodes = sum(1 for _ in csv.DictReader(f))

    # 統計
    pattern_counts = {}
    for v in violations:
        vtype = v["violation_type"]
        pattern_counts[vtype] = pattern_counts.get(vtype, 0) + 1

    print(f"📊 総エピソード数: {total_episodes:,}件")
    print(f"❌ 違反エピソード: {len(violations)}件")
    print()

    if len(violations) == 0:
        print("✅ 年齢境界違反は検出されませんでした")
        return 0

    print("📊 違反パターン別:")
    for vtype, count in sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {vtype}: {count}件")
    print()

    # 詳細表示
    if args.analyze:
        print("📋 違反エピソード詳細:")
        print()
        for i, v in enumerate(violations, 1):
            print(f"{i}. {v['person_name']} (ID: {v['episode_id']})")
            print(f"   違反タイプ: {v['violation_type']}")
            print(f"   詳細: {v['details']}")
            print()

    # 削除IDリスト生成
    if args.generate_delete_list:
        delete_ids = generate_delete_list(violations)
        print("🗑️  削除IDリスト:")
        print()
        print("DELETE_IDS = [")
        for episode_id in delete_ids:
            print(f'    "{episode_id}",')
        print("]")
        print()

    # レポート出力
    if args.report:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report = {
            "timestamp": timestamp,
            "csv_path": str(csv_path),
            "total_episodes": total_episodes,
            "violations_found": len(violations),
            "patterns": pattern_counts,
            "episodes": violations,
            "delete_ids": generate_delete_list(violations),
        }

        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"📄 レポート出力: {report_path}")

    return 0


if __name__ == "__main__":
    exit(main())
