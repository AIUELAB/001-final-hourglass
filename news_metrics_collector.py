#!/usr/bin/env python3
"""
ニュースメトリクス収集モジュール
News Metrics Collection Module

News API、Google News、Brave Newsから
ニュース掲載数と話題性を測定
"""

import os
import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import requests
from urllib.parse import quote

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NewsMetricsCollector:
    """
    ニュースメトリクス収集クラス

    複数のニュースソースから言及数と話題性を測定
    """

    def __init__(self):
        """初期化"""
        self.apis_available = {
            'newsapi': False,
            'brave_news': False,
            'google_news': True  # 無料、キー不要
        }

        # API認証情報確認
        self._check_api_credentials()

        # ニュースソースの重要度
        self.source_weights = {
            '主要メディア': 1.0,    # NHK、朝日、読売など
            '専門メディア': 0.8,    # 業界紙、専門誌
            'ウェブメディア': 0.6,  # オンライン専門
            'ローカルメディア': 0.4 # 地方紙
        }

        # 主要メディアリスト（日本）
        self.major_sources_jp = [
            'NHK', '朝日新聞', '読売新聞', '毎日新聞', '日本経済新聞',
            '産経新聞', '共同通信', '時事通信', 'TBS', 'フジテレビ',
            'テレビ朝日', '日本テレビ', 'テレビ東京', 'AERA', '文春オンライン'
        ]

        # ニュース鮮度による重み付け
        self.freshness_weights = {
            '24時間以内': 1.0,
            '1週間以内': 0.7,
            '1ヶ月以内': 0.4,
            '3ヶ月以内': 0.2,
            'それ以前': 0.1
        }

    def _check_api_credentials(self):
        """API認証情報の確認"""

        # News API
        if os.getenv('NEWS_API_KEY'):
            self.apis_available['newsapi'] = True
            logger.info("✅ News API認証情報確認")
        else:
            logger.warning("⚠️ News API未設定（無料登録: https://newsapi.org/）")

        # Brave News（Brave Search APIで代用）
        if os.getenv('BRAVE_API_KEY'):
            self.apis_available['brave_news'] = True
            logger.info("✅ Brave News API利用可能")

        logger.info("✅ Google News（RSS）利用可能（キー不要）")

    def get_newsapi_mentions(self, name: str, name_en: Optional[str] = None) -> Dict:
        """
        News APIでニュース言及数取得

        Args:
            name: 日本語名
            name_en: 英語名

        Returns:
            ニュースメトリクス
        """
        if not self.apis_available['newsapi']:
            return {'count': 0, 'articles': [], 'source': 'newsapi'}

        try:
            api_key = os.getenv('NEWS_API_KEY')
            url = "https://newsapi.org/v2/everything"

            # 過去1ヶ月のニュース
            from_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

            # 日本語名で検索
            params = {
                'q': f'"{name}"',
                'apiKey': api_key,
                'from': from_date,
                'sortBy': 'relevancy',
                'language': 'ja',
                'pageSize': 100
            }

            response = requests.get(url, params=params)

            if response.status_code == 200:
                data = response.json()
                total_results = data.get('totalResults', 0)
                articles = data.get('articles', [])

                # 主要メディアの記事をカウント
                major_media_count = sum(
                    1 for article in articles
                    if any(source in article.get('source', {}).get('name', '')
                          for source in self.major_sources_jp)
                )

                result = {
                    'count': total_results,
                    'major_media_count': major_media_count,
                    'articles': articles[:10],  # 上位10件
                    'source': 'newsapi',
                    'query': name
                }

                # 英語名でも検索
                if name_en:
                    params['q'] = f'"{name_en}"'
                    params['language'] = 'en'
                    response_en = requests.get(url, params=params)

                    if response_en.status_code == 200:
                        data_en = response_en.json()
                        result['count_en'] = data_en.get('totalResults', 0)
                        result['total_count'] = result['count'] + result['count_en']

                logger.info(f"📰 News API: {result.get('total_count', result['count'])}件 - {name}")
                return result

        except Exception as e:
            logger.error(f"❌ News APIエラー: {e}")

        return {'count': 0, 'articles': [], 'source': 'newsapi'}

    def get_brave_news_mentions(self, name: str) -> Dict:
        """
        Brave Search APIでニュース検索

        Args:
            name: 検索名

        Returns:
            ニュースメトリクス
        """
        if not self.apis_available['brave_news']:
            return {'count': 0, 'articles': [], 'source': 'brave_news'}

        try:
            api_key = os.getenv('BRAVE_API_KEY')
            headers = {"X-Subscription-Token": api_key}

            # ニュース検索
            url = "https://api.search.brave.com/res/v1/news/search"
            params = {
                'q': f'"{name}"',
                'count': 20,
                'freshness': 'pm'  # 過去1ヶ月
            }

            response = requests.get(url, headers=headers, params=params)

            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])

                # 推定総数（Braveは正確な総数を返さない）
                estimated_count = len(results) * 10

                result = {
                    'count': estimated_count,
                    'articles': results[:10],
                    'source': 'brave_news',
                    'query': name
                }

                logger.info(f"📰 Brave News: 約{estimated_count}件 - {name}")
                return result

        except Exception as e:
            logger.error(f"❌ Brave Newsエラー: {e}")

        return {'count': 0, 'articles': [], 'source': 'brave_news'}

    def get_google_news_mentions(self, name: str) -> Dict:
        """
        Google News RSS検索（無料、キー不要）

        Args:
            name: 検索名

        Returns:
            ニュースメトリクス
        """
        try:
            # Google News RSS URL
            query = quote(f'"{name}"')
            url = f"https://news.google.com/rss/search?q={query}&hl=ja&gl=JP&ceid=JP:ja"

            response = requests.get(url)

            if response.status_code == 200:
                # 簡易的なRSSパース（正確にはxml.etreeやfeedparserを使用）
                content = response.text

                # <item>タグの数をカウント（各記事）
                item_count = content.count('<item>')

                # タイトル抽出（簡易版）
                import re
                titles = re.findall(r'<title>(.*?)</title>', content)

                result = {
                    'count': item_count,
                    'estimated_total': item_count * 10,  # 推定値
                    'titles': titles[1:11],  # 最初の1つはフィードタイトル
                    'source': 'google_news',
                    'query': name
                }

                logger.info(f"📰 Google News: {item_count}件（推定{item_count * 10}件） - {name}")
                return result

        except Exception as e:
            logger.error(f"❌ Google Newsエラー: {e}")

        return {'count': 0, 'articles': [], 'source': 'google_news'}

    def calculate_news_score(self, name: str, name_en: Optional[str] = None) -> Tuple[float, Dict]:
        """
        統合ニューススコア計算

        Args:
            name: 日本語名
            name_en: 英語名

        Returns:
            (スコア 0-100, 詳細メトリクス)
        """
        logger.info(f"📰 ニュース話題性測定開始: {name}")

        metrics = {
            'name': name,
            'timestamp': datetime.now().isoformat(),
            'sources': {},
            'total_mentions': 0,
            'major_media_mentions': 0,
            'news_score': 0.0
        }

        # News API
        newsapi_data = self.get_newsapi_mentions(name, name_en)
        if newsapi_data['count'] > 0:
            metrics['sources']['newsapi'] = newsapi_data
            metrics['total_mentions'] += newsapi_data.get('total_count', newsapi_data['count'])
            metrics['major_media_mentions'] += newsapi_data.get('major_media_count', 0)

        # Brave News
        brave_data = self.get_brave_news_mentions(name)
        if brave_data['count'] > 0:
            metrics['sources']['brave_news'] = brave_data
            metrics['total_mentions'] += brave_data['count']

        # Google News
        google_data = self.get_google_news_mentions(name)
        if google_data['count'] > 0:
            metrics['sources']['google_news'] = google_data
            metrics['total_mentions'] += google_data.get('estimated_total', google_data['count'])

        # スコア計算（0-100）
        score = self._calculate_score(metrics)
        metrics['news_score'] = score

        logger.info(f"✅ ニューススコア: {score:.2f}/100 - {name}")
        logger.info(f"   総言及数: {metrics['total_mentions']:,}件")
        logger.info(f"   主要メディア: {metrics['major_media_mentions']}件")

        return score, metrics

    def _calculate_score(self, metrics: Dict) -> float:
        """
        ニューススコア計算

        言及数を0-100にスコア化
        """
        total = metrics['total_mentions']
        major = metrics['major_media_mentions']

        if total == 0:
            return 0.0

        # 基本スコア（言及数ベース）
        if total >= 1000:
            base_score = 100
        elif total >= 500:
            base_score = 90
        elif total >= 100:
            base_score = 70
        elif total >= 50:
            base_score = 50
        elif total >= 10:
            base_score = 30
        else:
            base_score = total * 3

        # 主要メディアボーナス
        major_bonus = min(20, major * 5)

        # 複数ソースボーナス
        source_count = len(metrics['sources'])
        source_bonus = min(10, source_count * 3)

        final_score = min(100, base_score + major_bonus + source_bonus)

        return round(final_score, 2)

    def analyze_trend(self, name: str, days: int = 30) -> Dict:
        """
        ニューストレンド分析

        Args:
            name: 分析対象名
            days: 分析期間（日数）

        Returns:
            トレンド分析結果
        """
        trend = {
            'name': name,
            'period_days': days,
            'trend_direction': 'stable',  # rising/stable/declining
            'peak_date': None,
            'average_mentions_per_day': 0
        }

        # 実装：日別のニュース数を取得してトレンド分析
        # ここでは構造のみ示す

        return trend

    def export_metrics(self, metrics: Dict, output_path: str):
        """メトリクスをJSONファイルにエクスポート"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, ensure_ascii=False, indent=2)

        logger.info(f"✅ ニュースメトリクスエクスポート完了: {output_path}")


def main():
    """メイン実行"""
    collector = NewsMetricsCollector()

    # テストケース
    test_persons = [
        {'name': 'HIKAKIN', 'name_en': 'Hikakin'},
        {'name': '大谷翔平', 'name_en': 'Shohei Ohtani'},
        {'name': '宮崎駿', 'name_en': 'Hayao Miyazaki'}
    ]

    all_results = []

    for person in test_persons:
        print(f"\n{'='*60}")
        print(f"ニュース分析: {person['name']}")
        print('='*60)

        score, metrics = collector.calculate_news_score(
            person['name'],
            person.get('name_en')
        )

        all_results.append({
            'name': person['name'],
            'score': score,
            'total_mentions': metrics['total_mentions'],
            'major_media': metrics['major_media_mentions']
        })

        print(f"ニューススコア: {score:.2f}/100")
        print(f"総言及数: {metrics['total_mentions']:,}件")
        print(f"主要メディア掲載: {metrics['major_media_mentions']}件")

        # ソース別内訳
        print("\n【ソース別内訳】")
        for source, data in metrics['sources'].items():
            count = data.get('total_count', data.get('estimated_total', data['count']))
            print(f"  {source}: {count:,}件")

        # エクスポート
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"news_metrics_{person['name']}_{timestamp}.json"
        collector.export_metrics(metrics, output_path)

    # サマリー表示
    print(f"\n{'='*60}")
    print("ニュース話題性ランキング")
    print('='*60)

    all_results.sort(key=lambda x: x['score'], reverse=True)
    for i, result in enumerate(all_results, 1):
        print(f"{i}位: {result['name']} - スコア{result['score']:.1f} ({result['total_mentions']:,}件)")

    print(f"\n✅ ニュース分析完了")


if __name__ == "__main__":
    main()
