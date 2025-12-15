#!/usr/bin/env python3
"""
バランスの取れた有名人データベース構築システム
歴史的偉人から現代の著名人まで、教育的価値の高い包括的なデータベースを構築
"""

import json
import requests
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import time
from dataclasses import dataclass, field, asdict
import hashlib

@dataclass
class BalancedPerson:
    """バランスの取れた人物データ"""
    name: str
    birth_date: str
    death_date: str = ""
    nationality: str = ""
    occupation: str = ""
    main_category: str = ""
    subcategory: str = ""
    wikidata_id: str = ""
    description: str = ""
    birth_year: Optional[int] = None

    # 評価スコア
    historical_impact: int = 0      # 歴史的影響力 (1-10)
    educational_value: int = 0      # 教育的価値 (1-10)
    cultural_significance: int = 0  # 文化的重要性 (1-10)
    global_recognition: int = 0     # 国際的認知度 (1-10)
    inspirational_value: int = 0    # インスピレーション価値 (1-10)

    # グレード
    grade: str = ""  # S, A, B, C (Dは廃止)
    era: str = ""    # 時代区分

    def to_dict(self) -> Dict:
        return asdict(self)

    def generate_id(self) -> str:
        text = f"{self.name}_{self.birth_date}"
        return f"person_{hashlib.md5(text.encode()).hexdigest()[:8]}"

class BalancedFamousPersonCollector:
    """バランスの取れた有名人収集システム"""

    def __init__(self):
        self.wikidata_endpoint = "https://query.wikidata.org/sparql"
        self.collected_people = {}
        self.stats = {
            'total_collected': 0,
            'historical_figures': 0,
            'scientists': 0,
            'artists': 0,
            'politicians': 0,
            'business': 0,
            'sports': 0,
            'entertainment': 0,
            'start_time': datetime.now()
        }

        # 必須収集リスト（最優先）
        self.essential_people = {
            # 世界の科学者・発明家
            "Thomas Edison": (1847, 1931, "アメリカ", "発明家", "エジソン"),
            "Albert Einstein": (1879, 1955, "ドイツ/アメリカ", "物理学者", "アインシュタイン"),
            "Isaac Newton": (1643, 1727, "イギリス", "物理学者", "ニュートン"),
            "Charles Darwin": (1809, 1882, "イギリス", "生物学者", "ダーウィン"),
            "Marie Curie": (1867, 1934, "ポーランド/フランス", "物理学者", "キュリー夫人"),
            "Galileo Galilei": (1564, 1642, "イタリア", "天文学者", "ガリレオ"),
            "Louis Pasteur": (1822, 1895, "フランス", "微生物学者", "パスツール"),
            "Alexander Fleming": (1881, 1955, "イギリス", "細菌学者", "フレミング"),
            "Nikola Tesla": (1856, 1943, "セルビア/アメリカ", "発明家", "テスラ"),

            # 日本の歴史的偉人
            "Oda Nobunaga": (1534, 1582, "日本", "武将", "織田信長"),
            "Toyotomi Hideyoshi": (1537, 1598, "日本", "武将", "豊臣秀吉"),
            "Tokugawa Ieyasu": (1543, 1616, "日本", "武将", "徳川家康"),
            "Sakamoto Ryoma": (1836, 1867, "日本", "志士", "坂本龍馬"),
            "Saigo Takamori": (1828, 1877, "日本", "政治家", "西郷隆盛"),
            "Fukuzawa Yukichi": (1835, 1901, "日本", "啓蒙思想家", "福沢諭吉"),
            "Noguchi Hideyo": (1876, 1928, "日本", "細菌学者", "野口英世"),
            "Kitasato Shibasaburo": (1853, 1931, "日本", "細菌学者", "北里柴三郎"),
            "Murasaki Shikibu": (973, 1014, "日本", "作家", "紫式部"),
            "Shotoku Taishi": (574, 622, "日本", "政治家", "聖徳太子"),
            "Kukai": (774, 835, "日本", "僧侶", "空海"),

            # 世界の政治家・指導者
            "Abraham Lincoln": (1809, 1865, "アメリカ", "大統領", "リンカーン"),
            "Winston Churchill": (1874, 1965, "イギリス", "首相", "チャーチル"),
            "Napoleon Bonaparte": (1769, 1821, "フランス", "皇帝", "ナポレオン"),
            "George Washington": (1732, 1799, "アメリカ", "大統領", "ワシントン"),
            "Nelson Mandela": (1918, 2013, "南アフリカ", "大統領", "マンデラ"),
            "Mahatma Gandhi": (1869, 1948, "インド", "独立運動家", "ガンジー"),
            "Martin Luther King Jr.": (1929, 1968, "アメリカ", "公民権運動家", "キング牧師"),

            # 芸術家・文化人
            "Leonardo da Vinci": (1452, 1519, "イタリア", "芸術家", "レオナルド・ダ・ヴィンチ"),
            "Michelangelo": (1475, 1564, "イタリア", "芸術家", "ミケランジェロ"),
            "Pablo Picasso": (1881, 1973, "スペイン", "画家", "ピカソ"),
            "Vincent van Gogh": (1853, 1890, "オランダ", "画家", "ゴッホ"),
            "Wolfgang Amadeus Mozart": (1756, 1791, "オーストリア", "作曲家", "モーツァルト"),
            "Ludwig van Beethoven": (1770, 1827, "ドイツ", "作曲家", "ベートーヴェン"),
            "Johann Sebastian Bach": (1685, 1750, "ドイツ", "作曲家", "バッハ"),
            "William Shakespeare": (1564, 1616, "イギリス", "劇作家", "シェイクスピア"),
            "Rembrandt": (1606, 1669, "オランダ", "画家", "レンブラント"),
            "Utagawa Hiroshige": (1797, 1858, "日本", "浮世絵師", "歌川広重"),
            "Katsushika Hokusai": (1760, 1849, "日本", "浮世絵師", "葛飾北斎"),

            # 哲学者・思想家
            "Socrates": (-469, -399, "ギリシャ", "哲学者", "ソクラテス"),
            "Plato": (-428, -348, "ギリシャ", "哲学者", "プラトン"),
            "Aristotle": (-384, -322, "ギリシャ", "哲学者", "アリストテレス"),
            "Confucius": (-551, -479, "中国", "思想家", "孔子"),
            "René Descartes": (1596, 1650, "フランス", "哲学者", "デカルト"),
            "Immanuel Kant": (1724, 1804, "ドイツ", "哲学者", "カント"),

            # 実業家
            "John D. Rockefeller": (1839, 1937, "アメリカ", "実業家", "ロックフェラー"),
            "Andrew Carnegie": (1835, 1919, "アメリカ", "実業家", "カーネギー"),
            "Henry Ford": (1863, 1947, "アメリカ", "実業家", "ヘンリー・フォード"),
        }

    def collect_all_people(self, target_count: int = 12410) -> List[BalancedPerson]:
        """バランスの取れた有名人収集"""
        print("🎯 バランスの取れた有名人データベース構築システム起動")
        print(f"📊 目標: {target_count}人（教育的価値重視）")
        print("=" * 60)

        all_people = []

        # Phase 1: 必須人物の収集（最優先）
        print("\n📌 Phase 1: 歴史的偉人の収集")
        essential = self._collect_essential_people()
        all_people.extend(essential)
        print(f"  ✅ {len(essential)}名の必須人物を収集")

        # Phase 2: ノーベル賞受賞者
        print("\n🏆 Phase 2: ノーベル賞受賞者")
        nobel_laureates = self._collect_nobel_laureates(500)
        all_people.extend(nobel_laureates)

        # Phase 3: 各時代の代表的人物
        print("\n📚 Phase 3: 時代別代表人物")
        historical = self._collect_historical_figures(2000)
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
        leaders = self._collect_leaders(1000)
        all_people.extend(leaders)

        # Phase 7: ビジネス・イノベーター
        print("\n💼 Phase 7: ビジネス・イノベーター")
        business = self._collect_business_leaders(1000)
        all_people.extend(business)

        # Phase 8: スポーツの英雄
        print("\n⚽ Phase 8: スポーツの英雄")
        sports = self._collect_sports_heroes(1000)
        all_people.extend(sports)

        # Phase 9: 現代の影響力ある人物（最小限）
        print("\n🌟 Phase 9: 現代の影響力ある人物")
        modern = self._collect_modern_influencers(1500)
        all_people.extend(modern)

        # 重複除去と品質評価
        unique_people = self._evaluate_and_dedupe(all_people)

        # 統計表示
        self._print_statistics(unique_people[:target_count])

        return unique_people[:target_count]

    def _collect_essential_people(self) -> List[BalancedPerson]:
        """必須人物の収集"""
        people = []

        for name, (birth, death, nationality, occupation, name_ja) in self.essential_people.items():
            person = BalancedPerson(
                name=name,
                birth_date=f"{birth:04d}-01-01" if birth > 0 else f"BC{abs(birth):04d}",
                death_date=f"{death:04d}-01-01" if death and death > 0 else "",
                nationality=nationality,
                occupation=occupation,
                main_category=self._determine_category(occupation),
                subcategory=occupation,
                birth_year=birth,
                historical_impact=10,
                educational_value=10,
                cultural_significance=9,
                global_recognition=10,
                inspirational_value=9,
                grade="S",
                era=self._determine_era(birth)
            )

            # 日本語名を追加
            person.description = f"{name_ja} - {occupation}"

            people.append(person)
            self.stats['historical_figures'] += 1

        return people

    def _collect_nobel_laureates(self, limit: int) -> List[BalancedPerson]:
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
                person = self._create_person_from_result(
                    item,
                    category="科学・学術",
                    grade="S",
                    historical_impact=9,
                    educational_value=10
                )
                if person:
                    people.append(person)
                    self.stats['scientists'] += 1
        except Exception as e:
            print(f"  ⚠️ ノーベル賞受賞者収集エラー: {str(e)[:50]}")

        return people[:limit]

    def _collect_historical_figures(self, limit: int) -> List[BalancedPerson]:
        """各時代の代表的人物を収集"""
        people = []

        # 時代別クエリ
        eras = [
            ("古代", "BC1000", "500", 300),
            ("中世", "500", "1500", 400),
            ("近世", "1500", "1800", 400),
            ("近代", "1800", "1900", 400),
            ("現代", "1900", "1950", 500)
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

              FILTER(?birthDate >= "{start_year}-01-01"^^xsd:dateTime &&
                     ?birthDate <= "{end_year}-12-31"^^xsd:dateTime)

              SERVICE wikibase:label {{ bd:serviceParam wikibase:language "ja,en". }}
            }}
            LIMIT {count}
            """

            try:
                result = self._execute_query(query)
                for item in result:
                    person = self._create_person_from_result(
                        item,
                        category="歴史的人物",
                        grade="A",
                        era=era_name
                    )
                    if person:
                        people.append(person)
                        self.stats['historical_figures'] += 1
            except Exception as e:
                print(f"  ⚠️ {era_name}収集エラー: {str(e)[:50]}")

        return people[:limit]

    def _determine_category(self, occupation: str) -> str:
        """職業からカテゴリを判定"""
        categories = {
            "科学": ["科学者", "物理学者", "化学者", "生物学者", "数学者", "発明家"],
            "芸術": ["画家", "彫刻家", "作曲家", "音楽家", "作家", "詩人"],
            "政治": ["大統領", "首相", "皇帝", "王", "政治家", "独立運動家"],
            "哲学": ["哲学者", "思想家"],
            "ビジネス": ["実業家", "起業家", "経営者"],
            "軍事": ["武将", "将軍", "提督"],
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

    def _create_person_from_result(self, item: Dict, category: str, grade: str,
                                  historical_impact: int = 7,
                                  educational_value: int = 8,
                                  era: str = "") -> Optional[BalancedPerson]:
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
                    if birth_date.startswith('BC'):
                        birth_year = -int(birth_date[2:6])
                    else:
                        birth_year = int(birth_date[:4])
                except:
                    pass

            person = BalancedPerson(
                name=name,
                birth_date=birth_date,
                death_date=death_date,
                nationality=item.get('countryLabel', {}).get('value', ''),
                occupation=item.get('occupationLabel', {}).get('value', ''),
                main_category=category,
                birth_year=birth_year,
                historical_impact=historical_impact,
                educational_value=educational_value,
                cultural_significance=7,
                global_recognition=7,
                inspirational_value=7,
                grade=grade,
                era=era or self._determine_era(birth_year) if birth_year else ""
            )

            return person
        except Exception as e:
            print(f"Person creation error: {str(e)[:50]}")
            return None

    def _collect_scientists(self, limit: int) -> List[BalancedPerson]:
        """科学者・技術者の収集"""
        # 実装省略（基本的にはSPARQLクエリで科学者を収集）
        return []

    def _collect_artists(self, limit: int) -> List[BalancedPerson]:
        """芸術家・文化人の収集"""
        # 実装省略
        return []

    def _collect_leaders(self, limit: int) -> List[BalancedPerson]:
        """政治・社会の指導者収集"""
        # 実装省略
        return []

    def _collect_business_leaders(self, limit: int) -> List[BalancedPerson]:
        """ビジネスリーダーの収集"""
        # 実装省略
        return []

    def _collect_sports_heroes(self, limit: int) -> List[BalancedPerson]:
        """スポーツの英雄収集"""
        # 実装省略
        return []

    def _collect_modern_influencers(self, limit: int) -> List[BalancedPerson]:
        """現代の影響力ある人物（最小限）"""
        # 実装省略
        return []

    def _evaluate_and_dedupe(self, people: List[BalancedPerson]) -> List[BalancedPerson]:
        """重複除去と品質評価"""
        seen_names = set()
        unique_people = []

        for person in people:
            if person.name not in seen_names:
                seen_names.add(person.name)

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

    def _print_statistics(self, people: List[BalancedPerson]):
        """統計情報の表示"""
        print("\n" + "=" * 60)
        print("📊 収集統計")
        print("=" * 60)

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
        for era, count in sorted(eras.items()):
            percentage = count / len(people) * 100
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

        print(f"\n✅ 総収集数: {len(people)}人")

    def save_to_files(self, people: List[BalancedPerson]):
        """データをファイルに保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # JSON形式で保存
        json_file = f"balanced_famous_people_{timestamp}.json"
        data = {}
        for person in people:
            person_id = person.generate_id()
            data[person_id] = person.to_dict()

        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"\n💾 保存完了: {json_file}")

        # CSV形式でも保存
        import csv
        csv_file = f"balanced_famous_people_{timestamp}.csv"

        if people:
            fieldnames = list(people[0].to_dict().keys())
            with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for person in people:
                    writer.writerow(person.to_dict())

            print(f"💾 CSV保存: {csv_file}")


def main():
    """メイン実行"""
    collector = BalancedFamousPersonCollector()

    # バランスの取れた有名人を収集
    people = collector.collect_all_people(target_count=12410)

    # ファイルに保存
    collector.save_to_files(people)

    print("\n🎯 バランスの取れた有名人データベース構築完了!")
    print("歴史的偉人から現代まで、教育的価値の高いデータベースが完成しました。")


if __name__ == "__main__":
    main()
