#!/usr/bin/env python3
"""
Fast Wikipedia Collector - 高速収集版
テスト結果に基づき、より積極的な設定で収集
"""

import concurrent.futures
import csv
import json
import logging
import time
from datetime import datetime
from typing import Dict, List

import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FastWikipediaCollector:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'HourglassApp/1.0 (Fast Collection Mode)',
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        })
        
        # 高速設定（テスト結果に基づく）
        self.delay = 0.5  # 0.5秒遅延（テストで遅延なしでも成功）
        self.batch_size = 10  # 10タイトル同時（テストで5は成功）
        self.collected_people = []
        
    def search_batch(self, queries: List[str], lang: str = 'ja') -> Dict:
        """複数クエリを同時検索"""
        endpoint = f'https://{lang}.wikipedia.org/w/api.php'
        results = {}
        
        for query in queries:
            time.sleep(self.delay)
            params = {
                'action': 'query',
                'format': 'json',
                'list': 'search',
                'srsearch': query,
                'srlimit': 50,  # 50件取得
                'srinfo': 'totalhits',
                'srprop': 'size|wordcount|timestamp'
            }
            
            try:
                response = self.session.get(endpoint, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if 'query' in data and 'search' in data['query']:
                        results[query] = [item['title'] for item in data['query']['search']]
                        logger.info(f"Found {len(results[query])} results for: {query}")
            except Exception as e:
                logger.warning(f"Search failed for {query}: {e}")
                results[query] = []
                
        return results
    
    def get_pages_batch(self, titles: List[str], lang: str = 'ja') -> List[Dict]:
        """複数ページを一括取得（バッチ処理）"""
        endpoint = f'https://{lang}.wikipedia.org/w/api.php'
        people = []
        
        # 10タイトルずつバッチ処理
        for i in range(0, len(titles), self.batch_size):
            batch = titles[i:i+self.batch_size]
            time.sleep(self.delay)
            
            params = {
                'action': 'query',
                'format': 'json',
                'prop': 'extracts|pageprops|categories|info|pageimages',
                'exintro': True,
                'explaintext': True,
                'exsentences': 5,
                'inprop': 'url',
                'piprop': 'thumbnail',
                'pithumbsize': 100,
                'titles': '|'.join(batch)
            }
            
            try:
                response = self.session.get(endpoint, params=params, timeout=15)
                if response.status_code == 200:
                    data = response.json()
                    if 'query' in data and 'pages' in data['query']:
                        for page_id, page_data in data['query']['pages'].items():
                            if page_id != '-1':
                                person = self.extract_person_info(page_data, lang)
                                if person:
                                    people.append(person)
            except Exception as e:
                logger.warning(f"Batch fetch failed: {e}")
                
        return people
    
    def extract_person_info(self, page_data: Dict, lang: str) -> Dict:
        """ページデータから人物情報抽出"""
        title = page_data.get('title', '')
        extract = page_data.get('extract', '')
        
        # 最低限の説明があることを確認
        if len(extract) < 50:
            return None
            
        categories = [cat.get('title', '') for cat in page_data.get('categories', [])]
        
        return {
            'name': title,
            'birth_date': self.extract_date(extract),
            'death_date': '',
            'nationality': self.infer_nationality(extract, lang),
            'occupation': self.infer_occupation(categories, extract),
            'main_category': self.categorize(categories, extract),
            'subcategory': '',
            'wikidata_id': '',
            'description': extract[:500],
            'impact_score': min(7 + len(extract) // 500, 10),
            'japanese_relevance': 10 if lang == 'ja' else 5,
            'grade': 'A' if len(extract) > 1000 else 'B',
            'data_source': f'wikipedia_{lang}_fast',
            'url': page_data.get('fullurl', ''),
            'thumbnail': page_data.get('thumbnail', {}).get('source', '')
        }
    
    def extract_date(self, text: str) -> str:
        """日付抽出（簡易版）"""
        import re
        pattern = r'(\d{4})年'
        match = re.search(pattern, text)
        return f"{match.group(1)}-01-01" if match else ''
    
    def infer_nationality(self, text: str, lang: str) -> str:
        """国籍推定"""
        if lang == 'ja' or '日本' in text:
            return '日本'
        elif 'アメリカ' in text or 'America' in text:
            return 'アメリカ'
        return '不明'
    
    def infer_occupation(self, categories: List[str], extract: str) -> str:
        """職業推定"""
        text = ' '.join(categories) + ' ' + extract
        
        occupations = {
            '俳優': ['俳優', '女優', '映画'],
            '歌手': ['歌手', '歌', 'ミュージシャン'],
            '政治家': ['政治家', '首相', '大統領'],
            'スポーツ選手': ['選手', 'プレイヤー', 'アスリート'],
            '作家': ['作家', '小説家', '著者']
        }
        
        for occ, keywords in occupations.items():
            if any(kw in text for kw in keywords):
                return occ
        return '著名人'
    
    def categorize(self, categories: List[str], extract: str) -> str:
        """カテゴリ分類"""
        text = ' '.join(categories) + ' ' + extract
        
        if any(word in text for word in ['俳優', '歌手', '芸能', 'タレント']):
            return 'エンターテインメント'
        elif any(word in text for word in ['選手', 'スポーツ', 'オリンピック']):
            return 'スポーツ'
        elif any(word in text for word in ['政治', '大統領', '首相']):
            return '政治・社会'
        elif any(word in text for word in ['起業', '社長', 'CEO']):
            return 'ビジネス・テクノロジー'
        elif any(word in text for word in ['歴史', '戦国', '江戸']):
            return '歴史的教訓'
        else:
            return '文化・芸術'
    
    def collect_category(self, category: str, queries: List[str], target: int):
        """カテゴリ別収集"""
        logger.info(f"Collecting {category}: target={target}")
        category_people = []
        
        # 日本語検索
        ja_results = self.search_batch(queries, 'ja')
        for query, titles in ja_results.items():
            if titles:
                people = self.get_pages_batch(titles[:30], 'ja')
                category_people.extend(people)
        
        # 英語で補完（必要な場合）
        if len(category_people) < target:
            en_queries = [q.replace('日本', 'Japan') for q in queries[:3]]
            en_results = self.search_batch(en_queries, 'en')
            for query, titles in en_results.items():
                if titles:
                    people = self.get_pages_batch(titles[:20], 'en')
                    category_people.extend(people)
        
        # カテゴリ統一
        for person in category_people:
            person['main_category'] = category
        
        # 目標数まで取得
        self.collected_people.extend(category_people[:target])
        logger.info(f"Collected {len(category_people)} for {category}")
        
        return len(category_people)
    
    def collect_all_fast(self):
        """高速全収集"""
        start_time = time.time()
        
        collections = {
            'エンターテインメント': {
                'queries': ['日本 俳優', '日本 女優', '日本 歌手', 'アイドル', 'お笑い芸人', 
                          '声優', 'YouTuber', 'タレント', 'アニメ監督', '映画監督'],
                'target': 1000
            },
            'スポーツ': {
                'queries': ['野球選手', 'サッカー選手', 'テニス選手', 'オリンピック',
                          'プロレスラー', '相撲力士', 'ゴルファー', 'フィギュアスケート'],
                'target': 800
            },
            '文化・芸術': {
                'queries': ['作家', '小説家', '漫画家', '画家', '音楽家',
                          '建築家', 'デザイナー', '写真家'],
                'target': 700
            },
            'ビジネス・テクノロジー': {
                'queries': ['起業家', '実業家', 'CEO', 'プログラマー', 
                          '投資家', 'AI研究者'],
                'target': 600
            },
            '政治・社会': {
                'queries': ['政治家', '首相', '活動家', '外交官'],
                'target': 500
            },
            '歴史的教訓': {
                'queries': ['戦国武将', '幕末', '明治維新', '歴史'],
                'target': 400
            }
        }
        
        total_collected = 0
        for category, config in collections.items():
            collected = self.collect_category(
                category,
                config['queries'],
                config['target']
            )
            total_collected += collected
            
            # 進捗報告
            elapsed = time.time() - start_time
            logger.info(f"Progress: {total_collected} people in {elapsed:.1f} seconds")
        
        # 重複削除
        self.remove_duplicates()
        
        # 最終報告
        elapsed = time.time() - start_time
        logger.info(f"Collection complete: {len(self.collected_people)} people in {elapsed:.1f} seconds")
        logger.info(f"Speed: {len(self.collected_people) / elapsed:.1f} people/second")
    
    def remove_duplicates(self):
        """重複削除"""
        seen = set()
        unique = []
        for person in self.collected_people:
            key = person['name']
            if key not in seen:
                seen.add(key)
                unique.append(person)
        self.collected_people = unique
        logger.info(f"After deduplication: {len(self.collected_people)} people")
    
    def save_results(self):
        """結果保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"wikipedia_fast_{timestamp}.csv"
        
        if self.collected_people:
            import pandas as pd
            df = pd.DataFrame(self.collected_people)
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            logger.info(f"Saved to {filename}")
            
            # カテゴリ別集計
            print("\nカテゴリ別集計:")
            print(df['main_category'].value_counts())
            
        return filename

def main():
    collector = FastWikipediaCollector()
    collector.collect_all_fast()
    return collector.save_results()

if __name__ == "__main__":
    main()