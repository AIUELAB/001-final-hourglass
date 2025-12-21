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
        print(f"  - 記憶性: {row.get('記憶性スコア', 'N/A')}")
        print(f"  - 共感性: {row.get('共感性スコア', 'N/A')}")
        print(f"  - 意外性: {row.get('意外性スコア', 'N/A')}")
        print(f"  - 生成品質: {row.get('生成品質スコア', 'N/A')}")
        print(f"  - 教育的価値: {row.get('教育的価値', 'N/A')}")
        print(f"  - ストーリー品質: {row.get('ストーリー品質', 'N/A')}")
        print(f"  - 事実密度: {row.get('事実密度', 'N/A')}")

    print("\n" + "=" * 80)
    print("💡 推奨アクション:")
    print("=" * 80)
    print("1. エピソードテキストを再生成")
    print("2. より具体的な事実やエピソードを追加")
    print("3. 記憶に残る要素を強化")
    print("4. ストーリー構成を改善")


if __name__ == "__main__":
    check_low_quality()
