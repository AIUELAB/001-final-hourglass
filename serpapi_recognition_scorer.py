#!/usr/bin/env python3
"""
SerpAPI基盤の知名度スコアリングシステム
SerpAPI-based Recognition Scoring System

Google検索結果を使った高精度な知名度測定
月100回無料、クレジットカード不要
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import numpy as np

# SerpAPI（pip install google-search-results）
from serpapi import GoogleSearch

# pytrends（Google Trends）
try:
    from pytrends.request import TrendReq
    PYTRENDS_AVAILABLE = True
except ImportError:
    PYTRENDS_AVAILABLE = False
    print("⚠️ pytrends未インストール。Google Trendsは利用できません。")

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class RecognitionMetrics:
    """知名度メトリクスデータクラス"""
    google_search_count: int  # Google検索ヒット数
    google_trends_score: float  # Google Trendsスコア (0-100)
    news_count: int  # ニュース検索ヒット数
    image_count: int  # 画像検索ヒット数
    video_count: int  # 動画検索ヒット数
    wikipedia_exists: bool  # Wikipedia存在確認
    knowledge_graph: bool  # Googleナレッジグラフ存在
    timestamp: str


class SerpApiRecognitionScorer:
    """
    SerpAPI基盤の知名度スコアリングエンジン
    
    特徴：
    - Google検索の正確な結果数を取得
    - 月100回まで無料（クレカ不要）
    - ニュース、画像、動画も検索可能
    - Googleナレッジグラフ情報も取得
    """
    
    def __init__(self, serpapi_key: Optional[str] = None):
        """初期化"""
        # SerpAPIキー（環境変数から取得）
        self.serpapi_key = serpapi_key or os.getenv('SERPAPI_KEY')
        
        # 無料枠カウンター（月100回）
        self.api_calls_count = 0
        self.api_calls_limit = 100
        
        # pytrends初期化（オプション）
        self.pytrends = None
        if PYTRENDS_AVAILABLE:
            try:
                self.pytrends = TrendReq(hl='ja-JP', tz=540)
                logger.info("✅ Google Trends API初期化成功")
            except Exception as e:
                logger.warning(f"⚠️ Google Trends初期化失敗: {e}")
        
        # 設定
        self.config = self._load_config()
        
        # API検証
        self._validate_apis()
        
    def _load_config(self) -> Dict:
        """設定ロード"""
        return {
            'weights': {
                'google_search': 0.30,     # Google検索ヒット数
                'google_trends': 0.20,     # Google Trends
                'news_presence': 0.15,     # ニュース掲載
                'media_presence': 0.15,    # 画像・動画
                'wikipedia': 0.10,         # Wikipedia
                'knowledge_graph': 0.10    # ナレッジグラフ
            },
            'search_count_ranges': {
                'ultra_famous': 10000000,   # 1000万件以上
                'very_famous': 1000000,     # 100万件以上
                'famous': 100000,           # 10万件以上
                'well_known': 10000,        # 1万件以上
                'known': 1000,             # 1000件以上
                'minor': 100               # 100件以上
            },
            'category_adjustments': {
                'YouTuber': 1.3,           # +30% (現代的な有名人)
                'TikToker': 1.3,          # +30%
                'VTuber': 1.25,           # +25%
                'インフルエンサー': 1.25,  # +25%
                '配信者': 1.2,            # +20%
                'ゲーム実況者': 1.2,      # +20%
                'お笑い芸人': 1.1,        # +10%
                '俳優': 1.1,              # +10%
                '歌手': 1.1,              # +10%
                'アイドル': 1.15,         # +15%
                'スポーツ選手': 1.1,      # +10%
            }
        }
    
    def _validate_apis(self):
        """API利用可能性検証"""
        if not self.serpapi_key:
            # SerpAPIキーがない場合の代替案を提示
            error_msg = """
            ⚠️ SerpAPIキーが設定されていません
            
            【無料で取得する方法】
            1. https://serpapi.com/users/sign_up にアクセス
            2. メールアドレスで登録（クレカ不要）
            3. APIキーを取得
            4. 環境変数に設定:
               export SERPAPI_KEY='your_api_key_here'
            
            【代替案】
            - Google Custom Search API（1日100回無料）を使用
            - 既存のBrave Search APIを使用（設定済み）
            
            現在はBrave Search APIで代替動作します。
            """
            logger.warning(error_msg)
            
            # Brave Search APIの確認
            brave_key = os.getenv('BRAVE_API_KEY')
            if brave_key:
                logger.info("✅ Brave Search APIで代替動作します")
                self.use_brave_fallback = True
            else:
                logger.error("❌ 検索APIが1つも利用できません")
                raise SystemError("検索APIが必要です（SerpAPIまたはBrave Search）")
        else:
            logger.info(f"✅ SerpAPI初期化成功（残り{self.api_calls_limit}回）")
            self.use_brave_fallback = False
    
    def get_google_search_count(self, name: str, name_en: Optional[str] = None) -> int:
        """
        Google検索ヒット数を取得（SerpAPI使用）
        
        Args:
            name: 日本語名
            name_en: 英語名
            
        Returns:
            検索ヒット数
        """
        if self.use_brave_fallback:
            return self._get_brave_search_count(name, name_en)
        
        if self.api_calls_count >= self.api_calls_limit:
            logger.warning(f"⚠️ SerpAPI無料枠上限到達 ({self.api_calls_limit}回)")
            return 0
        
        try:
            # 日本語名で検索
            params = {
                "q": f'"{name}"',  # 完全一致検索
                "api_key": self.serpapi_key,
                "hl": "ja",  # 日本語結果
                "gl": "jp",  # 日本からの検索
                "num": 1     # 結果数だけ必要
            }
            
            search = GoogleSearch(params)
            results = search.get_dict()
            self.api_calls_count += 1
            
            # 正確な検索件数を取得
            search_info = results.get("search_information", {})
            total_results = search_info.get("total_results", 0)
            
            # 英語名でも検索して最大値を採用
            if name_en:
                params["q"] = f'"{name_en}"'
                params["hl"] = "en"
                search_en = GoogleSearch(params)
                results_en = search_en.get_dict()
                self.api_calls_count += 1
                
                en_total = results_en.get("search_information", {}).get("total_results", 0)
                total_results = max(total_results, en_total)
            
            logger.info(f"📊 Google検索ヒット数: {total_results:,} - {name}")
            return int(total_results)
            
        except Exception as e:
            logger.error(f"❌ SerpAPIエラー: {e}")
            return 0
    
    def _get_brave_search_count(self, name: str, name_en: Optional[str] = None) -> int:
        """Brave Search APIでの代替検索"""
        import requests
        
        brave_key = os.getenv('BRAVE_API_KEY')
        if not brave_key:
            return 0
        
        try:
            headers = {"X-Subscription-Token": brave_key}
            params = {"q": f'"{name}"', "count": 1}
            
            response = requests.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers=headers,
                params=params
            )
            
            if response.ok:
                data = response.json()
                # Braveは正確な総数を返さないので推定値
                estimated_count = len(data.get("web", {}).get("results", [])) * 10000
                logger.info(f"📊 Brave推定ヒット数: {estimated_count:,} - {name}")
                return estimated_count
                
        except Exception as e:
            logger.error(f"❌ Brave Search APIエラー: {e}")
            
        return 0
    
    def get_news_count(self, name: str) -> int:
        """ニュース検索ヒット数取得"""
        if self.use_brave_fallback or self.api_calls_count >= self.api_calls_limit:
            return 0
        
        try:
            params = {
                "q": f'"{name}"',
                "api_key": self.serpapi_key,
                "tbm": "nws",  # ニュース検索
                "hl": "ja",
                "gl": "jp",
                "num": 1
            }
            
            search = GoogleSearch(params)
            results = search.get_dict()
            self.api_calls_count += 1
            
            # ニュース結果数
            news_results = results.get("news_results", [])
            total_results = results.get("search_information", {}).get("total_results", 0)
            
            logger.info(f"📰 ニュースヒット数: {total_results:,} - {name}")
            return int(total_results)
            
        except Exception as e:
            logger.error(f"❌ ニュース検索エラー: {e}")
            return 0
    
    def get_image_video_count(self, name: str) -> Tuple[int, int]:
        """画像・動画検索ヒット数取得"""
        if self.use_brave_fallback or self.api_calls_count >= self.api_calls_limit:
            return 0, 0
        
        image_count = 0
        video_count = 0
        
        try:
            # 画像検索
            params = {
                "q": f'"{name}"',
                "api_key": self.serpapi_key,
                "tbm": "isch",  # 画像検索
                "hl": "ja",
                "gl": "jp",
                "num": 1
            }
            
            search = GoogleSearch(params)
            results = search.get_dict()
            self.api_calls_count += 1
            image_count = len(results.get("images_results", [])) * 1000  # 推定値
            
            # 動画検索
            params["tbm"] = "vid"  # 動画検索
            search = GoogleSearch(params)
            results = search.get_dict()
            self.api_calls_count += 1
            video_count = len(results.get("video_results", [])) * 100  # 推定値
            
            logger.info(f"🖼️ 画像: {image_count:,}, 🎥 動画: {video_count:,} - {name}")
            
        except Exception as e:
            logger.error(f"❌ 画像・動画検索エラー: {e}")
        
        return image_count, video_count
    
    def check_knowledge_graph(self, name: str) -> bool:
        """Googleナレッジグラフの存在確認"""
        if self.use_brave_fallback or self.api_calls_count >= self.api_calls_limit:
            return False
        
        try:
            params = {
                "q": name,
                "api_key": self.serpapi_key,
                "hl": "ja",
                "gl": "jp",
                "num": 1
            }
            
            search = GoogleSearch(params)
            results = search.get_dict()
            self.api_calls_count += 1
            
            # ナレッジグラフの存在確認
            has_knowledge = "knowledge_graph" in results
            
            if has_knowledge:
                logger.info(f"✅ ナレッジグラフあり: {name}")
            
            return has_knowledge
            
        except Exception as e:
            logger.error(f"❌ ナレッジグラフ確認エラー: {e}")
            return False
    
    def get_google_trends_score(self, name: str, name_en: Optional[str] = None) -> float:
        """Google Trendsスコア取得（pytrends使用）"""
        if not self.pytrends:
            return 0.0
        
        try:
            keywords = [name]
            if name_en:
                keywords.append(name_en)
            
            # 過去12ヶ月のトレンドデータ
            self.pytrends.build_payload(
                keywords,
                timeframe='today 12-m',
                geo='JP'
            )
            
            interest_over_time = self.pytrends.interest_over_time()
            
            if interest_over_time.empty:
                return 0.0
            
            # 平均値を計算
            scores = []
            for keyword in keywords:
                if keyword in interest_over_time.columns:
                    avg_score = interest_over_time[keyword].mean()
                    scores.append(avg_score)
            
            return max(scores) if scores else 0.0
            
        except Exception as e:
            logger.warning(f"⚠️ Google Trends取得失敗: {e}")
            return 0.0
    
    def check_wikipedia(self, name: str, name_en: Optional[str] = None) -> bool:
        """Wikipedia存在確認"""
        import requests
        
        try:
            # 日本語Wikipedia
            ja_url = f"https://ja.wikipedia.org/wiki/{name}"
            response = requests.head(ja_url, allow_redirects=True, timeout=5)
            if response.status_code == 200:
                return True
            
            # 英語Wikipedia
            if name_en:
                en_url = f"https://en.wikipedia.org/wiki/{name_en.replace(' ', '_')}"
                response = requests.head(en_url, allow_redirects=True, timeout=5)
                if response.status_code == 200:
                    return True
                    
        except Exception as e:
            logger.warning(f"⚠️ Wikipedia確認エラー: {e}")
            
        return False
    
    def calculate_recognition_score(self, 
                                  name: str,
                                  name_en: Optional[str] = None,
                                  category: Optional[str] = None) -> Tuple[float, RecognitionMetrics]:
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
        
        # メトリクス収集
        metrics = RecognitionMetrics(
            google_search_count=self.get_google_search_count(name, name_en),
            google_trends_score=self.get_google_trends_score(name, name_en),
            news_count=self.get_news_count(name),
            image_count=0,
            video_count=0,
            wikipedia_exists=self.check_wikipedia(name, name_en),
            knowledge_graph=self.check_knowledge_graph(name),
            timestamp=datetime.now().isoformat()
        )
        
        # 画像・動画（API節約のため重要人物のみ）
        if metrics.google_search_count > 10000:
            image_count, video_count = self.get_image_video_count(name)
            metrics.image_count = image_count
            metrics.video_count = video_count
        
        # スコア計算
        score = self._calculate_final_score(metrics, category)
        
        logger.info(f"✅ 最終スコア: {score:.2f}/10 - {name}")
        logger.info(f"📊 API使用状況: {self.api_calls_count}/{self.api_calls_limit}")
        
        return score, metrics
    
    def _calculate_final_score(self, metrics: RecognitionMetrics, category: Optional[str]) -> float:
        """最終スコア計算"""
        weights = self.config['weights']
        component_scores = {}
        
        # 1. Google検索スコア（ヒット数を0-100に正規化）
        search_score = self._normalize_search_count(metrics.google_search_count)
        component_scores['google_search'] = search_score
        
        # 2. Google Trendsスコア（0-100そのまま）
        component_scores['google_trends'] = metrics.google_trends_score
        
        # 3. ニューススコア（ヒット数を0-100に正規化）
        news_score = min(100, metrics.news_count / 100)  # 10000件で満点
        component_scores['news_presence'] = news_score
        
        # 4. メディアスコア（画像・動画）
        media_score = min(100, (metrics.image_count + metrics.video_count) / 1000)
        component_scores['media_presence'] = media_score
        
        # 5. Wikipediaスコア（存在すれば100）
        component_scores['wikipedia'] = 100 if metrics.wikipedia_exists else 0
        
        # 6. ナレッジグラフスコア（存在すれば100）
        component_scores['knowledge_graph'] = 100 if metrics.knowledge_graph else 0
        
        # 重み付け合計
        weighted_sum = sum(
            component_scores.get(key, 0) * weight
            for key, weight in weights.items()
        )
        
        # 0-10スケールに変換
        final_score = weighted_sum / 10
        
        # カテゴリ別補正
        if category and category in self.config['category_adjustments']:
            adjustment = self.config['category_adjustments'][category]
            final_score *= adjustment
            logger.debug(f"📈 カテゴリ補正: {category} × {adjustment}")
        
        return min(10.0, max(0.0, final_score))
    
    def _normalize_search_count(self, count: int) -> float:
        """検索ヒット数を0-100に正規化"""
        ranges = self.config['search_count_ranges']
        
        if count >= ranges['ultra_famous']:
            return 100
        elif count >= ranges['very_famous']:
            return 90
        elif count >= ranges['famous']:
            return 80
        elif count >= ranges['well_known']:
            return 70
        elif count >= ranges['known']:
            return 50
        elif count >= ranges['minor']:
            return 30
        else:
            # 100件未満は線形スケール
            return min(20, count / 100 * 20)
    
    def export_results(self, results: List[Tuple[str, float, RecognitionMetrics]], 
                       output_path: str):
        """結果エクスポート"""
        data = []
        
        for person_id, score, metrics in results:
            data.append({
                'id': person_id,
                'recognition_score': score,
                'google_search_count': metrics.google_search_count,
                'google_trends': metrics.google_trends_score,
                'news_count': metrics.news_count,
                'image_count': metrics.image_count,
                'video_count': metrics.video_count,
                'wikipedia_exists': metrics.wikipedia_exists,
                'knowledge_graph': metrics.knowledge_graph,
                'timestamp': metrics.timestamp,
                'api_calls_used': self.api_calls_count
            })
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ 結果エクスポート完了: {output_path}")


def main():
    """メイン実行"""
    # SerpAPIキーチェック
    if not os.getenv('SERPAPI_KEY'):
        print("""
        ========================================
        SerpAPI無料アカウント作成方法
        ========================================
        1. https://serpapi.com/users/sign_up
        2. メールアドレスで登録（クレカ不要）
        3. APIキーをコピー
        4. 環境変数に設定:
           export SERPAPI_KEY='your_key_here'
        
        月100回まで無料で利用可能！
        ========================================
        """)
    
    scorer = SerpApiRecognitionScorer()
    
    # テスト実行
    test_persons = [
        {'id': 'P000013', 'name': 'HIKAKIN', 'name_en': 'Hikakin', 'category': 'YouTuber'},
        {'id': 'P000001', 'name': '宮崎駿', 'name_en': 'Hayao Miyazaki', 'category': '映画監督'},
        {'id': 'P000100', 'name': 'イチロー', 'name_en': 'Ichiro Suzuki', 'category': '野球選手'},
    ]
    
    results = []
    for person in test_persons:
        score, metrics = scorer.calculate_recognition_score(
            person['name'],
            person.get('name_en'),
            person.get('category')
        )
        results.append((person['id'], score, metrics))
        
        print(f"\n📌 {person['name']} ({person.get('name_en', '')})")
        print(f"   カテゴリ: {person.get('category', '不明')}")
        print(f"   総合スコア: {score:.2f}/10")
        print(f"   Google検索: {metrics.google_search_count:,}件")
        print(f"   Google Trends: {metrics.google_trends_score:.1f}/100")
        print(f"   Wikipedia: {'あり' if metrics.wikipedia_exists else 'なし'}")
        print(f"   ナレッジグラフ: {'あり' if metrics.knowledge_graph else 'なし'}")
    
    # 結果保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"serpapi_recognition_scores_{timestamp}.json"
    scorer.export_results(results, output_path)
    
    print(f"\n✅ 完了！結果は {output_path} に保存されました")
    print(f"📊 API使用状況: {scorer.api_calls_count}/{scorer.api_calls_limit}回")


if __name__ == "__main__":
    main()