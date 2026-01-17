#!/usr/bin/env python3
"""
person_type正規化スクリプト

MASTER_EPISODES_CURRENT.csvのperson_type列を正規化する。

正規化ルール:
    "REAL", "Real", "real", "R" → "REAL"
    "FICTIONAL", "Fictional", "fictional", "F" → "FICTIONAL"
    "", None, NaN, その他 → "UNKNOWN"（要確認対象）

Usage:
    # dry-run（統計確認）
    python scripts/fix/normalize_person_type.py --dry-run

    # 実行
    python scripts/fix/normalize_person_type.py --execute
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"

# 正規化マッピング
PERSON_TYPE_MAPPING = {
    # REAL系
    "REAL": "REAL",
    "Real": "REAL",
    "real": "REAL",
    "R": "REAL",
    # FICTIONAL系
    "FICTIONAL": "FICTIONAL",
    "Fictional": "FICTIONAL",
    "fictional": "FICTIONAL",
    "F": "FICTIONAL",
}

# 有効な正規化後の値
VALID_TYPES = {"REAL", "FICTIONAL"}


def normalize_person_type(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """person_type列を正規化する"""
    df = df.copy()

    stats = {
        "before": {},
        "after": {},
        "changes": {},
        "unknown_values": [],
    }

    # 正規化前の統計
    before_counts = df["person_type"].value_counts(dropna=False)
    for val, count in before_counts.items():
        key = str(val) if pd.notna(val) else "NaN"
        stats["before"][key] = int(count)

    # 正規化処理
    def normalize_value(val):
        if pd.isna(val) or val == "":
            return "UNKNOWN"
        val_str = str(val).strip()
        if val_str in PERSON_TYPE_MAPPING:
            return PERSON_TYPE_MAPPING[val_str]
        return "UNKNOWN"

    original_values = df["person_type"].copy()
    df["person_type"] = df["person_type"].apply(normalize_value)

    # 変更統計
    changed_mask = original_values.fillna("__NAN__").astype(str) != df["person_type"]
    for idx in df[changed_mask].index:
        old_val = original_values.loc[idx]
        old_key = str(old_val) if pd.notna(old_val) else "NaN"
        new_val = df.loc[idx, "person_type"]
        change_key = f"{old_key} → {new_val}"
        stats["changes"][change_key] = stats["changes"].get(change_key, 0) + 1

    # 正規化後の統計
    after_counts = df["person_type"].value_counts(dropna=False)
    for val, count in after_counts.items():
        key = str(val) if pd.notna(val) else "NaN"
        stats["after"][key] = int(count)

    # UNKNOWN対象の元値を収集
    unknown_sources = original_values[df["person_type"] == "UNKNOWN"].value_counts(dropna=False)
    for val, count in unknown_sources.items():
        key = str(val) if pd.notna(val) else "NaN"
        stats["unknown_values"].append((key, int(count)))

    return df, stats


def print_report(df: pd.DataFrame, stats: dict):
    """レポートを出力"""
    total = len(df)

    print()
    print("=" * 40)
    print("📊 person_type正規化")
    print("=" * 40)
    print(f"総エピソード: {total:,}件")
    print()

    # 正規化後の統計
    print("【正規化後の分布】")
    for ptype in ["REAL", "FICTIONAL", "UNKNOWN"]:
        count = stats["after"].get(ptype, 0)
        pct = count / total * 100 if total > 0 else 0
        print(f"  {ptype}: {count:,}件 ({pct:.1f}%)")
    print()

    # 変更内容
    if stats["changes"]:
        print("【変更内容】")
        for change, count in sorted(stats["changes"].items(), key=lambda x: -x[1]):
            print(f"  {change}: {count:,}件")
        total_changes = sum(stats["changes"].values())
        print(f"  合計変更: {total_changes:,}件")
        print()

    # UNKNOWN対象の詳細
    if stats["unknown_values"]:
        print("【UNKNOWN対象の元値（要確認）】")
        for val, count in sorted(stats["unknown_values"], key=lambda x: -x[1]):
            print(f"  {val}: {count:,}件")
        print()


def main():
    parser = argparse.ArgumentParser(description="person_type正規化")
    parser.add_argument("--dry-run", action="store_true", help="統計確認のみ")
    parser.add_argument("--execute", action="store_true", help="実行")
    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        parser.print_help()
        return

    # 読み込み
    logger.info(f"読み込み: {MASTER_CSV}")
    df = pd.read_csv(MASTER_CSV, encoding="utf-8-sig", low_memory=False)
    logger.info(f"総レコード: {len(df):,}件")

    # 正規化
    df_normalized, stats = normalize_person_type(df)

    # レポート出力
    print_report(df_normalized, stats)

    total_changes = sum(stats["changes"].values())

    if args.dry_run:
        print(f"🔍 dry-run完了（変更予定: {total_changes:,}件）")
        return

    if args.execute:
        if total_changes == 0:
            print("✅ 変更なし")
            return

        # バックアップ
        backup_dir = PROJECT_ROOT / "preserved" / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = backup_dir / f"MASTER_pre_person_type_norm_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(backup_path, index=False, encoding="utf-8-sig")
        logger.info(f"バックアップ: {backup_path}")

        # 保存
        df_normalized.to_csv(MASTER_CSV, index=False, encoding="utf-8-sig")
        logger.info(f"保存完了: {MASTER_CSV}")
        print(f"✅ 正規化完了（変更: {total_changes:,}件）")


if __name__ == "__main__":
    main()
