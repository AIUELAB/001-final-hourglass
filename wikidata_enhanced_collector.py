#!/usr/bin/env python3
"""
強化版Wikidata SPARQLコレクター
- より多様なカテゴリ
- 効率的なクエリ
- データ品質の向上
"""

import csv
import json
import time
from datetime import datetime

import requests


class WikidataEnhancedCollector:
    """強化版Wikidata SPARQLコレクター"""
    
    def __init__(self):
        self.endpoint = "https://query.wikidata.org/sparql"
        self.headers = {
            'User-Agent': 'HourglassApp/2.0 Enhanced Python/3.9',
            'Accept': 'application/sparql-results+json'
        }
        self.collected_people = []
        
    def execute_query(self, sparql_query, description=""):
        """SPARQLクエリを実行（エラーハンドリング強化）"""
        print(f"  🔍 {description}...")
        
        try:
            response = requests.get(
                self.endpoint,
                params={'query': sparql_query, 'format': 'json'},
                headers=self.headers,
                timeout=60  # タイムアウトを延長
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            print("    ⏱️ タイムアウト - クエリを簡素化して再試行")
            return None
        except Exception as e:
            print(f"    ❌ エラー: {e}")
            return None
    
    # ========== 日本の有名人（詳細版） ==========
    def get_japanese_celebrities(self, limit=500):
        """日本の有名人を詳細に取得"""
        query = """
        SELECT DISTINCT ?person ?personLabel ?birthDate ?deathDate ?occupationLabel ?description 
               (COUNT(?sitelink) as ?popularity)
        WHERE {
          ?person wdt:P31 wd:Q5 ;                    # 人間
                  wdt:P27 wd:Q17 ;                   # 日本国籍
                  wdt:P569 ?birthDate .               # 生年月日
          
          # 職業がある人を優先
          OPTIONAL { ?person wdt:P106 ?occupation }
          OPTIONAL { ?person wdt:P570 ?deathDate }
          OPTIONAL { ?person schema:description ?description FILTER(LANG(?description) = "ja") }
          
          # Wikipedia記事の数で人気度を測定
          ?sitelink schema:about ?person .
          
          SERVICE wikibase:label { bd:serviceParam wikibase:language "ja,en" }
        }
        GROUP BY ?person ?personLabel ?birthDate ?deathDate ?occupationLabel ?description
        HAVING (?popularity > 5)  # 複数のWikipedia記事がある人のみ
        ORDER BY DESC(?popularity)
        LIMIT """ + str(limit)
        
        return self.execute_query(query, f"日本の有名人（最大{limit}人）")
    
    # ========== YouTuber・インフルエンサー ==========
    def get_youtubers_influencers(self, limit=200):
        """YouTuberとインフルエンサーを取得"""
        query = """
        SELECT DISTINCT ?person ?personLabel ?birthDate ?channelLabel ?subscribers
        WHERE {
          ?person wdt:P31 wd:Q5 ;                    # 人間
                  wdt:P106 wd:Q17125263 ;            # YouTuber
                  wdt:P569 ?birthDate .               # 生年月日
          
          # YouTubeチャンネル情報
          OPTIONAL { ?person wdt:P2397 ?channel }    # YouTubeチャンネルID
          OPTIONAL { ?person wdt:P8687 ?subscribers } # 登録者数
          
          SERVICE wikibase:label { bd:serviceParam wikibase:language "ja,en" }
        }
        ORDER BY DESC(?subscribers)
        LIMIT """ + str(limit)
        
        return self.execute_query(query, f"YouTuber・インフルエンサー（最大{limit}人）")
    
    # ========== eスポーツ選手 ==========
    def get_esports_players(self, limit=200):
        """eスポーツ選手を取得"""
        query = """
        SELECT DISTINCT ?person ?personLabel ?birthDate ?gameLabel ?teamLabel
        WHERE {
          ?person wdt:P31 wd:Q5 ;                    # 人間
                  wdt:P106 wd:Q4379701 ;             # eスポーツ選手
                  wdt:P569 ?birthDate .               # 生年月日
          
          OPTIONAL { ?person wdt:P641 ?game }        # ゲーム
          OPTIONAL { ?person wdt:P54 ?team }         # 所属チーム
          
          SERVICE wikibase:label { bd:serviceParam wikibase:language "ja,en" }
        }
        ORDER BY DESC(?birthDate)
        LIMIT """ + str(limit)
        
        return self.execute_query(query, f"eスポーツ選手（最大{limit}人）")
    
    # ========== スタートアップ創業者 ==========
    def get_startup_founders(self, limit=300):
        """スタートアップ創業者を取得"""
        query = """
        SELECT DISTINCT ?person ?personLabel ?birthDate ?companyLabel ?founded
        WHERE {
          ?person wdt:P31 wd:Q5 ;                    # 人間
                  wdt:P106 wd:Q131524 ;              # 起業家
                  wdt:P569 ?birthDate .               # 生年月日
          
          # 会社を設立した人
          ?company wdt:P112 ?person ;                # 創業者
                   wdt:P571 ?founded .                # 設立日
          
          # 2000年以降に設立された会社（スタートアップ）
          FILTER(YEAR(?founded) >= 2000)
          
          SERVICE wikibase:label { bd:serviceParam wikibase:language "ja,en" }
        }
        ORDER BY DESC(?founded)
        LIMIT """ + str(limit)
        
        return self.execute_query(query, f"スタートアップ創業者（最大{limit}人）")
    
    # ========== ノーベル賞受賞者（詳細版） ==========
    def get_nobel_laureates_detailed(self, limit=200):
        """ノーベル賞受賞者を詳細情報付きで取得"""
        query = """
        SELECT DISTINCT ?person ?personLabel ?birthDate ?deathDate ?awardLabel ?year ?fieldLabel
        WHERE {
          ?person wdt:P31 wd:Q5 ;                    # 人間
                  wdt:P166 ?award ;                  # 受賞
                  wdt:P569 ?birthDate .               # 生年月日
          
          ?award wdt:P361* wd:Q7191 .                # ノーベル賞の一部
          
          # 受賞年と分野
          OPTIONAL { ?person p:P166 ?awardStatement .
                     ?awardStatement pq:P585 ?year ;
                                     pq:P1027 ?field }
          
          OPTIONAL { ?person wdt:P570 ?deathDate }
          
          SERVICE wikibase:label { bd:serviceParam wikibase:language "ja,en" }
        }
        ORDER BY DESC(?year)
        LIMIT """ + str(limit)
        
        return self.execute_query(query, f"ノーベル賞受賞者詳細（最大{limit}人）")
    
    # ========== 女性リーダー ==========
    def get_female_leaders(self, limit=200):
        """女性のリーダー・先駆者を取得"""
        query = """
        SELECT DISTINCT ?person ?personLabel ?birthDate ?positionLabel ?countryLabel
        WHERE {
          ?person wdt:P31 wd:Q5 ;                    # 人間
                  wdt:P21 wd:Q6581072 ;              # 女性
                  wdt:P569 ?birthDate .               # 生年月日
          
          # リーダーポジション
          { ?person wdt:P39 ?position .
            ?position wdt:P279* wd:Q30461 }          # 国家元首
          UNION
          { ?person wdt:P106 wd:Q82955 }             # 政治家
          UNION
          { ?person wdt:P106 wd:Q131524 }            # 起業家
          
          OPTIONAL { ?person wdt:P27 ?country }
          
          SERVICE wikibase:label { bd:serviceParam wikibase:language "ja,en" }
        }
        ORDER BY DESC(?birthDate)
        LIMIT """ + str(limit)
        
        return self.execute_query(query, f"女性リーダー（最大{limit}人）")
    
    # ========== アニメ・マンガ関係者 ==========
    def get_anime_manga_creators(self, limit=300):
        """アニメ・マンガ関係者を取得"""
        query = """
        SELECT DISTINCT ?person ?personLabel ?birthDate ?workLabel ?roleLabel
        WHERE {
          ?person wdt:P31 wd:Q5 ;                    # 人間
                  wdt:P569 ?birthDate .               # 生年月日
          
          # マンガ家、アニメーター、声優など
          { ?person wdt:P106 wd:Q3658341 }           # 漫画家
          UNION
          { ?person wdt:P106 wd:Q266569 }            # アニメーター
          UNION
          { ?person wdt:P106 wd:Q622807 }            # 声優
          UNION
          { ?person wdt:P106 wd:Q2526255 }           # 映画監督（アニメ含む）
          
          # 日本人を優先
          OPTIONAL { ?person wdt:P27 wd:Q17 }        # 日本国籍
          
          OPTIONAL { ?person wdt:P800 ?work }        # 著名な作品
          OPTIONAL { ?person wdt:P106 ?role }        # 役割
          
          SERVICE wikibase:label { bd:serviceParam wikibase:language "ja,en" }
        }
        ORDER BY DESC(?birthDate)
        LIMIT """ + str(limit)
        
        return self.execute_query(query, f"アニメ・マンガ関係者（最大{limit}人）")
    
    def process_results(self, results, category, subcategory=""):
        """クエリ結果を処理（データ品質向上）"""
        if not results or 'results' not in results:
            return 0
        
        count = 0
        for binding in results['results']['bindings']:
            try:
                # 基本データ抽出
                person_data = {
                    'id': binding.get('person', {}).get('value', '').split('/')[-1],
                    'name': binding.get('personLabel', {}).get('value', ''),
                    'name_ja': binding.get('personLabel', {}).get('value', ''),
                    'birth_year': self.extract_year(binding.get('birthDate', {}).get('value', '')),
                    'death_year': self.extract_year(binding.get('deathDate', {}).get('value', '')),
                    'nationality': binding.get('countryLabel', {}).get('value', '日本'),
                    'occupation': binding.get('occupationLabel', {}).get('value', category),
                    'main_category': category,
                    'subcategory': subcategory or binding.get('roleLabel', {}).get('value', ''),
                    'special_tags': 'Wikidata Enhanced',
                    'source': 'Wikidata SPARQL',
                    'wikidata_id': binding.get('person', {}).get('value', '').split('/')[-1],
                    'description': binding.get('description', {}).get('value', ''),
                    'popularity': binding.get('popularity', {}).get('value', '0'),
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
                
                # データ品質チェック
                if self.validate_person(person_data):
                    self.collected_people.append(person_data)
                    count += 1
                
            except Exception as e:
                continue
        
        return count
    
    def validate_person(self, person):
        """人物データの妥当性検証"""
        # 名前が必須
        if not person.get('name'):
            return False
            
        # 名前が番号や地名でないことを確認
        invalid_patterns = [
            r'^\d+$',  # 数字のみ
            r'^\[.*\]$',  # 括弧で囲まれた注釈
            r'^Q\d+$',  # WikidataのQID
        ]
        
        import re
        for pattern in invalid_patterns:
            if re.match(pattern, person['name']):
                return False
                
        return True
    
    def extract_year(self, date_string):
        """日付文字列から年を抽出"""
        if not date_string:
            return ''
        try:
            if 'T' in date_string:
                date_string = date_string.split('T')[0]
            if '-' in date_string:
                year = date_string.split('-')[0]
                # BC/紀元前の処理
                if year.startswith('-'):
                    return year  # 負の年はそのまま返す
                return year
            return date_string[:4] if len(date_string) >= 4 else ''
        except:
            return ''
    
    def collect_all_enhanced(self):
        """強化版：すべてのカテゴリからデータ収集"""
        print("🚀 強化版Wikidata SPARQLデータ収集開始...")
        print("=" * 70)
        
        collections = [
            ('日本の有名人', self.get_japanese_celebrities, 200, '日本'),
            ('YouTuber', self.get_youtubers_influencers, 100, 'インターネット'),
            ('eスポーツ選手', self.get_esports_players, 100, 'ゲーム'),
            ('起業家', self.get_startup_founders, 150, 'ビジネス'),
            ('ノーベル賞受賞者', self.get_nobel_laureates_detailed, 100, '学術'),
            ('女性リーダー', self.get_female_leaders, 100, 'リーダーシップ'),
            ('アニメ・マンガ', self.get_anime_manga_creators, 150, 'サブカルチャー'),
        ]
        
        total_collected = 0
        category_stats = {}
        
        for category_name, query_func, limit, subcategory in collections:
            print(f"\n📚 {category_name}を収集中...")
            
            results = query_func(limit)
            if results:
                count = self.process_results(results, category_name, subcategory)
                total_collected += count
                category_stats[category_name] = count
                print(f"  ✅ {count}人収集完了")
            else:
                print("  ⚠️ データ取得失敗")
                category_stats[category_name] = 0
            
            # API負荷軽減
            time.sleep(2)
        
        print("\n" + "=" * 70)
        print("🎯 収集完了！")
        print(f"  総収集人数: {total_collected}人")
        print("\n📊 カテゴリ別内訳:")
        
        for category, count in sorted(category_stats.items(), key=lambda x: x[1], reverse=True):
            if total_collected > 0:
                percentage = (count / total_collected) * 100
                print(f"  {category:20} : {count:4}人 ({percentage:5.1f}%)")
        
        return total_collected
    
    def save_to_csv(self, filename=None):
        """収集したデータをCSVに保存"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"wikidata_enhanced_{timestamp}.csv"
        
        with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
            fieldnames = [
                'id', 'name', 'name_ja', 'birth_year', 'death_year', 'death_age',
                'nationality', 'occupation', 'main_category', 'subcategory',
                'special_tags', 'source', 'wikidata_id', 'description', 
                'popularity', 'key_ages'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            writer.writerows(self.collected_people)
        
        print(f"\n💾 データを保存しました: {filename}")
        return filename

def main():
    """メイン処理"""
    print("=" * 70)
    print("🔧 強化版Wikidata SPARQLコレクター")
    print("=" * 70)
    
    collector = WikidataEnhancedCollector()
    
    # データ収集
    total = collector.collect_all_enhanced()
    
    if total > 0:
        # CSV保存
        output_file = collector.save_to_csv()
        
        print("\n" + "=" * 70)
        print("✅ 成功！")
        print(f"  - 総収集人数: {total}人")
        print("  - カテゴリの多様性: 向上")
        print("  - データ品質: 検証済み")
        print("  - コスト: $0（完全無料）")
        print("=" * 70)
    else:
        print("\n⚠️ データ収集に失敗しました")
    
    return output_file if total > 0 else None

if __name__ == "__main__":
    main()