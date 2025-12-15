#!/usr/bin/env python3
"""
Optimized Wikipedia Collector - 最適化版
適切な遅延とバッチサイズで安定収集
"""

import csv
import json
import logging
import time
from datetime import datetime
from typing import Dict, List

import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OptimizedWikipediaCollector:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'HourglassApp/1.0 (Optimized Collection)',
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate'
        })

        # 最適化設定
        self.search_delay = 1.0  # 検索は1秒遅延
        self.batch_delay = 1.5  # バッチ取得は1.5秒遅延
        self.batch_size = 5  # 5タイトルずつ
        self.collected_people = []
        self.stats = {
            'searches': 0,
            'fetches': 0,
            'errors': 0
        }

    def search_people(self, query: str, limit: int = 30) -> List[str]:
        """人物検索（安定版）"""
        time.sleep(self.search_delay)
        self.stats['searches'] += 1

        params = {
            'action': 'query',
            'format': 'json',
            'list': 'search',
            'srsearch': query,
            'srlimit': limit,
            'srnamespace': 0
        }

        try:
            response = self.session.get(
                'https://ja.wikipedia.org/w/api.php',
                params=params,
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if 'query' in data and 'search' in data['query']:
                    titles = [item['title'] for item in data['query']['search']]
                    logger.info(f"Search '{query}': {len(titles)} results")
                    return titles
        except Exception as e:
            logger.warning(f"Search error for '{query}': {e}")
            self.stats['errors'] += 1

        return []

    def get_pages_info(self, titles: List[str]) -> List[Dict]:
        """ページ情報取得（軽量版）"""
        people = []

        for i in range(0, len(titles), self.batch_size):
            batch = titles[i:i+self.batch_size]
            time.sleep(self.batch_delay)
            self.stats['fetches'] += 1

            params = {
                'action': 'query',
                'format': 'json',
                'prop': 'extracts|categories',
                'exintro': True,
                'explaintext': True,
                'exsentences': 2,  # 2文のみ（軽量化）
                'titles': '|'.join(batch)
            }

            try:
                response = self.session.get(
                    'https://ja.wikipedia.org/w/api.php',
                    params=params,
                    timeout=10
                )
                if response.status_code == 200:
                    data = response.json()
                    if 'query' in data and 'pages' in data['query']:
                        for page_id, page_data in data['query']['pages'].items():
                            if page_id != '-1':
                                person = self.parse_person(page_data)
                                if person:
                                    people.append(person)
            except Exception as e:
                logger.warning(f"Fetch error: {e}")
                self.stats['errors'] += 1

        return people

    def parse_person(self, page_data: Dict) -> Dict:
        """人物情報解析（シンプル版）"""
        title = page_data.get('title', '')
        extract = page_data.get('extract', '')

        if len(extract) < 30:  # 最低限の説明
            return None

        categories = [cat.get('title', '') for cat in page_data.get('categories', [])]
        category_text = ' '.join(categories)

        # カテゴリ判定
        if any(word in category_text or word in extract for word in ['俳優', '女優', '歌手', '芸人']):
            main_cat = 'エンターテインメント'
        elif any(word in category_text or word in extract for word in ['選手', 'プレイヤー', 'スポーツ']):
            main_cat = 'スポーツ'
        elif any(word in category_text or word in extract for word in ['政治家', '首相', '大臣']):
            main_cat = '政治・社会'
        elif any(word in category_text or word in extract for word in ['起業家', '社長', 'CEO']):
            main_cat = 'ビジネス・テクノロジー'
        elif any(word in category_text or word in extract for word in ['歴史', '武将', '江戸']):
            main_cat = '歴史的教訓'
        else:
            main_cat = '文化・芸術'

        return {
            'name': title,
            'birth_date': '',
            'death_date': '',
            'nationality': '日本' if '日本' in extract else '',
            'occupation': '',
            'main_category': main_cat,
            'subcategory': '',
            'wikidata_id': '',
            'description': extract[:200],
            'impact_score': 7,
            'japanese_relevance': 8,
            'grade': 'B',
            'data_source': 'wikipedia_optimized'
        }

    def collect_batch(self, queries: List[str], target: int = 500):
        """バッチ収集"""
        batch_people = []

        for query in queries:
            if len(batch_people) >= target:
                break

            titles = self.search_people(query, 30)
            if titles:
                people = self.get_pages_info(titles[:20])
                batch_people.extend(people)
                logger.info(f"Collected {len(people)} from '{query}'")

        return batch_people[:target]

    def quick_collect(self):
        """クイック収集（5分以内）"""
        start_time = time.time()

        # 優先度の高いカテゴリから収集
        priority_queries = [
            # エンターテインメント
            ['日本 俳優', '日本 女優', '日本 歌手', 'お笑い芸人', 'アイドル'],
            # スポーツ
            ['野球選手', 'サッカー選手', 'オリンピック選手'],
            # ビジネス
            ['日本 起業家', '日本 実業家'],
            # 文化
            ['日本 作家', '日本 漫画家'],
            # 政治
            ['日本 政治家'],
            # 歴史
            ['戦国武将', '幕末']
        ]

        for queries in priority_queries:
            people = self.collect_batch(queries, 200)
            self.collected_people.extend(people)

            # 時間チェック
            elapsed = time.time() - start_time
            if elapsed > 240:  # 4分で切り上げ
                logger.info("Time limit approaching, finishing up...")
                break

        # 重複削除
        seen = set()
        unique = []
        for person in self.collected_people:
            if person['name'] not in seen:
                seen.add(person['name'])
                unique.append(person)
        self.collected_people = unique

        # 統計報告
        elapsed = time.time() - start_time
        logger.info("\n=== Collection Statistics ===")
        logger.info(f"Total collected: {len(self.collected_people)}")
        logger.info(f"Time elapsed: {elapsed:.1f} seconds")
        logger.info(f"Speed: {len(self.collected_people)/elapsed:.1f} people/sec")
        logger.info(f"API calls - Searches: {self.stats['searches']}, Fetches: {self.stats['fetches']}")
        logger.info(f"Errors: {self.stats['errors']}")

    def save_results(self):
        """結果保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"wikipedia_optimized_{timestamp}.csv"

        if self.collected_people:
            import pandas as pd
            df = pd.DataFrame(self.collected_people)
            df.to_csv(filename, index=False, encoding='utf-8-sig')

            print(f"\n✅ 保存完了: {filename}")
            print(f"総人数: {len(self.collected_people)}")
            print("\nカテゴリ分布:")
            print(df['main_category'].value_counts())

        return filename

def main():
    collector = OptimizedWikipediaCollector()
    print("最適化版Wikipedia収集開始（目標: 5分以内）")
    collector.quick_collect()
    return collector.save_results()

if __name__ == "__main__":
    main()
