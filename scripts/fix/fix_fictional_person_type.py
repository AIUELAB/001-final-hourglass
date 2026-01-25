#!/usr/bin/env python3
"""
架空キャラクターのperson_type誤分類を修正するスクリプト

RCA-20260125: ナウシカ等の架空キャラがperson_type=REALに誤分類されていた問題を修正

処理内容:
1. CSVを読み込み
2. fictional_characters.pyのリストと照合
3. 誤分類（REAL→FICTIONAL）を修正
4. work_titleが空の場合は作品名を自動設定
5. 修正件数をレポート
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.fictional_characters import (
    get_work_for_character,
    is_fictional_character,
)

# マスターCSVパス
MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"


def detect_misclassified_fictional(df: pd.DataFrame) -> pd.DataFrame:
    """
    person_type=REALだが架空キャラクターと判定されるレコードを検出

    Args:
        df: エピソードDataFrame

    Returns:
        誤分類されたレコードのDataFrame
    """
    misclassified = []

    for idx, row in df.iterrows():
        person_name = str(row.get("person_name", ""))
        person_type = str(row.get("person_type", "")).upper()

        # person_type=REALだが架空キャラクターリストに含まれる場合
        if "FICTIONAL" not in person_type and is_fictional_character(person_name):
            misclassified.append(idx)

    return df.loc[misclassified].copy()


def fix_person_type(df: pd.DataFrame, dry_run: bool = True) -> tuple[pd.DataFrame, dict]:
    """
    person_type誤分類を修正

    Args:
        df: エピソードDataFrame
        dry_run: Trueの場合は変更を適用しない

    Returns:
        (修正後DataFrame, 修正レポート)
    """
    report: dict = {
        "total_episodes": len(df),
        "misclassified_count": 0,
        "fixed_person_type": 0,
        "fixed_work_title": 0,
        "details": [],
    }

    df_copy = df.copy()

    for idx, row in df.iterrows():
        person_name = str(row.get("person_name", ""))
        person_type = str(row.get("person_type", "")).upper()
        work_title = str(row.get("work_title", "")) if pd.notna(row.get("work_title")) else ""

        # 架空キャラクター判定
        if not is_fictional_character(person_name):
            continue

        changes = []

        # person_typeがFICTIONALでない場合は修正
        if "FICTIONAL" not in person_type:
            if not dry_run:
                df_copy.at[idx, "person_type"] = "FICTIONAL"
            changes.append(f"person_type: {person_type} → FICTIONAL")
            report["fixed_person_type"] += 1

        # work_titleが空の場合は作品名を設定
        if not work_title:
            work = get_work_for_character(person_name)
            if work:
                if not dry_run:
                    df_copy.at[idx, "work_title"] = work
                changes.append(f"work_title: (空) → {work}")
                report["fixed_work_title"] += 1

        if changes:
            report["misclassified_count"] += 1
            report["details"].append(
                {
                    "episode_id": row.get("episode_id", "unknown"),
                    "person_name": person_name,
                    "age": row.get("age", 0),
                    "changes": changes,
                }
            )

    return df_copy, report


def main():
    parser = argparse.ArgumentParser(description="架空キャラクターのperson_type誤分類を修正")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="変更を適用せずにレポートのみ表示 (デフォルト: True)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="実際に変更を適用する",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=MASTER_CSV,
        help=f"対象CSVファイル (デフォルト: {MASTER_CSV})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="詳細表示の最大件数 (デフォルト: 50)",
    )

    args = parser.parse_args()

    dry_run = not args.execute

    # CSVファイル確認
    if not args.csv.exists():
        print(f"❌ CSVファイルが見つかりません: {args.csv}")
        sys.exit(1)

    print(f"📂 対象CSV: {args.csv}")
    print(f"🔧 モード: {'dry-run（変更なし）' if dry_run else '⚠️ 実行（変更適用）'}")
    print()

    # CSV読み込み
    try:
        df = pd.read_csv(args.csv, encoding="utf-8-sig")
    except FileNotFoundError:
        print(f"❌ CSVファイルが見つかりません: {args.csv}")
        sys.exit(1)
    except pd.errors.EmptyDataError:
        print(f"❌ CSVファイルが空です: {args.csv}")
        sys.exit(1)
    except pd.errors.ParserError as e:
        print(f"❌ CSV解析エラー: {e}")
        sys.exit(1)
    print(f"📊 総エピソード数: {len(df):,}")
    print()

    # 修正実行
    df_fixed, report = fix_person_type(df, dry_run=dry_run)

    # レポート表示
    print("=" * 60)
    print("📋 修正レポート")
    print("=" * 60)
    print(f"  誤分類検出数: {report['misclassified_count']}")
    print(f"  person_type修正: {report['fixed_person_type']}")
    print(f"  work_title補完: {report['fixed_work_title']}")
    print()

    if report["details"]:
        print("📝 詳細 (最大{}件):".format(args.limit))
        for i, detail in enumerate(report["details"][: args.limit]):
            print(f"  [{i + 1}] {detail['person_name']} ({detail['age']}歳)")
            print(f"      episode_id: {detail['episode_id']}")
            for change in detail["changes"]:
                print(f"      ✏️ {change}")
            print()

        if len(report["details"]) > args.limit:
            print(f"  ... 他 {len(report['details']) - args.limit}件")
            print()

    # 実行モードの場合はCSV保存
    if not dry_run and report["misclassified_count"] > 0:
        # バックアップ
        backup_path = args.csv.with_suffix(".csv.bak")
        df.to_csv(backup_path, index=False, encoding="utf-8-sig")
        print(f"💾 バックアップ: {backup_path}")

        # 修正後CSV保存
        df_fixed.to_csv(args.csv, index=False, encoding="utf-8-sig")
        print(f"✅ 修正完了: {args.csv}")
    elif dry_run and report["misclassified_count"] > 0:
        print("💡 実際に修正を適用するには --execute オプションを使用してください")
    else:
        print("✨ 修正対象なし")


if __name__ == "__main__":
    main()
