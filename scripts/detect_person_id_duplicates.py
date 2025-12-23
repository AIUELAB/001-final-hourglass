#!/usr/bin/env python3
"""
同一人物の重複PERSON ID検出スクリプト。

芸名/本名、別表記などで重複登録されている人物を検出する。
"""

import pandas as pd
from pathlib import Path

# 禁止カテゴリプレフィックス
FORBIDDEN_PREFIXES = [
    "歌舞伎",
    "落語",
    "漫才",
    "俳優",
    "女優",
    "歌手",
    "作家",
    "画家",
    "音楽家",
    "政治家",
    "科学者",
    "哲学者",
    "漫画家",
    "小説家",
    "詩人",
    "映画監督",
    "実業家",
    "武将",
    "大名",
    "天皇",
    "皇后",
    "王",
    "皇帝",
]

# 既知の同一人物パターン（短縮名/芸名→正式名）
KNOWN_ALIASES = {
    # 芸名→本名
    "ビートたけし": "北野武",
    "マリリン・モンロー": "ノーマ・ジーン・モーテンソン",
    "ボブ・ディラン": "ロバート・アレン・ジマーマン",
    "美空ひばり": "加藤和枝",
    "GACKT": "大城ガクト",
    "YOSHIKI": "林佳樹",
    # 短縮名→正式名
    "北斎": "葛飾北斎",
    "ベートーヴェン": "ルートヴィヒ・ヴァン・ベートーヴェン",
    "モーツァルト": "ヴォルフガング・アマデウス・モーツァルト",
    "ダ・ヴィンチ": "レオナルド・ダ・ヴィンチ",
    # 'ゴッホ': 統合済み (2025-12-23)
    "ピカソ": "パブロ・ピカソ",
}


def detect_duplicates(csv_path: Path) -> list[dict]:
    """重複の可能性がある人物を検出"""
    df = pd.read_csv(csv_path, low_memory=False)

    persons = (
        df.groupby("person_id")
        .agg(
            {
                "person_name": "first",
            }
        )
        .reset_index()
    )

    duplicates = []

    # 1. 既知のエイリアスをチェック
    for alias, real_name in KNOWN_ALIASES.items():
        alias_rows = persons[persons["person_name"] == alias]
        real_rows = persons[persons["person_name"] == real_name]

        if len(alias_rows) > 0 and len(real_rows) > 0:
            duplicates.append(
                {
                    "type": "known_alias",
                    "short": alias,
                    "short_id": alias_rows.iloc[0]["person_id"],
                    "full": real_name,
                    "full_id": real_rows.iloc[0]["person_id"],
                }
            )

    # 2. 部分一致検出（短い名前が長い名前に含まれる）
    names = persons["person_name"].tolist()
    ids = persons["person_id"].tolist()

    for i, short in enumerate(names):
        if len(short) < 2 or len(short) > 6:
            continue
        for j, full in enumerate(names):
            if i == j or len(full) <= len(short):
                continue
            if short in full and ids[i] != ids[j]:
                duplicates.append(
                    {
                        "type": "substring",
                        "short": short,
                        "short_id": ids[i],
                        "full": full,
                        "full_id": ids[j],
                    }
                )

    # 3. 禁止プレフィックス検出
    for pid, name in zip(ids, names):
        for prefix in FORBIDDEN_PREFIXES:
            if name.startswith(prefix + "・") or name.startswith(prefix + "　"):
                duplicates.append(
                    {
                        "type": "forbidden_prefix",
                        "short": prefix,
                        "short_id": pid,
                        "full": name,
                        "full_id": pid,
                    }
                )
                break

    return duplicates


def main():
    csv_path = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")

    print("=== 同一人物 重複PERSON ID検出 ===\n")

    duplicates = detect_duplicates(csv_path)

    known = [d for d in duplicates if d["type"] == "known_alias"]
    substr = [d for d in duplicates if d["type"] == "substring"]
    forbidden = [d for d in duplicates if d["type"] == "forbidden_prefix"]

    if forbidden:
        print(f"[禁止プレフィックス] {len(forbidden)}件 ⚠️ 要修正")
        for d in forbidden:
            print(f"  {d['full_id']}: {d['full']}")

    if known:
        print(f"\n[既知エイリアス] {len(known)}件")
        for d in known:
            print(f"  {d['short']} ({d['short_id']}) → {d['full']} ({d['full_id']})")

    if substr:
        print(f"\n[部分一致候補] {len(substr)}件 (要確認)")
        for d in substr[:20]:
            print(f"  {d['short']} ({d['short_id']}) ⊂ {d['full']} ({d['full_id']})")
        if len(substr) > 20:
            print(f"  ... 他{len(substr)-20}件")

    if not duplicates:
        print("問題は検出されませんでした。")


if __name__ == "__main__":
    main()
