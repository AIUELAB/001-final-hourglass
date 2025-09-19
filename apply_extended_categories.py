#!/usr/bin/env python3
"""
拡張カテゴリを適用して有名人データを分類
犯罪者・歴史的教訓、日本サブカル、架空人物を含む
"""

import csv
import json
from datetime import datetime

from comprehensive_categories_extended import EXTENDED_CATEGORIES


def categorize_with_extended_categories(person):
    """拡張カテゴリシステムで人物を分類"""
    
    name = person.get('name', '').lower()
    name_ja = person.get('name_ja', '').lower()
    occupation = person.get('occupation', '').lower()
    nationality = person.get('nationality', '').lower()
    description = person.get('description', '').lower()
    
    # 全てのテキストを結合して検索用
    full_text = f"{name} {name_ja} {occupation} {nationality} {description}"
    
    # 結果を格納
    main_category = None
    subcategory = None
    special_tags = []
    
    # ========== 歴史的教訓カテゴリのチェック ==========
    for cat_name, cat_info in EXTENDED_CATEGORIES['historical_lessons']['categories'].items():
        keywords = cat_info.get('keywords', [])
        for keyword in keywords:
            if keyword.lower() in full_text:
                main_category = '歴史的教訓'
                subcategory = cat_name
                special_tags.append('負の歴史')
                break
        
        # 具体的な人名でチェック
        examples = cat_info.get('examples', '')
        if examples:
            example_names = [e.strip() for e in examples.split('、')]
            for example_name in example_names:
                if example_name.lower() in full_text or example_name in name_ja:
                    main_category = '歴史的教訓'
                    subcategory = cat_name
                    special_tags.append('負の歴史')
                    break
    
    # ========== 日本のサブカルチャーのチェック ==========
    if not main_category:
        for cat_name, cat_info in EXTENDED_CATEGORIES['japanese_subculture']['categories'].items():
            keywords = cat_info.get('keywords', [])
            for keyword in keywords:
                if keyword.lower() in full_text:
                    main_category = '日本サブカルチャー'
                    subcategory = cat_name
                    
                    # 細分類もチェック
                    if 'subcategories' in cat_info:
                        for subcat_name, subcat_list in cat_info['subcategories'].items():
                            for person_name in subcat_list:
                                if person_name.lower() in full_text or person_name in name_ja:
                                    special_tags.append(subcat_name)
                                    break
                    break
    
    # ========== テクノロジー・起業家のチェック ==========
    if not main_category:
        tech_keywords = [
            'tech', 'technology', 'software', 'hardware', 'computer', 'internet',
            'startup', 'founder', 'ceo', 'entrepreneur', 'business',
            'テクノロジー', '起業家', 'IT', 'ソフトウェア', 'プログラマー'
        ]
        
        unicorn_founders = [
            'zuckerberg', 'bezos', 'musk', 'gates', 'jobs', 'wozniak',
            'page', 'brin', 'dorsey', 'systrom', 'spiegel', 'chesky',
            '孫正義', '三木谷', '堀江貴文', '前澤友作', '山田進太郎'
        ]
        
        for keyword in tech_keywords:
            if keyword in full_text:
                main_category = 'テクノロジー・起業家'
                
                # ユニコーン創業者チェック
                for founder in unicorn_founders:
                    if founder in full_text:
                        subcategory = 'ユニコーン創業者'
                        special_tags.append('革新者')
                        break
                
                if not subcategory:
                    if 'ai' in full_text or 'artificial intelligence' in full_text:
                        subcategory = 'AI研究者'
                    elif 'program' in full_text or 'developer' in full_text:
                        subcategory = 'プログラマー'
                    elif 'venture' in full_text:
                        subcategory = 'ベンチャーキャピタリスト'
                    else:
                        subcategory = 'テック起業家'
                break
    
    # ========== 日本の偉人チェック ==========
    if not main_category and ('japan' in nationality or '日本' in nationality):
        japanese_categories = {
            '戦国武将': ['織田信長', '豊臣秀吉', '徳川家康', '武田信玄', '上杉謙信'],
            '幕末・明治維新': ['坂本龍馬', '西郷隆盛', '勝海舟', '伊藤博文', '福沢諭吉'],
            '文豪': ['夏目漱石', '芥川龍之介', '太宰治', '三島由紀夫', '川端康成'],
            '映画監督': ['黒澤明', '小津安二郎', '北野武', '是枝裕和', '新海誠'],
            '漫画家': ['手塚治虫', '鳥山明', '尾田栄一郎', '宮崎駿', '富野由悠季'],
            '音楽家': ['坂本龍一', '久石譲', 'YMO', 'X JAPAN', 'B\'z'],
        }
        
        for cat_name, names in japanese_categories.items():
            for person_name in names:
                if person_name in name_ja or person_name.lower() in full_text:
                    main_category = '日本の偉人'
                    subcategory = cat_name
                    special_tags.append('日本文化')
                    break
    
    # ========== 基本カテゴリのチェック ==========
    if not main_category:
        basic_categories = {
            '科学者・研究者': ['scientist', 'researcher', 'physicist', 'chemist', 'biologist', 'mathematician', '科学者', '研究者'],
            '芸術家': ['artist', 'painter', 'sculptor', 'designer', '芸術家', '画家', '彫刻家'],
            '音楽家': ['musician', 'composer', 'singer', 'pianist', '音楽家', '作曲家', '歌手'],
            '文学者': ['writer', 'author', 'poet', 'novelist', '作家', '小説家', '詩人'],
            '政治家': ['politician', 'president', 'minister', 'senator', '政治家', '大統領', '首相'],
            '実業家': ['business', 'executive', 'industrialist', '実業家', '経営者'],
            'スポーツ選手': ['athlete', 'player', 'sport', 'olympic', 'スポーツ', '選手'],
            '俳優・芸能人': ['actor', 'actress', 'celebrity', '俳優', '女優', 'タレント'],
            '活動家': ['activist', 'movement', 'rights', '活動家', '運動家'],
        }
        
        for cat_name, keywords in basic_categories.items():
            for keyword in keywords:
                if keyword in full_text:
                    main_category = cat_name
                    break
            if main_category:
                break
    
    # デフォルトカテゴリ
    if not main_category:
        main_category = 'その他'
        subcategory = '未分類'
    
    # 時代タグを追加
    birth_year = person.get('birth_year', '')
    if birth_year:
        try:
            year = int(birth_year)
            if year < 0:
                special_tags.append('紀元前')
            elif year < 500:
                special_tags.append('古代')
            elif year < 1500:
                special_tags.append('中世')
            elif year < 1800:
                special_tags.append('近世')
            elif year < 1900:
                special_tags.append('近代')
            elif year < 1950:
                special_tags.append('戦前・戦中')
            elif year < 2000:
                special_tags.append('20世紀')
            else:
                special_tags.append('21世紀')
        except:
            pass
    
    return {
        'main_category': main_category,
        'subcategory': subcategory or '',
        'special_tags': ', '.join(special_tags) if special_tags else ''
    }

def add_fictional_characters():
    """架空の人物を追加"""
    fictional_people = []
    
    if 'fictional_characters' not in EXTENDED_CATEGORIES:
        return fictional_people
    
    for category_name, cat_info in EXTENDED_CATEGORIES['fictional_characters']['categories'].items():
        if 'characters' not in cat_info:
            continue
        for char_name, char_info in cat_info['characters'].items():
            age_events = char_info.get('age_events', [])
            events_dict = {}
            for age, event in age_events:
                events_dict[str(age)] = event
            
            fictional_person = {
                'id': f"fictional_{char_name.replace(' ', '_').replace('・', '_').lower()}",
                'name': char_name,
                'name_ja': char_name,
                'birth_year': '',
                'death_year': '',
                'death_age': '',
                'nationality': '架空',
                'occupation': category_name,
                'main_category': '架空の人物',
                'subcategory': category_name,
                'special_tags': '架空キャラクター',
                'source': category_name,
                'description': f"{category_name}の登場人物",
                'key_ages': json.dumps(events_dict, ensure_ascii=False) if events_dict else ''
            }
            fictional_people.append(fictional_person)
    
    return fictional_people

def main():
    """メイン処理"""
    
    # 入力CSVファイル
    input_file = 'all_famous_people_20250821_224848.csv'
    
    # 出力CSVファイル
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f'extended_categorized_people_{timestamp}.csv'
    
    print(f"📚 CSVファイルを読み込み中: {input_file}")
    
    # 既存のデータを読み込み
    people = []
    with open(input_file, 'r', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            people.append(row)
    
    print(f"✅ {len(people)}人の実在人物データを読み込みました")
    
    # 拡張カテゴリで分類
    print("🏷️ 拡張カテゴリで分類中...")
    
    category_stats = {
        '歴史的教訓': {'count': 0, 'subcategories': {}},
        '日本サブカルチャー': {'count': 0, 'subcategories': {}},
        'テクノロジー・起業家': {'count': 0, 'subcategories': {}},
        '日本の偉人': {'count': 0, 'subcategories': {}},
        '架空の人物': {'count': 0, 'subcategories': {}},
    }
    
    for person in people:
        categories = categorize_with_extended_categories(person)
        person['main_category'] = categories['main_category']
        person['subcategory'] = categories['subcategory']
        person['special_tags'] = categories['special_tags']
        person['key_ages'] = ''  # 後で年齢別エピソードを追加
        
        # 統計を更新
        main_cat = categories['main_category']
        if main_cat in category_stats:
            category_stats[main_cat]['count'] += 1
            if categories['subcategory']:
                sub = categories['subcategory']
                if sub not in category_stats[main_cat]['subcategories']:
                    category_stats[main_cat]['subcategories'][sub] = 0
                category_stats[main_cat]['subcategories'][sub] += 1
    
    # 架空の人物を追加
    print("🎭 架空の人物を追加中...")
    fictional_people = add_fictional_characters()
    people.extend(fictional_people)
    category_stats['架空の人物']['count'] = len(fictional_people)
    
    print(f"✅ {len(fictional_people)}人の架空人物を追加しました")
    
    # CSVに書き出し
    print(f"💾 拡張カテゴリ付きCSVファイルを作成中: {output_file}")
    
    with open(output_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
        fieldnames = [
            'id', 'name', 'name_ja', 'birth_year', 'death_year', 'death_age',
            'nationality', 'occupation', 'main_category', 'subcategory', 
            'special_tags', 'source', 'wikidata_id', 'description', 'key_ages'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
        
        writer.writeheader()
        writer.writerows(people)
    
    # 統計を表示
    print("\n📊 拡張カテゴリ統計:")
    print("=" * 70)
    
    total = len(people)
    for main_cat, stats in category_stats.items():
        if stats['count'] > 0:
            percentage = (stats['count'] / total) * 100
            print(f"\n【{main_cat}】: {stats['count']:,}人 ({percentage:.1f}%)")
            
            # サブカテゴリを表示
            for sub_cat, count in sorted(stats['subcategories'].items(), 
                                        key=lambda x: x[1], reverse=True)[:5]:
                sub_percentage = (count / stats['count']) * 100
                print(f"  └─ {sub_cat}: {count}人 ({sub_percentage:.1f}%)")
    
    print("=" * 70)
    print(f"合計: {total:,}人")
    
    # 重要な発見を表示
    print("\n🔍 注目すべき発見:")
    
    # 歴史的教訓カテゴリの人物
    historical_lessons = [p for p in people if p.get('main_category') == '歴史的教訓']
    if historical_lessons:
        print(f"\n📚 歴史的教訓として学ぶべき人物: {len(historical_lessons)}人")
        for person in historical_lessons[:5]:
            name = person.get('name_ja') or person.get('name')
            subcategory = person.get('subcategory', '')
            print(f"  - {name} ({subcategory})")
    
    # 日本サブカルチャーの人物
    subculture = [p for p in people if p.get('main_category') == '日本サブカルチャー']
    if subculture:
        print(f"\n🎌 日本サブカルチャーの人物: {len(subculture)}人")
        for person in subculture[:5]:
            name = person.get('name_ja') or person.get('name')
            subcategory = person.get('subcategory', '')
            print(f"  - {name} ({subcategory})")
    
    print("\n✅ 処理完了！")
    print(f"📄 出力ファイル: {output_file}")
    print(f"📊 総人数: {len(people)}人（実在: {len(people) - len(fictional_people)}人、架空: {len(fictional_people)}人）")
    
    # 必要人数との差を計算
    required = 12410
    current = len(people)
    shortage = required - current
    
    if shortage > 0:
        print(f"\n⚠️ 必要人数まであと {shortage:,}人不足しています")
        print("💡 追加で収集すべきカテゴリ:")
        print("  - 日本のYouTuber、VTuber、インフルエンサー")
        print("  - 映画・アニメ・ゲームの架空キャラクター")
        print("  - 歴史上の minor な人物（地方の武将、商人など）")
        print("  - 現代のスタートアップ創業者")
    else:
        print(f"\n✅ 必要人数を達成しました！（余剰: {-shortage:,}人）")
    
    return output_file

if __name__ == "__main__":
    output_file = main()