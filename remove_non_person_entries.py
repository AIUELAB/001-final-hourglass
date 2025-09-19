#!/usr/bin/env python3
"""
person_name_displayフィールドが明らかに人名でないエントリを削除
"""

import csv
import json
import shutil
from datetime import datetime


# ファイルから削除対象IDを読み込む
def load_delete_ids():
    """non_person_ids.txtから削除対象IDを読み込む"""
    try:
        with open('non_person_ids.txt', 'r') as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return []

def main():
    """メイン処理"""
    print("=" * 60)
    print("非人名エントリの削除")
    print("=" * 60)
    
    input_file = 'final_12410_firebase_20250822_201828.json'
    
    # バックアップ作成
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f'backup_before_cleanup_{timestamp}.json'
    shutil.copy2(input_file, backup_file)
    print(f"✅ バックアップ作成: {backup_file}")
    
    # JSON読み込み
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    initial_count = len(data)
    print(f"\n📊 初期データ数: {initial_count}件")
    
    # 削除対象IDを読み込む
    delete_ids = load_delete_ids()
    if not delete_ids:
        print("❌ 削除対象IDが見つかりません")
        return 0
    
    print(f"📋 削除対象: {len(delete_ids)}件")
    
    # 削除処理
    deleted_entries = []
    for delete_id in delete_ids:
        if delete_id in data:
            entry = data[delete_id]
            deleted_entries.append({
                'id': delete_id,
                'person_name': entry.get('person_name', ''),
                'person_name_display': entry.get('person_name_display', ''),
                'category': entry.get('main_category', '')
            })
            del data[delete_id]
            print(f"  ❌ 削除: {delete_id} - {entry.get('person_name_display', '')}")
    
    # 結果を保存
    output_file = f'cleaned_{timestamp}.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    # 削除ログ保存
    log_file = f'cleanup_log_{timestamp}.json'
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump({
            'deleted_count': len(deleted_entries),
            'timestamp': timestamp,
            'deleted_entries': deleted_entries
        }, f, ensure_ascii=False, indent=2)
    
    # 元のファイルを更新
    shutil.copy2(output_file, input_file)
    
    final_count = len(data)
    
    print("\n📊 処理結果:")
    print(f"  削除件数: {len(deleted_entries)}件")
    print(f"  最終データ数: {final_count}件")
    
    # カテゴリ別削除数
    category_counts = {}
    for entry in deleted_entries:
        cat = entry['category'] or '不明'
        category_counts[cat] = category_counts.get(cat, 0) + 1
    
    print("\n📊 カテゴリ別削除数:")
    for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {cat}: {count}件")
    
    # CSV出力
    print("\n📊 CSV出力中...")
    csv_filename = f'cleaned_{timestamp}.csv'
    
    headers = [
        'id', 'person_name', 'person_name_ja', 'person_name_display', 'grade',
        'birth_date', 'death_date', 'nationality', 'occupation',
        'main_category', 'subcategory', 'description'
    ]
    
    with open(csv_filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        
        for key, person in data.items():
            row = {
                'id': person.get('id', key),
                'person_name': person.get('person_name', ''),
                'person_name_ja': person.get('person_name_ja', ''),
                'person_name_display': person.get('person_name_display', ''),
                'grade': person.get('grade', ''),
                'birth_date': person.get('birth_date', ''),
                'death_date': person.get('death_date', ''),
                'nationality': person.get('nationality', ''),
                'occupation': person.get('occupation', ''),
                'main_category': person.get('main_category', ''),
                'subcategory': person.get('subcategory', ''),
                'description': person.get('description', '')
            }
            writer.writerow(row)
    
    print(f"✅ CSV出力完了: {csv_filename}")
    
    return len(deleted_entries)

if __name__ == "__main__":
    main()
