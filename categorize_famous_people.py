#!/usr/bin/env python3
"""
有名人データに職業ベースでカテゴリを自動分類
"""

import csv
from datetime import datetime


def categorize_person(occupation, nationality=''):
    """職業と国籍からカテゴリを決定"""
    
    occupation_lower = occupation.lower() if occupation else ''
    nationality_lower = nationality.lower() if nationality else ''
    
    # 科学者・学者
    if any(word in occupation_lower for word in [
        'scientist', 'physicist', 'chemist', 'biologist', 'mathematician',
        'astronomer', 'geologist', 'inventor', 'engineer', 'researcher',
        'professor', 'academic', 'scholar', 'doctor', 'physician',
        'surgeon', 'medical', 'psychiatrist', 'psychologist'
    ]):
        return '科学者・学者'
    
    # 芸術家・音楽家
    elif any(word in occupation_lower for word in [
        'composer', 'musician', 'conductor', 'pianist', 'violinist',
        'singer', 'vocalist', 'performer', 'artist', 'painter',
        'sculptor', 'architect', 'designer', 'photographer'
    ]):
        return '芸術家・音楽家'
    
    # 文学者・作家
    elif any(word in occupation_lower for word in [
        'writer', 'author', 'poet', 'novelist', 'playwright',
        'journalist', 'editor', 'publisher', 'literary'
    ]):
        return '文学者・作家'
    
    # 哲学者・思想家
    elif any(word in occupation_lower for word in [
        'philosopher', 'thinker', 'theologian', 'religious',
        'priest', 'monk', 'clergy', 'bishop', 'pope'
    ]):
        return '哲学者・思想家'
    
    # 政治家・指導者
    elif any(word in occupation_lower for word in [
        'politician', 'president', 'minister', 'governor',
        'senator', 'congressman', 'deputy', 'mayor',
        'diplomat', 'ambassador', 'statesperson', 'statesman'
    ]):
        return '政治家・指導者'
    
    # 王族・貴族
    elif any(word in occupation_lower for word in [
        'king', 'queen', 'emperor', 'empress', 'prince', 'princess',
        'monarch', 'sovereign', 'royal', 'duke', 'duchess',
        'count', 'countess', 'baron', 'aristocrat', 'noble'
    ]):
        return '王族・貴族'
    
    # 軍人・軍事関係者
    elif any(word in occupation_lower for word in [
        'military', 'general', 'admiral', 'colonel', 'captain',
        'soldier', 'army', 'navy', 'air force', 'marine',
        'warrior', 'commander', 'officer'
    ]):
        return '軍人・軍事関係者'
    
    # 実業家・起業家
    elif any(word in occupation_lower for word in [
        'business', 'entrepreneur', 'industrialist', 'merchant',
        'banker', 'financier', 'investor', 'ceo', 'founder',
        'executive', 'manager', 'trader'
    ]):
        return '実業家・起業家'
    
    # スポーツ選手
    elif any(word in occupation_lower for word in [
        'athlete', 'player', 'sport', 'football', 'baseball',
        'basketball', 'tennis', 'golf', 'olympic', 'champion',
        'boxer', 'wrestler', 'racer', 'driver'
    ]):
        return 'スポーツ選手'
    
    # 俳優・芸能人
    elif any(word in occupation_lower for word in [
        'actor', 'actress', 'film', 'movie', 'cinema',
        'theater', 'theatre', 'entertainer', 'celebrity',
        'comedian', 'director', 'producer'
    ]):
        return '俳優・芸能人'
    
    # 探検家・冒険家
    elif any(word in occupation_lower for word in [
        'explorer', 'adventurer', 'navigator', 'discoverer',
        'traveler', 'expedition'
    ]):
        return '探検家・冒険家'
    
    # 活動家・社会運動家
    elif any(word in occupation_lower for word in [
        'activist', 'revolutionary', 'reformer', 'rights',
        'movement', 'leader', 'organizer'
    ]):
        return '活動家・社会運動家'
    
    # 法律家
    elif any(word in occupation_lower for word in [
        'lawyer', 'attorney', 'judge', 'justice', 'legal',
        'barrister', 'solicitor', 'prosecutor'
    ]):
        return '法律家'
    
    # 教育者
    elif any(word in occupation_lower for word in [
        'teacher', 'educator', 'instructor', 'lecturer',
        'tutor', 'pedagogue'
    ]):
        return '教育者'
    
    # 日本人特別カテゴリ（国籍ベース）
    elif 'japan' in nationality_lower or '日本' in nationality:
        if any(word in occupation_lower for word in ['samurai', 'shogun', 'daimyo', '武将', '侍']):
            return '日本の武将・侍'
        else:
            return '日本の偉人'
    
    # 古代の人物
    elif any(word in nationality_lower for word in ['ancient', 'rome', 'greek', 'egypt']):
        return '古代の偉人'
    
    # その他
    else:
        return 'その他'

def main():
    """メイン処理"""
    
    # 入力CSVファイル
    input_file = 'all_famous_people_20250821_224848.csv'
    
    # 出力CSVファイル
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f'categorized_famous_people_{timestamp}.csv'
    
    print(f"📚 CSVファイルを読み込み中: {input_file}")
    
    # CSVを読み込み
    people = []
    with open(input_file, 'r', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            people.append(row)
    
    print(f"✅ {len(people)}人のデータを読み込みました")
    
    # カテゴリを分類
    print("🏷️ カテゴリを分類中...")
    
    category_counts = {}
    for person in people:
        # 既存のカテゴリがある場合はそれを優先
        if person.get('category') and person['category'] not in ['', 'unknown']:
            # 既存カテゴリをより分かりやすい日本語に変換
            existing_cat = person['category']
            if existing_cat == 'scientists':
                person['category'] = '科学者・学者'
            elif existing_cat == 'artists':
                person['category'] = '芸術家・音楽家'
            elif existing_cat == 'leaders':
                person['category'] = '政治家・指導者'
            elif existing_cat == 'writers':
                person['category'] = '文学者・作家'
            elif existing_cat == 'japanese':
                person['category'] = '日本の偉人'
            elif existing_cat == 'others':
                person['category'] = 'その他'
            else:
                # occupationベースで再分類
                person['category'] = categorize_person(
                    person.get('occupation', ''),
                    person.get('nationality', '')
                )
        else:
            # occupationベースで分類
            person['category'] = categorize_person(
                person.get('occupation', ''),
                person.get('nationality', '')
            )
        
        # カウント
        cat = person['category']
        category_counts[cat] = category_counts.get(cat, 0) + 1
    
    # 新しいCSVファイルに書き出し
    print(f"💾 カテゴリ付きCSVファイルを作成中: {output_file}")
    
    with open(output_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
        fieldnames = ['id', 'name', 'name_ja', 'birth_year', 'death_year', 'death_age', 
                      'nationality', 'occupation', 'category', 'source', 'wikidata_id', 'description']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        writer.writerows(people)
    
    print("\n✅ カテゴリ分類完了！")
    
    # 統計を表示
    print("\n📊 カテゴリ別統計:")
    print("-" * 50)
    
    total = sum(category_counts.values())
    for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total) * 100
        print(f"{category:20} : {count:5,}人 ({percentage:5.1f}%)")
    
    print("-" * 50)
    print(f"{'合計':20} : {total:5,}人 (100.0%)")
    
    # カテゴリ別の代表的な人物を表示
    print("\n👥 各カテゴリの代表的な人物（最初の3人）:")
    print("-" * 50)
    
    for category in sorted(category_counts.keys()):
        print(f"\n【{category}】")
        count = 0
        for person in people:
            if person['category'] == category and count < 3:
                name = person['name_ja'] if person['name_ja'] else person['name']
                birth_death = f"({person['birth_year']}-{person['death_year']})" if person['birth_year'] else ""
                print(f"  - {name} {birth_death}")
                count += 1
    
    return output_file

if __name__ == "__main__":
    output_file = main()
    print("\n🎉 処理完了！")
    print(f"📄 出力ファイル: {output_file}")