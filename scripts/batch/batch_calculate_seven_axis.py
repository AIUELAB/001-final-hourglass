#!/usr/bin/env python3
"""
全エピソードの7軸スコア一括算出スクリプト

story_qualityとfactual_densityを全エピソードに対して算出

NOTE: story_qualityとfactual_densityの算出ロジックは統一モジュールからインポート
      backend/app/utils/score_calculator.py に正規実装あり
"""

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 統一モジュールからインポート（重複実装の排除）
from backend.app.utils.score_calculator import (
    calculate_factual_density,
    calculate_storytelling_quality,
)

CSV_PATH = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
BACKUP_PATH = (
    PROJECT_ROOT
    / "preserved"
    / "data"
    / "backups"
    / f"MASTER_EPISODES_CURRENT_backup_before_seven_axis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
)


def batch_calculate():
    """全エピソードの7軸スコアを一括算出"""

    print("=" * 80)
    print("📊 全エピソードの7軸スコア一括算出")
    print("=" * 80)
    print()

    # Step 1: CSVファイル読み込み
    print("Step 1: CSVファイル読み込み中...")
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    print(f"  ✅ 読み込み完了: {len(df):,}件")
    print()

    # Step 2: バックアップ作成
    print("Step 2: バックアップ作成中...")
    df.to_csv(BACKUP_PATH, index=False, encoding="utf-8-sig")
    print(f"  ✅ バックアップ作成: {BACKUP_PATH}")
    print()

    # Step 3: 現状確認
    print("Step 3: 現状確認中...")

    # story_qualityの確認（数値でないものをカウント）
    storytelling_needs_calc = 0
    for val in df["story_quality"]:
        if pd.isna(val):
            storytelling_needs_calc += 1
        else:
            try:
                float(val)
            except (ValueError, TypeError):
                storytelling_needs_calc += 1

    # factual_densityの確認
    factual_needs_calc = df["factual_density"].isna().sum()

    print(f"  story_qualityの算出が必要: {storytelling_needs_calc:,}件")
    print(f"  factual_densityの算出が必要: {factual_needs_calc:,}件")
    print()

    # Step 4: 一括算出
    print("Step 4: 7軸スコア一括算出中...")

    storytelling_updated = 0
    factual_updated = 0

    for idx, row in df.iterrows():
        episode_text = str(row["episode_text"])
        episode_type = str(row["episode_type"])

        # story_qualityの算出
        current_storytelling = row["story_quality"]
        needs_storytelling = False

        if pd.isna(current_storytelling):
            needs_storytelling = True
        else:
            try:
                float(current_storytelling)
            except (ValueError, TypeError):
                needs_storytelling = True

        if needs_storytelling:
            storytelling_score = calculate_storytelling_quality(episode_text, episode_type)
            df.at[idx, "story_quality"] = storytelling_score
            storytelling_updated += 1

        # factual_densityの算出
        if pd.isna(row["factual_density"]):
            factual_score = calculate_factual_density(episode_text, episode_type)
            df.at[idx, "factual_density"] = factual_score
            factual_updated += 1

        # 進捗表示（100件ごと）
        if (idx + 1) % 100 == 0:
            print(f"    進捗: {idx + 1:,}/{len(df):,}件処理完了...")

    print("  ✅ 算出完了")
    print(f"    - story_quality: {storytelling_updated:,}件更新")
    print(f"    - factual_density: {factual_updated:,}件更新")
    print()

    # Step 5: 7軸スコアの統計
    print("Step 5: 7軸スコア統計")

    axes = [
        "memorability_score",
        "empathy_score",
        "surprise_score",
        "generation_quality_score",
        "educational_value",
        "story_quality",
        "factual_density",
    ]

    complete_count = 0
    for _, row in df.iterrows():
        all_complete = True
        for axis in axes:
            if pd.isna(row[axis]):
                all_complete = False
                break
            try:
                float(row[axis])
            except (ValueError, TypeError):
                all_complete = False
                break
        if all_complete:
            complete_count += 1

    print(f"  7軸すべて揃っているエピソード: {complete_count:,}件 ({complete_count / len(df) * 100:.1f}%)")
    print()

    # 各軸の統計
    for axis in axes:
        numeric_values = []
        for val in df[axis]:
            if pd.notna(val):
                try:
                    numeric_values.append(float(val))
                except (ValueError, TypeError):
                    pass

        if numeric_values:
            avg = sum(numeric_values) / len(numeric_values)
            print(f"  {axis:15s}: 平均 {avg:.2f} ({len(numeric_values):,}件設定済み)")

    print()

    # Step 6: CSVファイル保存
    print("Step 6: CSVファイル保存中...")
    df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
    print(f"  ✅ 保存完了: {CSV_PATH}")
    print()

    # サマリー
    print("=" * 80)
    print("✅ 7軸スコア一括算出が完了しました！")
    print("=" * 80)
    print()
    print("📊 サマリー:")
    print(f"  - 総エピソード数: {len(df):,}件")
    print(f"  - story_quality更新: {storytelling_updated:,}件")
    print(f"  - factual_density更新: {factual_updated:,}件")
    print(f"  - 7軸完全設定: {complete_count:,}件 ({complete_count / len(df) * 100:.1f}%)")
    print(f"  - バックアップ: {BACKUP_PATH}")
    print()


if __name__ == "__main__":
    batch_calculate()
