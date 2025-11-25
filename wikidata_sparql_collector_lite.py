#!/usr/bin/env python3
"""
Wikidata SPARQLクエリで有名人データを無料で収集（軽量版）
"""

import csv
import json
import time
from datetime import datetime

import requests


class WikidataSPARQLCollectorLite:
    """Wikidata SPARQLエンドポイントから有名人データを収集（軽量版）"""

    def __init__(self):
        self.endpoint = "https://query.wikidata.org/sparql"
        self.headers = {
            'User-Agent': 'HourglassApp/1.0 Python/3.9',
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

    def get_recent_japanese_people(self, limit=100):
        """最近の日本人有名人を取得（シンプルなクエリ）"""
        query = """
        SELECT DISTINCT ?person ?personLabel ?birthDate ?deathDate ?occupationLabel
        WHERE {
          ?person wdt:P31 wd:Q5 ;                    # 人間
                  wdt:P27 wd:Q17 ;                   # 日本国籍
                  wdt:P569 ?birthDate .               # 生年月日
          FILTER(YEAR(?birthDate) > 1950)            # 1950年以降生まれ
          OPTIONAL { ?person wdt:P106 ?occupation }  # 職業
          OPTIONAL { ?person wdt:P570 ?deathDate }   # 死亡日
          SERVICE wikibase:label { bd:serviceParam wikibase:language "ja,en" }
        }
        ORDER BY DESC(?birthDate)
        LIMIT """ + str(limit)

        return self.execute_query(query)

    def get_simple_athletes(self, limit=100):
        """スポーツ選手を取得（シンプル版）"""
        query = """
        SELECT DISTINCT ?person ?personLabel ?birthDate ?nationalityLabel
        WHERE {
          ?person wdt:P31 wd:Q5 ;                    # 人間
                  wdt:P106 wd:Q2066131 ;             # アスリート
                  wdt:P569 ?birthDate .               # 生年月日
          FILTER(YEAR(?birthDate) > 1970)            # 1970年以降生まれ
          OPTIONAL { ?person wdt:P27 ?nationality }  # 国籍
          SERVICE wikibase:label { bd:serviceParam wikibase:language "ja,en" }
        }
        ORDER BY DESC(?birthDate)
        LIMIT """ + str(limit)

        return self.execute_query(query)

    def get_simple_musicians(self, limit=100):
        """音楽家を取得（シンプル版）"""
        query = """
        SELECT DISTINCT ?person ?personLabel ?birthDate ?nationalityLabel
        WHERE {
          ?person wdt:P31 wd:Q5 ;                    # 人間
                  wdt:P106 wd:Q639669 ;              # 音楽家
                  wdt:P569 ?birthDate .               # 生年月日
          FILTER(YEAR(?birthDate) > 1960)            # 1960年以降生まれ
          OPTIONAL { ?person wdt:P27 ?nationality }  # 国籍
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
                    'description': '',
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

    def collect_sample_data(self):
        """サンプルデータを収集（軽量版）"""
        print("🔍 Wikidata SPARQL軽量版でデータ収集開始...")

        categories = [
            ('日本の有名人', self.get_recent_japanese_people, 100),
            ('スポーツ選手', self.get_simple_athletes, 100),
            ('音楽家', self.get_simple_musicians, 100),
        ]

        total_collected = 0

        for category_name, query_func, limit in categories:
            print(f"\n📚 {category_name}を収集中（最大{limit}人）...")

            results = query_func(limit)
            count = self.process_results(results, category_name)

            total_collected += count
            print(f"  ✅ {count}人収集完了")

            # API負荷軽減のため少し待機
            time.sleep(1)

        print(f"\n🎯 合計 {total_collected}人のデータを収集しました")
        return total_collected

    def save_to_csv(self, filename=None):
        """収集したデータをCSVに保存"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"wikidata_lite_{timestamp}.csv"

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
    collector = WikidataSPARQLCollectorLite()

    # データ収集
    total = collector.collect_sample_data()

    # CSV保存
    output_file = collector.save_to_csv()

    print("\n✅ Wikidata収集完了！")
    print(f"📊 総収集人数: {total}人")
    print("💰 コスト: $0（完全無料）")

    # より多くのデータが必要な場合の説明
    print("\n💡 ヒント:")
    print("  - クエリのLIMITを増やすとより多くのデータを取得できます")
    print("  - カテゴリを追加して様々な分野の人物を収集できます")
    print("  - バッチ処理で段階的に収集することも可能です")

    return output_file

if __name__ == "__main__":
    main()
