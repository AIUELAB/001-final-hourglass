#!/usr/bin/env python3
"""
有名人データを詳細にカテゴリ分類（受賞歴、時代、専門分野など）
"""

import csv
import re
from datetime import datetime


class AdvancedCategorizer:
    """高度なカテゴリ分類器"""

    def __init__(self):
        # メインカテゴリとサブカテゴリのマッピング
        self.category_mappings = {
            '科学者': {
                'keywords': ['scientist', 'researcher', 'inventor'],
                'subcategories': {
                    '物理学者': ['physicist', 'physics'],
                    '化学者': ['chemist', 'chemistry'],
                    '生物学者': ['biologist', 'biology'],
                    '数学者': ['mathematician', 'mathematics'],
                    '天文学者': ['astronomer', 'astronomy'],
                    '医学者': ['physician', 'doctor', 'surgeon', 'medical'],
                    '工学者': ['engineer', 'engineering'],
                    'コンピュータ科学者': ['computer', 'software', 'programmer'],
                    '地質学者': ['geologist', 'geology'],
                    '心理学者': ['psychologist', 'psychiatrist']
                }
            },
            '芸術家': {
                'keywords': ['artist', 'painter', 'sculptor', 'designer'],
                'subcategories': {
                    '画家': ['painter', 'painting'],
                    '彫刻家': ['sculptor', 'sculpture'],
                    '建築家': ['architect', 'architecture'],
                    '写真家': ['photographer', 'photography'],
                    'デザイナー': ['designer', 'design'],
                    'イラストレーター': ['illustrator', 'illustration']
                }
            },
            '音楽家': {
                'keywords': ['composer', 'musician', 'conductor'],
                'subcategories': {
                    '作曲家': ['composer', 'composition'],
                    '指揮者': ['conductor', 'conducting'],
                    'ピアニスト': ['pianist', 'piano'],
                    'ヴァイオリニスト': ['violinist', 'violin'],
                    '歌手': ['singer', 'vocalist', 'soprano', 'tenor'],
                    'ジャズ音楽家': ['jazz'],
                    'ロック音楽家': ['rock'],
                    'クラシック音楽家': ['classical', 'orchestra'],
                    'オペラ歌手': ['opera']
                }
            },
            '文学者': {
                'keywords': ['writer', 'author', 'poet', 'novelist'],
                'subcategories': {
                    '小説家': ['novelist', 'fiction'],
                    '詩人': ['poet', 'poetry'],
                    '劇作家': ['playwright', 'dramatist'],
                    'ジャーナリスト': ['journalist', 'reporter'],
                    '評論家': ['critic', 'reviewer'],
                    '編集者': ['editor', 'publisher'],
                    '児童文学作家': ['children', 'youth']
                }
            },
            '政治家': {
                'keywords': ['politician', 'president', 'minister'],
                'subcategories': {
                    '大統領': ['president'],
                    '首相': ['prime minister', 'premier', 'chancellor'],
                    '国王・女王': ['king', 'queen', 'emperor', 'empress'],
                    '独裁者': ['dictator', 'autocrat'],
                    '革命家': ['revolutionary', 'revolution'],
                    '外交官': ['diplomat', 'ambassador'],
                    '議員': ['senator', 'congressman', 'deputy', 'parliamentarian']
                }
            },
            '軍人': {
                'keywords': ['military', 'general', 'admiral', 'soldier'],
                'subcategories': {
                    '将軍': ['general', 'marshal'],
                    '提督': ['admiral', 'naval'],
                    '戦略家': ['strategist', 'tactician'],
                    '傭兵': ['mercenary'],
                    '騎士': ['knight', 'samurai', '武将']
                }
            },
            'スポーツ': {
                'keywords': ['athlete', 'player', 'sport', 'olympic'],
                'subcategories': {
                    'サッカー選手': ['football', 'soccer'],
                    '野球選手': ['baseball'],
                    'バスケットボール選手': ['basketball'],
                    'テニス選手': ['tennis'],
                    'ゴルフ選手': ['golf'],
                    'オリンピック選手': ['olympic'],
                    'ボクサー': ['boxer', 'boxing'],
                    'F1ドライバー': ['formula', 'racing', 'driver']
                }
            },
            'エンターテインメント': {
                'keywords': ['actor', 'actress', 'film', 'movie'],
                'subcategories': {
                    '俳優': ['actor', 'actress'],
                    '映画監督': ['director', 'filmmaker'],
                    'プロデューサー': ['producer'],
                    'コメディアン': ['comedian', 'comic'],
                    'ダンサー': ['dancer', 'choreographer'],
                    'マジシャン': ['magician', 'illusionist']
                }
            },
            'ビジネス': {
                'keywords': ['business', 'entrepreneur', 'ceo', 'founder'],
                'subcategories': {
                    '起業家': ['entrepreneur', 'founder'],
                    'CEO': ['ceo', 'chief executive'],
                    '投資家': ['investor', 'financier'],
                    '銀行家': ['banker', 'banking'],
                    '実業家': ['industrialist', 'magnate']
                }
            },
            '哲学・宗教': {
                'keywords': ['philosopher', 'theologian', 'religious'],
                'subcategories': {
                    '哲学者': ['philosopher', 'philosophy'],
                    '神学者': ['theologian', 'theology'],
                    '宗教指導者': ['pope', 'bishop', 'priest', 'monk', 'rabbi', 'imam'],
                    '思想家': ['thinker', 'intellectual']
                }
            },
            '活動家': {
                'keywords': ['activist', 'rights', 'movement'],
                'subcategories': {
                    '人権活動家': ['rights', 'civil rights'],
                    '環境活動家': ['environmental', 'climate'],
                    '女性運動家': ['feminist', 'women'],
                    '労働運動家': ['labor', 'union']
                }
            }
        }

        # 受賞歴の検出パターン
        self.award_patterns = {
            'ノーベル賞受賞者': ['nobel', 'ノーベル'],
            'アカデミー賞受賞者': ['academy award', 'oscar', 'アカデミー'],
            'グラミー賞受賞者': ['grammy', 'グラミー'],
            'フィールズ賞受賞者': ['fields medal', 'フィールズ'],
            'ピューリッツァー賞受賞者': ['pulitzer', 'ピューリッツァー'],
            'トニー賞受賞者': ['tony award', 'トニー'],
            'エミー賞受賞者': ['emmy', 'エミー']
        }

    def get_era(self, birth_year, death_year):
        """時代を判定"""
        try:
            birth = int(birth_year) if birth_year else None
            death = int(death_year) if death_year else None

            # 生年を基準に判定
            if birth:
                if birth < 0:
                    return '古代（紀元前）'
                elif birth < 500:
                    return '古代（紀元後）'
                elif birth < 1000:
                    return '中世前期'
                elif birth < 1500:
                    return '中世後期'
                elif birth < 1700:
                    return '近世'
                elif birth < 1800:
                    return '18世紀'
                elif birth < 1850:
                    return '19世紀前半'
                elif birth < 1900:
                    return '19世紀後半'
                elif birth < 1950:
                    return '20世紀前半'
                elif birth < 2000:
                    return '20世紀後半'
                else:
                    return '21世紀'
        except:
            pass

        return '時代不明'

    def get_region(self, nationality):
        """地域を判定"""
        if not nationality:
            return '地域不明'

        nat_lower = nationality.lower()

        # 地域マッピング
        regions = {
            '北アメリカ': ['united states', 'america', 'canada', 'mexico'],
            '南アメリカ': ['brazil', 'argentina', 'chile', 'colombia', 'peru', 'venezuela'],
            'ヨーロッパ': ['france', 'germany', 'italy', 'spain', 'united kingdom', 'england',
                      'russia', 'poland', 'austria', 'netherlands', 'belgium', 'switzerland',
                      'sweden', 'norway', 'denmark', 'finland', 'greece', 'portugal'],
            'アジア': ['japan', 'china', 'india', 'korea', 'thailand', 'vietnam', 'indonesia'],
            '中東': ['israel', 'egypt', 'saudi', 'iran', 'iraq', 'syria', 'turkey'],
            'アフリカ': ['south africa', 'nigeria', 'kenya', 'ethiopia', 'ghana'],
            'オセアニア': ['australia', 'new zealand'],
            '古代文明': ['ancient rome', 'rome', 'greek', 'egypt', 'babylon', 'persia']
        }

        for region, countries in regions.items():
            if any(country in nat_lower for country in countries):
                return region

        # 日本の特別処理
        if '日本' in nationality or 'japan' in nat_lower:
            return '日本'

        return 'その他地域'

    def categorize_detailed(self, person):
        """詳細なカテゴリ分類"""
        occupation = person.get('occupation', '').lower()
        nationality = person.get('nationality', '')
        name = person.get('name', '').lower()

        # 結果を格納
        main_category = 'その他'
        sub_category = ''
        special_tags = []

        # メインカテゴリとサブカテゴリを判定
        for main_cat, cat_info in self.category_mappings.items():
            # メインカテゴリのキーワードチェック
            if any(keyword in occupation for keyword in cat_info['keywords']):
                main_category = main_cat

                # サブカテゴリを判定
                for sub_cat, sub_keywords in cat_info['subcategories'].items():
                    if any(keyword in occupation for keyword in sub_keywords):
                        sub_category = sub_cat
                        break

                if not sub_category:
                    sub_category = main_cat + '（詳細不明）'
                break

        # 特別な職業の処理
        if 'ancient roman' in occupation:
            if 'military' in occupation:
                main_category = '軍人'
                sub_category = '古代ローマ軍人'
            elif 'politician' in occupation:
                main_category = '政治家'
                sub_category = '古代ローマ政治家'

        # 受賞歴をチェック（本来はdescriptionフィールドやWikidataから取得すべき）
        for award, patterns in self.award_patterns.items():
            if any(pattern in occupation or pattern in name for pattern in patterns):
                special_tags.append(award)

        # 時代を取得
        era = self.get_era(person.get('birth_year'), person.get('death_year'))

        # 地域を取得
        region = self.get_region(nationality)

        # 日本人の特別処理
        if region == '日本' or '日本' in nationality:
            special_tags.append('日本人')
            if any(word in occupation for word in ['samurai', '武将', 'shogun', 'daimyo']):
                main_category = '軍人'
                sub_category = '武将・侍'

        # 100歳以上生きた人
        try:
            death_age = int(person.get('death_age', 0))
            if death_age >= 100:
                special_tags.append('長寿（100歳以上）')
            elif death_age <= 30 and death_age > 0:
                special_tags.append('若逝（30歳以下）')
        except:
            pass

        return {
            'main_category': main_category,
            'sub_category': sub_category,
            'era': era,
            'region': region,
            'special_tags': '|'.join(special_tags) if special_tags else ''
        }

def main():
    """メイン処理"""

    # カテゴライザーを初期化
    categorizer = AdvancedCategorizer()

    # 入力CSVファイル
    input_file = 'all_famous_people_20250821_224848.csv'

    # 出力CSVファイル
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f'detailed_categorized_famous_people_{timestamp}.csv'

    print(f"📚 CSVファイルを読み込み中: {input_file}")

    # CSVを読み込み
    people = []
    with open(input_file, 'r', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            people.append(row)

    print(f"✅ {len(people)}人のデータを読み込みました")

    # 詳細カテゴリを分類
    print("🏷️ 詳細カテゴリを分類中...")

    # 統計用カウンター
    main_cat_counts = {}
    sub_cat_counts = {}
    era_counts = {}
    region_counts = {}
    tag_counts = {}

    for person in people:
        # 詳細分類を実行
        categories = categorizer.categorize_detailed(person)

        # データに追加
        person['main_category'] = categories['main_category']
        person['sub_category'] = categories['sub_category']
        person['era'] = categories['era']
        person['region'] = categories['region']
        person['special_tags'] = categories['special_tags']

        # 統計カウント
        main_cat_counts[categories['main_category']] = main_cat_counts.get(categories['main_category'], 0) + 1
        if categories['sub_category']:
            sub_cat_counts[categories['sub_category']] = sub_cat_counts.get(categories['sub_category'], 0) + 1
        era_counts[categories['era']] = era_counts.get(categories['era'], 0) + 1
        region_counts[categories['region']] = region_counts.get(categories['region'], 0) + 1

        # 特別タグのカウント
        if categories['special_tags']:
            for tag in categories['special_tags'].split('|'):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

    # 新しいCSVファイルに書き出し
    print(f"💾 詳細カテゴリ付きCSVファイルを作成中: {output_file}")

    with open(output_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
        fieldnames = ['id', 'name', 'name_ja', 'birth_year', 'death_year', 'death_age',
                      'nationality', 'occupation', 'category', 'main_category', 'sub_category',
                      'era', 'region', 'special_tags', 'source', 'wikidata_id', 'description']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        writer.writerows(people)

    print("\n✅ 詳細カテゴリ分類完了！")

    # 統計を表示
    print("\n" + "="*60)
    print("📊 詳細統計レポート")
    print("="*60)

    # メインカテゴリ統計
    print("\n【メインカテゴリ】")
    print("-"*40)
    for cat, count in sorted(main_cat_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / len(people)) * 100
        print(f"{cat:20} : {count:5,}人 ({percentage:5.1f}%)")

    # サブカテゴリ統計（上位20）
    print("\n【サブカテゴリ（上位20）】")
    print("-"*40)
    for cat, count in sorted(sub_cat_counts.items(), key=lambda x: x[1], reverse=True)[:20]:
        percentage = (count / len(people)) * 100
        print(f"{cat:25} : {count:5,}人 ({percentage:5.1f}%)")

    # 時代別統計
    print("\n【時代別分布】")
    print("-"*40)
    era_order = ['古代（紀元前）', '古代（紀元後）', '中世前期', '中世後期', '近世',
                 '18世紀', '19世紀前半', '19世紀後半', '20世紀前半', '20世紀後半', '21世紀', '時代不明']
    for era in era_order:
        if era in era_counts:
            count = era_counts[era]
            percentage = (count / len(people)) * 100
            print(f"{era:15} : {count:5,}人 ({percentage:5.1f}%)")

    # 地域別統計
    print("\n【地域別分布】")
    print("-"*40)
    for region, count in sorted(region_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / len(people)) * 100
        print(f"{region:15} : {count:5,}人 ({percentage:5.1f}%)")

    # 特別タグ統計
    if tag_counts:
        print("\n【特別タグ】")
        print("-"*40)
        for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"{tag:20} : {count:5,}人")

    print("\n" + "="*60)
    print("総カテゴリ数:")
    print(f"  - メインカテゴリ: {len(main_cat_counts)}種類")
    print(f"  - サブカテゴリ: {len(sub_cat_counts)}種類")
    print(f"  - 時代区分: {len(era_counts)}種類")
    print(f"  - 地域区分: {len(region_counts)}種類")
    print(f"  - 特別タグ: {len(tag_counts)}種類")

    return output_file

if __name__ == "__main__":
    output_file = main()
    print("\n🎉 処理完了！")
    print(f"📄 出力ファイル: {output_file}")
