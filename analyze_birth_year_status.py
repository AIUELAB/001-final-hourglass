#!/usr/bin/env python3
"""
誕生年の詳細分析スクリプト
架空キャラクターと実在人物を分類し、収集優先順位を決定
"""

import pandas as pd
from datetime import datetime
from collections import Counter

def analyze_birth_year_status():
    """誕生年の現状を詳細分析"""

    # CSVファイルを読み込み
    input_file = 'ultra_think_WITH_BIRTH_DATES_SIMPLE_20250917_113030.csv'
    print(f"Loading {input_file}...")

    df = pd.read_csv(input_file, encoding='utf-8-sig')
    print(f"Total records: {len(df)}")

    # 基本統計
    print("\n=== 基本統計 ===")
    print(f"Total records: {len(df)}")
    print(f"Records with birth_year_int: {df['birth_year_int'].notna().sum()} ({df['birth_year_int'].notna().sum()/len(df)*100:.1f}%)")
    print(f"Records missing birth_year_int: {df['birth_year_int'].isna().sum()} ({df['birth_year_int'].isna().sum()/len(df)*100:.1f}%)")

    # entity_typeごとの分析
    print("\n=== Entity Type別分析 ===")
    entity_types = df['entity_type'].value_counts()
    for entity_type, count in entity_types.items():
        df_type = df[df['entity_type'] == entity_type]
        with_year = df_type['birth_year_int'].notna().sum()
        without_year = df_type['birth_year_int'].isna().sum()
        print(f"\n{entity_type}: {count}人")
        print(f"  - 誕生年あり: {with_year} ({with_year/count*100:.1f}%)")
        print(f"  - 誕生年なし: {without_year} ({without_year/count*100:.1f}%)")

        # fame_score上位を表示
        if without_year > 0:
            top_missing = df_type[df_type['birth_year_int'].isna()].nlargest(5, 'fame_score')[['person_name_display', 'fame_score', 'category']]
            print(f"  - 誕生年欠落上位5名:")
            for _, row in top_missing.iterrows():
                print(f"    • {row['person_name_display']} (fame:{row['fame_score']:.0f}, {row['category']})")

    # 架空キャラクターの詳細分析
    print("\n=== 架空キャラクター詳細分析 ===")
    fictional_df = df[df['entity_type'] == 'fictional_character']
    print(f"Total fictional characters: {len(fictional_df)}")

    # カテゴリ別
    print("\n架空キャラクターのカテゴリ分布:")
    for category, count in fictional_df['category'].value_counts().head(10).items():
        df_cat = fictional_df[fictional_df['category'] == category]
        with_year = df_cat['birth_year_int'].notna().sum()
        print(f"  {category}: {count}人 (誕生年あり: {with_year})")

    # fame_score上位の架空キャラクター
    print("\n有名な架空キャラクター（fame_score上位20）:")
    top_fictional = fictional_df.nlargest(20, 'fame_score')[['person_name_display', 'fame_score', 'category', 'birth_year_int']]
    for _, row in top_fictional.iterrows():
        year_str = f"{int(row['birth_year_int'])}年" if pd.notna(row['birth_year_int']) else "未設定"
        print(f"  {row['person_name_display']}: fame={row['fame_score']:.0f}, {row['category']}, 誕生年={year_str}")

    # 異常な誕生年の検出
    print("\n=== 異常な誕生年の検出 ===")
    df_with_year = df[df['birth_year_int'].notna()].copy()
    df_with_year['birth_year_int'] = df_with_year['birth_year_int'].astype(int)

    # 未来の年（2025年以降）
    future_births = df_with_year[df_with_year['birth_year_int'] > 2024]
    if len(future_births) > 0:
        print(f"\n未来の誕生年（エラー候補）: {len(future_births)}件")
        for _, row in future_births.head(10).iterrows():
            print(f"  {row['person_name_display']}: {row['birth_year_int']}年 ({row['category']})")

    # 非常に古い年（1800年以前）
    ancient_births = df_with_year[df_with_year['birth_year_int'] < 1800]
    if len(ancient_births) > 0:
        print(f"\n1800年以前の誕生年: {len(ancient_births)}件")
        for _, row in ancient_births.head(10).iterrows():
            print(f"  {row['person_name_display']}: {row['birth_year_int']}年 ({row['category']})")

    # カテゴリ別の誕生年カバレッジ
    print("\n=== カテゴリ別誕生年カバレッジ ===")
    categories = df['category'].value_counts()
    for category, total in categories.head(10).items():
        df_cat = df[df['category'] == category]
        with_year = df_cat['birth_year_int'].notna().sum()
        coverage = with_year / total * 100
        print(f"{category}: {with_year}/{total} ({coverage:.1f}%)")

    # 収集優先順位の提案
    print("\n=== 誕生年収集の優先順位（提案）===")

    # 実在人物で誕生年なし、fame_score高い順
    real_missing = df[(df['entity_type'] == 'person') & (df['birth_year_int'].isna())]
    print(f"\n1. 実在人物・高fame_score（上位30名）:")
    for _, row in real_missing.nlargest(30, 'fame_score').iterrows():
        print(f"  {row['person_name_display']}: fame={row['fame_score']:.0f}, {row['category']}")

    # 架空キャラクターで誕生年なし、fame_score高い順
    fictional_missing = df[(df['entity_type'] == 'fictional_character') & (df['birth_year_int'].isna())]
    print(f"\n2. 架空キャラクター・高fame_score（上位20名）:")
    for _, row in fictional_missing.nlargest(20, 'fame_score').iterrows():
        print(f"  {row['person_name_display']}: fame={row['fame_score']:.0f}, {row['category']}")

    # 統計サマリー
    print("\n=== 収集対象サマリー ===")
    print(f"実在人物で誕生年欠落: {len(real_missing)}人")
    print(f"架空キャラクターで誕生年欠落: {len(fictional_missing)}人")
    print(f"合計収集対象: {len(real_missing) + len(fictional_missing)}人")

    # CSVファイルに優先順位リストを出力
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 実在人物優先リスト
    real_priority = real_missing.nlargest(500, 'fame_score')[['person_name_display', 'fame_score', 'category', 'wikipedia_url']]
    real_priority.to_csv(f'birth_year_priority_real_{timestamp}.csv', index=False, encoding='utf-8-sig')
    print(f"\n実在人物優先リスト出力: birth_year_priority_real_{timestamp}.csv")

    # 架空キャラクター優先リスト
    fictional_priority = fictional_missing.nlargest(200, 'fame_score')[['person_name_display', 'fame_score', 'category', 'wikipedia_url']]
    fictional_priority.to_csv(f'birth_year_priority_fictional_{timestamp}.csv', index=False, encoding='utf-8-sig')
    print(f"架空キャラクター優先リスト出力: birth_year_priority_fictional_{timestamp}.csv")

    return df

if __name__ == '__main__':
    df = analyze_birth_year_status()