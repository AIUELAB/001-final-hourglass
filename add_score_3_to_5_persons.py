#!/usr/bin/env python3
"""
スコア3.0-4.9の人物を最新データベースに追加するスクリプト
"""

import csv
import os
from datetime import datetime
from glob import glob
from typing import Dict, List, Tuple

def collect_score_3_to_5_persons() -> Dict[str, Dict]:
    """
    複数のCSVファイルからスコア3.0-4.9の人物を収集
    """
    
    # 対象ファイル（削除済みファイルは除外）
    target_files = [
        'checkpoint_2000_20250910_024328.csv',
        'database_expanded_20250910_045159.csv',
        'recognition_results_ALL_20250908_224635.csv',
        'reprocessed_ALL_20250910_025225.csv',
        'checkpoint_3000_20250910_024701.csv'
    ]
    
    persons = {}
    
    for filename in target_files:
        filepath = f'/Users/admin/Documents/AIUELAB/001-final-hourglass/{filename}'
        if not os.path.exists(filepath):
            print(f"ファイルが見つかりません: {filename}")
            continue
            
        try:
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        # スコアの取得（複数のフィールド名に対応）
                        score = float(row.get('recognition_score', row.get('score', 0)))
                        
                        if 3.0 <= score < 5.0:
                            person_id = row.get('person_id', '')
                            name = row.get('name', row.get('person_name', ''))
                            
                            if not person_id:
                                # person_idがない場合は名前から生成
                                person_id = f"P3_{name.replace(' ', '_')}"
                            
                            # 既存のエントリより高いスコアの場合のみ更新
                            if person_id not in persons or persons[person_id].get('recognition_score', 0) < score:
                                persons[person_id] = {
                                    'person_id': person_id,
                                    'person_name': name,  # フィールド名を統一
                                    'recognition_score': score,
                                    'wikipedia_found': row.get('wikipedia_found', 'True'),
                                    'occupation': row.get('occupation', ''),
                                    'description': row.get('description', ''),
                                    'category': row.get('category', ''),
                                    'source_file': filename
                                }
                    except ValueError:
                        continue
        except Exception as e:
            print(f"エラー: {filename} - {e}")
            continue
    
    return persons

def enrich_person_info(person: Dict) -> Dict:
    """
    人物情報を補完
    """
    name = person.get('person_name', person.get('name', ''))  # 両方のフィールド名に対応
    score = person['recognition_score']
    
    # occupation と description が空の場合は推定
    if not person['occupation']:
        # 名前から職業を推定
        if 'ベーコン' in name:
            person['occupation'] = '哲学者・政治家'
            person['description'] = 'イギリスの哲学者、政治家、法律家'
        elif 'デュマ' in name:
            person['occupation'] = '作家'
            person['description'] = 'フランスの小説家、「三銃士」「モンテ・クリスト伯」の著者'
        elif 'ホランド' in name and 'トム' in name:
            person['occupation'] = '俳優'
            person['description'] = 'イギリスの俳優、スパイダーマン役で知られる'
        elif 'ネルソン' in name:
            person['occupation'] = '海軍提督'
            person['description'] = 'イギリス海軍の名提督、トラファルガー海戦の英雄'
        elif 'ロックフェラー' in name:
            person['occupation'] = '実業家'
            person['description'] = 'アメリカの実業家、石油王として知られる'
        elif 'ワトソン' in name:
            person['occupation'] = '実業家'
            person['description'] = 'IBM創業者または関連人物'
        elif 'コックス' in name:
            person['occupation'] = '物理学者・科学番組司会者'
            person['description'] = 'イギリスの物理学者、科学番組の司会者'
        else:
            # デフォルト値
            if score >= 4.5:
                person['occupation'] = '著名人'
                person['description'] = f'知名度スコア{score}の著名人'
            elif score >= 4.0:
                person['occupation'] = '公人'
                person['description'] = f'知名度スコア{score}の公人'
            else:
                person['occupation'] = '一般著名人'
                person['description'] = f'知名度スコア{score}の人物'
    
    # カテゴリの設定
    if not person['category']:
        occupation = person['occupation'].lower()
        if '俳優' in occupation or '女優' in occupation:
            person['category'] = 'エンターテインメント'
        elif '作家' in occupation or '小説' in occupation:
            person['category'] = '文学'
        elif '哲学' in occupation:
            person['category'] = '学術'
        elif '実業' in occupation or '経営' in occupation:
            person['category'] = 'ビジネス'
        elif '政治' in occupation:
            person['category'] = '政治'
        elif '科学' in occupation or '物理' in occupation:
            person['category'] = '科学'
        elif 'スポーツ' in occupation or '選手' in occupation:
            person['category'] = 'スポーツ'
        elif '音楽' in occupation or '歌手' in occupation:
            person['category'] = '音楽'
        else:
            person['category'] = 'その他'
    
    return person

def main():
    """メイン処理"""
    
    print("=" * 60)
    print("スコア3.0-4.9の人物をデータベースに追加")
    print("=" * 60)
    
    # 1. スコア3.0-4.9の人物を収集
    print("\n1. スコア3.0-4.9の人物データを収集中...")
    persons_3_to_5 = collect_score_3_to_5_persons()
    print(f"   収集された人物数: {len(persons_3_to_5)}人")
    
    # スコア範囲別の統計
    ranges = {
        '3.0-3.4': 0,
        '3.5-3.9': 0,
        '4.0-4.4': 0,
        '4.5-4.9': 0
    }
    
    for person in persons_3_to_5.values():
        score = person['recognition_score']
        if 3.0 <= score < 3.5:
            ranges['3.0-3.4'] += 1
        elif 3.5 <= score < 4.0:
            ranges['3.5-3.9'] += 1
        elif 4.0 <= score < 4.5:
            ranges['4.0-4.4'] += 1
        elif 4.5 <= score < 5.0:
            ranges['4.5-4.9'] += 1
    
    print("\n   スコア範囲別:")
    for range_name, count in ranges.items():
        print(f"     {range_name}: {count}人")
    
    # 2. 人物情報の補完
    print("\n2. 人物情報を補完中...")
    for person_id in persons_3_to_5:
        persons_3_to_5[person_id] = enrich_person_info(persons_3_to_5[person_id])
    
    # 3. 既存データベースの読み込み
    print("\n3. 既存データベースを読み込み中...")
    existing_db_path = '/Users/admin/Documents/AIUELAB/001-final-hourglass/database_fully_enriched_20250910_113805.csv'
    
    existing_persons = {}
    fieldnames = []
    
    with open(existing_db_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            person_id = row.get('person_id', '')
            if person_id:
                existing_persons[person_id] = row
    
    print(f"   既存の人物数: {len(existing_persons)}人")
    
    # 4. データの統合
    print("\n4. データを統合中...")
    
    # 新規追加される人物をカウント
    new_additions = 0
    updates = 0
    
    for person_id, person in persons_3_to_5.items():
        if person_id not in existing_persons:
            # 新規追加
            new_additions += 1
            # フィールドを合わせる
            new_person = {}
            for field in fieldnames:
                if field in person:
                    new_person[field] = person[field]
                elif field == 'person_name' and 'person_name' in person:
                    new_person[field] = person['person_name']
                else:
                    new_person[field] = ''
            # source_fileは削除（既存のフィールドにない）
            existing_persons[person_id] = new_person
        else:
            # 既存エントリのスコアより高い場合は更新を検討
            existing_score = float(existing_persons[person_id].get('recognition_score', 0))
            new_score = person['recognition_score']
            if new_score > existing_score:
                updates += 1
                # スコアと関連情報を更新
                existing_persons[person_id]['recognition_score'] = new_score
                if person['occupation']:
                    existing_persons[person_id]['occupation'] = person['occupation']
                if person['description']:
                    existing_persons[person_id]['description'] = person['description']
    
    print(f"   新規追加: {new_additions}人")
    print(f"   スコア更新: {updates}人")
    print(f"   統合後の総人数: {len(existing_persons)}人")
    
    # 5. 新しいデータベースファイルの作成
    print("\n5. 新しいデータベースファイルを作成中...")
    
    output_file = f'database_with_score_3_to_5_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    
    # スコア順にソート
    sorted_persons = sorted(existing_persons.values(), 
                           key=lambda x: float(x.get('recognition_score', 0)), 
                           reverse=True)
    
    # CSVファイルに書き込み（UTF-8 BOM付き）
    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sorted_persons)
    
    print(f"   ファイル作成完了: {output_file}")
    
    # 6. 統計情報の表示
    print("\n6. 最終統計:")
    
    # スコア分布を再計算
    final_ranges = {}
    for i in range(3, 11):
        final_ranges[f'{i}-{i+1}'] = 0
    
    for person in sorted_persons:
        score = float(person.get('recognition_score', 0))
        for i in range(3, 11):
            if i <= score < i + 1:
                final_ranges[f'{i}-{i+1}'] += 1
                break
    
    print("\n   スコア分布:")
    for range_name, count in final_ranges.items():
        if count > 0:
            percentage = (count / len(sorted_persons)) * 100
            print(f"     {range_name}: {count}人 ({percentage:.1f}%)")
    
    # 追加された人物のサンプル表示
    print("\n   追加された主な人物（スコア4.5以上）:")
    sample_count = 0
    for person in sorted_persons:
        score = float(person.get('recognition_score', 0))
        if 4.5 <= score < 5.0:  # スコア4.5-4.9の人物
            person_name = person.get('person_name', person.get('name', 'Unknown'))
            occupation = person.get('occupation', '')
            print(f"     - {person_name}: {score} ({occupation})")
            sample_count += 1
            if sample_count >= 10:
                break
    
    print("\n" + "=" * 60)
    print("処理完了！")
    print("=" * 60)

if __name__ == '__main__':
    main()