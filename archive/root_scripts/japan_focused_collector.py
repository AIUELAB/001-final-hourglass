#!/usr/bin/env python3
"""
日本人ユーザー価値最優先の有名人物収集システム
目標: 12,410人の価値ある人物を収集（地域バランス不要）
"""

import concurrent.futures
import hashlib
import json
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests


@dataclass
class JapanFocusedPerson:
    """日本人ユーザー向け人物データ"""
    name: str
    birth_date: str
    death_date: str = ""
    nationality: str = ""
    occupation: str = ""
    main_category: str = ""
    subcategory: str = ""
    wikidata_id: str = ""
    description: str = ""

    # 新規フィールド
    impact_score: int = 0  # 社会的インパクト・歴史的影響（1-10）
    japanese_relevance: int = 0  # 日本人への関連度（1-10）
    grade: str = ""  # A級～D級
    inspirational_points: List[str] = field(default_factory=list)
    target_age_groups: List[str] = field(default_factory=list)
    historical_lesson: str = ""  # D級のみ：歴史的教訓

    def to_dict(self) -> Dict:
        return asdict(self)

    def generate_id(self) -> str:
        text = f"{self.name}_{self.birth_date}"
        return hashlib.md5(text.encode()).hexdigest()[:16]

class JapanFocusedCollector:
    """日本人ユーザー価値最優先の収集システム"""

    def __init__(self):
        self.wikidata_endpoint = "https://query.wikidata.org/sparql"
        self.collected_people = {}
        self.stats = {
            'total_collected': 0,
            'japanese': 0,
            'american': 0,
            'korean': 0,
            'other': 0,
            'grade_a': 0,
            'grade_b': 0,
            'grade_c': 0,
            'grade_d': 0,
            'start_time': datetime.now()
        }

    def collect_all_people(self, target_count: int = 12410) -> List[JapanFocusedPerson]:
        """全カテゴリから日本人ユーザーに価値のある人物を収集"""
        print("🎯 日本人ユーザー価値最優先収集システム起動")
        print(f"📊 目標: {target_count}人（地域バランス不要）")
        print("=" * 60)

        all_people = []

        # 1. エンターテインメント（3,475人）- 日本人中心
        all_people.extend(self._collect_entertainment(3475))

        # 2. 文化・芸術（2,854人）- 日本文化重視
        all_people.extend(self._collect_culture_arts(2854))

        # 3. スポーツ（2,234人）- 日本人＋世界的スター
        all_people.extend(self._collect_sports(2234))

        # 4. ビジネス・テクノロジー（1,737人）
        all_people.extend(self._collect_business_tech(1737))

        # 5. 政治・社会（1,117人）
        all_people.extend(self._collect_politics_society(1117))

        # 6. 歴史的教訓（993人）- D級
        all_people.extend(self._collect_historical_lessons(993))

        # 重複除去と優先順位付け
        unique_people = self._prioritize_and_dedupe(all_people)

        # 統計表示
        self._print_statistics(unique_people[:target_count])

        return unique_people[:target_count]

    def _collect_entertainment(self, limit: int) -> List[JapanFocusedPerson]:
        """エンターテインメント収集（日本人中心）"""
        print(f"\n🎭 エンターテインメント収集（目標: {limit}人）")
        people = []

        # 日本のお笑い芸人（800人）
        queries = [
            ("日本のお笑い芸人", """
            SELECT DISTINCT ?person ?personLabel ?birthDate ?deathDate
            WHERE {
              ?person wdt:P31 wd:Q5 ;
                      wdt:P106 wd:Q245068 ;
                      wdt:P27 wd:Q17 ;
                      wdt:P569 ?birthDate .
              OPTIONAL { ?person wdt:P570 ?deathDate }
              SERVICE wikibase:label { bd:serviceParam wikibase:language "ja,en". }
            }
            LIMIT 800
            """, "A", ["明石家さんま", "ダウンタウン", "サンドウィッチマン"]),

            # 日本の俳優・女優（700人）
            ("日本の俳優", """
            SELECT DISTINCT ?person ?personLabel ?birthDate ?deathDate
            WHERE {
              ?person wdt:P31 wd:Q5 ;
                      wdt:P106 wd:Q33999 ;
                      wdt:P27 wd:Q17 ;
                      wdt:P569 ?birthDate .
              OPTIONAL { ?person wdt:P570 ?deathDate }
              SERVICE wikibase:label { bd:serviceParam wikibase:language "ja,en". }
            }
            LIMIT 700
            """, "A", ["新垣結衣", "佐藤健", "綾瀬はるか"]),

            # 日本のYouTuber（500人）
            ("YouTuber", """
            SELECT DISTINCT ?person ?personLabel ?birthDate
            WHERE {
              ?person wdt:P31 wd:Q5 ;
                      wdt:P106 wd:Q17125263 ;
                      wdt:P569 ?birthDate .
              ?person wdt:P27 wd:Q17 .
              SERVICE wikibase:label { bd:serviceParam wikibase:language "ja,en". }
            }
            LIMIT 500
            """, "A", ["HIKAKIN", "はじめしゃちょー", "Fischer's"]),

            # K-POPアーティスト（400人）- 日本で人気
            ("K-POP", """
            SELECT DISTINCT ?person ?personLabel ?birthDate
            WHERE {
              ?person wdt:P31 wd:Q5 ;
                      wdt:P106 wd:Q177220 ;
                      wdt:P27 wd:Q884 ;
                      wdt:P569 ?birthDate .
              SERVICE wikibase:label { bd:serviceParam wikibase:language "ja,ko,en". }
            }
            LIMIT 400
            """, "B", ["BTS", "BLACKPINK", "TWICE"]),

            # ハリウッドスター（300人）- 日本で知名度高い
            ("ハリウッド", """
            SELECT DISTINCT ?person ?personLabel ?birthDate ?deathDate
            WHERE {
              ?person wdt:P31 wd:Q5 ;
                      wdt:P106 wd:Q33999 ;
                      wdt:P27 wd:Q30 ;
                      wdt:P569 ?birthDate .
              OPTIONAL { ?person wdt:P570 ?deathDate }
              SERVICE wikibase:label { bd:serviceParam wikibase:language "ja,en". }
            }
            LIMIT 300
            """, "B", ["トム・クルーズ", "レオナルド・ディカプリオ"])
        ]

        for category, query, grade, examples in queries:
            try:
                result = self._execute_query(query)
                for item in result:
                    person = self._create_person(
                        item,
                        category="エンターテインメント",
                        subcategory=category,
                        grade=grade,
                        japanese_relevance=9 if "日本" in category else 7
                    )
                    if person:
                        people.append(person)
            except Exception as e:
                print(f"  ⚠️ {category}エラー: {str(e)[:50]}")

        # 声優（275人）
        people.extend(self._collect_voice_actors(275))

        return people[:limit]

    def _collect_culture_arts(self, limit: int) -> List[JapanFocusedPerson]:
        """文化・芸術収集（日本文化重視）"""
        print(f"\n🎨 文化・芸術収集（目標: {limit}人）")
        people = []

        queries = [
            # 漫画家（750人）
            ("漫画家", """
            SELECT DISTINCT ?person ?personLabel ?birthDate ?deathDate
            WHERE {
              ?person wdt:P31 wd:Q5 ;
                      wdt:P106 wd:Q3658341 ;
                      wdt:P27 wd:Q17 ;
                      wdt:P569 ?birthDate .
              OPTIONAL { ?person wdt:P570 ?deathDate }
              SERVICE wikibase:label { bd:serviceParam wikibase:language "ja,en". }
            }
            LIMIT 750
            """, "A", ["尾田栄一郎", "鳥山明", "諫山創"]),

            # 作家・小説家（550人）
            ("作家", """
            SELECT DISTINCT ?person ?personLabel ?birthDate ?deathDate
            WHERE {
              ?person wdt:P31 wd:Q5 ;
                      wdt:P106 wd:Q36180 ;
                      wdt:P27 wd:Q17 ;
                      wdt:P569 ?birthDate .
              OPTIONAL { ?person wdt:P570 ?deathDate }
              SERVICE wikibase:label { bd:serviceParam wikibase:language "ja,en". }
            }
            LIMIT 550
            """, "A", ["村上春樹", "東野圭吾", "宮部みゆき"]),

            # アニメ監督（450人）
            ("アニメ監督", """
            SELECT DISTINCT ?person ?personLabel ?birthDate ?deathDate
            WHERE {
              ?person wdt:P31 wd:Q5 ;
                      wdt:P106 wd:Q2526255 ;
                      wdt:P27 wd:Q17 ;
                      wdt:P569 ?birthDate .
              OPTIONAL { ?person wdt:P570 ?deathDate }
              SERVICE wikibase:label { bd:serviceParam wikibase:language "ja,en". }
            }
            LIMIT 450
            """, "A", ["宮崎駿", "新海誠", "細田守"]),

            # ゲームクリエイター（350人）
            ("ゲームクリエイター", """
            SELECT DISTINCT ?person ?personLabel ?birthDate
            WHERE {
              ?person wdt:P31 wd:Q5 ;
                      wdt:P106 wd:Q4618975 ;
                      wdt:P569 ?birthDate .
              ?person wdt:P27 wd:Q17 .
              SERVICE wikibase:label { bd:serviceParam wikibase:language "ja,en". }
            }
            LIMIT 350
            """, "A", ["宮本茂", "小島秀夫", "堀井雄二"])
        ]

        for category, query, grade, examples in queries:
            try:
                result = self._execute_query(query)
                for item in result:
                    person = self._create_person(
                        item,
                        category="文化・芸術",
                        subcategory=category,
                        grade=grade,
                        japanese_relevance=10
                    )
                    if person:
                        people.append(person)
            except Exception as e:
                print(f"  ⚠️ {category}エラー: {str(e)[:50]}")

        # その他の芸術家（754人）
        people.extend(self._collect_other_artists(754))

        return people[:limit]

    def _collect_sports(self, limit: int) -> List[JapanFocusedPerson]:
        """スポーツ選手収集（日本人＋世界的スター）"""
        print(f"\n⚽ スポーツ収集（目標: {limit}人）")
        people = []

        # 日本人選手（1,000人）
        japanese_sports = [
            ("野球選手", "wd:Q10871364", 400),
            ("サッカー選手", "wd:Q937857", 300),
            ("相撲力士", "wd:Q4886741", 100),
            ("柔道家", "wd:Q6665249", 100),
            ("フィギュアスケート", "wd:Q13219587", 100)
        ]

        for sport, wikidata_id, count in japanese_sports:
            query = f"""
            SELECT DISTINCT ?person ?personLabel ?birthDate ?deathDate
            WHERE {{
              ?person wdt:P31 wd:Q5 ;
                      wdt:P106 {wikidata_id} ;
                      wdt:P27 wd:Q17 ;
                      wdt:P569 ?birthDate .
              OPTIONAL {{ ?person wdt:P570 ?deathDate }}
              SERVICE wikibase:label {{ bd:serviceParam wikibase:language "ja,en". }}
            }}
            LIMIT {count}
            """

            try:
                result = self._execute_query(query)
                for item in result:
                    person = self._create_person(
                        item,
                        category="スポーツ",
                        subcategory=sport,
                        grade="A",
                        japanese_relevance=10
                    )
                    if person:
                        people.append(person)
            except Exception as e:
                print(f"  ⚠️ {sport}エラー: {str(e)[:50]}")

        # 世界的スター（1,234人）
        world_stars = self._collect_world_sports_stars(1234)
        people.extend(world_stars)

        return people[:limit]

    def _collect_business_tech(self, limit: int) -> List[JapanFocusedPerson]:
        """ビジネス・テクノロジー収集"""
        print(f"\n💼 ビジネス・テクノロジー収集（目標: {limit}人）")
        people = []

        # 日本の起業家（700人）
        query_jp_entrepreneur = """
        SELECT DISTINCT ?person ?personLabel ?birthDate ?deathDate
        WHERE {
          ?person wdt:P31 wd:Q5 ;
                  wdt:P106 wd:Q131524 ;
                  wdt:P27 wd:Q17 ;
                  wdt:P569 ?birthDate .
          OPTIONAL { ?person wdt:P570 ?deathDate }
          SERVICE wikibase:label { bd:serviceParam wikibase:language "ja,en". }
        }
        LIMIT 700
        """

        # シリコンバレー起業家（500人）
        query_sv_entrepreneur = """
        SELECT DISTINCT ?person ?personLabel ?birthDate ?deathDate
        WHERE {
          ?person wdt:P31 wd:Q5 ;
                  wdt:P106 wd:Q131524 ;
                  wdt:P27 wd:Q30 ;
                  wdt:P569 ?birthDate .
          OPTIONAL { ?person wdt:P570 ?deathDate }
          SERVICE wikibase:label { bd:serviceParam wikibase:language "ja,en". }
        }
        LIMIT 500
        """

        for query, relevance, grade in [
            (query_jp_entrepreneur, 10, "A"),
            (query_sv_entrepreneur, 8, "B")
        ]:
            try:
                result = self._execute_query(query)
                for item in result:
                    person = self._create_person(
                        item,
                        category="ビジネス・テクノロジー",
                        subcategory="起業家",
                        grade=grade,
                        japanese_relevance=relevance
                    )
                    if person:
                        people.append(person)
            except Exception as e:
                print(f"  ⚠️ 起業家エラー: {str(e)[:50]}")

        # その他のビジネス・テクノロジー（537人）
        people.extend(self._collect_other_business_tech(537))

        return people[:limit]

    def _collect_politics_society(self, limit: int) -> List[JapanFocusedPerson]:
        """政治・社会収集（日本に関係ある人物のみ）"""
        print(f"\n🏛️ 政治・社会収集（目標: {limit}人）")
        people = []

        # 日本の政治家・活動家（600人）
        query_jp_politics = """
        SELECT DISTINCT ?person ?personLabel ?birthDate ?deathDate
        WHERE {
          ?person wdt:P31 wd:Q5 ;
                  wdt:P106 wd:Q82955 ;
                  wdt:P27 wd:Q17 ;
                  wdt:P569 ?birthDate .
          OPTIONAL { ?person wdt:P570 ?deathDate }
          SERVICE wikibase:label { bd:serviceParam wikibase:language "ja,en". }
        }
        LIMIT 600
        """

        try:
            result = self._execute_query(query_jp_politics)
            for item in result:
                person = self._create_person(
                    item,
                    category="政治・社会",
                    subcategory="政治家",
                    grade="B",
                    japanese_relevance=9
                )
                if person:
                    people.append(person)
        except Exception as e:
            print(f"  ⚠️ 政治家エラー: {str(e)[:50]}")

        # 国際的活動家（日本で知られている）（517人）
        people.extend(self._collect_international_activists(517))

        return people[:limit]

    def _collect_historical_lessons(self, limit: int) -> List[JapanFocusedPerson]:
        """歴史的教訓（D級）収集 - 反面教師"""
        print(f"\n⚠️ 歴史的教訓収集（目標: {limit}人）")
        people = []

        # 独裁者・戦争犯罪者（200人）
        dictators = [
            ("アドルフ・ヒトラー", "1889-04-20", "1945-04-30", "ドイツ",
             "第二次世界大戦とホロコーストの首謀者", 10),
            ("ヨシフ・スターリン", "1878-12-18", "1953-03-05", "ソ連",
             "大粛清による数百万人の犠牲者", 9),
            ("ポル・ポト", "1925-05-19", "1998-04-15", "カンボジア",
             "カンボジア大虐殺（200万人死亡）", 8),
            ("毛沢東", "1893-12-26", "1976-09-09", "中国",
             "文化大革命による大量の犠牲者", 9)
        ]

        for name, birth, death, nationality, lesson, impact in dictators:
            person = JapanFocusedPerson(
                name=name,
                birth_date=birth,
                death_date=death,
                nationality=nationality,
                occupation="独裁者",
                main_category="歴史的教訓",
                subcategory="独裁者・戦争犯罪者",
                grade="D",
                impact_score=impact,
                japanese_relevance=7,
                historical_lesson=lesson
            )
            people.append(person)

        # テロリスト（150人）
        terrorists = [
            ("麻原彰晃", "1955-03-02", "2018-07-06", "日本",
             "地下鉄サリン事件の首謀者", 10),
            ("オサマ・ビン・ラディン", "1957-03-10", "2011-05-02", "サウジアラビア",
             "9.11同時多発テロの首謀者", 9)
        ]

        for name, birth, death, nationality, lesson, impact in terrorists:
            person = JapanFocusedPerson(
                name=name,
                birth_date=birth,
                death_date=death,
                nationality=nationality,
                occupation="テロリスト",
                main_category="歴史的教訓",
                subcategory="テロリスト・過激派",
                grade="D",
                impact_score=impact,
                japanese_relevance=10 if nationality == "日本" else 7,
                historical_lesson=lesson
            )
            people.append(person)

        # 重大犯罪者（200人）
        criminals = self._collect_major_criminals(200)
        people.extend(criminals)

        # 転落した成功者（200人）
        fallen_success = [
            ("堀江貴文", "1972-10-29", "", "日本",
             "ライブドア事件（証券取引法違反）から復活", 8),
            ("カルロス・ゴーン", "1954-03-09", "", "ブラジル",
             "日産再建後、金融商品取引法違反で逮捕・逃亡", 9)
        ]

        for name, birth, death, nationality, lesson, impact in fallen_success:
            person = JapanFocusedPerson(
                name=name,
                birth_date=birth,
                death_date=death,
                nationality=nationality,
                occupation="元経営者",
                main_category="歴史的教訓",
                subcategory="転落した成功者",
                grade="D",
                impact_score=impact,
                japanese_relevance=9,
                historical_lesson=lesson
            )
            people.append(person)

        # カルト教祖（100人）
        cult_leaders = self._collect_cult_leaders(100)
        people.extend(cult_leaders)

        # 歴史的失敗者（143人）
        historical_failures = self._collect_historical_failures(143)
        people.extend(historical_failures)

        return people[:limit]

    def _execute_query(self, query: str) -> List[Dict]:
        """SPARQLクエリ実行"""
        try:
            response = requests.get(
                self.wikidata_endpoint,
                params={'query': query, 'format': 'json'},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                return data['results']['bindings']
        except Exception as e:
            print(f"    クエリエラー: {str(e)[:50]}")
        return []

    def _create_person(self, item: Dict, category: str, subcategory: str,
                      grade: str, japanese_relevance: int) -> Optional[JapanFocusedPerson]:
        """人物データ作成"""
        try:
            name = item.get('personLabel', {}).get('value', '')
            if not name or name.startswith('Q'):
                return None

            birth_date = item.get('birthDate', {}).get('value', '')[:10]
            if not birth_date:
                return None

            # 日本人価値判定
            if not self._is_valuable_to_japanese(name, category):
                return None

            person = JapanFocusedPerson(
                name=name,
                birth_date=birth_date,
                death_date=item.get('deathDate', {}).get('value', '')[:10],
                nationality=item.get('nationalityLabel', {}).get('value', ''),
                occupation=subcategory,
                main_category=category,
                subcategory=subcategory,
                wikidata_id=item.get('person', {}).get('value', '').split('/')[-1],
                grade=grade,
                japanese_relevance=japanese_relevance,
                impact_score=self._calculate_impact_score(name, category)
            )

            # 感銘ポイント設定
            person.inspirational_points = self._get_inspirational_points(name, category)
            person.target_age_groups = self._get_target_age_groups(birth_date)

            return person

        except Exception as e:
            return None

    def _is_valuable_to_japanese(self, name: str, category: str) -> bool:
        """日本人ユーザーにとって価値があるか判定"""
        # 日本語名前チェック
        if self._is_japanese_name(name):
            return True

        # 世界的に有名な人物リスト（一部）
        global_stars = [
            "Michael Jackson", "Madonna", "Lady Gaga", "Taylor Swift",
            "Cristiano Ronaldo", "Lionel Messi", "LeBron James",
            "Steve Jobs", "Elon Musk", "Bill Gates", "Mark Zuckerberg",
            "BTS", "BLACKPINK", "PSY"
        ]

        for star in global_stars:
            if star.lower() in name.lower():
                return True

        # カテゴリ別判定
        if category == "エンターテインメント":
            # K-POP、ハリウッドは一定の知名度があれば含める
            return True
        elif category == "歴史的教訓":
            # 教訓として重要なら含める
            return True

        # デフォルトは除外
        return False

    def _is_japanese_name(self, name: str) -> bool:
        """日本人名判定"""
        # ひらがな、カタカナ、漢字を含むか
        japanese_pattern = re.compile(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]')
        return bool(japanese_pattern.search(name))

    def _calculate_impact_score(self, name: str, category: str) -> int:
        """社会的インパクト・歴史的影響スコア計算"""
        # 簡易的なスコア計算（実際はより詳細な判定が必要）
        if category == "歴史的教訓":
            return 9
        elif "日本" in name or self._is_japanese_name(name):
            return 8
        elif category in ["エンターテインメント", "スポーツ"]:
            return 7
        else:
            return 6

    def _get_inspirational_points(self, name: str, category: str) -> List[str]:
        """感銘ポイント取得"""
        points = []

        if category == "エンターテインメント":
            points.append("エンターテインメントで人々を楽しませる")
            points.append("夢を追い続ける姿勢")
        elif category == "スポーツ":
            points.append("限界に挑戦し続ける姿勢")
            points.append("努力と継続の重要性")
        elif category == "ビジネス・テクノロジー":
            points.append("イノベーションで世界を変える")
            points.append("起業家精神の体現")
        elif category == "歴史的教訓":
            points.append("歴史から学ぶ重要性")
            points.append("同じ過ちを繰り返さない教訓")

        return points

    def _get_target_age_groups(self, birth_date: str) -> List[str]:
        """ターゲット年齢層判定"""
        try:
            birth_year = int(birth_date[:4])
            current_year = datetime.now().year
            age = current_year - birth_year

            if age < 30:
                return ["10代", "20代"]
            elif age < 50:
                return ["20代", "30代", "40代"]
            elif age < 70:
                return ["30代", "40代", "50代"]
            else:
                return ["40代", "50代", "60代以上"]
        except:
            return ["全世代"]

    def _collect_voice_actors(self, limit: int) -> List[JapanFocusedPerson]:
        """声優収集"""
        people = []
        # 実装省略（実際は声優データを収集）
        return people

    def _collect_other_artists(self, limit: int) -> List[JapanFocusedPerson]:
        """その他芸術家収集"""
        people = []
        # 実装省略
        return people

    def _collect_world_sports_stars(self, limit: int) -> List[JapanFocusedPerson]:
        """世界的スポーツスター収集"""
        people = []
        # 実装省略
        return people

    def _collect_other_business_tech(self, limit: int) -> List[JapanFocusedPerson]:
        """その他ビジネス・テクノロジー収集"""
        people = []
        # 実装省略
        return people

    def _collect_international_activists(self, limit: int) -> List[JapanFocusedPerson]:
        """国際的活動家収集"""
        people = []
        # 実装省略
        return people

    def _collect_major_criminals(self, limit: int) -> List[JapanFocusedPerson]:
        """重大犯罪者収集"""
        people = []
        # 実装省略
        return people

    def _collect_cult_leaders(self, limit: int) -> List[JapanFocusedPerson]:
        """カルト教祖収集"""
        people = []
        # 実装省略
        return people

    def _collect_historical_failures(self, limit: int) -> List[JapanFocusedPerson]:
        """歴史的失敗者収集"""
        people = []
        # 実装省略
        return people

    def _prioritize_and_dedupe(self, people: List[JapanFocusedPerson]) -> List[JapanFocusedPerson]:
        """優先順位付けと重複除去"""
        # 重複除去
        unique = {}
        for person in people:
            person_id = person.generate_id()
            if person_id not in unique:
                unique[person_id] = person

        # 優先順位でソート
        sorted_people = sorted(
            unique.values(),
            key=lambda p: (
                -p.japanese_relevance,  # 日本人関連度
                -p.impact_score,  # 社会的インパクト
                p.grade  # グレード（A > B > C > D）
            )
        )

        return sorted_people

    def _print_statistics(self, people: List[JapanFocusedPerson]):
        """統計表示"""
        elapsed = (datetime.now() - self.stats['start_time']).total_seconds()

        print("\n" + "=" * 60)
        print("📊 収集統計（日本人ユーザー価値最優先）")
        print("=" * 60)
        print(f"✅ 総収集数: {len(people)}人")
        print(f"⏱️ 処理時間: {elapsed:.1f}秒")

        # カテゴリ分布
        categories = {}
        for person in people:
            cat = person.main_category
            categories[cat] = categories.get(cat, 0) + 1

        print("\n📈 カテゴリ分布:")
        for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / len(people)) * 100
            print(f"  {cat:20} {count:5}人 ({percentage:5.1f}%)")

        # グレード分布
        grades = {"A": 0, "B": 0, "C": 0, "D": 0}
        for person in people:
            if person.grade in grades:
                grades[person.grade] += 1

        print("\n⭐ グレード分布:")
        for grade, count in sorted(grades.items()):
            percentage = (count / len(people)) * 100 if len(people) > 0 else 0
            print(f"  {grade}級: {count:5}人 ({percentage:5.1f}%)")

        # 国籍分布（上位10）
        nationalities = {}
        for person in people:
            nat = person.nationality or "不明"
            nationalities[nat] = nationalities.get(nat, 0) + 1

        print("\n🌍 国籍分布（上位10）:")
        for nat, count in sorted(nationalities.items(), key=lambda x: x[1], reverse=True)[:10]:
            percentage = (count / len(people)) * 100
            print(f"  {nat:15} {count:5}人 ({percentage:5.1f}%)")

        # 日本人関連度の平均
        avg_relevance = sum(p.japanese_relevance for p in people) / len(people) if people else 0
        print(f"\n🎌 日本人関連度平均: {avg_relevance:.1f}/10")

    def export_to_csv(self, people: List[JapanFocusedPerson], filename: str):
        """CSVエクスポート"""
        df = pd.DataFrame([p.to_dict() for p in people])
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"\n📄 CSVエクスポート完了: {filename}")

    def export_to_firebase(self, people: List[JapanFocusedPerson], filename: str):
        """Firebase用JSONエクスポート"""
        firebase_data = []

        for person in people:
            firebase_person = {
                'id': person.generate_id(),
                'name': person.name,
                'birthDate': person.birth_date,
                'deathDate': person.death_date,
                'nationality': person.nationality,
                'occupation': person.occupation,
                'mainCategory': person.main_category,
                'subcategory': person.subcategory,
                'wikidataId': person.wikidata_id,
                'description': person.description,
                'grade': person.grade,
                'impactScore': person.impact_score,
                'japaneseRelevance': person.japanese_relevance,
                'inspirationalPoints': person.inspirational_points,
                'targetAgeGroups': person.target_age_groups,
                'historicalLesson': person.historical_lesson,
                'createdAt': datetime.now().isoformat()
            }
            firebase_data.append(firebase_person)

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(firebase_data, f, ensure_ascii=False, indent=2)

        print(f"📱 Firebase JSONエクスポート完了: {filename}")

def main():
    """メイン処理"""
    print("=" * 60)
    print("🎌 日本人ユーザー価値最優先収集システム")
    print("📋 選定基準: 日本人に響く人物のみ")
    print("🌍 地域バランス: 不要（価値のみ重視）")
    print("=" * 60)

    collector = JapanFocusedCollector()

    # デモ版: 1,000人収集（フル版は12,410人）
    people = collector.collect_all_people(target_count=1000)

    # エクスポート
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # CSV
    csv_filename = f"japan_focused_people_{timestamp}.csv"
    collector.export_to_csv(people, csv_filename)

    # Firebase JSON
    json_filename = f"japan_focused_firebase_{timestamp}.json"
    collector.export_to_firebase(people, json_filename)

    print("\n" + "=" * 60)
    print("✅ 収集完了！")
    print(f"  人数: {len(people)}人")
    print("  基準: 日本人ユーザー価値最優先")
    print("  特徴: 地域バランス不要、価値のみ重視")
    print("=" * 60)

if __name__ == "__main__":
    main()
