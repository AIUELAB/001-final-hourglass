#!/usr/bin/env python3
"""
高度な名前変換システム
person_name → person_name_ja（日本語訳）
person_name_ja → person_name_display（表示用短縮名）
"""

import json
import re
import shutil
from datetime import datetime

# 主要な西洋名の日本語訳辞書
NAME_TRANSLATIONS = {
    # 王族・貴族
    'Louis XIV of France': 'ルイ14世',
    'Louis XVI of France': 'ルイ16世',
    'Elizabeth I': 'エリザベス1世',
    'Elizabeth II': 'エリザベス2世',

    # エンターテイナー
    'Charlie Chaplin': 'チャーリー・チャップリン',
    'Chaplin': 'チャップリン',
    'Marilyn Monroe': 'マリリン・モンロー',
    'Monroe': 'モンロー',
    'Elvis Presley': 'エルヴィス・プレスリー',
    'Presley': 'プレスリー',
    'Michael Jackson': 'マイケル・ジャクソン',
    'Jackson': 'ジャクソン',
    'John Lennon': 'ジョン・レノン',
    'Lennon': 'レノン',
    'Bob Dylan': 'ボブ・ディラン',
    'Dylan': 'ディラン',

    # スポーツ選手
    'Pelé': 'ペレ',
    'Diego Maradona': 'ディエゴ・マラドーナ',
    'Cristiano Ronaldo': 'クリスティアーノ・ロナウド',
    'Lionel Messi': 'リオネル・メッシ',

    # 古代ローマ
    'Gaius Norbanus Sorex': 'ガイウス・ノルバヌス・ソレクス',
    'Julius Caesar': 'ユリウス・カエサル',
    'Marcus Aurelius': 'マルクス・アウレリウス',

    # ギリシャ
    'Aristion': 'アリスティオン',
    'Plato': 'プラトン',
    'Aristotle': 'アリストテレス',

    # その他の歴史人物
    'Napoleon Bonaparte': 'ナポレオン・ボナパルト',
    'George Washington': 'ジョージ・ワシントン',
    'Abraham Lincoln': 'エイブラハム・リンカーン',

    # 中国系
    'Chuzi II': '楚子二世',

    # その他
    'Tigellius': 'ティゲリウス',
}

# 表示用短縮名の辞書
DISPLAY_NAME_MAP = {
    # 日本語名から短縮形
    'ルイ14世': 'ルイ14世',
    'ルイ16世': 'ルイ16世',
    'エリザベス1世': 'エリザベス1世',
    'エリザベス2世': 'エリザベス2世',
    'チャーリー・チャップリン': 'チャップリン',
    'マリリン・モンロー': 'モンロー',
    'エルヴィス・プレスリー': 'プレスリー',
    'マイケル・ジャクソン': 'ジャクソン',
    'ジョン・レノン': 'レノン',
    'ボブ・ディラン': 'ディラン',
    'ディエゴ・マラドーナ': 'マラドーナ',
    'クリスティアーノ・ロナウド': 'ロナウド',
    'リオネル・メッシ': 'メッシ',
    'ガイウス・ノルバヌス・ソレクス': 'ソレクス',
    'ユリウス・カエサル': 'カエサル',
    'マルクス・アウレリウス': 'アウレリウス',
    'ナポレオン・ボナパルト': 'ナポレオン',
    'ジョージ・ワシントン': 'ワシントン',
    'エイブラハム・リンカーン': 'リンカーン',

    # 日本の歴史人物
    '織田信長': '信長',
    '豊臣秀吉': '秀吉',
    '徳川家康': '家康',
    '坂本龍馬': '龍馬',
    '西郷隆盛': '西郷',
}

# 特殊な表示名ルール
SPECIAL_DISPLAY_RULES = {
    'Louis XIV of France': 'France',  # スクリーンショットに見られる特殊ケース
    'ルロア・クララ': 'クララ',  # カタカナ名の最後の部分
}

def is_japanese(text):
    """日本語が含まれるかチェック"""
    return bool(re.search(r'[ぁ-ん]|[ァ-ヴ]|[一-龯]', text))

def is_western(text):
    """西洋名かチェック（英語のみ）"""
    return bool(re.search(r'^[A-Za-z\s\-\.\'\,]+$', text))

def is_comedy_duo(name):
    """お笑いコンビ形式かチェック"""
    comedy_duos = ['中川家', 'サンドウィッチマン', 'フットボールアワー',
                   'ますだおかだ', '千鳥', 'ダウンタウン', 'ナインティナイン']
    return any(duo in name for duo in comedy_duos) and '・' in name

def translate_to_japanese(name):
    """英語名を日本語に翻訳"""
    # 完全一致
    if name in NAME_TRANSLATIONS:
        return NAME_TRANSLATIONS[name]

    # 部分一致（姓のみなど）
    for eng, jpn in NAME_TRANSLATIONS.items():
        if name in eng:
            # 姓のみの場合
            if ' ' in eng and name == eng.split()[-1]:
                return jpn.split('・')[-1] if '・' in jpn else jpn

    # 翻訳がない場合はそのまま返す
    return name

def get_display_name(name_ja, original_name=None):
    """表示用短縮名を取得"""
    # 特殊ルールのチェック
    if original_name and original_name in SPECIAL_DISPLAY_RULES:
        return SPECIAL_DISPLAY_RULES[original_name]

    # 完全一致の短縮名
    if name_ja in DISPLAY_NAME_MAP:
        return DISPLAY_NAME_MAP[name_ja]

    # お笑いコンビ形式はそのまま
    if is_comedy_duo(name_ja):
        return name_ja

    # カタカナの長い名前は最後の部分
    if '・' in name_ja and not is_comedy_duo(name_ja):
        parts = name_ja.split('・')
        # カタカナ名の場合は最後の部分（姓）
        if all(re.match(r'^[ァ-ヴー]+$', part) for part in parts):
            return parts[-1]

    # 日本人の名前で短い場合はそのまま
    if is_japanese(name_ja) and len(name_ja) <= 4:
        return name_ja

    # その他はそのまま
    return name_ja

def process_person_data(person_data):
    """
    1人分のデータを処理
    """
    # IDを保持
    person_id = person_data.get('id', '')

    # person_nameが存在しない場合は何もしない
    if 'person_name' not in person_data:
        return person_data

    original_name = person_data['person_name']

    # person_name_ja の設定
    if is_japanese(original_name):
        # すでに日本語の場合
        person_name_ja = original_name

        # TAIGAのような日本のエンターテイナーでローマ字の場合
        if person_data.get('nationality') in ['日本', 'Japan', '日本国']:
            if is_western(original_name) and ' ' not in original_name:
                # 単語のローマ字名（TAIGA, IKKO等）はそのまま
                person_name_ja = original_name
    else:
        # 西洋名の場合は翻訳
        person_name_ja = translate_to_japanese(original_name)

    # person_name_display の設定
    person_name_display = get_display_name(person_name_ja, original_name)

    # データ更新
    person_data['person_name_ja'] = person_name_ja
    person_data['person_name_display'] = person_name_display

    return person_data

def main():
    """メイン処理"""
    print("=" * 60)
    print("高度な名前変換処理")
    print("=" * 60)

    input_file = 'final_12410_firebase_20250822_201828.json'

    # バックアップ作成
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f'backup_before_advanced_convert_{timestamp}.json'
    shutil.copy2(input_file, backup_file)
    print(f"✅ バックアップ作成: {backup_file}")

    # JSON読み込み
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 変換処理
    convert_count = 0
    convert_log = []

    for key, person in data.items():
        original_person = person.copy()
        converted_person = process_person_data(person)

        # 変更があったかチェック
        if (original_person.get('person_name_ja') != converted_person.get('person_name_ja') or
            original_person.get('person_name_display') != converted_person.get('person_name_display')):

            convert_log.append({
                'id': key,
                'person_name': converted_person.get('person_name'),
                'person_name_ja_before': original_person.get('person_name_ja'),
                'person_name_ja_after': converted_person.get('person_name_ja'),
                'person_name_display_before': original_person.get('person_name_display'),
                'person_name_display_after': converted_person.get('person_name_display')
            })

            data[key] = converted_person
            convert_count += 1

    # 結果を保存
    output_file = f'advanced_converted_{timestamp}.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # ログ保存
    log_file = f'advanced_convert_log_{timestamp}.json'
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump({
            'convert_count': convert_count,
            'timestamp': timestamp,
            'samples': convert_log[:100]  # 最初の100件をサンプルとして保存
        }, f, ensure_ascii=False, indent=2)

    # 元のファイルを更新
    shutil.copy2(output_file, input_file)

    print(f"✅ 変換件数: {convert_count}件")
    print(f"✅ 出力ファイル: {output_file}")
    print(f"✅ ログファイル: {log_file}")
    print(f"✅ 元のファイルを更新: {input_file}")

    # サンプル表示
    print("\n📝 変換例（最初の20件）:")
    for i, log in enumerate(convert_log[:20], 1):
        print(f"\n{i}. ID: {log['id']}")
        print(f"   person_name: {log['person_name']}")
        print(f"   person_name_ja: {log['person_name_ja_before']} → {log['person_name_ja_after']}")
        print(f"   person_name_display: {log['person_name_display_before']} → {log['person_name_display_after']}")

    # CSV出力も更新
    print("\n📊 CSV出力を更新中...")
    import csv
    csv_filename = f'final_converted_{timestamp}.csv'

    headers = [
        'id', 'person_name', 'person_name_ja', 'person_name_display',
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

    return convert_count

if __name__ == "__main__":
    main()
