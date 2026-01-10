#!/usr/bin/env python3
"""
CSVカラム整理スクリプト

重複カラムの統合と不要カラムの削除を行う。
75カラム → 64カラム（11カラム削減）
"""

import shutil
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
BACKUP_DIR = PROJECT_ROOT / "preserved" / "backups"

# 削除対象カラム（11個）
DELETE_COLUMNS = [
    # 重複カラム（LLM版に統合）
    "memorability_score",  # → llm_memorability_score
    "empathy_score",  # → llm_empathy_score
    "surprise_score",  # → llm_surprise_score
    "generation_quality_score",  # → llm_generation_quality_score
    "educational_value",  # → llm_educational_value
    "story_quality",  # → llm_storytelling_quality
    "factual_density",  # → llm_factual_density
    # 不要カラム
    "slot",  # 用途不明
    "tier",  # 用途不明
    "week",  # tier と重複
    "highlight_selection_method",  # ほぼ「none」
]

# カラム名変更（LLM版を標準名に）
RENAME_COLUMNS = {
    "llm_memorability_score": "memorability_score",
    "llm_empathy_score": "empathy_score",
    "llm_surprise_score": "surprise_score",
    "llm_generation_quality_score": "generation_quality_score",
    "llm_educational_value": "educational_value",
    "llm_storytelling_quality": "storytelling_quality",
    "llm_factual_density": "factual_density",
}


def create_backup(csv_path: Path, operation: str) -> Path:
    """バックアップを作成"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"MASTER_EPISODES_{operation}_{timestamp}.csv"
    backup_path = BACKUP_DIR / backup_name
    shutil.copy2(csv_path, backup_path)
    return backup_path


def reorganize_columns(
    csv_path: Path = MASTER_CSV,
    dry_run: bool = True,
) -> dict:
    """
    CSVカラムを整理

    Args:
        csv_path: CSVファイルパス
        dry_run: Trueの場合、変更を保存しない

    Returns:
        整理結果のサマリー
    """
    print("=" * 60)
    print("CSVカラム整理")
    print("=" * 60)
    print(f"対象: {csv_path}")
    print(f"モード: {'dry-run' if dry_run else '実行'}")
    print()

    # CSV読み込み
    df = pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    original_columns = list(df.columns)
    print(f"元のカラム数: {len(original_columns)}")
    print(f"レコード数: {len(df)}")
    print()

    results = {
        "original_columns": len(original_columns),
        "deleted_columns": [],
        "renamed_columns": {},
        "final_columns": 0,
    }

    # 1. 重複カラムの値をLLM版にマージ（LLM版が空の場合のみ）
    print("=== カラム統合 ===")
    merge_pairs = [
        ("memorability_score", "llm_memorability_score"),
        ("empathy_score", "llm_empathy_score"),
        ("surprise_score", "llm_surprise_score"),
        ("generation_quality_score", "llm_generation_quality_score"),
        ("educational_value", "llm_educational_value"),
        ("story_quality", "llm_storytelling_quality"),
        ("factual_density", "llm_factual_density"),
    ]

    for old_col, llm_col in merge_pairs:
        if old_col in df.columns and llm_col in df.columns:
            # LLM版が空/NaN の場合、元のカラムの値を使用
            mask = df[llm_col].isna() | (df[llm_col] == 0)
            filled_count = mask.sum()
            if filled_count > 0:
                df.loc[mask, llm_col] = df.loc[mask, old_col]
                print(f"  {old_col} → {llm_col}: {filled_count}件補完")

    # 2. 不要カラムを削除
    print()
    print("=== カラム削除 ===")
    for col in DELETE_COLUMNS:
        if col in df.columns:
            df = df.drop(columns=[col])
            results["deleted_columns"].append(col)
            print(f"  ✓ 削除: {col}")
        else:
            print(f"  - スキップ（存在しない）: {col}")

    # 3. カラム名を変更（LLM版を標準名に）
    print()
    print("=== カラム名変更 ===")
    for old_name, new_name in RENAME_COLUMNS.items():
        if old_name in df.columns:
            df = df.rename(columns={old_name: new_name})
            results["renamed_columns"][old_name] = new_name
            print(f"  ✓ {old_name} → {new_name}")

    results["final_columns"] = len(df.columns)

    # サマリー出力
    print()
    print("=" * 60)
    print("整理サマリー")
    print("=" * 60)
    print(f"削除カラム: {len(results['deleted_columns'])}個")
    print(f"名前変更: {len(results['renamed_columns'])}個")
    print(f"最終カラム数: {results['final_columns']}個")
    print(
        f"削減: {results['original_columns']} → {results['final_columns']} ({results['original_columns'] - results['final_columns']}カラム削減)"
    )

    # 最終カラム一覧
    print()
    print("=== 最終カラム一覧 ===")
    for i, col in enumerate(df.columns, 1):
        print(f"  {i:2d}. {col}")

    # 保存
    if not dry_run:
        # バックアップ作成
        backup_path = create_backup(csv_path, "column_reorg")
        print()
        print(f"バックアップ: {backup_path}")

        print("保存中...")
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print("✓ 保存完了")

    return results


def main():
    """メイン処理"""
    import argparse

    parser = argparse.ArgumentParser(description="CSVカラム整理")
    parser.add_argument("--dry-run", action="store_true", help="dry-runモード")
    parser.add_argument(
        "--csv",
        default=str(MASTER_CSV),
        help="対象CSVファイル",
    )
    args = parser.parse_args()

    reorganize_columns(
        csv_path=Path(args.csv),
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
