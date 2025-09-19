#!/usr/bin/env python3
"""
アンダースコア修正の品質検証
"""
import pandas as pd
import re

# 修正済みファイルを読み込み
df = pd.read_csv('ultra_think_UNDERSCORE_FIXED_20250828_205441.csv')

print("=" * 80)
print("📊 アンダースコア修正の品質検証")
print("=" * 80)

# 1. person_nameにアンダースコアが残っていないか確認
with_underscore = df[df['person_name'].str.contains('_', na=False)]
print(f"\n✅ person_nameのアンダースコア: {len(with_underscore)}件")
if len(with_underscore) > 0:
    print("⚠️ まだアンダースコアが残っています:")
    for idx, row in with_underscore.head(5).iterrows():
        print(f"   {row['person_id']}: {row['person_name']}")

# 2. display名の重複確認
display_duplicates = []
for idx, row in df.iterrows():
    display = str(row.get('person_name_display', ''))
    # 括弧内のグループ名を抽出
    match = re.search(r'[\(（](.*?)[\)）]', display)
    if match:
        group_in_parentheses = match.group(1)
        # displayの中に同じグループ名が2回以上出現するか確認
        if display.count(group_in_parentheses) > 1:
            display_duplicates.append({
                'person_id': row['person_id'],
                'display': display,
                'occupation': row.get('occupation', '')
            })

print(f"\n✅ 重複グループ名: {len(display_duplicates)}件")
if display_duplicates:
    print("⚠️ まだ重複が残っています:")
    for dup in display_duplicates[:5]:
        print(f"   {dup['person_id']}: {dup['display']}")

# 3. 重要レコードの個別確認
print("\n" + "=" * 80)
print("🌟 重要レコードの確認")
print("=" * 80)

important_ids = ['P000133', 'P000058', 'P000401', 'P000051', 'P000072']
for person_id in important_ids:
    record = df[df['person_id'] == person_id]
    if not record.empty:
        row = record.iloc[0]
        print(f"\n{person_id}:")
        print(f"  person_name: {row['person_name']}")
        print(f"  person_name_display: {row['person_name_display']}")
        print(f"  person_name_ja: {row.get('person_name_ja', '')}")
        
        # 正しい形式か確認
        name = str(row['person_name'])
        display = str(row['person_name_display'])
        
        has_underscore = '_' in name
        has_proper_display = '(' in display and ')' in display
        
        if not has_underscore and has_proper_display:
            print("  ✅ 正しく修正されています")
        else:
            print("  ❌ 問題があります")

# 4. グループ別統計
print("\n" + "=" * 80)
print("📊 グループ別統計")
print("=" * 80)

comedians = df[df['occupation'] == 'お笑い芸人']
groups = {}
for idx, row in comedians.iterrows():
    display = str(row.get('person_name_display', ''))
    match = re.search(r'[\(（](.*?)[\)）]', display)
    if match:
        group_name = match.group(1)
        if group_name not in groups:
            groups[group_name] = []
        groups[group_name].append(row['person_id'])

print(f"グループ数: {len(groups)}")
print("\n主要グループ:")
for group_name in sorted(groups.keys())[:10]:
    members = groups[group_name]
    print(f"  {group_name}: {len(members)}名")

# 5. 最終統計
print("\n" + "=" * 80)
print("📈 最終統計")
print("=" * 80)

print(f"総レコード数: {len(df)}")
print(f"お笑い芸人: {len(comedians)}名")
print(f"グループ所属芸人: {sum(len(m) for m in groups.values())}名")
print(f"アンダースコア残存: {len(with_underscore)}件")
print(f"重複表示残存: {len(display_duplicates)}件")

if len(with_underscore) == 0 and len(display_duplicates) == 0:
    print("\n✨ 完璧！すべての問題が解決されています！")
else:
    print("\n⚠️ まだ問題が残っています。追加修正が必要です。")