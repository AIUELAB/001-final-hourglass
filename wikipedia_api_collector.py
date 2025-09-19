#!/usr/bin/env python3
"""
Wikipedia API Collector - 日本で有名な人物を収集
"""

import csv
import json
import time
from datetime import datetime

import requests


class WikipediaAPICollector:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'HourglassApp/1.0 Educational'
        })
        self.collected_people = []
        
    def search_wikipedia(self, query, limit=50):
        """Wikipedia APIで検索"""
        url = "https://ja.wikipedia.org/w/api.php"
        params = {
            'action': 'query',
            'format': 'json',
            'list': 'search',
            'srsearch': query,
            'srlimit': limit
        }
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                return data.get('query', {}).get('search', [])
        except Exception as e:
            print(f"エラー: {e}")
        return []
    
    def get_page_info(self, title):
        """ページの詳細情報を取得"""
        url = "https://ja.wikipedia.org/w/api.php"
        params = {
            'action': 'query',
            'format': 'json',
            'prop': 'extracts|pageprops|categories',
            'exintro': True,
            'explaintext': True,
            'exsentences': 2,
            'titles': title
        }
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                pages = data.get('query', {}).get('pages', {})
                for page_id, page_data in pages.items():
                    return page_data
        except:
            pass
        return None
    
    def categorize_person(self, categories, extract):
        """カテゴリと説明文から分類"""
        category_map = {
            'エンターテインメント': ['俳優', '歌手', '芸人', 'タレント', 'アイドル', '声優', 'ミュージシャン', 'バンド'],
            'スポーツ': ['選手', 'プロ野球', 'サッカー', 'テニス', 'ゴルフ', 'オリンピック', '相撲', '競馬'],
            '文化・芸術': ['作家', '画家', '芸術家', '詩人', '小説家', '漫画家', 'デザイナー'],
            'ビジネス・テクノロジー': ['実業家', '起業家', 'CEO', '社長', 'エンジニア', 'プログラマ'],
            '政治・社会': ['政治家', '首相', '大臣', '知事', '市長', '活動家'],
            '歴史的教訓': ['歴史', '戦国', '江戸', '明治', '大正', '昭和']
        }
        
        text = str(categories) + ' ' + str(extract)
        
        for main_cat, keywords in category_map.items():
            for keyword in keywords:
                if keyword in text:
                    return main_cat
        
        return '文化・芸術'
    
    def collect_by_category(self):
        """カテゴリ別に収集"""
        queries = [
            # エンターテインメント
            ('日本 俳優', 'エンターテインメント', 200),
            ('日本 歌手', 'エンターテインメント', 200),
            ('お笑い芸人', 'エンターテインメント', 150),
            ('アイドル', 'エンターテインメント', 100),
            ('声優', 'エンターテインメント', 100),
            
            # スポーツ
            ('プロ野球選手', 'スポーツ', 150),
            ('サッカー選手 日本代表', 'スポーツ', 100),
            ('オリンピック メダリスト', 'スポーツ', 100),
            
            # ビジネス
            ('日本 起業家', 'ビジネス・テクノロジー', 50),
            ('日本 実業家', 'ビジネス・テクノロジー', 50),
            
            # 文化
            ('日本 作家', '文化・芸術', 100),
            ('日本 漫画家', '文化・芸術', 100),
        ]
        
        for query, default_category, limit in queries:
            print(f"検索中: {query}")
            results = self.search_wikipedia(query, limit)
            
            for result in results:
                title = result.get('title', '')
                if '一覧' in title or 'リスト' in title:
                    continue
                    
                # ページ情報を取得
                page_info = self.get_page_info(title)
                if page_info:
                    categories = page_info.get('categories', [])
                    extract = page_info.get('extract', '')
                    
                    # 人物かどうか簡易判定
                    if any(word in extract for word in ['生まれ', '出身', '歌手', '俳優', '選手']):
                        person = {
                            'name': title,
                            'birth_date': '',
                            'death_date': '',
                            'nationality': '日本',
                            'occupation': query.replace('日本 ', ''),
                            'main_category': self.categorize_person(categories, extract),
                            'subcategory': '',
                            'wikidata_id': '',
                            'description': extract[:100] if extract else '',
                            'impact_score': 7,
                            'japanese_relevance': 9,
                            'grade': 'B',
                            'data_source': 'wikipedia_api'
                        }
                        self.collected_people.append(person)
            
            time.sleep(1)  # API制限対策
        
        # 重複削除
        seen = set()
        unique = []
        for person in self.collected_people:
            if person['name'] not in seen:
                seen.add(person['name'])
                unique.append(person)
        
        self.collected_people = unique
        print(f"収集完了: {len(self.collected_people)}人")
        
    def save_to_csv(self):
        """CSVに保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"wikipedia_api_{timestamp}.csv"
        
        if self.collected_people:
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=self.collected_people[0].keys())
                writer.writeheader()
                writer.writerows(self.collected_people)
            print(f"保存完了: {filename}")
            return filename
        return None

def main():
    collector = WikipediaAPICollector()
    collector.collect_by_category()
    return collector.save_to_csv()

if __name__ == "__main__":
    main()