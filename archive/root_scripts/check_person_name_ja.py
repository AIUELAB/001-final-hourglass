#!/usr/bin/env python3
"""
person_name_jaフィールドの生成結果確認
"""

import json


def main():
    """メイン処理"""
    data_file = 'final_12410_with_person_name_ja.json'

    # JSONファイルを読み込み
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print("=== person_name_ja生成結果の確認 ===")
    print(f"データ件数: {len(data)}")

    # person_name_jaフィールドの確認
    person_name_ja_count = 0
    for key, person in data.items():
        if 'person_name_ja' in person:
            person_name_ja_count += 1

    print(f"person_name_jaフィールドが存在するエントリ: {person_name_ja_count}件")

    # サンプルデータ表示
    print("\n=== サンプルデータ ===")
    sample_keys = list(data.keys())[:5]
    for key in sample_keys:
        person = data[key]
        print(f"ID: {key}")
        print(f"  名前: {person.get('name', 'N/A')}")
        print(f"  person_name_ja: {person.get('person_name_ja', 'N/A')}")
        print(f"  職業: {person.get('occupation', 'N/A')}")
        print()

    # フィールドの一貫性チェック
    print("=== フィールドの一貫性チェック ===")
    inconsistent_count = 0
    for key, person in data.items():
        name = person.get('name', '')
        person_name_ja = person.get('person_name_ja', '')
        if name != person_name_ja:
            inconsistent_count += 1
            if inconsistent_count <= 3:  # 最初の3件のみ表示
                print(f"不一致: {key}")
                print(f"  name: {name}")
                print(f"  person_name_ja: {person_name_ja}")
                print()

    print(f"不一致件数: {inconsistent_count}件")

    if inconsistent_count == 0:
        print("✅ すべてのエントリでnameとperson_name_jaが一致しています")
    else:
        print("⚠️ 一部のエントリで不一致が検出されました")

if __name__ == "__main__":
    main()
