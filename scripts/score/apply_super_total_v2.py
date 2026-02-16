#!/usr/bin/env python3
"""
super_total_score v2.1.0 一括再計算スクリプト

全エピソードのsuper_total_scoreをv2.1.0設定で再計算し、
マスターCSVを更新する。

使用方法:
    # ドライラン（変更なし、統計のみ）
    python scripts/score/apply_super_total_v2.py --dry-run

    # 実行（CSVを更新）
    python scripts/score/apply_super_total_v2.py

    # カスタム設定ファイル使用
    python scripts/score/apply_super_total_v2.py --config configs/super_total_score/custom.json

    # サンプルのみ確認
    python scripts/score/apply_super_total_v2.py --dry-run --limit 1000
"""

import argparse
import csv
import logging
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from tqdm import tqdm

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.score.super_total_scorer import SuperTotalConfig, SuperTotalScorer

# パス設定
CSV_PATH = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
BACKUP_DIR = PROJECT_ROOT / "preserved/data/backups"
DEFAULT_CONFIG = PROJECT_ROOT / "configs/super_total_score/v2.2.0.json"

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def safe_float(value, default: float = 0.0) -> float:
    """安全なfloat変換

    Args:
        value: 変換する値
        default: 変換失敗時のデフォルト値

    Returns:
        float値またはデフォルト値
    """
    if pd.isna(value) or value == "" or value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def create_backup(timestamp: str) -> Path:
    """バックアップを作成

    Args:
        timestamp: タイムスタンプ文字列

    Returns:
        バックアップファイルパス
    """
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_path = BACKUP_DIR / f"MASTER_EPISODES_CURRENT_super_total_v2_{timestamp}.csv"

    # 元のCSVをコピー
    df_backup = pd.read_csv(CSV_PATH, dtype=str)
    df_backup.to_csv(backup_path, index=False, quoting=csv.QUOTE_ALL)

    return backup_path


def calculate_statistics(scores: list) -> dict:
    """スコアの統計を計算

    Args:
        scores: スコアのリスト

    Returns:
        統計情報の辞書
    """
    if not scores:
        return {"mean": 0.0, "median": 0.0, "max": 0.0}

    import numpy as np

    scores_array = np.array(scores)
    return {
        "mean": float(np.mean(scores_array)),
        "median": float(np.median(scores_array)),
        "max": float(np.max(scores_array)),
    }


def format_number(num: float) -> str:
    """数値をカンマ区切りでフォーマット

    Args:
        num: フォーマットする数値

    Returns:
        フォーマット済み文字列
    """
    return f"{num:,.0f}"


def apply_super_total_v2(config_path: Path, dry_run: bool = False, limit: int | None = None):
    """super_total_score v2.1.0を全件再計算

    Args:
        config_path: 設定ファイルパス
        dry_run: ドライランモード（True: CSV更新しない）
        limit: 処理件数制限（None: 全件）
    """
    print("=" * 60)
    print("super_total_score v2.1.0 再計算")
    print("=" * 60)
    print()

    # 設定ファイル読み込み
    if not config_path.exists():
        logger.error(f"設定ファイルが見つかりません: {config_path}")
        return

    config = SuperTotalConfig.from_json(config_path)

    print(f"設定: {config.version} ({config_path.relative_to(PROJECT_ROOT)})")
    print(
        f"  celebrity: {config.weight_celebrity:.2f}, "
        f"episode_fame: {config.weight_episode_fame:.2f}, "
        f"quality: {config.weight_quality:.2f}, "
        f"historical: {config.weight_historical:.2f}"
    )
    print(f"  achievement_boost_multiplier: {config.achievement_boost_multiplier}")
    print(f"  iconic_boost_multiplier: {config.iconic_boost_multiplier}")
    print()

    # CSV読み込み
    if not CSV_PATH.exists():
        logger.error(f"CSVファイルが見つかりません: {CSV_PATH}")
        return

    df = pd.read_csv(CSV_PATH, dtype=str)
    total_count = len(df)

    # 処理件数制限
    if limit and limit < total_count:
        df = df.head(limit)
        logger.info(f"処理件数を{limit:,}件に制限")

    print(f"データ読み込み: {len(df):,}件")
    print()

    # エピソードをdict化
    episodes = df.to_dict("records")

    # SuperTotalScorer初期化（正規化パラメータ自動計算）
    logger.info("正規化パラメータを計算中...")
    scorer = SuperTotalScorer(episodes, config=config)

    print("正規化パラメータ:")
    print(
        f"  celebrity_score_v2: "
        f"median={scorer.norm_params.celebrity_median:.1f}, "
        f"iqr={scorer.norm_params.celebrity_iqr:.1f}"
    )
    print(
        f"  episode_fame_v6: " f"median={scorer.norm_params.fame_median:.1f}, " f"iqr={scorer.norm_params.fame_iqr:.1f}"
    )
    print(
        f"  episode_importance: "
        f"median={scorer.norm_params.importance_median:.1f}, "
        f"iqr={scorer.norm_params.importance_iqr:.1f}"
    )
    print()

    # 旧スコアの収集
    old_scores = []
    for _, row in df.iterrows():
        val = safe_float(row.get("super_total_score"))
        if val > 0:
            old_scores.append(val)

    # 全件再計算
    print("再計算中...")
    new_scores = []
    gate_failed_count = 0
    top_episodes = []  # Top 20用

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Processing"):
        episode = row.to_dict()
        result = scorer.calculate(episode)

        if result.passed_gate:
            new_scores.append(result.score)
            # Top 20候補に追加
            top_episodes.append(
                {
                    "person_name": row.get("person_name", ""),
                    "age": safe_float(row.get("age"), 0),
                    "old_score": safe_float(row.get("super_total_score")),
                    "new_score": result.score,
                    "episode_id": row.get("episode_id", ""),
                }
            )
        else:
            new_scores.append(0)
            gate_failed_count += 1

        # DataFrameに反映（dry-run以外）
        if not dry_run:
            df.loc[idx, "super_total_score"] = result.score

    print()

    # 統計比較
    old_stats = calculate_statistics(old_scores)
    new_stats = calculate_statistics([s for s in new_scores if s > 0])

    print("統計比較:")
    print(f"           {'旧スコア':>12}      {'新スコア':>12}      変化")
    print(
        f"  平均:    {format_number(old_stats['mean']):>12}      {format_number(new_stats['mean']):>12}      {((new_stats['mean'] - old_stats['mean']) / old_stats['mean'] * 100):+.1f}%"
    )
    print(
        f"  中央値:  {format_number(old_stats['median']):>12}      {format_number(new_stats['median']):>12}      {((new_stats['median'] - old_stats['median']) / old_stats['median'] * 100):+.1f}%"
    )
    print(
        f"  最大:    {format_number(old_stats['max']):>12}      {format_number(new_stats['max']):>12}      {((new_stats['max'] - old_stats['max']) / old_stats['max'] * 100):+.1f}%"
    )
    print()

    # ゲート情報
    print(f"ゲート不通過: {gate_failed_count:,}件 ({gate_failed_count / len(df) * 100:.1f}%)")
    print()

    # Top 20表示（新スコア降順）
    top_episodes.sort(key=lambda x: x["new_score"], reverse=True)
    print("Top 20:")
    for i, ep in enumerate(top_episodes[:20], 1):
        old_score = ep["old_score"]
        new_score = ep["new_score"]

        if old_score > 0:
            change_pct = ((new_score - old_score) / old_score) * 100
            change_str = f"{change_pct:+.1f}%"
        else:
            change_str = "N/A"

        age_str = f"{ep['age']:.0f}歳" if ep["age"] > 0 else "不明"
        print(
            f"  {i:2d}. {ep['person_name']}（{age_str}）: "
            f"{format_number(old_score)} → {format_number(new_score)} ({change_str})"
        )
    print()

    # バックアップ作成・CSV保存
    if dry_run:
        print("⚠️  ドライランモード: CSV更新は行いません")
    else:
        # バックアップ作成
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = create_backup(timestamp)
        print(f"バックアップ作成: {backup_path.relative_to(PROJECT_ROOT)}")

        # CSV保存
        df.to_csv(CSV_PATH, index=False, quoting=csv.QUOTE_ALL)
        print(f"CSV保存完了: {CSV_PATH.relative_to(PROJECT_ROOT)}")

    print()
    print("=" * 60)
    print("処理完了")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="super_total_score v2.1.0を全件再計算",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # ドライラン
  python scripts/score/apply_super_total_v2.py --dry-run

  # 実行
  python scripts/score/apply_super_total_v2.py

  # カスタム設定
  python scripts/score/apply_super_total_v2.py --config configs/super_total_score/custom.json

  # サンプル確認
  python scripts/score/apply_super_total_v2.py --dry-run --limit 1000
        """,
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help=f"設定ファイルパス（デフォルト: {DEFAULT_CONFIG.relative_to(PROJECT_ROOT)}）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="ドライランモード（CSV更新しない）",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="処理件数制限（テスト用）",
    )

    args = parser.parse_args()

    apply_super_total_v2(
        config_path=args.config,
        dry_run=args.dry_run,
        limit=args.limit,
    )


if __name__ == "__main__":
    main()
