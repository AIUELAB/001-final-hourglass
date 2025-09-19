#!/usr/bin/env python3
"""
Ultra Think データベース現状調査スクリプト
"""

import pandas as pd
import re
from typing import Dict, Any

def analyze_ultra_think_database(csv_path: str) -> Dict[str, Any]:
    """Ultra Thinkデータベースの現状を分析する"""
    
    # CSVファイル読み込み
    print(f"📊 ファイル読み込み中: {csv_path}")
    df = pd.read_csv(csv_path)
    
    print(f"✅ 読み込み完了: {len(df):,} レコード")
    print("-" * 80)
    
    results = {}
    
    # 1. データセット概要
    results['dataset_overview'] = {
        'total_records': len(df),
        'total_columns': len(df.columns),
        'file_name': csv_path.split('/')[-1]
    }
    
    print(f"📋 データセット概要")
    print(f"   総レコード数: {results['dataset_overview']['total_records']:,}")
    print(f"   カラム数: {results['dataset_overview']['total_columns']}")
    print("-" * 80)
    
    # 2. person_name_display列の外国語名分析
    print("🌍 person_name_display列の外国語名分析")
    
    # 外国語パターン定義
    patterns = {
        '英語': r'[A-Za-z]',  # アルファベット
        '中国語': r'[\u4e00-\u9fff]',  # 中国語（簡体字・繁体字）
        '韓国語': r'[\uac00-\ud7af]',  # ハングル
    }
    
    foreign_name_counts = {}
    total_foreign = 0
    
    for lang, pattern in patterns.items():
        mask = df['person_name_display'].str.contains(pattern, na=False, regex=True)
        count = mask.sum()
        foreign_name_counts[lang] = count
        
        print(f"   {lang}名: {count:,} 件")
        
        # サンプル表示
        if count > 0:
            samples = df[mask]['person_name_display'].head(3).tolist()
            print(f"     サンプル: {', '.join(samples)}")
        
        total_foreign += count
    
    # カタカナのみ（外国語のカタカナ表記）
    katakana_only = df['person_name_display'].str.contains(r'^[\u30a0-\u30ff\s・]+$', na=False, regex=True)
    katakana_count = katakana_only.sum()
    foreign_name_counts['カタカナ表記'] = katakana_count
    print(f"   カタカナ表記: {katakana_count:,} 件")
    
    if katakana_count > 0:
        samples = df[katakana_only]['person_name_display'].head(3).tolist()
        print(f"     サンプル: {', '.join(samples)}")
    
    results['foreign_names'] = foreign_name_counts
    print("-" * 80)
    
    # 3. occupation列の特定職業分析
    print("💼 occupation列の職業分析")
    
    # 架空キャラクター
    fictional_mask1 = df['occupation'] == '架空キャラクター'
    fictional_mask2 = df['category'] == '架空の存在'
    fictional_total = (fictional_mask1 | fictional_mask2).sum()
    
    # お笑い芸人
    comedian_mask = df['occupation'] == 'お笑い芸人'
    comedian_count = comedian_mask.sum()
    
    # YouTuber
    youtuber_mask = df['occupation'] == 'YouTuber'
    youtuber_count = youtuber_mask.sum()
    
    occupation_counts = {
        '架空キャラクター': fictional_total,
        'お笑い芸人': comedian_count,
        'YouTuber': youtuber_count
    }
    
    for occupation, count in occupation_counts.items():
        print(f"   {occupation}: {count:,} 件")
        
        # サンプル表示
        if occupation == '架空キャラクター':
            mask = fictional_mask1 | fictional_mask2
        else:
            mask = df['occupation'] == occupation
            
        if count > 0:
            samples = df[mask][['person_name_display', 'person_name_ja']].head(3)
            for _, row in samples.iterrows():
                print(f"     - {row['person_name_display']} ({row['person_name_ja']})")
    
    results['occupation_counts'] = occupation_counts
    print("-" * 80)
    
    # 4. person_name_ja列の充実度分析
    print("🇯🇵 person_name_ja列の充実度分析")
    
    # 非null値の確認
    ja_not_null = df['person_name_ja'].notna()
    ja_not_empty = df['person_name_ja'].str.strip() != ''
    ja_valid = ja_not_null & ja_not_empty
    
    ja_valid_count = ja_valid.sum()
    ja_missing_count = len(df) - ja_valid_count
    ja_coverage_rate = (ja_valid_count / len(df)) * 100
    
    ja_analysis = {
        'total_records': len(df),
        'with_japanese_name': ja_valid_count,
        'missing_japanese_name': ja_missing_count,
        'coverage_rate': ja_coverage_rate
    }
    
    print(f"   総レコード数: {ja_analysis['total_records']:,}")
    print(f"   日本語名あり: {ja_analysis['with_japanese_name']:,} 件")
    print(f"   日本語名なし: {ja_analysis['missing_japanese_name']:,} 件")
    print(f"   充実度: {ja_analysis['coverage_rate']:.2f}%")
    
    # 日本語名が不足しているサンプル
    if ja_missing_count > 0:
        missing_samples = df[~ja_valid][['person_name_display', 'person_name_ja', 'nationality']].head(5)
        print(f"\n   日本語名が不足している例:")
        for _, row in missing_samples.iterrows():
            print(f"     - {row['person_name_display']} (国籍: {row['nationality']})")
    
    results['japanese_name_analysis'] = ja_analysis
    print("-" * 80)
    
    # 5. 総合サマリー
    print("📊 総合サマリー")
    print(f"   データベース名: {results['dataset_overview']['file_name']}")
    print(f"   総レコード数: {results['dataset_overview']['total_records']:,}")
    print(f"   外国語名: 英語{results['foreign_names']['英語']:,}件, 中国語{results['foreign_names']['中国語']:,}件, 韓国語{results['foreign_names']['韓国語']:,}件")
    print(f"   特定職業: 架空キャラクター{results['occupation_counts']['架空キャラクター']:,}件, お笑い芸人{results['occupation_counts']['お笑い芸人']:,}件, YouTuber{results['occupation_counts']['YouTuber']:,}件")
    print(f"   日本語名充実度: {results['japanese_name_analysis']['coverage_rate']:.2f}%")
    
    return results

if __name__ == "__main__":
    csv_file = "/Users/admin/Documents/AIUELAB/001-final-hourglass/ultra_think_CONVERTED_20250827_224054.csv"
    results = analyze_ultra_think_database(csv_file)
    print("\n✅ 分析完了")