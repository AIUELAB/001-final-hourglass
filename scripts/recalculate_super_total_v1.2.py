#!/usr/bin/env python3
"""
超総合スコア v1.2.0 再計算スクリプト

変更点:
- 科学史キーワード追加（特殊相対性理論、E=mc²等）
- TURNING_POINT_MANUALブースト追加（+8%）
"""

import csv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from scripts.score.super_total_scorer import SuperTotalScorer

CSV_PATH = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
NORM_PARAMS_PATH = PROJECT_ROOT / "preserved/data/super_total_norm_params_v1.2.0.json"


def main():
    print("=" * 60)
    print("超総合スコア v1.2.0 再計算")
    print("=" * 60)

    # データ読み込み
    print("\n1. データ読み込み中...")
    df = pd.read_csv(CSV_PATH, dtype=str)
    episodes = df.to_dict("records")
    print(f"   読み込み完了: {len(episodes):,}件")

    # スコアラー初期化（正規化パラメータは既存を使用）
    print("\n2. スコアラー初期化中...")
    scorer = SuperTotalScorer(episodes)
    print("   正規化パラメータ:")
    print(
        f"     celebrity_score_v2: median={scorer.norm_params.celebrity_median:.1f}, iqr={scorer.norm_params.celebrity_iqr:.1f}"
    )
    print(f"     episode_fame_v6: median={scorer.norm_params.fame_median:.1f}, iqr={scorer.norm_params.fame_iqr:.1f}")
    print(
        f"     episode_importance: median={scorer.norm_params.importance_median:.1f}, iqr={scorer.norm_params.importance_iqr:.1f}"
    )

    # 保存
    scorer.save_normalization_params(NORM_PARAMS_PATH)
    print(f"   正規化パラメータ保存: {NORM_PARAMS_PATH}")

    # 全エピソード再計算
    print("\n3. 全エピソード再計算中...")
    passed_count = 0
    failed_count = 0
    new_scores = []

    for i, ep in enumerate(episodes):
        result = scorer.calculate(ep)
        if result.passed_gate:
            new_scores.append(result.score)
            passed_count += 1
        else:
            new_scores.append(0)
            failed_count += 1

        if (i + 1) % 2000 == 0:
            print(f"   処理中: {i + 1:,}/{len(episodes):,}")

    print(f"   完了: {passed_count:,}件通過, {failed_count:,}件ゲート不通過")

    # スコア更新
    df["super_total_score"] = new_scores

    # 比較確認（対象の2エピソード）
    print("\n4. 対象エピソード確認:")
    ep1 = df[df["episode_id"] == "EP-000002832"].iloc[0]
    ep2 = df[df["episode_id"] == "EP-3947C4DE"].iloc[0]

    result1 = scorer.calculate(ep1.to_dict())
    result2 = scorer.calculate(ep2.to_dict())

    print("\n   EP-000002832 (41歳、反ユダヤ主義):")
    print(f"     スコア: {result1.score:,.0f}")
    print(f"     ブースト: {result1.breakdown.get('achievement_boost', 0):.0%}")
    print(f"     キーワード: {result1.breakdown.get('boost_keywords', [])}")

    print("\n   EP-3947C4DE (26歳、奇跡の年):")
    print(f"     スコア: {result2.score:,.0f}")
    print(f"     ブースト: {result2.breakdown.get('achievement_boost', 0):.0%}")
    print(f"     キーワード: {result2.breakdown.get('boost_keywords', [])}")

    if result2.score > result1.score:
        print(f"\n   ✅ 正常: 奇跡の年エピソードが上位 (差: {result2.score - result1.score:,.0f})")
    else:
        print("\n   ⚠️ 異常: まだ反ユダヤ主義エピソードが上位")

    # CSV保存
    print("\n5. CSV保存中...")
    df.to_csv(CSV_PATH, index=False, quoting=csv.QUOTE_ALL)
    print(f"   保存完了: {CSV_PATH}")

    # Top 10表示
    print("\n6. アインシュタインエピソード Top 5:")
    einstein_df = df[df["person_name"] == "アインシュタイン"].copy()
    einstein_df["super_total_score"] = pd.to_numeric(einstein_df["super_total_score"], errors="coerce")
    einstein_sorted = einstein_df.nlargest(5, "super_total_score")
    for i, (_, row) in enumerate(einstein_sorted.iterrows(), 1):
        age = row.get("age", "?")
        score = row.get("super_total_score", 0)
        text = str(row.get("episode_text", ""))[:60] + "..."
        print(f"   {i}. {age}歳: {float(score):,.0f} - {text}")

    print("\n" + "=" * 60)
    print("完了")


if __name__ == "__main__":
    main()
