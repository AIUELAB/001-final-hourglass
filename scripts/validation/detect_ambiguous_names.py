#!/usr/bin/env python3
"""
曖昧性のある短名を検出（14名のパターンに類似）
"""

import pandas as pd
from pathlib import Path

PROCESSED_NAMES = {
    "エイブラハム・リンカーン",
    "ナポレオン・ボナパルト",
    "スティーヴン・スピルバーグ",
    "オードリー・ヘプバーン",
    "メッシ",
    "ネイマール",
    "アルフレッド・ノーベル",
    "ノバク・ジョコビッチ",
}

# 14名の元々の短名パターン
ORIGINAL_SHORT_PATTERNS = ["リンカーン", "ナポレオン", "スピルバーグ", "ヘプバーン", "ノーベル", "ジョコビッチ"]


def load_master_csv():
    csv_path = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")
    return pd.read_csv(csv_path, encoding="utf-8-sig")


def main():
    print("=" * 60)
    print("曖昧性のある短名検出（歴史人物・著名人パターン）")
    print("=" * 60)

    df = load_master_csv()

    name_stats = (
        df.groupby("person_name")
        .agg({"person_id": lambda x: sorted(list(x.unique())), "episode_id": "count"})
        .reset_index()
    )
    name_stats.columns = ["person_name", "person_ids", "episode_count"]

    print(f"総レコード数: {len(df):,}")
    print(f"ユニーク人物名: {len(name_stats):,}\n")

    # カタカナのみ、3-6文字、スペース・中黒なし
    katakana_short = name_stats[
        (name_stats["person_name"].str.match(r"^[\u30A0-\u30FF]{3,6}$"))
        & (~name_stats["person_name"].isin(PROCESSED_NAMES))
    ].copy()

    print(f"🔍 カタカナ短名（3-6文字）: {len(katakana_short)}件")
    print("   （著名な外国人名の可能性）\n")

    # エピソード数でソート（著名度の指標）
    katakana_short = katakana_short.sort_values("episode_count", ascending=False)

    print("=" * 60)
    print("📊 カタカナ短名トップ30（エピソード数順）")
    print("=" * 60)

    for i, row in katakana_short.head(30).iterrows():
        name = row["person_name"]
        ep_count = row["episode_count"]
        person_id = row["person_ids"][0]
        print(f"{name:15s} | {ep_count:2d}ep | {person_id}")

    # 漢字のみ、2-4文字、スペースなし（歴史人物の姓または名のみの可能性）
    print("\n" + "=" * 60)
    print("📊 漢字短名（2-4文字）トップ30（エピソード数順）")
    print("=" * 60)

    kanji_short = name_stats[
        (name_stats["person_name"].str.match(r"^[\u4E00-\u9FFF]{2,4}$"))
        & (~name_stats["person_name"].isin(PROCESSED_NAMES))
    ].copy()

    kanji_short = kanji_short.sort_values("episode_count", ascending=False)

    for i, row in kanji_short.head(30).iterrows():
        name = row["person_name"]
        ep_count = row["episode_count"]
        person_id = row["person_ids"][0]
        print(f"{name:15s} | {ep_count:2d}ep | {person_id}")

    # 特定の著名人パターン（姓のみ）を検出
    print("\n" + "=" * 60)
    print("📊 姓のみパターン候補（エピソード3件以上）")
    print("=" * 60)

    # エピソード3件以上の漢字短名
    surname_candidates = kanji_short[kanji_short["episode_count"] >= 3]

    if len(surname_candidates) > 0:
        for _, row in surname_candidates.head(20).iterrows():
            name = row["person_name"]
            ep_count = row["episode_count"]
            person_id = row["person_ids"][0]

            # この姓を含むフルネームが存在するか
            full_names = name_stats[
                (name_stats["person_name"].str.contains(name, regex=False))
                & (name_stats["person_name"] != name)
                & (name_stats["person_name"].str.len() > len(name))
            ]

            if len(full_names) > 0:
                print(f"\n{name} ({ep_count}ep, {person_id})")
                for _, full_row in full_names.iterrows():
                    print(f"  → {full_row['person_name']} ({full_row['episode_count']}ep, {full_row['person_ids'][0]})")
            else:
                print(f"{name} ({ep_count}ep, {person_id}) - フルネーム版なし")
    else:
        print("該当なし")

    print("\n" + "=" * 60)
    print("検出完了")
    print("=" * 60)


if __name__ == "__main__":
    main()
