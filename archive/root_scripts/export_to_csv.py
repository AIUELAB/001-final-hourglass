#!/usr/bin/env python3
"""
final_12410_firebase_20250822_201828.jsonをCSVに変換
"""

import csv
import json
from datetime import datetime


def json_to_csv():
    """JSONファイルをCSVに変換"""

    # JSONファイル読み込み
    with open('final_12410_firebase_20250822_201828.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    # CSVファイル名（タイムスタンプ付き）
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_filename = f'final_12410_export_{timestamp}.csv'

    # CSVヘッダー定義（主要フィールド）
    headers = [
        'id',
        'person_name',
        'person_name_ja',
        'person_name_display',
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
        'grade',
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
                'grade': person.get('grade', ''),
                'data_source': person.get('data_source', ''),
                'created_at': person.get('created_at', '')
            }
            writer.writerow(row)

    print(f"✅ CSV出力完了: {csv_filename}")
    print(f"   レコード数: {len(data)}件")

    # サンプル表示
    print("\n📝 CSVの最初の5件:")
    with open(csv_filename, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader):
            if i >= 6:  # ヘッダー + 5件
                break
            if i == 0:
                print("   ヘッダー:", ', '.join(row[:5]) + '...')
            else:
                print(f"   {i}. {row[1]} | {row[2]} | {row[3]}")

    return csv_filename

if __name__ == "__main__":
    json_to_csv()
