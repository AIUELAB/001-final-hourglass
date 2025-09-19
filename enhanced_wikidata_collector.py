#!/usr/bin/env python3
"""
Enhanced Wikidata Collector - エンターテインメント重視の追加収集
"""

import csv
import json
import time
from datetime import datetime

import pandas as pd
import requests


class EnhancedWikidataCollector:
    def __init__(self):
        self.endpoint = "https://query.wikidata.org/sparql"
        self.headers = {
            'User-Agent': 'HourglassApp/1.0 Python/3.9',
            'Accept': 'application/sparql-results+json'
        }
        self.collected_people = []
        
    def execute_query(self, sparql_query, retry=3):
        """SPARQLクエリを実行（リトライ付き）"""
        for attempt in range(retry):
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
                print(f"エラー (試行 {attempt+1}/{retry}): {e}")
                if attempt < retry - 1:
                    time.sleep(2)
        return None
    
    def get_entertainers(self, limit=800):
        """エンターテイナー（俳優、歌手、芸人）を取得"""
        query = f"""
        SELECT DISTINCT ?person ?personLabel ?birthDate ?deathDate ?occupationLabel ?nationalityLabel
        WHERE {{
          ?person wdt:P31 wd:Q5 ;
                  wdt:P106 ?occupation .
          ?occupation wdt:P279* wd:Q488111 .  # 芸能人のサブクラス
          OPTIONAL {{ ?person wdt:P569 ?birthDate }}
          OPTIONAL {{ ?person wdt:P570 ?deathDate }}
          OPTIONAL {{ ?person wdt:P27 ?nationality }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "ja,en" }}
        }}
        ORDER BY DESC(?birthDate)
        LIMIT {limit}
        """
        return self.execute_query(query)
    
    def get_actors(self, limit=600):
        """俳優を取得"""
        query = f"""
        SELECT DISTINCT ?person ?personLabel ?birthDate ?deathDate ?nationalityLabel
        WHERE {{
          ?person wdt:P31 wd:Q5 ;
                  wdt:P106 wd:Q33999 .  # 俳優
          OPTIONAL {{ ?person wdt:P569 ?birthDate }}
          OPTIONAL {{ ?person wdt:P570 ?deathDate }}
          OPTIONAL {{ ?person wdt:P27 ?nationality }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "ja,en" }}
        }}
        ORDER BY DESC(?birthDate)
        LIMIT {limit}
        """
        return self.execute_query(query)
    
    def get_musicians(self, limit=600):
        """音楽家・歌手を取得"""
        query = f"""
        SELECT DISTINCT ?person ?personLabel ?birthDate ?deathDate ?nationalityLabel
        WHERE {{
          ?person wdt:P31 wd:Q5 ;
                  wdt:P106 wd:Q639669 .  # 音楽家
          OPTIONAL {{ ?person wdt:P569 ?birthDate }}
          OPTIONAL {{ ?person wdt:P570 ?deathDate }}
          OPTIONAL {{ ?person wdt:P27 ?nationality }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "ja,en" }}
        }}
        ORDER BY DESC(?birthDate)
        LIMIT {limit}
        """
        return self.execute_query(query)
    
    def get_athletes_extended(self, limit=500):
        """スポーツ選手（拡張版）"""
        query = f"""
        SELECT DISTINCT ?person ?personLabel ?birthDate ?deathDate ?sportLabel ?nationalityLabel
        WHERE {{
          ?person wdt:P31 wd:Q5 ;
                  wdt:P106 wd:Q2066131 ;  # アスリート
                  wdt:P641 ?sport .
          OPTIONAL {{ ?person wdt:P569 ?birthDate }}
          OPTIONAL {{ ?person wdt:P570 ?deathDate }}
          OPTIONAL {{ ?person wdt:P27 ?nationality }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "ja,en" }}
        }}
        ORDER BY DESC(?birthDate)
        LIMIT {limit}
        """
        return self.execute_query(query)
    
    def process_results(self, results, category):
        """クエリ結果を処理"""
        people = []
        if results and 'results' in results and 'bindings' in results['results']:
            for binding in results['results']['bindings']:
                person = {
                    'name': binding.get('personLabel', {}).get('value', ''),
                    'birth_date': binding.get('birthDate', {}).get('value', '')[:10] if 'birthDate' in binding else '',
                    'death_date': binding.get('deathDate', {}).get('value', '')[:10] if 'deathDate' in binding else '',
                    'nationality': binding.get('nationalityLabel', {}).get('value', ''),
                    'occupation': binding.get('occupationLabel', {}).get('value', category),
                    'main_category': self.categorize(category),
                    'subcategory': category,
                    'wikidata_id': binding.get('person', {}).get('value', '').split('/')[-1] if 'person' in binding else '',
                    'description': f"{category} from Wikidata",
                    'impact_score': 7,
                    'japanese_relevance': 5 if 'Japan' not in binding.get('nationalityLabel', {}).get('value', '') else 10,
                    'grade': 'B',
                    'data_source': 'wikidata_enhanced'
                }
                people.append(person)
        return people
    
    def categorize(self, occupation):
        """職業をメインカテゴリに分類"""
        entertainment = ['俳優', '歌手', '音楽家', '芸人', 'タレント', '声優', 'アイドル']
        sports = ['選手', 'アスリート', 'プレイヤー', '力士', '騎手']
        
        for e in entertainment:
            if e in occupation:
                return 'エンターテインメント'
        for s in sports:
            if s in occupation:
                return 'スポーツ'
        return '文化・芸術'
    
    def collect_all(self):
        """すべてのデータを収集"""
        print("エンターテイナー収集中...")
        entertainers = self.get_entertainers(800)
        self.collected_people.extend(self.process_results(entertainers, 'エンターテイナー'))
        time.sleep(1)
        
        print("俳優収集中...")
        actors = self.get_actors(600)
        self.collected_people.extend(self.process_results(actors, '俳優'))
        time.sleep(1)
        
        print("音楽家収集中...")
        musicians = self.get_musicians(600)
        self.collected_people.extend(self.process_results(musicians, '音楽家'))
        time.sleep(1)
        
        print("スポーツ選手収集中...")
        athletes = self.get_athletes_extended(500)
        self.collected_people.extend(self.process_results(athletes, 'スポーツ選手'))
        
        # 重複削除
        seen = set()
        unique_people = []
        for person in self.collected_people:
            key = (person['name'], person['birth_date'])
            if key not in seen:
                seen.add(key)
                unique_people.append(person)
        
        self.collected_people = unique_people
        print(f"収集完了: {len(self.collected_people)}人")
        return self.collected_people
    
    def save_to_csv(self, filename=None):
        """CSVファイルに保存"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"wikidata_enhanced_{timestamp}.csv"
        
        if self.collected_people:
            df = pd.DataFrame(self.collected_people)
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"保存完了: {filename}")
            return filename
        return None

def main():
    collector = EnhancedWikidataCollector()
    collector.collect_all()
    return collector.save_to_csv()

if __name__ == "__main__":
    main()