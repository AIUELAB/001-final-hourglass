#!/usr/bin/env python3
"""
name_recognitionフィールドを0-100,000の範囲に拡張
より細分化された知名度スコアを生成
"""

import pandas as pd
import numpy as np
from datetime import datetime

def expand_recognition_score(df):
    """
    name_recognitionを0-100,000の範囲に拡張
    """
    print("=" * 60)
    print("📊 name_recognition拡張処理")
    print("=" * 60)

    # 現在の値を確認
    current_min = df['name_recognition'].min()
    current_max = df['name_recognition'].max()
    current_mean = df['name_recognition'].mean()

    print(f"\n📈 現在の統計:")
    print(f"  範囲: {current_min:.0f} - {current_max:.0f}")
    print(f"  平均: {current_mean:.1f}")

    # 拡張用の複合スコアを計算
    df['composite_score'] = 0

    # 1. 基本スコア（現在のname_recognition）を1000倍
    df['composite_score'] += df['name_recognition'].fillna(0) * 1000

    # 2. Wikipedia記事の長さによる補正（0-20,000）
    if 'wikipedia_content_length' in df.columns:
        max_content = df['wikipedia_content_length'].max()
        if max_content > 0:
            df['composite_score'] += (df['wikipedia_content_length'].fillna(0) / max_content) * 20000

    # 3. 検索結果数による補正（0-30,000）
    if 'search_result_count' in df.columns:
        # 対数スケールで正規化（検索結果は指数的に増加するため）
        search_log = np.log10(df['search_result_count'].fillna(1) + 1)
        max_search_log = search_log.max()
        if max_search_log > 0:
            df['composite_score'] += (search_log / max_search_log) * 30000

    # 4. impact_scoreによる補正（0-10,000）
    if 'impact_score' in df.columns:
        df['composite_score'] += df['impact_score'].fillna(0) * 100

    # 5. カテゴリによる基礎点
    category_base_scores = {
        '政治': 15000,
        'エンタメ': 12000,
        'スポーツ': 10000,
        '科学': 8000,
        'ビジネス': 7000,
        '芸術': 6000,
        '歴史': 5000,
        'その他': 3000,
        '架空の存在': 2000
    }

    if 'category' in df.columns:
        for category, base_score in category_base_scores.items():
            mask = df['category'] == category
            df.loc[mask, 'composite_score'] += base_score

    # 6. 活動タイプによる補正
    activity_multipliers = {
        'solo': 1.2,
        'group': 1.0,
        'historical': 0.8,
        'fictional': 0.5
    }

    if 'activity_type' in df.columns:
        for activity, multiplier in activity_multipliers.items():
            mask = df['activity_type'] == activity
            df.loc[mask, 'composite_score'] *= multiplier

    # 7. Wikipedia有無による補正
    if 'wikipedia_url' in df.columns:
        has_wikipedia = df['wikipedia_url'].notna() & (df['wikipedia_url'] != '')
        df.loc[has_wikipedia, 'composite_score'] *= 1.3

    # 8. 特別な人物への追加点（有名人の例）
    special_persons = {
        'HIKAKIN': 95000,
        '安倍晋三': 92000,
        'イチロー': 90000,
        '松本人志': 88000,
        '明石家さんま': 87000,
        'ビートたけし': 86000,
        '大谷翔平': 85000,
        '羽生結弦': 83000,
        '新垣結衣': 82000,
        '米津玄師': 80000
    }

    for person, min_score in special_persons.items():
        mask = df['person_name_display'].str.contains(person, na=False)
        df.loc[mask, 'composite_score'] = df.loc[mask, 'composite_score'].clip(lower=min_score)

    # 最終的なスコアを0-100,000の範囲に正規化
    min_score = df['composite_score'].min()
    max_score = df['composite_score'].max()

    if max_score > min_score:
        df['name_recognition_expanded'] = ((df['composite_score'] - min_score) /
                                           (max_score - min_score)) * 100000
    else:
        df['name_recognition_expanded'] = df['composite_score']

    # 小数点以下も保持（細分化）
    df['name_recognition_expanded'] = df['name_recognition_expanded'].round(2)

    # 元のname_recognitionフィールドを更新
    df['name_recognition_original'] = df['name_recognition'].copy()  # 元の値を保存
    df['name_recognition'] = df['name_recognition_expanded']

    # 不要なカラムを削除
    df = df.drop(['composite_score', 'name_recognition_expanded'], axis=1)

    return df

def show_statistics(df):
    """統計情報を表示"""
    print("\n📊 拡張後の統計:")
    print(f"  範囲: {df['name_recognition'].min():.2f} - {df['name_recognition'].max():.2f}")
    print(f"  平均: {df['name_recognition'].mean():.2f}")
    print(f"  中央値: {df['name_recognition'].median():.2f}")
    print(f"  標準偏差: {df['name_recognition'].std():.2f}")

    # 分布を表示
    print("\n📈 分布:")
    bins = [0, 10000, 20000, 30000, 40000, 50000, 60000, 70000, 80000, 90000, 100000]
    labels = ['0-10k', '10-20k', '20-30k', '30-40k', '40-50k',
              '50-60k', '60-70k', '70-80k', '80-90k', '90-100k']

    df['range'] = pd.cut(df['name_recognition'], bins=bins, labels=labels, include_lowest=True)
    distribution = df['range'].value_counts().sort_index()

    for range_label, count in distribution.items():
        bar_length = int(count / len(df) * 50)
        bar = '█' * bar_length
        print(f"  {range_label:8s}: {bar} {count:4d}件 ({count/len(df)*100:.1f}%)")

    # トップ10を表示
    print("\n🏆 トップ10:")
    top10 = df.nlargest(10, 'name_recognition')[['person_name_display', 'name_recognition', 'category']]
    for i, (_, row) in enumerate(top10.iterrows(), 1):
        print(f"  {i:2d}. {row['person_name_display']:20s}: {row['name_recognition']:,.2f} ({row['category']})")

def main():
    # データ読み込み
    input_file = 'ultra_think_with_search_counts_20250915_140948.csv'

    print(f"📂 ファイル読み込み: {input_file}")
    df = pd.read_csv(input_file)
    print(f"✅ {len(df)}件のデータを読み込みました")

    # name_recognition拡張
    df = expand_recognition_score(df)

    # 統計表示
    show_statistics(df)

    # 保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'ultra_think_expanded_recognition_{timestamp}.csv'

    # UTF-8 BOMで保存（Excel対応）
    with open(output_file, 'w', encoding='utf-8-sig') as f:
        df.to_csv(f, index=False)

    print(f"\n✅ 保存完了: {output_file}")

    # sheets_config.jsonを更新
    import json
    config_file = 'sheets_config.json'
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)

        config['csv_file'] = output_file
        config['latest_csv'] = output_file
        config['recognition_expanded'] = True
        config['recognition_range'] = '0-100000'
        config['last_expanded'] = timestamp

        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        print(f"✅ 設定ファイル更新: {config_file}")

if __name__ == "__main__":
    import os
    main()
