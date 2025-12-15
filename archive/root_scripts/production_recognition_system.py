#!/usr/bin/env python3
"""
本番用知名度評価システム
実際のAPIを統合した完全版
"""

import os
import asyncio
import aiohttp
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import hashlib
import time
from collections import deque
import pickle

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'production_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class APIProvider(Enum):
    """APIプロバイダー定義"""
    GOOGLE = "google"
    YOUTUBE = "youtube"
    TWITTER = "twitter"
    NEWS = "news"
    BRAVE = "brave"


@dataclass
class APIConfig:
    """API設定"""
    provider: APIProvider
    endpoint: str
    api_key: str
    rate_limit: int  # requests per minute
    retry_limit: int = 3
    timeout: int = 30


class ProductionRecognitionSystem:
    """本番用知名度評価システム"""

    def __init__(self):
        """初期化"""
        self.api_configs = self._load_api_configs()
        self.cache = self._initialize_cache()
        self.rate_limiters = {}
        self.stats = {
            'total_processed': 0,
            'api_calls': 0,
            'cache_hits': 0,
            'ml_skipped': 0,
            'errors': 0,
            'start_time': time.time()
        }

        # ML patterns
        self.ml_patterns = {
            'ultra_famous': [
                'HIKAKIN', '米津玄師', '大谷翔平', '嵐', '新垣結衣',
                'イチロー', '羽生結弦', '錦織圭', '本田圭佑', '香川真司'
            ],
            'fictional_protected': [
                'ドラえもん', '孫悟空', 'ピカチュウ', 'ルフィ', 'ナルト',
                'エヴァンゲリオン', 'セーラームーン', 'アンパンマン',
                '竈門炭治郎', 'サザエさん'
            ],
            'general_patterns': [
                'test', 'テスト', '山田太郎', '田中', 'sample'
            ]
        }

    def _load_api_configs(self) -> Dict[APIProvider, APIConfig]:
        """API設定を読み込み"""
        configs = {}

        # 環境変数から読み込み
        env_file = Path('.env')
        if env_file.exists():
            from dotenv import load_dotenv
            load_dotenv()

        # Google/SerpAPI
        if os.getenv('SERPAPI_API_KEY'):
            configs[APIProvider.GOOGLE] = APIConfig(
                provider=APIProvider.GOOGLE,
                endpoint='https://serpapi.com/search',
                api_key=os.getenv('SERPAPI_API_KEY'),
                rate_limit=100  # 100 requests/minute
            )

        # YouTube Data API
        if os.getenv('YOUTUBE_API_KEY'):
            configs[APIProvider.YOUTUBE] = APIConfig(
                provider=APIProvider.YOUTUBE,
                endpoint='https://www.googleapis.com/youtube/v3/search',
                api_key=os.getenv('YOUTUBE_API_KEY'),
                rate_limit=60  # Quota-based
            )

        # Twitter API v2
        if os.getenv('TWITTER_BEARER_TOKEN'):
            configs[APIProvider.TWITTER] = APIConfig(
                provider=APIProvider.TWITTER,
                endpoint='https://api.twitter.com/2/tweets/search/recent',
                api_key=os.getenv('TWITTER_BEARER_TOKEN'),
                rate_limit=450  # 450 requests/15min = 30/min
            )

        # News API
        if os.getenv('NEWS_API_KEY'):
            configs[APIProvider.NEWS] = APIConfig(
                provider=APIProvider.NEWS,
                endpoint='https://newsapi.org/v2/everything',
                api_key=os.getenv('NEWS_API_KEY'),
                rate_limit=500  # 500 requests/day
            )

        # Brave Search API
        if os.getenv('BRAVE_API_KEY'):
            configs[APIProvider.BRAVE] = APIConfig(
                provider=APIProvider.BRAVE,
                endpoint='https://api.search.brave.com/res/v1/web/search',
                api_key=os.getenv('BRAVE_API_KEY'),
                rate_limit=1000  # 1000 requests/month (free tier)
            )

        logger.info(f"✅ API設定読み込み完了: {list(configs.keys())}")
        return configs

    def _initialize_cache(self) -> dict:
        """キャッシュ初期化"""
        cache_file = Path('production_cache.pkl')
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    cache = pickle.load(f)
                logger.info(f"📦 キャッシュ読み込み: {len(cache)}件")
                return cache
            except:
                pass
        return {}

    def save_cache(self):
        """キャッシュ保存"""
        try:
            with open('production_cache.pkl', 'wb') as f:
                pickle.dump(self.cache, f)
            logger.info(f"💾 キャッシュ保存: {len(self.cache)}件")
        except Exception as e:
            logger.error(f"キャッシュ保存エラー: {e}")

    async def evaluate_person(self, person_data: dict) -> dict:
        """個人の知名度を評価"""

        person_id = person_data.get('person_id', '')
        person_name = person_data.get('person_name_ja', person_data.get('person_name', ''))
        category = person_data.get('category', '')

        # Phase 1: ML Pre-filtering
        ml_score = self._ml_prefilter(person_name, category)
        if ml_score is not None:
            self.stats['ml_skipped'] += 1
            return {
                'person_id': person_id,
                'person_name': person_name,
                'final_score': ml_score,
                'method': 'ML判定',
                'confidence': 0.95,
                'data_sources': ['ML'],
                'timestamp': datetime.now().isoformat()
            }

        # Phase 2: Cache check
        cache_key = f"{person_name}:{category}"
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            # Check cache freshness (7 days)
            if self._is_cache_fresh(cached.get('timestamp')):
                self.stats['cache_hits'] += 1
                return cached

        # Phase 3: API evaluation
        api_results = await self._evaluate_with_apis(person_name, category)

        # Aggregate results
        final_score = self._aggregate_scores(api_results)

        result = {
            'person_id': person_id,
            'person_name': person_name,
            'final_score': final_score,
            'method': 'API評価',
            'confidence': self._calculate_confidence(api_results),
            'data_sources': list(api_results.keys()),
            'api_scores': api_results,
            'timestamp': datetime.now().isoformat()
        }

        # Cache the result
        self.cache[cache_key] = result

        return result

    def _ml_prefilter(self, name: str, category: str) -> Optional[float]:
        """ML事前フィルタリング"""

        # Ultra famous
        if any(keyword in str(name) for keyword in self.ml_patterns['ultra_famous']):
            return 9.5

        # Fictional protected
        if any(keyword in str(name) for keyword in self.ml_patterns['fictional_protected']):
            return 8.5

        # General patterns
        if any(pattern in str(name) for pattern in self.ml_patterns['general_patterns']):
            return 2.0

        # Category-based quick decisions
        category_scores = {
            '架空': 7.5,
            'テスト': 1.0,
            'プレースホルダー': 1.0
        }

        if category in category_scores:
            return category_scores[category]

        return None

    def _is_cache_fresh(self, timestamp: str, max_age_days: int = 7) -> bool:
        """キャッシュの鮮度確認"""
        if not timestamp:
            return False

        try:
            cached_time = datetime.fromisoformat(timestamp)
            age = datetime.now() - cached_time
            return age.days < max_age_days
        except:
            return False

    async def _evaluate_with_apis(self, name: str, category: str) -> dict:
        """API群で評価"""
        results = {}
        tasks = []

        # Create API tasks
        for provider, config in self.api_configs.items():
            if provider == APIProvider.GOOGLE:
                task = self._search_google(name, config)
            elif provider == APIProvider.YOUTUBE:
                task = self._search_youtube(name, config)
            elif provider == APIProvider.TWITTER:
                task = self._search_twitter(name, config)
            elif provider == APIProvider.NEWS:
                task = self._search_news(name, config)
            elif provider == APIProvider.BRAVE:
                task = self._search_brave(name, config)
            else:
                continue

            tasks.append((provider, task))

        # Execute concurrently
        if tasks:
            for provider, task in tasks:
                try:
                    result = await task
                    if result is not None:
                        results[provider.value] = result
                        self.stats['api_calls'] += 1
                except Exception as e:
                    logger.warning(f"API error ({provider.value}): {e}")
                    self.stats['errors'] += 1

        return results

    async def _search_google(self, query: str, config: APIConfig) -> Optional[float]:
        """Google検索（SerpAPI）"""
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    'q': query,
                    'api_key': config.api_key,
                    'engine': 'google',
                    'gl': 'jp',
                    'hl': 'ja'
                }

                async with session.get(config.endpoint, params=params, timeout=config.timeout) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Extract result count
                        total_results = data.get('search_information', {}).get('total_results', 0)
                        # Convert to score (log scale)
                        if total_results > 0:
                            score = min(10, np.log10(total_results))
                            return score
        except Exception as e:
            logger.error(f"Google search error: {e}")

        return None

    async def _search_youtube(self, query: str, config: APIConfig) -> Optional[float]:
        """YouTube検索"""
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    'part': 'snippet',
                    'q': query,
                    'key': config.api_key,
                    'maxResults': 10,
                    'type': 'video'
                }

                async with session.get(config.endpoint, params=params, timeout=config.timeout) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Get total results
                        total_results = data.get('pageInfo', {}).get('totalResults', 0)
                        # Convert to score
                        if total_results > 0:
                            score = min(10, total_results / 100)
                            return score
        except Exception as e:
            logger.error(f"YouTube search error: {e}")

        return None

    async def _search_twitter(self, query: str, config: APIConfig) -> Optional[float]:
        """Twitter検索"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'Bearer {config.api_key}'
                }
                params = {
                    'query': query,
                    'max_results': 10
                }

                async with session.get(config.endpoint, headers=headers, params=params, timeout=config.timeout) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Get result count
                        result_count = data.get('meta', {}).get('result_count', 0)
                        # Convert to score
                        score = min(10, result_count)
                        return score
        except Exception as e:
            logger.error(f"Twitter search error: {e}")

        return None

    async def _search_news(self, query: str, config: APIConfig) -> Optional[float]:
        """ニュース検索"""
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    'q': query,
                    'apiKey': config.api_key,
                    'language': 'ja',
                    'sortBy': 'popularity'
                }

                async with session.get(config.endpoint, params=params, timeout=config.timeout) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Get article count
                        total_results = data.get('totalResults', 0)
                        # Convert to score
                        if total_results > 0:
                            score = min(10, total_results / 10)
                            return score
        except Exception as e:
            logger.error(f"News search error: {e}")

        return None

    async def _search_brave(self, query: str, config: APIConfig) -> Optional[float]:
        """Brave検索"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'X-Subscription-Token': config.api_key
                }
                params = {
                    'q': query,
                    'country': 'jp'
                }

                async with session.get(config.endpoint, headers=headers, params=params, timeout=config.timeout) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Get result count (estimated)
                        results = data.get('web', {}).get('results', [])
                        # Convert to score based on result quality
                        if results:
                            score = min(10, len(results))
                            return score
        except Exception as e:
            logger.error(f"Brave search error: {e}")

        return None

    def _aggregate_scores(self, api_results: dict) -> float:
        """スコアを集約"""
        if not api_results:
            return 5.0  # Default middle score

        scores = [score for score in api_results.values() if score is not None]

        if not scores:
            return 5.0

        # Weighted average
        weights = {
            'google': 0.3,
            'youtube': 0.2,
            'twitter': 0.2,
            'news': 0.15,
            'brave': 0.15
        }

        weighted_sum = 0
        weight_total = 0

        for source, score in api_results.items():
            if score is not None:
                weight = weights.get(source, 0.1)
                weighted_sum += score * weight
                weight_total += weight

        if weight_total > 0:
            return weighted_sum / weight_total

        return np.mean(scores)

    def _calculate_confidence(self, api_results: dict) -> float:
        """信頼度を計算"""
        if not api_results:
            return 0.0

        # Based on number of successful API calls
        success_rate = len(api_results) / len(self.api_configs)

        # Adjust for consistency
        if len(api_results) > 1:
            scores = list(api_results.values())
            std_dev = np.std(scores)
            consistency = 1.0 - min(1.0, std_dev / 5.0)
            confidence = (success_rate * 0.7) + (consistency * 0.3)
        else:
            confidence = success_rate * 0.5

        return min(1.0, confidence)

    async def process_database(self, csv_path: str, output_path: str = None):
        """データベース処理"""
        logger.info(f"📂 データベース読み込み: {csv_path}")

        # Load data
        df = pd.read_csv(csv_path, encoding='utf-8-sig')
        logger.info(f"✅ {len(df)}件のレコード読み込み完了")

        # Process in batches
        batch_size = 10
        results = []

        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i+batch_size]

            # Process batch
            tasks = []
            for idx, row in batch.iterrows():
                task = self.evaluate_person(row.to_dict())
                tasks.append(task)

            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)

            self.stats['total_processed'] += len(batch_results)

            # Progress
            progress = (self.stats['total_processed'] / len(df)) * 100
            print(f"\r進捗: {progress:.1f}% ({self.stats['total_processed']}/{len(df)})", end='')

        print()  # New line

        # Create result dataframe
        result_df = pd.DataFrame(results)

        # Merge with original data
        for col in df.columns:
            if col not in result_df.columns:
                result_df[col] = df[col]

        # Sort by score
        result_df = result_df.sort_values('final_score', ascending=False)

        # Save results
        if output_path:
            result_df.to_csv(output_path, index=False, encoding='utf-8-sig')
            logger.info(f"💾 結果を保存: {output_path}")

        # Save cache
        self.save_cache()

        # Display statistics
        self._display_statistics(result_df)

        return result_df

    def _display_statistics(self, df):
        """統計情報表示"""
        elapsed = time.time() - self.stats['start_time']

        print("\n" + "=" * 70)
        print("✅ 処理完了")
        print("=" * 70)

        print(f"\n📊 処理統計:")
        print(f"  総処理数: {self.stats['total_processed']}件")
        print(f"  API呼び出し: {self.stats['api_calls']}回")
        print(f"  キャッシュヒット: {self.stats['cache_hits']}件")
        print(f"  ML判定: {self.stats['ml_skipped']}件")
        print(f"  エラー: {self.stats['errors']}件")
        print(f"  処理時間: {elapsed:.1f}秒")

        if self.stats['total_processed'] > 0:
            print(f"  平均処理速度: {self.stats['total_processed']/elapsed:.1f}件/秒")


async def main():
    """メイン実行"""
    system = ProductionRecognitionSystem()

    # Check API configuration
    if not system.api_configs:
        logger.error("❌ APIが設定されていません。.envファイルを確認してください。")
        return

    print("\n" + "=" * 70)
    print("🚀 本番用知名度評価システム")
    print("=" * 70)
    print(f"利用可能API: {list(system.api_configs.keys())}")

    # Process database
    csv_path = "ultra_think_EPISODE_FINAL_20250901_020106_fixed.csv"
    output_path = f"production_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    await system.process_database(csv_path, output_path)


if __name__ == "__main__":
    asyncio.run(main())
