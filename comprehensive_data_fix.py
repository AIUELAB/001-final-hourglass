#!/usr/bin/env python3
"""
Comprehensive Data Fix Script
Addresses all identified issues:
1. Wikipedia non-existent persons (set name_recognition=0)
2. Group members missing group names in parentheses
3. Placeholder/synthetic data removal
"""

import pandas as pd
from datetime import datetime
import json
import re

def comprehensive_data_fix(csv_file: str) -> str:
    """
    Fix all identified data quality issues
    """
    # Load database
    df = pd.read_csv(csv_file, encoding='utf-8-sig')
    initial_count = len(df)
    
    print(f"📊 Initial database: {initial_count:,} records")
    
    # Issue 1: Wikipedia non-existent persons (from Task agent report)
    print("\n🔍 Issue 1: Wikipedia Non-Existent Persons")
    
    # Placeholder patterns detected
    placeholder_ids = [
        'P002839', 'P002864', 'P002875', 'P003081', 
        'P004252', 'P004257', 'P004266', 'P004271', 'P004279'
    ]
    
    # Set name_recognition to 0 for placeholders
    for person_id in placeholder_ids:
        mask = df['person_id'] == person_id
        if mask.any():
            df.loc[mask, 'name_recognition'] = 0.0
            print(f"  ⚠️ Set name_recognition=0 for {person_id} (placeholder)")
    
    # Additional Wikipedia non-existent from investigation
    wikipedia_not_found = [
        'P002843', 'P002845', 'P002861', 'P002863', 'P002867', 
        'P002871', 'P002876', 'P002881', 'P002887', 'P003047',
        'P003051', 'P003055', 'P003062', 'P003071', 'P003077',
        'P003083', 'P004237', 'P004239', 'P004247', 'P004251',
        'P004254', 'P004260', 'P004272', 'P004275', 'P004282',
        'P005334', 'P005338', 'P005339', 'P005340',
        'P001562', 'P001563', 'P001565', 'P001567', 
        'P001568', 'P001576', 'P001577'
    ]
    
    for person_id in wikipedia_not_found:
        mask = df['person_id'] == person_id
        if mask.any():
            df.loc[mask, 'name_recognition'] = 0.0
            print(f"  ⚠️ Set name_recognition=0 for {person_id} (Wikipedia not found)")
    
    # Issue 2: Group members missing group names
    print("\n🎭 Issue 2: Group Members Missing Group Names")
    
    group_member_fixes = {
        'P002593': '大島美幸（森三中）',
        'P005487': '黒沢かずこ（森三中）',
        'P004907': '藤原基央（BUMP OF CHICKEN）',
        'P001827': '春日俊彰（オードリー）',  # 修正: ハリセンボンは誤り
        'P001832': '井戸田潤（スピードワゴン）',
        'P001834': '亜生（ミキ）',
        'P001897': '昴生（ミキ）',  # 修正: 兄は昴生
        'P001903': '伊藤俊介（オズワルド）',
        'P001927': '畠中悠（オズワルド）',  # 修正: 畠中が正しい
        'P002327': 'ハリウッドザコシショウ',  # ピン芸人なので括弧不要
        'P002434': '品川祐（品川庄司）',
        'P002520': '堂前透（ビスケッティ）',  # 修正: ビスケッティが正式名
        'P002527': '塙宣之（ナイツ）',
        'P003084': '山添寛（相席スタート）',
        'P003161': '山﨑ケイ（相席スタート）',
        'P003225': '川北茂澄（ビスケッティ）',
        'P003226': '川原克己（天津）',
        'P003237': '川田広樹（ガレッジセール）',
        'P003257': '布川ひろき（トータルテンボス）',  # 修正: ライスではなくトータルテンボス
        'P003317': '後藤拓実（四千頭身）',
        'P003320': '後藤淳平（ジャルジャル）',
        'P003643': '東貴博（Take2）',
        'P004112': '河井ゆずる（ぺこぱ）',
        'P004004': '中川礼二（中川家）',  # 修正: 礼二が正しい
        'P004466': '都築拓紀（四千頭身）',  # 修正: 都築が正しい
        'P004611': '福徳秀介（ジャルジャル）',
        'P004673': '箕輪はるか（ハリセンボン）',
        'P005100': '近藤春菜（ハリセンボン）',
        'P000141': 'りんたろー。（EXIT）'
    }
    
    fixed_count = 0
    for person_id, correct_display in group_member_fixes.items():
        mask = df['person_id'] == person_id
        if mask.any():
            current = df.loc[mask, 'person_name_display'].iloc[0]
            if current != correct_display:
                df.loc[mask, 'person_name_display'] = correct_display
                fixed_count += 1
                print(f"  ✅ Fixed: {person_id} → {correct_display}")
    
    # Issue 3: Detect and mark additional synthetic data
    print("\n🚨 Issue 3: Synthetic Data Detection")
    
    # Pattern: 一般的な姓 + 一般的な名前 + 同一スコア
    common_surnames = ['佐藤', '鈴木', '高橋', '田中', '渡辺', '伊藤', '中村', '小林', '山田', '加藤']
    common_names = ['太郎', '花子', '一郎', '美咲', '健太', '優子', '翔太', '愛', '大輝', '結衣']
    
    synthetic_count = 0
    for idx, row in df.iterrows():
        person_name = str(row.get('person_name', ''))
        person_name_ja = str(row.get('person_name_ja', ''))
        score = row.get('name_recognition', 0)
        
        # Check for synthetic patterns
        is_synthetic = False
        
        # Pattern 1: Common surname + common name
        for surname in common_surnames:
            for name in common_names:
                if surname in person_name_ja and name in person_name_ja:
                    if score in [50.0, 60.0, 35.0]:  # Common synthetic scores
                        is_synthetic = True
                        break
        
        # Pattern 2: "Actor XXX" or similar
        if re.match(r'^(Actor|Singer|Athlete|Player)\s+\d+', person_name):
            is_synthetic = True
        
        if is_synthetic:
            df.at[idx, 'name_recognition'] = 0.0
            synthetic_count += 1
    
    print(f"  ⚠️ Detected and marked {synthetic_count} synthetic records")
    
    # Issue 4: Remove records with name_recognition = 0
    print("\n🗑️ Issue 4: Removing Records with name_recognition = 0")
    
    zero_score_mask = df['name_recognition'] == 0.0
    zero_count = zero_score_mask.sum()
    
    if zero_count > 0:
        df = df[~zero_score_mask]
        print(f"  ❌ Removed {zero_count} records with name_recognition = 0")
    
    # Generate timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Save cleaned database
    output_file = f"/Users/admin/Documents/AIUELAB/001-final-hourglass/ultra_think_COMPREHENSIVE_FIX_{timestamp}.csv"
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    # Generate comprehensive report
    report = {
        'timestamp': timestamp,
        'initial_count': int(initial_count),
        'final_count': int(len(df)),
        'fixes_applied': {
            'wikipedia_not_found_marked': len(placeholder_ids) + len(wikipedia_not_found),
            'group_names_fixed': int(fixed_count),
            'synthetic_data_marked': int(synthetic_count),
            'zero_score_removed': int(zero_count)
        },
        'data_quality_metrics': {
            'removal_rate': float((initial_count - len(df)) / initial_count * 100),
            'group_member_compliance': int(fixed_count),
            'wikipedia_validation_applied': True
        }
    }
    
    report_file = f"/Users/admin/Documents/AIUELAB/001-final-hourglass/COMPREHENSIVE_FIX_REPORT_{timestamp}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n📊 Summary:")
    print(f"  Initial records: {initial_count:,}")
    print(f"  Wikipedia not found marked: {len(placeholder_ids) + len(wikipedia_not_found)}")
    print(f"  Group names fixed: {fixed_count}")
    print(f"  Synthetic data marked: {synthetic_count}")
    print(f"  Zero score removed: {zero_count}")
    print(f"  Final records: {len(df):,}")
    print(f"  Removal rate: {(initial_count - len(df)) / initial_count * 100:.1f}%")
    print(f"\n  📁 Output: {output_file}")
    print(f"  📄 Report: {report_file}")
    
    return output_file

def validate_critical_persons(df: pd.DataFrame):
    """
    Validate that critical persons are preserved
    """
    critical_persons = {
        'HIKAKIN': 35.0,
        '米津玄師': None,
        '大谷翔平': None,
        'Ado': 60.0
    }
    
    print("\n✅ Critical Person Validation:")
    for name, min_score in critical_persons.items():
        mask = df['person_name_display'].str.contains(name, na=False)
        if mask.any():
            score = df.loc[mask, 'name_recognition'].iloc[0]
            if min_score and score < min_score:
                print(f"  ⚠️ WARNING: {name} has low score: {score}")
            else:
                print(f"  ✅ {name}: score={score}")
        else:
            print(f"  ❌ ERROR: {name} not found!")

def main():
    """Main execution function"""
    # Use the latest cleaned database
    csv_file = "/Users/admin/Documents/AIUELAB/001-final-hourglass/ultra_think_NO_GROUPS_20250912_064413.csv"
    
    print("🔧 COMPREHENSIVE DATA FIX SYSTEM")
    print("=" * 50)
    print("Fixing all identified data quality issues:")
    print("1. Wikipedia non-existent persons")
    print("2. Group members missing group names")
    print("3. Synthetic/placeholder data")
    print("4. Zero score records")
    print()
    
    # Execute comprehensive fix
    output_file = comprehensive_data_fix(csv_file)
    
    # Validate critical persons
    df = pd.read_csv(output_file, encoding='utf-8-sig')
    validate_critical_persons(df)
    
    print("\n✅ COMPREHENSIVE FIX COMPLETED SUCCESSFULLY")

if __name__ == "__main__":
    main()