#!/usr/bin/env python3
"""
マルチAPI統合認識システム
Wikipedia、Brave Search、その他のAPIを統合して包括的な知名度スコアを算出
"""

import os
import time
import json
import logging
from typing import Dict, List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from datetime import datetime, timedelta
import hashlib

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)
logger = logging.getLogger(__name__)

# 既存のWikipediaシステムをインポート
from wikipedia_recognition_system_v2 import WikipediaRecognitionSystemV2

class MultiAPIRecognitionSystem:
    """マルチAPI統合認識システム"""
    
    def __init__(self):
        """初期化"""
        self.wikipedia_system = WikipediaRecognitionSystemV2()
        self.cache_dir = '.cache/multi_api'
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # API制限管理
        self.api_limits = {
            'wikipedia': {'limit': 200, 'window': 3600, 'used': 0, 'reset_time': time.time()},
            'brave': {'limit': 2000, 'window': 2592000, 'used': 0, 'reset_time': time.time()},  # 月間
            'serpapi': {'limit': 100, 'window': 86400, 'used': 0, 'reset_time': time.time()},  # 日次
        }
        
        # APIキー（環境変数から取得）
        self.brave_api_key = os.getenv('BRAVE_API_KEY', '')
        self.serpapi_key = os.getenv('SERPAPI_KEY', '')
        
        # 重み付け設定
        self.weights = {
            'wikipedia': 0.30,    # Wikipedia情報の重要度
            'web_search': 0.25,   # Web検索結果の重要度
            'news': 0.20,         # ニュース露出の重要度
            'social': 0.15,       # ソーシャルメディアの重要度
            'lesson': 0.10,       # 教訓的価値の重要度
        }
    
    def _check_api_limit(self, api_name: str) -> bool:
        """API制限チェック"""
        if api_name not in self.api_limits:
            return True
        
        limit_info = self.api_limits[api_name]
        current_time = time.time()
        
        # リセット時間を過ぎていればカウンタをリセット
        if current_time - limit_info['reset_time'] > limit_info['window']:
            limit_info['used'] = 0
            limit_info['reset_time'] = current_time
        
        # 制限チェック
        if limit_info['used'] >= limit_info['limit']:
            logger.warning(f"API制限到達: {api_name} ({limit_info['used']}/{limit_info['limit']})")
            return False
        
        return True
    
    def _increment_api_usage(self, api_name: str):
        """API使用カウントを増やす"""
        if api_name in self.api_limits:
            self.api_limits[api_name]['used'] += 1
    
    def _get_cache_path(self, name: str, api_type: str) -> str:
        """キャッシュファイルパスを取得"""
        safe_name = hashlib.md5(name.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{api_type}_{safe_name}.json")
    
    def _load_cache(self, name: str, api_type: str, max_age_hours: int = 168) -> Optional[Dict]:
        """キャッシュを読み込み"""
        cache_path = self._get_cache_path(name, api_type)
        
        if not os.path.exists(cache_path):
            return None
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # キャッシュの有効期限チェック
            cache_time = datetime.fromisoformat(cache_data.get('timestamp', '2000-01-01'))
            if datetime.now() - cache_time > timedelta(hours=max_age_hours):
                return None
            
            return cache_data.get('data')
        except Exception:
            return None
    
    def _save_cache(self, name: str, api_type: str, data: Dict):
        """キャッシュに保存"""
        cache_path = self._get_cache_path(name, api_type)
        
        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"キャッシュ保存失敗: {e}")
    
    def search_brave(self, name: str) -> Dict:
        """Brave Search APIで検索"""
        # キャッシュチェック
        cached = self._load_cache(name, 'brave')
        if cached:
            logger.debug(f"Braveキャッシュヒット: {name}")
            return cached
        
        # API制限チェック
        if not self._check_api_limit('brave') or not self.brave_api_key:
            return {'found': False, 'score': 0, 'reason': 'API制限またはキー未設定'}
        
        try:
            # Brave Search API呼び出し
            headers = {'X-Subscription-Token': self.brave_api_key}
            params = {
                'q': f'"{name}" 日本',
                'count': 20,
                'lang': 'ja'
            }
            
            response = requests.get(
                'https://api.search.brave.com/res/v1/web/search',
                headers=headers,
                params=params,
                timeout=10
            )
            
            self._increment_api_usage('brave')
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('web', {}).get('results', [])
                
                # スコア計算
                score = min(10.0, len(results) * 0.5)  # 検索結果数に基づくスコア
                
                # 特定のドメインでの言及をチェック
                major_sites = ['wikipedia.org', 'yahoo.co.jp', 'nhk.or.jp', 'asahi.com']
                major_mentions = sum(1 for r in results if any(site in r.get('url', '') for site in major_sites))
                score = min(10.0, score + major_mentions * 0.5)
                
                result = {
                    'found': len(results) > 0,
                    'score': score,
                    'result_count': len(results),
                    'major_mentions': major_mentions
                }
                
                self._save_cache(name, 'brave', result)
                return result
            
        except Exception as e:
            logger.warning(f"Brave Search エラー ({name}): {e}")
        
        return {'found': False, 'score': 0}
    
    def search_news(self, name: str) -> Dict:
        """ニュース検索（Brave News API）"""
        # キャッシュチェック
        cached = self._load_cache(name, 'news', max_age_hours=24)
        if cached:
            return cached
        
        if not self._check_api_limit('brave') or not self.brave_api_key:
            return {'found': False, 'score': 0}
        
        try:
            headers = {'X-Subscription-Token': self.brave_api_key}
            params = {
                'q': f'"{name}"',
                'count': 10,
                'lang': 'ja'
            }
            
            response = requests.get(
                'https://api.search.brave.com/res/v1/news/search',
                headers=headers,
                params=params,
                timeout=10
            )
            
            self._increment_api_usage('brave')
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                # 最近のニュース記事数に基づくスコア
                recent_news = 0
                for article in results:
                    pub_date = article.get('published', {}).get('date', '')
                    if pub_date:
                        # 最近1年以内の記事をカウント
                        try:
                            article_date = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                            if (datetime.now() - article_date).days < 365:
                                recent_news += 1
                        except:
                            pass
                
                score = min(10.0, recent_news * 1.5)
                
                result = {
                    'found': len(results) > 0,
                    'score': score,
                    'article_count': len(results),
                    'recent_news': recent_news
                }
                
                self._save_cache(name, 'news', result)
                return result
                
        except Exception as e:
            logger.warning(f"News Search エラー ({name}): {e}")
        
        return {'found': False, 'score': 0}
    
    def calculate_lesson_value(self, name: str, description: str = '') -> float:
        """教訓的価値を計算"""
        # 教訓的キーワード
        positive_keywords = ['ノーベル賞', '国民栄誉賞', '文化勲章', '成功', '革新', '先駆者', '偉業']
        negative_keywords = ['事件', '詐欺', '犯罪', 'スキャンダル', '炎上', '逮捕', '破産']
        lesson_keywords = ['教訓', '警鐘', '問題提起', '議論', '社会問題', '改革']
        
        score = 5.0  # 基本スコア
        
        # 説明文のキーワードチェック
        desc_lower = description.lower()
        
        # ポジティブな教訓
        if any(keyword in desc_lower for keyword in positive_keywords):
            score += 2.0
        
        # ネガティブだが教訓的価値
        if any(keyword in desc_lower for keyword in negative_keywords):
            if any(lesson in desc_lower for lesson in lesson_keywords):
                score += 1.5  # 教訓として価値がある
            else:
                score -= 1.0  # 単なるネガティブ
        
        # 教訓的キーワード
        if any(keyword in desc_lower for keyword in lesson_keywords):
            score += 1.0
        
        return min(10.0, max(0.0, score))
    
    def calculate_comprehensive_score(self, name: str, occupation: str = '', 
                                     description: str = '', min_score: float = 0.0) -> Tuple[float, Dict]:
        """
        包括的な知名度スコアを計算
        
        Returns:
            Tuple[float, Dict]: (最終スコア, 詳細情報)
        """
        logger.info(f"包括的スコア計算開始: {name}")
        
        scores = {}
        details = {}
        
        # 1. Wikipedia スコア
        wiki_result = self.wikipedia_system.search_wikipedia(name)
        if wiki_result.get('found'):
            wiki_score = self.wikipedia_system.calculate_recognition_score(wiki_result)
            scores['wikipedia'] = wiki_score
            details['wikipedia'] = wiki_result
        else:
            scores['wikipedia'] = 0.0
            details['wikipedia'] = {'found': False}
        
        # 2. Web検索スコア（Brave Search）
        if self.brave_api_key:
            brave_result = self.search_brave(name)
            scores['web_search'] = brave_result.get('score', 0.0)
            details['brave'] = brave_result
        else:
            scores['web_search'] = 0.0
            details['brave'] = {'found': False, 'reason': 'API key not set'}
        
        # 3. ニューススコア
        if self.brave_api_key:
            news_result = self.search_news(name)
            scores['news'] = news_result.get('score', 0.0)
            details['news'] = news_result
        else:
            scores['news'] = 0.0
            details['news'] = {'found': False}
        
        # 4. ソーシャルスコア（簡易版）
        # 実際のSNS APIは別途実装が必要
        scores['social'] = 5.0  # デフォルト値
        
        # 5. 教訓的価値
        lesson_score = self.calculate_lesson_value(name, description)
        scores['lesson'] = lesson_score
        details['lesson'] = {'score': lesson_score}
        
        # 重み付け平均を計算
        final_score = 0.0
        total_weight = 0.0
        
        for score_type, weight in self.weights.items():
            if score_type in scores:
                final_score += scores[score_type] * weight
                total_weight += weight
        
        if total_weight > 0:
            final_score = final_score / total_weight
        
        # 最低スコア保証
        final_score = max(final_score, min_score)
        
        # 詳細情報をまとめる
        details['scores'] = scores
        details['final_score'] = final_score
        details['min_score'] = min_score
        
        logger.info(f"  {name}: 最終スコア {final_score:.1f} (Wiki: {scores.get('wikipedia', 0):.1f}, Web: {scores.get('web_search', 0):.1f})")
        
        return final_score, details
    
    def process_batch(self, persons: List[Tuple], max_workers: int = 5) -> List[Dict]:
        """
        バッチ処理で複数人物を処理
        
        Args:
            persons: [(name, occupation, description, min_score), ...]のリスト
            max_workers: 並列処理数
            
        Returns:
            処理結果のリスト
        """
        results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 非同期タスクを投入
            future_to_person = {}
            for name, occupation, description, min_score in persons:
                future = executor.submit(
                    self.calculate_comprehensive_score,
                    name, occupation, description, min_score
                )
                future_to_person[future] = (name, occupation, description, min_score)
            
            # 結果を収集
            for future in as_completed(future_to_person):
                name, occupation, description, min_score = future_to_person[future]
                try:
                    score, details = future.result()
                    results.append({
                        'name': name,
                        'occupation': occupation,
                        'description': description,
                        'score': score,
                        'details': details
                    })
                except Exception as e:
                    logger.error(f"処理エラー ({name}): {e}")
                    results.append({
                        'name': name,
                        'occupation': occupation,
                        'description': description,
                        'score': min_score,
                        'error': str(e)
                    })
        
        return results
    
    def get_api_status(self) -> Dict:
        """API使用状況を取得"""
        status = {}
        for api_name, info in self.api_limits.items():
            remaining = info['limit'] - info['used']
            reset_in = max(0, info['window'] - (time.time() - info['reset_time']))
            status[api_name] = {
                'used': info['used'],
                'limit': info['limit'],
                'remaining': remaining,
                'reset_in_seconds': int(reset_in)
            }
        return status


if __name__ == "__main__":
    # テスト実行
    system = MultiAPIRecognitionSystem()
    
    # API状態確認
    print("API使用状況:")
    for api, status in system.get_api_status().items():
        print(f"  {api}: {status['used']}/{status['limit']} (残り: {status['remaining']})")
    
    # テスト人物
    test_persons = [
        ('武満徹', '作曲家', '世界的現代音楽作曲家', 8.5),
        ('相田みつを', '詩人・書家', '「にんげんだもの」作者', 8.0),
        ('関口愛美', 'VTuber', 'おめがシスターズ', 6.5),
    ]
    
    print("\nテスト実行:")
    for name, occupation, description, min_score in test_persons:
        score, details = system.calculate_comprehensive_score(name, occupation, description, min_score)
        print(f"  {name}: {score:.1f}")
        if 'wikipedia' in details and details['wikipedia'].get('found'):
            print(f"    Wikipedia: ✓")
        if 'brave' in details and details['brave'].get('found'):
            print(f"    Web検索: {details['brave'].get('result_count')}件")
