#!/usr/bin/env python3
"""
エピソードIDを指定してスロット値を表示するスクリプト
"""

import sys

import pandas as pd


def show_episode_slot(episode_id):
    """エピソードのスロット値を表示"""
    csv_path = "MASTER_EPISODES_CURRENT.csv"
    df = pd.read_csv(csv_path, encoding="utf-8-sig")

    # エピソードIDで検索
    episode = df[df["episode_id"] == episode_id]

    if episode.empty:
        print(f"❌ エピソードID '{episode_id}' が見つかりませんでした")
        return

    # 1行目を取得
    row = episode.iloc[0]

    print("=" * 80)
    print(f"📋 エピソード詳細: {episode_id}")
    print("=" * 80)
    print()

    # 基本情報
    print("【基本情報】")
    print(f"  person_id         : {row['person_id']}")
    print(f"  person_name       : {row['person_name']}")
    print(f"  age               : {row['age']}")
    print(f"  category          : {row['category']}")
    print(f"  person_type       : {row['person_type']}")
    print()

    # エピソード情報
    print("【エピソード情報】")
    print(f"  episode_type      : {row['episode_type']}")
    print(f"  episode_text      : {row['episode_text'][:100]}...")
    print()

    # スロット値（重要）
    print("【スロット値】")
    slot_value = row["slot"]
    if pd.isna(slot_value) or slot_value == "":
        print("  slot              : （空）")
    else:
        print(f"  slot              : {slot_value}")
    print()

    # 品質スコア
    print("【品質スコア】")
    print(f"  composite_score   : {row['composite_score']}")
    print(f"  fame_score        : {row['fame_score']}")
    print()

    # その他のスコア
    print("【詳細スコア】")
    if "memorability_score" in df.columns:
        print(f"  memorability_score      : {row['memorability_score']}")
    if "empathy_score" in df.columns:
        print(f"  empathy_score      : {row['empathy_score']}")
    if "surprise_score" in df.columns:
        print(f"  surprise_score      : {row['surprise_score']}")
    if "generation_quality_score" in df.columns:
        print(f"  generation_quality_score    : {row['generation_quality_score']}")
    print()

    # 全フィールド表示
    print("【全フィールド】")
    for col in df.columns:
        value = row[col]
        if pd.isna(value):
            value = "（空）"
        elif col == "episode_text":
            value = f"{str(value)[:100]}..."
        print(f"  {col:30s}: {value}")

    print()
    print("=" * 80)


if __name__ == "__main__":
    episode_id = sys.argv[1] if len(sys.argv) > 1 else "EP-001,716"
    show_episode_slot(episode_id)
