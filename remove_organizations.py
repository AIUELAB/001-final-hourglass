#!/usr/bin/env python3
"""
組織レコード除去スクリプト
個人データベースから誤って含まれた組織を削除
"""

import pandas as pd
import json
from datetime import datetime
import shutil

def remove_organizations():
    """組織レコードを削除"""
    print("="*60)
    print("🔧 組織レコード除去")
    print("="*60)
    
    # バックアップ作成
    csv_file = "ultra_think_EPISODE_FINAL_20250901_020106_fixed.csv"
    backup_file = f"backup_{csv_file}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy(csv_file, backup_file)
    print(f"📦 バックアップ作成: {backup_file}")
    
    # データ読み込み
    df = pd.read_csv(csv_file)
    original_count = len(df)
    print(f"📂 データ読み込み: {original_count}件")
    
    # 組織レコードの確認
    print("\n🔍 組織レコードの確認:")
    organizations = df[df['entity_type'] == 'organization']
    print(f"  組織として分類されているレコード: {len(organizations)}件")
    
    if not organizations.empty:
        print("\n削除対象:")
        for idx, row in organizations.iterrows():
            print(f"  - {row['person_id']}: {row['person_name_ja']}")
            if pd.notna(row.get('occupation')):
                print(f"    職業: {row['occupation']}")
            if pd.notna(row.get('nationality')):
                print(f"    国籍: {row['nationality']}")
    
    # 組織レコードを削除
    df_cleaned = df[df['entity_type'] != 'organization'].copy()
    removed_count = original_count - len(df_cleaned)
    
    print(f"\n✂️ 削除されたレコード数: {removed_count}件")
    
    # 削除後の統計
    print("\n📊 削除後のentity_type分布:")
    entity_type_dist = df_cleaned['entity_type'].value_counts()
    print(entity_type_dist)
    
    # 削除記録の作成
    removal_report = {
        "timestamp": datetime.now().isoformat(),
        "removed_records": removed_count,
        "removed_ids": organizations['person_id'].tolist() if not organizations.empty else [],
        "removed_details": []
    }
    
    for idx, row in organizations.iterrows():
        removal_report["removed_details"].append({
            "person_id": row['person_id'],
            "person_name_ja": row['person_name_ja'],
            "person_name": row.get('person_name', ''),
            "occupation": row.get('occupation', ''),
            "nationality": row.get('nationality', ''),
            "entity_type": row['entity_type']
        })
    
    # 削除記録を保存
    with open('organization_removal_report.json', 'w', encoding='utf-8') as f:
        json.dump(removal_report, f, ensure_ascii=False, indent=2)
    print(f"\n📝 削除記録保存: organization_removal_report.json")
    
    # CSVファイルを保存
    df_cleaned.to_csv(csv_file, index=False, encoding='utf-8-sig')
    print(f"\n💾 クリーンデータ保存: {csv_file}")
    print(f"📊 最終レコード数: {len(df_cleaned)}件 (削除: {removed_count}件)")
    
    # 品質検証
    print("\n✅ 品質検証:")
    print(f"  組織レコード残存: {(df_cleaned['entity_type'] == 'organization').sum()}件")
    print(f"  データ整合性: {'OK' if len(df_cleaned) == original_count - removed_count else 'ERROR'}")
    
    # 特定IDの確認（世界食糧計画など）
    specific_checks = ['P015757', 'P002087', 'P004140', 'P015868']
    print("\n🔍 特定IDの削除確認:")
    for check_id in specific_checks:
        if check_id in organizations['person_id'].values:
            print(f"  ✅ {check_id}: 削除済み")
        elif check_id in df_cleaned['person_id'].values:
            print(f"  ⚠️ {check_id}: まだ存在")
        else:
            print(f"  - {check_id}: 元々存在しない")
    
    return df_cleaned

if __name__ == "__main__":
    df = remove_organizations()
    print("\n✅ 組織レコード除去完了")