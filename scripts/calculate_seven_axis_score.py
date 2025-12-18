#!/usr/bin/env python3
"""
7軸スコア算出スクリプト

エピソードの7軸スコア（記憶性、共感性、意外性、生成品質、教育的価値、ストーリー品質、事実密度）を算出

NOTE: ストーリー品質と事実密度の算出ロジックは統一モジュールからインポート
      backend/app/utils/score_calculator.py に正規実装あり
"""

import sys
from pathlib import Path

import pandas as pd

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

# 統一モジュールからインポート（重複実装の排除）
from backend.app.utils.score_calculator import (
    calculate_factual_density,
    calculate_storytelling_quality,
)

CSV_PATH = Path(__file__).parent.parent / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"


def calculate_seven_axis_score(episode_id: str):
    """指定されたエピソードの7軸スコアを算出"""

    # CSVファイル読み込み
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")

    # エピソード取得
    episode = df[df["episode_id"] == episode_id]
    if episode.empty:
        print(f"❌ エピソードID '{episode_id}' が見つかりませんでした")
        return

    row = episode.iloc[0]

    print("=" * 80)
    print(f"📊 7軸スコア算出: {episode_id}")
    print("=" * 80)
    print()

    # 基本情報
    print("【基本情報】")
    print(f"  人物名: {row['person_name']}")
    print(f"  年齢: {row['age']}歳")
    print(f"  カテゴリ: {row['category']}")
    print(f"  エピソードタイプ: {row['episode_type']}")
    print()

    # エピソードテキスト
    print("【エピソードテキスト】")
    episode_text = str(row["episode_text"])
    print(f"  {episode_text[:200]}...")
    print()

    # 既存の7軸スコア
    print("【既存の7軸スコア】")
    axis_scores = {
        "記憶性スコア": row.get("記憶性スコア"),
        "共感性スコア": row.get("共感性スコア"),
        "意外性スコア": row.get("意外性スコア"),
        "生成品質スコア": row.get("生成品質スコア"),
        "教育的価値": row.get("教育的価値"),
        "ストーリー品質": row.get("ストーリー品質"),
        "事実密度": row.get("事実密度"),
    }

    for axis, score in axis_scores.items():
        if pd.notna(score):
            try:
                score_value = float(score)
                print(f"  {axis:15s}: {score_value:.1f}")
            except (ValueError, TypeError):
                print(f"  {axis:15s}: {score} (数値変換不可)")
        else:
            print(f"  {axis:15s}: （未設定）")
    print()

    # 新規算出が必要なスコア
    print("【新規算出】")

    # ストーリー品質
    storytelling_score = calculate_storytelling_quality(episode_text, str(row["episode_type"]))
    print(f"  ストーリー品質: {storytelling_score:.1f}")

    # 事実密度
    factual_density = calculate_factual_density(episode_text, str(row["episode_type"]))
    print(f"  事実密度: {factual_density:.1f}")
    print()

    # 総合スコア（7軸の平均）
    print("【7軸スコア統合】")

    # 既存スコアを取得（数値のみ）
    final_scores = {}
    for axis, score in axis_scores.items():
        if pd.notna(score):
            try:
                final_scores[axis] = float(score)
            except (ValueError, TypeError):
                pass

    # 新規算出スコアを追加
    final_scores["ストーリー品質"] = storytelling_score
    final_scores["事実密度"] = factual_density

    # 7軸すべてが揃っているか確認
    all_axes = [
        "記憶性スコア",
        "共感性スコア",
        "意外性スコア",
        "生成品質スコア",
        "教育的価値",
        "ストーリー品質",
        "事実密度",
    ]

    print("  全7軸スコア:")
    for i, axis in enumerate(all_axes, 1):
        score_val = final_scores.get(axis, None)
        if score_val is not None:
            print(f"    {i}. {axis:15s}: {score_val:.1f}")
        else:
            print(f"    {i}. {axis:15s}: （未設定）")

    # 平均スコア計算
    if len(final_scores) == 7:
        average_score = sum(final_scores.values()) / 7
        print()
        print(f"  📊 7軸平均スコア: {average_score:.2f}")
    else:
        print()
        print(f"  ⚠️  7軸のうち{len(final_scores)}軸のみ設定されています")

    print()
    print("=" * 80)
    print("✅ 7軸スコア算出完了")
    print("=" * 80)

    # CSVへの反映（オプション）
    print()
    update = input("CSVファイルに算出結果を反映しますか？ (y/N): ")
    if update.lower() == "y":
        df.loc[df["episode_id"] == episode_id, "ストーリー品質"] = storytelling_score
        df.loc[df["episode_id"] == episode_id, "事実密度"] = factual_density
        df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
        print("✅ CSVファイルを更新しました")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        episode_id = sys.argv[1]
    else:
        episode_id = "EP-001,713"

    calculate_seven_axis_score(episode_id)
