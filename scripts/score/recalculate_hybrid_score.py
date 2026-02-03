#!/usr/bin/env python3
"""
hybrid_score再計算スクリプト

super_total_scoreとdesirability_scoreを組み合わせたハイブリッドスコアを計算。

Usage:
    python scripts/score/recalculate_hybrid_score.py [--dry-run] [--limit N]

Options:
    --dry-run   実際にCSVを更新せず、計算結果のみ表示
    --limit N   処理するエピソード数を制限（テスト用）

計算式:
    hybrid_score = super_total_score * 0.8 + desirability_score * 0.2

出力カラム:
    - hybrid_score: ハイブリッドスコア（0〜1,000,000）
"""

import argparse
import csv
import logging
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from tqdm import tqdm

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# パス設定
CSV_PATH = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
BACKUP_DIR = PROJECT_ROOT / "preserved/data/backups"

# 重み設定
WEIGHT_SUPER_TOTAL = 0.8
WEIGHT_DESIRABILITY = 0.2


def create_backup(df: pd.DataFrame) -> Path:
    """バックアップを作成"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"MASTER_EPISODES_CURRENT_hybrid_{timestamp}.csv"
    df.to_csv(backup_path, index=False, quoting=csv.QUOTE_ALL)
    logger.info(f"バックアップ作成: {backup_path}")
    return backup_path


def safe_float(value, default: float = 0.0) -> float:
    """安全にfloatに変換（欠損値は0）"""
    if pd.isna(value) or value == "" or value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def calculate_hybrid_score(row: pd.Series) -> float:
    """hybrid_scoreを計算

    Args:
        row: エピソードの行データ

    Returns:
        hybrid_score: ハイブリッドスコア
    """
    super_total = safe_float(row.get("super_total_score"), 0.0)
    desirability = safe_float(row.get("desirability_score"), 0.0)

    hybrid = super_total * WEIGHT_SUPER_TOTAL + desirability * WEIGHT_DESIRABILITY
    return round(hybrid, 2)


def calculate_statistics(scores: list) -> dict:
    """スコアの統計を計算"""
    if not scores:
        return {}

    import numpy as np

    scores_array = np.array([s for s in scores if s > 0])
    if len(scores_array) == 0:
        return {}

    return {
        "count": len(scores_array),
        "mean": round(float(np.mean(scores_array)), 2),
        "std": round(float(np.std(scores_array)), 2),
        "min": round(float(np.min(scores_array)), 2),
        "max": round(float(np.max(scores_array)), 2),
        "median": round(float(np.median(scores_array)), 2),
    }


def parse_args():
    """コマンドライン引数をパース"""
    parser = argparse.ArgumentParser(description="hybrid_score再計算")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="実際にCSVを更新せず、結果のみ表示",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="処理するエピソード数を制限（テスト用）",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    print("=" * 60)
    print("hybrid_score 再計算")
    print("=" * 60)
    print()

    # 計算式表示
    print("計算式:")
    print(f"  hybrid_score = super_total_score * {WEIGHT_SUPER_TOTAL} + desirability_score * {WEIGHT_DESIRABILITY}")
    print()

    # データ読み込み
    logger.info("データ読み込み中...")
    if not CSV_PATH.exists():
        logger.error(f"CSVファイルが見つかりません: {CSV_PATH}")
        sys.exit(1)

    df = pd.read_csv(CSV_PATH, dtype=str)
    total_count = len(df)
    logger.info(f"読み込み完了: {total_count:,}件")

    # 制限がある場合は絞り込み
    if args.limit:
        df = df.head(args.limit)
        logger.info(f"制限適用: {len(df):,}件")

    # 全エピソード再計算
    logger.info("全エピソード再計算中...")
    hybrid_scores = []
    missing_super_total = 0
    missing_desirability = 0

    for _, row in tqdm(df.iterrows(), total=len(df), desc="計算中", unit="件"):
        # 欠損チェック
        if pd.isna(row.get("super_total_score")) or row.get("super_total_score") == "":
            missing_super_total += 1
        if pd.isna(row.get("desirability_score")) or row.get("desirability_score") == "":
            missing_desirability += 1

        hybrid = calculate_hybrid_score(row)
        hybrid_scores.append(hybrid)

    logger.info(f"完了: {len(df):,}件処理")

    # 欠損値統計
    print()
    print("欠損値統計:")
    print(f"  super_total_score欠損: {missing_super_total:,}件")
    print(f"  desirability_score欠損: {missing_desirability:,}件")

    # スコア統計
    print()
    print("hybrid_score統計:")
    stats = calculate_statistics(hybrid_scores)
    if stats:
        print(f"  件数: {stats['count']:,}件（スコア>0）")
        print(f"  平均: {stats['mean']:,.2f}")
        print(f"  標準偏差: {stats['std']:,.2f}")
        print(f"  最小: {stats['min']:,.2f}")
        print(f"  最大: {stats['max']:,.2f}")
        print(f"  中央値: {stats['median']:,.2f}")
    else:
        print("  有効なスコアがありません")

    # スコア更新
    df["hybrid_score"] = hybrid_scores

    # Top 20表示
    print()
    print("Top 20 確認:")
    df_sorted = df.copy()
    df_sorted["hybrid_score"] = pd.to_numeric(df_sorted["hybrid_score"], errors="coerce")
    top20 = df_sorted.nlargest(20, "hybrid_score")
    for i, (_, row) in enumerate(top20.iterrows(), 1):
        name = row.get("person_name", "?")
        age = row.get("age", "?")
        hybrid = row.get("hybrid_score") or 0
        super_total = safe_float(row.get("super_total_score"), 0)
        desirability = safe_float(row.get("desirability_score"), 0)
        episode_text = str(row.get("episode_text", ""))[:30]
        print(
            f"  {i:2}. {name}（{age}歳）: {float(hybrid):,.0f} (ST:{super_total:,.0f} + DS:{desirability:,.0f}) | {episode_text}..."
        )

    if args.dry_run:
        print()
        print("ドライラン: CSVは更新されません")
    else:
        # バックアップ作成
        print()
        original_df = pd.read_csv(CSV_PATH, dtype=str)
        create_backup(original_df)

        # CSV保存
        logger.info("CSV保存中...")
        df.to_csv(CSV_PATH, index=False, quoting=csv.QUOTE_ALL)
        logger.info(f"保存完了: {CSV_PATH}")

    print()
    print("=" * 60)
    print("完了")
    print("=" * 60)


if __name__ == "__main__":
    main()
