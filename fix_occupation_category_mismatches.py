#!/usr/bin/env python3
"""
Fix Occupation-Category Mismatches
職業とカテゴリの不整合を修正

This script fixes mismatches between occupation and category fields,
particularly for sports category records.
"""

import pandas as pd
import json
from datetime import datetime

def main():
    print("="*60)
    print("職業・カテゴリ不整合修正プロセス")
    print("="*60)
    
    # 1. 最新のデータベースを検索
    import glob
    csv_files = glob.glob('ultra_think_PSY_RESTORED_*.csv')
    if csv_files:
        csv_file = max(csv_files, key=lambda f: f.split('_')[-1])
    else:
        csv_files = glob.glob('ultra_think_P000305_FIXED_*.csv')
        if csv_files:
            csv_file = max(csv_files, key=lambda f: f.split('_')[-1])
        else:
            csv_file = 'ultra_think_FINAL_CLEAN_20250831_205221.csv'
    
    print(f"\n📂 Loading database from {csv_file}...")
    df = pd.read_csv(csv_file, encoding='utf-8')
    print(f"✅ Loaded {len(df)} records")
    
    # 2. スポーツカテゴリの不整合を検出
    print("\n🔍 Detecting occupation-category mismatches...")
    
    fixes_applied = []
    
    # スポーツカテゴリの修正マッピング
    sports_occupation_map = {
        'フィギュアスケーター': 'フィギュアスケート選手',
        '力士': '大相撲力士',
        'YouTuber': '陸上選手'  # P000305のケース（既に修正済みの場合はスキップ）
    }
    
    # 特定の人物に対する修正
    specific_fixes = {
        'P002498': {  # Kaori Sakamoto
            'occupation': 'フィギュアスケート選手',
            'person_name_display': '坂本花織'
        },
        'P004344': {  # Terunofuji Haruo
            'occupation': '大相撲力士',
            'person_name_display': '照ノ富士春雄'
        },
        'P004686': {  # Rika Kihira
            'occupation': 'フィギュアスケート選手',
            'person_name_display': '紀平梨花'
        },
        'P005051': {  # Takakeisho Mitsunobu
            'occupation': '大相撲力士',
            'person_name_display': '貴景勝光信'
        }
    }
    
    # 3. スポーツカテゴリの職業を正規化
    sports_df = df[df['category'] == 'スポーツ']
    print(f"\n📊 Found {len(sports_df)} sports category records")
    
    for idx, row in sports_df.iterrows():
        person_id = row['person_id']
        current_occupation = row['occupation']
        needs_fix = False
        new_occupation = current_occupation
        new_display = row['person_name_display']
        
        # 特定の修正が必要な場合
        if person_id in specific_fixes:
            fix_data = specific_fixes[person_id]
            new_occupation = fix_data['occupation']
            new_display = fix_data.get('person_name_display', new_display)
            needs_fix = True
            
        # 一般的な修正マッピング
        elif current_occupation in sports_occupation_map:
            new_occupation = sports_occupation_map[current_occupation]
            needs_fix = True
        
        # 修正を適用
        if needs_fix:
            df.loc[df['person_id'] == person_id, 'occupation'] = new_occupation
            if new_display != row['person_name_display']:
                df.loc[df['person_id'] == person_id, 'person_name_display'] = new_display
            
            fixes_applied.append({
                'person_id': person_id,
                'person_name': row['person_name'],
                'occupation': {'before': current_occupation, 'after': new_occupation},
                'person_name_display': {'before': row['person_name_display'], 'after': new_display}
            })
            
            print(f"  ✅ Fixed {person_id}: {current_occupation} → {new_occupation}")
    
    # 4. その他のカテゴリの不整合チェック
    print("\n🔍 Checking other category mismatches...")
    
    # エンタメカテゴリで適切でない職業
    entertainment_df = df[df['category'] == 'エンタメ']
    wrong_entertainment = entertainment_df[
        entertainment_df['occupation'].str.contains('選手|政治|科学|教授', na=False)
    ]
    
    if not wrong_entertainment.empty:
        print(f"  ⚠️ Found {len(wrong_entertainment)} potential mismatches in エンタメ category")
        for _, row in wrong_entertainment.head(3).iterrows():
            print(f"    {row['person_id']}: {row['person_name']} (occupation: {row['occupation']})")
    
    # 5. 修正結果の保存
    if fixes_applied:
        print(f"\n📝 Applied {len(fixes_applied)} fixes")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"ultra_think_OCCUPATION_FIXED_{timestamp}.csv"
        df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"💾 Fixed database saved to {output_file}")
        
        # 修正ログを記録
        fix_log = {
            'timestamp': datetime.now().isoformat(),
            'total_fixes': len(fixes_applied),
            'fixes': fixes_applied,
            'output_file': output_file
        }
        
        log_file = f"occupation_fix_log_{timestamp}.json"
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(fix_log, f, ensure_ascii=False, indent=2)
        print(f"📝 Fix log saved to {log_file}")
    else:
        print("\n✅ No occupation-category mismatches found that need fixing")
        output_file = csv_file
    
    # 6. 統計
    print("\n📊 Final Statistics:")
    print(f"  Total records: {len(df)}")
    print(f"  Sports category records: {len(sports_df)}")
    print(f"  Fixes applied: {len(fixes_applied)}")
    
    # 最終確認
    print("\n🔍 Final verification:")
    
    # P000305の確認
    p305 = df[df['person_id'] == 'P000305']
    if not p305.empty:
        p305_rec = p305.iloc[0]
        print(f"  P000305 (Usain Bolt):")
        print(f"    occupation: {p305_rec['occupation']} {'✅' if p305_rec['occupation'] == '陸上選手' else '❌'}")
        print(f"    display: {p305_rec['person_name_display']} {'✅' if 'PSY' not in p305_rec['person_name_display'] else '❌'}")
    
    return output_file

if __name__ == "__main__":
    output_file = main()
    print(f"\n🎉 職業・カテゴリ不整合の修正が完了しました！")
    print(f"   Output: {output_file}")
    print(f"   Next step: python3 validate_data_integrity.py")