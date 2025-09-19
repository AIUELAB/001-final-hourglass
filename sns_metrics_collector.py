#!/usr/bin/env python3
"""
SNSメトリクス収集モジュール
SNS Metrics Collection Module

Twitter、Instagram、TikTok、YouTubeから
フォロワー数とエンゲージメントを収集
"""

import os
import json
import logging
import time
from typing import Dict, Optional, Tuple, Any
from datetime import datetime
import requests

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SNSMetricsCollector:
    """
    SNSメトリクス収集クラス
    
    各SNSプラットフォームから影響力指標を収集
    """
    
    def __init__(self):
        """初期化"""
        self.apis_available = {
            'twitter': False,
            'instagram': False,
            'youtube': False,
            'tiktok': False
        }
        
        # API認証情報の確認
        self._check_api_credentials()
        
        # メトリクス重み付け
        self.weights = {
            'followers': 0.4,      # フォロワー数
            'engagement': 0.3,     # エンゲージメント率
            'content_count': 0.2,  # コンテンツ数
            'growth_rate': 0.1     # 成長率
        }
    
    def _check_api_credentials(self):
        """API認証情報の確認"""
        
        # Twitter API
        if all([
            os.getenv('TWITTER_API_KEY'),
            os.getenv('TWITTER_API_SECRET'),
            os.getenv('TWITTER_BEARER_TOKEN')
        ]):
            self.apis_available['twitter'] = True
            logger.info("✅ Twitter API認証情報確認")
        else:
            logger.warning("⚠️ Twitter API認証情報未設定")
        
        # Instagram API
        if all([
            os.getenv('INSTAGRAM_APP_ID'),
            os.getenv('INSTAGRAM_APP_SECRET')
        ]):
            self.apis_available['instagram'] = True
            logger.info("✅ Instagram API認証情報確認")
        else:
            logger.warning("⚠️ Instagram API認証情報未設定")
        
        # YouTube API（既に設定済み）
        if os.getenv('YOUTUBE_API_KEY'):
            self.apis_available['youtube'] = True
            logger.info("✅ YouTube API認証情報確認")
        
        # TikTok API
        if all([
            os.getenv('TIKTOK_CLIENT_KEY'),
            os.getenv('TIKTOK_CLIENT_SECRET')
        ]):
            self.apis_available['tiktok'] = True
            logger.info("✅ TikTok API認証情報確認")
        else:
            logger.warning("⚠️ TikTok API認証情報未設定")
    
    def get_twitter_metrics(self, username: str) -> Optional[Dict]:
        """
        Twitterメトリクス取得
        
        Args:
            username: Twitterユーザー名
            
        Returns:
            メトリクス辞書
        """
        if not self.apis_available['twitter']:
            return None
        
        try:
            bearer_token = os.getenv('TWITTER_BEARER_TOKEN')
            headers = {
                'Authorization': f'Bearer {bearer_token}',
                'User-Agent': 'v2UserLookupPython'
            }
            
            # ユーザー情報取得
            url = f"https://api.twitter.com/2/users/by/username/{username}"
            params = {
                'user.fields': 'public_metrics,created_at,description,verified'
            }
            
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data:
                    user_data = data['data']
                    metrics = user_data.get('public_metrics', {})
                    
                    return {
                        'platform': 'Twitter',
                        'username': username,
                        'followers': metrics.get('followers_count', 0),
                        'following': metrics.get('following_count', 0),
                        'tweets': metrics.get('tweet_count', 0),
                        'verified': user_data.get('verified', False),
                        'engagement_rate': self._calculate_engagement_rate(
                            metrics.get('followers_count', 0),
                            metrics.get('tweet_count', 0)
                        )
                    }
            else:
                logger.error(f"Twitter API エラー: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Twitter メトリクス取得エラー: {e}")
        
        return None
    
    def get_youtube_metrics(self, channel_name: str) -> Optional[Dict]:
        """
        YouTubeメトリクス取得
        
        Args:
            channel_name: チャンネル名
            
        Returns:
            メトリクス辞書
        """
        if not self.apis_available['youtube']:
            return None
        
        try:
            api_key = os.getenv('YOUTUBE_API_KEY')
            
            # チャンネル検索
            search_url = "https://www.googleapis.com/youtube/v3/search"
            search_params = {
                'part': 'snippet',
                'q': channel_name,
                'type': 'channel',
                'key': api_key,
                'maxResults': 1
            }
            
            response = requests.get(search_url, params=search_params)
            
            if response.status_code == 200:
                data = response.json()
                if 'items' in data and len(data['items']) > 0:
                    channel_id = data['items'][0]['id']['channelId']
                    
                    # チャンネル詳細取得
                    channel_url = "https://www.googleapis.com/youtube/v3/channels"
                    channel_params = {
                        'part': 'statistics,snippet',
                        'id': channel_id,
                        'key': api_key
                    }
                    
                    channel_response = requests.get(channel_url, params=channel_params)
                    
                    if channel_response.status_code == 200:
                        channel_data = channel_response.json()
                        if 'items' in channel_data and len(channel_data['items']) > 0:
                            stats = channel_data['items'][0]['statistics']
                            
                            return {
                                'platform': 'YouTube',
                                'channel_name': channel_name,
                                'channel_id': channel_id,
                                'subscribers': int(stats.get('subscriberCount', 0)),
                                'total_views': int(stats.get('viewCount', 0)),
                                'video_count': int(stats.get('videoCount', 0)),
                                'average_views': int(stats.get('viewCount', 0)) // max(1, int(stats.get('videoCount', 1))),
                                'engagement_score': self._calculate_youtube_engagement(stats)
                            }
            
        except Exception as e:
            logger.error(f"YouTube メトリクス取得エラー: {e}")
        
        return None
    
    def get_instagram_metrics(self, username: str) -> Optional[Dict]:
        """
        Instagramメトリクス取得（Basic Display API）
        
        注：実装にはOAuth認証フローが必要
        ここでは構造のみ示す
        """
        if not self.apis_available['instagram']:
            return None
        
        # Instagram Basic Display APIは認証フローが複雑なため
        # 実装例のみ示す
        return {
            'platform': 'Instagram',
            'username': username,
            'followers': 0,  # 実際のAPIコールで取得
            'following': 0,
            'posts': 0,
            'engagement_rate': 0.0,
            'note': 'Instagram APIは認証フローの実装が必要'
        }
    
    def get_tiktok_metrics(self, username: str) -> Optional[Dict]:
        """
        TikTokメトリクス取得
        
        注：TikTok APIは申請が必要
        """
        if not self.apis_available['tiktok']:
            return None
        
        # TikTok APIは事前申請が必要なため
        # 実装例のみ示す
        return {
            'platform': 'TikTok',
            'username': username,
            'followers': 0,  # 実際のAPIコールで取得
            'likes': 0,
            'videos': 0,
            'engagement_rate': 0.0,
            'note': 'TikTok APIは事前申請が必要'
        }
    
    def _calculate_engagement_rate(self, followers: int, content_count: int) -> float:
        """エンゲージメント率計算"""
        if followers == 0:
            return 0.0
        
        # 簡易的なエンゲージメント率
        # 実際は「いいね」「コメント」「シェア」から計算
        base_rate = min(10.0, content_count / max(1, followers) * 100)
        return round(base_rate, 2)
    
    def _calculate_youtube_engagement(self, stats: Dict) -> float:
        """YouTubeエンゲージメントスコア計算"""
        subscribers = int(stats.get('subscriberCount', 0))
        views = int(stats.get('viewCount', 0))
        videos = int(stats.get('videoCount', 1))
        
        if subscribers == 0:
            return 0.0
        
        # 平均視聴回数 / 登録者数 = エンゲージメント指標
        avg_views_per_video = views / max(1, videos)
        engagement_score = min(100, (avg_views_per_video / max(1, subscribers)) * 100)
        
        return round(engagement_score, 2)
    
    def collect_all_metrics(self, 
                           name: str,
                           twitter_username: Optional[str] = None,
                           youtube_channel: Optional[str] = None,
                           instagram_username: Optional[str] = None,
                           tiktok_username: Optional[str] = None) -> Dict:
        """
        全SNSメトリクス収集
        
        Args:
            name: 人物名
            各SNSのユーザー名/チャンネル名
            
        Returns:
            統合メトリクス
        """
        metrics = {
            'name': name,
            'timestamp': datetime.now().isoformat(),
            'platforms': {},
            'total_followers': 0,
            'platform_count': 0,
            'influence_score': 0.0
        }
        
        # Twitter
        if twitter_username:
            twitter_data = self.get_twitter_metrics(twitter_username)
            if twitter_data:
                metrics['platforms']['twitter'] = twitter_data
                metrics['total_followers'] += twitter_data.get('followers', 0)
                metrics['platform_count'] += 1
        
        # YouTube
        if youtube_channel:
            youtube_data = self.get_youtube_metrics(youtube_channel)
            if youtube_data:
                metrics['platforms']['youtube'] = youtube_data
                metrics['total_followers'] += youtube_data.get('subscribers', 0)
                metrics['platform_count'] += 1
        
        # Instagram
        if instagram_username:
            instagram_data = self.get_instagram_metrics(instagram_username)
            if instagram_data:
                metrics['platforms']['instagram'] = instagram_data
                metrics['total_followers'] += instagram_data.get('followers', 0)
                metrics['platform_count'] += 1
        
        # TikTok
        if tiktok_username:
            tiktok_data = self.get_tiktok_metrics(tiktok_username)
            if tiktok_data:
                metrics['platforms']['tiktok'] = tiktok_data
                metrics['total_followers'] += tiktok_data.get('followers', 0)
                metrics['platform_count'] += 1
        
        # 影響力スコア計算（0-100）
        metrics['influence_score'] = self._calculate_influence_score(metrics)
        
        return metrics
    
    def _calculate_influence_score(self, metrics: Dict) -> float:
        """
        SNS影響力スコア計算
        
        フォロワー数を基準に0-100のスコアを算出
        """
        total_followers = metrics['total_followers']
        platform_count = metrics['platform_count']
        
        if total_followers == 0:
            return 0.0
        
        # フォロワー数による基本スコア
        if total_followers >= 10000000:  # 1000万以上
            base_score = 100
        elif total_followers >= 1000000:  # 100万以上
            base_score = 90
        elif total_followers >= 100000:   # 10万以上
            base_score = 70
        elif total_followers >= 10000:    # 1万以上
            base_score = 50
        elif total_followers >= 1000:     # 1000以上
            base_score = 30
        else:
            base_score = total_followers / 1000 * 30
        
        # プラットフォーム数によるボーナス
        platform_bonus = min(10, platform_count * 2.5)
        
        final_score = min(100, base_score + platform_bonus)
        
        return round(final_score, 2)
    
    def export_metrics(self, metrics: Dict, output_path: str):
        """メトリクスをJSONファイルにエクスポート"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ SNSメトリクスエクスポート完了: {output_path}")


def main():
    """メイン実行"""
    collector = SNSMetricsCollector()
    
    # テストケース
    test_cases = [
        {
            'name': 'HIKAKIN',
            'twitter_username': 'hikakin',
            'youtube_channel': 'HikakinTV',
            'instagram_username': 'hikakin',
            'tiktok_username': 'hikakin'
        },
        {
            'name': '米津玄師',
            'twitter_username': 'hachi_08',
            'youtube_channel': '米津玄師',
            'instagram_username': 'hachi_08',
            'tiktok_username': None
        }
    ]
    
    for person in test_cases:
        print(f"\n{'='*60}")
        print(f"収集中: {person['name']}")
        print('='*60)
        
        metrics = collector.collect_all_metrics(
            name=person['name'],
            twitter_username=person.get('twitter_username'),
            youtube_channel=person.get('youtube_channel'),
            instagram_username=person.get('instagram_username'),
            tiktok_username=person.get('tiktok_username')
        )
        
        print(f"総フォロワー数: {metrics['total_followers']:,}")
        print(f"プラットフォーム数: {metrics['platform_count']}")
        print(f"影響力スコア: {metrics['influence_score']}/100")
        
        for platform, data in metrics['platforms'].items():
            print(f"\n{platform.upper()}:")
            if platform == 'twitter':
                print(f"  フォロワー: {data.get('followers', 0):,}")
            elif platform == 'youtube':
                print(f"  登録者: {data.get('subscribers', 0):,}")
                print(f"  総再生回数: {data.get('total_views', 0):,}")
        
        # エクスポート
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"sns_metrics_{person['name']}_{timestamp}.json"
        collector.export_metrics(metrics, output_path)
    
    print(f"\n✅ SNSメトリクス収集完了")


if __name__ == "__main__":
    main()