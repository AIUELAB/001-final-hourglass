#!/usr/bin/env python3
"""
最終プレースホルダー削除スクリプト
Final Placeholder Removal Script

このスクリプトは、特定された真のプレースホルダーを削除し、
クリーンなエピソードデータベースを作成します。
"""

import pandas as pd
import json
from datetime import datetime

def remove_placeholders(df, placeholder_ids):
    """
    特定されたプレースホルダーを削除
    """
    print(f"\n🗑️ Removing {len(placeholder_ids)} placeholders...")
    
    # 削除前のレコード数
    before_count = len(df)
    
    # 削除対象のレコードを確認
    deleted_records = []
    for pid in placeholder_ids:
        record = df[df['person_id'] == pid]
        if not record.empty:
            deleted_records.append({
                'person_id': pid,
                'person_name': record.iloc[0]['person_name'],
                'person_name_display': record.iloc[0]['person_name_display'],
                'occupation': record.iloc[0]['occupation'],
                'recognition': record.iloc[0].get('name_recognition', 0)
            })
    
    # プレースホルダーを削除
    df_clean = df[~df['person_id'].isin(placeholder_ids)]
    
    # 削除後のレコード数
    after_count = len(df_clean)
    deleted_count = before_count - after_count
    
    return df_clean, deleted_records, deleted_count

def validate_database(df):
    """
    データベースの品質検証
    """
    validation_results = {
        'total_records': len(df),
        'occupation_unknown': len(df[df['occupation'] == '不明']),
        'nationality_unknown': len(df[df['nationality'] == '不明']),
        'fictional_characters': len(df[df['category'] == '架空の存在']),
        'high_recognition': len(df[df['name_recognition'] >= 40]),
        'medium_recognition': len(df[(df['name_recognition'] >= 30) & (df['name_recognition'] < 40)]),
        'low_recognition': len(df[df['name_recognition'] < 30]),
        'empty_names': len(df[df['person_name'].isna() | (df['person_name'] == '')])
    }
    
    # カテゴリ分布
    if 'category' in df.columns:
        validation_results['category_distribution'] = df['category'].value_counts().to_dict()
    
    # occupation分布（上位10）
    validation_results['top_occupations'] = df['occupation'].value_counts().head(10).to_dict()
    
    return validation_results

def main():
    print("="*60)
    print("最終プレースホルダー削除")
    print("Final Placeholder Removal")
    print("="*60)
    
    # 修正済みデータベースを読み込み
    csv_file = 'ultra_think_PROTECTED_FIXED_20250901_015931.csv'
    print(f"\n📂 Loading protected database: {csv_file}")
    df = pd.read_csv(csv_file, encoding='utf-8')
    print(f"✅ Total records before deletion: {len(df)}")
    
    # 削除対象のプレースホルダーID
    placeholder_ids = ['P002091', 'P003123', 'P003608', 'P004394']
    
    print("\n🎯 Placeholders to delete:")
    print(f"  P002091: 兎 (Single character)")
    print(f"  P003123: 山田花子 (Test placeholder)")
    print(f"  P003608: 杏 (Single character)")
    print(f"  P004394: 田中太郎 (Test placeholder)")
    
    # プレースホルダーを削除
    df_clean, deleted_records, deleted_count = remove_placeholders(df, placeholder_ids)
    
    print(f"\n✅ Successfully deleted {deleted_count} placeholders")
    print(f"📊 Total records after deletion: {len(df_clean)}")
    
    # データベース検証
    print("\n🔍 Validating cleaned database...")
    validation_results = validate_database(df_clean)
    
    print(f"\n📊 Database Quality Metrics:")
    print(f"  Total records: {validation_results['total_records']}")
    print(f"  High recognition (≥40): {validation_results['high_recognition']} ({validation_results['high_recognition']/validation_results['total_records']*100:.1f}%)")
    print(f"  Medium recognition (30-39): {validation_results['medium_recognition']} ({validation_results['medium_recognition']/validation_results['total_records']*100:.1f}%)")
    print(f"  Low recognition (<30): {validation_results['low_recognition']} ({validation_results['low_recognition']/validation_results['total_records']*100:.1f}%)")
    print(f"  Fictional characters: {validation_results['fictional_characters']}")
    print(f"  Unknown occupation: {validation_results['occupation_unknown']}")
    print(f"  Empty names: {validation_results['empty_names']}")
    
    # タイムスタンプ
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # クリーンなデータベースを保存
    final_csv = f"ultra_think_EPISODE_FINAL_{timestamp}.csv"
    df_clean.to_csv(final_csv, index=False, encoding='utf-8')
    print(f"\n💾 Final clean database saved: {final_csv}")
    
    # 削除レポートを保存
    deletion_report = {
        'timestamp': datetime.now().isoformat(),
        'deleted_count': deleted_count,
        'deleted_records': deleted_records,
        'validation_results': validation_results,
        'final_database': {
            'filename': final_csv,
            'total_records': len(df_clean),
            'quality_score': (validation_results['high_recognition'] / validation_results['total_records']) * 100
        }
    }
    
    report_file = f"deletion_report_{timestamp}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(deletion_report, f, ensure_ascii=False, indent=2)
    print(f"📝 Deletion report saved: {report_file}")
    
    # 最終サマリー
    print("\n" + "="*60)
    print("🎯 EPISODE DATABASE CLEANUP COMPLETED")
    print("="*60)
    print(f"✅ Historical figures protected and fixed: 28")
    print(f"✅ Placeholders removed: {deleted_count}")
    print(f"✅ Final database records: {len(df_clean)}")
    print(f"✅ Database quality score: {deletion_report['final_database']['quality_score']:.1f}%")
    print("\n📚 The episode database is now clean and ready for use!")
    print(f"   High-quality episodes: {validation_results['high_recognition']}")
    print(f"   Fictional characters preserved: {validation_results['fictional_characters']}")
    
    return df_clean

if __name__ == "__main__":
    df_final = main()