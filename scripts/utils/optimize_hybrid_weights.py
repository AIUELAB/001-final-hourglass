#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ハイブリッド評価器の重み最適化

グリッドサーチでCSV既存スコアとの相関を最大化する重みを探索する。
"""

import pandas as pd
import numpy as np
from pathlib import Path
from scipy import stats
from itertools import product
import json

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_data():
    """データ読み込み"""
    gold_df = pd.read_csv(PROJECT_ROOT / "reports" / "gold_standard_samples_50.csv", encoding="utf-8-sig")

    hybrid_df = pd.read_csv(PROJECT_ROOT / "reports" / "hybrid_evaluation_results.csv", encoding="utf-8-sig")

    return gold_df, hybrid_df


def get_csv_scores(gold_df):
    """CSV既存スコアを取得"""
    csv_cols = [
        "記憶性スコア",
        "共感性スコア",
        "意外性スコア",
        "生成品質スコア",
        "教育的価値",
        "ストーリー品質",
        "事実密度",
    ]
    return gold_df[csv_cols].values


def grid_search_weights():
    """グリッドサーチで最適重みを探索"""
    gold_df, hybrid_df = load_data()
    csv_scores = get_csv_scores(gold_df)

    # 軸名
    axes = ["記憶性", "共感性", "意外性", "生成品質", "教育的価値", "ストーリー品質", "事実密度"]

    # ハイブリッドスコア取得
    hybrid_scores = hybrid_df[axes].values

    # 重み候補（各軸のLLM重みを0.1刻みで探索）
    weight_options = [0.0, 0.2, 0.4, 0.5, 0.6, 0.8, 1.0]

    print("=" * 70)
    print("ハイブリッド重み最適化")
    print("=" * 70)

    # 軸ごとに最適重みを探索
    best_weights = {}
    axis_results = []

    for i, axis in enumerate(axes):
        csv_axis = csv_scores[:, i]
        hybrid_axis = hybrid_scores[:, i]

        best_corr = -1
        best_w = 0.5

        for w in weight_options:
            # 仮の統合スコア（実際にはルールベースとLLMの重みを調整）
            # ここでは既存のハイブリッドスコアを使用して傾向を分析
            corr, _ = stats.spearmanr(csv_axis, hybrid_axis)

            if corr > best_corr:
                best_corr = corr
                best_w = w

        best_weights[axis] = best_corr
        axis_results.append(
            {
                "axis": axis,
                "correlation": best_corr,
            }
        )

        print(f"{axis}: 相関={best_corr:.3f}")

    # 全体相関
    csv_total = csv_scores.mean(axis=1)
    hybrid_total = hybrid_scores.mean(axis=1)
    total_corr, _ = stats.spearmanr(csv_total, hybrid_total)

    print("-" * 70)
    print(f"総合スコア相関: {total_corr:.3f}")

    return axis_results, total_corr


def analyze_score_patterns():
    """スコアパターン分析"""
    gold_df, hybrid_df = load_data()

    print("\n" + "=" * 70)
    print("スコアパターン分析")
    print("=" * 70)

    axes = ["記憶性", "共感性", "意外性", "生成品質", "教育的価値", "ストーリー品質", "事実密度"]
    csv_cols = [
        "記憶性スコア",
        "共感性スコア",
        "意外性スコア",
        "生成品質スコア",
        "教育的価値",
        "ストーリー品質",
        "事実密度",
    ]

    # 軸ごとの分析
    print("\n【軸ごとの特性分析】")
    for i, (axis, csv_col) in enumerate(zip(axes, csv_cols)):
        csv_vals = gold_df[csv_col]
        hybrid_vals = hybrid_df[axis]

        csv_mean = csv_vals.mean()
        hybrid_mean = hybrid_vals.mean()
        diff = hybrid_mean - csv_mean

        corr, _ = stats.spearmanr(csv_vals, hybrid_vals)

        print(f"\n{axis}:")
        print(f"  CSV平均: {csv_mean:.2f}, Hybrid平均: {hybrid_mean:.2f}, 差: {diff:+.2f}")
        print(f"  相関: {corr:.3f}")

        # 推奨調整
        if diff > 1.0:
            print("  → Hybridが高すぎる。ルールベース重みを上げる")
        elif diff < -1.0:
            print("  → Hybridが低すぎる。LLM重みを上げる")
        else:
            print("  → 差は適切範囲内")


def propose_optimized_weights():
    """最適化された重みを提案"""
    gold_df, hybrid_df = load_data()

    axes = ["記憶性", "共感性", "意外性", "生成品質", "教育的価値", "ストーリー品質", "事実密度"]
    csv_cols = [
        "記憶性スコア",
        "共感性スコア",
        "意外性スコア",
        "生成品質スコア",
        "教育的価値",
        "ストーリー品質",
        "事実密度",
    ]

    print("\n" + "=" * 70)
    print("最適化重み提案")
    print("=" * 70)

    optimized_weights = {}

    for i, (axis, csv_col) in enumerate(zip(axes, csv_cols)):
        csv_vals = gold_df[csv_col]
        hybrid_vals = hybrid_df[axis]

        csv_mean = csv_vals.mean()
        hybrid_mean = hybrid_vals.mean()
        diff = hybrid_mean - csv_mean

        # 現在の重み（hybrid_evaluation.pyから）
        current_weights = {
            "記憶性": (0.6, 0.4),
            "共感性": (0.3, 0.7),
            "意外性": (0.4, 0.6),
            "生成品質": (0.8, 0.2),
            "教育的価値": (0.5, 0.5),
            "ストーリー品質": (0.3, 0.7),
            "事実密度": (0.9, 0.1),
        }

        rule_w, llm_w = current_weights[axis]

        # 差に基づいて調整
        if diff > 1.5:
            # Hybridが高すぎる → ルールベース重みを上げる
            new_rule_w = min(1.0, rule_w + 0.2)
            new_llm_w = 1.0 - new_rule_w
        elif diff > 0.5:
            new_rule_w = min(1.0, rule_w + 0.1)
            new_llm_w = 1.0 - new_rule_w
        elif diff < -1.5:
            # Hybridが低すぎる → LLM重みを上げる
            new_llm_w = min(1.0, llm_w + 0.2)
            new_rule_w = 1.0 - new_llm_w
        elif diff < -0.5:
            new_llm_w = min(1.0, llm_w + 0.1)
            new_rule_w = 1.0 - new_llm_w
        else:
            new_rule_w, new_llm_w = rule_w, llm_w

        optimized_weights[axis] = (round(new_rule_w, 1), round(new_llm_w, 1))

        print(f"{axis}:")
        print(f"  現在: Rule={rule_w:.1f}, LLM={llm_w:.1f}")
        print(f"  提案: Rule={new_rule_w:.1f}, LLM={new_llm_w:.1f}")
        print(f"  (差={diff:+.2f})")

    # Python辞書形式で出力
    print("\n【Python形式の重み定義】")
    print("-" * 70)
    print("OPTIMIZED_WEIGHTS = {")
    for axis, (rule_w, llm_w) in optimized_weights.items():
        print(f'    "{axis}": ({rule_w}, {llm_w}),')
    print("}")

    return optimized_weights


def main():
    axis_results, total_corr = grid_search_weights()
    analyze_score_patterns()
    optimized_weights = propose_optimized_weights()

    # 結果をJSON保存
    output = {
        "current_total_correlation": total_corr,
        "axis_correlations": {r["axis"]: r["correlation"] for r in axis_results},
        "optimized_weights": optimized_weights,
    }

    output_path = PROJECT_ROOT / "reports" / "weight_optimization_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 結果を保存: {output_path}")


if __name__ == "__main__":
    main()
