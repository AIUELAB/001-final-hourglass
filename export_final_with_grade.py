#!/usr/bin/env python3
"""
最終的なCSVエクスポート（gradeカラム付き）
"""

import csv
import json
from datetime import datetime


def main():
    """メイン処理"""
    print("=" * 60)
    print("最終CSV出力（gradeカラム付き）")
    print("=" * 60)

    # JSON読み込み
    input_file = 'final_12410_firebase_20250822_201828.json'
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_filename = f'final_with_grade_{timestamp}.csv'

    # ヘッダー定義（gradeを含む）
    headers = [
        'id', 'person_name', 'person_name_ja', 'person_name_display', 'grade',
        'birth_date', 'death_date', 'nationality', 'occupation',
        'main_category', 'subcategory', 'description'
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
                'description': person.get('description', '')
            }
            writer.writerow(row)

    print(f"✅ 最終CSV出力完了: {csv_filename}")
    print(f"📊 総エントリ数: {len(data)}件")

    # Grade別統計
    grade_counts = {}
    for person in data.values():
        grade = person.get('grade', '未設定')
        grade_counts[grade] = grade_counts.get(grade, 0) + 1

    print("\n📊 Grade別統計:")
    for grade in ['A', 'B', 'C', 'D', '未設定']:
        if grade in grade_counts:
            print(f"  Grade {grade}: {grade_counts[grade]}件")

    return csv_filename

if __name__ == "__main__":
    main()
