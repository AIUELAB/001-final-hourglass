#!/usr/bin/env python3
"""
Wikipedia多層検証システム
Wikipedia Multi-Layer Validation System

このシステムは、人物の知名度をWikipediaの複数指標から評価します。
"""

import requests
import pandas as pd
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import concurrent.futures
from urllib.parse import quote
import logging
import hashlib

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WikipediaValidator:
    """Wikipedia多層検証システム"""
    
    def __init__(self, cache_file='wikipedia_cache.json'):
        self.cache_file = cache_file
        self.cache = self.load_cache()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'UltraThinkValidator/1.0 (contact@example.com)'
        })
        
        # API エンドポイント
        self.ja_api = 'https://ja.wikipedia.org/w/api.php'
        self.en_api = 'https://en.wikipedia.org/w/api.php'
        self.pageview_api = 'https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article'
        
        # レート制限
        self.last_request_time = 0
        self.min_request_interval = 0.5  # 500ms between requests
        
    def load_cache(self) -> Dict:
        """キャッシュのロード"""
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def save_cache(self):
        """キャッシュの保存"""
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)
    
    def get_cache_key(self, query: str, lang: str) -> str:
        """キャッシュキーの生成"""
        return hashlib.md5(f"{lang}:{query}".encode()).hexdigest()
    
    def rate_limit(self):
        """レート制限の適用"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()
    
    def search_wikipedia(self, query: str, lang: str = 'ja') -> Dict:
        """Wikipedia検索"""
        cache_key = self.get_cache_key(query, lang)
        
        # キャッシュチェック（1週間有効）
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if datetime.fromisoformat(cached['timestamp']) > datetime.now() - timedelta(days=7):
                return cached['data']
        
        self.rate_limit()
        
        api_url = self.ja_api if lang == 'ja' else self.en_api
        
        params = {
            'action': 'query',
            'format': 'json',
            'list': 'search',
            'srsearch': query,
            'srlimit': 10,
            'srinfo': 'totalhits|suggestion',
            'srprop': 'size|wordcount|timestamp|snippet'
        }
        
        try:
            response = self.session.get(api_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            result = {
                'found': len(data.get('query', {}).get('search', [])) > 0,
                'total_hits': data.get('query', {}).get('searchinfo', {}).get('totalhits', 0),
                'results': data.get('query', {}).get('search', []),
                'suggestion': data.get('query', {}).get('searchinfo', {}).get('suggestion')
            }
            
            # キャッシュ保存
            self.cache[cache_key] = {
                'timestamp': datetime.now().isoformat(),
                'data': result
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Wikipedia search error for {query}: {e}")
            return {'found': False, 'total_hits': 0, 'results': [], 'error': str(e)}
    
    def get_page_info(self, title: str, lang: str = 'ja') -> Dict:
        """ページ詳細情報の取得"""
        self.rate_limit()
        
        api_url = self.ja_api if lang == 'ja' else self.en_api
        
        params = {
            'action': 'query',
            'format': 'json',
            'prop': 'info|categories|pageprops|revisions',
            'titles': title,
            'inprop': 'protection|talkid|watched|watchers|visitingwatchers|notificationtimestamp|subjectid|url|readable|preload|displaytitle',
            'rvprop': 'timestamp|user|comment|size',
            'rvlimit': 1
        }
        
        try:
            response = self.session.get(api_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            pages = data.get('query', {}).get('pages', {})
            if pages:
                page_id = list(pages.keys())[0]
                if page_id != '-1':
                    page_data = pages[page_id]
                    return {
                        'exists': True,
                        'page_id': page_id,
                        'title': page_data.get('title'),
                        'length': page_data.get('length', 0),
                        'categories': len(page_data.get('categories', [])),
                        'last_revision': page_data.get('revisions', [{}])[0].get('timestamp'),
                        'url': page_data.get('fullurl')
                    }
            
            return {'exists': False}
            
        except Exception as e:
            logger.error(f"Page info error for {title}: {e}")
            return {'exists': False, 'error': str(e)}
    
    def get_pageviews(self, title: str, lang: str = 'ja', days: int = 30) -> Dict:
        """ページビュー統計の取得"""
        self.rate_limit()
        
        # 日付範囲の設定
        end_date = datetime.now() - timedelta(days=1)  # 昨日まで
        start_date = end_date - timedelta(days=days)
        
        # URLエンコード
        encoded_title = quote(title.replace(' ', '_'))
        project = f"{lang}.wikipedia"
        
        url = f"{self.pageview_api}/{project}/all-access/all-agents/{encoded_title}/daily/{start_date.strftime('%Y%m%d')}/{end_date.strftime('%Y%m%d')}"
        
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 404:
                return {'has_pageviews': False, 'monthly_average': 0}
            
            response.raise_for_status()
            data = response.json()
            
            items = data.get('items', [])
            if items:
                views = [item['views'] for item in items]
                return {
                    'has_pageviews': True,
                    'monthly_average': sum(views) / len(views) * 30,
                    'total_views': sum(views),
                    'max_daily': max(views),
                    'min_daily': min(views)
                }
            
            return {'has_pageviews': False, 'monthly_average': 0}
            
        except Exception as e:
            logger.error(f"Pageview error for {title}: {e}")
            return {'has_pageviews': False, 'monthly_average': 0, 'error': str(e)}
    
    def calculate_wikipedia_score(self, person_name: str, person_name_display: str, 
                                 occupation: str = None, nationality: str = None) -> Dict:
        """Wikipedia総合スコアの計算"""
        
        scores = {
            'japanese_wikipedia': 0,
            'english_wikipedia': 0,
            'pageviews': 0,
            'article_quality': 0,
            'total_score': 0,
            'details': {}
        }
        
        # 日本語Wikipedia検索
        ja_results = self.search_wikipedia(person_name_display, 'ja')
        if ja_results['found']:
            scores['japanese_wikipedia'] = min(10, ja_results['total_hits'] / 100)
            
            # 最初の結果の詳細を取得
            if ja_results['results']:
                first_result = ja_results['results'][0]
                page_info = self.get_page_info(first_result['title'], 'ja')
                
                if page_info.get('exists'):
                    # 記事の長さによる品質評価
                    length_score = min(10, page_info.get('length', 0) / 5000)
                    scores['article_quality'] = length_score
                    
                    # ページビュー取得
                    pageviews = self.get_pageviews(first_result['title'], 'ja')
                    if pageviews.get('has_pageviews'):
                        # 月間1000ビュー = スコア5
                        scores['pageviews'] = min(10, pageviews.get('monthly_average', 0) / 200)
                    
                    scores['details']['ja_page'] = {
                        'title': first_result['title'],
                        'length': page_info.get('length'),
                        'categories': page_info.get('categories'),
                        'monthly_views': pageviews.get('monthly_average', 0)
                    }
        
        # 英語Wikipedia検索（person_nameで検索）
        if person_name and person_name != 'nan':
            en_results = self.search_wikipedia(person_name, 'en')
            if en_results['found']:
                scores['english_wikipedia'] = min(10, en_results['total_hits'] / 100)
                
                if en_results['results']:
                    first_result = en_results['results'][0]
                    scores['details']['en_page'] = {
                        'title': first_result['title'],
                        'size': first_result.get('size', 0)
                    }
        
        # 総合スコア計算（10点満点）
        scores['total_score'] = (
            scores['japanese_wikipedia'] * 0.4 +
            scores['english_wikipedia'] * 0.2 +
            scores['pageviews'] * 0.2 +
            scores['article_quality'] * 0.2
        )
        
        # 判定
        if scores['total_score'] < 2:
            scores['recommendation'] = 'DELETE_HIGH_CONFIDENCE'
        elif scores['total_score'] < 4:
            scores['recommendation'] = 'DELETE_MEDIUM_CONFIDENCE'
        elif scores['total_score'] < 6:
            scores['recommendation'] = 'REVIEW_REQUIRED'
        else:
            scores['recommendation'] = 'KEEP'
        
        return scores
    
    def validate_batch(self, df: pd.DataFrame, sample_size: int = None) -> pd.DataFrame:
        """バッチ検証処理"""
        if sample_size:
            df = df.sample(min(sample_size, len(df)))
        
        results = []
        total = len(df)
        
        for idx, row in df.iterrows():
            logger.info(f"Processing {idx + 1}/{total}: {row.get('person_name_display', '')}")
            
            score = self.calculate_wikipedia_score(
                person_name=row.get('person_name', ''),
                person_name_display=row.get('person_name_display', ''),
                occupation=row.get('occupation'),
                nationality=row.get('nationality')
            )
            
            results.append({
                'person_id': row.get('person_id'),
                'person_name': row.get('person_name'),
                'person_name_display': row.get('person_name_display'),
                'wikipedia_score': score['total_score'],
                'ja_wikipedia': score['japanese_wikipedia'],
                'en_wikipedia': score['english_wikipedia'],
                'pageviews': score['pageviews'],
                'article_quality': score['article_quality'],
                'recommendation': score['recommendation'],
                'details': json.dumps(score['details'], ensure_ascii=False)
            })
            
            # 定期的にキャッシュ保存
            if (idx + 1) % 10 == 0:
                self.save_cache()
        
        # 最終キャッシュ保存
        self.save_cache()
        
        return pd.DataFrame(results)


def main():
    """メイン実行関数"""
    print("="*60)
    print("Wikipedia多層検証システム")
    print("Wikipedia Multi-Layer Validation System")
    print("="*60)
    
    # バリデーター初期化
    validator = WikipediaValidator()
    
    # テストケース
    test_cases = [
        {'person_name': 'Hayao Miyazaki', 'person_name_display': '宮崎駿', 'occupation': '映画監督'},
        {'person_name': 'Test Person', 'person_name_display': 'テスト太郎', 'occupation': '不明'},
    ]
    
    print("\n🔍 Testing validation system...")
    for test in test_cases:
        print(f"\n Testing: {test['person_name_display']}")
        score = validator.calculate_wikipedia_score(**test)
        print(f"  Total Score: {score['total_score']:.2f}/10")
        print(f"  Recommendation: {score['recommendation']}")
        print(f"  Details: {score['details']}")
    
    # データベース検証の準備
    csv_file = 'ultra_think_EPISODE_FINAL_20250901_020106.csv'
    if pd.io.common.file_exists(csv_file):
        print(f"\n📂 Loading database: {csv_file}")
        df = pd.read_csv(csv_file, encoding='utf-8')
        print(f"✅ Total records: {len(df)}")
        
        # サンプル検証
        print("\n🔍 Validating sample records...")
        results_df = validator.validate_batch(df, sample_size=5)
        
        # 結果保存
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"wikipedia_validation_results_{timestamp}.csv"
        results_df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"\n💾 Results saved to: {output_file}")
        
        # サマリー表示
        print("\n📊 Validation Summary:")
        print(f"  DELETE_HIGH_CONFIDENCE: {len(results_df[results_df['recommendation'] == 'DELETE_HIGH_CONFIDENCE'])}")
        print(f"  DELETE_MEDIUM_CONFIDENCE: {len(results_df[results_df['recommendation'] == 'DELETE_MEDIUM_CONFIDENCE'])}")
        print(f"  REVIEW_REQUIRED: {len(results_df[results_df['recommendation'] == 'REVIEW_REQUIRED'])}")
        print(f"  KEEP: {len(results_df[results_df['recommendation'] == 'KEEP'])}")
    
    print("\n✅ Wikipedia validation system ready!")


if __name__ == "__main__":
    main()