#!/usr/bin/env python3
"""
認知度35のデフォルト値疑い案件の詳細調査
1,666人の認知度35レコードを深掘り分析

実行例:
python3 investigate_default_recognition_35.py
"""

import pandas as pd
import json
import numpy as np
from collections import Counter, defaultdict
from datetime import datetime
import requests
import time

def load_database():
    """データベースCSVを読み込み"""
    df = pd.read_csv('ultra_think_EPISODE_FINAL_20250901_020106.csv')
    return df

def analyze_recognition_35_group(df):
    """認知度35グループの詳細分析"""
    print("🔍 認知度35レコードの詳細調査")
    print("=" * 60)
    
    recognition_35 = df[df['name_recognition'] == 35]
    print(f"対象レコード数: {len(recognition_35):,}件")
    
    # カテゴリ別分布
    category_dist = recognition_35['category'].value_counts()
    print(f"\n📊 カテゴリ別分布:")
    for category, count in category_dist.head(10).items():
        percentage = count / len(recognition_35) * 100
        print(f"  {category}: {count:,}件 ({percentage:.1f}%)")
    
    # 職業別分布
    occupation_dist = recognition_35['occupation'].value_counts()
    print(f"\n💼 職業別分布 (上位15):")
    for occupation, count in occupation_dist.head(15).items():
        percentage = count / len(recognition_35) * 100
        print(f"  {occupation}: {count:,}件 ({percentage:.1f}%)")
    
    # 国籍分布
    nationality_dist = recognition_35['nationality'].value_counts()
    print(f"\n🌍 国籍分布 (上位10):")
    for nationality, count in nationality_dist.head(10).items():
        percentage = count / len(recognition_35) * 100
        print(f"  {nationality}: {count:,}件 ({percentage:.1f}%)")
    
    return recognition_35

def identify_suspicious_patterns(recognition_35_df):
    """疑わしいパターンの特定"""
    print(f"\n🚨 疑わしいパターン分析")
    print("=" * 40)
    
    # パターン1: スポーツ選手で認知度35（通常もっと高いはず）
    sports_35 = recognition_35_df[recognition_35_df['category'] == 'スポーツ']
    print(f"パターン1 - スポーツ選手で認知度35: {len(sports_35):,}件")
    
    # パターン2: エンタメで認知度35（通常もっと高いはず）
    entertainment_35 = recognition_35_df[recognition_35_df['category'] == 'エンタメ']
    print(f"パターン2 - エンタメで認知度35: {len(entertainment_35):,}件")
    
    # パターン3: 職業がミュージシャン系で35（異常に低い）
    musician_35 = recognition_35_df[
        recognition_35_df['occupation'].str.contains('ミュージシャン|歌手|DJ|プロデューサー|ギタリスト|ドラマー|ベーシスト', na=False)
    ]
    print(f"パターン3 - ミュージシャン系で認知度35: {len(musician_35):,}件")
    
    # パターン4: YouTuber/VTuberで35（プラットフォーム特性上異常）
    youtuber_35 = recognition_35_df[
        recognition_35_df['occupation'].str.contains('YouTuber|VTuber', na=False, case=False)
    ]
    print(f"パターン4 - YouTuber/VTuberで認知度35: {len(youtuber_35):,}件")
    
    # パターン5: 俳優・女優で35
    actor_35 = recognition_35_df[
        recognition_35_df['occupation'].str.contains('俳優|女優|アクター', na=False)
    ]
    print(f"パターン5 - 俳優・女優で認知度35: {len(actor_35):,}件")
    
    return {
        'sports': sports_35,
        'entertainment': entertainment_35,
        'musician': musician_35,
        'youtuber': youtuber_35,
        'actor': actor_35
    }

def analyze_calibration_metadata(recognition_35_df):
    """キャリブレーション メタデータの分析"""
    print(f"\n🔧 キャリブレーション分析")
    print("=" * 30)
    
    original_scores = []
    calibrated_scores = []
    
    for idx, row in recognition_35_df.iterrows():
        try:
            metadata = json.loads(row['recognition_metadata'])
            original_score = metadata.get('original_score')
            calibrated_score = metadata.get('calibrated_score')
            
            if original_score and calibrated_score:
                original_scores.append(float(original_score))
                calibrated_scores.append(float(calibrated_score))
        except (json.JSONDecodeError, TypeError, ValueError):
            continue
    
    if original_scores:
        original_avg = np.mean(original_scores)
        calibrated_avg = np.mean(calibrated_scores)
        
        print(f"オリジナルスコア平均: {original_avg:.1f}")
        print(f"キャリブレート後平均: {calibrated_avg:.1f}")
        print(f"サンプル数: {len(original_scores):,}件")
        
        # オリジナルスコアが35でない場合を特定
        non_35_original = [s for s in original_scores if s != 35]
        if non_35_original:
            print(f"オリジナルが35以外: {len(non_35_original):,}件 (平均: {np.mean(non_35_original):.1f})")
    
    return original_scores, calibrated_scores

def sample_suspicious_records(suspicious_patterns):
    """疑わしいレコードのサンプル表示"""
    print(f"\n📋 疑わしいレコードサンプル")
    print("=" * 40)
    
    for pattern_name, pattern_df in suspicious_patterns.items():
        if len(pattern_df) > 0:
            print(f"\n🎯 {pattern_name.upper()} パターン (上位5件):")
            sample_cols = ['person_name', 'occupation', 'nationality', 'category']
            for idx, (_, row) in enumerate(pattern_df[sample_cols].head(5).iterrows()):
                print(f"  {idx+1}. {row['person_name']} | {row['occupation']} | {row['nationality']} | {row['category']}")

def generate_deletion_recommendations(recognition_35_df, suspicious_patterns):
    """削除推奨リスト生成"""
    print(f"\n🎯 削除推奨リスト生成")
    print("=" * 30)
    
    # 削除スコア計算
    deletion_recommendations = []
    
    for idx, row in recognition_35_df.iterrows():
        risk_score = 0
        reasons = []
        
        # スポーツ選手で35は疑わしい
        if row['category'] == 'スポーツ' and row['occupation'] in ['サッカー選手', '野球選手', 'バスケットボール選手']:
            risk_score += 30
            reasons.append("主要スポーツ選手で低認知度")
        
        # エンタメで35は疑わしい  
        if row['category'] == 'エンタメ':
            risk_score += 20
            reasons.append("エンタメカテゴリで低認知度")
        
        # YouTuber/VTuberで35は異常
        if 'YouTuber' in str(row['occupation']) or 'VTuber' in str(row['occupation']):
            risk_score += 40
            reasons.append("YouTuber/VTuberで異常な低認知度")
        
        # ミュージシャンで35は疑わしい
        if any(keyword in str(row['occupation']) for keyword in ['ミュージシャン', '歌手', 'DJ']):
            risk_score += 25
            reasons.append("ミュージシャン系で低認知度")
        
        # 「その他」カテゴリで職業も曖昧
        if row['category'] == 'その他' and str(row['occupation']) in ['不明', 'その他']:
            risk_score += 35
            reasons.append("カテゴリ・職業ともに曖昧")
        
        if risk_score >= 40:
            deletion_recommendations.append({
                'person_id': row['person_id'],
                'person_name': row['person_name'],
                'occupation': row['occupation'],
                'category': row['category'],
                'nationality': row['nationality'],
                'risk_score': risk_score,
                'reasons': reasons
            })
    
    deletion_recommendations.sort(key=lambda x: x['risk_score'], reverse=True)
    
    print(f"🚨 高リスク削除候補: {len(deletion_recommendations):,}件")
    print(f"📊 全体に占める割合: {len(deletion_recommendations)/len(recognition_35_df)*100:.1f}%")
    
    # 上位20件表示
    print(f"\n📋 上位削除候補 (リスクスコア順):")
    for i, rec in enumerate(deletion_recommendations[:20]):
        print(f"  {i+1:2d}. {rec['person_name']:20s} | {rec['occupation']:15s} | スコア{rec['risk_score']:2d} | {', '.join(rec['reasons'])}")
    
    return deletion_recommendations

def export_results(recognition_35_df, suspicious_patterns, deletion_recommendations):
    """結果のエクスポート"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 削除候補CSVエクスポート
    deletion_df = pd.DataFrame(deletion_recommendations)
    if len(deletion_df) > 0:
        deletion_csv = f"DELETION_CANDIDATES_RECOGNITION_35_{timestamp}.csv"
        deletion_df.to_csv(deletion_csv, index=False, encoding='utf-8')
        print(f"\n📁 削除候補リスト: {deletion_csv}")
    
    # 詳細レポート
    report_file = f"RECOGNITION_35_INVESTIGATION_{timestamp}.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# 認知度35デフォルト値調査レポート\n\n")
        f.write(f"**調査日時**: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}\n")
        f.write(f"**対象レコード数**: {len(recognition_35_df):,}件\n\n")
        
        f.write("## 🚨 主要発見事項\n\n")
        f.write("### 疑わしいパターン統計\n")
        for pattern_name, pattern_df in suspicious_patterns.items():
            f.write(f"- **{pattern_name}**: {len(pattern_df):,}件\n")
        
        f.write(f"\n### 高リスク削除候補\n")
        f.write(f"- **削除推奨**: {len(deletion_recommendations):,}件\n")
        f.write(f"- **割合**: {len(deletion_recommendations)/len(recognition_35_df)*100:.1f}%\n\n")
        
        f.write("## 📋 推奨アクション\n\n")
        f.write("1. **即座検証**: YouTuber/VTuberで認知度35の案件\n")
        f.write("2. **Wikipedia確認**: スポーツ選手・エンタメの低認知度案件\n")
        f.write("3. **削除検討**: 「その他」カテゴリで職業不明案件\n")
        f.write("4. **キャリブレーション再実行**: オリジナルスコアとの乖離大きい案件\n\n")
    
    print(f"📄 調査レポート: {report_file}")

def main():
    """メイン調査実行"""
    print("🔍 認知度35デフォルト値疑い案件の詳細調査")
    print("=" * 70)
    
    # データ読み込み
    df = load_database()
    
    # 認知度35グループの分析
    recognition_35_df = analyze_recognition_35_group(df)
    
    # 疑わしいパターンの特定
    suspicious_patterns = identify_suspicious_patterns(recognition_35_df)
    
    # キャリブレーション分析
    original_scores, calibrated_scores = analyze_calibration_metadata(recognition_35_df)
    
    # サンプル表示
    sample_suspicious_records(suspicious_patterns)
    
    # 削除推奨リスト生成
    deletion_recommendations = generate_deletion_recommendations(recognition_35_df, suspicious_patterns)
    
    # 結果エクスポート
    export_results(recognition_35_df, suspicious_patterns, deletion_recommendations)
    
    print("\n" + "=" * 70)
    print("🎯 調査完了サマリー")
    print("=" * 70)
    print(f"📊 認知度35レコード数: {len(recognition_35_df):,}件")
    print(f"🚨 高リスク削除候補: {len(deletion_recommendations):,}件")
    print(f"📈 削除対象率: {len(deletion_recommendations)/len(recognition_35_df)*100:.1f}%")
    print(f"⚠️ 疑わしいパターン合計: {sum(len(pattern_df) for pattern_df in suspicious_patterns.values()):,}件")

if __name__ == "__main__":
    main()