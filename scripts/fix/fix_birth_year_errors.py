#!/usr/bin/env python3
"""
A3違反（birth_year誤入力）対処スクリプト

対処対象:
- birth_yearとtext_yearからexpected_ageを計算
- expected_age < 0（生年前のイベント）→ 削除
- expected_age > 150（非現実的）→ 削除
- abs(expected_age - age) > 50 → birth_yearをクリア（空文字に設定）

Usage:
    python scripts/fix/fix_birth_year_errors.py --dry-run
    python scripts/fix/fix_birth_year_errors.py --execute
"""

import argparse
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
LOG_DIR = PROJECT_ROOT / "src" / "reports" / "logs"


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

    # パターン: 4桁の年号（任意の4桁数字）
    pattern = r"(\d{4})年"
    match = re.search(pattern, str(episode_text))

    if match:
        return int(match.group(1))
    return None


def fix_birth_year_errors(dry_run: bool = True) -> dict:
    """
    A3違反（birth_year誤入力）を対処

    対処ロジック:
    1. CSVを読み込む
    2. 各エピソードの本文から年号（YYYY年）を抽出
    3. expected_age = text_year - birth_year を計算
    4. 判定基準:
       - expected_age < 0（生年前のイベント） → 削除
       - expected_age > 150（非現実的） → 削除
       - abs(expected_age - age) > 50 → birth_yearをクリア

    Args:
        dry_run: Trueの場合、実際には保存しない（プレビューのみ）

    Returns:
        対処結果の統計情報
    """
    print("=" * 70)
    print("A3違反（birth_year誤入力）対処スクリプト")
    print("=" * 70)

    # CSV読み込み
    print(f"\n📂 CSV読み込み中: {MASTER_CSV}")
    df = pd.read_csv(MASTER_CSV, dtype={"episode_id": str}, low_memory=False)
    original_count = len(df)
    print(f"   総レコード数: {original_count:,}")

    # 違反を検出
    to_delete = []  # 削除対象（expected_age < 0 or > 150）
    to_clear_birth = []  # birth_yearクリア対象（abs(expected_age - age) > 50）
    skipped_no_year = 0
    skipped_no_birth = 0
    skipped_no_age = 0
    ok_count = 0

    for idx, row in df.iterrows():
        episode_id = row["episode_id"]
        episode_text = row.get("episode_text", "")
        birth_year = row.get("birth_year")
        age = row.get("age")

        # 本文から年号を抽出
        text_year = extract_text_year(str(episode_text) if episode_text else "")

        if text_year is None:
            skipped_no_year += 1
            continue

        if birth_year is None or pd.isna(birth_year):
            skipped_no_birth += 1
            continue

        if age is None or pd.isna(age):
            skipped_no_age += 1
            continue

        birth_year_int = int(float(birth_year))
        age_int = int(float(age))
        expected_age = text_year - birth_year_int

        # expected_age < 0（生年前のイベント）→ 削除
        if expected_age < 0:
            to_delete.append(
                {
                    "episode_id": episode_id,
                    "person_name": row.get("person_name", ""),
                    "birth_year": birth_year_int,
                    "text_year": text_year,
                    "age": age_int,
                    "expected_age": expected_age,
                    "reason": "生年前のイベント（expected_age < 0）",
                    "idx": idx,
                }
            )
            continue

        # expected_age > 150（非現実的）→ 削除
        if expected_age > 150:
            to_delete.append(
                {
                    "episode_id": episode_id,
                    "person_name": row.get("person_name", ""),
                    "birth_year": birth_year_int,
                    "text_year": text_year,
                    "age": age_int,
                    "expected_age": expected_age,
                    "reason": "非現実的（expected_age > 150）",
                    "idx": idx,
                }
            )
            continue

        # abs(expected_age - age) > 2 → birth_yearをクリア（閾値を下げて残存A3違反を対象に）
        age_diff = abs(expected_age - age_int)
        if age_diff > 2:
            to_clear_birth.append(
                {
                    "episode_id": episode_id,
                    "person_name": row.get("person_name", ""),
                    "birth_year": birth_year_int,
                    "text_year": text_year,
                    "age": age_int,
                    "expected_age": expected_age,
                    "diff": age_diff,
                    "idx": idx,
                }
            )
            continue

        # 問題なし
        ok_count += 1

    # 結果表示
    print("\n📊 検出結果:")
    print(f"   年号なしでスキップ: {skipped_no_year:,}")
    print(f"   生年なしでスキップ: {skipped_no_birth:,}")
    print(f"   年齢なしでスキップ: {skipped_no_age:,}")
    print(f"   整合OK（差≤2）: {ok_count:,}")
    print(f"   削除対象: {len(to_delete)}")
    print(f"   birth_yearクリア対象: {len(to_clear_birth)}")

    # 削除対象一覧
    if to_delete:
        print("\n🗑️ 削除対象一覧:")
        print("-" * 110)
        print(
            f"   {'No':>3s}  {'episode_id':24s}  {'person_name':20s}  "
            f"{'birth':>5s}  {'text_year':>9s}  {'age':>3s}  {'expected':>8s}  {'reason':s}"
        )
        print("-" * 110)
        for i, item in enumerate(to_delete[:50], 1):
            person_name = item["person_name"][:18] if item["person_name"] else ""
            reason_short = item["reason"][:30]
            print(
                f"   {i:3d}. {item['episode_id']:24s}  {person_name:20s}  "
                f"{item['birth_year']:5d}  {item['text_year']:9d}  "
                f"{item['age']:3d}  {item['expected_age']:+8d}  {reason_short}"
            )
        if len(to_delete) > 50:
            print(f"   ... 他 {len(to_delete) - 50} 件")
        print("-" * 110)

    # birth_yearクリア対象一覧
    if to_clear_birth:
        print("\n🔧 birth_yearクリア対象一覧（abs(expected_age - age) > 50）:")
        print("-" * 100)
        print(
            f"   {'No':>3s}  {'episode_id':24s}  {'person_name':20s}  "
            f"{'birth':>5s}  {'text_year':>9s}  {'age':>3s}  {'expected':>8s}  {'diff':>5s}"
        )
        print("-" * 100)
        for i, item in enumerate(to_clear_birth[:30], 1):
            person_name = item["person_name"][:18] if item["person_name"] else ""
            print(
                f"   {i:3d}. {item['episode_id']:24s}  {person_name:20s}  "
                f"{item['birth_year']:5d}  {item['text_year']:9d}  "
                f"{item['age']:3d}  {item['expected_age']:8d}  {item['diff']:5d}"
            )
        if len(to_clear_birth) > 30:
            print(f"   ... 他 {len(to_clear_birth) - 30} 件")
        print("-" * 100)

    # 実行
    if not dry_run and (to_delete or to_clear_birth):
        print("\n🔧 対処実行中...")

        # バックアップ作成
        backup_path = create_backup(MASTER_CSV, "birth_year_errors")
        print(f"   バックアップ作成: {backup_path.name}")

        # ログ出力
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if to_delete:
            # 削除対象をログ出力
            delete_log_path = LOG_DIR / f"birth_year_errors_deleted_{timestamp}.csv"
            delete_df = pd.DataFrame(to_delete)
            delete_df.to_csv(delete_log_path, index=False)
            print(f"   削除ログ保存: {delete_log_path.name}")

            # 削除実行
            delete_indices = [item["idx"] for item in to_delete]
            df = df.drop(delete_indices)
            print(f"   削除完了: {len(to_delete)} 件")

        if to_clear_birth:
            # birth_yearクリア対象をログ出力
            clear_log_path = LOG_DIR / f"birth_year_cleared_{timestamp}.csv"
            clear_df = pd.DataFrame(to_clear_birth)
            clear_df.to_csv(clear_log_path, index=False)
            print(f"   クリアログ保存: {clear_log_path.name}")

            # birth_yearクリア実行
            cleared_count = 0
            for item in to_clear_birth:
                if item["idx"] in df.index:
                    df.at[item["idx"], "birth_year"] = ""
                    cleared_count += 1
            print(f"   birth_yearクリア完了: {cleared_count} 件")

        # 保存
        df.to_csv(MASTER_CSV, index=False)
        print(f"   ✅ CSV保存完了: {MASTER_CSV}")
        print(f"   最終レコード数: {len(df):,} (削除: {original_count - len(df)})")

    elif dry_run:
        print("\n⚠️ ドライラン: 実際の対処は行いません")
        print("   実行するには --execute オプションを付けてください")

    return {
        "original_count": original_count,
        "skipped_no_year": skipped_no_year,
        "skipped_no_birth": skipped_no_birth,
        "skipped_no_age": skipped_no_age,
        "ok_count": ok_count,
        "to_delete_count": len(to_delete),
        "to_clear_birth_count": len(to_clear_birth),
        "to_delete": to_delete,
        "to_clear_birth": to_clear_birth,
    }


def main():
    parser = argparse.ArgumentParser(description="A3違反（birth_year誤入力）対処スクリプト")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="実際に対処を実行する（デフォルトはドライラン）",
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

    result = fix_birth_year_errors(dry_run=dry_run)

    print("\n" + "=" * 70)
    print("📈 処理サマリー")
    print("=" * 70)
    print(f"   元レコード数: {result['original_count']:,}")
    print(f"   年号なしスキップ: {result['skipped_no_year']:,}")
    print(f"   生年なしスキップ: {result['skipped_no_birth']:,}")
    print(f"   年齢なしスキップ: {result['skipped_no_age']:,}")
    print(f"   整合OK（差≤2）: {result['ok_count']:,}")
    print("-" * 70)
    print(f"   削除対象: {result['to_delete_count']} 件")
    print("     - expected_age < 0（生年前のイベント）")
    print("     - expected_age > 150（非現実的）")
    print(f"   birth_yearクリア対象: {result['to_clear_birth_count']} 件")
    print("     - abs(expected_age - age) > 50")
    print("=" * 70)

    if args.execute:
        if result["to_delete_count"] > 0 or result["to_clear_birth_count"] > 0:
            print("\n✅ 対処完了!")
        else:
            print("\n✅ 対処対象なし")


if __name__ == "__main__":
    main()
