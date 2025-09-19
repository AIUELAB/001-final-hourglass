#!/usr/bin/env python3
"""
データベース内の知名度分布と削除候補の深層分析
4,701レコードの詳細分析と削除候補特定

実行例:
python3 analyze_database_distribution.py
"""

import pandas as pd
import json
import numpy as np
from collections import Counter, defaultdict
from datetime import datetime
import re

def load_database():
    """データベースCSVを読み込み"""
    try:
        df = pd.read_csv('ultra_think_EPISODE_FINAL_20250901_020106.csv')
        print(f"✓ データベース読み込み完了: {len(df):,} レコード")
        return df
    except FileNotFoundError:
        print("❌ データベースファイルが見つかりません")
        return None

def analyze_recognition_distribution(df):
    """知名度分布の詳細分析"""
    print("\n=== 📊 知名度分布分析 ===")
    
    # 基本統計
    recognition_stats = df['name_recognition'].describe()
    print(f"知名度スコア統計:")
    print(f"  平均値: {recognition_stats['mean']:.1f}")
    print(f"  中央値: {recognition_stats['50%']:.1f}")
    print(f"  標準偏差: {recognition_stats['std']:.1f}")
    print(f"  範囲: {recognition_stats['min']:.0f} - {recognition_stats['max']:.0f}")
    
    # 分布詳細
    recognition_counts = df['name_recognition'].value_counts().sort_index()
    print(f"\n知名度別人数分布:")
    for score, count in recognition_counts.head(10).items():
        percentage = count / len(df) * 100
        print(f"  {score}点: {count:,}人 ({percentage:.1f}%)")
    
    # 疑わしいデフォルト値35の分析
    default_35_count = (df['name_recognition'] == 35).sum()
    print(f"\n🚨 疑わしいデフォルト値35: {default_35_count:,}人 ({default_35_count/len(df)*100:.1f}%)")
    
    return recognition_counts

def analyze_metadata_quality(df):
    """メタデータ品質分析"""
    print("\n=== 🔍 メタデータ品質分析 ===")
    
    # 不明データの分析
    unknown_occupation = (df['occupation'] == '不明').sum()
    unknown_nationality = (df['nationality'] == '不明').sum()
    
    print(f"不明データ:")
    print(f"  職業不明: {unknown_occupation:,}人 ({unknown_occupation/len(df)*100:.1f}%)")
    print(f"  国籍不明: {unknown_nationality:,}人 ({unknown_nationality/len(df)*100:.1f}%)")
    
    # 複合条件での削除候補
    both_unknown = ((df['occupation'] == '不明') & (df['nationality'] == '不明')).sum()
    print(f"  職業・国籍両方不明: {both_unknown:,}人 ({both_unknown/len(df)*100:.1f}%)")
    
    # カテゴリ分布
    category_dist = df['category'].value_counts()
    print(f"\nカテゴリ分布:")
    for category, count in category_dist.items():
        percentage = count / len(df) * 100
        print(f"  {category}: {count:,}人 ({percentage:.1f}%)")
    
    return {
        'unknown_occupation': unknown_occupation,
        'unknown_nationality': unknown_nationality,
        'both_unknown': both_unknown,
        'category_dist': category_dist
    }

def parse_extended_data(df):
    """extended_dataフィールドの解析"""
    print("\n=== 🔧 Extended Data分析 ===")
    
    fictional_count = 0
    batch_analysis = defaultdict(int)
    
    for idx, row in df.iterrows():
        try:
            extended_data = json.loads(row['extended_data'])
            
            # 架空キャラクター判定
            if extended_data.get('is_fictional') == 'TRUE':
                fictional_count += 1
            
            # バッチ分析
            batch_id = extended_data.get('original_batch_id', 'unknown')
            batch_analysis[batch_id] += 1
            
        except (json.JSONDecodeError, TypeError):
            continue
    
    print(f"架空キャラクター: {fictional_count}人")
    print(f"\nバッチ別分布 (上位10):")
    for batch, count in sorted(batch_analysis.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {batch}: {count}人")
    
    return fictional_count, batch_analysis

def identify_deletion_candidates(df):
    """削除候補の特定"""
    print("\n=== ❌ 削除候補特定システム ===")
    
    deletion_candidates = []
    
    # 条件1: デフォルト認知度35 + 職業不明
    condition1 = (df['name_recognition'] == 35) & (df['occupation'] == '不明')
    candidates1 = df[condition1]
    print(f"条件1 (認知度35 + 職業不明): {len(candidates1):,}人")
    
    # 条件2: 認知度30以下
    condition2 = df['name_recognition'] <= 30
    candidates2 = df[condition2]
    print(f"条件2 (認知度30以下): {len(candidates2):,}人")
    
    # 条件3: 国籍・職業両方不明 + 認知度35
    condition3 = (df['nationality'] == '不明') & (df['occupation'] == '不明') & (df['name_recognition'] == 35)
    candidates3 = df[condition3]
    print(f"条件3 (両方不明 + 認知度35): {len(candidates3):,}人")
    
    # 条件4: YouTube系だが認知度が異常に低い
    condition4 = (df['occupation'].str.contains('YouTube', na=False)) & (df['name_recognition'] < 35)
    candidates4 = df[condition4]
    print(f"条件4 (YouTube系だが低認知度): {len(candidates4):,}人")
    
    # 統合削除候補リスト作成
    all_candidates = pd.concat([candidates1, candidates2, candidates3, candidates4]).drop_duplicates()
    
    print(f"\n🎯 統合削除候補: {len(all_candidates):,}人 ({len(all_candidates)/len(df)*100:.1f}%)")
    
    return {
        'condition1': candidates1,
        'condition2': candidates2, 
        'condition3': candidates3,
        'condition4': candidates4,
        'all_candidates': all_candidates
    }

def analyze_protected_entities(df):
    """保護すべきエンティティの分析"""
    print("\n=== 🛡️ 保護対象分析 ===")
    
    protected_count = 0
    protected_categories = []
    
    # 歴史的人物（era情報がある）
    historical = df[df['era'].notna() & (df['era'] != '')]
    print(f"歴史的人物: {len(historical):,}人")
    
    # 架空キャラクター判定
    fictional_count = 0
    for idx, row in df.iterrows():
        try:
            extended_data = json.loads(row['extended_data'])
            if extended_data.get('is_fictional') == 'TRUE':
                fictional_count += 1
        except:
            continue
    
    print(f"架空キャラクター: {fictional_count}人")
    
    # 高認知度エンタメ人物
    high_recognition_entertainment = df[
        (df['category'] == 'エンタメ') & 
        (df['name_recognition'] >= 50)
    ]
    print(f"高認知度エンタメ人物: {len(high_recognition_entertainment):,}人")
    
    # VTuber/YouTuber（エンタメ価値）
    vtuber_youtuber = df[
        df['occupation'].str.contains('VTuber|YouTuber', na=False, case=False)
    ]
    print(f"VTuber/YouTuber: {len(vtuber_youtuber):,}人")
    
    # ミュージシャン/アーティスト
    musicians = df[
        df['occupation'].str.contains('ミュージシャン|歌手|アーティスト|ギタリスト|ドラマー|ベーシスト', na=False)
    ]
    print(f"ミュージシャン/アーティスト: {len(musicians):,}人")
    
    return {
        'historical': len(historical),
        'fictional': fictional_count,
        'high_recognition_entertainment': len(high_recognition_entertainment),
        'vtuber_youtuber': len(vtuber_youtuber),
        'musicians': len(musicians)
    }

def create_deletion_priority_score(df):
    """複合スコアリングシステムによる削除優先度"""
    print("\n=== 🎯 複合スコアリングシステム ===")
    
    df_copy = df.copy()
    df_copy['deletion_score'] = 0
    
    # スコア計算
    for idx, row in df_copy.iterrows():
        score = 0
        
        # 1. 認知度スコア (40%)
        recognition = row['name_recognition']
        if recognition <= 30:
            score += 40
        elif recognition == 35:  # デフォルト値疑い
            score += 30
        elif recognition <= 40:
            score += 20
        elif recognition <= 50:
            score += 10
        
        # 2. メタデータ不完全性 (30%)
        if row['occupation'] == '不明':
            score += 15
        if row['nationality'] == '不明':
            score += 15
        
        # 3. カテゴリ重要度 (20%)
        category = row['category']
        if category in ['その他', '現代のイノベーター']:
            score += 20
        elif category in ['エンタメ', '文化・芸術']:
            score += 5  # 保護対象
        
        # 4. 特別保護要素 (-30%)
        occupation = str(row['occupation']).lower()
        if any(keyword in occupation for keyword in ['vtuber', 'youtuber', 'ミュージシャン', '歌手']):
            score -= 30
        
        # 歴史的人物保護
        if pd.notna(row['era']) and row['era'] != '':
            score -= 30
        
        # 架空キャラクター保護
        try:
            extended_data = json.loads(row['extended_data'])
            if extended_data.get('is_fictional') == 'TRUE':
                score -= 30
        except:
            pass
        
        df_copy.loc[idx, 'deletion_score'] = max(0, min(100, score))
    
    # 高スコア削除候補
    high_priority = df_copy[df_copy['deletion_score'] >= 70]
    medium_priority = df_copy[(df_copy['deletion_score'] >= 50) & (df_copy['deletion_score'] < 70)]
    
    print(f"高優先度削除候補 (スコア70+): {len(high_priority):,}人")
    print(f"中優先度削除候補 (スコア50-69): {len(medium_priority):,}人")
    
    return high_priority, medium_priority, df_copy

def generate_detailed_report(df, analysis_results):
    """詳細レポート生成"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"DATABASE_DISTRIBUTION_ANALYSIS_{timestamp}.md"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# データベース知名度分布と削除候補分析レポート\n\n")
        f.write(f"**分析日時**: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}\n")
        f.write(f"**対象データベース**: ultra_think_EPISODE_FINAL_20250901_020106.csv\n")
        f.write(f"**総レコード数**: {len(df):,}件\n\n")
        
        f.write("## 🚨 主要発見事項\n\n")
        f.write("### 疑わしいデフォルト値\n")
        default_35_count = (df['name_recognition'] == 35).sum()
        f.write(f"- **認知度35のレコード**: {default_35_count:,}件 ({default_35_count/len(df)*100:.1f}%)\n")
        f.write("- これらは一律デフォルト値の可能性が高い\n\n")
        
        f.write("### データ品質問題\n")
        unknown_occupation = (df['occupation'] == '不明').sum()
        unknown_nationality = (df['nationality'] == '不明').sum()
        f.write(f"- **職業不明**: {unknown_occupation:,}件 ({unknown_occupation/len(df)*100:.1f}%)\n")
        f.write(f"- **国籍不明**: {unknown_nationality:,}件 ({unknown_nationality/len(df)*100:.1f}%)\n\n")
        
        f.write("## 📊 削除候補統計\n\n")
        deletion_candidates = analysis_results['deletion_candidates']
        f.write(f"- **条件1** (認知度35 + 職業不明): {len(deletion_candidates['condition1']):,}件\n")
        f.write(f"- **条件2** (認知度30以下): {len(deletion_candidates['condition2']):,}件\n")
        f.write(f"- **条件3** (両方不明 + 認知度35): {len(deletion_candidates['condition3']):,}件\n")
        f.write(f"- **統合削除候補**: {len(deletion_candidates['all_candidates']):,}件\n\n")
        
        f.write("## 🛡️ 保護対象統計\n\n")
        protected = analysis_results['protected']
        f.write(f"- **歴史的人物**: {protected['historical']:,}件\n")
        f.write(f"- **架空キャラクター**: {protected['fictional']:,}件\n")
        f.write(f"- **高認知度エンタメ人物**: {protected['high_recognition_entertainment']:,}件\n")
        f.write(f"- **VTuber/YouTuber**: {protected['vtuber_youtuber']:,}件\n")
        f.write(f"- **ミュージシャン**: {protected['musicians']:,}件\n\n")
        
        f.write("## 📋 推奨アクション\n\n")
        f.write("1. **即座削除推奨**: 認知度30以下 + メタデータ不完全\n")
        f.write("2. **要検証**: 認知度35のデフォルト値疑い案件\n") 
        f.write("3. **保護継続**: 歴史的人物・架空キャラクター・エンタメ高認知度\n")
        f.write("4. **Wikipedia検証**: 不明データの外部ソース確認\n\n")
        
    print(f"\n📄 詳細レポート生成: {report_file}")
    return report_file

def main():
    """メイン分析実行"""
    print("🔍 データベース深層分析開始")
    print("=" * 60)
    
    # データ読み込み
    df = load_database()
    if df is None:
        return
    
    # 各種分析実行
    recognition_dist = analyze_recognition_distribution(df)
    metadata_quality = analyze_metadata_quality(df)
    fictional_count, batch_analysis = parse_extended_data(df)
    deletion_candidates = identify_deletion_candidates(df)
    protected_entities = analyze_protected_entities(df)
    high_priority, medium_priority, scored_df = create_deletion_priority_score(df)
    
    # 結果統合
    analysis_results = {
        'recognition_dist': recognition_dist,
        'metadata_quality': metadata_quality,
        'fictional_count': fictional_count,
        'batch_analysis': batch_analysis,
        'deletion_candidates': deletion_candidates,
        'protected': protected_entities,
        'high_priority_deletion': high_priority,
        'medium_priority_deletion': medium_priority
    }
    
    # 詳細レポート生成
    report_file = generate_detailed_report(df, analysis_results)
    
    print("\n" + "=" * 60)
    print("🎯 分析完了サマリー")
    print("=" * 60)
    print(f"📊 総データ数: {len(df):,}件")
    print(f"❌ 高優先度削除候補: {len(high_priority):,}件 ({len(high_priority)/len(df)*100:.1f}%)")
    print(f"⚠️ 中優先度削除候補: {len(medium_priority):,}件 ({len(medium_priority)/len(df)*100:.1f}%)")
    print(f"🛡️ 保護対象合計: {sum(protected_entities.values()):,}件")
    print(f"📄 詳細レポート: {report_file}")
    
    # サンプル削除候補を表示
    if len(high_priority) > 0:
        print(f"\n🔍 高優先度削除候補サンプル (上位10件):")
        sample_columns = ['person_name', 'occupation', 'nationality', 'name_recognition', 'deletion_score']
        for idx, (_, row) in enumerate(high_priority.nlargest(10, 'deletion_score')[sample_columns].iterrows()):
            print(f"  {idx+1}. {row['person_name']} | {row['occupation']} | {row['nationality']} | 認知度{row['name_recognition']} | スコア{row['deletion_score']:.0f}")

if __name__ == "__main__":
    main()