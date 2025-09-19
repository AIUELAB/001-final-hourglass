#!/usr/bin/env python3
"""
りんたろーデータの正しい復元
P000141とP000142の重複から、より品質の高い方を選んで復元
"""

import pandas as pd
import shutil
from datetime import datetime

def main():
    print("="*60)
    print("りんたろーデータ復元プロセス")
    print("="*60)
    
    # 1. オリジナルデータから該当レコードを取得
    original_file = 'ultra_think_GROUP_FIXED_20250831_185100.csv'
    print(f"\n📂 Loading original data from {original_file}...")
    original_df = pd.read_csv(original_file, encoding='utf-8')
    
    # りんたろーのレコードを検索
    rintaro_records = original_df[original_df['person_id'].isin(['P000141', 'P000142'])]
    
    if rintaro_records.empty:
        print("❌ りんたろーのレコードが見つかりません")
        return
    
    print(f"\n🔍 Found {len(rintaro_records)} りんたろー records:")
    for _, row in rintaro_records.iterrows():
        print(f"   {row['person_id']}: {row['person_name']} (Recognition: {row.get('name_recognition', 0)})")
    
    # 2. より品質の高いレコードを選択
    # P000141: りんたろー。(Recognition: 49)
    # P000142: りんたろー (Recognition: 35)
    best_record = rintaro_records.loc[rintaro_records['name_recognition'].idxmax()]
    print(f"\n✅ Selected best quality record: {best_record['person_id']} (Recognition: {best_record['name_recognition']})")
    
    # 表示名を統一（句読点なし版）
    best_record = best_record.copy()
    best_record['person_name'] = 'りんたろー'
    best_record['person_name_display'] = 'りんたろー (EXIT)'
    
    # 3. 現在のクリーンデータベースに追加
    current_file = 'ultra_think_GROUP_FIXED_DEDUPLICATED_20250831_193249.csv'
    print(f"\n📂 Loading current database from {current_file}...")
    current_df = pd.read_csv(current_file, encoding='utf-8')
    
    # バックアップ作成
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f"backup_before_rintaro_restore_{timestamp}.csv"
    shutil.copy2(current_file, backup_file)
    print(f"💾 Backup created: {backup_file}")
    
    # りんたろーを追加
    updated_df = pd.concat([current_df, pd.DataFrame([best_record])], ignore_index=True)
    
    # 4. 保存
    output_file = f"ultra_think_FINAL_CLEAN_{timestamp}.csv"
    updated_df.to_csv(output_file, index=False, encoding='utf-8')
    print(f"\n✅ Database updated with りんたろー record")
    print(f"   Output file: {output_file}")
    print(f"   Total records: {len(updated_df)}")
    
    # 5. 検証
    print("\n🔍 Verification:")
    rintaro_check = updated_df[updated_df['person_name'].str.contains('りんたろー', na=False)]
    if not rintaro_check.empty:
        for _, row in rintaro_check.iterrows():
            print(f"   ✅ {row['person_id']}: {row['person_name_display']}")
    
    # 統計
    print(f"\n📊 Final Statistics:")
    print(f"   Total records: {len(updated_df)}")
    print(f"   Unique person_ids: {updated_df['person_id'].nunique()}")
    print(f"   りんたろー restored: ✅")
    
    return output_file

if __name__ == "__main__":
    output_file = main()
    print(f"\n🎉 りんたろーの復元が完了しました！")
    print(f"   Next step: python3 direct_sync.py")
