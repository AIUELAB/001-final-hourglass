#!/usr/bin/env python3
"""
A3_year_age_mismatch違反修正スクリプト

修正ロジック:
1. CSVを読み込む
2. 各エピソードの本文(episode_text)から年号（YYYY年パターン）を抽出
3. expected_age = text_year - birth_year を計算
4. abs(age - expected_age) > 1 の場合、ageをexpected_ageに更新
5. CSVを保存

パターン例:
- 「1995年」
- 「2023年」
"""

import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
BACKUP_DIR = PROJECT_ROOT / "preserved" / "backups"


def create_backup(csv_path: Path, operation: str) -> Path:
    """バックアップを作成"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"MASTER_EPISODES_{operation}_{timestamp}.csv"
    backup_path = BACKUP_DIR / backup_name
    shutil.copy2(csv_path, backup_path)
    return backup_path


def extract_text_year(episode_text: str) -> int | None:
    """
    本文から年号（YYYY年パターン）を抽出

    パターン:
    - 「1995年」「2023年」などの4桁年号
    - 複数ある場合は最初にマッチしたものを返す
    """
    if not episode_text or pd.isna(episode_text):
        return None

    # パターン: 4桁の年号（1800年〜2100年の範囲）
    pattern = r"(1[89]\d{2}|20\d{2}|21\d{2})年"
    match = re.search(pattern, str(episode_text))

    if match:
        return int(match.group(1))
    return None


def fix_age_year_consistency(dry_run: bool = True) -> dict:
    """
    年号-年齢不整合を修正

    Args:
        dry_run: Trueの場合、実際には保存しない（プレビューのみ）

    Returns:
        修正結果の統計情報
    """
    print("=" * 70)
    print("A3_year_age_mismatch違反修正スクリプト")
    print("=" * 70)

    # CSV読み込み
    print(f"\n📂 CSV読み込み中: {MASTER_CSV}")
    df = pd.read_csv(MASTER_CSV, dtype={"episode_id": str})
    print(f"   総レコード数: {len(df):,}")

    # 不整合を検出・修正
    fixes = []
    skipped_no_year = 0
    skipped_no_birth = 0
    skipped_within_tolerance = 0
    skipped_invalid_age = 0

    for idx, row in df.iterrows():
        episode_id = row["episode_id"]
        current_age = row.get("age")
        episode_text = row.get("episode_text", "")
        birth_year = row.get("birth_year")

        # 本文から年号を抽出
        episode_text_str = str(episode_text) if episode_text is not None else ""
        text_year = extract_text_year(episode_text_str)

        if text_year is None:
            skipped_no_year += 1
            continue

        if birth_year is None or (isinstance(birth_year, float) and pd.isna(birth_year)):
            skipped_no_birth += 1
            continue

        if current_age is None or (isinstance(current_age, float) and pd.isna(current_age)):
            continue

        # 期待される年齢を計算
        birth_year_int = int(float(birth_year))
        expected_age = text_year - birth_year_int
        current_age_int = int(float(current_age))

        # 妥当性チェック: 0歳未満または120歳超えは不正データとしてスキップ
        if expected_age < 0 or expected_age > 120:
            skipped_invalid_age += 1
            continue

        # 1歳以上の差がある場合のみ修正
        if abs(current_age_int - expected_age) > 1:
            fixes.append(
                {
                    "episode_id": episode_id,
                    "person_name": row.get("person_name", ""),
                    "birth_year": birth_year_int,
                    "text_year": text_year,
                    "old_age": current_age_int,
                    "expected_age": expected_age,
                    "diff": abs(current_age_int - expected_age),
                    "idx": idx,
                }
            )
        else:
            skipped_within_tolerance += 1

    # 結果表示
    print("\n📊 検出結果:")
    print(f"   年号なしでスキップ: {skipped_no_year:,}")
    print(f"   生年なしでスキップ: {skipped_no_birth:,}")
    print(f"   不正年齢でスキップ: {skipped_invalid_age:,} (0未満 or 120超)")
    print(f"   許容範囲内（差≤1）: {skipped_within_tolerance:,}")
    print(f"   不整合件数（差>1）: {len(fixes)}")

    if fixes:
        print("\n📋 修正対象一覧:")
        print("-" * 90)
        print(
            f"   {'No':>3s}  {'episode_id':20s}  {'person_name':20s}  "
            f"{'birth':>5s}  {'text_year':>9s}  {'old':>3s} → {'new':>3s}  {'diff':>4s}"
        )
        print("-" * 90)
        for i, fix in enumerate(fixes[:50], 1):  # 最大50件表示
            person_name = fix["person_name"][:18] if fix["person_name"] else ""
            print(
                f"   {i:3d}. {fix['episode_id']:20s}  {person_name:20s}  "
                f"{fix['birth_year']:5d}  {fix['text_year']:9d}  "
                f"{fix['old_age']:3d} → {fix['expected_age']:3d}  ({fix['diff']:+3d})"
            )
        if len(fixes) > 50:
            print(f"   ... 他 {len(fixes) - 50} 件")
        print("-" * 90)

    # 修正実行
    if not dry_run and fixes:
        print("\n🔧 修正実行中...")

        # バックアップ作成
        backup_path = create_backup(MASTER_CSV, "age_year_consistency")
        print(f"   バックアップ作成: {backup_path.name}")

        # 修正適用
        for fix in fixes:
            df.at[fix["idx"], "age"] = fix["expected_age"]

        # 保存
        df.to_csv(MASTER_CSV, index=False)
        print(f"   ✅ CSV保存完了: {MASTER_CSV}")
    elif dry_run:
        print("\n⚠️ ドライラン: 実際の修正は行いません")
        print("   実行するには --execute オプションを付けてください")

    return {
        "total_records": len(df),
        "skipped_no_year": skipped_no_year,
        "skipped_no_birth": skipped_no_birth,
        "skipped_invalid_age": skipped_invalid_age,
        "skipped_within_tolerance": skipped_within_tolerance,
        "fixes_count": len(fixes),
        "fixes": fixes,
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="A3_year_age_mismatch違反修正スクリプト（年号-年齢不整合）")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="実際に修正を実行する（デフォルトはドライラン）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="変更をプレビュー（デフォルト）",
    )

    args = parser.parse_args()

    # --execute が指定された場合は dry_run を False に
    dry_run = not args.execute

    result = fix_age_year_consistency(dry_run=dry_run)

    print("\n📈 サマリー:")
    print(f"   総レコード数: {result['total_records']:,}")
    print(f"   年号なしスキップ: {result['skipped_no_year']:,}")
    print(f"   生年なしスキップ: {result['skipped_no_birth']:,}")
    print(f"   不正年齢スキップ: {result['skipped_invalid_age']:,}")
    print(f"   許容範囲内: {result['skipped_within_tolerance']:,}")
    print(f"   修正件数: {result['fixes_count']}")

    if args.execute and result["fixes_count"] > 0:
        print("\n✅ 修正完了!")


if __name__ == "__main__":
    main()
