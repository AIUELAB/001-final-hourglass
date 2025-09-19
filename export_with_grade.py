#!/usr/bin/env python3
"""
gradeカラムを含むCSV出力
"""

import csv
import json
from datetime import datetime


def export_to_csv_with_grade():
    """gradeカラムを含むCSVエクスポート"""
    
    # JSONファイル読み込み（変換済みのファイル）
    with open('final_12410_firebase_20250822_201828.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # タイムスタンプ
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_filename = f'final_with_grade_{timestamp}.csv'
    
    # CSVヘッダー定義（gradeを追加）
    headers = [
        'id',
        'person_name',
        'person_name_ja', 
        'person_name_display',
        'grade',  # gradeカラムを追加
        'birth_date',
        'death_date',
        'nationality',
        'occupation',
        'main_category',
        'subcategory',
        'wikidata_id',
        'description',
        'impact_score',
        'japanese_relevance',
        'data_source',
        'created_at'
    ]
    
    # CSV書き込み
    with open(csv_filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        
        # データを行として書き込み
        for key, person in data.items():
            row = {
                'id': person.get('id', key),
                'person_name': person.get('person_name', ''),
                'person_name_ja': person.get('person_name_ja', ''),
                'person_name_display': person.get('person_name_display', ''),
                'grade': person.get('grade', ''),  # gradeフィールドを追加
                'birth_date': person.get('birth_date', ''),
                'death_date': person.get('death_date', ''),
                'nationality': person.get('nationality', ''),
                'occupation': person.get('occupation', ''),
                'main_category': person.get('main_category', ''),
                'subcategory': person.get('subcategory', ''),
                'wikidata_id': person.get('wikidata_id', ''),
                'description': person.get('description', ''),
                'impact_score': person.get('impact_score', ''),
                'japanese_relevance': person.get('japanese_relevance', ''),
                'data_source': person.get('data_source', ''),
                'created_at': person.get('created_at', '')
            }
            writer.writerow(row)
    
    print(f"✅ CSV出力完了: {csv_filename}")
    print(f"   レコード数: {len(data)}件")
    print("   gradeカラムを含む")
    
    # サンプル表示（grade含む）
    print("\n📝 CSVサンプル（最初の10件）:")
    with open(csv_filename, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= 10:
                break
            print(f"   {i+1}. {row['id']} | {row['person_name']} | {row['person_name_ja']} | {row['person_name_display']} | grade: {row['grade']}")
    
    # gradeフィールドの統計
    print("\n📊 gradeフィールドの統計:")
    grade_stats = {}
    for person in data.values():
        grade = person.get('grade', '空')
        if grade == '':
            grade = '空'
        grade_stats[grade] = grade_stats.get(grade, 0) + 1
    
    for grade, count in sorted(grade_stats.items()):
        print(f"   {grade}: {count}件")
    
    return csv_filename

if __name__ == "__main__":
    export_to_csv_with_grade()