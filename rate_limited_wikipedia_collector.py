#!/usr/bin/env python3
"""
Rate-Limited Wikipedia Collector - API制限対応版
20,000人の高品質データを収集
"""

import csv
import json
import logging
import random
import time
from datetime import datetime
from typing import Dict, List, Optional

import requests

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RateLimitedWikipediaCollector:
    """API制限を考慮したWikipedia収集クラス"""
    
    def __init__(self):
        # セッション設定（Keep-Alive）
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'HourglassApp/1.0 (Educational; Contact: admin@example.com)',
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        })
        
        # レート制限設定
        self.min_delay = 2.0  # 最小遅延（秒）
        self.max_delay = 3.0  # 最大遅延（秒）
        self.batch_size = 50  # バッチサイズ
        self.max_retries = 3  # 最大リトライ回数
        
        # 収集データ
        self.collected_people = []
        self.failed_requests = []
        
        # API エンドポイント
        self.endpoints = {
            'ja': 'https://ja.wikipedia.org/w/api.php',
            'en': 'https://en.wikipedia.org/w/api.php'
        }
        
        # カテゴリ別収集目標
        self.category_targets = {
            'エンターテインメント': 6000,
            'スポーツ': 4000,
            '文化・芸術': 3500,
            'ビジネス・テクノロジー': 3000,
            '政治・社会': 2000,
            '歴史的教訓': 1500
        }
        
    def wait_with_jitter(self):
        """ジッター付き待機（API制限対策）"""
        delay = random.uniform(self.min_delay, self.max_delay)
        time.sleep(delay)
        
    def make_request(self, endpoint: str, params: dict, retry_count: int = 0) -> Optional[dict]:
        """リトライ機能付きAPIリクエスト"""
        try:
            self.wait_with_jitter()  # レート制限対策
            
            response = self.session.get(endpoint, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request failed: {e}")
            
            if retry_count < self.max_retries:
                # エクスポネンシャルバックオフ
                backoff_time = (2 ** retry_count) + random.uniform(0, 1)
                logger.info(f"Retrying in {backoff_time:.1f} seconds...")
                time.sleep(backoff_time)
                return self.make_request(endpoint, params, retry_count + 1)
            else:
                logger.error(f"Max retries exceeded for {params.get('titles', params.get('srsearch', ''))}")
                self.failed_requests.append(params)
                return None
                
    def search_people(self, query: str, lang: str = 'ja', limit: int = 50) -> List[str]:
        """人物検索（タイトルリスト取得）"""
        endpoint = self.endpoints[lang]
        params = {
            'action': 'query',
            'format': 'json',
            'list': 'search',
            'srsearch': query,
            'srlimit': min(limit, self.batch_size),
            'srnamespace': 0,
            'srwhat': 'text'
        }
        
        data = self.make_request(endpoint, params)
        if data and 'query' in data:
            return [item['title'] for item in data['query'].get('search', [])]
        return []
        
    def get_page_details(self, titles: List[str], lang: str = 'ja') -> List[Dict]:
        """ページ詳細情報取得（バッチ処理）"""
        endpoint = self.endpoints[lang]
        people = []
        
        # バッチ処理
        for i in range(0, len(titles), 10):  # 10件ずつ処理
            batch_titles = titles[i:i+10]
            
            params = {
                'action': 'query',
                'format': 'json',
                'prop': 'extracts|pageprops|categories|info',
                'exintro': True,
                'explaintext': True,
                'exsentences': 3,
                'inprop': 'url',
                'titles': '|'.join(batch_titles)
            }
            
            data = self.make_request(endpoint, params)
            
            if data and 'query' in data and 'pages' in data['query']:
                for page_id, page_data in data['query']['pages'].items():
                    if page_id != '-1':  # ページが存在する場合
                        person = self.extract_person_data(page_data, lang)
                        if person:
                            people.append(person)
                            
        return people
        
    def extract_person_data(self, page_data: Dict, lang: str) -> Optional[Dict]:
        """ページデータから人物情報を抽出"""
        title = page_data.get('title', '')
        extract = page_data.get('extract', '')
        categories = page_data.get('categories', [])
        url = page_data.get('fullurl', '')
        
        # 認知度チェック（最低限の説明文があるか）
        if len(extract) < 100:
            return None
            
        # カテゴリから職業・分野を推測
        occupation = self.infer_occupation(categories, extract)
        main_category = self.categorize_person(occupation, extract)
        
        # 生年月日を抽出（簡易版）
        birth_date = self.extract_birth_date(extract)
        
        return {
            'name': title,
            'birth_date': birth_date,
            'death_date': '',
            'nationality': self.infer_nationality(extract, lang),
            'occupation': occupation,
            'main_category': main_category,
            'subcategory': '',
            'wikidata_id': '',
            'description': extract[:500],
            'impact_score': self.calculate_impact_score(extract, categories),
            'japanese_relevance': self.calculate_japanese_relevance(extract, lang),
            'grade': self.assign_grade(extract, categories),
            'data_source': f'wikipedia_{lang}',
            'url': url
        }
        
    def infer_occupation(self, categories: List, extract: str) -> str:
        """カテゴリと説明文から職業を推測"""
        text = str(categories) + ' ' + extract
        
        occupations = {
            '俳優': ['俳優', '女優', '出演', '映画'],
            '歌手': ['歌手', 'シンガー', '歌', 'ボーカル'],
            '芸人': ['芸人', 'お笑い', 'コメディアン'],
            'スポーツ選手': ['選手', 'プレイヤー', 'アスリート'],
            '作家': ['作家', '小説家', '著者'],
            '政治家': ['政治家', '大臣', '首相', '議員'],
            '実業家': ['実業家', '起業家', 'CEO', '社長'],
            '科学者': ['科学者', '研究者', '博士', '教授']
        }
        
        for occ, keywords in occupations.items():
            if any(kw in text for kw in keywords):
                return occ
                
        return '著名人'
        
    def categorize_person(self, occupation: str, extract: str) -> str:
        """メインカテゴリを決定"""
        category_map = {
            'エンターテインメント': ['俳優', '歌手', '芸人', 'タレント', 'アイドル'],
            'スポーツ': ['選手', 'アスリート', 'プレイヤー'],
            'ビジネス・テクノロジー': ['実業家', '起業家', 'CEO', 'エンジニア'],
            '政治・社会': ['政治家', '活動家', '大臣'],
            '歴史的教訓': ['武将', '歴史', '江戸', '明治'],
            '文化・芸術': ['作家', '画家', '芸術家', '音楽家']
        }
        
        for cat, keywords in category_map.items():
            if any(kw in occupation or kw in extract for kw in keywords):
                return cat
                
        return '文化・芸術'
        
    def extract_birth_date(self, extract: str) -> str:
        """説明文から生年月日を抽出（簡易版）"""
        import re
        
        # パターン: 1990年1月1日
        pattern = r'(\d{4})年(\d{1,2})月(\d{1,2})日'
        match = re.search(pattern, extract)
        if match:
            return f"{match.group(1)}-{match.group(2):0>2}-{match.group(3):0>2}"
            
        # パターン: 1990年生まれ
        pattern = r'(\d{4})年.*生'
        match = re.search(pattern, extract)
        if match:
            return f"{match.group(1)}-01-01"
            
        return ''
        
    def infer_nationality(self, extract: str, lang: str) -> str:
        """国籍を推測"""
        if lang == 'ja' and any(word in extract for word in ['日本', '東京', '大阪']):
            return '日本'
        elif 'アメリカ' in extract or 'America' in extract:
            return 'アメリカ'
        elif 'イギリス' in extract or 'British' in extract:
            return 'イギリス'
        return ''
        
    def calculate_impact_score(self, extract: str, categories: List) -> int:
        """影響力スコア計算"""
        score = 5  # 基本スコア
        
        # 説明文の長さ
        if len(extract) > 500:
            score += 2
        elif len(extract) > 300:
            score += 1
            
        # カテゴリ数
        if len(categories) > 10:
            score += 2
        elif len(categories) > 5:
            score += 1
            
        return min(score, 10)
        
    def calculate_japanese_relevance(self, extract: str, lang: str) -> int:
        """日本人関連度計算"""
        score = 5
        
        if lang == 'ja':
            score += 3
            
        japanese_keywords = ['日本', 'Japan', '東京', 'Tokyo', '大阪', 'Osaka']
        if any(kw in extract for kw in japanese_keywords):
            score += 2
            
        return min(score, 10)
        
    def assign_grade(self, extract: str, categories: List) -> str:
        """グレード割り当て"""
        if len(extract) > 500 and len(categories) > 10:
            return 'A'
        elif len(extract) > 300 and len(categories) > 5:
            return 'B'
        else:
            return 'C'
            
    def collect_by_category(self, category: str, queries: List[str], target_count: int):
        """カテゴリ別収集"""
        logger.info(f"Collecting {category}: target={target_count}")
        category_people = []
        
        for query in queries:
            if len(category_people) >= target_count:
                break
                
            # 日本語版で検索
            logger.info(f"  Searching JA: {query}")
            ja_titles = self.search_people(query, 'ja', 100)
            if ja_titles:
                ja_people = self.get_page_details(ja_titles[:50], 'ja')
                category_people.extend(ja_people)
                
            # 英語版で補完
            if len(category_people) < target_count:
                logger.info(f"  Searching EN: {query}")
                en_titles = self.search_people(query, 'en', 50)
                if en_titles:
                    en_people = self.get_page_details(en_titles[:25], 'en')
                    category_people.extend(en_people)
                    
        # カテゴリを統一
        for person in category_people:
            person['main_category'] = category
            
        self.collected_people.extend(category_people[:target_count])
        logger.info(f"  Collected {len(category_people)} people for {category}")
        
    def collect_all(self):
        """全カテゴリ収集"""
        # カテゴリ別クエリ
        category_queries = {
            'エンターテインメント': [
                '日本 俳優', '日本 女優', '日本 歌手', 'アイドル',
                'お笑い芸人', '声優', 'タレント', 'YouTuber',
                'アニメ キャラクター', '漫画 キャラクター'
            ],
            'スポーツ': [
                '野球選手', 'サッカー選手', 'テニス選手', 'ゴルフ選手',
                'オリンピック メダリスト', '相撲力士', 'プロレスラー',
                'フィギュアスケート', 'マラソン選手', 'NBA選手'
            ],
            '文化・芸術': [
                '作家', '小説家', '詩人', '画家', '彫刻家',
                '映画監督', '漫画家', 'アニメ監督', '建築家', 'デザイナー'
            ],
            'ビジネス・テクノロジー': [
                '起業家', '実業家', 'CEO', 'プログラマー', 'エンジニア',
                '投資家', 'イノベーター', 'AI研究者', 'ゲームクリエイター'
            ],
            '政治・社会': [
                '政治家', '首相', '大統領', '活動家', '革命家',
                '外交官', '国連', 'ノーベル平和賞', '社会運動家'
            ],
            '歴史的教訓': [
                '戦国武将', '幕末 志士', '明治維新', '天皇',
                '将軍', '武士', '忍者', '歴史上の人物', '古代 皇帝'
            ]
        }
        
        # 各カテゴリを収集
        for category, queries in category_queries.items():
            target = self.category_targets[category]
            self.collect_by_category(category, queries, target)
            
            # 進捗保存
            self.save_checkpoint()
            
    def save_checkpoint(self):
        """進捗保存（中断対策）"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        checkpoint_file = f"checkpoint_{timestamp}.json"
        
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump({
                'collected': len(self.collected_people),
                'failed': len(self.failed_requests),
                'timestamp': timestamp
            }, f, ensure_ascii=False, indent=2)
            
        logger.info(f"Checkpoint saved: {len(self.collected_people)} people")
        
    def remove_duplicates(self):
        """重複削除"""
        seen = set()
        unique = []
        
        for person in self.collected_people:
            key = (person['name'], person['birth_date'][:4] if person['birth_date'] else '')
            if key not in seen:
                seen.add(key)
                unique.append(person)
                
        self.collected_people = unique
        logger.info(f"After deduplication: {len(self.collected_people)} people")
        
    def save_to_csv(self):
        """最終データ保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"wikipedia_20k_{timestamp}.csv"
        
        if self.collected_people:
            import pandas as pd
            df = pd.DataFrame(self.collected_people)
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            logger.info(f"Saved {len(self.collected_people)} people to {filename}")
            
        # 失敗リスト保存
        if self.failed_requests:
            with open(f"failed_{timestamp}.json", 'w') as f:
                json.dump(self.failed_requests, f, indent=2)
                
        return filename

def main():
    """メイン処理"""
    collector = RateLimitedWikipediaCollector()
    
    try:
        logger.info("Starting collection...")
        collector.collect_all()
        
        logger.info("Removing duplicates...")
        collector.remove_duplicates()
        
        logger.info("Saving data...")
        filename = collector.save_to_csv()
        
        logger.info(f"Collection complete: {filename}")
        return filename
        
    except KeyboardInterrupt:
        logger.info("Collection interrupted by user")
        collector.save_checkpoint()
        collector.save_to_csv()
        
    except Exception as e:
        logger.error(f"Collection failed: {e}")
        collector.save_checkpoint()
        raise

if __name__ == "__main__":
    main()