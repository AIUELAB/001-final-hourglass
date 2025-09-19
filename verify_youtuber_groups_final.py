#!/usr/bin/env python3
"""
YouTuberグループ修正の最終検証
"""
import pandas as pd
import re

# 修正済みファイルを読み込み
df = pd.read_csv('ultra_think_YOUTUBER_GROUPS_FIXED_20250828_201154.csv')

# YouTuberのみ抽出
youtubers = df[df['occupation'] == 'YouTuber']

print("=" * 80)
print("📊 YouTuberグループ表示の最終検証")
print("=" * 80)

# 括弧付きの表示名を持つYouTuber
has_parentheses = youtubers[youtubers['person_name_display'].str.contains(r'[\(（]', na=False)]
print(f"\n✅ 括弧付き表示（グループメンバー）: {len(has_parentheses)}名")

# グループ別に集計
groups = {}
for idx, row in has_parentheses.iterrows():
    display = str(row['person_name_display'])
    match = re.search(r'[\(（](.*?)[\)）]', display)
    if match:
        group_name = match.group(1)
        if group_name not in groups:
            groups[group_name] = []
        groups[group_name].append({
            'person_id': row['person_id'],
            'name': row['person_name'],
            'display': display
        })

print("\n📋 グループ別メンバー一覧:")
for group_name, members in sorted(groups.items(), key=lambda x: len(x[1]), reverse=True):
    print(f"\n【{group_name}】 {len(members)}名")
    for member in members[:5]:  # 最初の5名のみ表示
        print(f"  {member['person_id']}: {member['display']}")
    if len(members) > 5:
        print(f"  ...他{len(members)-5}名")

# P000111の確認
print("\n" + "=" * 80)
print("🌟 P000111（ふくらP）の最終確認")
print("=" * 80)

p000111 = df[df['person_id'] == 'P000111']
if not p000111.empty:
    row = p000111.iloc[0]
    print(f"person_id: {row['person_id']}")
    print(f"person_name: {row['person_name']}")
    print(f"person_name_display: {row['person_name_display']}")
    print(f"occupation: {row['occupation']}")
    
    if 'QuizKnock' in str(row['person_name_display']):
        print("\n✅ 正しく修正されています！")
    else:
        print("\n❌ 修正が適用されていません")

# 統計
print("\n" + "=" * 80)
print("📊 最終統計")
print("=" * 80)
print(f"YouTuber総数: {len(youtubers)}")
print(f"グループメンバー（括弧付き）: {len(has_parentheses)} ({len(has_parentheses)/len(youtubers)*100:.1f}%)")
print(f"個人YouTuber（括弧なし）: {len(youtubers) - len(has_parentheses)} ({(len(youtubers)-len(has_parentheses))/len(youtubers)*100:.1f}%)")
print(f"グループ数: {len(groups)}")

# 注意事項
print("\n⚠️ 注意事項:")
print("- UUUMは事務所名（グループではない）")
print("- カジサックは個人名（グループではない）")
print("- 一部のメンバーは複数グループに所属している可能性あり")

print("\n✨ 検証完了!")