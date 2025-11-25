#!/usr/bin/env python3
"""
P000111とその他のYouTuberグループの問題を調査
"""
import pandas as pd
import json

# 最新のデータベースを読み込み
csv_file = 'ultra_think_HAJIME_FIXED_20250828_194909.csv'
df = pd.read_csv(csv_file)

print("=" * 80)
print("🔍 P000111の調査")
print("=" * 80)

# P000111の情報を確認
p000111 = df[df['person_id'] == 'P000111']
if not p000111.empty:
    row = p000111.iloc[0]
    print(f"person_id: {row['person_id']}")
    print(f"person_name: {row['person_name']}")
    print(f"person_name_display: {row['person_name_display']}")
    print(f"person_name_ja: {row['person_name_ja']}")
    print(f"occupation: {row['occupation']}")
    print(f"nationality: {row['nationality']}")
    print(f"birth_year: {row['birth_year']}")
    print()

print("=" * 80)
print("📊 YouTuberグループ/ユニットの可能性がある候補を探索")
print("=" * 80)

# YouTuberでグループっぽい名前を持つレコードを探す
youtubers = df[df['occupation'] == 'YouTuber']

# グループ/ユニットの可能性がある名前のパターン
group_patterns = [
    'ズ', 'ーズ',  # 〜ズ、〜ーズ
    'ブラザーズ', 'シスターズ',  # Brothers, Sisters
    'チャンネル', 'ch', 'CH',  # チャンネル名
    'コンビ', '兄弟', '姉妹',  # コンビ、兄弟、姉妹
    'ユニット', 'unit',  # ユニット
    'グループ', 'group',  # グループ
    '団', '隊', '組',  # 団体系
    'TV', 'tv',  # TV系
    'ファミリー', 'family',  # ファミリー
    '&', '＆', 'and', 'with',  # 複数人を示す記号
    '×', 'vs', 'VS',  # コラボ系
]

potential_groups = []
for idx, row in youtubers.iterrows():
    name = str(row['person_name'])
    name_display = str(row['person_name_display'])
    name_ja = str(row['person_name_ja'])

    # 名前にグループパターンが含まれるか確認
    is_group = False
    for pattern in group_patterns:
        if pattern in name or pattern in name_display or pattern in name_ja:
            is_group = True
            break

    # または、複数人を示唆する名前（カタカナ・ひらがな・漢字の組み合わせ）
    if '・' in name or '・' in name_display or '・' in name_ja:
        is_group = True

    if is_group:
        # 括弧がついているか確認
        has_parentheses = '(' in name_display or '（' in name_display

        potential_groups.append({
            'person_id': row['person_id'],
            'person_name': name,
            'person_name_display': name_display,
            'person_name_ja': name_ja,
            'has_parentheses': has_parentheses,
            'nationality': row['nationality']
        })

print(f"グループ/ユニットの可能性があるYouTuber: {len(potential_groups)}件")
print()

# グループ候補を表示（最初の20件）
print("🎯 括弧なしのグループ候補（要検証）:")
no_paren_groups = [g for g in potential_groups if not g['has_parentheses']][:20]
for group in no_paren_groups:
    print(f"  {group['person_id']}: {group['person_name_display']} | {group['person_name']} | {group['nationality']}")

print()
print("✅ 括弧付きのグループ（正しく表示されている）:")
with_paren_groups = [g for g in potential_groups if g['has_parentheses']][:10]
for group in with_paren_groups:
    print(f"  {group['person_id']}: {group['person_name_display']}")

# 統計
print()
print("📊 統計:")
print(f"  YouTuber総数: {len(youtubers)}")
print(f"  グループ候補: {len(potential_groups)}")
print(f"  括弧なし: {len([g for g in potential_groups if not g['has_parentheses']])}")
print(f"  括弧あり: {len([g for g in potential_groups if g['has_parentheses']])}")

# JSONに保存
output = {
    'total_youtubers': len(youtubers),
    'potential_groups': len(potential_groups),
    'no_parentheses': no_paren_groups,
    'with_parentheses': with_paren_groups[:10],
    'p000111_info': p000111.to_dict('records')[0] if not p000111.empty else None
}

with open('youtuber_groups_investigation.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\n📁 詳細は youtuber_groups_investigation.json に保存")
