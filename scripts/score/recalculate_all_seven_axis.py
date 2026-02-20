#!/usr/bin/env python3
"""
7軸スコア一括再計算スクリプト

全エピソードの7軸スコアを新しい計算式で再計算し、
composite_score（0-1000スケール）も更新する。

使用方法:
    # ドライラン（変更なし、統計のみ）
    python scripts/recalculate_all_seven_axis.py

    # 実行（CSVを更新）
    python scripts/recalculate_all_seven_axis.py --execute

    # サンプルのみ確認
    python scripts/recalculate_all_seven_axis.py --sample 10
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

# 統一モジュールからインポート（重複実装の排除完了）
from backend.app.utils.score_calculator import (
    SEVEN_AXIS_FIELDS,
    calculate_all_five_axes,
    calculate_enhanced_composite_score,
    calculate_factual_density,
    calculate_story_quality,
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


def calculate_statistics(scores: list, name: str = "") -> dict:
    """スコアの統計を計算"""
    if not scores:
        return {}

    scores_array = np.array(scores)
    stats = {
        "count": len(scores),
        "mean": round(float(np.mean(scores_array)), 2),
        "std": round(float(np.std(scores_array)), 2),
        "min": round(float(np.min(scores_array)), 2),
        "max": round(float(np.max(scores_array)), 2),
        "q25": round(float(np.percentile(scores_array, 25)), 2),
        "median": round(float(np.percentile(scores_array, 50)), 2),
        "q75": round(float(np.percentile(scores_array, 75)), 2),
    }
    return stats


def print_axis_comparison(axis_name: str, old_scores: list, new_scores: list):
    """軸ごとの旧→新の比較を表示"""
    old_stats = calculate_statistics(old_scores)
    new_stats = calculate_statistics(new_scores)

    print(f"\n  【{axis_name}】")
    if old_stats and new_stats:
        print(
            f"    旧: 平均={old_stats['mean']:.2f}, 標準偏差={old_stats['std']:.2f}, 範囲={old_stats['min']:.1f}〜{old_stats['max']:.1f}"
        )
        print(
            f"    新: 平均={new_stats['mean']:.2f}, 標準偏差={new_stats['std']:.2f}, 範囲={new_stats['min']:.1f}〜{new_stats['max']:.1f}"
        )

        # 改善度
        if old_stats["std"] > 0:
            std_improvement = (new_stats["std"] - old_stats["std"]) / old_stats["std"] * 100
            print(f"    → 標準偏差変化: {std_improvement:+.1f}%")


def recalculate_all_scores(execute: bool = False, sample_size: int = None):
    """全エピソードの7軸スコアを再計算"""
    print("=" * 80)
    print("📊 7軸スコア一括再計算スクリプト")
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

    # サンプルモード
    if sample_size:
        df_target = df.sample(n=min(sample_size, total_episodes), random_state=42)
        print(f"🎯 サンプルモード: {len(df_target)}件を抽出")
    else:
        df_target = df

    # 旧スコアの収集
    old_scores = {axis: [] for axis in SEVEN_AXIS_FIELDS}
    old_composite = []

    for _, row in df_target.iterrows():
        for axis in SEVEN_AXIS_FIELDS:
            val = row.get(axis)
            if pd.notna(val) and val != "":
                try:
                    old_scores[axis].append(float(val))
                except (ValueError, TypeError):
                    pass

        comp = row.get("composite_score")
        if pd.notna(comp) and comp != "":
            try:
                old_composite.append(float(comp))
            except (ValueError, TypeError):
                pass

    # 旧スコアの統計表示
    print("【旧スコア統計】")
    for axis in SEVEN_AXIS_FIELDS:
        if old_scores[axis]:
            stats = calculate_statistics(old_scores[axis])
            print(
                f"  {axis:15s}: 平均={stats['mean']:.2f}, 標準偏差={stats['std']:.2f}, 範囲={stats['min']:.1f}〜{stats['max']:.1f}"
            )

    if old_composite:
        stats = calculate_statistics(old_composite)
        print(f"\n  composite_score: 平均={stats['mean']:.1f}, 範囲={stats['min']:.1f}〜{stats['max']:.1f}")
    print()

    # 新スコア計算
    print("【新スコア計算中...】")
    new_scores = {axis: [] for axis in SEVEN_AXIS_FIELDS}
    new_composite = []
    updated_count = 0

    for idx, row in df_target.iterrows():
        episode_data = row.to_dict()
        episode_text = str(episode_data.get("episode_text", ""))
        episode_type = str(episode_data.get("episode_type", ""))

        # 5軸を計算（記憶性、共感性、意外性、生成品質、educational_value）
        five_axes = calculate_all_five_axes(episode_data)

        # 2軸を計算（story_quality、factual_density）
        storytelling = calculate_story_quality(episode_text, episode_type)
        factual = calculate_factual_density(episode_text, episode_type)

        # 新スコアを収集
        for axis, score in five_axes.items():
            new_scores[axis].append(score)
            if execute:
                df.loc[idx, axis] = score

        new_scores["story_quality"].append(storytelling)
        new_scores["factual_density"].append(factual)

        if execute:
            df.loc[idx, "story_quality"] = storytelling
            df.loc[idx, "factual_density"] = factual

        # composite_score計算
        updated_data = episode_data.copy()
        updated_data.update(five_axes)
        updated_data["story_quality"] = storytelling
        updated_data["factual_density"] = factual

        composite = calculate_enhanced_composite_score(updated_data)
        if composite is not None:
            new_composite.append(composite)
            if execute:
                df.loc[idx, "composite_score"] = composite

        updated_count += 1

        # 進捗表示
        if updated_count % 1000 == 0:
            print(f"  処理中: {updated_count:,} / {len(df_target):,}")

    print(f"  完了: {updated_count:,}件処理")
    print()

    # 新スコアの統計表示
    print("【新スコア統計】")
    for axis in SEVEN_AXIS_FIELDS:
        if new_scores[axis]:
            stats = calculate_statistics(new_scores[axis])
            print(
                f"  {axis:15s}: 平均={stats['mean']:.2f}, 標準偏差={stats['std']:.2f}, 範囲={stats['min']:.1f}〜{stats['max']:.1f}"
            )

    if new_composite:
        stats = calculate_statistics(new_composite)
        print(f"\n  composite_score: 平均={stats['mean']:.1f}, 範囲={stats['min']:.1f}〜{stats['max']:.1f}")

        # グレード分布
        grades = {"S": 0, "A": 0, "B": 0, "C": 0, "D": 0, "E": 0}
        for score in new_composite:
            grade = get_score_grade(score)
            grades[grade] += 1

        print("\n  【グレード分布】")
        total = sum(grades.values())
        for grade, count in grades.items():
            pct = count / total * 100 if total > 0 else 0
            bar = "█" * int(pct / 2)
            print(f"    {grade}: {count:>5,} ({pct:>5.1f}%) {bar}")
    print()

    # 軸ごとの比較
    print("【軸ごとの改善度】")
    for axis in SEVEN_AXIS_FIELDS:
        print_axis_comparison(axis, old_scores[axis], new_scores[axis])
    print()

    # サンプル表示
    if sample_size and sample_size <= 10:
        print("【サンプルエピソード】")
        sample_indices = df_target.head(3).index.tolist()
        for idx in sample_indices:
            row = df.loc[idx]
            print(f"\n  {row['episode_id']} - {row['person_name']}")
            print(f"    テキスト: {str(row['episode_text'])[:50]}...")
            for axis in SEVEN_AXIS_FIELDS:
                old_val = df_target.loc[idx, axis] if axis in df_target.columns else "-"
                new_val = new_scores[axis][list(df_target.index).index(idx)] if axis in new_scores else "-"
                print(f"    {axis}: {old_val} → {new_val}")
            print(
                f"    composite_score: {row.get('composite_score', '-')} → {new_composite[list(df_target.index).index(idx)]:.1f}"
            )
        print()

    # 実行
    if execute and not sample_size:
        # バックアップ作成
        create_backup(pd.read_csv(CSV_PATH, encoding="utf-8-sig"))

        # CSV保存
        df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
        print(f"✅ CSVファイルを更新しました: {CSV_PATH}")
    elif sample_size:
        print("ℹ️  サンプルモード: 実際のCSV更新は行いません")
    else:
        print("⚠️  ドライランモード: --execute オプションで実行してください")

    print()
    print("=" * 80)
    print("📊 処理完了")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description="7軸スコアを一括再計算")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="実際にCSVファイルを更新する",
    )
    parser.add_argument(
        "--sample",
        type=int,
        help="サンプル数を指定（テスト用）",
    )

    args = parser.parse_args()
    recalculate_all_scores(execute=args.execute, sample_size=args.sample)


if __name__ == "__main__":
    main()
