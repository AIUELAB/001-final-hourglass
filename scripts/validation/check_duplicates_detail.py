#!/usr/bin/env python3
"""
重複エピソード詳細チェックスクリプト
"""

import pandas as pd


def check_duplicates():
    """重複エピソードの詳細を確認"""

    df = pd.read_csv("MASTER_EPISODES_CURRENT.csv", encoding="utf-8-sig")

    print("=" * 80)
    print("🔍 重複エピソード詳細チェック")
    print("=" * 80)

    # person_idで重複しているものを抽出
    duplicates = df[df.duplicated(subset=["person_id"], keep=False)]

    if len(duplicates) == 0:
        print("\n✅ 重複なし")
        return

    print(f"\n総重複件数: {len(duplicates)}件")
    print(f"重複person_id数: {duplicates['person_id'].nunique()}個\n")

    # person_idごとにグループ化
    grouped = duplicates.groupby("person_id")

    print("=" * 80)
    print("重複詳細（person_idごと）")
    print("=" * 80)

    duplicate_summary = []

    for person_id, group in grouped:
        person_name = group.iloc[0]["person_name"]
        count = len(group)
        categories = group["category"].unique()
        ages = group["age"].unique()

        print(f"\n📌 person_id: {person_id}")
        print(f"   person_name: {person_name}")
        print(f"   重複数: {count}件")
        print(f"   カテゴリ: {', '.join(map(str, categories))}")
        print(f"   年齢: {', '.join(map(str, ages))}")

        # エピソードテキストの最初の50文字を表示
        for idx, row in group.iterrows():
            episode_preview = row["episode_text"][:50] if pd.notna(row["episode_text"]) else ""
            composite_score = row.get("composite_score", "N/A")
            print(f"   - [{idx}] {episode_preview}... (スコア: {composite_score})")

        duplicate_summary.append({"person_id": person_id, "person_name": person_name, "duplicate_count": count})

    # サマリー
    print("\n" + "=" * 80)
    print("サマリー")
    print("=" * 80)

    # 重複数の分布
    duplicate_counts = duplicates.groupby("person_id").size()
    print("\n重複数の分布:")
    for count in sorted(duplicate_counts.unique(), reverse=True):
        num_persons = len(duplicate_counts[duplicate_counts == count])
        print(f"  - {count}件重複: {num_persons}人")

    # 削除推奨
    print("\n💡 推奨アクション:")
    print("   各person_idにつき1件を残し、残りを削除")
    print(f"   削除対象: {len(duplicates) - len(duplicate_summary)}件")

    # 削除基準の提案
    print("\n📋 削除基準の提案:")
    print("   1. composite_scoreが高いものを優先して残す")
    print("   2. episode_textが長いものを優先して残す")
    print("   3. 最新のgeneration_timestampを優先して残す")


if __name__ == "__main__":
    check_duplicates()
