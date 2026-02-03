#!/usr/bin/env python3
"""
desirability_score再計算スクリプト

Usage:
    python scripts/score/recalculate_desirability.py [--dry-run] [--limit N]

Options:
    --dry-run   実際にCSVを更新せず、計算結果のみ表示
    --limit N   処理するエピソード数を制限（テスト用）

出力カラム:
    - desirability_score: ユーザーにとっての「読みたさ」スコア（0〜1,000,000）
    - event_magnitude: イベント重要度（0〜50）
    - recency_boost: 時代性ブースト乗数（0.9〜1.2）
"""

import argparse
import csv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from tqdm import tqdm

from scripts.score.desirability.scorer import (
    calculate_desirability_score,
    NormalizationParams,
)

CSV_PATH = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"


def parse_args():
    """コマンドライン引数をパース"""
    parser = argparse.ArgumentParser(description="desirability_score再計算")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="実際にCSVを更新せず、結果のみ表示",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="処理するエピソード数を制限（テスト用）",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    print("=" * 60)
    print("desirability_score 再計算")
    print("=" * 60)

    # 正規化パラメータ表示
    params = NormalizationParams()
    print("\n正規化パラメータ:")
    print(f"  celebrity_median: {params.celebrity_median:.2f}")
    print(f"  celebrity_iqr: {params.celebrity_iqr:.2f}")
    print(f"  fame_median: {params.fame_median:.2f}")
    print(f"  fame_iqr: {params.fame_iqr:.2f}")
    print(f"  importance_median: {params.importance_median:.2f}")
    print(f"  importance_iqr: {params.importance_iqr:.2f}")

    # データ読み込み
    print("\n1. データ読み込み中...")
    df = pd.read_csv(CSV_PATH, dtype=str)
    episodes = df.to_dict("records")
    total_count = len(episodes)
    print(f"   読み込み完了: {total_count:,}件")

    # 制限がある場合は絞り込み
    if args.limit:
        episodes = episodes[: args.limit]
        print(f"   制限適用: {len(episodes):,}件")

    # 全エピソード再計算
    print("\n2. 全エピソード再計算中...")
    desirability_scores = []
    event_magnitudes = []
    recency_boosts = []

    for ep in tqdm(episodes, desc="   計算中", unit="件"):
        result = calculate_desirability_score(ep, params)
        desirability_scores.append(result["desirability_score"])
        event_magnitudes.append(result["event_magnitude"])
        recency_boosts.append(result["recency_boost"])

    print(f"   完了: {len(episodes):,}件処理")

    # スコア統計
    print("\n3. スコア統計:")
    scores_for_stats = [s for s in desirability_scores if s > 0]
    if scores_for_stats:
        avg_score = sum(scores_for_stats) / len(scores_for_stats)
        max_score = max(scores_for_stats)
        min_score = min(scores_for_stats)
        print(f"   平均: {avg_score:,.0f}")
        print(f"   最大: {max_score:,.0f}")
        print(f"   最小: {min_score:,.0f}")

    # スコア更新
    if args.limit:
        # limitがある場合は対象エピソードのみ更新
        for i, idx in enumerate(range(len(episodes))):
            df.at[idx, "desirability_score"] = desirability_scores[i]
            df.at[idx, "event_magnitude"] = event_magnitudes[i]
            df.at[idx, "recency_boost"] = recency_boosts[i]
    else:
        df["desirability_score"] = desirability_scores
        df["event_magnitude"] = event_magnitudes
        df["recency_boost"] = recency_boosts

    # Top50表示
    print("\n4. Top 50 確認:")
    df_sorted = df.copy()
    df_sorted["desirability_score"] = pd.to_numeric(
        df_sorted["desirability_score"], errors="coerce"
    )
    top50 = df_sorted.nlargest(50, "desirability_score")
    for i, (_, row) in enumerate(top50.iterrows(), 1):
        name = row.get("person_name", "?")
        age = row.get("age", "?")
        score = row.get("desirability_score") or 0
        episode_text = str(row.get("episode_text", ""))[:40]
        print(f"   {i:2}. {name}（{age}歳）: {float(score):,.0f} | {episode_text}...")

    # 参照対象の人物確認（大谷翔平 vs 竹内結子）
    print("\n5. 参照ランキング対象者の順位:")
    reference_persons = ["大谷翔平", "竹内結子", "イチロー", "孫正義", "羽生結弦"]
    df_sorted = df_sorted.sort_values("desirability_score", ascending=False).reset_index(
        drop=True
    )
    for person in reference_persons:
        person_df = df_sorted[df_sorted["person_name"] == person]
        if not person_df.empty:
            # reset_index済みなのでilocで最初の行のインデックスを取得
            best_row = person_df.iloc[0]
            best_age = best_row.get("age", "?")
            best_score = best_row.get("desirability_score") or 0
            # person_dfのインデックスはリセット済みのdf_sortedのインデックス
            rank = int(person_df.index.tolist()[0]) + 1
            print(f"   {person}（{best_age}歳）: {rank}位 ({float(best_score):,.0f})")
        else:
            print(f"   {person}: 見つかりません")

    # 大谷翔平 vs 竹内結子の順位チェック
    print("\n6. 検証: 大谷翔平 vs 竹内結子")
    ohtani_rank = None
    takeuchi_rank = None
    for i, (_, row) in enumerate(df_sorted.iterrows(), 1):
        name = row.get("person_name", "")
        if name == "大谷翔平" and ohtani_rank is None:
            ohtani_rank = i
        if name == "竹内結子" and takeuchi_rank is None:
            takeuchi_rank = i
        if ohtani_rank and takeuchi_rank:
            break

    if ohtani_rank and takeuchi_rank:
        if ohtani_rank < takeuchi_rank:
            print(f"   ✅ 大谷翔平（{ohtani_rank}位）> 竹内結子（{takeuchi_rank}位）: OK")
        else:
            print(f"   ❌ 大谷翔平（{ohtani_rank}位）< 竹内結子（{takeuchi_rank}位）: NG")
    else:
        print(f"   ⚠️ 順位取得失敗: 大谷={ohtani_rank}, 竹内={takeuchi_rank}")

    if args.dry_run:
        print("\n⚠️ ドライラン: CSVは更新されません")
    else:
        # CSV保存
        print("\n7. CSV保存中...")
        df.to_csv(CSV_PATH, index=False, quoting=csv.QUOTE_ALL)
        print(f"   保存完了: {CSV_PATH}")

    print("\n" + "=" * 60)
    print("完了")


if __name__ == "__main__":
    main()
