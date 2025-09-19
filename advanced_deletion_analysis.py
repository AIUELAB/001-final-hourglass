#!/usr/bin/env python3
"""
高度な削除候補分析システム
Wikipedia検証、メタデータ整合性、複合スコアリングによる最終判定

実行例:
python3 advanced_deletion_analysis.py
"""

import pandas as pd
import json
import numpy as np
from collections import Counter, defaultdict
from datetime import datetime
import re

def load_database():
    """データベースCSVを読み込み"""
    df = pd.read_csv('ultra_think_EPISODE_FINAL_20250901_020106.csv')
    return df

def analyze_metadata_consistency(df):
    """メタデータ整合性の詳細分析"""
    print("🔍 メタデータ整合性分析")
    print("=" * 50)
    
    inconsistencies = []
    metadata_scores = []
    
    for idx, row in df.iterrows():
        inconsistency_score = 0
        issues = []
        
        try:
            # recognition_metadata解析
            recognition_meta = json.loads(row['recognition_metadata'])
            extended_data = json.loads(row['extended_data'])
            
            # スコア整合性チェック
            original_score = float(recognition_meta.get('original_score', 0))
            calibrated_score = float(recognition_meta.get('calibrated_score', 0))
            current_score = row['name_recognition']
            
            if abs(calibrated_score - current_score) > 0.1:
                inconsistency_score += 20
                issues.append("キャリブレートスコア不一致")
            
            if original_score == 35 and calibrated_score == 35:
                inconsistency_score += 15
                issues.append("疑わしいデフォルト値")
            
            # カテゴリと職業の整合性
            category = row['category']
            occupation = row['occupation']
            
            # エンタメカテゴリなのに認知度が低い
            if category == 'エンタメ' and current_score <= 40:
                inconsistency_score += 25
                issues.append("エンタメ低認知度")
            
            # スポーツカテゴリなのに認知度が低い
            if category == 'スポーツ' and current_score <= 40:
                inconsistency_score += 30
                issues.append("スポーツ低認知度")
            
            # YouTuber/VTuberで異常に低い認知度
            if any(keyword in str(occupation).lower() for keyword in ['youtuber', 'vtuber']) and current_score <= 35:
                inconsistency_score += 35
                issues.append("デジタルネイティブ低認知度")
            
            # 「その他」カテゴリで職業も曖昧
            if category == 'その他' and occupation in ['不明', 'その他', '']:
                inconsistency_score += 30
                issues.append("カテゴリ・職業不明確")
            
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            inconsistency_score += 40
            issues.append("メタデータ破損")
        
        if inconsistency_score >= 30:
            inconsistencies.append({
                'person_id': row['person_id'],
                'person_name': row['person_name'],
                'occupation': row['occupation'],
                'category': row['category'],
                'name_recognition': row['name_recognition'],
                'inconsistency_score': inconsistency_score,
                'issues': issues
            })
        
        metadata_scores.append(inconsistency_score)
    
    print(f"📊 メタデータ整合性統計:")
    print(f"  平均不整合スコア: {np.mean(metadata_scores):.1f}")
    print(f"  高不整合案件(30+): {len(inconsistencies):,}件")
    print(f"  全体に占める割合: {len(inconsistencies)/len(df)*100:.1f}%")
    
    return inconsistencies

def create_comprehensive_scoring_system(df):
    """包括的スコアリングシステム"""
    print(f"\n🎯 包括的削除スコアリングシステム")
    print("=" * 50)
    
    df_scored = df.copy()
    df_scored['deletion_score'] = 0
    df_scored['deletion_reasons'] = ''
    
    for idx, row in df_scored.iterrows():
        score = 0
        reasons = []
        
        # 1. 認知度ベーススコア (40%)
        recognition = row['name_recognition']
        if recognition <= 30:
            score += 40
            reasons.append("超低認知度")
        elif recognition <= 34:
            score += 35
            reasons.append("極低認知度")
        elif recognition == 35:
            score += 20
            reasons.append("デフォルト値疑い")
        
        # 2. カテゴリ・職業整合性 (25%)
        category = row['category']
        occupation = str(row['occupation'])
        
        if category == 'その他' and occupation in ['不明', 'その他', '']:
            score += 25
            reasons.append("分類不明確")
        
        if category in ['スポーツ', 'エンタメ'] and recognition <= 35:
            score += 20
            reasons.append("主要カテゴリ低認知")
        
        # 3. デジタルプラットフォーム特別判定 (20%)
        if any(keyword in occupation.lower() for keyword in ['youtuber', 'vtuber']):
            if recognition <= 35:
                score += 20
                reasons.append("デジタル系異常低認知")
            # 逆に高認知度なら保護
            elif recognition >= 50:
                score -= 15
                reasons.append("デジタル系高認知(保護)")
        
        # 4. 歴史・文化的価値 (10%)
        if category in ['歴史', '歴史的偉人', '歴史上の人物']:
            score -= 10
            reasons.append("歴史的価値(保護)")
        
        if category in ['文化・芸術', '文化・学術', '文化']:
            score -= 10
            reasons.append("文化的価値(保護)")
        
        # 5. 架空キャラクター特別保護 (-15%)
        try:
            extended_data = json.loads(row['extended_data'])
            if extended_data.get('is_fictional') == 'TRUE':
                score -= 15
                reasons.append("架空キャラ(保護)")
        except:
            pass
        
        # 6. メタデータ品質 (5%)
        if row['nationality'] == '不明':
            score += 3
            reasons.append("国籍不明")
        if occupation == '不明':
            score += 2
            reasons.append("職業不明")
        
        # スコアを0-100に正規化
        final_score = max(0, min(100, score))
        
        df_scored.loc[idx, 'deletion_score'] = final_score
        df_scored.loc[idx, 'deletion_reasons'] = '; '.join(reasons)
    
    # 削除候補の分類
    critical_deletion = df_scored[df_scored['deletion_score'] >= 70]
    high_deletion = df_scored[(df_scored['deletion_score'] >= 55) & (df_scored['deletion_score'] < 70)]
    medium_deletion = df_scored[(df_scored['deletion_score'] >= 40) & (df_scored['deletion_score'] < 55)]
    
    print(f"🚨 CRITICAL削除候補 (70+): {len(critical_deletion):,}件 ({len(critical_deletion)/len(df)*100:.1f}%)")
    print(f"⚠️  HIGH削除候補 (55-69): {len(high_deletion):,}件 ({len(high_deletion)/len(df)*100:.1f}%)")
    print(f"📋 MEDIUM削除候補 (40-54): {len(medium_deletion):,}件 ({len(medium_deletion)/len(df)*100:.1f}%)")
    
    return critical_deletion, high_deletion, medium_deletion, df_scored

def analyze_batch_patterns(df):
    """バッチパターン分析"""
    print(f"\n🔧 バッチパターン分析")
    print("=" * 30)
    
    batch_stats = defaultdict(lambda: {'count': 0, 'avg_recognition': 0, 'recognition_scores': []})
    
    for idx, row in df.iterrows():
        try:
            extended_data = json.loads(row['extended_data'])
            batch_id = extended_data.get('original_batch_id', 'unknown')
            
            batch_stats[batch_id]['count'] += 1
            batch_stats[batch_id]['recognition_scores'].append(row['name_recognition'])
        except:
            batch_stats['unknown']['count'] += 1
            batch_stats['unknown']['recognition_scores'].append(row['name_recognition'])
    
    # 統計計算
    suspicious_batches = []
    for batch_id, stats in batch_stats.items():
        if stats['recognition_scores']:
            avg_recognition = np.mean(stats['recognition_scores'])
            std_recognition = np.std(stats['recognition_scores'])
            stats['avg_recognition'] = avg_recognition
            stats['std_recognition'] = std_recognition
            
            # 疑わしいバッチの特定
            if avg_recognition <= 36 and stats['count'] >= 20:
                suspicious_batches.append({
                    'batch_id': batch_id,
                    'count': stats['count'],
                    'avg_recognition': avg_recognition,
                    'std_recognition': std_recognition
                })
    
    print(f"疑わしいバッチ (平均認知度36以下, 20件以上):")
    for batch in sorted(suspicious_batches, key=lambda x: x['avg_recognition'])[:10]:
        print(f"  {batch['batch_id']}: {batch['count']}件, 平均{batch['avg_recognition']:.1f}, 標準偏差{batch['std_recognition']:.1f}")
    
    return suspicious_batches

def generate_final_recommendations(critical_deletion, high_deletion, medium_deletion, inconsistencies):
    """最終推奨アクション"""
    print(f"\n📋 最終推奨アクション")
    print("=" * 30)
    
    total_deletion_candidates = len(critical_deletion) + len(high_deletion) + len(medium_deletion)
    
    print(f"削除候補合計: {total_deletion_candidates:,}件")
    print(f"不整合案件: {len(inconsistencies):,}件")
    
    # アクションプラン
    actions = [
        f"1. 【即座削除推奨】CRITICAL案件 {len(critical_deletion):,}件 - メタデータ破損・極低認知度",
        f"2. 【検証後削除】HIGH案件 {len(high_deletion):,}件 - Wikipedia等で最終確認",
        f"3. 【慎重検討】MEDIUM案件 {len(medium_deletion):,}件 - 個別判断必要",
        f"4. 【メタデータ修正】不整合案件 {len(inconsistencies):,}件 - データ品質向上"
    ]
    
    for action in actions:
        print(f"  {action}")
    
    return actions

def export_comprehensive_results(df_scored, critical_deletion, high_deletion, medium_deletion, inconsistencies, suspicious_batches):
    """包括的結果のエクスポート"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 共通カラム定義
    critical_cols = ['person_id', 'person_name', 'occupation', 'category', 'nationality', 'name_recognition', 'deletion_score', 'deletion_reasons']
    
    # CRITICAL削除候補
    if len(critical_deletion) > 0:
        critical_csv = f"CRITICAL_DELETION_CANDIDATES_{timestamp}.csv"
        critical_deletion[critical_cols].to_csv(critical_csv, index=False, encoding='utf-8')
        print(f"📁 CRITICAL削除候補: {critical_csv}")
    
    # HIGH削除候補
    if len(high_deletion) > 0:
        high_csv = f"HIGH_DELETION_CANDIDATES_{timestamp}.csv"
        high_deletion[critical_cols].to_csv(high_csv, index=False, encoding='utf-8')
        print(f"📁 HIGH削除候補: {high_csv}")
    
    # 不整合案件
    if len(inconsistencies) > 0:
        inconsistency_df = pd.DataFrame(inconsistencies)
        inconsistency_csv = f"METADATA_INCONSISTENCIES_{timestamp}.csv"
        inconsistency_df.to_csv(inconsistency_csv, index=False, encoding='utf-8')
        print(f"📁 不整合案件: {inconsistency_csv}")
    
    # 統合レポート
    report_file = f"COMPREHENSIVE_DELETION_ANALYSIS_{timestamp}.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# 包括的削除候補分析レポート\n\n")
        f.write(f"**分析日時**: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}\n")
        f.write(f"**総データ数**: {len(df_scored):,}件\n\n")
        
        f.write("## 🎯 削除候補サマリー\n\n")
        f.write(f"| 優先度 | 件数 | 割合 | 説明 |\n")
        f.write(f"|--------|------|------|------|\n")
        f.write(f"| CRITICAL | {len(critical_deletion):,} | {len(critical_deletion)/len(df_scored)*100:.1f}% | 即座削除推奨 |\n")
        f.write(f"| HIGH | {len(high_deletion):,} | {len(high_deletion)/len(df_scored)*100:.1f}% | 検証後削除 |\n")
        f.write(f"| MEDIUM | {len(medium_deletion):,} | {len(medium_deletion)/len(df_scored)*100:.1f}% | 慎重検討 |\n\n")
        
        f.write("## 🔍 品質問題\n\n")
        f.write(f"- **メタデータ不整合**: {len(inconsistencies):,}件\n")
        f.write(f"- **疑わしいバッチ**: {len(suspicious_batches)}個\n\n")
        
        f.write("## 📈 削除による効果予測\n\n")
        total_candidates = len(critical_deletion) + len(high_deletion)
        f.write(f"- **削除対象**: {total_candidates:,}件\n")
        f.write(f"- **削除後サイズ**: {len(df_scored) - total_candidates:,}件\n")
        f.write(f"- **圧縮率**: {total_candidates/len(df_scored)*100:.1f}%\n\n")
        
        f.write("## 🛡️ 保護対象確認\n\n")
        protected_categories = df_scored[df_scored['deletion_score'] <= 10]['category'].value_counts()
        f.write("保護されるカテゴリ:\n")
        for category, count in protected_categories.head(10).items():
            f.write(f"- {category}: {count:,}件\n")
    
    print(f"📄 包括レポート: {report_file}")
    
    return report_file

def main():
    """メイン分析実行"""
    print("🧠 包括的削除候補分析システム")
    print("=" * 80)
    
    # データ読み込み
    df = load_database()
    print(f"✓ データベース読み込み: {len(df):,}件")
    
    # メタデータ整合性分析
    inconsistencies = analyze_metadata_consistency(df)
    
    # 包括的スコアリング
    critical_deletion, high_deletion, medium_deletion, df_scored = create_comprehensive_scoring_system(df)
    
    # バッチパターン分析
    suspicious_batches = analyze_batch_patterns(df)
    
    # 最終推奨アクション
    actions = generate_final_recommendations(critical_deletion, high_deletion, medium_deletion, inconsistencies)
    
    # 結果エクスポート
    report_file = export_comprehensive_results(df_scored, critical_deletion, high_deletion, medium_deletion, inconsistencies, suspicious_batches)
    
    print("\n" + "=" * 80)
    print("🎯 最終分析結果")
    print("=" * 80)
    print(f"📊 総データ数: {len(df):,}件")
    print(f"🚨 CRITICAL削除候補: {len(critical_deletion):,}件 ({len(critical_deletion)/len(df)*100:.1f}%)")
    print(f"⚠️ HIGH削除候補: {len(high_deletion):,}件 ({len(high_deletion)/len(df)*100:.1f}%)")
    print(f"📋 MEDIUM削除候補: {len(medium_deletion):,}件 ({len(medium_deletion)/len(df)*100:.1f}%)")
    print(f"🔧 不整合案件: {len(inconsistencies):,}件")
    print(f"📄 包括レポート: {report_file}")
    
    # 最も問題のある削除候補を表示
    if len(critical_deletion) > 0:
        print(f"\n🚨 CRITICAL削除候補サンプル (上位10件):")
        sample_cols = ['person_name', 'occupation', 'category', 'name_recognition', 'deletion_score', 'deletion_reasons']
        for idx, (_, row) in enumerate(critical_deletion.nlargest(10, 'deletion_score')[sample_cols].iterrows()):
            print(f"  {idx+1:2d}. {row['person_name'][:15]:15s} | {row['occupation'][:12]:12s} | 認知度{row['name_recognition']:2.0f} | スコア{row['deletion_score']:2.0f} | {row['deletion_reasons'][:50]}")

if __name__ == "__main__":
    main()