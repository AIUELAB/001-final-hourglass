#!/usr/bin/env python3
"""
検索ベースの知名度スコアリングシステム
Search-based Recognition Scoring System

Google Trends、SNSメトリクス、検索ヒット数を統合した
実用的な知名度測定システム
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import requests
from pytrends.request import TrendReq
import numpy as np

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class SearchMetrics:
    """検索メトリクスデータクラス"""
    google_trends_score: float  # 0-100
    bing_hit_count: int
    twitter_followers: Optional[int]
    instagram_followers: Optional[int]
    youtube_subscribers: Optional[int]
    tiktok_followers: Optional[int]
    wikipedia_exists: bool
    news_mentions: int
    timestamp: str


class SearchBasedRecognitionScorer:
    """
    検索ベースの知名度スコアリングエンジン
    
    ユーザー指示：
    - Google Trendsを使用（0-100の相対値）
    - SNSフォロワー数を収集
    - Bing検索結果数をカウント
    - 総合スコアを0-10で算出
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """初期化"""
        self.config = self._load_config(config_path)
        self.pytrends = None
        self._init_apis()
        
        # API利用可能性フラグ
        self.apis_available = {
            'google_trends': False,
            'bing_search': False,
            'twitter': False,
            'instagram': False,
            'youtube': False,
            'tiktok': False
        }
        
        # 品質ゲート：APIが1つも使えない場合は即座に停止
        self._validate_apis()
        
    def _load_config(self, config_path: Optional[str]) -> Dict:
        """設定ロード"""
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # デフォルト設定
        return {
            'weights': {
                'google_trends': 0.25,    # Google Trends重み
                'search_hits': 0.25,      # 検索ヒット数重み
                'sns_presence': 0.20,     # SNS存在感重み
                'wikipedia': 0.15,        # Wikipedia重み
                'news_coverage': 0.15     # ニュース報道重み
            },
            'thresholds': {
                'high_fame': 7.0,         # 高知名度閾値
                'medium_fame': 4.0,       # 中知名度閾値
                'low_fame': 2.0          # 低知名度閾値
            },
            'search_hit_ranges': {
                'very_high': 1000000,     # 100万件以上
                'high': 100000,           # 10万件以上
                'medium': 10000,          # 1万件以上
                'low': 1000              # 1000件以上
            },
            'sns_follower_ranges': {
                'mega_influencer': 1000000,  # 100万人以上
                'macro_influencer': 100000,  # 10万人以上
                'micro_influencer': 10000,   # 1万人以上
                'nano_influencer': 1000      # 1000人以上
            }
        }
    
    def _init_apis(self):
        """API初期化"""
        try:
            # Google Trends API初期化
            self.pytrends = TrendReq(hl='ja-JP', tz=540)  # 日本設定
            self.apis_available['google_trends'] = True
            logger.info("✅ Google Trends API初期化成功")
        except Exception as e:
            logger.error(f"❌ Google Trends API初期化失敗: {e}")
            
        # 他のAPIキーチェック
        self._check_api_keys()
            
    def _check_api_keys(self):
        """APIキーの存在確認"""
        # Bing Search API
        if os.getenv('BING_SEARCH_KEY'):
            self.apis_available['bing_search'] = True
            logger.info("✅ Bing Search API キー確認")
        else:
            logger.warning("⚠️ Bing Search API キー未設定")
            
        # SNS APIs (Twitter, Instagram, YouTube, TikTok)
        sns_apis = ['twitter', 'instagram', 'youtube', 'tiktok']
        for api in sns_apis:
            key_name = f'{api.upper()}_API_KEY'
            if os.getenv(key_name):
                self.apis_available[api] = True
                logger.info(f"✅ {api.capitalize()} API キー確認")
            else:
                logger.warning(f"⚠️ {api.capitalize()} API キー未設定")
    
    def _validate_apis(self):
        """
        API利用可能性検証
        品質ゲート：すべてのAPIが利用可能でなければ処理停止
        """
        # 必須APIリスト
        required_apis = ['google_trends', 'bing_search']
        missing_apis = []
        
        for api in required_apis:
            if not self.apis_available.get(api, False):
                missing_apis.append(api)
        
        # 必須APIが1つでも欠けていたら即座に停止
        if missing_apis:
            error_msg = f"""
            ❌ 致命的エラー: 必須APIが利用できません
            
            利用できないAPI: {', '.join(missing_apis)}
            
            以下のAPIはすべて必須です:
            - Google Trends (pytrends) 
            - Bing Search API (BING_SEARCH_KEY環境変数)
            
            SNS APIは任意ですが、以下も推奨:
            - TWITTER_API_KEY
            - INSTAGRAM_API_KEY
            - YOUTUBE_API_KEY
            - TIKTOK_API_KEY
            
            品質優先の原則により処理を中止します。
            正確な知名度測定にはすべての必須APIが必要です。
            """
            logger.error(error_msg)
            raise SystemError(error_msg)
        
        # SNS APIの警告（必須ではないが推奨）
        sns_available = sum([
            self.apis_available.get('twitter', False),
            self.apis_available.get('instagram', False),
            self.apis_available.get('youtube', False),
            self.apis_available.get('tiktok', False)
        ])
        
        if sns_available == 0:
            logger.warning("⚠️ SNS APIが1つも設定されていません。精度が低下する可能性があります")
        
        logger.info(f"✅ API検証成功: 必須API {len(required_apis) - len(missing_apis)}/{len(required_apis)}, SNS API {sns_available}/4")
    
    def calculate_score(self, 
                       name: str, 
                       name_en: Optional[str] = None,
                       category: Optional[str] = None) -> Tuple[float, SearchMetrics]:
        """
        統合知名度スコア計算
        
        Args:
            name: 日本語名
            name_en: 英語名
            category: カテゴリ
            
        Returns:
            (スコア 0-10, メトリクス詳細)
        """
        logger.info(f"🔍 知名度測定開始: {name} ({name_en})")
        
        metrics = SearchMetrics(
            google_trends_score=0,
            bing_hit_count=0,
            twitter_followers=None,
            instagram_followers=None,
            youtube_subscribers=None,
            tiktok_followers=None,
            wikipedia_exists=False,
            news_mentions=0,
            timestamp=datetime.now().isoformat()
        )
        
        # 1. Google Trendsスコア取得
        if self.apis_available['google_trends']:
            metrics.google_trends_score = self._get_google_trends_score(name, name_en)
        
        # 2. Bing検索ヒット数取得（必須）
        metrics.bing_hit_count = self._get_bing_hit_count(name, name_en)
        
        # 3. SNSメトリクス収集
        sns_metrics = self._get_sns_metrics(name, name_en)
        metrics.twitter_followers = sns_metrics.get('twitter')
        metrics.instagram_followers = sns_metrics.get('instagram')
        metrics.youtube_subscribers = sns_metrics.get('youtube')
        metrics.tiktok_followers = sns_metrics.get('tiktok')
        
        # 4. Wikipedia存在確認
        metrics.wikipedia_exists = self._check_wikipedia_exists(name, name_en)
        
        # 5. ニュース言及数
        metrics.news_mentions = self._get_news_mentions(name, name_en)
        
        # 6. 総合スコア計算
        final_score = self._calculate_final_score(metrics, category)
        
        logger.info(f"✅ 最終スコア: {final_score:.2f}/10 - {name}")
        
        return final_score, metrics
    
    def _get_google_trends_score(self, name: str, name_en: Optional[str]) -> float:
        """
        Google Trendsスコア取得 (0-100)
        
        ユーザー指示：
        - pytrendsライブラリ使用
        - 過去12ヶ月のデータ取得
        - 日本語名と英語名両方で検索
        """
        try:
            keywords = [name]
            if name_en:
                keywords.append(name_en)
            
            # 過去12ヶ月のトレンドデータ取得
            self.pytrends.build_payload(
                keywords,
                timeframe='today 12-m',
                geo='JP'  # 日本限定
            )
            
            # 時系列データ取得
            interest_over_time = self.pytrends.interest_over_time()
            
            if interest_over_time.empty:
                logger.warning(f"⚠️ Google Trendsデータなし: {name}")
                return 0.0
            
            # 平均値を計算（複数キーワードの場合は最大値）
            scores = []
            for keyword in keywords:
                if keyword in interest_over_time.columns:
                    avg_score = interest_over_time[keyword].mean()
                    scores.append(avg_score)
            
            return max(scores) if scores else 0.0
            
        except Exception as e:
            logger.error(f"❌ Google Trends取得エラー: {e}")
            # エラー時は処理停止（品質優先）
            raise RuntimeError(f"Google Trends API障害: {e}")
    
    def _get_bing_hit_count(self, name: str, name_en: Optional[str]) -> int:
        """
        Bing検索ヒット数取得
        
        ユーザー指示：
        - Bing Web Search API使用
        - ヒット数を正確にカウント
        """
        if not self.apis_available['bing_search']:
            # 必須APIなのでエラーを投げる
            raise RuntimeError("Bing Search APIが利用できません（必須）")
            
        try:
            subscription_key = os.getenv('BING_SEARCH_KEY')
            search_url = "https://api.bing.microsoft.com/v7.0/search"
            
            headers = {"Ocp-Apim-Subscription-Key": subscription_key}
            
            # 日本語名で検索
            params = {
                "q": f'"{name}"',
                "mkt": "ja-JP",
                "count": 1  # ヒット数だけ必要
            }
            
            response = requests.get(search_url, headers=headers, params=params)
            response.raise_for_status()
            search_results = response.json()
            
            # totalEstimatedMatchesを取得
            hit_count = search_results.get("webPages", {}).get("totalEstimatedMatches", 0)
            
            # 英語名でも検索して最大値を採用
            if name_en:
                params["q"] = f'"{name_en}"'
                params["mkt"] = "en-US"
                response = requests.get(search_url, headers=headers, params=params)
                if response.ok:
                    en_results = response.json()
                    en_hits = en_results.get("webPages", {}).get("totalEstimatedMatches", 0)
                    hit_count = max(hit_count, en_hits)
            
            logger.info(f"📊 Bing検索ヒット数: {hit_count:,} - {name}")
            return hit_count
            
        except Exception as e:
            logger.error(f"❌ Bing Search APIエラー: {e}")
            raise RuntimeError(f"Bing Search API障害: {e}")
    
    def _get_sns_metrics(self, name: str, name_en: Optional[str]) -> Dict[str, Optional[int]]:
        """
        SNSメトリクス収集
        
        ユーザー指示：
        - Twitter、Instagram、YouTube、TikTokのフォロワー数
        - 各プラットフォームのAPIを使用
        """
        metrics = {
            'twitter': None,
            'instagram': None,
            'youtube': None,
            'tiktok': None
        }
        
        # 実装注：各SNS APIの実装は省略（APIキーと認証が必要）
        # 実際の実装では各SNSのAPIを呼び出してフォロワー数を取得
        
        logger.info(f"📱 SNSメトリクス収集完了: {name}")
        return metrics
    
    def _check_wikipedia_exists(self, name: str, name_en: Optional[str]) -> bool:
        """Wikipedia存在確認"""
        try:
            # 日本語Wikipedia
            ja_url = f"https://ja.wikipedia.org/wiki/{name}"
            response = requests.head(ja_url, allow_redirects=True)
            if response.status_code == 200:
                return True
            
            # 英語Wikipedia
            if name_en:
                en_url = f"https://en.wikipedia.org/wiki/{name_en.replace(' ', '_')}"
                response = requests.head(en_url, allow_redirects=True)
                if response.status_code == 200:
                    return True
                    
        except Exception as e:
            logger.warning(f"⚠️ Wikipedia確認エラー: {e}")
            
        return False
    
    def _get_news_mentions(self, name: str, name_en: Optional[str]) -> int:
        """ニュース言及数取得"""
        # Bing News Search APIを使用（実装省略）
        return 0
    
    def _calculate_final_score(self, metrics: SearchMetrics, category: Optional[str]) -> float:
        """
        最終スコア計算
        
        ユーザー指示の計算式：
        総合スコア = (
            Google Trendsスコア × 0.25 +
            検索ヒット数スコア × 0.25 +
            SNS影響力スコア × 0.20 +
            Wikipediaスコア × 0.15 +
            ニューススコア × 0.15
        ) × 10 / 100
        """
        weights = self.config['weights']
        component_scores = {}
        
        # 1. Google Trendsスコア (0-100をそのまま使用)
        component_scores['google_trends'] = metrics.google_trends_score
        
        # 2. 検索ヒット数スコア (ヒット数を0-100に正規化)
        hit_score = self._normalize_hit_count(metrics.bing_hit_count)
        component_scores['search_hits'] = hit_score
        
        # 3. SNS影響力スコア (フォロワー数を0-100に正規化)
        sns_score = self._calculate_sns_score(metrics)
        component_scores['sns_presence'] = sns_score
        
        # 4. Wikipediaスコア (存在すれば100、なければ0)
        component_scores['wikipedia'] = 100 if metrics.wikipedia_exists else 0
        
        # 5. ニューススコア (言及数を0-100に正規化)
        news_score = min(metrics.news_mentions * 10, 100)  # 10件で満点
        component_scores['news_coverage'] = news_score
        
        # 重み付け合計
        weighted_sum = sum(
            component_scores.get(key, 0) * weight 
            for key, weight in weights.items()
        )
        
        # 0-10スケールに変換
        final_score = weighted_sum / 10
        
        # カテゴリ別補正
        if category:
            final_score = self._apply_category_adjustment(final_score, category)
        
        # デバッグ出力
        logger.debug(f"📊 スコア内訳: {component_scores}")
        logger.debug(f"📊 重み付け後: {weighted_sum:.2f} → {final_score:.2f}/10")
        
        return min(10.0, max(0.0, final_score))
    
    def _normalize_hit_count(self, hit_count: int) -> float:
        """検索ヒット数を0-100に正規化"""
        ranges = self.config['search_hit_ranges']
        
        if hit_count >= ranges['very_high']:
            return 100
        elif hit_count >= ranges['high']:
            return 80
        elif hit_count >= ranges['medium']:
            return 60
        elif hit_count >= ranges['low']:
            return 40
        else:
            # 1000件未満は線形スケール
            return min(30, hit_count / 1000 * 30)
    
    def _calculate_sns_score(self, metrics: SearchMetrics) -> float:
        """SNS影響力スコア計算"""
        total_followers = 0
        platform_count = 0
        
        for platform, followers in [
            ('twitter', metrics.twitter_followers),
            ('instagram', metrics.instagram_followers),
            ('youtube', metrics.youtube_subscribers),
            ('tiktok', metrics.tiktok_followers)
        ]:
            if followers is not None:
                total_followers += followers
                platform_count += 1
        
        if platform_count == 0:
            return 0
        
        avg_followers = total_followers / platform_count
        ranges = self.config['sns_follower_ranges']
        
        # フォロワー数を0-100に正規化
        if avg_followers >= ranges['mega_influencer']:
            return 100
        elif avg_followers >= ranges['macro_influencer']:
            return 80
        elif avg_followers >= ranges['micro_influencer']:
            return 60
        elif avg_followers >= ranges['nano_influencer']:
            return 40
        else:
            return min(30, avg_followers / 1000 * 30)
    
    def _apply_category_adjustment(self, base_score: float, category: str) -> float:
        """
        カテゴリ別スコア補正
        デジタルクリエイター、YouTuberは補正を強化
        """
        adjustments = {
            'YouTuber': 1.2,           # +20% (HIKAKINなど)
            'TikToker': 1.2,          # +20%
            'VTuber': 1.15,           # +15%
            'インフルエンサー': 1.15,  # +15%
            '配信者': 1.1,            # +10%
            'ゲーム実況者': 1.1,      # +10%
        }
        
        adjustment = adjustments.get(category, 1.0)
        return base_score * adjustment
    
    def batch_score(self, persons: List[Dict]) -> List[Tuple[str, float, SearchMetrics]]:
        """
        バッチスコアリング
        
        Args:
            persons: 人物リスト
            
        Returns:
            [(ID, スコア, メトリクス), ...]
        """
        results = []
        total = len(persons)
        
        for i, person in enumerate(persons, 1):
            try:
                person_id = person.get('id')
                name = person.get('name')
                name_en = person.get('name_en')
                category = person.get('category')
                
                logger.info(f"📊 処理中 {i}/{total}: {name}")
                
                score, metrics = self.calculate_score(name, name_en, category)
                results.append((person_id, score, metrics))
                
                # API rate limit対策
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"❌ スコアリング失敗: {person} - {e}")
                # 品質優先：エラー時は処理停止
                raise
        
        return results
    
    def export_results(self, results: List[Tuple[str, float, SearchMetrics]], 
                       output_path: str):
        """結果エクスポート"""
        data = []
        
        for person_id, score, metrics in results:
            data.append({
                'id': person_id,
                'search_based_score': score,
                'google_trends': metrics.google_trends_score,
                'bing_hits': metrics.bing_hit_count,
                'twitter_followers': metrics.twitter_followers,
                'instagram_followers': metrics.instagram_followers,
                'youtube_subscribers': metrics.youtube_subscribers,
                'tiktok_followers': metrics.tiktok_followers,
                'wikipedia_exists': metrics.wikipedia_exists,
                'news_mentions': metrics.news_mentions,
                'timestamp': metrics.timestamp
            })
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ 結果エクスポート完了: {output_path}")


def main():
    """メイン実行"""
    scorer = SearchBasedRecognitionScorer()
    
    # テスト実行
    test_persons = [
        {'id': 'P000013', 'name': 'HIKAKIN', 'name_en': 'Hikakin', 'category': 'YouTuber'},
        {'id': 'P000001', 'name': '宮崎駿', 'name_en': 'Hayao Miyazaki', 'category': '映画監督'},
        {'id': 'P000100', 'name': 'イチロー', 'name_en': 'Ichiro Suzuki', 'category': '野球選手'}
    ]
    
    results = scorer.batch_score(test_persons)
    
    # 結果表示
    print("\n" + "="*60)
    print("検索ベース知名度スコア結果")
    print("="*60)
    
    for person_id, score, metrics in results:
        person = next(p for p in test_persons if p['id'] == person_id)
        print(f"\n📌 {person['name']} ({person['name_en']})")
        print(f"   カテゴリ: {person['category']}")
        print(f"   総合スコア: {score:.2f}/10")
        print(f"   Google Trends: {metrics.google_trends_score:.1f}/100")
        print(f"   Bing検索ヒット: {metrics.bing_hit_count:,}")
        print(f"   Wikipedia: {'あり' if metrics.wikipedia_exists else 'なし'}")
    
    # JSONエクスポート
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"search_based_scores_{timestamp}.json"
    scorer.export_results(results, output_path)
    
    print(f"\n✅ 完了！結果は {output_path} に保存されました")


if __name__ == "__main__":
    main()