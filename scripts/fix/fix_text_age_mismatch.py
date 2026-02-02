#!/usr/bin/env python3
"""
本文の年齢表記修正スクリプト

C1違反（age field vs text age mismatch）を修正する。
Phase 18でageフィールドは text_year - birth_year で正しく修正済み。
本文の「あなたと同じX歳のとき」をageフィールドに合わせて修正。

Usage:
    python scripts/fix/fix_text_age_mismatch.py --dry-run
    python scripts/fix/fix_text_age_mismatch.py --execute
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


def extract_text_age(episode_text: str) -> int | None:
    """
    本文から「同じX歳」パターンを抽出して年齢を返す

    パターン:
    - 「あなたと同じX歳のとき」
    - 「同じX歳のとき」
    """
    if not episode_text or pd.isna(episode_text):
        return None

    # パターン: 「あなたと同じX歳のとき」または「同じX歳のとき」
    pattern = r"(?:あなたと)?同じ(\d+)歳のとき"
    match = re.search(pattern, str(episode_text))

    if match:
        return int(match.group(1))
    return None


def replace_text_age(episode_text: str, correct_age: int) -> str:
    """
    本文の「同じX歳のとき」を正しい年齢に置換

    Args:
        episode_text: 元の本文
        correct_age: 正しい年齢（ageフィールドの値）

    Returns:
        置換後の本文
    """
    if not episode_text or pd.isna(episode_text):
        return episode_text

    # パターン: 「あなたと同じX歳のとき」または「同じX歳のとき」
    pattern = r"((?:あなたと)?同じ)\d+(歳のとき)"

    def replacer(match):
        return f"{match.group(1)}{correct_age}{match.group(2)}"

    return re.sub(pattern, replacer, str(episode_text))


def fix_text_age_mismatch(dry_run: bool = True, force: bool = False, include_invalid_age: bool = False) -> dict:
    """
    本文の年齢表記をageフィールドに合わせて修正

    Args:
        dry_run: Trueの場合、実際には保存しない（プレビューのみ）
        force: Trueの場合、差分が大きいケース（SUSPICIOUS_DIFF_THRESHOLD超）も修正対象にする
        include_invalid_age: Trueの場合、age > 100のケースも修正対象にする

    Returns:
        修正結果の統計情報
    """
    print("=" * 70)
    print("C1違反修正: 本文の年齢表記をageフィールドに合わせる")
    if force:
        print("⚠️ FORCEモード: 差分が大きいケースも修正対象に含めます")
    if include_invalid_age:
        print("⚠️ INCLUDE-INVALID-AGEモード: age > 100のケースも修正対象に含めます")
    print("=" * 70)

    # CSV読み込み
    print(f"\n📂 CSV読み込み中: {MASTER_CSV}")
    df = pd.read_csv(MASTER_CSV, dtype={"episode_id": str}, low_memory=False)
    print(f"   総レコード数: {len(df):,}")

    # 不整合を検出・修正
    fixes = []
    suspicious = []  # 差分が大きく疑わしいケース
    skipped_no_pattern = 0
    skipped_no_age = 0
    skipped_invalid_age = 0
    matched_ok = 0

    # 差分閾値: これを超えると疑わしいケースとして別扱い
    SUSPICIOUS_DIFF_THRESHOLD = 40

    for idx, row in df.iterrows():
        episode_id = row["episode_id"]
        age_field = row.get("age")
        episode_text = str(row.get("episode_text", "") or "")

        # 本文から年齢を抽出
        text_age = extract_text_age(episode_text)

        if text_age is None:
            skipped_no_pattern += 1
            continue

        if age_field is None or (isinstance(age_field, float) and pd.isna(age_field)):
            skipped_no_age += 1
            continue

        age_field_int = int(float(age_field))

        # 異常なageフィールド値をスキップ
        # Phase 18でbirth_yearが誤っている場合、異常なageになっている
        # include_invalid_age=False の場合: age < 0 or age > 100 をスキップ
        # include_invalid_age=True の場合: age < 0 のみスキップ（age > 100は対象に含める）
        if age_field_int < 0:
            skipped_invalid_age += 1
            continue
        if age_field_int > 100 and not include_invalid_age:
            skipped_invalid_age += 1
            continue

        if text_age == age_field_int:
            matched_ok += 1
            continue

        diff = age_field_int - text_age

        # 差分が大きすぎる場合は疑わしいケースとして別扱い
        # birth_yearが誤っている可能性が高い
        # --force オプション指定時は、疑わしいケースも修正対象にする
        if abs(diff) > SUSPICIOUS_DIFF_THRESHOLD and not force:
            suspicious.append(
                {
                    "episode_id": episode_id,
                    "person_name": row.get("person_name", ""),
                    "text_age": text_age,
                    "age_field": age_field_int,
                    "diff": diff,
                    "birth_year": row.get("birth_year"),
                    "idx": idx,
                }
            )
            continue

        # 不整合: 本文を修正
        new_text = replace_text_age(episode_text, age_field_int)

        fixes.append(
            {
                "episode_id": episode_id,
                "person_name": row.get("person_name", ""),
                "text_age": text_age,
                "correct_age": age_field_int,
                "diff": diff,
                "old_text_snippet": str(episode_text)[:60] if episode_text else "",
                "new_text": new_text,
                "idx": idx,
            }
        )

    # 結果表示
    print("\n📊 検出結果:")
    print(f"   パターンなしでスキップ: {skipped_no_pattern:,}")
    print(f"   ageフィールドなしでスキップ: {skipped_no_age:,}")
    print(f"   異常age(0未満or100超)スキップ: {skipped_invalid_age:,}")
    print(f"   整合OK（修正不要）: {matched_ok:,}")
    print(f"   疑わしいケース（差分>{SUSPICIOUS_DIFF_THRESHOLD}）: {len(suspicious)}")
    print(f"   不整合件数（要修正）: {len(fixes)}")

    if fixes:
        print("\n📋 修正対象一覧:")
        print("-" * 100)
        print(f"   {'No':>3s}  {'episode_id':20s}  {'person_name':20s}  " f"{'text':>4s} → {'age':>4s}  {'diff':>5s}")
        print("-" * 100)
        for i, fix in enumerate(fixes[:50], 1):  # 最大50件表示
            person_name = fix["person_name"][:18] if fix["person_name"] else ""
            print(
                f"   {i:3d}. {fix['episode_id']:20s}  {person_name:20s}  "
                f"{fix['text_age']:4d} → {fix['correct_age']:4d}  ({fix['diff']:+4d})"
            )
        if len(fixes) > 50:
            print(f"   ... 他 {len(fixes) - 50} 件")
        print("-" * 100)

    # 疑わしいケースの警告表示
    if suspicious:
        print(f"\n⚠️ 疑わしいケース（差分>{SUSPICIOUS_DIFF_THRESHOLD}、修正対象外）:")
        print("-" * 110)
        print(
            f"   {'No':>3s}  {'episode_id':20s}  {'person_name':20s}  "
            f"{'text':>4s}  {'age':>4s}  {'diff':>5s}  {'birth_year':>10s}"
        )
        print("-" * 110)
        for i, s in enumerate(suspicious[:20], 1):  # 最大20件表示
            person_name = s["person_name"][:18] if s["person_name"] else ""
            birth = int(s["birth_year"]) if pd.notna(s["birth_year"]) else "?"
            print(
                f"   {i:3d}. {s['episode_id']:20s}  {person_name:20s}  "
                f"{s['text_age']:4d}  {s['age_field']:4d}  ({s['diff']:+4d})  {birth:>10}"
            )
        if len(suspicious) > 20:
            print(f"   ... 他 {len(suspicious) - 20} 件")
        print("-" * 110)
        print("   ※ これらはbirth_yearが誤っている可能性があります。手動確認を推奨。")

    # 修正実行
    if not dry_run and fixes:
        print("\n🔧 修正実行中...")

        # バックアップ作成
        backup_path = create_backup(MASTER_CSV, "text_age_mismatch")
        print(f"   バックアップ作成: {backup_path.name}")

        # 修正適用: 本文を更新
        for fix in fixes:
            df.at[fix["idx"], "episode_text"] = fix["new_text"]

        # 保存
        df.to_csv(MASTER_CSV, index=False)
        print(f"   ✅ CSV保存完了: {MASTER_CSV}")
    elif dry_run:
        print("\n⚠️ ドライラン: 実際の修正は行いません")
        print("   実行するには --execute オプションを付けてください")

    return {
        "total_records": len(df),
        "skipped_no_pattern": skipped_no_pattern,
        "skipped_no_age": skipped_no_age,
        "skipped_invalid_age": skipped_invalid_age,
        "matched_ok": matched_ok,
        "suspicious_count": len(suspicious),
        "fixes_count": len(fixes),
        "fixes": fixes,
        "suspicious": suspicious,
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="C1違反修正: 本文の年齢表記をageフィールドに合わせる")
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
    parser.add_argument(
        "--force",
        action="store_true",
        help="差分が大きいケース（40超）も修正対象に含める",
    )
    parser.add_argument(
        "--include-invalid-age",
        action="store_true",
        help="age > 100のケースも修正対象に含める（デフォルトはスキップ）",
    )

    args = parser.parse_args()

    # --execute が指定された場合は dry_run を False に
    dry_run = not args.execute

    result = fix_text_age_mismatch(dry_run=dry_run, force=args.force, include_invalid_age=args.include_invalid_age)

    print("\n📈 サマリー:")
    print(f"   総レコード数: {result['total_records']:,}")
    print(f"   パターンなしスキップ: {result['skipped_no_pattern']:,}")
    print(f"   ageなしスキップ: {result['skipped_no_age']:,}")
    print(f"   異常ageスキップ: {result['skipped_invalid_age']:,}")
    print(f"   整合OK: {result['matched_ok']:,}")
    print(f"   疑わしいケース: {result['suspicious_count']}")
    print(f"   修正件数: {result['fixes_count']}")

    if args.execute and result["fixes_count"] > 0:
        print("\n✅ 修正完了!")


if __name__ == "__main__":
    main()
