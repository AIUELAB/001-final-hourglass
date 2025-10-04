#!/usr/bin/env python3
"""
信頼できるエピソードの文字数を詳細分析
"""

import pandas as pd

# CSVファイル読み込み
df = pd.read_csv('trusted_episodes_latest.csv', encoding='utf-8-sig')

print("="*60)
print("📊 文字数分析レポート")
print("="*60)

for idx, row in df.iterrows():
    episode = row['episode_text']
    actual_length = len(episode)
    csv_length = row['character_count']

    print(f"\n{idx+1}. {row['person_name']}（{row['episode_age']}歳）")
    print(f"  CSV記載文字数: {csv_length}")
    print(f"  実際の文字数: {actual_length}")
    print(f"  差分: {actual_length - csv_length}")

    if actual_length < 150:
        print(f"  ⚠️ 150文字未満！")
    elif actual_length > 250:
        print(f"  ⚠️ 250文字超過！")
    else:
        print(f"  ✅ 文字数OK")

    print(f"  エピソード冒頭: {episode[:50]}...")

print("\n" + "="*60)
print("📈 統計サマリー:")
print(f"  平均文字数: {df['episode_text'].str.len().mean():.1f}")
print(f"  最小文字数: {df['episode_text'].str.len().min()}")
print(f"  最大文字数: {df['episode_text'].str.len().max()}")
print(f"  150文字未満: {(df['episode_text'].str.len() < 150).sum()}件")
print(f"  150-250文字: {((df['episode_text'].str.len() >= 150) & (df['episode_text'].str.len() <= 250)).sum()}件")
print(f"  250文字超: {(df['episode_text'].str.len() > 250).sum()}件")