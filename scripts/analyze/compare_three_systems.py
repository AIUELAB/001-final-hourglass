#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
3評価システム比較分析

CSV既存スコア、構造化LLM評価、ハイブリッド評価を比較する。
"""

import pandas as pd
import numpy as np
from pathlib import Path
from scipy import stats

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_all_data():
    """全データ読み込み"""
    # ゴールドスタンダード（CSV既存スコア）
    gold_df = pd.read_csv(PROJECT_ROOT / "reports" / "gold_standard_samples_50.csv", encoding="utf-8-sig")

    # 構造化LLM評価
    llm_df = pd.read_csv(PROJECT_ROOT / "reports" / "structured_llm_evaluation_50.csv", encoding="utf-8-sig")

    # ハイブリッド評価
    hybrid_df = pd.read_csv(PROJECT_ROOT / "reports" / "hybrid_evaluation_results.csv", encoding="utf-8-sig")

    return gold_df, llm_df, hybrid_df


def calculate_total_scores(gold_df, llm_df, hybrid_df):
    """総合スコア計算"""
    # CSV既存スコアの軸
    csv_cols = [
        "memorability_score",
        "empathy_score",
        "surprise_score",
        "generation_quality_score",
        "educational_value",
        "story_quality",
        "factual_density",
    ]

    # 構造化LLM評価の軸
    llm_cols = [
        "記憶性_スコア",
        "共感性_スコア",
        "意外性_スコア",
        "生成品質_スコア",
        "educational_value_スコア",
        "story_quality_スコア",
        "factual_density_スコア",
    ]

    # ハイブリッドの軸
    hybrid_cols = ["記憶性", "共感性", "意外性", "生成品質", "educational_value", "story_quality", "factual_density"]

    gold_df["csv_total"] = gold_df[csv_cols].mean(axis=1)
    llm_df["llm_total"] = llm_df[llm_cols].mean(axis=1)
    hybrid_df["hybrid_total"] = hybrid_df[hybrid_cols].mean(axis=1)

    return gold_df, llm_df, hybrid_df


def compare_systems():
    """3システム比較"""
    gold_df, llm_df, hybrid_df = load_all_data()
    gold_df, llm_df, hybrid_df = calculate_total_scores(gold_df, llm_df, hybrid_df)

    print("=" * 80)
    print("3評価システム比較分析レポート")
    print("=" * 80)

    # 軸マッピング
    axes = ["記憶性", "共感性", "意外性", "生成品質", "educational_value", "story_quality", "factual_density"]

    csv_map = {
        "記憶性": "memorability_score",
        "共感性": "empathy_score",
        "意外性": "surprise_score",
        "生成品質": "generation_quality_score",
        "educational_value": "educational_value",
        "story_quality": "story_quality",
        "factual_density": "factual_density",
    }
    llm_map = {
        "記憶性": "記憶性_スコア",
        "共感性": "共感性_スコア",
        "意外性": "意外性_スコア",
        "生成品質": "生成品質_スコア",
        "educational_value": "educational_value_スコア",
        "story_quality": "story_quality_スコア",
        "factual_density": "factual_density_スコア",
    }

    # 1. 基本統計量
    print("\n【1. 軸別平均スコア比較】")
    print("-" * 80)
    print(f"{'軸名':<12} {'CSV既存':>10} {'構造化LLM':>10} {'ハイブリッド':>12}")
    print("-" * 80)

    for axis in axes:
        csv_mean = gold_df[csv_map[axis]].mean()
        llm_mean = llm_df[llm_map[axis]].mean()
        hybrid_mean = hybrid_df[axis].mean()
        print(f"{axis:<12} {csv_mean:>10.2f} {llm_mean:>10.2f} {hybrid_mean:>12.2f}")

    # 全体平均
    csv_total_mean = gold_df["csv_total"].mean()
    llm_total_mean = llm_df["llm_total"].mean()
    hybrid_total_mean = hybrid_df["hybrid_total"].mean()
    print("-" * 80)
    print(f"{'全体平均':<12} {csv_total_mean:>10.2f} {llm_total_mean:>10.2f} {hybrid_total_mean:>12.2f}")

    # 2. 標準偏差（識別力）
    print("\n【2. 軸別標準偏差（識別力）】")
    print("-" * 80)
    print(f"{'軸名':<12} {'CSV既存':>10} {'構造化LLM':>10} {'ハイブリッド':>12}")
    print("-" * 80)

    for axis in axes:
        csv_std = gold_df[csv_map[axis]].std()
        llm_std = llm_df[llm_map[axis]].std()
        hybrid_std = hybrid_df[axis].std()
        print(f"{axis:<12} {csv_std:>10.2f} {llm_std:>10.2f} {hybrid_std:>12.2f}")

    csv_std_avg = np.mean([gold_df[csv_map[a]].std() for a in axes])
    llm_std_avg = np.mean([llm_df[llm_map[a]].std() for a in axes])
    hybrid_std_avg = np.mean([hybrid_df[a].std() for a in axes])
    print("-" * 80)
    print(f"{'平均':<12} {csv_std_avg:>10.2f} {llm_std_avg:>10.2f} {hybrid_std_avg:>12.2f}")

    # 3. CSV既存との相関
    print("\n【3. CSV既存スコアとの相関（Spearman）】")
    print("-" * 80)
    print(f"{'軸名':<12} {'構造化LLM':>12} {'ハイブリッド':>12}")
    print("-" * 80)

    for axis in axes:
        csv_vals = gold_df[csv_map[axis]]
        llm_vals = llm_df[llm_map[axis]]
        hybrid_vals = hybrid_df[axis]

        llm_corr, _ = stats.spearmanr(csv_vals, llm_vals)
        hybrid_corr, _ = stats.spearmanr(csv_vals, hybrid_vals)

        print(f"{axis:<12} {llm_corr:>12.3f} {hybrid_corr:>12.3f}")

    # 総合スコアの相関
    llm_total_corr, _ = stats.spearmanr(gold_df["csv_total"], llm_df["llm_total"])
    hybrid_total_corr, _ = stats.spearmanr(gold_df["csv_total"], hybrid_df["hybrid_total"])
    print("-" * 80)
    print(f"{'総合スコア':<12} {llm_total_corr:>12.3f} {hybrid_total_corr:>12.3f}")

    # 4. スコア範囲
    print("\n【4. スコア範囲（最小-最大）】")
    print("-" * 80)
    print(f"{'軸名':<12} {'CSV既存':>12} {'構造化LLM':>12} {'ハイブリッド':>14}")
    print("-" * 80)

    for axis in axes:
        csv_range = f"{gold_df[csv_map[axis]].min():.1f}-{gold_df[csv_map[axis]].max():.1f}"
        llm_range = f"{llm_df[llm_map[axis]].min():.0f}-{llm_df[llm_map[axis]].max():.0f}"
        hybrid_range = f"{hybrid_df[axis].min():.1f}-{hybrid_df[axis].max():.1f}"
        print(f"{axis:<12} {csv_range:>12} {llm_range:>12} {hybrid_range:>14}")

    # 5. 評価
    print("\n【5. システム特性評価】")
    print("-" * 80)

    print("\n● CSV既存スコア:")
    print(f"  - 平均: {csv_total_mean:.2f}")
    print(f"  - 識別力（標準偏差平均）: {csv_std_avg:.2f}")
    print("  - 特徴: バラツキがあり、低スコアも含む")

    print("\n● 構造化LLM評価:")
    print(f"  - 平均: {llm_total_mean:.2f}")
    print(f"  - 識別力（標準偏差平均）: {llm_std_avg:.2f}")
    print(f"  - CSV既存との相関: {llm_total_corr:.3f}")
    print("  - 特徴: 高スコア集中、識別力低い")

    print("\n● ハイブリッド評価:")
    print(f"  - 平均: {hybrid_total_mean:.2f}")
    print(f"  - 識別力（標準偏差平均）: {hybrid_std_avg:.2f}")
    print(f"  - CSV既存との相関: {hybrid_total_corr:.3f}")
    print("  - 特徴: ルールベース＋LLMで適度なバラツキ")

    # 6. 推奨
    print("\n【6. 結論と推奨】")
    print("-" * 80)

    best_corr = "ハイブリッド" if hybrid_total_corr > llm_total_corr else "構造化LLM"
    best_std = "ハイブリッド" if hybrid_std_avg > llm_std_avg else "構造化LLM"

    print(f"CSV既存との相関が高いのは: {best_corr}")
    print(f"識別力が高いのは: {best_std}")

    if hybrid_total_corr > llm_total_corr and hybrid_std_avg > llm_std_avg:
        print("\n★ ハイブリッド方式が両指標で優れており、採用を推奨")
    elif hybrid_total_corr > llm_total_corr:
        print("\n★ ハイブリッド方式はCSV既存との整合性が高い")
    elif hybrid_std_avg > llm_std_avg:
        print("\n★ ハイブリッド方式は識別力が高い")

    # 個別サンプルでの比較
    print("\n【7. 個別サンプルでのスコア差異（上位5件）】")
    print("-" * 80)

    merged = pd.DataFrame(
        {
            "sample_no": gold_df["sample_no"],
            "person_name": gold_df["person_name"],
            "csv": gold_df["csv_total"],
            "llm": llm_df["llm_total"],
            "hybrid": hybrid_df["hybrid_total"],
        }
    )
    merged["hybrid_csv_diff"] = abs(merged["hybrid"] - merged["csv"])
    merged["llm_csv_diff"] = abs(merged["llm"] - merged["csv"])

    print("\nハイブリッドがCSVに近いサンプル（差が小さい）:")
    closest = merged.nsmallest(5, "hybrid_csv_diff")
    for _, row in closest.iterrows():
        print(
            f"  {row['person_name']:<20} CSV={row['csv']:.1f} Hybrid={row['hybrid']:.1f} 差={row['hybrid_csv_diff']:.2f}"
        )

    print("\nハイブリッドとCSVの差が大きいサンプル:")
    farthest = merged.nlargest(5, "hybrid_csv_diff")
    for _, row in farthest.iterrows():
        print(
            f"  {row['person_name']:<20} CSV={row['csv']:.1f} Hybrid={row['hybrid']:.1f} 差={row['hybrid_csv_diff']:.2f}"
        )


def main():
    compare_systems()
    print("\n" + "=" * 80)
    print("分析完了")
    print("=" * 80)


if __name__ == "__main__":
    main()
