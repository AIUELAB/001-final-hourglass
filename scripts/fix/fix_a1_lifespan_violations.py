#!/usr/bin/env python3
"""
A1違反（年齢が寿命超過）修正スクリプト

A1違反: age > (death_year - birth_year)
本文のtext_yearから推定birth_yearを計算し、妥当性をチェックして修正または削除を行う。

修正ロジック:
1. A1違反エピソードを検出 (age + birth_year > death_year)
2. 本文からtext_yearを抽出
3. 推定birth_year = text_year - age を計算
4. 推定値が妥当（1850-2010）かチェック
5. 修正可能: birth_year/death_yearをクリア（将来的に再設定可能に）
6. 修正不可: 削除

Usage:
    python scripts/fix/fix_a1_lifespan_violations.py --dry-run
    python scripts/fix/fix_a1_lifespan_violations.py --execute
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
LOGS_DIR = PROJECT_ROOT / "src" / "reports" / "logs"

# 推定birth_yearの妥当範囲
MIN_VALID_BIRTH_YEAR = 1850
MAX_VALID_BIRTH_YEAR = 2010


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


def detect_a1_violations(df: pd.DataFrame) -> list[dict]:
    """
    A1違反（age + birth_year > death_year）を検出

    Args:
        df: マスターCSVのDataFrame

    Returns:
        違反エピソードのリスト
    """
    violations = []

    for idx, row in df.iterrows():
        episode_id = row.get("episode_id", "")
        person_name = row.get("person_name", "")
        age_str = row.get("age", "")
        birth_year_str = row.get("birth_year", "")
        death_year_str = row.get("death_year", "")
        episode_text = row.get("episode_text", "")

        # 必須フィールドの存在チェック
        if not age_str or not birth_year_str or not death_year_str:
            continue

        try:
            age = int(float(age_str))
            birth_year = int(float(birth_year_str))
            death_year = int(float(death_year_str))
        except (ValueError, TypeError):
            continue

        # A1違反チェック: age > (death_year - birth_year)
        max_age = death_year - birth_year
        if age > max_age:
            # 本文から年号を抽出
            text_year = extract_text_year(str(episode_text) if episode_text else "")

            # 推定birth_yearを計算
            estimated_birth_year = None
            if text_year is not None:
                estimated_birth_year = text_year - age

            violations.append(
                {
                    "idx": idx,
                    "episode_id": episode_id,
                    "person_name": person_name,
                    "age": age,
                    "birth_year": birth_year,
                    "death_year": death_year,
                    "max_age": max_age,
                    "excess": age - max_age,
                    "text_year": text_year,
                    "estimated_birth_year": estimated_birth_year,
                }
            )

    return violations


def classify_violations(violations: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    違反を「修正可能」と「削除対象」に分類

    修正可能条件:
    - text_yearから推定したbirth_yearが妥当範囲（1850-2010）
    - 推定birth_yearがdeath_yearより前

    Args:
        violations: A1違反リスト

    Returns:
        (修正可能リスト, 削除対象リスト)
    """
    fixable = []
    deletable = []

    for v in violations:
        estimated = v["estimated_birth_year"]
        death_year = v["death_year"]

        if estimated is None:
            # text_yearが抽出できなかった場合は削除
            v["reason"] = "text_yearが抽出できない"
            deletable.append(v)
        elif estimated < MIN_VALID_BIRTH_YEAR or estimated > MAX_VALID_BIRTH_YEAR:
            # 推定birth_yearが範囲外
            v["reason"] = f"推定birth_year={estimated}が範囲外({MIN_VALID_BIRTH_YEAR}-{MAX_VALID_BIRTH_YEAR})"
            deletable.append(v)
        elif estimated >= death_year:
            # 推定birth_yearがdeath_year以降（不正）
            v["reason"] = f"推定birth_year={estimated} >= death_year={death_year}"
            deletable.append(v)
        else:
            # 修正可能
            v["new_birth_year"] = estimated
            fixable.append(v)

    return fixable, deletable


def fix_a1_lifespan_violations(dry_run: bool = True) -> dict:
    """
    A1違反を修正/削除

    Args:
        dry_run: Trueの場合、実際には保存しない（プレビューのみ）

    Returns:
        修正結果の統計情報
    """
    print("=" * 70)
    print("A1違反修正: 年齢が寿命超過")
    print("=" * 70)

    # CSV読み込み
    print(f"\n📂 CSV読み込み中: {MASTER_CSV}")
    df = pd.read_csv(MASTER_CSV, dtype={"episode_id": str}, low_memory=False)
    original_count = len(df)
    print(f"   総レコード数: {original_count:,}")

    # A1違反を検出
    print("\n🔍 A1違反を検出中...")
    violations = detect_a1_violations(df)
    print(f"   検出件数: {len(violations)}")

    if not violations:
        print("\n✅ A1違反は検出されませんでした")
        return {
            "total_records": original_count,
            "violations_found": 0,
            "fixed_count": 0,
            "deleted_count": 0,
        }

    # 修正可能/削除対象に分類
    fixable, deletable = classify_violations(violations)
    print("\n📊 分類結果:")
    print(f"   修正可能（birth_year/death_yearクリア）: {len(fixable)}件")
    print(f"   削除対象: {len(deletable)}件")

    # 修正可能リスト表示
    if fixable:
        print("\n📋 修正可能リスト（birth_year/death_yearをクリア）:")
        print("-" * 100)
        print(
            f"   {'No':>3s}  {'episode_id':24s}  {'person_name':20s}  "
            f"{'age':>3s}  {'old_birth':>10s}  {'est_birth':>10s}  {'text_year':>9s}"
        )
        print("-" * 100)
        for i, v in enumerate(fixable[:30], 1):
            person_name = v["person_name"][:18] if v["person_name"] else ""
            print(
                f"   {i:3d}. {v['episode_id']:24s}  {person_name:20s}  "
                f"{v['age']:3d}  {v['birth_year']:10d}  {v['estimated_birth_year']:10d}  "
                f"{v['text_year']:9d}"
            )
        if len(fixable) > 30:
            print(f"   ... 他 {len(fixable) - 30} 件")
        print("-" * 100)

    # 削除対象リスト表示
    if deletable:
        print("\n🗑️  削除対象リスト:")
        print("-" * 110)
        print(
            f"   {'No':>3s}  {'episode_id':24s}  {'person_name':20s}  "
            f"{'age':>3s}  {'birth':>5s}  {'death':>5s}  {'reason':40s}"
        )
        print("-" * 110)
        for i, v in enumerate(deletable[:30], 1):
            person_name = v["person_name"][:18] if v["person_name"] else ""
            reason = v["reason"][:38] if v.get("reason") else ""
            print(
                f"   {i:3d}. {v['episode_id']:24s}  {person_name:20s}  "
                f"{v['age']:3d}  {v['birth_year']:5d}  {v['death_year']:5d}  {reason:40s}"
            )
        if len(deletable) > 30:
            print(f"   ... 他 {len(deletable) - 30} 件")
        print("-" * 110)

    # 修正実行
    if not dry_run:
        print("\n🔧 修正実行中...")

        # バックアップ作成
        backup_path = create_backup(MASTER_CSV, "a1_lifespan_fix")
        print(f"   バックアップ作成: {backup_path.name}")

        # 修正可能: birth_year/death_yearをクリア
        fixed_count = 0
        for v in fixable:
            idx = v["idx"]
            df.at[idx, "birth_year"] = ""
            df.at[idx, "death_year"] = ""
            fixed_count += 1

        # 削除対象: 行を削除
        delete_indices = [v["idx"] for v in deletable]
        df = df.drop(delete_indices)
        deleted_count = len(delete_indices)

        # 保存
        df.to_csv(MASTER_CSV, index=False)
        print(f"   ✅ CSV保存完了: {MASTER_CSV}")
        print(f"   修正（クリア）: {fixed_count}件")
        print(f"   削除: {deleted_count}件")

        # ログ出力
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        log_path = LOGS_DIR / f"a1_lifespan_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("=" * 70 + "\n")
            f.write("A1違反修正ログ\n")
            f.write(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 70 + "\n\n")

            f.write("【サマリー】\n")
            f.write(f"  総レコード数: {original_count:,}\n")
            f.write(f"  A1違反検出: {len(violations)}件\n")
            f.write(f"  修正（クリア）: {fixed_count}件\n")
            f.write(f"  削除: {deleted_count}件\n\n")

            if fixable:
                f.write("【修正（birth_year/death_yearクリア）】\n")
                for v in fixable:
                    f.write(f"  {v['episode_id']}: {v['person_name']}\n")
                    f.write(f"    age={v['age']}, old_birth={v['birth_year']}, est_birth={v['estimated_birth_year']}\n")
                f.write("\n")

            if deletable:
                f.write("【削除】\n")
                for v in deletable:
                    f.write(f"  {v['episode_id']}: {v['person_name']}\n")
                    f.write(f"    理由: {v.get('reason', '不明')}\n")

        print(f"   📄 ログ出力: {log_path}")

        return {
            "total_records": original_count,
            "violations_found": len(violations),
            "fixed_count": fixed_count,
            "deleted_count": deleted_count,
            "final_count": len(df),
        }
    else:
        print("\n⚠️ ドライラン: 実際の修正は行いません")
        print("   実行するには --execute オプションを付けてください")

        return {
            "total_records": original_count,
            "violations_found": len(violations),
            "fixable_count": len(fixable),
            "deletable_count": len(deletable),
        }


def main():
    parser = argparse.ArgumentParser(description="A1違反（年齢が寿命超過）修正スクリプト")
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

    result = fix_a1_lifespan_violations(dry_run=dry_run)

    print("\n" + "=" * 70)
    print("📈 サマリー")
    print("=" * 70)
    print(f"   総レコード数: {result['total_records']:,}")
    print(f"   A1違反検出: {result['violations_found']}")

    if dry_run:
        print(f"   修正可能（クリア対象）: {result.get('fixable_count', 0)}")
        print(f"   削除対象: {result.get('deletable_count', 0)}")
    else:
        print(f"   修正（クリア）: {result.get('fixed_count', 0)}")
        print(f"   削除: {result.get('deleted_count', 0)}")
        print(f"   最終レコード数: {result.get('final_count', 0):,}")

    print("=" * 70)

    if args.execute and result.get("violations_found", 0) > 0:
        print("\n✅ 修正完了!")


if __name__ == "__main__":
    main()
