#!/usr/bin/env python3
"""
一般著名人レコードを抽出して分析
"""

import pandas as pd
import json

# CSVファイルを読み込み
csv_file = 'database_final_enriched_20250910_132247.csv'
df = pd.read_csv(csv_file)

# 一般著名人を抽出
generic_persons = df[
    (df['occupation'] == '一般著名人') &
    (df['description'] == '一般的な著名人')
].copy()

print(f"一般著名人レコード数: {len(generic_persons)}")

# 名前でグループ化して頻度を確認
name_counts = generic_persons['person_name'].value_counts()
print("\n同じ名前の重複:")
print(name_counts[name_counts > 1])

# 結果をJSONに保存
result = []
for idx, row in generic_persons.iterrows():
    result.append({
        'person_id': row['person_id'],
        'person_name': row['person_name'],
        'person_name_display': row['person_name_display'],
        'person_name_ja': row['person_name_ja'],
        'category': row['category'],
        'nationality': row['nationality'],
        'occupation': row['occupation'],
        'description': row['description'],
        'recognition_score': row['recognition_score']
    })

# JSON出力
with open('generic_persons_to_split.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"\n抽出結果を generic_persons_to_split.json に保存しました")

# 名前のリストを作成
unique_names = generic_persons['person_name'].unique()
print(f"\nユニークな名前数: {len(unique_names)}")

# 調査が必要な名前をリストアップ
print("\n調査が必要な名前:")
for i, name in enumerate(unique_names[:20], 1):
    print(f"{i}. {name}")

if len(unique_names) > 20:
    print(f"... 他 {len(unique_names) - 20} 件")
