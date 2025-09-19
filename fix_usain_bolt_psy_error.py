#!/usr/bin/env python3
"""
Fix P000305 (Usain Bolt) Data Corruption
P000305のデータ破損を修復

This script fixes the critical error where Usain Bolt's display name
was incorrectly set to "PSY" and occupation was set to "YouTuber".
"""

import pandas as pd
import json
from datetime import datetime
import shutil

def main():
    print("="*60)
    print("P000305 (Usain Bolt) データ修復プロセス")
    print("="*60)
    
    # 1. データ読み込み
    csv_file = 'ultra_think_FINAL_CLEAN_20250831_205221.csv'
    print(f"\n📂 Loading database from {csv_file}...")
    df = pd.read_csv(csv_file, encoding='utf-8')
    print(f"✅ Loaded {len(df)} records")
    
    # 2. P000305の現状確認
    print("\n🔍 Checking P000305 current state...")
    p000305_mask = df['person_id'] == 'P000305'
    if not df[p000305_mask].empty:
        current = df[p000305_mask].iloc[0]
        print(f"  person_id: {current['person_id']}")
        print(f"  person_name: {current['person_name']}")
        print(f"  person_name_display: {current['person_name_display']} ❌")
        print(f"  person_name_ja: {current['person_name_ja']}")
        print(f"  occupation: {current['occupation']} ❌")
        print(f"  nationality: {current['nationality']}")
        print(f"  category: {current['category']}")
    else:
        print("❌ P000305 not found!")
        return
    
    # 3. 修正を適用
    print("\n🔧 Applying fixes...")
    
    # person_name_displayを修正
    df.loc[p000305_mask, 'person_name_display'] = 'ウサイン・ボルト'
    print("  ✅ person_name_display: PSY → ウサイン・ボルト")
    
    # occupationを修正
    df.loc[p000305_mask, 'occupation'] = '陸上選手'
    print("  ✅ occupation: YouTuber → 陸上選手")
    
    # extended_dataを修正
    extended_data = df.loc[p000305_mask, 'extended_data'].iloc[0]
    if pd.notna(extended_data):
        try:
            data = json.loads(extended_data)
            # YouTuber関連の情報を削除
            if 'platform' in data:
                del data['platform']
            # バッチIDを修正
            data['original_batch_id'] = 'sports_athletes'
            # subcategoryを修正
            data['subcategory'] = '陸上競技'
            # 修正日時を記録
            data['fix_date'] = datetime.now().isoformat()
            data['fix_reason'] = 'P000305 PSY display name error correction'
            
            df.loc[p000305_mask, 'extended_data'] = json.dumps(data, ensure_ascii=False)
            print("  ✅ extended_data: YouTuber情報を削除、sports_athletesバッチに修正")
        except json.JSONDecodeError:
            print("  ⚠️ extended_data parsing failed, skipping...")
    
    # 4. 修正後の確認
    print("\n✅ Fixed state:")
    fixed = df[p000305_mask].iloc[0]
    print(f"  person_name_display: {fixed['person_name_display']} ✅")
    print(f"  occupation: {fixed['occupation']} ✅")
    
    # 5. 保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"ultra_think_P000305_FIXED_{timestamp}.csv"
    df.to_csv(output_file, index=False, encoding='utf-8')
    print(f"\n💾 Fixed database saved to {output_file}")
    
    # 6. 修正ログを記録
    fix_log = {
        'timestamp': datetime.now().isoformat(),
        'person_id': 'P000305',
        'fixes': {
            'person_name_display': {'before': 'PSY', 'after': 'ウサイン・ボルト'},
            'occupation': {'before': 'YouTuber', 'after': '陸上選手'},
            'extended_data': {'platform': 'removed', 'batch_id': 'sports_athletes'}
        },
        'output_file': output_file
    }
    
    log_file = f"p000305_fix_log_{timestamp}.json"
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(fix_log, f, ensure_ascii=False, indent=2)
    print(f"📝 Fix log saved to {log_file}")
    
    # 7. 統計
    print("\n📊 Statistics:")
    print(f"  Total records: {len(df)}")
    print(f"  Records fixed: 1")
    print(f"  P000305 status: ✅ Fixed")
    
    return output_file

if __name__ == "__main__":
    output_file = main()
    print(f"\n🎉 P000305 (Usain Bolt) のデータ修復が完了しました！")
    print(f"   Output: {output_file}")
    print(f"   Next step: python3 restore_psy_record.py")