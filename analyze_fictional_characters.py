#!/usr/bin/env python3
"""
架空キャラクター分析スクリプト
現在のデータベースから架空キャラクターを抽出し、問題を特定
"""

import pandas as pd
import json
from datetime import datetime

def main():
    print("="*60)
    print("架空キャラクター分析")
    print("="*60)
    
    # データベース読み込み
    csv_file = 'ultra_think_FINAL_COMPLETE_20250831_215329.csv'
    print(f"\n📂 Loading database: {csv_file}")
    df = pd.read_csv(csv_file, encoding='utf-8')
    print(f"✅ Total records: {len(df)}")
    
    # 架空キャラクターの特定
    # 方法1: categoryが"架空の存在"
    fictional_by_category = df[df['category'] == '架空の存在'].copy()
    print(f"\n🎯 Category='架空の存在': {len(fictional_by_category)} characters")
    
    # 方法2: occupationが"架空キャラクター"
    fictional_by_occupation = df[df['occupation'] == '架空キャラクター'].copy()
    print(f"🎯 Occupation='架空キャラクター': {len(fictional_by_occupation)} characters")
    
    # 両方を結合（重複除去）
    all_fictional_ids = set(fictional_by_category['person_id'].tolist() + 
                           fictional_by_occupation['person_id'].tolist())
    all_fictional = df[df['person_id'].isin(all_fictional_ids)].copy()
    print(f"🎯 Total unique fictional characters: {len(all_fictional)}")
    
    # 問題の分析
    print("\n🔍 Analyzing display name issues...")
    
    issues = []
    missing_work = []
    wrong_parentheses = []
    correct_format = []
    
    for _, char in all_fictional.iterrows():
        person_id = char['person_id']
        person_name = char['person_name']
        display = char['person_name_display']
        
        # 作品名が括弧内にあるかチェック
        if '（' in display or '(' in display:
            if '（' in display and '）' in display:
                # 全角括弧（正しい形式）
                correct_format.append({
                    'person_id': person_id,
                    'person_name': person_name,
                    'display': display
                })
            elif '(' in display and ')' in display:
                # 半角括弧（修正が必要）
                wrong_parentheses.append({
                    'person_id': person_id,
                    'person_name': person_name,
                    'display': display,
                    'issue': 'Half-width parentheses'
                })
            else:
                # 括弧が不完全
                issues.append({
                    'person_id': person_id,
                    'person_name': person_name,
                    'display': display,
                    'issue': 'Incomplete parentheses'
                })
        else:
            # 作品名が完全に欠落
            missing_work.append({
                'person_id': person_id,
                'person_name': person_name,
                'display': display,
                'occupation': char['occupation'],
                'nationality': char.get('nationality', ''),
                'category': char.get('category', '')
            })
    
    # 特定のキャラクターの詳細分析
    print("\n🎯 Specific character analysis:")
    
    # P000583 (Sanji)の詳細
    sanji = df[df['person_id'] == 'P000583']
    if not sanji.empty:
        s = sanji.iloc[0]
        print(f"\nP000583 (Sanji):")
        print(f"  person_name: {s['person_name']}")
        print(f"  person_name_display: {s['person_name_display']}")
        print(f"  person_name_ja: {s.get('person_name_ja', 'N/A')}")
        print(f"  occupation: {s['occupation']}")
        print(f"  nationality: {s.get('nationality', 'N/A')}")
        print(f"  category: {s.get('category', 'N/A')}")
        print(f"  ❌ Missing work name: Should be 'サンジ（ONE PIECE）'")
    
    # 結果の表示
    print(f"\n📊 Summary:")
    print(f"  ✅ Correct format: {len(correct_format)} characters")
    print(f"  ❌ Missing work name: {len(missing_work)} characters")
    print(f"  ⚠️ Wrong parentheses: {len(wrong_parentheses)} characters")
    print(f"  🔧 Other issues: {len(issues)} characters")
    
    # 作品名が欠落しているキャラクターのリスト
    if missing_work:
        print(f"\n🚨 Characters missing work names ({len(missing_work)}):")
        for char in missing_work[:20]:  # 最初の20件を表示
            print(f"  {char['person_id']}: {char['person_name']} - '{char['display']}'")
            if char['nationality'] in ['北の海', 'East Blue', '偉大なる航路']:
                print(f"    → Likely ONE PIECE character")
    
    # レポートを保存
    report = {
        'timestamp': datetime.now().isoformat(),
        'total_fictional': len(all_fictional),
        'correct_format': len(correct_format),
        'missing_work': len(missing_work),
        'wrong_parentheses': len(wrong_parentheses),
        'other_issues': len(issues),
        'missing_work_list': missing_work,
        'wrong_parentheses_list': wrong_parentheses
    }
    
    report_file = f"fictional_character_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n📝 Analysis report saved to: {report_file}")
    
    return report

if __name__ == "__main__":
    report = main()
    print("\n✅ Analysis complete!")