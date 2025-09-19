#!/usr/bin/env python3
"""
Wikidataコレクターのテスト実行
"""

import pandas as pd
from wikidata_birth_collector_optimized import WikidataBirthCollector
import logging

logging.basicConfig(level=logging.INFO)

# テストデータ作成
test_data = pd.DataFrame([
    {'person_id': 'P000543', 'person_name': 'Kobe Bryant', 'person_name_ja': 'コービー・ブライアント', 'birth_year_int': None},
    {'person_id': 'P001365', 'person_name': 'Ulysses S. Grant', 'person_name_ja': 'ユリシーズ・グラント', 'birth_year_int': None},
    {'person_id': 'P002884', 'person_name': '小林陵侑', 'person_name_ja': '小林陵侑', 'birth_year_int': None},
    {'person_id': 'P015812', 'person_name': 'Félix Tshisekedi', 'person_name_ja': 'フェリックス・チセケディ', 'birth_year_int': None},
    {'person_id': 'P002304', 'person_name': 'Hara', 'person_name_ja': '原', 'birth_year_int': None}
])

print("🧪 テスト実行: Wikidataから誕生年取得")
print("=" * 60)
print("テスト対象:")
for _, row in test_data.iterrows():
    print(f"  - {row['person_id']}: {row['person_name_ja']}")
print("=" * 60)

# コレクター初期化
collector = WikidataBirthCollector()

# テスト実行
results = collector.process_dataframe(test_data, batch_size=5)

print("\n📊 テスト結果:")
print("=" * 60)
for _, row in results.iterrows():
    if pd.notna(row.get('birth_year_int')):
        print(f"✅ {row['person_id']}: {row['person_name_ja']} -> {row['birth_year_int']}")
    else:
        print(f"❌ {row['person_id']}: {row['person_name_ja']} -> 取得失敗")

# 統計
total = len(results)
found = results['birth_year_int'].notna().sum()
print("=" * 60)
print(f"成功率: {found}/{total} ({found/total*100:.1f}%)")