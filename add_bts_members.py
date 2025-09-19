#!/usr/bin/env python3
"""
BTSグループエントリを削除し、メンバー7名を個別に追加
"""

import json
import shutil
from datetime import datetime

# BTSメンバー情報
BTS_MEMBERS = [
    {
        'id': 'person_13001',
        'person_name': 'RM',
        'person_name_ja': 'RM（アールエム）',
        'person_name_display': 'RM',
        'birth_date': '1994-09-12',
        'death_date': '',
        'nationality': '韓国',
        'occupation': '歌手、ラッパー、作詞家、音楽プロデューサー',
        'main_category': 'エンターテインメント',
        'subcategory': 'K-POP',
        'description': 'BTS（防弾少年団）のリーダー。本名：キム・ナムジュン（金南俊）',
        'grade': 'A',
        'impact_score': 95,
        'japanese_relevance': 90,
        'data_source': 'manual_entry',
        'created_at': datetime.now().strftime('%Y%m%d_%H%M%S')
    },
    {
        'id': 'person_13002',
        'person_name': 'Jin',
        'person_name_ja': 'ジン',
        'person_name_display': 'ジン',
        'birth_date': '1992-12-04',
        'death_date': '',
        'nationality': '韓国',
        'occupation': '歌手、俳優',
        'main_category': 'エンターテインメント',
        'subcategory': 'K-POP',
        'description': 'BTS（防弾少年団）の最年長メンバー。本名：キム・ソクジン（金碩珍）',
        'grade': 'A',
        'impact_score': 92,
        'japanese_relevance': 88,
        'data_source': 'manual_entry',
        'created_at': datetime.now().strftime('%Y%m%d_%H%M%S')
    },
    {
        'id': 'person_13003',
        'person_name': 'SUGA',
        'person_name_ja': 'シュガ',
        'person_name_display': 'シュガ',
        'birth_date': '1993-03-09',
        'death_date': '',
        'nationality': '韓国',
        'occupation': '歌手、ラッパー、作詞家、音楽プロデューサー',
        'main_category': 'エンターテインメント',
        'subcategory': 'K-POP',
        'description': 'BTS（防弾少年団）のメンバー。本名：ミン・ユンギ（閔玧其）。ソロ名義Agust D',
        'grade': 'A',
        'impact_score': 94,
        'japanese_relevance': 89,
        'data_source': 'manual_entry',
        'created_at': datetime.now().strftime('%Y%m%d_%H%M%S')
    },
    {
        'id': 'person_13004',
        'person_name': 'j-hope',
        'person_name_ja': 'ジェイホープ',
        'person_name_display': 'J-HOPE',
        'birth_date': '1994-02-18',
        'death_date': '',
        'nationality': '韓国',
        'occupation': '歌手、ラッパー、ダンサー、振付師',
        'main_category': 'エンターテインメント',
        'subcategory': 'K-POP',
        'description': 'BTS（防弾少年団）のメインダンサー。本名：チョン・ホソク（鄭號錫）',
        'grade': 'A',
        'impact_score': 93,
        'japanese_relevance': 88,
        'data_source': 'manual_entry',
        'created_at': datetime.now().strftime('%Y%m%d_%H%M%S')
    },
    {
        'id': 'person_13005',
        'person_name': 'Jimin',
        'person_name_ja': 'ジミン',
        'person_name_display': 'ジミン',
        'birth_date': '1995-10-13',
        'death_date': '',
        'nationality': '韓国',
        'occupation': '歌手、ダンサー',
        'main_category': 'エンターテインメント',
        'subcategory': 'K-POP',
        'description': 'BTS（防弾少年団）のリードボーカル、メインダンサー。本名：パク・ジミン（朴智旻）',
        'grade': 'A',
        'impact_score': 95,
        'japanese_relevance': 91,
        'data_source': 'manual_entry',
        'created_at': datetime.now().strftime('%Y%m%d_%H%M%S')
    },
    {
        'id': 'person_13006',
        'person_name': 'V',
        'person_name_ja': 'ヴィ',
        'person_name_display': 'V',
        'birth_date': '1995-12-30',
        'death_date': '',
        'nationality': '韓国',
        'occupation': '歌手、俳優',
        'main_category': 'エンターテインメント',
        'subcategory': 'K-POP',
        'description': 'BTS（防弾少年団）のサブボーカル。本名：キム・テヒョン（金泰亨）',
        'grade': 'A',
        'impact_score': 95,
        'japanese_relevance': 90,
        'data_source': 'manual_entry',
        'created_at': datetime.now().strftime('%Y%m%d_%H%M%S')
    },
    {
        'id': 'person_13007',
        'person_name': 'Jungkook',
        'person_name_ja': 'ジョングク',
        'person_name_display': 'ジョングク',
        'birth_date': '1997-09-01',
        'death_date': '',
        'nationality': '韓国',
        'occupation': '歌手、ダンサー',
        'main_category': 'エンターテインメント',
        'subcategory': 'K-POP',
        'description': 'BTS（防弾少年団）のメインボーカル、最年少メンバー。本名：チョン・ジョングク（田柾國）',
        'grade': 'A',
        'impact_score': 96,
        'japanese_relevance': 92,
        'data_source': 'manual_entry',
        'created_at': datetime.now().strftime('%Y%m%d_%H%M%S')
    }
]

def find_and_remove_bts_group(data):
    """BTSグループエントリを検索して削除"""
    bts_keys = []
    
    for key, person in data.items():
        # BTSグループエントリを検索
        name = person.get('person_name', '')
        name_ja = person.get('person_name_ja', '')
        
        if 'BTS' in name and '防弾少年団' in str(person.get('description', '')):
            bts_keys.append(key)
            print(f"  🔍 BTSグループエントリ発見: {key} - {name}")
        elif name == 'BTS' or name_ja == 'BTS（防弾少年団）':
            bts_keys.append(key)
            print(f"  🔍 BTSグループエントリ発見: {key} - {name}")
    
    # 削除
    for key in bts_keys:
        del data[key]
        print(f"  ❌ 削除: {key}")
    
    return len(bts_keys)

def add_bts_members(data):
    """BTSメンバーを個別に追加"""
    added_count = 0
    
    for member in BTS_MEMBERS:
        member_id = member['id']
        
        # 既存のIDと重複しないようチェック
        if member_id not in data:
            data[member_id] = member
            print(f"  ✅ 追加: {member_id} - {member['person_name']} ({member['person_name_ja']})")
            added_count += 1
        else:
            print(f"  ⚠️ ID重複のためスキップ: {member_id}")
    
    return added_count

def main():
    """メイン処理"""
    print("=" * 60)
    print("BTS グループ → メンバー個別追加処理")
    print("=" * 60)
    
    input_file = 'final_12410_firebase_20250822_201828.json'
    
    # バックアップ作成
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f'backup_before_bts_{timestamp}.json'
    shutil.copy2(input_file, backup_file)
    print(f"✅ バックアップ作成: {backup_file}")
    
    # JSON読み込み
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    initial_count = len(data)
    print(f"\n📊 初期データ数: {initial_count}件")
    
    # BTSグループエントリを削除
    print("\n🔍 BTSグループエントリを検索中...")
    removed_count = find_and_remove_bts_group(data)
    
    # BTSメンバーを追加
    print("\n➕ BTSメンバーを個別に追加中...")
    added_count = add_bts_members(data)
    
    # 結果を保存
    output_file = f'bts_updated_{timestamp}.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    # 元のファイルを更新
    shutil.copy2(output_file, input_file)
    
    final_count = len(data)
    
    print("\n" + "=" * 60)
    print("📊 処理結果:")
    print(f"  初期データ数: {initial_count}件")
    print(f"  削除件数: {removed_count}件")
    print(f"  追加件数: {added_count}件")
    print(f"  最終データ数: {final_count}件")
    print(f"\n✅ 出力ファイル: {output_file}")
    print(f"✅ 元のファイルを更新: {input_file}")
    
    # CSV出力も更新
    print("\n📊 CSV出力を更新中...")
    import csv
    csv_filename = f'bts_updated_{timestamp}.csv'
    
    headers = [
        'id', 'person_name', 'person_name_ja', 'person_name_display', 'grade',
        'birth_date', 'death_date', 'nationality', 'occupation',
        'main_category', 'subcategory', 'description'
    ]
    
    with open(csv_filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        
        # BTSメンバーのデータを最初に表示
        for member_id in [f'person_1300{i}' for i in range(1, 8)]:
            if member_id in data:
                person = data[member_id]
                row = {
                    'id': person.get('id', member_id),
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
    
    print(f"✅ CSV出力完了: {csv_filename}")
    
    return final_count

if __name__ == "__main__":
    main()