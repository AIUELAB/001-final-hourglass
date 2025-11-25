#!/usr/bin/env python3
"""
Quick Wikidata Collector - 高速収集版
"""

import csv
import time
from datetime import datetime

import requests


def quick_collect():
    """シンプルで高速な収集"""
    endpoint = "https://query.wikidata.org/sparql"
    headers = {
        'User-Agent': 'HourglassApp/1.0',
        'Accept': 'application/sparql-results+json'
    }

    all_people = []

    # クエリ1: 日本の有名人（エンターテインメント）
    query1 = """
    SELECT DISTINCT ?person ?personLabel ?birthDate ?occupationLabel
    WHERE {
      ?person wdt:P31 wd:Q5 ;
              wdt:P27 wd:Q17 ;
              wdt:P106 ?occupation .
      ?occupation wdt:P279* wd:Q488111 .
      OPTIONAL { ?person wdt:P569 ?birthDate }
      SERVICE wikibase:label { bd:serviceParam wikibase:language "ja,en" }
    }
    LIMIT 500
    """

    # クエリ2: 世界的に有名なアスリート
    query2 = """
    SELECT DISTINCT ?person ?personLabel ?birthDate ?nationalityLabel
    WHERE {
      ?person wdt:P31 wd:Q5 ;
              wdt:P106 wd:Q2066131 ;
              wdt:P166 ?award .
      OPTIONAL { ?person wdt:P569 ?birthDate }
      OPTIONAL { ?person wdt:P27 ?nationality }
      SERVICE wikibase:label { bd:serviceParam wikibase:language "ja,en" }
    }
    LIMIT 500
    """

    # クエリ3: ノーベル賞受賞者
    query3 = """
    SELECT DISTINCT ?person ?personLabel ?birthDate ?awardLabel
    WHERE {
      ?person wdt:P31 wd:Q5 ;
              wdt:P166 ?award .
      ?award wdt:P361* wd:Q7191 .
      OPTIONAL { ?person wdt:P569 ?birthDate }
      SERVICE wikibase:label { bd:serviceParam wikibase:language "ja,en" }
    }
    LIMIT 300
    """

    queries = [
        (query1, 'エンターテインメント'),
        (query2, 'スポーツ'),
        (query3, '文化・芸術')
    ]

    for query, category in queries:
        print(f"{category}収集中...")
        try:
            response = requests.get(
                endpoint,
                params={'query': query, 'format': 'json'},
                headers=headers,
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                if 'results' in data and 'bindings' in data['results']:
                    for binding in data['results']['bindings']:
                        person = {
                            'name': binding.get('personLabel', {}).get('value', ''),
                            'birth_date': binding.get('birthDate', {}).get('value', '')[:10] if 'birthDate' in binding else '',
                            'death_date': '',
                            'nationality': binding.get('nationalityLabel', {}).get('value', ''),
                            'occupation': binding.get('occupationLabel', {}).get('value', category),
                            'main_category': category,
                            'subcategory': '',
                            'wikidata_id': binding.get('person', {}).get('value', '').split('/')[-1] if 'person' in binding else '',
                            'description': f'{category} from Wikidata',
                            'impact_score': 7,
                            'japanese_relevance': 8,
                            'grade': 'B',
                            'data_source': 'wikidata_quick'
                        }
                        all_people.append(person)
                    print(f"  {len(data['results']['bindings'])}人収集")
        except Exception as e:
            print(f"  エラー: {e}")
        time.sleep(1)

    # CSVに保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"wikidata_quick_{timestamp}.csv"

    with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
        if all_people:
            writer = csv.DictWriter(f, fieldnames=all_people[0].keys())
            writer.writeheader()
            writer.writerows(all_people)

    print(f"\n合計 {len(all_people)}人を {filename} に保存")
    return filename

if __name__ == "__main__":
    quick_collect()
