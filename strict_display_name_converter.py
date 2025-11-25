#!/usr/bin/env python3
"""
person_name_display 短縮名ルール厳格化
「見た人が絶対にこの人だ！と特定できる」歴史的に唯一無二の人物のみ短縮名を使用
"""

import csv
import json
import shutil
from datetime import datetime

# 歴史的に唯一無二で短縮可能な人物
UNIQUE_SHORTNAME_ALLOWED = {
    # 音楽史の巨匠
    'ヴォルフガング・アマデウス・モーツァルト': 'モーツァルト',
    'ルートヴィヒ・ヴァン・ベートーヴェン': 'ベートーヴェン',
    'ヨハン・セバスチャン・バッハ': 'バッハ',

    # 美術史の巨匠
    'パブロ・ピカソ': 'ピカソ',
    'レオナルド・ダ・ヴィンチ': 'ダ・ヴィンチ',
    'フィンセント・ファン・ゴッホ': 'ゴッホ',
    'ミケランジェロ・ブオナローティ': 'ミケランジェロ',

    # 科学史の巨匠
    'アルベルト・アインシュタイン': 'アインシュタイン',
    'アイザック・ニュートン': 'ニュートン',
    'ガリレオ・ガリレイ': 'ガリレオ',
    'チャールズ・ダーウィン': 'ダーウィン',

    # 歴史上の偉人
    'ユリウス・カエサル': 'カエサル',
    'ナポレオン・ボナパルト': 'ナポレオン',
    'アレクサンドロス大王': 'アレクサンドロス',

    # スポーツ界の伝説
    'ペレ': 'ペレ',  # サッカーの王様

    # 日本の歴史人物（姓のみで特定可能）
    '織田信長': '信長',
    '豊臣秀吉': '秀吉',
    '徳川家康': '家康',
    '坂本龍馬': '龍馬',
    '西郷隆盛': '西郷',
}

# フルネームに変更すべき人物
FULLNAME_REQUIRED = {
    # エンターテインメント
    'チャップリン': 'チャーリー・チャップリン',
    'モンロー': 'マリリン・モンロー',
    'プレスリー': 'エルビス・プレスリー',
    'ジャクソン': 'マイケル・ジャクソン',  # Andrew Jacksonと区別
    'レノン': 'ジョン・レノン',
    'ディラン': 'ボブ・ディラン',

    # その他のジャクソン対応
    'Jackson': 'マイケル・ジャクソン',  # person_00024, person_00030のケース
}

# 特殊ケース（芸名・ブランド名など）
SPECIAL_CASES = {
    'MrBeast（ジミー・ドナルドソン）': 'MrBeast',
    'MrBeast': 'MrBeast',
    'TAIGA': 'TAIGA',  # 日本のお笑い芸人
    'IKKO': 'IKKO',
    'ルロア・クララ': 'ルロア・クララ',
    'アルベルト・フジモリ': 'アルベルト・フジモリ',
    'カズオ・イシグロ': 'カズオ・イシグロ',
}

# 重複エントリの統合ルール（最初のIDを維持）
DUPLICATE_MAPPING = {
    # Chaplin
    'person_00027': 'person_00021',  # 重複を統合
    'person_07892': 'person_00021',

    # Monroe
    'person_00028': 'person_00022',
    'person_07939': None,  # James Monroe（別人）

    # Presley
    'person_00029': 'person_00023',
    'person_05596': 'person_00023',
    'person_10815': 'person_00023',

    # Jackson
    'person_00030': 'person_00024',  # Michael Jackson
    'person_05601': 'person_00024',
    'person_10820': 'person_00024',
    # Andrew JacksonやJackson Sundownは別人なので統合しない

    # Lennon
    'person_00031': 'person_00025',
    'person_07905': 'person_00025',

    # Dylan
    'person_00032': 'person_00026',
}

def should_use_shortname(name_ja):
    """短縮名を使用すべきか判定"""
    return name_ja in UNIQUE_SHORTNAME_ALLOWED

def get_strict_display_name(person_data):
    """厳格なルールに基づいて表示名を決定"""
    person_name = person_data.get('person_name', '')
    person_name_ja = person_data.get('person_name_ja', '')
    current_display = person_data.get('person_name_display', '')

    # 特殊ケースをチェック
    if person_name in SPECIAL_CASES:
        return SPECIAL_CASES[person_name]
    if person_name_ja in SPECIAL_CASES:
        return SPECIAL_CASES[person_name_ja]
    if current_display in SPECIAL_CASES:
        return SPECIAL_CASES[current_display]

    # フルネーム変更が必要な人物
    if current_display in FULLNAME_REQUIRED:
        return FULLNAME_REQUIRED[current_display]
    if person_name in FULLNAME_REQUIRED:
        return FULLNAME_REQUIRED[person_name]

    # 歴史的に唯一無二の人物は短縮可
    if person_name_ja in UNIQUE_SHORTNAME_ALLOWED:
        return UNIQUE_SHORTNAME_ALLOWED[person_name_ja]

    # Andrew Jacksonなど他のJacksonは区別
    if 'Andrew Jackson' in person_name:
        return 'アンドリュー・ジャクソン'
    if 'Jackson Sundown' in person_name:
        return 'ジャクソン・サンダウン'
    if 'James Monroe' in person_name:
        return 'ジェームズ・モンロー'

    # お笑いコンビ形式は維持
    if '・' in person_name_ja and any(x in person_name_ja for x in ['中川家', 'サンドウィッチマン', 'フットボールアワー']):
        return person_name_ja

    # その他はフルネームまたは現状維持
    # ただし単なる姓だけの場合は日本語名を使用
    if len(current_display) <= 5 and current_display in ['ジャクソン', 'レノン', 'ディラン', 'チャップリン', 'モンロー', 'プレスリー']:
        # これらは必ずフルネームに
        if current_display in FULLNAME_REQUIRED:
            return FULLNAME_REQUIRED[current_display]

    # 日本語名が適切な長さならそのまま使用
    if person_name_ja and 2 <= len(person_name_ja) <= 10:
        return person_name_ja

    return current_display

def process_data(data):
    """データ処理メイン"""
    # 重複エントリを削除
    keys_to_delete = []
    for duplicate_key, main_key in DUPLICATE_MAPPING.items():
        if duplicate_key in data:
            if main_key:  # 統合先がある場合
                # より詳細な情報があれば統合
                if main_key in data:
                    main_data = data[main_key]
                    dup_data = data[duplicate_key]
                    # 欠損フィールドを補完
                    for field in ['birth_date', 'death_date', 'wikidata_id', 'description']:
                        if not main_data.get(field) and dup_data.get(field):
                            main_data[field] = dup_data[field]
            keys_to_delete.append(duplicate_key)

    # 重複削除
    for key in keys_to_delete:
        if key in data:
            del data[key]
            print(f"  ❌ 重複削除: {key}")

    # 表示名の更新
    update_count = 0
    update_log = []

    for key, person in data.items():
        old_display = person.get('person_name_display', '')
        new_display = get_strict_display_name(person)

        if old_display != new_display:
            update_log.append({
                'id': key,
                'person_name': person.get('person_name', ''),
                'person_name_ja': person.get('person_name_ja', ''),
                'old_display': old_display,
                'new_display': new_display
            })
            person['person_name_display'] = new_display
            update_count += 1

    return update_count, update_log, len(keys_to_delete)

def main():
    """メイン処理"""
    print("=" * 60)
    print("person_name_display 短縮名ルール厳格化")
    print("=" * 60)

    input_file = 'final_12410_firebase_20250822_201828.json'

    # バックアップ作成
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f'backup_strict_display_{timestamp}.json'
    shutil.copy2(input_file, backup_file)
    print(f"✅ バックアップ作成: {backup_file}")

    # JSON読み込み
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    initial_count = len(data)
    print(f"\n📊 初期データ数: {initial_count}件")

    # データ処理
    update_count, update_log, deleted_count = process_data(data)

    # 結果を保存
    output_file = f'strict_display_{timestamp}.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # ログ保存
    log_file = f'strict_display_log_{timestamp}.json'
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump({
            'update_count': update_count,
            'deleted_count': deleted_count,
            'timestamp': timestamp,
            'samples': update_log[:50]
        }, f, ensure_ascii=False, indent=2)

    # 元のファイルを更新
    shutil.copy2(output_file, input_file)

    final_count = len(data)

    print("\n📊 処理結果:")
    print(f"  表示名更新: {update_count}件")
    print(f"  重複削除: {deleted_count}件")
    print(f"  最終データ数: {final_count}件")

    # 更新例を表示
    print("\n📝 主な変更例:")
    important_changes = [
        log for log in update_log
        if log['old_display'] in ['チャップリン', 'モンロー', 'プレスリー', 'ジャクソン', 'レノン', 'ディラン']
    ]
    for i, change in enumerate(important_changes[:10], 1):
        print(f"{i}. {change['id']}: {change['old_display']} → {change['new_display']}")

    # CSV出力
    print("\n📊 CSV出力中...")
    csv_filename = f'strict_display_{timestamp}.csv'

    headers = [
        'id', 'person_name', 'person_name_ja', 'person_name_display', 'grade',
        'birth_date', 'death_date', 'nationality', 'occupation',
        'main_category', 'subcategory', 'description'
    ]

    with open(csv_filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()

        for key, person in data.items():
            row = {
                'id': person.get('id', key),
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
