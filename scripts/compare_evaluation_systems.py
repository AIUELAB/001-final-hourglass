#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
評価システム比較分析

3つの評価システム（CSV既存スコア、構造化LLM評価）を比較分析する。
"""

import pandas as pd
import numpy as np
from pathlib import Path
from scipy import stats

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def load_data():
    """データ読み込み"""
    # ゴールドスタンダードサンプル（CSV既存スコア含む）
    gold_df = pd.read_csv(
        PROJECT_ROOT / "reports" / "gold_standard_samples_50.csv",
        encoding="utf-8-sig"
    )

    # 構造化LLM評価結果
    llm_df = pd.read_csv(
        PROJECT_ROOT / "reports" / "structured_llm_evaluation_50.csv",
        encoding="utf-8-sig"
    )

    return gold_df, llm_df


def compare_scores(gold_df, llm_df):
    """スコア比較分析"""

    # 軸名のマッピング
    axis_mapping = {
        "記憶性スコア": "記憶性_スコア",
        "共感性スコア": "共感性_スコア",
        "意外性スコア": "意外性_スコア",
        "生成品質スコア": "生成品質_スコア",
        "教育的価値": "教育的価値_スコア",
        "ストーリー品質": "ストーリー品質_スコア",
        "事実密度": "事実密度_スコア",
    }

    print("=" * 80)
    print("評価システム比較分析レポート")
    print("=" * 80)

    print("\n【1. 基本統計量比較】")
    print("-" * 80)
    print(f"{'軸名':<15} {'CSV既存':<15} {'構造化LLM':<15} {'差分':<10}")
    print("-" * 80)

    correlations = {}

    for csv_col, llm_col in axis_mapping.items():
        csv_mean = gold_df[csv_col].mean()
        llm_mean = llm_df[llm_col].mean()
        diff = llm_mean - csv_mean

        # 相関係数計算
        valid_mask = ~(gold_df[csv_col].isna() | llm_df[llm_col].isna())
        if valid_mask.sum() > 2:
            corr, p_value = stats.spearmanr(
                gold_df.loc[valid_mask, csv_col],
                llm_df.loc[valid_mask, llm_col]
            )
            correlations[csv_col] = (corr, p_value)

        axis_name = csv_col.replace("スコア", "").replace("_", "")
        print(f"{axis_name:<15} {csv_mean:>6.2f}        {llm_mean:>6.2f}        {diff:>+6.2f}")

    # 全体平均
    csv_all_mean = gold_df[[c for c in axis_mapping.keys()]].mean().mean()
    llm_all_mean = llm_df[[c for c in axis_mapping.values()]].mean().mean()
    print("-" * 80)
    print(f"{'全体平均':<15} {csv_all_mean:>6.2f}        {llm_all_mean:>6.2f}        {llm_all_mean - csv_all_mean:>+6.2f}")

    print("\n【2. 相関分析（Spearman）】")
    print("-" * 80)
    print(f"{'軸名':<15} {'相関係数':<12} {'p値':<12} {'解釈'}")
    print("-" * 80)

    for csv_col, (corr, p_val) in correlations.items():
        axis_name = csv_col.replace("スコア", "").replace("_", "")

        if corr > 0.7:
            interp = "強い正の相関"
        elif corr > 0.4:
            interp = "中程度の正の相関"
        elif corr > 0.2:
            interp = "弱い正の相関"
        elif corr > -0.2:
            interp = "相関なし"
        else:
            interp = "負の相関"

        sig = "***" if p_val < 0.001 else "**" if p_val < 0.01 else "*" if p_val < 0.05 else ""
        print(f"{axis_name:<15} {corr:>6.3f}{sig:<5} {p_val:>10.4f}   {interp}")

    print("\n【3. スコア分布比較】")
    print("-" * 80)

    for csv_col, llm_col in axis_mapping.items():
        axis_name = csv_col.replace("スコア", "").replace("_", "")

        csv_std = gold_df[csv_col].std()
        llm_std = llm_df[llm_col].std()
        csv_range = f"{gold_df[csv_col].min():.1f}-{gold_df[csv_col].max():.1f}"
        llm_range = f"{llm_df[llm_col].min():.0f}-{llm_df[llm_col].max():.0f}"

        print(f"{axis_name}:")
        print(f"  CSV既存:   範囲={csv_range:<10} 標準偏差={csv_std:.2f}")
        print(f"  構造化LLM: 範囲={llm_range:<10} 標準偏差={llm_std:.2f}")

    print("\n【4. 大きなスコア差異のあるサンプル】")
    print("-" * 80)

    # 総合スコア計算
    csv_cols = list(axis_mapping.keys())
    llm_cols = list(axis_mapping.values())

    gold_df["csv_total"] = gold_df[csv_cols].mean(axis=1)
    llm_df["llm_total"] = llm_df[llm_cols].mean(axis=1)

    # 差分計算
    diff_df = pd.DataFrame({
        "sample_no": gold_df["sample_no"],
        "person_name": gold_df["person_name"],
        "csv_avg": gold_df["csv_total"],
        "llm_avg": llm_df["llm_total"],
        "diff": llm_df["llm_total"] - gold_df["csv_total"]
    })

    # 大きな差異（±1.5以上）
    large_diff = diff_df[abs(diff_df["diff"]) >= 1.5].sort_values("diff")

    if len(large_diff) > 0:
        print("CSV既存スコアと構造化LLMスコアの差が1.5以上のサンプル:")
        for _, row in large_diff.iterrows():
            print(f"  {row['sample_no']:>3}. {row['person_name']:<20} CSV={row['csv_avg']:.1f} LLM={row['llm_avg']:.1f} 差={row['diff']:+.1f}")
    else:
        print("大きな差異（±1.5以上）のあるサンプルはありません。")

    print("\n【5. カテゴリ別分析】")
    print("-" * 80)

    # カテゴリ別平均
    merged = gold_df[["sample_no", "category", "csv_total"]].merge(
        llm_df[["sample_no", "llm_total"]],
        on="sample_no"
    )

    category_stats = merged.groupby("category").agg({
        "csv_total": "mean",
        "llm_total": "mean"
    }).round(2)

    print(f"{'カテゴリ':<20} {'CSV既存':<10} {'構造化LLM':<10} {'差分':<10}")
    print("-" * 50)
    for cat, row in category_stats.iterrows():
        diff = row["llm_total"] - row["csv_total"]
        print(f"{cat:<20} {row['csv_total']:>6.2f}    {row['llm_total']:>6.2f}    {diff:>+6.2f}")

    print("\n【6. 主要な発見】")
    print("-" * 80)

    # 発見事項
    avg_corr = np.mean([c for c, _ in correlations.values()])
    print(f"1. 平均相関係数: {avg_corr:.3f}")

    if avg_corr < 0.3:
        print("   → CSV既存スコアと構造化LLMスコアの相関は弱い")
        print("   → 両者は異なる評価基準で採点されている可能性")
    elif avg_corr < 0.6:
        print("   → CSV既存スコアと構造化LLMスコアの相関は中程度")
    else:
        print("   → CSV既存スコアと構造化LLMスコアの相関は強い")

    csv_avg = gold_df["csv_total"].mean()
    llm_avg = llm_df["llm_total"].mean()

    print(f"\n2. 平均スコア比較:")
    print(f"   CSV既存: {csv_avg:.2f}")
    print(f"   構造化LLM: {llm_avg:.2f}")

    if llm_avg > csv_avg + 0.5:
        print("   → 構造化LLMは全体的に高めの評価傾向")
    elif llm_avg < csv_avg - 0.5:
        print("   → 構造化LLMは全体的に低めの評価傾向")
    else:
        print("   → 両者の平均は近い")

    # スコア分散の比較
    csv_stds = [gold_df[c].std() for c in csv_cols]
    llm_stds = [llm_df[c].std() for c in llm_cols]

    print(f"\n3. スコア分散（標準偏差の平均）:")
    print(f"   CSV既存: {np.mean(csv_stds):.2f}")
    print(f"   構造化LLM: {np.mean(llm_stds):.2f}")

    if np.mean(llm_stds) < np.mean(csv_stds):
        print("   → 構造化LLMは評価が収束している（バラツキが小さい）")
    else:
        print("   → 構造化LLMは評価のバラツキが大きい")

    return correlations


def main():
    gold_df, llm_df = load_data()

    print(f"データ読み込み完了:")
    print(f"  ゴールドスタンダード: {len(gold_df)}件")
    print(f"  構造化LLM評価: {len(llm_df)}件")
    print()

    correlations = compare_scores(gold_df, llm_df)

    print("\n" + "=" * 80)
    print("分析完了")
    print("=" * 80)


if __name__ == "__main__":
    main()
