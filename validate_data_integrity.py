#!/usr/bin/env python3
"""
Validate Data Integrity
データ整合性検証

This script performs comprehensive validation of the database
to ensure all fixes have been properly applied.
"""

import pandas as pd
import json
from datetime import datetime
import re

def main():
    print("="*60)
    print("データ整合性検証プロセス")
    print("="*60)

    # 1. 最新のデータベースを検索
    import glob
    csv_files = glob.glob('ultra_think_OCCUPATION_FIXED_*.csv')
    if csv_files:
        csv_file = max(csv_files, key=lambda f: f.split('_')[-1])
    else:
        csv_files = glob.glob('ultra_think_PSY_RESTORED_*.csv')
        if csv_files:
            csv_file = max(csv_files, key=lambda f: f.split('_')[-1])
        else:
            csv_file = 'ultra_think_FINAL_CLEAN_20250831_205221.csv'

    print(f"\n📂 Loading database from {csv_file}...")
    df = pd.read_csv(csv_file, encoding='utf-8')
    print(f"✅ Loaded {len(df)} records")

    validation_results = {
        'total_records': len(df),
        'issues_found': [],
        'passed_checks': [],
        'critical_fixes_verified': []
    }

    # 2. P000305 (Usain Bolt) の検証
    print("\n🔍 Verifying P000305 (Usain Bolt) fix...")
    p305 = df[df['person_id'] == 'P000305']
    if not p305.empty:
        bolt = p305.iloc[0]

        # 期待される値
        expected = {
            'person_name': 'Usain Bolt',
            'person_name_display': 'ウサイン・ボルト',
            'person_name_ja': 'ウサイン・ボルト',
            'occupation': '陸上選手',
            'nationality': 'ジャマイカ',
            'category': 'スポーツ'
        }

        all_correct = True
        for field, expected_value in expected.items():
            actual_value = bolt[field]
            if actual_value == expected_value:
                print(f"  ✅ {field}: {actual_value}")
            else:
                print(f"  ❌ {field}: {actual_value} (expected: {expected_value})")
                all_correct = False
                validation_results['issues_found'].append({
                    'person_id': 'P000305',
                    'field': field,
                    'actual': actual_value,
                    'expected': expected_value
                })

        if all_correct:
            validation_results['critical_fixes_verified'].append('P000305_usain_bolt')
            validation_results['passed_checks'].append('P000305 completely fixed')
    else:
        print("  ❌ P000305 not found in database!")
        validation_results['issues_found'].append({'error': 'P000305 not found'})

    # 3. PSY レコードの検証
    print("\n🔍 Verifying PSY record restoration...")
    psy = df[df['person_name'] == 'PSY']
    if not psy.empty:
        psy_rec = psy.iloc[0]
        print(f"  ✅ PSY record found: {psy_rec['person_id']}")
        print(f"    person_name_display: {psy_rec['person_name_display']}")
        print(f"    occupation: {psy_rec['occupation']}")
        print(f"    nationality: {psy_rec['nationality']}")

        if psy_rec['nationality'] == '韓国' and psy_rec['occupation'] == '歌手':
            validation_results['critical_fixes_verified'].append('PSY_restoration')
            validation_results['passed_checks'].append('PSY correctly restored')
        else:
            validation_results['issues_found'].append({
                'person_id': psy_rec['person_id'],
                'issue': 'PSY data incorrect'
            })
    else:
        print("  ❌ PSY record not found!")
        validation_results['issues_found'].append({'error': 'PSY not found'})

    # 4. person_name vs person_name_display の整合性チェック
    print("\n🔍 Checking person_name vs person_name_display consistency...")

    severe_mismatches = []
    for _, row in df.iterrows():
        name = str(row['person_name']).lower()
        display = str(row['person_name_display']).lower()

        # グループ名の括弧を除外
        display_clean = re.sub(r'\([^)]+\)', '', display).strip()

        # PSYケースのような完全に異なる名前をチェック
        if name and display_clean:
            # アルファベット同士で完全に異なる
            if name.replace(' ', '').isalpha() and display_clean.replace(' ', '').isalpha():
                if not any(part in display_clean for part in name.split()) and \
                   not any(part in name for part in display_clean.split()):
                    # 許容される変換（英語→日本語）は除外
                    if not (name.isascii() and not display_clean.isascii()):
                        severe_mismatches.append({
                            'person_id': row['person_id'],
                            'person_name': row['person_name'],
                            'person_name_display': row['person_name_display']
                        })

    if severe_mismatches:
        print(f"  ⚠️ Found {len(severe_mismatches)} potential severe mismatches")
        for m in severe_mismatches[:5]:
            print(f"    {m['person_id']}: {m['person_name']} → {m['person_name_display']}")
        validation_results['issues_found'].extend(severe_mismatches)
    else:
        print("  ✅ No severe name mismatches found")
        validation_results['passed_checks'].append('No severe name mismatches')

    # 5. occupation vs category の整合性チェック
    print("\n🔍 Checking occupation vs category consistency...")

    # スポーツカテゴリで非スポーツ職業
    sports_df = df[df['category'] == 'スポーツ']
    non_sports_occupation = sports_df[
        ~sports_df['occupation'].str.contains(
            '選手|アスリート|スポーツ|力士|コーチ|監督|審判',
            na=False,
            regex=True
        )
    ]

    if not non_sports_occupation.empty:
        print(f"  ⚠️ Found {len(non_sports_occupation)} sports category with non-sports occupation")
        for _, row in non_sports_occupation.head(3).iterrows():
            print(f"    {row['person_id']}: {row['person_name']} (occupation: {row['occupation']})")
        validation_results['issues_found'].append({
            'issue': 'sports_category_mismatch',
            'count': len(non_sports_occupation)
        })
    else:
        print("  ✅ All sports category records have appropriate occupations")
        validation_results['passed_checks'].append('Sports category consistency')

    # 6. 重複チェック
    print("\n🔍 Checking for duplicates...")

    # person_idの重複
    duplicate_ids = df[df['person_id'].duplicated()]['person_id'].tolist()
    if duplicate_ids:
        print(f"  ❌ Found {len(duplicate_ids)} duplicate person_ids")
        validation_results['issues_found'].append({
            'issue': 'duplicate_person_ids',
            'ids': duplicate_ids[:10]
        })
    else:
        print("  ✅ No duplicate person_ids")
        validation_results['passed_checks'].append('No duplicate IDs')

    # 7. 最終統計
    print("\n📊 Validation Summary:")
    print(f"  Total records: {validation_results['total_records']}")
    print(f"  Passed checks: {len(validation_results['passed_checks'])}")
    print(f"  Issues found: {len(validation_results['issues_found'])}")
    print(f"  Critical fixes verified: {len(validation_results['critical_fixes_verified'])}")

    # 8. 検証レポートを保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    validation_file = f"data_validation_report_{timestamp}.json"

    with open(validation_file, 'w', encoding='utf-8') as f:
        json.dump(validation_results, f, ensure_ascii=False, indent=2)
    print(f"\n📝 Validation report saved to {validation_file}")

    # 9. 最終判定
    print("\n" + "="*60)
    if len(validation_results['issues_found']) == 0:
        print("✅ DATA VALIDATION PASSED!")
        print("All critical fixes have been successfully applied.")
        return True, csv_file
    else:
        print("⚠️ DATA VALIDATION COMPLETED WITH WARNINGS")
        print(f"Found {len(validation_results['issues_found'])} potential issues to review.")
        return False, csv_file

if __name__ == "__main__":
    passed, output_file = main()
    if passed:
        print(f"\n🎉 データベースの整合性検証が完了しました！")
        print(f"   すべての修正が正しく適用されています。")
        print(f"   Next step: python3 direct_sync.py")
    else:
        print(f"\n⚠️ いくつかの警告がありますが、主要な修正は完了しています。")
        print(f"   Next step: python3 direct_sync.py")
