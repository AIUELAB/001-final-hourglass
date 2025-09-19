#!/usr/bin/env python3
"""
クリーンアップ結果の確認
"""

import json


def main():
    """メイン処理"""
    data_file = 'final_12410_firebase_20250822_201828.json'

    # JSONファイルを読み込み
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print("=== クリーンアップ後の確認 ===")
    print(f"データ件数: {len(data)}")

    # 破損した名前の確認
    corrupted_names = [k for k, v in data.items() if 'name' in v and v['name'] == '[名前不明]']
    print(f"破損した名前件数: {len(corrupted_names)}")

    if corrupted_names:
        print(f"破損した名前例: {corrupted_names[0]}")
        person = data[corrupted_names[0]]
        print(f"  職業: {person.get('occupation', 'N/A')}")

    # フィルタリングされた職業の確認
    filtered_occupations = [k for k, v in data.items() if 'occupation' in v and v['occupation'] == '[フィルタリング済み]']
    print(f"フィルタリングされた職業件数: {len(filtered_occupations)}")

    # 正規化された職業の確認
    normalized_occupations = [k for k, v in data.items() if 'occupation' in v and v['occupation'] in ['俳優', '女優', 'actor', 'actress']]
    print(f"正規化された職業件数: {len(normalized_occupations)}")

    # サンプル表示
    print("\n=== サンプルデータ ===")
    sample_keys = list(data.keys())[:5]
    for key in sample_keys:
        person = data[key]
        print(f"ID: {key}")
        print(f"  名前: {person.get('name', 'N/A')}")
        print(f"  職業: {person.get('occupation', 'N/A')}")
        print()

if __name__ == "__main__":
    main()
