#!/usr/bin/env python3
"""
ギャップ分析スクリプト

分析内容:
    1. 現行ランキングTop100と参照Best100の一致率（overlap@K）
    2. NDCG@K
    3. 参照に入るが現行では低い群／参照に入らないが現行で高い群の特徴差
"""

import json
import math
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class GapAnalysisResult:
    """ギャップ分析結果"""

    source: str
    overlap_at_10: float
    overlap_at_50: float
    overlap_at_100: float
    ndcg_at_10: float
    ndcg_at_50: float
    ndcg_at_100: float
    avg_rank_diff: float
    undervalued_examples: list  # 参照で高いが現行で低い
    overvalued_examples: list  # 参照に入らないが現行で高い


def dcg_at_k(relevances: list, k: int) -> float:
    """DCG@k を計算"""
    relevances = np.array(relevances[:k])
    if relevances.size == 0:
        return 0.0
    discounts = np.log2(np.arange(2, relevances.size + 2))
    return np.sum(relevances / discounts)


def ndcg_at_k(predicted_relevances: list, ideal_relevances: list, k: int) -> float:
    """NDCG@k を計算"""
    dcg = dcg_at_k(predicted_relevances, k)
    idcg = dcg_at_k(sorted(ideal_relevances, reverse=True), k)
    if idcg == 0:
        return 0.0
    return dcg / idcg


def overlap_at_k(set_a: set, set_b: set, k: int) -> float:
    """Overlap@k を計算"""
    intersection = len(set_a & set_b)
    return intersection / k


def analyze_gap(mapping_results: list, df: pd.DataFrame, source: str) -> GapAnalysisResult:
    """ギャップ分析を実行（人物レベルランキング）"""
    # 人物ごとの最高スコアエピソードでランキング
    df["super_total_score_float"] = pd.to_numeric(df["super_total_score"], errors="coerce")
    df_sorted = df.sort_values("super_total_score_float", ascending=False).reset_index(drop=True)

    # 人物レベル集約: 各人物のベストエピソードを取得
    best_per_person = df_sorted.groupby("person_name", as_index=False).first()
    person_ranked = best_per_person.sort_values("super_total_score_float", ascending=False).reset_index(drop=True)

    current_top100_persons = set(person_ranked.head(100)["person_name"].dropna())
    current_top50_persons = set(person_ranked.head(50)["person_name"].dropna())
    current_top10_persons = set(person_ranked.head(10)["person_name"].dropna())

    # 参照ランキングのTop人物
    ref_top100_persons = {r["matched_person_name"] for r in mapping_results if r["matched_person_name"]}
    ref_top50_persons = {
        r["matched_person_name"] for r in mapping_results if r["matched_person_name"] and r["ref_rank"] <= 50
    }
    ref_top10_persons = {
        r["matched_person_name"] for r in mapping_results if r["matched_person_name"] and r["ref_rank"] <= 10
    }

    # Overlap@K
    overlap_10 = overlap_at_k(current_top10_persons, ref_top10_persons, min(10, len(ref_top10_persons)))
    overlap_50 = overlap_at_k(current_top50_persons, ref_top50_persons, min(50, len(ref_top50_persons)))
    overlap_100 = overlap_at_k(current_top100_persons, ref_top100_persons, min(100, len(ref_top100_persons)))

    # NDCG計算用のrelevance（参照順位の逆数をrelevanceとする）
    # 参照Top100に含まれるものはrelevance=1/rank、含まれないものは0
    ref_rank_map = {r["matched_person_name"]: r["ref_rank"] for r in mapping_results if r["matched_person_name"]}

    # 人物レベルTop100のrelevance
    top100_persons = person_ranked.head(100)
    predicted_relevances = []
    for _, row in top100_persons.iterrows():
        person = row["person_name"]
        if person in ref_rank_map:
            # relevance = (101 - ref_rank) / 100 で0〜1にスケール
            predicted_relevances.append((101 - ref_rank_map[person]) / 100)
        else:
            predicted_relevances.append(0)

    # ideal relevance（参照順位順に並べた場合のrelevance）
    ideal_relevances = sorted([(101 - r) / 100 for r in ref_rank_map.values()], reverse=True)

    ndcg_10 = ndcg_at_k(predicted_relevances[:10], ideal_relevances, 10)
    ndcg_50 = ndcg_at_k(predicted_relevances[:50], ideal_relevances, 50)
    ndcg_100 = ndcg_at_k(predicted_relevances, ideal_relevances, 100)

    # 順位差の分析
    rank_diffs = []
    undervalued = []
    overvalued = []

    for r in mapping_results:
        if r["current_rank"] is not None:
            diff = r["current_rank"] - r["ref_rank"]
            rank_diffs.append(diff)

            # 参照で高いが現行で低い（undervalued）
            if r["ref_rank"] <= 30 and r["current_rank"] > 100:
                undervalued.append(
                    {
                        "person_name": r["ref_person_name"],
                        "ref_rank": r["ref_rank"],
                        "current_rank": r["current_rank"],
                        "rank_diff": diff,
                    }
                )
            # 参照で低いが現行で高い（overvalued）
            elif r["ref_rank"] > 50 and r["current_rank"] <= 30:
                overvalued.append(
                    {
                        "person_name": r["ref_person_name"],
                        "ref_rank": r["ref_rank"],
                        "current_rank": r["current_rank"],
                        "rank_diff": diff,
                    }
                )

    avg_rank_diff = np.mean(rank_diffs) if rank_diffs else 0

    # 現行で高いが参照に入っていない人物（人物レベル）
    current_top30_persons = set(person_ranked.head(30)["person_name"].dropna())
    not_in_ref = current_top30_persons - ref_top100_persons
    for person in list(not_in_ref)[:5]:  # 上位5件
        person_row = person_ranked[person_ranked["person_name"] == person].iloc[0]
        overvalued.append(
            {
                "person_name": person,
                "ref_rank": "N/A",
                "current_rank": int(person_row.name) + 1,
                "note": "参照Best100に含まれない",
            }
        )

    return GapAnalysisResult(
        source=source,
        overlap_at_10=overlap_10,
        overlap_at_50=overlap_50,
        overlap_at_100=overlap_100,
        ndcg_at_10=ndcg_10,
        ndcg_at_50=ndcg_50,
        ndcg_at_100=ndcg_100,
        avg_rank_diff=avg_rank_diff,
        undervalued_examples=undervalued,
        overvalued_examples=overvalued[:10],
    )


def analyze_feature_diff(mapping_results: list, df: pd.DataFrame, source: str) -> dict:
    """参照に入る群 vs 参照に入らない群の特徴差を分析"""
    df["super_total_score_float"] = pd.to_numeric(df["super_total_score"], errors="coerce")
    df_sorted = df.sort_values("super_total_score_float", ascending=False).reset_index(drop=True)
    df_sorted["current_rank"] = range(1, len(df_sorted) + 1)

    # 参照に含まれるエピソードIDのセット
    ref_episode_ids = {r["matched_episode_id"] for r in mapping_results if r["matched_episode_id"]}

    # 現行Top200から、参照に含まれる群 vs 含まれない群を分離
    top200 = df_sorted.head(200)

    in_ref = top200[top200["episode_id"].isin(ref_episode_ids)]
    not_in_ref = top200[~top200["episode_id"].isin(ref_episode_ids)]

    # 特徴量の比較
    features = [
        "celebrity_score_v2",
        "episode_fame_v6",
        "memorability_score",
        "surprise_score",
        "empathy_score",
        "educational_value",
        "story_quality",
        "factual_density",
        "generation_quality_score",
        "episode_importance_score",
    ]

    comparison = {}
    for feat in features:
        in_ref_vals = pd.to_numeric(in_ref[feat], errors="coerce").dropna()
        not_in_ref_vals = pd.to_numeric(not_in_ref[feat], errors="coerce").dropna()

        comparison[feat] = {
            "in_ref_mean": round(in_ref_vals.mean(), 2) if len(in_ref_vals) > 0 else None,
            "not_in_ref_mean": round(not_in_ref_vals.mean(), 2) if len(not_in_ref_vals) > 0 else None,
            "diff": round(in_ref_vals.mean() - not_in_ref_vals.mean(), 2)
            if len(in_ref_vals) > 0 and len(not_in_ref_vals) > 0
            else None,
        }

    # カテゴリ分布
    in_ref_categories = in_ref["category"].value_counts().head(5).to_dict()
    not_in_ref_categories = not_in_ref["category"].value_counts().head(5).to_dict()

    return {
        "source": source,
        "in_ref_count": len(in_ref),
        "not_in_ref_count": len(not_in_ref),
        "feature_comparison": comparison,
        "in_ref_categories": in_ref_categories,
        "not_in_ref_categories": not_in_ref_categories,
    }


def main():
    """メイン処理"""
    # マッピング結果読み込み
    mapping_path = PROJECT_ROOT / "src/reports/reference_mapping_results.json"
    with open(mapping_path, encoding="utf-8") as f:
        mapping_data = json.load(f)

    # マスターCSV読み込み
    csv_path = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
    df = pd.read_csv(csv_path, dtype=str)

    # ギャップ分析
    claude_gap = analyze_gap(mapping_data["claude"], df, "claude")
    gemini_gap = analyze_gap(mapping_data["gemini"], df, "gemini")

    # 特徴差分析
    claude_feat = analyze_feature_diff(mapping_data["claude"], df, "claude")
    gemini_feat = analyze_feature_diff(mapping_data["gemini"], df, "gemini")

    # 結果表示
    print("=" * 60)
    print("ギャップ分析結果")
    print("=" * 60)

    for gap, source in [(claude_gap, "Claude"), (gemini_gap, "Gemini")]:
        print(f"\n=== {source} ===")
        print(f"  Overlap@10: {gap.overlap_at_10:.1%}")
        print(f"  Overlap@50: {gap.overlap_at_50:.1%}")
        print(f"  Overlap@100: {gap.overlap_at_100:.1%}")
        print(f"  NDCG@10: {gap.ndcg_at_10:.3f}")
        print(f"  NDCG@50: {gap.ndcg_at_50:.3f}")
        print(f"  NDCG@100: {gap.ndcg_at_100:.3f}")
        print(f"  平均順位差: {gap.avg_rank_diff:+.1f}")

        if gap.undervalued_examples:
            print("\n  [参照で高いが現行で低い]")
            for e in gap.undervalued_examples[:5]:
                print(f"    {e['person_name']}: 参照{e['ref_rank']}位 → 現行{e['current_rank']}位")

        if gap.overvalued_examples:
            print("\n  [現行で高いが参照で低い/含まれない]")
            for e in gap.overvalued_examples[:5]:
                note = e.get("note", f"参照{e['ref_rank']}位")
                print(f"    {e['person_name']}: 現行{e['current_rank']}位 ({note})")

    # 特徴差サマリー
    print("\n" + "=" * 60)
    print("特徴差分析（現行Top200内）")
    print("=" * 60)

    for feat, source in [(claude_feat, "Claude"), (gemini_feat, "Gemini")]:
        print(f"\n=== {source} ===")
        print(f"  参照に含まれる: {feat['in_ref_count']}件")
        print(f"  参照に含まれない: {feat['not_in_ref_count']}件")
        print("\n  [特徴量比較（参照含む - 参照含まない）]")
        for f_name, f_vals in feat["feature_comparison"].items():
            if f_vals["diff"] is not None:
                sign = "+" if f_vals["diff"] > 0 else ""
                print(f"    {f_name}: {sign}{f_vals['diff']}")

    # 結果保存
    output = {
        "claude_gap": asdict(claude_gap),
        "gemini_gap": asdict(gemini_gap),
        "claude_features": claude_feat,
        "gemini_features": gemini_feat,
    }

    output_path = PROJECT_ROOT / "src/reports/gap_analysis_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n結果を保存: {output_path}")


if __name__ == "__main__":
    main()
