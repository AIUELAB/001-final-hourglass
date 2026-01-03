#!/usr/bin/env python3
"""
Phase 7D: LLM連携評価システム統合テスト

50件サンプルでLLM評価を実行し、分散・相関を検証する。

Usage:
    python scripts/phase7d_integration_test.py [--samples N] [--no-api]
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
from scipy import stats

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.app.utils.score_calculator import (
    LLM_TARGET_STATS,
    calculate_hybrid_rule_scores,
    calculate_hybrid_scores_dynamic,
    detect_episode_characteristics,
    evaluate_with_llm,
    get_dynamic_weights,
)


def load_stratified_samples(n: int = 50) -> list:
    """
    層化抽出でサンプルエピソードを読み込み

    様々なタイプのエピソードを均等に抽出
    """
    csv_path = project_root / "preserved/data/MASTER_EPISODES_CURRENT.csv"

    if not csv_path.exists():
        print(f"❌ CSVファイルが見つかりません: {csv_path}")
        return []

    df = pd.read_csv(csv_path, encoding="utf-8-sig")

    # episode_textがあるものをフィルタ
    df = df[df["episode_text"].notna() & (df["episode_text"].str.len() > 100)]

    # 層化抽出（episode_typeごとに均等抽出）
    samples = []
    episode_types = df["episode_type"].dropna().unique()

    samples_per_type = max(1, n // len(episode_types))

    for ep_type in episode_types:
        type_df = df[df["episode_type"] == ep_type]
        type_samples = type_df.sample(n=min(samples_per_type, len(type_df)), random_state=42)
        samples.extend(type_samples.to_dict("records"))

    # 不足分をランダムに追加
    if len(samples) < n:
        remaining = df[~df["episode_id"].isin([s.get("episode_id") for s in samples])]
        additional = remaining.sample(n=min(n - len(samples), len(remaining)), random_state=42)
        samples.extend(additional.to_dict("records"))

    print(f"✅ {len(samples)}件のサンプルエピソードを読み込み（層化抽出）")
    return samples[:n]


def run_llm_evaluation(samples: list, calibrate: bool = True) -> list:
    """LLM評価を実行"""
    results = []

    try:
        import anthropic

        client = anthropic.Anthropic()
    except Exception as e:
        print(f"❌ Anthropic APIクライアント作成失敗: {e}")
        return results

    total = len(samples)
    for i, episode in enumerate(samples):
        print(f"\r評価中: {i + 1}/{total}", end="", flush=True)

        episode_text = str(episode.get("episode_text", ""))
        if not episode_text:
            results.append(None)
            continue

        # 特性検出
        chars = detect_episode_characteristics(episode_text)

        # 動的重み取得
        dynamic_weights = get_dynamic_weights(episode)

        # ルールベーススコア
        rule_scores = calculate_hybrid_rule_scores(episode)

        # LLM評価
        llm_scores = evaluate_with_llm(episode_text, client=client, calibrate=calibrate)

        if llm_scores is None:
            results.append(
                {
                    "episode_id": episode.get("episode_id"),
                    "person_name": episode.get("person_name"),
                    "episode_type": episode.get("episode_type"),
                    "characteristics": chars,
                    "rule_scores": rule_scores,
                    "llm_scores": None,
                    "hybrid_scores": rule_scores,
                    "error": "LLM evaluation failed",
                }
            )
            continue

        # ハイブリッドスコア（動的重み）
        hybrid_scores = calculate_hybrid_scores_dynamic(episode, llm_scores, use_dynamic_weights=True)

        results.append(
            {
                "episode_id": episode.get("episode_id"),
                "person_name": episode.get("person_name"),
                "episode_type": episode.get("episode_type"),
                "characteristics": chars,
                "dynamic_weights": dynamic_weights,
                "rule_scores": rule_scores,
                "llm_scores": llm_scores,
                "hybrid_scores": hybrid_scores,
            }
        )

        # レート制限対策
        time.sleep(0.5)

    print()
    return results


def analyze_results(results: list) -> dict:
    """結果を分析"""
    analysis = {
        "total_samples": len(results),
        "successful_llm_evals": sum(1 for r in results if r and r.get("llm_scores")),
        "failed_llm_evals": sum(1 for r in results if r and r.get("error")),
        "rule_stats": {},
        "llm_stats": {},
        "hybrid_stats": {},
        "correlations": {},
    }

    # 有効な結果のみ
    valid_results = [r for r in results if r and r.get("llm_scores")]

    if not valid_results:
        print("❌ 有効な結果がありません")
        return analysis

    # 各軸の統計
    axes = ["記憶性", "共感性", "意外性", "生成品質", "教育的価値", "ストーリー品質", "事実密度"]

    for axis in axes:
        # ルールベース
        rule_values = [r["rule_scores"].get(axis, 5) for r in valid_results]
        analysis["rule_stats"][axis] = {
            "mean": round(sum(rule_values) / len(rule_values), 2),
            "std": round(pd.Series(rule_values).std(), 2),
            "min": round(min(rule_values), 1),
            "max": round(max(rule_values), 1),
        }

        # LLM
        llm_values = [r["llm_scores"].get(axis, 7) for r in valid_results]
        analysis["llm_stats"][axis] = {
            "mean": round(sum(llm_values) / len(llm_values), 2),
            "std": round(pd.Series(llm_values).std(), 2),
            "min": round(min(llm_values), 1),
            "max": round(max(llm_values), 1),
        }

        # ハイブリッド
        hybrid_values = [r["hybrid_scores"].get(axis, 5) for r in valid_results]
        analysis["hybrid_stats"][axis] = {
            "mean": round(sum(hybrid_values) / len(hybrid_values), 2),
            "std": round(pd.Series(hybrid_values).std(), 2),
            "min": round(min(hybrid_values), 1),
            "max": round(max(hybrid_values), 1),
        }

    # 相関分析（ハイブリッドスコア）
    if len(valid_results) >= 10:
        hybrid_df = pd.DataFrame([r["hybrid_scores"] for r in valid_results])

        for i, axis1 in enumerate(axes):
            for axis2 in axes[i + 1 :]:
                if axis1 in hybrid_df.columns and axis2 in hybrid_df.columns:
                    corr, _ = stats.spearmanr(hybrid_df[axis1], hybrid_df[axis2])
                    analysis["correlations"][f"{axis1}↔{axis2}"] = round(corr, 3)

    return analysis


def print_analysis_report(analysis: dict):
    """分析レポートを出力"""
    print("\n" + "=" * 70)
    print("Phase 7D: LLM連携評価システム統合テスト結果")
    print("=" * 70)

    print(f"\n総サンプル数: {analysis['total_samples']}")
    print(f"LLM評価成功: {analysis['successful_llm_evals']}")
    print(f"LLM評価失敗: {analysis['failed_llm_evals']}")

    # 分散比較
    print("\n" + "-" * 70)
    print("分散（σ）比較")
    print("-" * 70)
    print(f"{'軸':<15} {'ルール':>8} {'LLM':>8} {'ハイブリッド':>10} {'目標':>8} {'達成':>6}")
    print("-" * 70)

    for axis in ["記憶性", "共感性", "意外性", "生成品質", "教育的価値", "ストーリー品質", "事実密度"]:
        rule_std = analysis["rule_stats"].get(axis, {}).get("std", 0)
        llm_std = analysis["llm_stats"].get(axis, {}).get("std", 0)
        hybrid_std = analysis["hybrid_stats"].get(axis, {}).get("std", 0)
        target_std = LLM_TARGET_STATS.get(axis, {}).get("std", 0.5)

        achieved = "✅" if hybrid_std >= target_std * 0.8 else "⚠️"
        print(f"{axis:<15} {rule_std:>8.2f} {llm_std:>8.2f} {hybrid_std:>10.2f} {target_std:>8.2f} {achieved:>6}")

    # 相関分析
    print("\n" + "-" * 70)
    print("高相関ペア（|r| > 0.4）")
    print("-" * 70)

    high_corr = {k: v for k, v in analysis.get("correlations", {}).items() if abs(v) > 0.4}
    if high_corr:
        for pair, corr in sorted(high_corr.items(), key=lambda x: abs(x[1]), reverse=True):
            status = "⚠️" if abs(corr) > 0.6 else "注意"
            print(f"  {pair}: {corr:.3f} {status}")
    else:
        print("  なし（全ペア |r| ≤ 0.4）✅")

    print("\n" + "=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Phase 7D 統合テスト")
    parser.add_argument("--samples", type=int, default=50, help="テストするサンプル数")
    parser.add_argument("--no-api", action="store_true", help="API呼び出しをスキップ")
    parser.add_argument("--no-calibrate", action="store_true", help="キャリブレーションを無効化")
    args = parser.parse_args()

    print("=" * 70)
    print("Phase 7D: LLM連携評価システム統合テスト")
    print(f"サンプル数: {args.samples}")
    print("=" * 70)

    # サンプル読み込み
    samples = load_stratified_samples(args.samples)

    if not samples:
        print("❌ サンプルがありません")
        return

    if args.no_api:
        print("\n⏭️ API呼び出しをスキップ（ルールベースのみ分析）")
        # ルールベースのみで分析
        results = []
        for episode in samples:
            rule_scores = calculate_hybrid_rule_scores(episode)
            chars = detect_episode_characteristics(str(episode.get("episode_text", "")))
            results.append(
                {
                    "episode_id": episode.get("episode_id"),
                    "person_name": episode.get("person_name"),
                    "characteristics": chars,
                    "rule_scores": rule_scores,
                    "llm_scores": rule_scores,  # 代用
                    "hybrid_scores": rule_scores,
                }
            )
    else:
        # LLM評価実行
        print("\n📊 LLM評価を実行中...")
        results = run_llm_evaluation(samples, calibrate=not args.no_calibrate)

    # 分析
    print("\n📈 結果を分析中...")
    analysis = analyze_results(results)

    # レポート出力
    print_analysis_report(analysis)

    # 結果保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = project_root / "reports"

    # 詳細結果
    detail_path = output_dir / f"phase7d_results_{timestamp}.json"
    with open(detail_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n✅ 詳細結果保存: {detail_path}")

    # 分析サマリー
    summary_path = output_dir / f"phase7d_analysis_{timestamp}.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)
    print(f"✅ 分析サマリー保存: {summary_path}")


if __name__ == "__main__":
    main()
