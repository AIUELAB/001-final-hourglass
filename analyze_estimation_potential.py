#!/usr/bin/env python3
"""
生年推定の可能性を分析
既存データから推定可能なパターンを発見
"""

import pandas as pd
import re
from collections import Counter
from datetime import datetime

def analyze_estimation_potential(csv_file):
    """推定可能なデータパターンを分析"""

    print("=" * 80)
    print("🔍 生年推定可能性分析")
    print("=" * 80)

    # データ読み込み
    df = pd.read_csv(csv_file, encoding='utf-8-sig')
    total_records = len(df)

    # 生年データがない記録を対象
    no_birth_year = df[df['birth_year_int'].isna()]
    missing_count = len(no_birth_year)

    print(f"\n📊 基本統計:")
    print(f"  - 総レコード数: {total_records:,}")
    print(f"  - 生年データなし: {missing_count:,} ({missing_count/total_records*100:.1f}%)")

    # 推定可能なパターンを分析
    patterns = {
        'debut_year': 0,      # デビュー年あり
        'group_member': 0,    # グループメンバー
        'historical': 0,      # 歴史上の人物
        'generation': 0,      # 世代情報あり
        'parent_child': 0,    # 親子関係
        'contemporary': 0,    # 同時代人
        'award_year': 0,      # 受賞年あり
        'graduation': 0,      # 卒業年あり
    }

    print("\n🎯 推定可能パターン分析:")

    # 1. デビュー年パターン（芸能人）
    if 'debut_year' in df.columns:
        debut_available = no_birth_year['debut_year'].notna()
        patterns['debut_year'] = debut_available.sum()
        print(f"  1. デビュー年から推定可能: {patterns['debut_year']:,}件")

    # 2. グループメンバーパターン
    if 'group_name' in df.columns:
        groups = no_birth_year[no_birth_year['group_name'].notna()]['group_name'].value_counts()
        multi_member_groups = groups[groups > 1]
        patterns['group_member'] = len(no_birth_year[no_birth_year['group_name'].isin(multi_member_groups.index)])
        print(f"  2. グループメンバーから推定可能: {patterns['group_member']:,}件")

    # 3. 職業別推定可能性
    if 'occupation' in df.columns:
        occupation_analysis = no_birth_year['occupation'].value_counts().head(10)
        print("\n📋 職業別分析（生年なし）:")
        for occ, count in occupation_analysis.items():
            # 職業別の推定ロジック適用可能性
            if occ in ['野球選手', 'サッカー選手', 'プロレスラー']:
                print(f"    {occ}: {count:,}件 → 引退年から推定可能")
            elif occ in ['俳優', '歌手', 'お笑い芸人']:
                print(f"    {occ}: {count:,}件 → デビュー年から推定可能")
            elif occ in ['政治家', '大統領', '首相']:
                print(f"    {occ}: {count:,}件 → 在任期間から推定可能")
            else:
                print(f"    {occ}: {count:,}件")

    # 4. Wikipedia URLパターン分析
    if 'wikipedia_url' in df.columns:
        wiki_pattern = no_birth_year[no_birth_year['wikipedia_url'].notna()]

        # URLから年代情報を抽出
        year_in_url = 0
        for url in wiki_pattern['wikipedia_url'].dropna():
            if re.search(r'(19|20)\d{2}', str(url)):
                year_in_url += 1

        print(f"\n  4. Wikipedia URLに年代情報: {year_in_url:,}件")

    # 5. 名前から世代推定
    generation_keywords = {
        '一世': 1900,  # ～世パターン
        '二世': 1930,
        'Jr': 1960,
        'ジュニア': 1960,
    }

    generation_count = 0
    for keyword in generation_keywords:
        mask = no_birth_year['person_name_ja'].str.contains(keyword, na=False)
        generation_count += mask.sum()

    patterns['generation'] = generation_count
    print(f"  5. 世代情報から推定可能: {generation_count:,}件")

    # 6. カテゴリ別分析
    if 'category' in df.columns:
        print("\n📊 カテゴリ別推定可能性:")
        category_analysis = no_birth_year['category'].value_counts()

        for cat, count in category_analysis.items():
            if cat == '歴史的偉人':
                print(f"    {cat}: {count:,}件 → 歴史記録から推定可能")
            elif cat == 'スポーツ':
                print(f"    {cat}: {count:,}件 → 現役/引退情報から推定可能")
            elif cat == 'エンタメ':
                print(f"    {cat}: {count:,}件 → デビュー年から推定可能")
            else:
                print(f"    {cat}: {count:,}件")

    # 推定可能総数
    total_estimable = sum(patterns.values())
    print("\n" + "=" * 80)
    print("📈 推定可能性サマリー:")
    print("=" * 80)
    print(f"✅ 推定可能レコード数: 約{total_estimable:,}件")
    print(f"📊 カバー率向上見込み: {total_estimable/total_records*100:.1f}%")
    print(f"🎯 推定後の予想カバー率: {(total_records-missing_count+total_estimable)/total_records*100:.1f}%")

    return patterns, no_birth_year

if __name__ == "__main__":
    # 最新のCSVファイルを使用
    csv_file = "ultra_think_WITH_BIRTH_DATES_BATCH5_20250917_094115.csv"
    patterns, missing_df = analyze_estimation_potential(csv_file)

    # 推定可能なレコードをCSVに出力
    output_file = f"estimation_candidates_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    missing_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n💾 推定候補を保存: {output_file}")