#!/usr/bin/env python3
"""
年齢境界違反エピソード検出スクリプト

CSVメタデータ（birth_year, death_year, award_year, age, category）をチェックし、
物理的に不可能な年齢設定のエピソードを検出する。

検出パターン：
1. Pattern A: award_year > death_year（死後の業績年）
2. Pattern B: age > (death_year - birth_year)（享年超過）
3. Pattern C: age > (current_year - birth_year)（未来年齢）
4. Pattern D: 現代カテゴリの人物が1920年以前生まれ（時代錯誤）
5. Pattern E: 現在年齢が120歳以上で存命扱い（超長寿）
6. Pattern F: birth_year > death_year（時系列矛盾）

出力：
- 検出されたエピソードのリスト（episode_id, person_name, 違反理由）
- 削除用IDリスト（delete_problematic_phase8.py 互換形式）
- サマリーレポート（JSON形式）
- ログファイル（src/reports/logs/abnormal_birth_year_YYYYMMDD.txt）
"""

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent
MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
REPORTS_DIR = PROJECT_ROOT / "src" / "reports"
LOGS_DIR = REPORTS_DIR / "logs"

# 現代カテゴリ（時代錯誤チェック対象）
MODERN_CATEGORIES = {"エンタメ", "芸能", "スポーツ", "アイドル"}

# 定数
MAX_HUMAN_AGE = 120
MODERN_CATEGORY_BIRTH_CUTOFF = 1920


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


def check_era_mismatch_violation(row: Dict) -> Optional[Dict]:
    """
    Pattern D: 現代カテゴリの人物が1920年以前生まれ（時代錯誤）

    Args:
        row: CSVの行データ

    Returns:
        違反情報 or None
    """
    try:
        birth_year_str = row.get("birth_year", "")
        category = row.get("category", "")

        if not birth_year_str or not category:
            return None

        birth_year = int(float(birth_year_str))

        if birth_year < MODERN_CATEGORY_BIRTH_CUTOFF and category in MODERN_CATEGORIES:
            return {
                "violation_type": "era_mismatch_violation",
                "details": f"時代錯誤: {category}カテゴリなのに{birth_year}年生まれ（1920年以前）",
                "birth_year": birth_year,
                "category": category,
            }
    except (ValueError, TypeError):
        pass

    return None


def check_super_longevity_violation(row: Dict) -> Optional[Dict]:
    """
    Pattern E: 現在年齢が120歳以上で存命扱い（超長寿）

    Args:
        row: CSVの行データ

    Returns:
        違反情報 or None
    """
    try:
        birth_year_str = row.get("birth_year", "")
        death_year_str = row.get("death_year", "")

        # death_yearがある場合はチェック不要（故人）
        if death_year_str and death_year_str.strip():
            return None

        if not birth_year_str:
            return None

        birth_year = int(float(birth_year_str))
        current_year = datetime.now().year
        current_age = current_year - birth_year

        if current_age > MAX_HUMAN_AGE:
            return {
                "violation_type": "super_longevity_violation",
                "details": f"超長寿: {current_age}歳で存命扱い（120歳超過）",
                "birth_year": birth_year,
                "current_age": current_age,
            }
    except (ValueError, TypeError):
        pass

    return None


def check_birth_death_order_violation(row: Dict) -> Optional[Dict]:
    """
    Pattern F: birth_year > death_year（時系列矛盾）

    Args:
        row: CSVの行データ

    Returns:
        違反情報 or None
    """
    try:
        birth_year_str = row.get("birth_year", "")
        death_year_str = row.get("death_year", "")

        if not birth_year_str or not death_year_str:
            return None

        birth_year = int(float(birth_year_str))
        death_year = int(float(death_year_str))

        if birth_year > death_year:
            return {
                "violation_type": "birth_death_order_violation",
                "details": f"時系列矛盾: birth_year({birth_year}) > death_year({death_year})",
                "birth_year": birth_year,
                "death_year": death_year,
            }
    except (ValueError, TypeError):
        pass

    return None


def detect_violations(csv_path: Path, patterns: Optional[List[str]] = None) -> List[Dict]:
    """
    CSVを読み込み、指定パターンをチェック

    Args:
        csv_path: CSVファイルパス
        patterns: チェックするパターンのリスト（None=全パターン）
                  有効値: A, B, C, D, E, F

    Returns:
        違反エピソードのリスト
    """
    violations = []

    # パターンマッピング
    pattern_checks = {
        "A": ("award_year_violation", check_award_year_violation),
        "B": ("age_boundary_violation", check_age_boundary_violation),
        "C": ("future_age_violation", check_future_age_violation),
        "D": ("era_mismatch_violation", check_era_mismatch_violation),
        "E": ("super_longevity_violation", check_super_longevity_violation),
        "F": ("birth_death_order_violation", check_birth_death_order_violation),
    }

    # パターン指定がない場合は全パターン
    if patterns is None:
        active_patterns = list(pattern_checks.keys())
    else:
        active_patterns = [p.upper() for p in patterns if p.upper() in pattern_checks]

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        for row in reader:
            episode_id = row.get("episode_id", "")
            person_name = row.get("person_name", "")

            if not episode_id or not person_name:
                continue

            # 指定されたパターンをチェック
            for pattern_key in active_patterns:
                _, check_func = pattern_checks[pattern_key]
                violation = check_func(row)

                if violation:
                    violations.append(
                        {
                            "episode_id": episode_id,
                            "person_name": person_name,
                            "pattern": pattern_key,
                            **violation,
                            "age": row.get("age", ""),
                            "category": row.get("category", ""),
                        }
                    )
                    break  # 1エピソード1違反のみ報告

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


def write_log_file(violations: List[Dict], log_path: Path) -> None:
    """
    検出結果をログファイルに出力

    Args:
        violations: 違反エピソードのリスト
        log_path: ログファイルパス
    """
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with open(log_path, "w", encoding="utf-8") as f:
        f.write("=" * 70 + "\n")
        f.write("異常birth_year検出レポート\n")
        f.write(f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 70 + "\n\n")

        # パターン別集計
        pattern_counts: dict[str, int] = {}
        for v in violations:
            pattern = v.get("pattern", "?")
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1

        f.write("【パターン別集計】\n")
        pattern_labels = {
            "A": "Pattern A (死後の業績年)",
            "B": "Pattern B (享年超過)",
            "C": "Pattern C (未来年齢)",
            "D": "Pattern D (時代錯誤)",
            "E": "Pattern E (超長寿)",
            "F": "Pattern F (時系列矛盾)",
        }
        for pattern, count in sorted(pattern_counts.items()):
            label = pattern_labels.get(pattern, f"Pattern {pattern}")
            f.write(f"  {label}: {count}件\n")
        f.write(f"\n  合計: {len(violations)}件\n\n")

        # 詳細
        f.write("【検出エピソード詳細】\n\n")
        for i, v in enumerate(violations, 1):
            f.write(f"{i}. {v['person_name']}\n")
            f.write(f"   episode_id: {v['episode_id']}\n")
            f.write(f"   パターン: {v.get('pattern', '?')}\n")
            f.write(f"   違反タイプ: {v['violation_type']}\n")
            f.write(f"   詳細: {v['details']}\n")
            if v.get("category"):
                f.write(f"   カテゴリ: {v['category']}\n")
            f.write("\n")


def main():
    parser = argparse.ArgumentParser(description="年齢境界違反エピソード検出")
    parser.add_argument("--analyze", action="store_true", help="分析のみ（削除なし）")
    parser.add_argument("--generate-delete-list", action="store_true", help="削除IDリスト生成")
    parser.add_argument("--report", type=str, help="レポート出力パス（JSON形式）")
    parser.add_argument("--csv", type=str, default=str(MASTER_CSV), help="CSVファイルパス")
    parser.add_argument(
        "--pattern",
        type=str,
        action="append",
        help="チェックするパターン（A/B/C/D/E/F）。複数指定可。未指定時は全パターン",
    )
    parser.add_argument("--log", action="store_true", help="ログファイル出力")
    args = parser.parse_args()

    csv_path = Path(args.csv)

    if not csv_path.exists():
        print(f"❌ CSVファイルが見つかりません: {csv_path}")
        return 1

    print("=" * 70)
    print("🔍 年齢境界違反エピソード検出")
    print("=" * 70)
    print(f"対象: {csv_path}")

    # パターン表示
    if args.pattern:
        print(f"パターン: {', '.join(args.pattern)}")
    else:
        print("パターン: 全パターン (A/B/C/D/E/F)")
    print()

    # 検出実行
    violations = detect_violations(csv_path, args.pattern)

    # エピソード総数
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        total_episodes = sum(1 for _ in csv.DictReader(f))

    # 統計
    pattern_counts: dict[str, int] = {}
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
    pattern_labels = {
        "award_year_violation": "Pattern A (死後の業績年)",
        "age_boundary_violation": "Pattern B (享年超過)",
        "future_age_violation": "Pattern C (未来年齢)",
        "era_mismatch_violation": "Pattern D (時代錯誤)",
        "super_longevity_violation": "Pattern E (超長寿)",
        "birth_death_order_violation": "Pattern F (時系列矛盾)",
    }
    for vtype, count in sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True):
        label = pattern_labels.get(vtype, vtype)
        print(f"  - {label}: {count}件")
    print()

    # 詳細表示
    if args.analyze:
        print("📋 違反エピソード詳細:")
        print()
        for i, v in enumerate(violations, 1):
            print(f"{i}. {v['person_name']} (ID: {v['episode_id']})")
            print(f"   パターン: {v.get('pattern', '?')}")
            print(f"   違反タイプ: {v['violation_type']}")
            print(f"   詳細: {v['details']}")
            if v.get("category"):
                print(f"   カテゴリ: {v['category']}")
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

    # ログ出力
    if args.log:
        date_str = datetime.now().strftime("%Y%m%d")
        log_path = LOGS_DIR / f"abnormal_birth_year_{date_str}.txt"
        write_log_file(violations, log_path)
        print(f"📄 ログ出力: {log_path}")

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
