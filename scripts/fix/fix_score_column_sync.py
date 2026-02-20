#!/usr/bin/env python3
"""
スコアカラム同期スクリプト

llm_xxx_scoreカラムと日本語名カラムの不整合を修復。
llm_xxx_scoreに値があり、日本語名カラムがNaNの場合、値をコピー。
"""

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
    import shutil

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"MASTER_EPISODES_{operation}_{timestamp}.csv"
    backup_path = BACKUP_DIR / backup_name
    shutil.copy2(csv_path, backup_path)
    return backup_path


# カラムマッピング: 日本語名 -> llm_xxx_score
SCORE_MAPPING = {
    "memorability_score": "llm_memorability_score",
    "empathy_score": "llm_empathy_score",
    "surprise_score": "llm_surprise_score",
    "generation_quality_score": "llm_generation_quality_score",
    "educational_value": "llm_educational_value",
    "story_quality": "llm_story_quality",
    "factual_density": "llm_factual_density",
}


def sync_score_columns(
    csv_path: Path = MASTER_CSV,
    dry_run: bool = True,
    verbose: bool = False,
) -> dict:
    """
    スコアカラムを同期

    Args:
        csv_path: CSVファイルパス
        dry_run: Trueの場合、変更を保存しない
        verbose: 詳細ログを出力

    Returns:
        同期結果のサマリー
    """
    print("=" * 60)
    print("スコアカラム同期")
    print("=" * 60)
    print(f"対象: {csv_path}")
    print(f"モード: {'dry-run' if dry_run else '実行'}")
    print()

    # バックアップ作成
    if not dry_run:
        backup_path = create_backup(csv_path, "score_sync")
        print(f"バックアップ: {backup_path}")

    # CSV読み込み
    df = pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    print(f"総エピソード数: {len(df)}")

    results = {
        "total": len(df),
        "synced_episodes": 0,
        "synced_values": 0,
        "by_column": {},
    }

    # 各カラムを同期
    for jp_col, llm_col in SCORE_MAPPING.items():
        if llm_col not in df.columns:
            print(f"⚠️ {llm_col} カラムが存在しません")
            continue

        if jp_col not in df.columns:
            print(f"⚠️ {jp_col} カラムが存在しません")
            continue

        # 日本語カラムがNaNでllmカラムに値がある行を特定
        mask = df[jp_col].isna() & df[llm_col].notna()
        count = mask.sum()

        if count > 0:
            results["by_column"][jp_col] = count
            results["synced_values"] += count

            if verbose:
                print(f"  {jp_col}: {count}件を同期")

            # 値をコピー
            df.loc[mask, jp_col] = df.loc[mask, llm_col]

    # 同期されたエピソード数をカウント
    # (少なくとも1つのカラムが同期されたエピソード)
    episode_ids_synced = set()
    for jp_col, llm_col in SCORE_MAPPING.items():
        if jp_col in df.columns and llm_col in df.columns:
            # 元のデータを再読み込みして比較
            df_orig = pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
            mask = df_orig[jp_col].isna() & df_orig[llm_col].notna()
            episode_ids_synced.update(df.loc[mask, "episode_id"].tolist())

    results["synced_episodes"] = len(episode_ids_synced)

    # サマリー出力
    print()
    print("=" * 60)
    print("同期サマリー")
    print("=" * 60)
    print(f"同期されたエピソード数: {results['synced_episodes']}")
    print(f"同期された値の総数: {results['synced_values']}")

    if results["by_column"]:
        print()
        print("カラム別:")
        for col, count in results["by_column"].items():
            print(f"  {col}: {count}件")

    # 保存
    if not dry_run and results["synced_values"] > 0:
        print()
        print("保存中...")
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print("保存完了")
    elif results["synced_values"] == 0:
        print()
        print("同期対象なし")

    return results


def main():
    """メイン処理"""
    import argparse

    parser = argparse.ArgumentParser(description="スコアカラム同期")
    parser.add_argument("--dry-run", action="store_true", help="dry-runモード")
    parser.add_argument("--verbose", action="store_true", help="詳細ログ")
    parser.add_argument(
        "--csv",
        default=str(MASTER_CSV),
        help="対象CSVファイル",
    )
    args = parser.parse_args()

    sync_score_columns(
        csv_path=Path(args.csv),
        dry_run=args.dry_run,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    main()
