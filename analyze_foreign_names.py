#!/usr/bin/env python3
"""
外国語のperson_name_displayを持つレコードの調査スクリプト
"""

import pandas as pd
import re
from collections import Counter
import json

def is_foreign_name(name):
    """
    名前が外国語（主に英語）かどうかを判定
    ひらがな、カタカナ、漢字が含まれていない場合に外国語と判定
    """
    if not name or pd.isna(name):
        return False
    
    # 日本語文字（ひらがな、カタカナ、漢字）を含むかチェック
    japanese_pattern = r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]'
    has_japanese = bool(re.search(japanese_pattern, str(name)))
    
    # アルファベットを含むかチェック
    alphabet_pattern = r'[A-Za-z]'
    has_alphabet = bool(re.search(alphabet_pattern, str(name)))
    
    # 日本語がなく、アルファベットがある場合に外国語と判定
    return not has_japanese and has_alphabet

def analyze_foreign_names(csv_file):
    """CSVファイルの外国語名を分析"""
    print(f"=== {csv_file} の外国語person_name_display分析 ===\n")
    
    # CSVファイル読み込み
    try:
        df = pd.read_csv(csv_file)
        print(f"総レコード数: {len(df):,}")
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return
    
    # 必要な列の存在確認
    required_cols = ['person_name_display', 'person_name_ja']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        print(f"Missing columns: {missing_cols}")
        return
    
    print(f"person_name_displayの総数: {df['person_name_display'].notna().sum():,}")
    print(f"person_name_jaの総数: {df['person_name_ja'].notna().sum():,}")
    print()
    
    # 1. 外国語のperson_name_displayを持つレコードを特定
    df['is_foreign_display'] = df['person_name_display'].apply(is_foreign_name)
    foreign_display_df = df[df['is_foreign_display']]
    
    print(f"1. 外国語person_name_displayレコード数: {len(foreign_display_df):,}")
    print(f"   全体に占める割合: {len(foreign_display_df)/len(df)*100:.1f}%")
    print()
    
    # 2. person_name_jaフィールドの存在確認
    foreign_with_ja = foreign_display_df[foreign_display_df['person_name_ja'].notna()]
    foreign_without_ja = foreign_display_df[foreign_display_df['person_name_ja'].isna()]
    
    print(f"2. person_name_jaフィールドの状況:")
    print(f"   外国語displayでperson_name_jaあり: {len(foreign_with_ja):,}")
    print(f"   外国語displayでperson_name_jaなし: {len(foreign_without_ja):,}")
    print()
    
    # 3. 外国語displayでperson_name_jaに日本語名があるケースの例
    print("3. 外国語display + 日本語person_name_jaの例:")
    if len(foreign_with_ja) > 0:
        examples = foreign_with_ja[['person_name_display', 'person_name_ja', 'nationality', 'occupation']].head(20)
        for idx, row in examples.iterrows():
            print(f"   Display: {row['person_name_display']:30} -> JA: {row['person_name_ja']:20} ({row['nationality']}, {row['occupation']})")
    else:
        print("   該当なし")
    print()
    
    # 4. 芸名・アーティスト名として外国語を維持すべき例の検出
    print("4. 芸名・アーティスト名として外国語維持すべき例の分析:")
    
    # エンタメ・音楽系の職業
    artist_occupations = ['歌手', 'ミュージシャン', '俳優', '女優', 'アーティスト', 'タレント', 'ラッパー', 'DJ']
    artist_categories = ['エンタメ', '文化・芸術', '音楽']
    
    foreign_artists = foreign_display_df[
        (foreign_display_df['occupation'].isin(artist_occupations)) |
        (foreign_display_df['category'].isin(artist_categories))
    ]
    
    print(f"   外国語名のアーティスト/エンタメ系: {len(foreign_artists):,}件")
    
    # 国籍別の分布
    if len(foreign_artists) > 0:
        nationality_counts = foreign_artists['nationality'].value_counts()
        print("   国籍別分布:")
        for nat, count in nationality_counts.head(10).items():
            print(f"     {nat}: {count}件")
        print()
        
        # 具体例の表示
        print("   具体例（芸名として外国語維持が適切と思われるケース）:")
        examples = foreign_artists[['person_name_display', 'person_name_ja', 'nationality', 'occupation']].head(15)
        for idx, row in examples.iterrows():
            ja_part = f" -> {row['person_name_ja']}" if pd.notna(row['person_name_ja']) else ""
            print(f"     {row['person_name_display']:25}{ja_part:30} ({row['nationality']}, {row['occupation']})")
    print()
    
    # 5. 統計サマリー
    print("5. 統計サマリー:")
    
    # 国籍別外国語名分布
    if len(foreign_display_df) > 0:
        nat_foreign = foreign_display_df['nationality'].value_counts()
        print("   外国語displayの国籍別分布（上位10）:")
        for nat, count in nat_foreign.head(10).items():
            print(f"     {nat}: {count}件")
        print()
    
    # 職業別外国語名分布
    if len(foreign_display_df) > 0:
        occ_foreign = foreign_display_df['occupation'].value_counts()
        print("   外国語displayの職業別分布（上位10）:")
        for occ, count in occ_foreign.head(10).items():
            print(f"     {occ}: {count}件")
        print()
    
    # 6. 修正が必要そうなケース
    print("6. 修正検討が必要そうなケース:")
    
    # 日本人で外国語displayのケース
    japanese_foreign = foreign_display_df[foreign_display_df['nationality'] == '日本']
    if len(japanese_foreign) > 0:
        print(f"   日本人で外国語display: {len(japanese_foreign)}件")
        print("   例:")
        examples = japanese_foreign[['person_name_display', 'person_name_ja', 'occupation']].head(10)
        for idx, row in examples.iterrows():
            ja_part = f" -> {row['person_name_ja']}" if pd.notna(row['person_name_ja']) else " (日本語名なし)"
            print(f"     {row['person_name_display']:25}{ja_part:30} ({row['occupation']})")
    else:
        print("   該当なし")
    print()
    
    # 7. 結果をJSONで出力
    results = {
        'total_records': len(df),
        'foreign_display_count': len(foreign_display_df),
        'foreign_display_percentage': len(foreign_display_df)/len(df)*100,
        'foreign_with_ja_count': len(foreign_with_ja),
        'foreign_without_ja_count': len(foreign_without_ja),
        'foreign_artists_count': len(foreign_artists),
        'japanese_with_foreign_display': len(japanese_foreign),
        'nationality_distribution': nat_foreign.to_dict() if len(foreign_display_df) > 0 else {},
        'occupation_distribution': occ_foreign.to_dict() if len(foreign_display_df) > 0 else {}
    }
    
    output_file = 'foreign_names_analysis_results.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"詳細結果を {output_file} に出力しました。")
    
    return foreign_display_df

if __name__ == "__main__":
    csv_file = "ultra_think_NO_FAKE_RESEARCHERS_20250827_143418.csv"
    foreign_df = analyze_foreign_names(csv_file)