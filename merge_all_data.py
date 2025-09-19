#!/usr/bin/env python3
"""
すべての有名人データを統合
"""

import csv
import json
from datetime import datetime


def merge_all_data():
    """すべてのデータを統合"""
    
    all_people = []
    
    # 1. 元のデータ（拡張カテゴリ適用済み）を読み込み
    base_file = 'extended_categorized_people_20250821_233050.csv'
    print(f"📚 基本データを読み込み中: {base_file}")
    
    with open(base_file, 'r', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            all_people.append(row)
    
    print(f"  ✅ {len(all_people)}人のデータを読み込みました")
    
    # 2. 日本のエンターテイナーデータを追加
    entertainers_file = 'japanese_entertainers_20250821_235024.csv'
    print(f"📚 エンターテイナーデータを読み込み中: {entertainers_file}")
    
    entertainers_count = 0
    with open(entertainers_file, 'r', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            all_people.append(row)
            entertainers_count += 1
    
    print(f"  ✅ {entertainers_count}人のエンターテイナーを追加しました")
    
    # 3. 統計情報を計算
    print("\n📊 統合後の統計:")
    
    # カテゴリ別集計
    main_categories = {}
    subcategories = {}
    
    for person in all_people:
        # メインカテゴリ
        main_cat = person.get('main_category', 'その他')
        main_categories[main_cat] = main_categories.get(main_cat, 0) + 1
        
        # サブカテゴリ
        sub_cat = person.get('subcategory', '')
        if sub_cat:
            subcategories[sub_cat] = subcategories.get(sub_cat, 0) + 1
    
    print(f"\n総人数: {len(all_people):,}人")
    
    print("\nメインカテゴリ TOP10:")
    for cat, count in sorted(main_categories.items(), key=lambda x: x[1], reverse=True)[:10]:
        percentage = (count / len(all_people)) * 100
        print(f"  {cat}: {count:,}人 ({percentage:.1f}%)")
    
    # 4. 統合データをCSVに出力
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"all_people_merged_{timestamp}.csv"
    
    print(f"\n💾 統合データを出力中: {output_file}")
    
    with open(output_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
        fieldnames = [
            'id', 'name', 'name_ja', 'birth_year', 'death_year', 'death_age',
            'nationality', 'occupation', 'main_category', 'subcategory',
            'special_tags', 'source', 'wikidata_id', 'description', 'key_ages'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
        
        writer.writeheader()
        writer.writerows(all_people)
    
    # 5. 目標達成状況を表示
    required = 12410
    current = len(all_people)
    shortage = required - current
    
    print("\n🎯 目標達成状況:")
    print(f"  現在の人数: {current:,}人")
    print(f"  必要人数: {required:,}人")
    if shortage > 0:
        print(f"  不足: {shortage:,}人")
        progress = (current / required) * 100
        print(f"  進捗率: {progress:.1f}%")
    else:
        print(f"  ✅ 目標達成！（余剰: {-shortage:,}人）")
    
    # 6. コスト見積もり更新
    print("\n💰 コスト見積もり（更新）:")
    
    # これまでのコスト
    cost_so_far = {
        'data_collection': 0,  # Wikidata無料
        'manual_entry': 5,  # 51人×0.1ドル
        'processing': 10,  # GPT-4処理
    }
    
    # 残りのコスト見積もり
    remaining_cost = {
        'data_collection': shortage * 0.01,  # 1人あたり0.01ドル
        'processing': shortage * 0.02,  # GPT-4処理
        'manual_validation': shortage * 0.05,  # 手動検証
    }
    
    total_spent = sum(cost_so_far.values())
    total_remaining = sum(remaining_cost.values())
    total_cost = total_spent + total_remaining
    
    print(f"  これまでの費用: ${total_spent:.2f}")
    print(f"  残り必要費用: ${total_remaining:.2f}")
    print(f"  総費用見積もり: ${total_cost:.2f} (約{int(total_cost * 150):,}円)")
    
    print("\n✅ 統合完了！")
    print(f"📄 出力ファイル: {output_file}")
    
    return output_file, current, shortage

if __name__ == "__main__":
    output_file, current, shortage = merge_all_data()