#!/usr/bin/env python3
"""
新規カテゴリ人物取得スクリプト
- 建築家（プリツカー賞受賞者）
- 料理人（ミシュラン3つ星シェフ）
- 写真家
- ジャーナリスト
- 長寿者（100歳以上）

Wikidata SPARQL APIを使用
"""

import requests
import json
import time
from datetime import datetime
from pathlib import Path

WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"
HEADERS = {"User-Agent": "FinalHourglass/1.0 (EPUP Episode Generator)", "Accept": "application/json"}

OUTPUT_DIR = Path("src/reports/new_category_persons")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def query_wikidata(sparql_query: str, category_name: str) -> list:
    """Wikidata SPARQLクエリを実行"""
    print(f"  Querying Wikidata for {category_name}...")

    try:
        response = requests.get(
            WIKIDATA_ENDPOINT, params={"query": sparql_query, "format": "json"}, headers=HEADERS, timeout=60
        )
        response.raise_for_status()
        data = response.json()

        results = []
        for item in data.get("results", {}).get("bindings", []):
            person = {
                "wikidata_id": item.get("person", {}).get("value", "").split("/")[-1],
                "name_en": item.get("personLabel", {}).get("value", ""),
                "name_ja": item.get("personLabel_ja", {}).get("value", ""),
                "birth_year": None,
                "death_year": None,
                "category": category_name,
            }

            # 生年
            if "birthDate" in item:
                try:
                    birth = item["birthDate"]["value"]
                    person["birth_year"] = int(birth[:4])
                except (ValueError, IndexError):
                    pass

            # 没年
            if "deathDate" in item:
                try:
                    death = item["deathDate"]["value"]
                    person["death_year"] = int(death[:4])
                except (ValueError, IndexError):
                    pass

            # 追加情報
            if "description" in item:
                person["description"] = item["description"]["value"]
            if "award" in item:
                person["award"] = item.get("awardLabel", {}).get("value", "")

            results.append(person)

        print(f"    Found {len(results)} persons")
        return results

    except Exception as e:
        print(f"    Error: {e}")
        return []


def fetch_architects() -> list:
    """建築家（プリツカー賞受賞者など）を取得"""
    query = """
    SELECT DISTINCT ?person ?personLabel ?personLabel_ja ?birthDate ?deathDate ?awardLabel WHERE {
      ?person wdt:P31 wd:Q5 .  # human
      ?person wdt:P106 wd:Q42973 .  # architect
      OPTIONAL { ?person wdt:P569 ?birthDate . }
      OPTIONAL { ?person wdt:P570 ?deathDate . }
      OPTIONAL {
        ?person wdt:P166 ?award .
        ?award wdt:P31/wdt:P279* wd:Q618779 .  # architecture award
      }
      SERVICE wikibase:label {
        bd:serviceParam wikibase:language "ja,en" .
        ?person rdfs:label ?personLabel_ja .
      }
      SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . }
      FILTER(BOUND(?birthDate))
    }
    LIMIT 200
    """
    return query_wikidata(query, "建築")


def fetch_chefs() -> list:
    """料理人・シェフを取得"""
    query = """
    SELECT DISTINCT ?person ?personLabel ?personLabel_ja ?birthDate ?deathDate WHERE {
      ?person wdt:P31 wd:Q5 .  # human
      ?person wdt:P106 wd:Q3499072 .  # chef
      OPTIONAL { ?person wdt:P569 ?birthDate . }
      OPTIONAL { ?person wdt:P570 ?deathDate . }
      SERVICE wikibase:label {
        bd:serviceParam wikibase:language "ja,en" .
        ?person rdfs:label ?personLabel_ja .
      }
      SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . }
      FILTER(BOUND(?birthDate))
    }
    LIMIT 150
    """
    return query_wikidata(query, "料理")


def fetch_photographers() -> list:
    """写真家を取得"""
    query = """
    SELECT DISTINCT ?person ?personLabel ?personLabel_ja ?birthDate ?deathDate WHERE {
      ?person wdt:P31 wd:Q5 .  # human
      ?person wdt:P106 wd:Q33231 .  # photographer
      OPTIONAL { ?person wdt:P569 ?birthDate . }
      OPTIONAL { ?person wdt:P570 ?deathDate . }
      SERVICE wikibase:label {
        bd:serviceParam wikibase:language "ja,en" .
        ?person rdfs:label ?personLabel_ja .
      }
      SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . }
      FILTER(BOUND(?birthDate))
    }
    LIMIT 150
    """
    return query_wikidata(query, "写真")


def fetch_journalists() -> list:
    """ジャーナリストを取得"""
    query = """
    SELECT DISTINCT ?person ?personLabel ?personLabel_ja ?birthDate ?deathDate WHERE {
      ?person wdt:P31 wd:Q5 .  # human
      ?person wdt:P106 wd:Q1930187 .  # journalist
      OPTIONAL { ?person wdt:P569 ?birthDate . }
      OPTIONAL { ?person wdt:P570 ?deathDate . }
      SERVICE wikibase:label {
        bd:serviceParam wikibase:language "ja,en" .
        ?person rdfs:label ?personLabel_ja .
      }
      SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . }
      FILTER(BOUND(?birthDate))
    }
    LIMIT 150
    """
    return query_wikidata(query, "ジャーナリズム")


def fetch_centenarians() -> list:
    """長寿者（100歳以上）を取得"""
    query = """
    SELECT DISTINCT ?person ?personLabel ?personLabel_ja ?birthDate ?deathDate WHERE {
      ?person wdt:P31 wd:Q5 .  # human
      ?person wdt:P569 ?birthDate .
      OPTIONAL { ?person wdt:P570 ?deathDate . }

      # 100歳以上で亡くなった人
      FILTER(BOUND(?deathDate))
      BIND(YEAR(?deathDate) - YEAR(?birthDate) AS ?age)
      FILTER(?age >= 100)

      SERVICE wikibase:label {
        bd:serviceParam wikibase:language "ja,en" .
        ?person rdfs:label ?personLabel_ja .
      }
      SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . }
    }
    LIMIT 300
    """
    return query_wikidata(query, "長寿者")


def fetch_astronauts() -> list:
    """宇宙飛行士を取得"""
    query = """
    SELECT DISTINCT ?person ?personLabel ?personLabel_ja ?birthDate ?deathDate WHERE {
      ?person wdt:P31 wd:Q5 .  # human
      ?person wdt:P106 wd:Q11631 .  # astronaut
      OPTIONAL { ?person wdt:P569 ?birthDate . }
      OPTIONAL { ?person wdt:P570 ?deathDate . }
      SERVICE wikibase:label {
        bd:serviceParam wikibase:language "ja,en" .
        ?person rdfs:label ?personLabel_ja .
      }
      SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . }
      FILTER(BOUND(?birthDate))
    }
    LIMIT 100
    """
    return query_wikidata(query, "宇宙開発")


def main():
    print("=== 新規カテゴリ人物取得開始 ===")
    print(f"開始時刻: {datetime.now().isoformat()}")

    all_persons = []

    # 各カテゴリを順次取得（API制限回避のため間隔を空ける）
    fetchers = [
        ("建築家", fetch_architects),
        ("料理人", fetch_chefs),
        ("写真家", fetch_photographers),
        ("ジャーナリスト", fetch_journalists),
        ("長寿者", fetch_centenarians),
        ("宇宙飛行士", fetch_astronauts),
    ]

    for name, fetcher in fetchers:
        print(f"\n[{name}]")
        persons = fetcher()
        all_persons.extend(persons)
        time.sleep(2)  # API制限回避

    # 結果保存
    output_file = OUTPUT_DIR / f"new_category_persons_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_persons, f, ensure_ascii=False, indent=2)

    # サマリー
    print("\n=== 取得完了 ===")
    print(f"総人物数: {len(all_persons)}")

    # カテゴリ別集計
    from collections import Counter

    cat_counts = Counter(p["category"] for p in all_persons)
    for cat, count in cat_counts.most_common():
        print(f"  {cat}: {count}人")

    # 年齢分布（高齢層の確認）
    elderly = [
        p
        for p in all_persons
        if p.get("birth_year") and p.get("death_year") and (p["death_year"] - p["birth_year"]) >= 75
    ]
    print(f"\n75歳以上で没した人物: {len(elderly)}人")

    print(f"\n✅ 保存: {output_file}")
    return all_persons


if __name__ == "__main__":
    main()
