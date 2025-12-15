#!/usr/bin/env python3
"""
Wikidata SPARQLクエリで有名人データを無料で収集
"""

import csv
import json
import time
from datetime import datetime

import requests


class WikidataSPARQLCollector:
    """Wikidata SPARQLエンドポイントから有名人データを収集"""

    def __init__(self):
        self.endpoint = "https://query.wikidata.org/sparql"
        self.headers = {
            'User-Agent': 'HourglassApp/1.0 (https://example.com/contact) Python/3.9',
            'Accept': 'application/sparql-results+json'
        }
        self.collected_people = []

    def execute_query(self, sparql_query):
        """SPARQLクエリを実行"""
        try:
            response = requests.get(
                self.endpoint,
                params={'query': sparql_query, 'format': 'json'},
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"エラー: {e}")
            return None

    def get_scientists(self, limit=500):
        """科学者・研究者を取得"""
        query = """
        SELECT DISTINCT ?person ?personLabel ?birthDate ?deathDate ?occupationLabel ?nationalityLabel ?description
        WHERE {
          ?person wdt:P31 wd:Q5 ;                    # 人間
                  wdt:P106 ?occupation ;             # 職業
                  wdt:P569 ?birthDate .               # 生年月日
          ?occupation wdt:P279* wd:Q901 .            # 科学者のサブクラス
          OPTIONAL { ?person wdt:P570 ?deathDate }   # 死亡日（オプション）
          OPTIONAL { ?person wdt:P27 ?nationality }  # 国籍
          OPTIONAL { ?person schema:description ?description FILTER(LANG(?description) = "ja") }
          SERVICE wikibase:label { bd:serviceParam wikibase:language "ja,en" }
        }
        ORDER BY DESC(?birthDate)
        LIMIT """ + str(limit)

        return self.execute_query(query)

    def get_nobel_laureates(self, limit=300):
        """ノーベル賞受賞者を取得"""
        query = """
        SELECT DISTINCT ?person ?personLabel ?birthDate ?deathDate ?awardLabel ?nationalityLabel ?description
        WHERE {
          ?person wdt:P31 wd:Q5 ;                    # 人間
                  wdt:P166 ?award ;                  # 受賞
                  wdt:P569 ?birthDate .               # 生年月日
          ?award wdt:P361* wd:Q7191 .                # ノーベル賞の一部
          OPTIONAL { ?person wdt:P570 ?deathDate }   # 死亡日
          OPTIONAL { ?person wdt:P27 ?nationality }  # 国籍
          OPTIONAL { ?person schema:description ?description FILTER(LANG(?description) = "ja") }
          SERVICE wikibase:label { bd:serviceParam wikibase:language "ja,en" }
        }
        ORDER BY DESC(?birthDate)
        LIMIT """ + str(limit)

        return self.execute_query(query)

    def get_athletes(self, limit=1000):
        """スポーツ選手を取得"""
        query = """
        SELECT DISTINCT ?person ?personLabel ?birthDate ?deathDate ?sportLabel ?nationalityLabel ?description
        WHERE {
          ?person wdt:P31 wd:Q5 ;                    # 人間
                  wdt:P106 wd:Q2066131 ;             # アスリート
                  wdt:P569 ?birthDate ;               # 生年月日
                  wdt:P641 ?sport .                   # スポーツ
          OPTIONAL { ?person wdt:P570 ?deathDate }   # 死亡日
          OPTIONAL { ?person wdt:P27 ?nationality }  # 国籍
          OPTIONAL { ?person schema:description ?description FILTER(LANG(?description) = "ja") }
          SERVICE wikibase:label { bd:serviceParam wikibase:language "ja,en" }
        }
        ORDER BY DESC(?birthDate)
        LIMIT """ + str(limit)

        return self.execute_query(query)

    def get_japanese_people(self, limit=1000):
        """日本人の有名人を取得"""
        query = """
        SELECT DISTINCT ?person ?personLabel ?birthDate ?deathDate ?occupationLabel ?description
        WHERE {
          ?person wdt:P31 wd:Q5 ;                    # 人間
                  wdt:P27 wd:Q17 ;                   # 日本国籍
                  wdt:P569 ?birthDate .               # 生年月日
          OPTIONAL { ?person wdt:P106 ?occupation }  # 職業
          OPTIONAL { ?person wdt:P570 ?deathDate }   # 死亡日
          OPTIONAL { ?person schema:description ?description FILTER(LANG(?description) = "ja") }

          # Wikipediaの記事がある人のみ（有名人の指標）
          ?article schema:about ?person ;
                   schema:isPartOf <https://ja.wikipedia.org/> .

          SERVICE wikibase:label { bd:serviceParam wikibase:language "ja,en" }
        }
        ORDER BY DESC(?birthDate)
        LIMIT """ + str(limit)

        return self.execute_query(query)

    def get_tech_entrepreneurs(self, limit=500):
        """テクノロジー起業家を取得"""
        query = """
        SELECT DISTINCT ?person ?personLabel ?birthDate ?deathDate ?companyLabel ?nationalityLabel ?description
        WHERE {
          ?person wdt:P31 wd:Q5 ;                    # 人間
                  wdt:P106 wd:Q131524 ;              # 起業家
                  wdt:P569 ?birthDate .               # 生年月日
          OPTIONAL { ?person wdt:P112 ?company }     # 設立した会社
          OPTIONAL { ?person wdt:P570 ?deathDate }   # 死亡日
          OPTIONAL { ?person wdt:P27 ?nationality }  # 国籍
          OPTIONAL { ?person schema:description ?description FILTER(LANG(?description) = "en") }

          # テクノロジー関連の職業も含む
          OPTIONAL {
            ?person wdt:P106 ?techOccupation .
            VALUES ?techOccupation { wd:Q82594 wd:Q170790 wd:Q183888 }  # プログラマー、数学者、ソフトウェア開発者
          }

          SERVICE wikibase:label { bd:serviceParam wikibase:language "ja,en" }
        }
        ORDER BY DESC(?birthDate)
        LIMIT """ + str(limit)

        return self.execute_query(query)

    def get_musicians(self, limit=1000):
        """音楽家を取得"""
        query = """
        SELECT DISTINCT ?person ?personLabel ?birthDate ?deathDate ?genreLabel ?nationalityLabel ?description
        WHERE {
          ?person wdt:P31 wd:Q5 ;                    # 人間
                  wdt:P106 ?occupation ;             # 職業
                  wdt:P569 ?birthDate .               # 生年月日
          ?occupation wdt:P279* wd:Q639669 .         # 音楽家のサブクラス
          OPTIONAL { ?person wdt:P136 ?genre }       # ジャンル
          OPTIONAL { ?person wdt:P570 ?deathDate }   # 死亡日
          OPTIONAL { ?person wdt:P27 ?nationality }  # 国籍
          OPTIONAL { ?person schema:description ?description FILTER(LANG(?description) = "ja") }
          SERVICE wikibase:label { bd:serviceParam wikibase:language "ja,en" }
        }
        ORDER BY DESC(?birthDate)
        LIMIT """ + str(limit)

        return self.execute_query(query)

    def get_actors(self, limit=800):
        """俳優・女優を取得"""
        query = """
        SELECT DISTINCT ?person ?personLabel ?birthDate ?deathDate ?nationalityLabel ?description
        WHERE {
          ?person wdt:P31 wd:Q5 ;                    # 人間
                  wdt:P106 ?occupation ;             # 職業
                  wdt:P569 ?birthDate .               # 生年月日
          VALUES ?occupation { wd:Q33999 wd:Q10800557 }  # 俳優、女優
          OPTIONAL { ?person wdt:P570 ?deathDate }   # 死亡日
          OPTIONAL { ?person wdt:P27 ?nationality }  # 国籍
          OPTIONAL { ?person schema:description ?description FILTER(LANG(?description) = "ja") }
          SERVICE wikibase:label { bd:serviceParam wikibase:language "ja,en" }
        }
        ORDER BY DESC(?birthDate)
        LIMIT """ + str(limit)

        return self.execute_query(query)

    def get_historical_figures(self, limit=500):
        """歴史的人物（独裁者、戦争犯罪者など）を取得"""
        query = """
        SELECT DISTINCT ?person ?personLabel ?birthDate ?deathDate ?occupationLabel ?nationalityLabel ?description
        WHERE {
          ?person wdt:P31 wd:Q5 ;                    # 人間
                  wdt:P569 ?birthDate .               # 生年月日

          # 独裁者、戦争犯罪者、政治家など
          { ?person wdt:P106 wd:Q30461 }             # 独裁者
          UNION { ?person wdt:P106 wd:Q2478141 }     # 戦争犯罪者
          UNION { ?person wdt:P106 wd:Q82955 }       # 政治家（歴史的）
          UNION { ?person wdt:P39 wd:Q30461 }        # 独裁者の地位

          OPTIONAL { ?person wdt:P570 ?deathDate }   # 死亡日
          OPTIONAL { ?person wdt:P27 ?nationality }  # 国籍
          OPTIONAL { ?person wdt:P106 ?occupation }  # 職業
          OPTIONAL { ?person schema:description ?description FILTER(LANG(?description) = "ja") }

          # 死亡している人物を優先（歴史的人物）
          FILTER(BOUND(?deathDate))

          SERVICE wikibase:label { bd:serviceParam wikibase:language "ja,en" }
        }
        ORDER BY DESC(?birthDate)
        LIMIT """ + str(limit)

        return self.execute_query(query)

    def process_results(self, results, category):
        """クエリ結果を処理してリストに追加"""
        if not results or 'results' not in results:
            return 0

        count = 0
        for binding in results['results']['bindings']:
            try:
                # データ抽出
                person_data = {
                    'id': binding.get('person', {}).get('value', '').split('/')[-1],
                    'name': binding.get('personLabel', {}).get('value', ''),
                    'name_ja': binding.get('personLabel', {}).get('value', ''),
                    'birth_year': self.extract_year(binding.get('birthDate', {}).get('value', '')),
                    'death_year': self.extract_year(binding.get('deathDate', {}).get('value', '')),
                    'nationality': binding.get('nationalityLabel', {}).get('value', ''),
                    'occupation': binding.get('occupationLabel', {}).get('value', category),
                    'main_category': category,
                    'subcategory': '',
                    'special_tags': 'Wikidata',
                    'source': 'Wikidata SPARQL',
                    'wikidata_id': binding.get('person', {}).get('value', '').split('/')[-1],
                    'description': binding.get('description', {}).get('value', ''),
                    'key_ages': ''
                }

                # 死亡年齢を計算
                if person_data['birth_year'] and person_data['death_year']:
                    try:
                        death_age = int(person_data['death_year']) - int(person_data['birth_year'])
                        person_data['death_age'] = str(death_age)
                    except:
                        person_data['death_age'] = ''
                else:
                    person_data['death_age'] = ''

                self.collected_people.append(person_data)
                count += 1

            except Exception as e:
                print(f"データ処理エラー: {e}")
                continue

        return count

    def extract_year(self, date_string):
        """日付文字列から年を抽出"""
        if not date_string:
            return ''
        try:
            # ISO 8601形式から年を抽出
            if 'T' in date_string:
                date_string = date_string.split('T')[0]
            if '-' in date_string:
                return date_string.split('-')[0]
            return date_string[:4] if len(date_string) >= 4 else ''
        except:
            return ''

    def collect_all_categories(self):
        """すべてのカテゴリからデータ収集"""
        print("🔍 Wikidata SPARQLでデータ収集開始...")

        categories = [
            ('科学者・研究者', self.get_scientists, 500),
            ('ノーベル賞受賞者', self.get_nobel_laureates, 300),
            ('スポーツ選手', self.get_athletes, 1000),
            ('日本の有名人', self.get_japanese_people, 1000),
            ('テクノロジー起業家', self.get_tech_entrepreneurs, 500),
            ('音楽家', self.get_musicians, 500),
            ('俳優・女優', self.get_actors, 500),
            ('歴史的人物', self.get_historical_figures, 300),
        ]

        total_collected = 0

        for category_name, query_func, limit in categories:
            print(f"\n📚 {category_name}を収集中（最大{limit}人）...")

            results = query_func(limit)
            count = self.process_results(results, category_name)

            total_collected += count
            print(f"  ✅ {count}人収集完了")

            # API負荷軽減のため少し待機
            time.sleep(2)

        print(f"\n🎯 合計 {total_collected}人のデータを収集しました")
        return total_collected

    def save_to_csv(self, filename=None):
        """収集したデータをCSVに保存"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"wikidata_people_{timestamp}.csv"

        with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
            fieldnames = [
                'id', 'name', 'name_ja', 'birth_year', 'death_year', 'death_age',
                'nationality', 'occupation', 'main_category', 'subcategory',
                'special_tags', 'source', 'wikidata_id', 'description', 'key_ages'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            writer.writerows(self.collected_people)

        print(f"💾 データを保存しました: {filename}")
        return filename

def main():
    """メイン処理"""
    collector = WikidataSPARQLCollector()

    # データ収集
    total = collector.collect_all_categories()

    # CSV保存
    output_file = collector.save_to_csv()

    print("\n✅ Wikidata収集完了！")
    print(f"📊 総収集人数: {total}人")
    print("💰 コスト: $0（完全無料）")

    return output_file

if __name__ == "__main__":
    main()
