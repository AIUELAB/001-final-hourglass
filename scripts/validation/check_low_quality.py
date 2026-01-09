#!/usr/bin/env python3
"""
低品質エピソードチェックスクリプト
"""

import pandas as pd


def check_low_quality():
    """低品質エピソードを確認"""

    df = pd.read_csv("MASTER_EPISODES_CURRENT.csv", encoding="utf-8-sig")

    print("=" * 80)
    print("🔍 低品質エピソードチェック（composite_score < 70）")
    print("=" * 80)

    # composite_score < 70のエピソードを抽出
    low_quality = df[df["composite_score"] < 70]

    if len(low_quality) == 0:
        print("\n✅ 低品質エピソードなし")
        return

    print(f"\n低品質エピソード数: {len(low_quality)}件\n")

    for idx, row in low_quality.iterrows():
        print("=" * 80)
        print(f"行番号: {idx}")
        print(f"person_id: {row['person_id']}")
        print(f"person_name: {row['person_name']}")
        print(f"年齢: {row['age']}歳")
        print(f"カテゴリ: {row['category']}")
        print(f"composite_score: {row['composite_score']}点")
        print("\nエピソードテキスト:")
        print(row["episode_text"])
        print("\n個別スコア:")
        print(f"  - 記憶性: {row.get('memorability_score', 'N/A')}")
        print(f"  - 共感性: {row.get('empathy_score', 'N/A')}")
        print(f"  - 意外性: {row.get('surprise_score', 'N/A')}")
        print(f"  - 生成品質: {row.get('generation_quality_score', 'N/A')}")
        print(f"  - educational_value: {row.get('educational_value', 'N/A')}")
        print(f"  - story_quality: {row.get('story_quality', 'N/A')}")
        print(f"  - factual_density: {row.get('factual_density', 'N/A')}")

    print("\n" + "=" * 80)
    print("💡 推奨アクション:")
    print("=" * 80)
    print("1. エピソードテキストを再生成")
    print("2. より具体的な事実やエピソードを追加")
    print("3. 記憶に残る要素を強化")
    print("4. ストーリー構成を改善")


if __name__ == "__main__":
    check_low_quality()
