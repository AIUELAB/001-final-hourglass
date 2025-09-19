#!/usr/bin/env python3
"""
最終的に修正されたデータのCSVエクスポート
"""

import csv
import json
from datetime import datetime


def main():
    """メイン処理"""
    print("=" * 60)
    print("最終修正済みデータのCSV出力")
    print("=" * 60)
    
    # JSON読み込み
    input_file = 'final_12410_firebase_20250822_201828.json'
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_filename = f'final_corrected_{timestamp}.csv'
    
    # ヘッダー定義
    headers = [
        'id', 'person_name', 'person_name_ja', 'person_name_display', 'grade',
        'birth_date', 'death_date', 'nationality', 'occupation',
        'main_category', 'subcategory', 'description', 'wikidata_id'
    ]
    
    # CSV書き込み
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
                'description': person.get('description', ''),
                'wikidata_id': person.get('wikidata_id', '')
            }
            writer.writerow(row)
    
    print(f"✅ 最終CSV出力完了: {csv_filename}")
    print(f"📊 総エントリ数: {len(data)}件")
    
    # カテゴリー統計
    category_stats = {}
    subcategory_stats = {}
    
    for person in data.values():
        main_cat = person.get('main_category', '未設定')
        sub_cat = person.get('subcategory', '未設定')
        
        category_stats[main_cat] = category_stats.get(main_cat, 0) + 1
        if sub_cat:
            subcategory_stats[sub_cat] = subcategory_stats.get(sub_cat, 0) + 1
    
    print("\n📊 メインカテゴリー分布:")
    for cat, count in sorted(category_stats.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {cat}: {count}件")
    
    print("\n📊 サブカテゴリー分布（上位10）:")
    for cat, count in sorted(subcategory_stats.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {cat}: {count}件")
    
    # 修正確認
    print("\n✅ 主要人物の確認:")
    check_list = [
        'ガッツ石松', '桑田佳祐', '赤崎勇', '川端康成', 
        '大島渚', '黒澤明', '小津安二郎', 'クリストファー・ノーラン'
    ]
    
    for key, person in data.items():
        name = person.get('person_name_ja', '')
        display = person.get('person_name_display', '')
        
        if name in check_list or display in check_list:
            print(f"  {display}: {person.get('subcategory', '')} / {person.get('occupation', '')}")
    
    return csv_filename

if __name__ == "__main__":
    main()