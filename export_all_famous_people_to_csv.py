#!/usr/bin/env python3
"""
約7,200人の有名人データを統合してCSVファイルにエクスポート
"""

import csv
import json
import sys
from datetime import datetime

# パスを追加
sys.path.append('/Users/admin/Documents/AIUELAB/00-final-hourglass')

def load_improved_famous_people():
    """improved_famous_people_20250809_061626.json (6,201人) を読み込み"""
    with open('/Users/admin/Documents/AIUELAB/00-final-hourglass/improved_famous_people_20250809_061626.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    people = []
    for person in data['people']:
        # 生年・没年を整形
        birth_year = ""
        death_year = ""
        if person.get('birth_date'):
            birth_year = person['birth_date'][:4] if len(person['birth_date']) >= 4 else ""
        if person.get('death_date'):
            death_year = person['death_date'][:4] if len(person['death_date']) >= 4 else ""

        people.append({
            'id': person.get('id', ''),
            'name': person.get('name', ''),
            'name_ja': person.get('name_ja', ''),
            'birth_year': birth_year,
            'death_year': death_year,
            'death_age': person.get('death_age', ''),
            'nationality': person.get('nationality', ''),
            'occupation': person.get('occupation', ''),
            'category': '',  # このデータセットにはカテゴリなし
            'source': person.get('source', 'wikidata'),
            'wikidata_id': person.get('wikidata_id', ''),
            'description': person.get('description', '')
        })

    return people

def load_batch_famous_people():
    """famous_people_batch_20250809_061339.json (1,000人) を読み込み"""
    with open('/Users/admin/Documents/AIUELAB/00-final-hourglass/famous_people_batch_20250809_061339.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    people = []
    for item in data:
        # データが辞書か文字列かチェック
        if isinstance(item, dict):
            person = item
        else:
            # 文字列の場合は名前として扱う
            person = {'name': str(item)}

        # IDがない場合は名前からハッシュ生成
        import hashlib
        person_id = person.get('id', '')
        if not person_id:
            person_id = hashlib.md5(person.get('name', '').encode()).hexdigest()

        people.append({
            'id': person_id,
            'name': person.get('name', ''),
            'name_ja': person.get('name_ja', ''),
            'birth_year': '',
            'death_year': '',
            'death_age': '',
            'nationality': person.get('nationality', ''),
            'occupation': person.get('occupation', ''),
            'category': person.get('category', ''),
            'source': person.get('source', 'wikipedia'),
            'wikidata_id': '',
            'description': ''
        })

    return people

def load_database_famous_people():
    """famous_persons_database.py (140人) を読み込み"""
    from famous_persons_database import FAMOUS_PERSONS

    people = []
    for category, persons in FAMOUS_PERSONS.items():
        for person in persons:
            # IDを生成
            import hashlib
            person_id = hashlib.md5(person['name'].encode()).hexdigest()

            people.append({
                'id': person_id,
                'name': person['name'],
                'name_ja': person['name_ja'],
                'birth_year': str(person['birth']) if person['birth'] else '',
                'death_year': str(person['death']) if person['death'] else '',
                'death_age': str(person['death'] - person['birth']) if person['birth'] and person['death'] else '',
                'nationality': person['nationality'],
                'occupation': person['occupation'],
                'category': category,
                'source': 'manual_database',
                'wikidata_id': '',
                'description': ''
            })

    return people

def main():
    """メイン処理"""
    print("📚 有名人データを読み込み中...")

    # 各データソースから読み込み
    people1 = load_improved_famous_people()
    print(f"✅ improved_famous_people: {len(people1)}人")

    people2 = load_batch_famous_people()
    print(f"✅ batch_famous_people: {len(people2)}人")

    people3 = load_database_famous_people()
    print(f"✅ database_famous_people: {len(people3)}人")

    # 全データを統合
    all_people = people1 + people2 + people3
    print(f"\n📊 合計: {len(all_people)}人")

    # 重複チェック（名前ベース）
    unique_names = set()
    unique_people = []
    duplicates = 0

    for person in all_people:
        if person['name'] not in unique_names:
            unique_names.add(person['name'])
            unique_people.append(person)
        else:
            duplicates += 1

    print(f"⚠️  重複: {duplicates}人")
    print(f"✅ ユニーク: {len(unique_people)}人")

    # CSVファイルに出力
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = f'all_famous_people_{timestamp}.csv'

    with open(csv_filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
        fieldnames = ['id', 'name', 'name_ja', 'birth_year', 'death_year', 'death_age',
                      'nationality', 'occupation', 'category', 'source', 'wikidata_id', 'description']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        writer.writerows(unique_people)

    print(f"\n✅ CSVファイル作成完了: {csv_filename}")

    # 統計情報を表示
    print("\n📈 統計情報:")

    # ソース別
    sources = {}
    for person in unique_people:
        source = person['source']
        sources[source] = sources.get(source, 0) + 1

    print("\nソース別:")
    for source, count in sorted(sources.items(), key=lambda x: x[1], reverse=True):
        print(f"  {source}: {count}人")

    # 職業別（上位10）
    occupations = {}
    for person in unique_people:
        if person['occupation']:
            occupations[person['occupation']] = occupations.get(person['occupation'], 0) + 1

    print("\n職業別（上位10）:")
    for occ, count in sorted(occupations.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {occ}: {count}人")

    # カテゴリ別
    categories = {}
    for person in unique_people:
        if person['category']:
            categories[person['category']] = categories.get(person['category'], 0) + 1

    if categories:
        print("\nカテゴリ別:")
        for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            print(f"  {cat}: {count}人")

    return csv_filename

if __name__ == "__main__":
    csv_file = main()
    print(f"\n🎉 処理完了！ CSVファイル: {csv_file}")
