#!/usr/bin/env python3
"""
P000104（はじめしゃちょー）と他の有名YouTuberの表記問題を調査
"""
import pandas as pd
import re

# 最新のCSVファイルを読み込み
df = pd.read_csv('ultra_think_JAPANESE_DISPLAY_FIXED_20250828_192840.csv')

print("🔍 P000104（はじめしゃちょー）の調査")
print("="*60)

# P000104のレコードを探す
p000104 = df[df['person_id'] == 'P000104']
if not p000104.empty:
    row = p000104.iloc[0]
    print(f"person_id: {row['person_id']}")
    print(f"person_name: {row['person_name']}")
    print(f"person_name_display: {row['person_name_display']}")
    print(f"person_name_ja: {row['person_name_ja']}")
    print(f"occupation: {row['occupation']}")
    print(f"nationality: {row['nationality']}")
    print(f"category: {row['category']}")
else:
    print("❌ P000104が見つかりません")

print("\n" + "="*60)
print("🎬 他の有名日本人YouTuberの調査")
print("="*60)

# 日本人YouTuberを抽出
japanese_youtubers = df[(df['nationality'] == '日本') & (df['occupation'] == 'YouTuber')]

# 有名YouTuberの名前パターン（ひらがな・カタカナが含まれるべき）
famous_patterns = [
    'HIKAKIN', 'SEIKIN', 'はじめ', 'Hajime', 'フィッシャーズ', 'Fischer',
    'ヒカル', 'Hikaru', 'ラファエル', 'Raphael', 'カジサック', 'Kajisac',
    'ゆきりぬ', 'Yukirinu', 'みきぽん', 'Mikipon', 'あやなん', 'Ayanan',
    'コムドット', 'Comdot', 'スカイピース', 'Skypiece', 'ばんばんざい', 'Banbanzai',
    '東海オンエア', 'Tokai', 'すしらーめん', 'Sushiramen', 'へきトラ', 'Hekitora'
]

# 問題のあるレコードを探す
problems = []

def has_japanese(text):
    """日本語文字が含まれているか確認"""
    if pd.isna(text):
        return False
    return bool(re.search(r'[\u3000-\u303F\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', str(text)))

def should_have_japanese_display(row):
    """日本語表記であるべきか判定"""
    # person_name_jaがひらがな・カタカナを含む場合
    if pd.notna(row['person_name_ja']) and has_japanese(row['person_name_ja']):
        # でもperson_name_displayが英語の場合
        if not has_japanese(row['person_name_display']):
            return True
    return False

# 有名YouTuberパターンにマッチするレコードを調査
for _, row in japanese_youtubers.iterrows():
    person_name = str(row['person_name'])
    person_name_ja = str(row['person_name_ja'])
    person_name_display = str(row['person_name_display'])
    
    # 有名YouTuberの可能性があるか
    is_famous = False
    for pattern in famous_patterns:
        if pattern.lower() in person_name.lower() or \
           pattern.lower() in person_name_ja.lower() or \
           pattern.lower() in person_name_display.lower():
            is_famous = True
            break
    
    # 問題があるか確認
    if should_have_japanese_display(row):
        problems.append({
            'person_id': row['person_id'],
            'person_name': person_name,
            'person_name_display': person_name_display,
            'person_name_ja': person_name_ja,
            'is_famous': is_famous
        })

print(f"\n📊 統計:")
print(f"日本人YouTuber総数: {len(japanese_youtubers)}")
print(f"問題のあるレコード: {len(problems)}")

# 有名YouTuberの問題を優先表示
famous_problems = [p for p in problems if p['is_famous']]
if famous_problems:
    print(f"\n⚠️ 有名YouTuberで問題のあるレコード ({len(famous_problems)}件):")
    for p in famous_problems[:10]:
        print(f"  {p['person_id']}: {p['person_name_display']} → {p['person_name_ja']}")

# その他の問題も表示
other_problems = [p for p in problems if not p['is_famous']]
if other_problems:
    print(f"\n📝 その他の問題レコード (最初の10件):")
    for p in other_problems[:10]:
        print(f"  {p['person_id']}: {p['person_name_display']} → {p['person_name_ja']}")

# HIKAKINやSEIKINの状態も確認
print("\n🎯 主要YouTuberの表記状態:")
check_names = ['HIKAKIN', 'SEIKIN', 'はじめ', 'Hajime', 'ヒカル', 'Hikaru']
for name in check_names:
    matches = df[
        (df['person_name'].str.contains(name, case=False, na=False)) |
        (df['person_name_ja'].str.contains(name, case=False, na=False)) |
        (df['person_name_display'].str.contains(name, case=False, na=False))
    ]
    if not matches.empty:
        for _, row in matches.head(1).iterrows():
            print(f"  {row['person_id']}: {row['person_name']} → {row['person_name_display']}")

print(f"\n💡 分析結果:")
print(f"  問題の原因: person_name_jaが存在するのにperson_name_displayに反映されていない")
print(f"  影響範囲: {len(problems)}件のYouTuberレコード")
if 'P000104' in [p['person_id'] for p in problems]:
    print(f"  P000104（はじめしゃちょー）も影響を受けている ⚠️")