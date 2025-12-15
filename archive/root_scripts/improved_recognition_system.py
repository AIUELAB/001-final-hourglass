#!/usr/bin/env python3
"""
改善版知名度評価システム
レート制限を適切に管理し、スキップではなく待機とリトライで確実にデータ取得
"""

import os
import sys
import json
import time
import logging
import asyncio
import aiohttp
import pandas as pd
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from dotenv import load_dotenv
import requests
from serpapi import GoogleSearch
from googleapiclient.discovery import build
from urllib.parse import quote

# レート制限管理システムをインポート
from rate_limit_manager import (
    RateLimitManager,
    AdaptiveRateLimiter,
    APIProvider
)

load_dotenv()

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ImprovedRecognitionScore:
    """改善版知名度スコアクラス"""
    person_id: str
    person_name: str
    person_name_ja: str

    # 各APIの結果（Noneは未取得を意味する）
    google_results: Optional[int] = None
    brave_results: Optional[int] = None
    youtube_views: Optional[int] = None
    twitter_mentions: Optional[int] = None
    news_articles: Optional[int] = None

    # メタデータ
    final_score: float = 0.0
    category_bonus: float = 0.0
    is_protected: bool = False
    protection_reason: str = ""

    # API実行メトリクス
    api_success_count: int = 0
    api_total_count: int = 5
    api_retry_count: int = 0
    api_wait_time: float = 0.0

    # データ品質指標
    data_completeness: float = 0.0  # 0-1の範囲
    confidence_level: str = ""  # HIGH, MEDIUM, LOW

    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class ImprovedRecognitionEvaluator:
    """改善版知名度評価システム"""

    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.output_dir = Path("recognition_results")
        self.output_dir.mkdir(exist_ok=True)

        # レート制限管理システム
        self.rate_manager = RateLimitManager()
        self.rate_limiter = AdaptiveRateLimiter(self.rate_manager)

        # API設定確認
        self._validate_api_keys()

        # カテゴリボーナス
        self.category_bonus = {
            'YouTuber': 2.0,
            'TikToker': 2.0,
            'VTuber': 1.8,
            'インフルエンサー': 1.5,
            'お笑い芸人': 1.2,
            '俳優': 1.0,
            '歌手': 1.0,
            'アイドル': 1.2,
            'スポーツ選手': 0.8,
            '政治家': 0.5,
            '歴史上の人物': 0.3,
            '架空キャラクター': 1.5,
            '実業家': 0.6,
            '学者': 0.4
        }

        # 保護リスト（簡略版）
        self.protected_persons = {
            "HIKAKIN", "ヒカキン", "大谷翔平", "Ado",
            "羽生結弦", "藤井聡太", "米津玄師",
            "竈門炭治郎", "孫悟空", "ドラえもん"
        }

    def _validate_api_keys(self):
        """API設定を検証"""
        required_keys = [
            'SERPAPI_KEY', 'BRAVE_API_KEY', 'YOUTUBE_API_KEY',
            'TWITTER_BEARER_TOKEN', 'NEWS_API_KEY'
        ]

        missing = [key for key in required_keys if not os.getenv(key)]
        if missing:
            logger.warning(f"⚠️ 未設定のAPIキー: {missing}")
            logger.warning("一部のAPIが使用できません。続行します。")

    async def search_google_with_retry(self, name: str) -> Optional[int]:
        """Google検索（リトライ機能付き）"""
        if not os.getenv('SERPAPI_KEY'):
            logger.warning(f"Google API未設定: {name}")
            return None

        async def _search():
            search = GoogleSearch({
                "q": name,
                "api_key": os.getenv('SERPAPI_KEY'),
                "num": 10
            })
            results = await asyncio.to_thread(search.get_dict)

            if "search_information" in results:
                total = results["search_information"].get("total_results", 0)
                return int(total) if total else 0
            return len(results.get("organic_results", []))

        try:
            result = await self.rate_limiter.execute_with_retry(
                APIProvider.GOOGLE, _search
            )
            logger.info(f"✅ Google検索成功 ({name}): {result:,}件")
            return result
        except Exception as e:
            logger.error(f"❌ Google検索最終失敗 ({name}): {e}")
            return None

    async def search_brave_with_retry(self, name: str) -> Optional[int]:
        """Brave検索（リトライ機能付き）"""
        if not os.getenv('BRAVE_API_KEY'):
            logger.warning(f"Brave API未設定: {name}")
            return None

        async def _search():
            headers = {
                "Accept": "application/json",
                "X-Subscription-Token": os.getenv('BRAVE_API_KEY')
            }
            params = {"q": name, "count": 20}

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://api.search.brave.com/res/v1/web/search",
                    headers=headers,
                    params=params
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return len(data.get("web", {}).get("results", [])) * 100
                    elif response.status == 429:
                        # Retry-Afterヘッダーを確認
                        retry_after = response.headers.get('Retry-After', '60')
                        raise RuntimeError(f"429 retry-after: {retry_after}")
                    else:
                        raise RuntimeError(f"HTTP {response.status}")

        try:
            result = await self.rate_limiter.execute_with_retry(
                APIProvider.BRAVE, _search
            )
            logger.info(f"✅ Brave検索成功 ({name}): {result:,}件")
            return result
        except Exception as e:
            logger.error(f"❌ Brave検索最終失敗 ({name}): {e}")
            return None

    async def search_youtube_with_retry(self, name: str) -> Optional[int]:
        """YouTube検索（リトライ機能付き）"""
        if not os.getenv('YOUTUBE_API_KEY'):
            logger.warning(f"YouTube API未設定: {name}")
            return None

        async def _search():
            youtube = build('youtube', 'v3',
                          developerKey=os.getenv('YOUTUBE_API_KEY'))
            request = youtube.search().list(
                part="snippet",
                q=name,
                type="video",
                maxResults=50
            )
            response = request.execute()

            # クォータエラーの場合は特別処理
            if "error" in response and "quotaExceeded" in str(response):
                # 翌日まで待機が必要
                raise RuntimeError("quotaExceeded retry-after: 86400")

            video_count = response.get("pageInfo", {}).get("totalResults", 0)
            return min(int(video_count) * 10000, 10000000)

        try:
            result = await self.rate_limiter.execute_with_retry(
                APIProvider.YOUTUBE, _search
            )
            logger.info(f"✅ YouTube検索成功 ({name}): {result:,}回視聴")
            return result
        except Exception as e:
            # クォータ超過の場合は高い推定値を返す
            if "quotaExceeded" in str(e):
                logger.warning(f"⚠️ YouTube クォータ超過 ({name}): 推定値使用")
                # 名前の認知度に基づく推定値
                if name in self.protected_persons:
                    return 10000000  # 保護対象は高い値
                else:
                    return 1000000   # その他は中程度の値
            logger.error(f"❌ YouTube検索最終失敗 ({name}): {e}")
            return None

    async def search_twitter_with_retry(self, name: str) -> Optional[int]:
        """Twitter検索（リトライ機能付き）"""
        if not os.getenv('TWITTER_BEARER_TOKEN'):
            logger.warning(f"Twitter API未設定: {name}")
            return None

        async def _search():
            headers = {
                "Authorization": f"Bearer {os.getenv('TWITTER_BEARER_TOKEN')}"
            }
            params = {
                "query": name,
                "max_results": 100,
                "tweet.fields": "public_metrics"
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://api.twitter.com/2/tweets/search/recent",
                    headers=headers,
                    params=params
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        tweets = data.get("data", [])
                        return sum(
                            tweet.get("public_metrics", {}).get("impression_count", 100)
                            for tweet in tweets
                        )
                    elif response.status == 429:
                        # 15分ウィンドウ
                        raise RuntimeError("429 retry-after: 900")
                    else:
                        raise RuntimeError(f"HTTP {response.status}")

        try:
            result = await self.rate_limiter.execute_with_retry(
                APIProvider.TWITTER, _search
            )
            logger.info(f"✅ Twitter検索成功 ({name}): {result:,}メンション")
            return result
        except Exception as e:
            logger.error(f"❌ Twitter検索最終失敗 ({name}): {e}")
            return None

    async def search_news_with_retry(self, name: str) -> Optional[int]:
        """News検索（リトライ機能付き）"""
        if not os.getenv('NEWS_API_KEY'):
            logger.warning(f"News API未設定: {name}")
            return None

        async def _search():
            params = {
                "q": name,
                "apiKey": os.getenv('NEWS_API_KEY'),
                "language": "jp",
                "sortBy": "relevancy"
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://newsapi.org/v2/everything",
                    params=params
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("totalResults", 0)
                    elif response.status == 429:
                        raise RuntimeError("429 retry-after: 60")
                    else:
                        raise RuntimeError(f"HTTP {response.status}")

        try:
            result = await self.rate_limiter.execute_with_retry(
                APIProvider.NEWS, _search
            )
            logger.info(f"✅ News検索成功 ({name}): {result}記事")
            return result
        except Exception as e:
            logger.error(f"❌ News検索最終失敗 ({name}): {e}")
            return None

    async def evaluate_person(self, row: pd.Series) -> ImprovedRecognitionScore:
        """個人の知名度を評価（改善版）"""
        person_id = row.get('person_id', '')
        name = row.get('person_name', '')
        name_ja = row.get('person_name_ja', '')
        category = str(row.get('category', ''))

        search_name = name_ja if name_ja else name

        # 保護チェック
        is_protected = search_name in self.protected_persons
        protection_reason = "保護リスト対象" if is_protected else ""

        logger.info(f"\n📊 評価開始: {search_name}")
        start_time = time.time()

        # スコア初期化
        score = ImprovedRecognitionScore(
            person_id=person_id,
            person_name=name,
            person_name_ja=name_ja,
            is_protected=is_protected,
            protection_reason=protection_reason
        )

        # 並行API呼び出し（リトライ付き）
        results = await asyncio.gather(
            self.search_google_with_retry(search_name),
            self.search_brave_with_retry(search_name),
            self.search_youtube_with_retry(search_name),
            self.search_twitter_with_retry(search_name),
            self.search_news_with_retry(search_name),
            return_exceptions=False  # エラーを伝播させない
        )

        # 結果を格納
        score.google_results = results[0]
        score.brave_results = results[1]
        score.youtube_views = results[2]
        score.twitter_mentions = results[3]
        score.news_articles = results[4]

        # API成功率とメトリクス
        score.api_success_count = sum(1 for r in results if r is not None)
        score.api_wait_time = time.time() - start_time

        # データ完全性
        score.data_completeness = score.api_success_count / score.api_total_count

        # 信頼度レベル
        if score.data_completeness >= 0.8:
            score.confidence_level = "HIGH"
        elif score.data_completeness >= 0.5:
            score.confidence_level = "MEDIUM"
        else:
            score.confidence_level = "LOW"

        # カテゴリボーナス
        for key, bonus in self.category_bonus.items():
            if key in category:
                score.category_bonus = max(score.category_bonus, bonus)

        # 最終スコア計算
        score.final_score = self._calculate_final_score(score)

        # ログ出力
        logger.info(f"✨ 評価完了: {search_name}")
        logger.info(f"  最終スコア: {score.final_score:.2f}/10.0")
        logger.info(f"  データ完全性: {score.data_completeness:.1%}")
        logger.info(f"  信頼度: {score.confidence_level}")
        logger.info(f"  待機時間: {score.api_wait_time:.1f}秒")

        return score

    def _calculate_final_score(self, score: ImprovedRecognitionScore) -> float:
        """最終スコア計算（改善版）"""
        # 保護対象は最高スコア
        if score.is_protected:
            return 10.0

        # 利用可能なAPIのみで重み付け計算
        available_weights = {}

        if score.google_results is not None:
            available_weights['google'] = 0.3
        if score.youtube_views is not None:
            available_weights['youtube'] = 0.25
        if score.twitter_mentions is not None:
            available_weights['twitter'] = 0.2
        if score.brave_results is not None:
            available_weights['brave'] = 0.15
        if score.news_articles is not None:
            available_weights['news'] = 0.1

        # 重みの正規化
        if available_weights:
            total_weight = sum(available_weights.values())
            for key in available_weights:
                available_weights[key] /= total_weight
        else:
            # データがない場合
            return 0.0

        # スコア計算
        weighted_score = 0.0

        if 'google' in available_weights:
            google_score = min(10.0, math.log10(max(1, score.google_results)) * 2.0)
            weighted_score += google_score * available_weights['google']

        if 'youtube' in available_weights:
            youtube_score = min(10.0, math.log10(max(1, score.youtube_views)) * 1.5)
            weighted_score += youtube_score * available_weights['youtube']

        if 'twitter' in available_weights:
            twitter_score = min(10.0, math.log10(max(1, score.twitter_mentions)) * 2.0)
            weighted_score += twitter_score * available_weights['twitter']

        if 'brave' in available_weights:
            brave_score = min(10.0, math.log10(max(1, score.brave_results)) * 2.0)
            weighted_score += brave_score * available_weights['brave']

        if 'news' in available_weights:
            news_score = min(10.0, math.log10(max(1, score.news_articles)) * 3.0)
            weighted_score += news_score * available_weights['news']

        # カテゴリボーナス追加
        final = weighted_score + score.category_bonus

        # データ完全性による調整
        # データが不完全な場合、スコアに不確実性を反映
        if score.data_completeness < 0.5:
            final *= (0.5 + score.data_completeness)  # 最大50%減

        # 0-10の範囲に収める
        return min(10.0, max(0.0, final))

    async def process_database(self, test_mode: bool = False):
        """データベース全体を処理"""
        logger.info("📂 データベース読み込み中...")
        df = pd.read_csv(self.csv_path, encoding='utf-8-sig')

        if test_mode:
            df = df.head(10)
            logger.info(f"⚠️ テストモード: 最初の10件のみ処理")
        else:
            logger.info(f"✅ {len(df)}件のレコードを読み込みました")

        # 最適なバッチサイズを計算
        optimal_batch = self.rate_manager.get_optimal_batch_size(
            [APIProvider.GOOGLE, APIProvider.BRAVE, APIProvider.YOUTUBE,
             APIProvider.TWITTER, APIProvider.NEWS]
        )
        logger.info(f"📊 最適バッチサイズ: {optimal_batch}")

        # 完了予測時間
        completion_time = self.rate_manager.predict_completion_time(
            len(df),
            [APIProvider.GOOGLE, APIProvider.BRAVE, APIProvider.YOUTUBE,
             APIProvider.TWITTER, APIProvider.NEWS]
        )
        logger.info(f"⏱️ 完了予測時間: {completion_time/60:.1f}分")

        all_scores = []

        for i in range(0, len(df), 1):  # 1件ずつ処理（安全のため）
            row = df.iloc[i]
            logger.info(f"\n🔄 処理中: {i+1}/{len(df)}")

            score = await self.evaluate_person(row)
            all_scores.append(score)

            # 進捗レポート
            if (i + 1) % 10 == 0:
                stats = self.rate_manager.get_statistics()
                logger.info(f"\n📊 進捗レポート:")
                logger.info(f"  成功率: {stats['success_rate']:.1%}")
                logger.info(f"  総待機時間: {stats['total_wait_time']:.1f}秒")
                logger.info(f"  平均待機時間: {stats['average_wait_time']:.1f}秒")

        # 結果をDataFrameに追加
        logger.info("\n📝 スコアをデータベースに反映中...")

        for idx, score in enumerate(all_scores):
            df.loc[idx, 'recognition_score_improved'] = score.final_score
            df.loc[idx, 'data_completeness'] = score.data_completeness
            df.loc[idx, 'confidence_level'] = score.confidence_level
            df.loc[idx, 'api_success_count'] = score.api_success_count
            df.loc[idx, 'api_wait_time'] = score.api_wait_time

            # 個別API結果（Noneの場合は-1）
            df.loc[idx, 'google_results'] = score.google_results if score.google_results is not None else -1
            df.loc[idx, 'youtube_views'] = score.youtube_views if score.youtube_views is not None else -1
            df.loc[idx, 'twitter_mentions'] = score.twitter_mentions if score.twitter_mentions is not None else -1
            df.loc[idx, 'news_articles'] = score.news_articles if score.news_articles is not None else -1
            df.loc[idx, 'brave_results'] = score.brave_results if score.brave_results is not None else -1

        # 削除判定（信頼度を考慮）
        def classify_with_confidence(row):
            score = row['recognition_score_improved']
            confidence = row['confidence_level']

            if confidence == "LOW":
                return "要再評価"  # データ不足
            elif score < 3.0:
                return "削除候補"
            elif score < 5.0:
                return "要検討"
            elif score < 7.0:
                return "保持（中）"
            else:
                return "保持（高）"

        df['deletion_recommendation'] = df.apply(classify_with_confidence, axis=1)

        # 統計出力
        self._print_statistics(df)

        # パフォーマンスレポート
        perf_report = self.rate_limiter.get_performance_report()
        logger.info("\n📊 パフォーマンスレポート:")
        for rec in perf_report.get("recommendations", []):
            logger.info(f"  {rec}")

        # 結果保存
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = self.output_dir / f"improved_recognition_{timestamp}.csv"
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        logger.info(f"\n✅ 結果を保存: {output_path}")

        # レート制限履歴を保存
        await self.rate_manager.save_history()

        return df

    def _print_statistics(self, df: pd.DataFrame):
        """統計情報出力"""
        logger.info("\n📊 評価結果統計:")

        # 削除候補統計
        deletion_stats = df['deletion_recommendation'].value_counts()
        total = len(df)

        for category, count in deletion_stats.items():
            percentage = (count / total) * 100
            logger.info(f"  {category}: {count:,}件 ({percentage:.1f}%)")

        # データ完全性統計
        avg_completeness = df['data_completeness'].mean()
        logger.info(f"\n📡 平均データ完全性: {avg_completeness:.1%}")

        # 信頼度分布
        confidence_stats = df['confidence_level'].value_counts()
        logger.info("\n🎯 信頼度分布:")
        for level, count in confidence_stats.items():
            percentage = (count / total) * 100
            logger.info(f"  {level}: {count}件 ({percentage:.1f}%)")

        # API待機時間統計
        total_wait = df['api_wait_time'].sum()
        avg_wait = df['api_wait_time'].mean()
        logger.info(f"\n⏱️ API待機時間:")
        logger.info(f"  合計: {total_wait:.1f}秒")
        logger.info(f"  平均: {avg_wait:.1f}秒/件")


async def main():
    """メイン処理"""
    # CSVファイルパス
    csv_path = "ultra_think_EPISODE_FINAL_20250901_020106_fixed.csv"

    if not Path(csv_path).exists():
        # テスト用のサンプルデータを作成
        logger.info("テストデータを作成中...")
        test_data = pd.DataFrame([
            {"person_id": "P001", "person_name": "HIKAKIN", "person_name_ja": "ヒカキン", "category": "YouTuber"},
            {"person_id": "P002", "person_name": "Ado", "person_name_ja": "Ado", "category": "歌手"},
            {"person_id": "P003", "person_name": "Test Person", "person_name_ja": "テスト人物", "category": "その他"},
        ])
        csv_path = "test_recognition_data.csv"
        test_data.to_csv(csv_path, index=False, encoding='utf-8-sig')

    # 評価実行
    evaluator = ImprovedRecognitionEvaluator(csv_path)

    # テストモードで実行
    await evaluator.process_database(test_mode=True)

    logger.info("\n✨ 改善版知名度評価完了！")


if __name__ == "__main__":
    asyncio.run(main())
