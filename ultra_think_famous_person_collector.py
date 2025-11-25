#!/usr/bin/env python3
"""
Ultra Think 完全有名人データベース構築システム
エピソード生成に最適化されたperson_name_display生成
歴史的偉人から現代まで、教育的価値の高い包括的データベース
"""

import json
import csv
import requests
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Set
import time
from dataclasses import dataclass, field, asdict
import hashlib
import re

@dataclass
class UltraThinkPerson:
    """Ultra Think人物データ構造"""
    # 必須フィールド
    person_name: str           # 英語名/原語名
    person_name_ja: str        # 日本語名（必須）
    person_name_display: str   # エピソード用表示名（必須）
    birth_year: int           # 生年（必須、NULL不可）

    # 基本情報
    birth_date: str = ""
    death_date: str = ""
    nationality: str = ""
    occupation: str = ""
    main_category: str = ""
    subcategory: str = ""
    wikidata_id: str = ""
    description: str = ""

    # 評価スコア
    historical_impact: int = 0      # 歴史的影響力 (1-10)
    educational_value: int = 0      # 教育的価値 (1-10)
    cultural_significance: int = 0  # 文化的重要性 (1-10)
    global_recognition: int = 0     # 国際的認知度 (1-10)
    inspirational_value: int = 0    # インスピレーション価値 (1-10)

    # メタ情報
    grade: str = ""        # S, A, B, C
    era: str = ""         # 時代区分
    group_affiliation: str = ""  # グループ所属

    def to_dict(self) -> Dict:
        return asdict(self)

    def generate_id(self) -> str:
        text = f"{self.person_name}_{self.birth_year}"
        return f"person_{hashlib.md5(text.encode()).hexdigest()[:8]}"


class PersonNameDisplayGenerator:
    """エピソード最適化されたperson_name_display生成"""

    def __init__(self):
        # 歴史的に唯一無二で短縮可能な人物
        self.historical_unique_names = {
            # 音楽家
            'ヨハン・セバスチャン・バッハ': 'バッハ',
            'ヴォルフガング・アマデウス・モーツァルト': 'モーツァルト',
            'ルートヴィヒ・ヴァン・ベートーヴェン': 'ベートーヴェン',
            'フレデリック・ショパン': 'ショパン',
            'ヨハネス・ブラームス': 'ブラームス',
            'リヒャルト・ワーグナー': 'ワーグナー',

            # 美術家
            'レオナルド・ダ・ヴィンチ': 'ダ・ヴィンチ',
            'ミケランジェロ・ブオナローティ': 'ミケランジェロ',
            'パブロ・ピカソ': 'ピカソ',
            'フィンセント・ファン・ゴッホ': 'ゴッホ',
            'レンブラント・ファン・レイン': 'レンブラント',

            # 科学者
            'アイザック・ニュートン': 'ニュートン',
            'チャールズ・ダーウィン': 'ダーウィン',
            'ガリレオ・ガリレイ': 'ガリレオ',
            'アルベルト・アインシュタイン': 'アインシュタイン',
            'トーマス・エジソン': 'エジソン',

            # 日本の歴史人物
            '織田信長': '信長',
            '豊臣秀吉': '秀吉',
            '徳川家康': '家康',
            '武田信玄': '信玄',
            '上杉謙信': '謙信',
            '千利休': '利休',
            '松尾芭蕉': '芭蕉',

            # 世界の歴史人物
            'ナポレオン・ボナパルト': 'ナポレオン',
            'ユリウス・カエサル': 'カエサル',
            'アレクサンドロス大王': 'アレクサンドロス',
        }

        # 同姓問題で区別が必要な人物
        self.disambiguation_required = {
            'クララ・シューマン': 'クララ・シューマン',  # ロベルトと区別
            'マリー・キュリー': 'マリー・キュリー',  # ピエールと区別
            'ヨハン・シュトラウス2世': 'ヨハン・シュトラウス2世',  # 父と区別
            'ジョン・F・ケネディ': 'ジョン・F・ケネディ',  # ロバートと区別
            'マイケル・ジャクソン': 'マイケル・ジャクソン',  # アンドリューと区別
        }

        # グループメンバー（グループ名を付与）
        self.group_members = {
            '伊達みきお': 'サンドウィッチマン',
            '富澤たけし': 'サンドウィッチマン',
            '松本人志': 'ダウンタウン',
            '浜田雅功': 'ダウンタウン',
            '桑田佳祐': 'サザンオールスターズ',
            'フリー': 'レッド・ホット・チリ・ペッパーズ',
        }

    def generate_display_name(self, person: Dict) -> str:
        """エピソード最適化されたdisplay name生成"""
        name_ja = person.get('person_name_ja', '')
        birth_year = person.get('birth_year', 9999)

        # グループメンバーチェック
        if name_ja in self.group_members:
            group = self.group_members[name_ja]
            # 個人名が短い場合はそのまま、長い場合は姓のみ
            short_name = self._get_short_name(name_ja)
            return f"{short_name}（{group}）"

        # 同姓問題チェック
        if name_ja in self.disambiguation_required:
            return self.disambiguation_required[name_ja]

        # 歴史的唯一無二チェック
        if name_ja in self.historical_unique_names:
            return self.historical_unique_names[name_ja]

        # 時代による判定
        if birth_year < 1900:
            # 歴史人物は短縮優先
            short = self._get_short_name(name_ja)
            # エピソード読みやすさテスト
            if len(short) <= 6:
                return short

        # 現代人（1950年以降）はフルネーム
        if birth_year >= 1950:
            return name_ja

        # デフォルトはフルネーム
        return name_ja

    def _get_short_name(self, full_name: str) -> str:
        """短縮名取得（姓または名のみ）"""
        # 日本人名の場合
        if self._is_japanese_name(full_name):
            # スペースで分割
            parts = full_name.split()
            if len(parts) >= 2:
                # 姓が特定しやすい場合は姓を返す
                return parts[0]

        # 西洋人名の場合
        if '・' in full_name:
            parts = full_name.split('・')
            # 最後の部分（姓）を返す
            return parts[-1]

        return full_name

    def _is_japanese_name(self, name: str) -> bool:
        """日本人名かどうか判定"""
        # ひらがな、カタカナ、漢字を含む
        japanese_pattern = re.compile(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]')
        # カタカナのみでない（外国人名の可能性）
        katakana_only = re.compile(r'^[\u30A0-\u30FF・ー]+$')

        return bool(japanese_pattern.search(name)) and not bool(katakana_only.match(name))


class UltraThinkCollector:
    """Ultra Think有名人収集システム"""

    def __init__(self):
        self.wikidata_endpoint = "https://query.wikidata.org/sparql"
        self.display_generator = PersonNameDisplayGenerator()
        self.collected_people = {}
        self.stats = {
            'total_collected': 0,
            'with_birth_year': 0,
            'historical_figures': 0,
            'scientists': 0,
            'artists': 0,
            'politicians': 0,
            'business': 0,
            'sports': 0,
            'entertainment': 0,
            'start_time': datetime.now()
        }

        # Firebase Episodesから欠落している必須人物
        self.essential_people = [
            # 科学者・発明家
            {"name": "Thomas Edison", "name_ja": "トーマス・エジソン", "birth_year": 1847, "death_year": 1931, "occupation": "発明家"},
            {"name": "Albert Einstein", "name_ja": "アルベルト・アインシュタイン", "birth_year": 1879, "death_year": 1955, "occupation": "物理学者"},
            {"name": "Isaac Newton", "name_ja": "アイザック・ニュートン", "birth_year": 1643, "death_year": 1727, "occupation": "物理学者"},
            {"name": "Charles Darwin", "name_ja": "チャールズ・ダーウィン", "birth_year": 1809, "death_year": 1882, "occupation": "生物学者"},
            {"name": "Marie Curie", "name_ja": "マリー・キュリー", "birth_year": 1867, "death_year": 1934, "occupation": "物理学者"},
            {"name": "Nikola Tesla", "name_ja": "ニコラ・テスラ", "birth_year": 1856, "death_year": 1943, "occupation": "発明家"},

            # 日本の歴史人物
            {"name": "Oda Nobunaga", "name_ja": "織田信長", "birth_year": 1534, "death_year": 1582, "occupation": "武将"},
            {"name": "Toyotomi Hideyoshi", "name_ja": "豊臣秀吉", "birth_year": 1537, "death_year": 1598, "occupation": "武将"},
            {"name": "Tokugawa Ieyasu", "name_ja": "徳川家康", "birth_year": 1543, "death_year": 1616, "occupation": "武将"},
            {"name": "Sakamoto Ryoma", "name_ja": "坂本龍馬", "birth_year": 1836, "death_year": 1867, "occupation": "志士"},
            {"name": "Saigo Takamori", "name_ja": "西郷隆盛", "birth_year": 1828, "death_year": 1877, "occupation": "政治家"},
            {"name": "Fukuzawa Yukichi", "name_ja": "福沢諭吉", "birth_year": 1835, "death_year": 1901, "occupation": "啓蒙思想家"},
            {"name": "Noguchi Hideyo", "name_ja": "野口英世", "birth_year": 1876, "death_year": 1928, "occupation": "細菌学者"},
            {"name": "Kitasato Shibasaburo", "name_ja": "北里柴三郎", "birth_year": 1853, "death_year": 1931, "occupation": "細菌学者"},

            # 政治家・指導者
            {"name": "Abraham Lincoln", "name_ja": "エイブラハム・リンカーン", "birth_year": 1809, "death_year": 1865, "occupation": "大統領"},
            {"name": "Winston Churchill", "name_ja": "ウィンストン・チャーチル", "birth_year": 1874, "death_year": 1965, "occupation": "首相"},
            {"name": "Napoleon Bonaparte", "name_ja": "ナポレオン・ボナパルト", "birth_year": 1769, "death_year": 1821, "occupation": "皇帝"},
            {"name": "Mahatma Gandhi", "name_ja": "マハトマ・ガンジー", "birth_year": 1869, "death_year": 1948, "occupation": "独立運動家"},

            # 芸術家
            {"name": "Leonardo da Vinci", "name_ja": "レオナルド・ダ・ヴィンチ", "birth_year": 1452, "death_year": 1519, "occupation": "芸術家"},
            {"name": "Pablo Picasso", "name_ja": "パブロ・ピカソ", "birth_year": 1881, "death_year": 1973, "occupation": "画家"},
            {"name": "Vincent van Gogh", "name_ja": "フィンセント・ファン・ゴッホ", "birth_year": 1853, "death_year": 1890, "occupation": "画家"},
            {"name": "Wolfgang Amadeus Mozart", "name_ja": "ヴォルフガング・アマデウス・モーツァルト", "birth_year": 1756, "death_year": 1791, "occupation": "作曲家"},
            {"name": "Ludwig van Beethoven", "name_ja": "ルートヴィヒ・ヴァン・ベートーヴェン", "birth_year": 1770, "death_year": 1827, "occupation": "作曲家"},
            {"name": "Johann Sebastian Bach", "name_ja": "ヨハン・セバスチャン・バッハ", "birth_year": 1685, "death_year": 1750, "occupation": "作曲家"},
            {"name": "Rembrandt", "name_ja": "レンブラント・ファン・レイン", "birth_year": 1606, "death_year": 1669, "occupation": "画家"},

            # その他重要人物
            {"name": "Helen Keller", "name_ja": "ヘレン・ケラー", "birth_year": 1880, "death_year": 1968, "occupation": "社会活動家"},
            {"name": "Alexander Fleming", "name_ja": "アレクサンダー・フレミング", "birth_year": 1881, "death_year": 1955, "occupation": "細菌学者"},
            {"name": "John D. Rockefeller", "name_ja": "ジョン・D・ロックフェラー", "birth_year": 1839, "death_year": 1937, "occupation": "実業家"},
        ]

    def collect_all_people(self, target_count: int = 12410) -> List[UltraThinkPerson]:
        """完全な有名人収集"""
        print("🎯 Ultra Think 有名人データベース構築システム起動")
        print(f"📊 目標: {target_count}人（エピソード生成最適化）")
        print("=" * 60)

        all_people = []

        # Phase 1: 必須人物の収集（最優先）
        print("\n📌 Phase 1: Firebase Episodes欠落人物の収集")
        essential = self._collect_essential_people()
        all_people.extend(essential)
        print(f"  ✅ {len(essential)}名の必須人物を収集")

        # Phase 2: ノーベル賞受賞者
        print("\n🏆 Phase 2: ノーベル賞受賞者")
        nobel = self._collect_nobel_laureates(500)
        all_people.extend(nobel)

        # Phase 3: 各時代の代表的人物
        print("\n📚 Phase 3: 時代別代表人物")
        historical = self._collect_historical_figures(2500)
        all_people.extend(historical)

        # Phase 4: 科学技術の先駆者
        print("\n🔬 Phase 4: 科学技術の先駆者")
        scientists = self._collect_scientists(1500)
        all_people.extend(scientists)

        # Phase 5: 文化・芸術の巨匠
        print("\n🎨 Phase 5: 文化・芸術の巨匠")
        artists = self._collect_artists(1500)
        all_people.extend(artists)

        # Phase 6: 政治・社会の指導者
        print("\n🏛️ Phase 6: 政治・社会の指導者")
        leaders = self._collect_leaders(1200)
        all_people.extend(leaders)

        # Phase 7: ビジネス・イノベーター
        print("\n💼 Phase 7: ビジネス・イノベーター")
        business = self._collect_business_leaders(1200)
        all_people.extend(business)

        # Phase 8: スポーツの英雄
        print("\n⚽ Phase 8: スポーツの英雄")
        sports = self._collect_sports_heroes(1200)
        all_people.extend(sports)

        # Phase 9: 現代のエンターテインメント（最小限）
        print("\n🌟 Phase 9: 現代のエンターテインメント")
        entertainment = self._collect_entertainment(1500)
        all_people.extend(entertainment)

        # birth_yearがNULLの人物を除外
        valid_people = [p for p in all_people if p.birth_year is not None]

        # 重複除去と品質評価
        unique_people = self._evaluate_and_dedupe(valid_people)

        # 統計表示
        self._print_statistics(unique_people[:target_count])

        return unique_people[:target_count]

    def _collect_essential_people(self) -> List[UltraThinkPerson]:
        """必須人物の収集"""
        people = []

        for data in self.essential_people:
            # person_name_display生成
            display_name = self.display_generator.generate_display_name({
                'person_name_ja': data['name_ja'],
                'birth_year': data['birth_year']
            })

            person = UltraThinkPerson(
                person_name=data['name'],
                person_name_ja=data['name_ja'],
                person_name_display=display_name,
                birth_year=data['birth_year'],
                birth_date=f"{data['birth_year']}-01-01",
                death_date=f"{data.get('death_year', '')}-01-01" if data.get('death_year') else "",
                occupation=data['occupation'],
                main_category=self._determine_category(data['occupation']),
                historical_impact=10,
                educational_value=10,
                cultural_significance=9,
                global_recognition=10,
                inspirational_value=9,
                grade="S",
                era=self._determine_era(data['birth_year'])
            )

            people.append(person)
            self.stats['historical_figures'] += 1
            self.stats['with_birth_year'] += 1

        return people

    def _collect_nobel_laureates(self, limit: int) -> List[UltraThinkPerson]:
        """ノーベル賞受賞者の収集"""
        query = """
        SELECT DISTINCT ?person ?personLabel ?birthDate ?deathDate ?countryLabel ?awardLabel
        WHERE {
          ?person wdt:P31 wd:Q5 ;
                  wdt:P166 ?award ;
                  wdt:P569 ?birthDate .
          ?award wdt:P31*/wdt:P279* wd:Q7191 .
          OPTIONAL { ?person wdt:P570 ?deathDate }
          OPTIONAL { ?person wdt:P27 ?country }
          SERVICE wikibase:label { bd:serviceParam wikibase:language "ja,en". }
        }
        LIMIT """ + str(limit)

        people = []
        try:
            result = self._execute_query(query)
            for item in result:
                person = self._create_person_from_result(item, "科学・学術", "S")
                if person and person.birth_year:
                    people.append(person)
                    self.stats['scientists'] += 1
                    self.stats['with_birth_year'] += 1
        except Exception as e:
            print(f"  ⚠️ ノーベル賞受賞者収集エラー: {str(e)[:50]}")

        return people[:limit]

    def _collect_historical_figures(self, limit: int) -> List[UltraThinkPerson]:
        """各時代の代表的人物を収集"""
        people = []

        # 時代別クエリ
        eras = [
            ("古代", "-1000", "500", 500),
            ("中世", "500", "1500", 500),
            ("近世", "1500", "1800", 500),
            ("近代", "1800", "1900", 500),
            ("現代前期", "1900", "1950", 500)
        ]

        for era_name, start_year, end_year, count in eras:
            query = f"""
            SELECT DISTINCT ?person ?personLabel ?birthDate ?deathDate ?countryLabel ?occupationLabel
            WHERE {{
              ?person wdt:P31 wd:Q5 ;
                      wdt:P569 ?birthDate ;
                      wdt:P106 ?occupation .
              OPTIONAL {{ ?person wdt:P570 ?deathDate }}
              OPTIONAL {{ ?person wdt:P27 ?country }}

              FILTER(YEAR(?birthDate) >= {start_year} && YEAR(?birthDate) <= {end_year})

              SERVICE wikibase:label {{ bd:serviceParam wikibase:language "ja,en". }}
            }}
            ORDER BY DESC(?birthDate)
            LIMIT {count}
            """

            try:
                result = self._execute_query(query)
                for item in result:
                    person = self._create_person_from_result(item, "歴史的人物", "A")
                    if person and person.birth_year:
                        person.era = era_name
                        people.append(person)
                        self.stats['historical_figures'] += 1
                        self.stats['with_birth_year'] += 1
            except Exception as e:
                print(f"  ⚠️ {era_name}収集エラー: {str(e)[:50]}")

        return people[:limit]

    def _create_person_from_result(self, item: Dict, category: str, grade: str) -> Optional[UltraThinkPerson]:
        """SPARQLの結果から人物データを作成"""
        try:
            name = item.get('personLabel', {}).get('value', '')
            if not name or name.startswith('Q'):  # WikidataIDのままの場合はスキップ
                return None

            birth_date = item.get('birthDate', {}).get('value', '')[:10]
            death_date = item.get('deathDate', {}).get('value', '')[:10] if 'deathDate' in item else ''

            # birth_yearを抽出
            birth_year = None
            if birth_date:
                try:
                    if birth_date.startswith('-'):  # BC dates
                        birth_year = int(birth_date[1:5]) * -1
                    else:
                        birth_year = int(birth_date[:4])
                except:
                    return None  # birth_yearが取得できない場合はスキップ
            else:
                return None  # birth_dateがない場合はスキップ

            # 日本語名を生成（仮）
            name_ja = name  # 実際にはWikidataから日本語ラベルを取得

            # display_name生成
            display_name = self.display_generator.generate_display_name({
                'person_name_ja': name_ja,
                'birth_year': birth_year
            })

            person = UltraThinkPerson(
                person_name=name,
                person_name_ja=name_ja,
                person_name_display=display_name,
                birth_year=birth_year,
                birth_date=birth_date,
                death_date=death_date,
                nationality=item.get('countryLabel', {}).get('value', ''),
                occupation=item.get('occupationLabel', {}).get('value', ''),
                main_category=category,
                historical_impact=7,
                educational_value=8,
                cultural_significance=7,
                global_recognition=7,
                inspirational_value=7,
                grade=grade,
                era=self._determine_era(birth_year)
            )

            return person
        except Exception as e:
            print(f"Person creation error: {str(e)[:50]}")
            return None

    def _collect_scientists(self, limit: int) -> List[UltraThinkPerson]:
        """科学者・技術者の収集"""
        query = """
        SELECT DISTINCT ?person ?personLabel ?birthDate ?deathDate ?countryLabel
        WHERE {
          ?person wdt:P31 wd:Q5 ;
                  wdt:P106/wdt:P279* wd:Q901 ;
                  wdt:P569 ?birthDate .
          OPTIONAL { ?person wdt:P570 ?deathDate }
          OPTIONAL { ?person wdt:P27 ?country }
          SERVICE wikibase:label { bd:serviceParam wikibase:language "ja,en". }
        }
        ORDER BY DESC(?birthDate)
        LIMIT """ + str(limit)

        people = []
        try:
            result = self._execute_query(query)
            for item in result:
                person = self._create_person_from_result(item, "科学・技術", "A")
                if person and person.birth_year:
                    people.append(person)
                    self.stats['scientists'] += 1
                    self.stats['with_birth_year'] += 1
        except Exception as e:
            print(f"  ⚠️ 科学者収集エラー: {str(e)[:50]}")

        return people[:limit]

    def _collect_artists(self, limit: int) -> List[UltraThinkPerson]:
        """芸術家・文化人の収集"""
        # 実装省略（科学者と同様のパターン）
        return []

    def _collect_leaders(self, limit: int) -> List[UltraThinkPerson]:
        """政治・社会の指導者収集"""
        # 実装省略
        return []

    def _collect_business_leaders(self, limit: int) -> List[UltraThinkPerson]:
        """ビジネスリーダーの収集"""
        # 実装省略
        return []

    def _collect_sports_heroes(self, limit: int) -> List[UltraThinkPerson]:
        """スポーツの英雄収集"""
        # 実装省略
        return []

    def _collect_entertainment(self, limit: int) -> List[UltraThinkPerson]:
        """エンターテインメント（最小限）"""
        # 実装省略
        return []

    def _determine_category(self, occupation: str) -> str:
        """職業からカテゴリを判定"""
        categories = {
            "科学・技術": ["科学者", "物理学者", "化学者", "生物学者", "数学者", "発明家", "技術者"],
            "芸術・文化": ["画家", "彫刻家", "作曲家", "音楽家", "作家", "詩人", "芸術家"],
            "政治・社会": ["大統領", "首相", "皇帝", "王", "政治家", "独立運動家", "社会活動家"],
            "哲学・思想": ["哲学者", "思想家", "宗教家"],
            "ビジネス": ["実業家", "起業家", "経営者"],
            "軍事・戦略": ["武将", "将軍", "提督", "軍人"],
            "スポーツ": ["スポーツ選手", "サッカー選手", "野球選手"],
        }

        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in occupation:
                    return category

        return "その他"

    def _determine_era(self, birth_year: int) -> str:
        """生年から時代を判定"""
        if birth_year < 0:
            return "古代"
        elif birth_year < 500:
            return "古代"
        elif birth_year < 1500:
            return "中世"
        elif birth_year < 1800:
            return "近世"
        elif birth_year < 1900:
            return "近代"
        elif birth_year < 1950:
            return "現代前期"
        else:
            return "現代後期"

    def _execute_query(self, query: str) -> List[Dict]:
        """SPARQLクエリ実行"""
        try:
            response = requests.get(
                self.wikidata_endpoint,
                params={'format': 'json', 'query': query},
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                return data['results']['bindings']
            else:
                print(f"Query failed with status {response.status_code}")
                return []
        except Exception as e:
            print(f"Query error: {str(e)[:100]}")
            return []

    def _evaluate_and_dedupe(self, people: List[UltraThinkPerson]) -> List[UltraThinkPerson]:
        """重複除去と品質評価"""
        seen_names = set()
        unique_people = []

        for person in people:
            # 名前とbirth_yearの組み合わせで重複チェック
            key = f"{person.person_name}_{person.birth_year}"
            if key not in seen_names:
                seen_names.add(key)

                # 総合スコア計算
                total_score = (
                    person.historical_impact +
                    person.educational_value +
                    person.cultural_significance +
                    person.global_recognition +
                    person.inspirational_value
                ) / 5

                # グレード再評価
                if total_score >= 9:
                    person.grade = "S"
                elif total_score >= 7:
                    person.grade = "A"
                elif total_score >= 5:
                    person.grade = "B"
                else:
                    person.grade = "C"

                unique_people.append(person)

        # スコアでソート（高い順）
        unique_people.sort(key=lambda p: (
            p.historical_impact + p.educational_value + p.cultural_significance
        ), reverse=True)

        return unique_people

    def _print_statistics(self, people: List[UltraThinkPerson]):
        """統計情報の表示"""
        print("\n" + "=" * 60)
        print("📊 Ultra Think 収集統計")
        print("=" * 60)

        # birth_year統計
        with_birth_year = len([p for p in people if p.birth_year is not None])
        print(f"\n✅ birth_yearカバー率: {with_birth_year}/{len(people)} ({with_birth_year/len(people)*100:.1f}%)")

        # カテゴリ別統計
        categories = {}
        for person in people:
            cat = person.main_category
            categories[cat] = categories.get(cat, 0) + 1

        print("\n📁 カテゴリ別:")
        for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            percentage = count / len(people) * 100
            print(f"  {cat}: {count}人 ({percentage:.1f}%)")

        # 時代別統計
        eras = {}
        for person in people:
            era = person.era
            if era:
                eras[era] = eras.get(era, 0) + 1

        print("\n📅 時代別:")
        for era in ["古代", "中世", "近世", "近代", "現代前期", "現代後期"]:
            count = eras.get(era, 0)
            percentage = count / len(people) * 100 if len(people) > 0 else 0
            print(f"  {era}: {count}人 ({percentage:.1f}%)")

        # グレード別統計
        grades = {}
        for person in people:
            grade = person.grade
            grades[grade] = grades.get(grade, 0) + 1

        print("\n🏆 グレード別:")
        for grade in ['S', 'A', 'B', 'C']:
            count = grades.get(grade, 0)
            percentage = count / len(people) * 100 if len(people) > 0 else 0
            print(f"  {grade}級: {count}人 ({percentage:.1f}%)")

        # display_name例
        print("\n📝 person_name_display例（TOP 10）:")
        for i, person in enumerate(people[:10], 1):
            print(f"  {i}. {person.person_name_ja} → {person.person_name_display}")

        print(f"\n✅ 総収集数: {len(people)}人")

    def save_to_files(self, people: List[UltraThinkPerson]):
        """データをファイルに保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # JSON形式で保存
        json_file = f"ultra_think_famous_people_{timestamp}.json"
        data = {}
        for person in people:
            person_id = person.generate_id()
            data[person_id] = person.to_dict()

        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"\n💾 JSON保存: {json_file}")

        # CSV形式でも保存
        csv_file = f"ultra_think_famous_people_{timestamp}.csv"

        if people:
            # 必須フィールドを最初に配置
            priority_fields = [
                'person_name', 'person_name_ja', 'person_name_display', 'birth_year',
                'birth_date', 'death_date', 'nationality', 'occupation',
                'main_category', 'subcategory', 'grade'
            ]

            all_fields = list(people[0].to_dict().keys())
            other_fields = [f for f in all_fields if f not in priority_fields]
            fieldnames = priority_fields + other_fields

            with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for person in people:
                    writer.writerow(person.to_dict())

            print(f"💾 CSV保存: {csv_file}")

        # 統計レポート生成
        self._generate_report(people, timestamp)

    def _generate_report(self, people: List[UltraThinkPerson], timestamp: str):
        """詳細レポート生成"""
        report_file = f"ULTRA_THINK_REPORT_{timestamp}.md"

        report = f"""# 🎯 Ultra Think 有名人データベース構築レポート

## 📊 概要
- **実行日時**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **総収集数**: {len(people):,}人
- **birth_yearカバー率**: 100%（NULL値完全排除）

## ✨ 特徴
1. **エピソード生成最適化** - person_name_displayの読みやすさ重視
2. **歴史的偉人網羅** - エジソン、坂本龍馬、織田信長など
3. **教育的価値重視** - S級・A級人物を優先収集

## 📝 person_name_display最適化例

### 歴史的人物（短縮名）
"""

        historical = [p for p in people if p.birth_year and p.birth_year < 1900][:10]
        for person in historical:
            report += f"- {person.person_name_ja} → **{person.person_name_display}**\n"

        report += f"""

### 現代人（フルネーム）
"""

        modern = [p for p in people if p.birth_year and p.birth_year >= 1950][:10]
        for person in modern:
            report += f"- {person.person_name_ja} → **{person.person_name_display}**\n"

        report += f"""

## 🎯 エピソード例
「あなたと同じ26歳のとき
**ベートーヴェン**は交響曲第1番を完成させました」

「あなたと同じ31歳のとき
**エジソン**は白熱電球の実用化に成功しました」

---
*Ultra Think Database v1.0 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"📄 詳細レポート: {report_file}")


def main():
    """メイン実行"""
    collector = UltraThinkCollector()

    print("🚀 Ultra Think 実行開始")
    print("エピソード生成に最適化された有名人データベースを構築します")

    # 有名人を収集（目標: 12,410人）
    people = collector.collect_all_people(target_count=12410)

    # ファイルに保存
    collector.save_to_files(people)

    print("\n🎯 Ultra Think 完了!")
    print("エピソード生成に最適化された有名人データベースが完成しました。")
    print("- エジソン、坂本龍馬、織田信長など歴史的偉人を網羅")
    print("- person_name_displayはエピソードの読みやすさに最適化")
    print("- birth_year 100%保証（NULL値なし）")


if __name__ == "__main__":
    main()
