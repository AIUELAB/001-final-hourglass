#!/usr/bin/env python3
"""
品質ゲート適用スクリプト (Phase 15)

品質基準を満たさないエピソードのsuper_total_scoreを0に設定し、
ランキングから除外する。

品質ゲート条件:
1. factual_density < 5.0 → 除外
2. generation_quality_score < 6.0 → 除外

Note: 高有名度・低品質（factual_density < 7.0）のエピソードは除外しない。
      大谷翔平、羽生結弦、アインシュタイン等の重要人物を保護するため。
      test_celebrity_not_dominant は xfail として継続管理。
"""

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"


def apply_quality_gates(dry_run: bool = True) -> dict[str, Any]:
    """品質ゲートを適用する"""
    df = pd.read_csv(CSV_PATH, dtype=str)
    original_count = len(df)

    # 数値変換
    numeric_cols = ["factual_density", "generation_quality_score", "super_total_score"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 変更追跡
    changes: dict[str, list[str]] = {
        "low_factual_density": [],
        "low_generation_quality": [],
    }

    # ゲート1: factual_density < 5.0
    mask_low_fd = (df["factual_density"] < 5.0) & (df["super_total_score"] > 0)
    low_fd_ids = df.loc[mask_low_fd, "episode_id"].tolist()
    changes["low_factual_density"] = low_fd_ids

    # ゲート2: generation_quality_score < 6.0
    mask_low_gq = (df["generation_quality_score"] < 6.0) & (df["super_total_score"] > 0)
    low_gq_ids = df.loc[mask_low_gq, "episode_id"].tolist()
    changes["low_generation_quality"] = low_gq_ids

    # サマリー表示
    print("=" * 60)
    print("品質ゲート適用 Phase 15")
    print("=" * 60)
    print(f"対象CSV: {CSV_PATH}")
    print(f"総エピソード数: {original_count:,}")
    print()
    print(f"[ゲート1] factual_density < 5.0: {len(changes['low_factual_density']):,}件")
    print(f"[ゲート2] generation_quality < 6.0: {len(changes['low_generation_quality']):,}件")

    # 全変更対象（重複除去）
    all_affected = set(changes["low_factual_density"]) | set(changes["low_generation_quality"])
    print(f"\n総変更対象（重複除去）: {len(all_affected):,}件")

    if dry_run:
        print("\n[DRY RUN] 変更は適用されません")

        # サンプル表示
        if changes["low_factual_density"]:
            print("\n--- factual_density < 5.0 のサンプル（先頭5件） ---")
            sample = df[mask_low_fd].head(5)
            for _, row in sample.iterrows():
                print(f"  {row['episode_id']}: {row['person_name']} (FD={row['factual_density']:.1f})")
    else:
        # 変更適用
        df.loc[df["episode_id"].isin(all_affected), "super_total_score"] = 0

        # CSV保存
        df.to_csv(CSV_PATH, index=False)
        print(f"\n✅ {len(all_affected):,}件のエピソードのsuper_total_scoreを0に設定しました")

        # 新Top100の確認
        new_top100 = df.nlargest(100, "super_total_score")
        new_avg_fd = new_top100["factual_density"].mean()
        print(f"新Top100の平均factual_density: {new_avg_fd:.2f}")

    return {
        "total_affected": len(all_affected),
        "changes": changes,
        "dry_run": dry_run,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="品質ゲート適用")
    parser.add_argument("--execute", action="store_true", help="実際に変更を適用")
    args = parser.parse_args()

    _ = apply_quality_gates(dry_run=not args.execute)

    if not args.execute:
        print("\n実行するには --execute オプションを付けてください")


if __name__ == "__main__":
    main()
