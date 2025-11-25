#!/usr/bin/env python3
"""
残存する指定IDの確認
Check Remaining Target IDs
"""

import csv

def check_remaining():
    # 指定されたperson_idリストを読み込み
    with open('check_person_ids.txt', 'r') as f:
        target_ids = set(line.strip() for line in f if line.strip())

    # 最新のクリーンデータベースを読み込み
    input_file = "ultra_think_NO_PLACEHOLDERS_20250827_141708.csv"

    with open(input_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        all_rows = list(reader)

    # 残存する指定IDの人物を抽出
    remaining_targets = []
    for row in all_rows:
        if row['person_id'] in target_ids:
            remaining_targets.append(row)

    print(f"📋 残存する指定ID: {len(remaining_targets)}件")
    print("\n【サンプル（最初の50件）】")
    print("-" * 80)

    for i, person in enumerate(remaining_targets[:50], 1):
        print(f"{i:3}. ID: {person['person_id']}")
        print(f"     名前: {person['person_name']}")
        print(f"     日本語: {person['person_name_ja']}")
        print(f"     表示: {person['person_name_display']}")
        print(f"     カテゴリ: {person['category']}")
        print(f"     職業: {person['occupation']}")
        print(f"     知名度: {person['name_recognition']}")
        print()

    # パターン分析
    patterns = {}
    for person in remaining_targets:
        name = person['person_name']
        # 最初の単語を抽出してパターン化
        first_word = name.split()[0] if ' ' in name else name
        patterns[first_word] = patterns.get(first_word, 0) + 1

    print("\n【名前パターン分析（上位20）】")
    print("-" * 80)
    for pattern, count in sorted(patterns.items(), key=lambda x: x[1], reverse=True)[:20]:
        print(f"  {pattern}: {count}件")

if __name__ == "__main__":
    check_remaining()
