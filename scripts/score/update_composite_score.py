#!/usr/bin/env python3
"""
composite_score更新スクリプト

7軸スコアから改善版composite_score（0-1000スケール）を計算し、
CSVファイルを更新する。

使用方法:
    # ドライラン（変更なし、統計のみ）
    python scripts/update_composite_score.py

    # 実行（CSVを更新）
    python scripts/update_composite_score.py --execute

    # 特定のエピソードのみ
    python scripts/update_composite_score.py --episode EP-000001
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.utils.score_calculator import (
    SEVEN_AXIS_FIELDS,
    calculate_enhanced_composite_score,
    get_score_grade,
)

# CSVファイルパス
CSV_PATH = Path(__file__).parent.parent / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
BACKUP_DIR = Path(__file__).parent.parent / "preserved" / "data" / "backups"


def create_backup(df: pd.DataFrame) -> Path:
    """バックアップを作成"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"MASTER_EPISODES_CURRENT_{timestamp}.csv"
    df.to_csv(backup_path, index=False, encoding="utf-8-sig")
    print(f"📦 バックアップ作成: {backup_path}")
    return backup_path


def calculate_statistics(scores: list) -> dict:
    """スコアの統計を計算"""
    if not scores:
        return {}

    import numpy as np

    scores_array = np.array(scores)
    return {
        "count": len(scores),
        "mean": round(float(np.mean(scores_array)), 1),
        "std": round(float(np.std(scores_array)), 1),
        "min": round(float(np.min(scores_array)), 1),
        "max": round(float(np.max(scores_array)), 1),
        "q25": round(float(np.percentile(scores_array, 25)), 1),
        "median": round(float(np.percentile(scores_array, 50)), 1),
        "q75": round(float(np.percentile(scores_array, 75)), 1),
    }


def get_grade_distribution(scores: list) -> dict:
    """グレード分布を取得"""
    grades = {"S": 0, "A": 0, "B": 0, "C": 0, "D": 0, "E": 0}
    for score in scores:
        grade = get_score_grade(score)
        grades[grade] += 1
    return grades


def update_composite_scores(execute: bool = False, episode_id: str = None):
    """composite_scoreを更新"""
    print("=" * 80)
    print("📊 composite_score更新スクリプト（0-1000スケール）")
    print("=" * 80)
    print()

    # CSV読み込み
    if not CSV_PATH.exists():
        print(f"❌ CSVファイルが見つかりません: {CSV_PATH}")
        return

    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    total_episodes = len(df)
    print(f"📁 読み込み: {total_episodes:,}件のエピソード")
    print()

    # 特定エピソードのみの場合
    if episode_id:
        df_target = df[df["episode_id"] == episode_id]
        if df_target.empty:
            print(f"❌ エピソードID '{episode_id}' が見つかりません")
            return
        print(f"🎯 対象: {episode_id}")
    else:
        df_target = df

    # 旧スコアの統計
    old_scores = df_target["composite_score"].dropna().astype(float).tolist()
    if old_scores:
        old_stats = calculate_statistics(old_scores)
        print("【旧スコア統計（1-10スケール）】")
        print(f"  件数: {old_stats['count']:,}")
        print(f"  平均: {old_stats['mean']:.1f}")
        print(f"  標準偏差: {old_stats['std']:.1f}")
        print(f"  範囲: {old_stats['min']:.1f} - {old_stats['max']:.1f}")
        print()

    # 新スコア計算
    new_scores = []
    updated_count = 0
    skipped_count = 0

    for idx, row in df_target.iterrows():
        episode_data = row.to_dict()

        # 7軸スコアが揃っているか確認
        valid_axes = sum(
            1 for field in SEVEN_AXIS_FIELDS if pd.notna(episode_data.get(field)) and episode_data.get(field) != ""
        )

        if valid_axes == 0:
            skipped_count += 1
            continue

        # 新スコア計算
        new_score = calculate_enhanced_composite_score(episode_data)

        if new_score is not None:
            new_scores.append(new_score)
            if execute:
                df.loc[idx, "composite_score"] = new_score
            updated_count += 1

    # 新スコアの統計
    if new_scores:
        new_stats = calculate_statistics(new_scores)
        grade_dist = get_grade_distribution(new_scores)

        print("【新スコア統計（0-1000スケール）】")
        print(f"  件数: {new_stats['count']:,}")
        print(f"  平均: {new_stats['mean']:.1f}")
        print(f"  標準偏差: {new_stats['std']:.1f}")
        print(f"  範囲: {new_stats['min']:.1f} - {new_stats['max']:.1f}")
        print(f"  四分位: Q1={new_stats['q25']:.1f}, 中央={new_stats['median']:.1f}, Q3={new_stats['q75']:.1f}")
        print()

        print("【グレード分布】")
        total = sum(grade_dist.values())
        for grade, count in grade_dist.items():
            pct = count / total * 100 if total > 0 else 0
            bar = "█" * int(pct / 2)
            print(f"  {grade}: {count:>5,} ({pct:>5.1f}%) {bar}")
        print()

    # 改善効果の可視化
    if old_scores and new_scores:
        print("【改善効果】")
        old_range = old_stats["max"] - old_stats["min"]
        new_range = new_stats["max"] - new_stats["min"]
        print(f"  旧スコア範囲: {old_range:.1f} (実質{int(old_range * 10)}段階)")
        print(f"  新スコア範囲: {new_range:.1f} (実質{int(new_range)}段階)")
        print(f"  解像度向上: {new_range / old_range:.1f}倍")
        print()

    # 結果サマリー
    print("【処理結果】")
    print(f"  更新対象: {updated_count:,}件")
    print(f"  スキップ: {skipped_count:,}件（7軸スコアなし）")
    print()

    # 実行
    if execute:
        # バックアップ作成
        create_backup(pd.read_csv(CSV_PATH, encoding="utf-8-sig"))

        # CSV保存
        df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
        print(f"✅ CSVファイルを更新しました: {CSV_PATH}")
    else:
        print("⚠️  ドライランモード: --execute オプションで実行してください")

    print()
    print("=" * 80)
    print("📊 処理完了")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description="composite_scoreを0-1000スケールに更新")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="実際にCSVファイルを更新する",
    )
    parser.add_argument(
        "--episode",
        type=str,
        help="特定のエピソードIDのみ処理",
    )

    args = parser.parse_args()
    update_composite_scores(execute=args.execute, episode_id=args.episode)


if __name__ == "__main__":
    main()
