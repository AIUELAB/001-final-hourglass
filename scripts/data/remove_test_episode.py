#!/usr/bin/env python3
"""
テストエピソード削除スクリプト
"""

from datetime import datetime

import pandas as pd


def remove_test_episode():
    """テストエピソードを削除"""

    # CSVファイル読み込み
    df = pd.read_csv("MASTER_EPISODES_CURRENT.csv", encoding="utf-8-sig")

    print("=" * 80)
    print("🗑️  テストエピソード削除")
    print("=" * 80)
    print(f"削除前のエピソード数: {len(df)}件\n")

    # テストエピソードを特定（person_id: P8D0502D または person_name: テストユーザー）
    test_episodes = df[(df["person_id"] == "P8D0502D") | (df["person_name"] == "テストユーザー")]

    print(f"削除対象エピソード: {len(test_episodes)}件\n")

    if len(test_episodes) == 0:
        print("✅ テストエピソードなし")
        return

    # 削除対象を表示
    for idx, row in test_episodes.iterrows():
        print(f"削除: [{idx}] {row['person_name']} - {row['episode_text'][:50]}...")

    # 削除
    df_cleaned = df[~((df["person_id"] == "P8D0502D") | (df["person_name"] == "テストユーザー"))]

    print(f"\n削除後のエピソード数: {len(df_cleaned)}件")
    print(f"削除したエピソード数: {len(df) - len(df_cleaned)}件")

    # 保存
    df_cleaned.to_csv("MASTER_EPISODES_CURRENT.csv", index=False, encoding="utf-8-sig")
    print("\n✅ 保存完了: MASTER_EPISODES_CURRENT.csv")

    # レポート
    report = {
        "operation": "remove_test_episode",
        "before_count": len(df),
        "after_count": len(df_cleaned),
        "removed_count": len(df) - len(df_cleaned),
        "timestamp": datetime.now().isoformat(),
    }

    print(f"\n{report}")


if __name__ == "__main__":
    remove_test_episode()
