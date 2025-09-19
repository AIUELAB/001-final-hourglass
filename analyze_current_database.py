#!/usr/bin/env python3
"""
現在のデータベースを分析して統計情報を表示
"""

import pandas as pd
from collections import Counter

# CSVファイルを読み込み
df = pd.read_csv('ultra_think_CLEANED_20250825_204705.csv')

print("=== データベース分析レポート ===\n")
print(f"総人数: {len(df):,}人\n")

# カテゴリー別分析
print("=== カテゴリー別分布 ===")
category_counts = df['main_category'].value_counts()
for cat, count in category_counts.head(20).items():
    print(f"{cat}: {count:,}人 ({count/len(df)*100:.1f}%)")

print("\n=== 国籍別分布 (Top 20) ===")
nationality_counts = df['nationality'].value_counts()
for nat, count in nationality_counts.head(20).items():
    print(f"{nat}: {count:,}人 ({count/len(df)*100:.1f}%)")

print("\n=== 職業別分布 (Top 20) ===")
occupation_counts = df['occupation'].value_counts()
for occ, count in occupation_counts.head(20).items():
    print(f"{occ}: {count:,}人")

# 生年情報の分析
print("\n=== 生年情報の分析 ===")
has_birth_year = df['birth_year'].notna().sum()
print(f"生年情報あり: {has_birth_year:,}人 ({has_birth_year/len(df)*100:.1f}%)")
print(f"生年情報なし: {len(df) - has_birth_year:,}人 ({(len(df) - has_birth_year)/len(df)*100:.1f}%)")

# 時代別分析（生年がある人のみ）
df_with_year = df[df['birth_year'].notna()].copy()
if len(df_with_year) > 0:
    df_with_year['century'] = ((df_with_year['birth_year'] - 1) // 100 + 1).astype(int)
    
    print("\n=== 世紀別分布 ===")
    century_counts = df_with_year['century'].value_counts().sort_index()
    for century, count in century_counts.items():
        if century > 0:
            print(f"{century}世紀: {count:,}人")
        else:
            print(f"紀元前: {count:,}人")

# グレード分析
print("\n=== グレード別分布 ===")
grade_counts = df['grade'].value_counts()
for grade, count in grade_counts.items():
    print(f"グレード {grade}: {count:,}人 ({count/len(df)*100:.1f}%)")

# プラットフォーム分析
print("\n=== プラットフォーム別分布 ===")
platform_counts = df['platform'].value_counts()
for platform, count in platform_counts.head(10).items():
    print(f"{platform}: {count:,}人")

# フェーズ分析
print("\n=== フェーズ別分布 ===")
phase_counts = df['phase'].value_counts()
for phase, count in phase_counts.items():
    print(f"{phase}: {count:,}人")