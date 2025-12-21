#!/usr/bin/env python3
"""
真の重複チェック（person_id + age が同じもの）
"""

import pandas as pd


def check_real_duplicates():
    """person_id + age が同じ真の重複をチェック"""

    df = pd.read_csv("MASTER_EPISODES_CURRENT.csv", encoding="utf-8-sig")

    print("=" * 80)
    print("🔍 真の重複チェック（person_id + age）")
    print("=" * 80)

    # person_id + age で重複しているものを抽出
    duplicates = df[df.duplicated(subset=["person_id", "age"], keep=False)]

    if len(duplicates) == 0:
        print("\n✅ 真の重複なし")
        print("\n💡 検出された重複は、同じ人物の異なる年齢でのエピソードです。")
        print("   これは仕様通りの動作です。")
        return

    print(f"\n⚠️  真の重複件数: {len(duplicates)}件")
    print(f"   重複グループ数: {duplicates.groupby(['person_id', 'age']).ngroups}グループ\n")

    # person_id + age でグループ化
    grouped = duplicates.groupby(["person_id", "age"])

    print("=" * 80)
    print("真の重複詳細")
    print("=" * 80)

    for (person_id, age), group in grouped:
        person_name = group.iloc[0]["person_name"]
        count = len(group)

        print(f"\n📌 person_id: {person_id}, 年齢: {age}歳")
        print(f"   person_name: {person_name}")
        print(f"   重複数: {count}件")

        for idx, row in group.iterrows():
            episode_preview = row["episode_text"][:60] if pd.notna(row["episode_text"]) else ""
            composite_score = row.get("composite_score", "N/A")
            category = row.get("category", "N/A")
            print(f"   - [{idx}] カテゴリ: {category}, スコア: {composite_score}")
            print(f"      {episode_preview}...")

    if len(duplicates) > 0:
        print("\n💡 推奨アクション:")
        print("   各グループにつき最もスコアの高いエピソードを残し、残りを削除")
        print(f"   削除対象: {len(duplicates) - grouped.ngroups}件")


if __name__ == "__main__":
    check_real_duplicates()
