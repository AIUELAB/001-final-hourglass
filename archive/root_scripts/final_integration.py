#!/usr/bin/env python3
"""
Final Integration - 全データ統合と最終データベース作成
"""

import json
import os
from datetime import datetime

import numpy as np
import pandas as pd


def integrate_all_data():
    """全データ統合"""

    all_people = []
    files_info = []

    # 収集済みファイルリスト
    data_files = [
        # 既存の大規模ファイル
        ('complete_12410_people_20250822_072301.csv', 'メインデータ'),
        ('all_famous_people_20250821_224848.csv', '有名人データ'),
        ('categorized_famous_people_20250821_225727.csv', 'カテゴリ分類済み'),
        ('detailed_categorized_famous_people_20250821_230406.csv', '詳細カテゴリ'),
        ('extended_categorized_people_20250821_233050.csv', '拡張カテゴリ'),

        # 新規収集
        ('wikidata_quick_20250822_193210.csv', 'Wikidata収集'),
        ('wikipedia_turbo_20250822_200648.csv', 'Wikipediaターボ'),

        # その他のデータ
        ('final_merged_data_20250822_001433.csv', '統合データ'),
        ('japan_focused_people_20250822_063736.csv', '日本重視'),
        ('inspirational_people_20250822_055814.csv', 'インスピレーション'),
        ('people_only_20250822_055027.csv', '人物のみ'),
        ('enhanced_people_data_20250822_004047.csv', '強化データ'),
        ('integrated_data_20250822_004637.csv', '統合済み'),
        ('japanese_entertainers_20250821_235024.csv', '日本エンターテイナー'),
        ('wikidata_lite_20250822_001114.csv', 'Wikidata軽量'),
        ('wikipedia_people_20250822_001309.csv', 'Wikipedia人物'),
    ]

    # 各ファイルを読み込み
    for filename, source_name in data_files:
        if os.path.exists(filename):
            try:
                df = pd.read_csv(filename, encoding='utf-8-sig')
                # NaNを空文字列に変換
                df = df.fillna('')

                # データ形式を統一
                for _, row in df.iterrows():
                    person = {
                        'name': str(row.get('name', '')),
                        'birth_date': str(row.get('birth_date', '')),
                        'death_date': str(row.get('death_date', '')),
                        'nationality': str(row.get('nationality', '')),
                        'occupation': str(row.get('occupation', '')),
                        'main_category': str(row.get('main_category', '')),
                        'subcategory': str(row.get('subcategory', '')),
                        'wikidata_id': str(row.get('wikidata_id', '')),
                        'description': str(row.get('description', '')),
                        'impact_score': row.get('impact_score', 7),
                        'japanese_relevance': row.get('japanese_relevance', 5),
                        'grade': str(row.get('grade', 'B')),
                        'data_source': source_name
                    }

                    # 名前が空でない場合のみ追加
                    if person['name'] and person['name'] != 'nan':
                        all_people.append(person)

                files_info.append({
                    'file': filename,
                    'source': source_name,
                    'count': len(df)
                })
                print(f"読み込み: {filename} - {len(df)}人")

            except Exception as e:
                print(f"エラー: {filename} - {e}")

    print(f"\n総読み込み数: {len(all_people)}人")

    # 重複削除（名前と生年で判定）
    seen = set()
    unique_people = []

    for person in all_people:
        # キー作成（名前 + 生年の最初4文字）
        birth_year = person['birth_date'][:4] if len(person['birth_date']) >= 4 else ''
        key = (person['name'], birth_year)

        if key not in seen:
            seen.add(key)

            # カテゴリ修正
            if not person['main_category'] or person['main_category'] in ['nan', '', 'None']:
                person['main_category'] = infer_category(person)

            unique_people.append(person)

    print(f"重複削除後: {len(unique_people)}人")

    return unique_people, files_info

def infer_category(person):
    """カテゴリ推定"""
    text = f"{person['occupation']} {person['description']}".lower()

    if any(word in text for word in ['俳優', '女優', '歌手', '芸人', 'タレント', 'アイドル', '声優', 'youtuber']):
        return 'エンターテインメント'
    elif any(word in text for word in ['選手', 'プレイヤー', 'アスリート', 'スポーツ', '野球', 'サッカー']):
        return 'スポーツ'
    elif any(word in text for word in ['起業家', '実業家', 'ceo', '社長', 'エンジニア', 'プログラマ']):
        return 'ビジネス・テクノロジー'
    elif any(word in text for word in ['政治家', '大臣', '知事', '市長', '議員']):
        return '政治・社会'
    elif any(word in text for word in ['歴史', '戦国', '江戸', '明治', '武将', '幕末']):
        return '歴史的教訓'
    else:
        return '文化・芸術'

def balance_categories(people, target_total=12410):
    """カテゴリバランス調整"""

    # 目標分布
    category_targets = {
        'エンターテインメント': 3475,
        '文化・芸術': 2854,
        'スポーツ': 2234,
        'ビジネス・テクノロジー': 1737,
        '政治・社会': 1117,
        '歴史的教訓': 993
    }

    # 現在の分布を確認
    df = pd.DataFrame(people)
    current_dist = df['main_category'].value_counts().to_dict()

    print("\n現在のカテゴリ分布:")
    for cat in category_targets.keys():
        count = current_dist.get(cat, 0)
        target = category_targets[cat]
        print(f"  {cat}: {count}人 (目標: {target}人)")

    # カテゴリ別にグループ化
    category_groups = {}
    for cat in category_targets.keys():
        category_groups[cat] = df[df['main_category'] == cat].to_dict('records')

    # バランス調整
    balanced_people = []

    for category, target_count in category_targets.items():
        group = category_groups.get(category, [])

        if len(group) >= target_count:
            # 超過している場合はランダムサンプリング
            # 日本人関連度とimpact_scoreでソート
            sorted_group = sorted(group,
                                key=lambda x: (x.get('japanese_relevance', 0),
                                             x.get('impact_score', 0)),
                                reverse=True)
            balanced_people.extend(sorted_group[:target_count])
        else:
            # 不足している場合は全て追加
            balanced_people.extend(group)

    print(f"\nバランス調整後: {len(balanced_people)}人")

    # 目標数に満たない場合は補完
    if len(balanced_people) < target_total:
        shortage = target_total - len(balanced_people)
        print(f"不足分 {shortage}人を補完")

        # 残りの人物から補完
        used_names = {p['name'] for p in balanced_people}
        remaining = [p for p in people if p['name'] not in used_names]

        # 日本人関連度でソート
        remaining_sorted = sorted(remaining,
                                key=lambda x: x.get('japanese_relevance', 0),
                                reverse=True)

        balanced_people.extend(remaining_sorted[:shortage])

    # 最終的に目標数に調整
    final_people = balanced_people[:target_total]

    # 最終分布確認
    final_df = pd.DataFrame(final_people)
    final_dist = final_df['main_category'].value_counts()

    print("\n最終カテゴリ分布:")
    for cat, count in final_dist.items():
        target = category_targets.get(cat, 0)
        percentage = (count / target * 100) if target > 0 else 0
        print(f"  {cat}: {count}人 (目標: {target}人, 達成率: {percentage:.1f}%)")

    return final_people

def save_final_database(people):
    """最終データベース保存"""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_file = f"final_12410_database_{timestamp}.csv"
    json_file = f"final_12410_firebase_{timestamp}.json"

    # CSV保存
    df = pd.DataFrame(people)
    df.to_csv(csv_file, index=False, encoding='utf-8-sig')

    # JSON保存（Firebase用）
    firebase_data = {}
    for i, person in enumerate(people):
        # Firebase用にIDを追加
        person_data = person.copy()
        person_data['id'] = f"person_{i+1:05d}"
        person_data['created_at'] = timestamp
        firebase_data[person_data['id']] = person_data

    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(firebase_data, f, ensure_ascii=False, indent=2)

    print("\n✅ 最終データベース保存完了:")
    print(f"  CSV: {csv_file}")
    print(f"  JSON: {json_file}")
    print(f"  総人数: {len(people)}人")

    # 品質統計
    avg_impact = np.mean([p.get('impact_score', 0) for p in people])
    avg_relevance = np.mean([p.get('japanese_relevance', 0) for p in people])

    print("\n品質指標:")
    print(f"  平均インパクトスコア: {avg_impact:.1f}/10")
    print(f"  平均日本人関連度: {avg_relevance:.1f}/10")

    # グレード分布
    grade_dist = pd.Series([p.get('grade', 'C') for p in people]).value_counts()
    print("\nグレード分布:")
    for grade, count in grade_dist.items():
        print(f"  {grade}級: {count}人 ({count/len(people)*100:.1f}%)")

    return csv_file, json_file

def main():
    print("="*60)
    print("最終データベース作成プロセス開始")
    print("="*60)

    # 1. 全データ統合
    print("\n[Step 1] データ統合...")
    all_people, files_info = integrate_all_data()

    # 2. カテゴリバランス調整
    print("\n[Step 2] カテゴリバランス調整...")
    balanced_people = balance_categories(all_people, 12410)

    # 3. 最終保存
    print("\n[Step 3] 最終データベース保存...")
    csv_file, json_file = save_final_database(balanced_people)

    print("\n" + "="*60)
    print("✨ 完了！12,410人のデータベースが作成されました")
    print("="*60)

    return csv_file, json_file

if __name__ == "__main__":
    main()
