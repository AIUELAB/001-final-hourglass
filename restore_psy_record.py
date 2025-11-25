#!/usr/bin/env python3
"""
Restore PSY Record to Database
PSYレコードをデータベースに復元

This script adds the missing PSY (Korean rapper) record to the database
after it was accidentally lost during deduplication.
"""

import pandas as pd
import json
from datetime import datetime
import numpy as np

def main():
    print("="*60)
    print("PSY レコード復元プロセス")
    print("="*60)

    # 1. 最新のデータベースを検索
    import glob
    csv_files = glob.glob('ultra_think_P000305_FIXED_*.csv')
    if csv_files:
        csv_file = max(csv_files, key=lambda f: f.split('_')[-1])
    else:
        csv_file = 'ultra_think_FINAL_CLEAN_20250831_205221.csv'

    print(f"\n📂 Loading database from {csv_file}...")
    df = pd.read_csv(csv_file, encoding='utf-8')
    print(f"✅ Loaded {len(df)} records")

    # 2. PSYレコードが既に存在しないか確認
    print("\n🔍 Checking for existing PSY records...")
    psy_exists = df[df['person_name'].str.contains('PSY|Psy', na=False, case=False)]
    if not psy_exists.empty:
        print("⚠️ PSY record already exists:")
        for _, row in psy_exists.iterrows():
            print(f"  {row['person_id']}: {row['person_name']}")
        return

    print("✅ No PSY record found, proceeding with restoration...")

    # 3. 新しいperson_idを生成
    # 既存の最大IDを取得
    existing_ids = df['person_id'].str.extract(r'P(\d+)', expand=False).astype(float)
    max_id = int(existing_ids.max())
    new_person_id = f"P{max_id + 1:06d}"
    print(f"\n📝 Generating new person_id: {new_person_id}")

    # 4. PSYレコードを作成
    print("\n🎵 Creating PSY record...")

    # extended_dataを作成
    extended_data = {
        "original_batch_id": "korean_artists",
        "cultural_significance": "9",
        "educational_value": "5",
        "historical_impact": "7",
        "global_recognition": "10",
        "followers": "",
        "platform": "",
        "main_category": "エンタメ",
        "subcategory": "歌手",
        "is_fictional": "FALSE",
        "is_animal": "FALSE",
        "note": "Gangnam Style artist",
        "conversion_date": datetime.now().isoformat(),
        "restoration_date": datetime.now().isoformat(),
        "restoration_reason": "Missing record restored after P000305 fix"
    }

    # recognition_metadataを作成
    recognition_metadata = {
        "japan_score": 85.0,
        "global_score": 95.0,
        "education_impact": 40,
        "media_presence": 100,
        "social_relevance": 85,
        "calibrated_at": datetime.now().isoformat(),
        "original_score": "90",
        "calibrated_score": 85
    }

    # 新しいレコードを作成
    new_record = {
        'accuracy_score': 95,
        'age': np.nan,
        'age_months': np.nan,
        'category': 'エンタメ',
        'created_at': datetime.now().isoformat(),
        'episode_date': np.nan,
        'episode_hash': f"psy_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        'episode_id': f"EP_{datetime.now().strftime('%Y%m%d_%H%M%S')}_PSY",
        'episode_text': np.nan,
        'episode_title': np.nan,
        'episode_type': np.nan,
        'episode_year': np.nan,
        'era': '現代',
        'extended_data': json.dumps(extended_data, ensure_ascii=False),
        'impact_score': 90,
        'is_published': True,
        'name_recognition': 85,
        'nationality': '韓国',
        'occupation': '歌手',
        'person_id': new_person_id,
        'person_name': 'PSY',
        'person_name_display': 'PSY (サイ)',
        'person_name_ja': 'サイ',
        'recognition_metadata': json.dumps(recognition_metadata, ensure_ascii=False),
        'source': 'Restored Record'
    }

    print("  ✅ PSY record created:")
    print(f"    person_id: {new_record['person_id']}")
    print(f"    person_name: {new_record['person_name']}")
    print(f"    person_name_display: {new_record['person_name_display']}")
    print(f"    person_name_ja: {new_record['person_name_ja']}")
    print(f"    occupation: {new_record['occupation']}")
    print(f"    nationality: {new_record['nationality']}")
    print(f"    name_recognition: {new_record['name_recognition']}")

    # 5. データベースに追加
    df = pd.concat([df, pd.DataFrame([new_record])], ignore_index=True)
    print(f"\n✅ PSY record added to database")
    print(f"  Total records: {len(df)}")

    # 6. 保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"ultra_think_PSY_RESTORED_{timestamp}.csv"
    df.to_csv(output_file, index=False, encoding='utf-8')
    print(f"\n💾 Database with PSY saved to {output_file}")

    # 7. 復元ログを記録
    restore_log = {
        'timestamp': datetime.now().isoformat(),
        'action': 'PSY record restoration',
        'new_person_id': new_person_id,
        'record': {
            'person_name': 'PSY',
            'person_name_display': 'PSY (サイ)',
            'person_name_ja': 'サイ',
            'occupation': '歌手',
            'nationality': '韓国',
            'name_recognition': 85
        },
        'reason': 'Record was missing after deduplication, restored as Korean rapper/singer',
        'output_file': output_file
    }

    log_file = f"psy_restore_log_{timestamp}.json"
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(restore_log, f, ensure_ascii=False, indent=2)
    print(f"📝 Restore log saved to {log_file}")

    # 8. 検証
    print("\n🔍 Verification:")
    psy_check = df[df['person_name'] == 'PSY']
    if not psy_check.empty:
        print("  ✅ PSY record successfully added")
    else:
        print("  ❌ PSY record addition failed")

    # Usain Boltの確認
    bolt_check = df[df['person_id'] == 'P000305']
    if not bolt_check.empty:
        bolt = bolt_check.iloc[0]
        if bolt['person_name_display'] != 'PSY':
            print("  ✅ P000305 (Usain Bolt) display name is correct")
        else:
            print("  ❌ P000305 still has PSY display name!")

    return output_file

if __name__ == "__main__":
    output_file = main()
    print(f"\n🎉 PSY レコードの復元が完了しました！")
    print(f"   Output: {output_file}")
    print(f"   Next step: python3 fix_occupation_category_mismatches.py")
