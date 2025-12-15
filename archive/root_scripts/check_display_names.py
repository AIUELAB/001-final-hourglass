#!/usr/bin/env python3
"""
display_name_jaフィールドの生成結果確認
"""

import json


def main():
    """メイン処理"""
    data_file = 'final_12410_with_display_names.json'

    # JSONファイルを読み込み
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print("=== display_name_ja生成結果の確認 ===")
    print(f"データ件数: {len(data)}")

    # display_name_jaフィールドの確認
    display_names_count = 0
    for key, person in data.items():
        if 'display_name_ja' in person:
            display_names_count += 1

    print(f"display_name_jaフィールドが存在するエントリ: {display_names_count}件")

    # サンプル表示
    print("\n=== サンプルデータ ===")
    sample_keys = list(data.keys())[:5]
    for key in sample_keys:
        person = data[key]
        print(f"ID: {key}")
        print(f"  名前: {person.get('name', 'N/A')}")
        print(f"  display_name_ja: {person.get('display_name_ja', 'N/A')}")
        print(f"  職業: {person.get('occupation', 'N/A')}")
        print()

    # フィールドの一貫性チェック
    print("=== フィールドの一貫性チェック ===")
    inconsistent_count = 0
    for key, person in data.items():
        name = person.get('name', '')
        display_name_ja = person.get('display_name_ja', '')
        if name and display_name_ja and name not in display_name_ja:
            inconsistent_count += 1
            if inconsistent_count <= 3:  # 最初の3件のみ表示
                print(f"不一致: {key}")
                print(f"  name: {name}")
                print(f"  display_name_ja: {display_name_ja}")
                print()

    print(f"不一致件数: {inconsistent_count}件")

    if inconsistent_count == 0:
        print("✅ すべてのエントリでdisplay_name_jaが正常に生成されています")
    else:
        print("⚠️ 一部のエントリで不一致が検出されました")

if __name__ == "__main__":
    main()
