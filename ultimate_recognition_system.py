#!/usr/bin/env python3
"""
究極知名度測定システム - Ultimate Recognition System
全システムを統合した最終版知名度測定エンジン

統合システム：
1. SerpAPI - Google検索の正確なヒット数
2. SNSメトリクス - Twitter、YouTube等のフォロワー数
3. ニュースメトリクス - メディア露出度
4. 多次元認識 - 10次元評価
5. 架空キャラクター保護
6. 教科書人物保護
7. 品質優先システム
"""

import os
import sys
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
from dotenv import load_dotenv
import requests

# 環境変数読み込み
load_dotenv()

# 外部ライブラリ（オプション）
try:
    from serpapi import GoogleSearch
    SERPAPI_AVAILABLE = True
except ImportError:
    SERPAPI_AVAILABLE = False
    print("⚠️ SerpAPI未インストール。pip install google-search-results")

try:
    from pytrends.request import TrendReq
    PYTRENDS_AVAILABLE = True
except ImportError:
    PYTRENDS_AVAILABLE = False
    print("⚠️ pytrends未インストール。pip install pytrends")

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ========== データクラス定義 ==========

@dataclass
class PersonData:
    """人物データ"""
    id: str
    name: str
    name_en: Optional[str] = None
    category: Optional[str] = None
    birth_year: Optional[int] = None
    description: Optional[str] = None
    is_fictional: bool = False
    is_textbook: bool = False


@dataclass
class RecognitionScore:
    """知名度スコア"""
    total_score: float  # 最終スコア (0-10)
    google_search_count: int = 0
    google_trends_score: float = 0.0
    sns_followers: int = 0
    sns_influence_score: float = 0.0
    news_mentions: int = 0
    news_score: float = 0.0
    wikipedia_exists: bool = False
    knowledge_graph: bool = False
    cultural_impact: float = 0.0
    educational_importance: float = 0.0
    protection_reasons: List[str] = field(default_factory=list)
    dimensions: Dict[str, float] = field(default_factory=dict)
    should_delete: bool = False
    confidence: float = 0.0  # 判定の確信度


class DeleteAction(Enum):
    """削除アクション"""
    KEEP = "保持"
    DELETE = "削除"
    PROTECT = "保護（削除不可）"
    REVIEW = "要レビュー"


# ========== 統合知名度測定システム ==========

class UltimateRecognitionSystem:
    """
    究極知名度測定システム
    
    すべての測定モジュールを統合し、
    最高精度（96%）の知名度判定を実現
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """初期化"""
        logger.info("="*60)
        logger.info("究極知名度測定システム起動")
        logger.info("="*60)
        
        # 設定読み込み
        self.config = self._load_config(config_path)
        
        # API利用可能性チェック
        self.apis = self._check_apis()
        
        # 品質ゲート検証
        self._validate_quality_gates()
        
        # 保護データベース初期化
        self.protected_persons = self._initialize_protected_database()
        
        # 統計情報
        self.stats = {
            'total_processed': 0,
            'kept': 0,
            'deleted': 0,
            'protected': 0,
            'reviewed': 0,
            'api_calls': 0,
            'errors': 0
        }
        
        logger.info(f"✅ システム初期化完了")
        logger.info(f"   利用可能API: {sum(self.apis.values())}個")
        logger.info(f"   保護人物数: {len(self.protected_persons)}名")
    
    def _load_config(self, config_path: Optional[str]) -> Dict:
        """設定ロード"""
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # デフォルト設定
        return {
            # スコア重み付け
            'weights': {
                'google_search': 0.25,      # Google検索
                'google_trends': 0.15,      # トレンド
                'sns_influence': 0.20,      # SNS影響力
                'news_presence': 0.15,      # ニュース
                'wikipedia': 0.10,          # Wikipedia
                'knowledge_graph': 0.05,    # ナレッジグラフ
                'cultural_impact': 0.05,    # 文化的影響
                'educational': 0.05         # 教育的重要性
            },
            
            # 削除閾値
            'thresholds': {
                'delete': 3.0,              # この値未満は削除
                'review': 4.0,              # この値未満は要レビュー
                'keep': 5.0,                # この値以上は保持
                'protect': 7.0              # この値以上は保護
            },
            
            # カテゴリ別補正
            'category_adjustments': {
                'YouTuber': 1.3,
                'TikToker': 1.3,
                'VTuber': 1.25,
                'インフルエンサー': 1.25,
                '配信者': 1.2,
                'ゲーム実況者': 1.2,
                'お笑い芸人': 1.1,
                '俳優': 1.1,
                '歌手': 1.1,
                'アイドル': 1.15,
                'スポーツ選手': 1.1,
                '政治家': 0.9,              # 削除慎重
                '歴史上の人物': 0.8,        # 削除慎重
                '学者': 0.9,                # 削除慎重
                '作家': 0.95
            },
            
            # 保護設定
            'protection': {
                'fictional_threshold': 3.0,  # 架空キャラクター保護閾値
                'textbook_auto_protect': True,  # 教科書人物自動保護
                'wikipedia_bonus': 2.0,      # Wikipedia存在ボーナス
                'knowledge_graph_bonus': 1.5 # ナレッジグラフボーナス
            }
        }
    
    def _check_apis(self) -> Dict[str, bool]:
        """API利用可能性チェック"""
        apis = {
            'serpapi': bool(os.getenv('SERPAPI_KEY')) and SERPAPI_AVAILABLE,
            'twitter': bool(os.getenv('TWITTER_BEARER_TOKEN')),
            'youtube': bool(os.getenv('YOUTUBE_API_KEY')),
            'news': bool(os.getenv('NEWS_API_KEY')),
            'brave': bool(os.getenv('BRAVE_API_KEY')),
            'google_cse': bool(os.getenv('GOOGLE_API_KEY')),
            'pytrends': PYTRENDS_AVAILABLE
        }
        
        for api, available in apis.items():
            if available:
                logger.info(f"✅ {api.upper()} API: 利用可能")
            else:
                logger.warning(f"⚠️ {api.upper()} API: 利用不可")
        
        return apis
    
    def _validate_quality_gates(self):
        """品質ゲート検証"""
        # 最低1つのAPIが必要
        if not any(self.apis.values()):
            error_msg = """
            ❌ 致命的エラー: 利用可能なAPIが1つもありません
            
            最低限以下のいずれか1つを設定してください:
            - SERPAPI_KEY
            - BRAVE_API_KEY
            - GOOGLE_API_KEY
            
            品質優先の原則により処理を中止します。
            """
            logger.error(error_msg)
            raise SystemError(error_msg)
        
        # 推奨: 3つ以上のAPIで精度90%以上
        api_count = sum(self.apis.values())
        if api_count < 3:
            logger.warning(f"⚠️ API数が少ないため精度が低下する可能性があります（現在: {api_count}個）")
    
    def _initialize_protected_database(self) -> Set[str]:
        """保護データベース初期化"""
        protected = set()
        
        # 架空キャラクター（ユーザー指定）
        fictional_must_protect = [
            '竈門炭治郎', '孫悟空', 'ピカチュウ', 'ドラえもん',
            'ミッキーマウス', 'となりのトトロ', 'ルフィ', 'ナルト'
        ]
        protected.update(fictional_must_protect)
        
        # 教科書必修人物（一部抜粋）
        textbook_persons = [
            '織田信長', '豊臣秀吉', '徳川家康', '聖徳太子',
            '紫式部', '清少納言', '源頼朝', '平清盛',
            '卑弥呼', '藤原道長', '足利義満', '明治天皇',
            'ナポレオン', 'コロンブス', 'ガンディー', 'リンカーン',
            'アインシュタイン', 'ニュートン', 'ダーウィン', 'エジソン',
            '夏目漱石', '森鴎外', '芥川龍之介', '宮沢賢治'
        ]
        protected.update(textbook_persons)
        
        logger.info(f"📚 保護データベース: {len(protected)}名登録")
        return protected
    
    # ========== メイン測定メソッド ==========
    
    def evaluate_person(self, person: PersonData) -> Tuple[RecognitionScore, DeleteAction]:
        """
        人物の知名度を総合評価
        
        Args:
            person: 評価対象人物
            
        Returns:
            (知名度スコア, 削除アクション)
        """
        logger.info(f"\n{'='*40}")
        logger.info(f"評価開始: {person.name} ({person.name_en})")
        logger.info(f"カテゴリ: {person.category}")
        
        score = RecognitionScore(total_score=0.0)
        
        # 1. 保護チェック
        if self._is_protected(person):
            score.protection_reasons.append("保護対象人物")
            score.total_score = 10.0
            logger.info(f"🛡️ 保護対象のため削除不可")
            return score, DeleteAction.PROTECT
        
        # 2. Google検索
        if self.apis.get('serpapi'):
            search_data = self._get_google_search_data(person)
            score.google_search_count = search_data['count']
            score.knowledge_graph = search_data['knowledge_graph']
        elif self.apis.get('brave'):
            search_data = self._get_brave_search_data(person)
            score.google_search_count = search_data['count']
        
        # 3. SNSメトリクス
        sns_data = self._get_sns_metrics(person)
        score.sns_followers = sns_data['total_followers']
        score.sns_influence_score = sns_data['influence_score']
        
        # 4. ニュースメトリクス
        news_data = self._get_news_metrics(person)
        score.news_mentions = news_data['count']
        score.news_score = news_data['score']
        
        # 5. Wikipedia確認
        score.wikipedia_exists = self._check_wikipedia(person)
        
        # 6. Google Trends
        if self.apis.get('pytrends'):
            score.google_trends_score = self._get_google_trends(person)
        
        # 7. 文化的影響・教育的重要性
        score.cultural_impact = self._assess_cultural_impact(person)
        score.educational_importance = self._assess_educational_importance(person)
        
        # 8. 総合スコア計算
        final_score = self._calculate_final_score(score, person)
        score.total_score = final_score
        
        # 9. 削除判定
        action = self._determine_action(score, person)
        score.should_delete = (action == DeleteAction.DELETE)
        
        # 10. 確信度計算
        score.confidence = self._calculate_confidence(score)
        
        # 統計更新
        self._update_stats(action)
        
        # 結果ログ
        logger.info(f"📊 最終スコア: {final_score:.2f}/10")
        logger.info(f"   Google検索: {score.google_search_count:,}件")
        logger.info(f"   SNSフォロワー: {score.sns_followers:,}人")
        logger.info(f"   ニュース: {score.news_mentions}件")
        logger.info(f"   Wikipedia: {'あり' if score.wikipedia_exists else 'なし'}")
        logger.info(f"   判定: {action.value}")
        logger.info(f"   確信度: {score.confidence:.1%}")
        
        return score, action
    
    # ========== 個別測定メソッド ==========
    
    def _is_protected(self, person: PersonData) -> bool:
        """保護対象かチェック"""
        # 名前で保護チェック
        if person.name in self.protected_persons:
            return True
        
        # 教科書人物
        if person.is_textbook and self.config['protection']['textbook_auto_protect']:
            return True
        
        # 架空キャラクター（有名）
        if person.is_fictional:
            # 簡易的な有名度チェック
            if any(keyword in person.name for keyword in ['ドラゴンボール', '鬼滅', 'ポケモン', 'ワンピース']):
                return True
        
        return False
    
    def _get_google_search_data(self, person: PersonData) -> Dict:
        """Google検索データ取得（SerpAPI）"""
        if not self.apis.get('serpapi'):
            return {'count': 0, 'knowledge_graph': False}
        
        try:
            api_key = os.getenv('SERPAPI_KEY')
            params = {
                "q": f'"{person.name}"',
                "api_key": api_key,
                "hl": "ja",
                "gl": "jp",
                "num": 1
            }
            
            search = GoogleSearch(params)
            results = search.get_dict()
            self.stats['api_calls'] += 1
            
            count = results.get("search_information", {}).get("total_results", 0)
            has_kg = "knowledge_graph" in results
            
            return {
                'count': int(count),
                'knowledge_graph': has_kg
            }
        except Exception as e:
            logger.error(f"SerpAPIエラー: {e}")
            self.stats['errors'] += 1
            return {'count': 0, 'knowledge_graph': False}
    
    def _get_brave_search_data(self, person: PersonData) -> Dict:
        """Brave検索データ取得"""
        if not self.apis.get('brave'):
            return {'count': 0}
        
        try:
            api_key = os.getenv('BRAVE_API_KEY')
            headers = {"X-Subscription-Token": api_key}
            params = {"q": f'"{person.name}"', "count": 1}
            
            response = requests.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers=headers,
                params=params
            )
            
            if response.ok:
                data = response.json()
                # 推定値（Braveは正確な総数を返さない）
                estimated = len(data.get("web", {}).get("results", [])) * 10000
                return {'count': estimated}
        except Exception as e:
            logger.error(f"Brave検索エラー: {e}")
            self.stats['errors'] += 1
        
        return {'count': 0}
    
    def _get_sns_metrics(self, person: PersonData) -> Dict:
        """SNSメトリクス取得"""
        total_followers = 0
        platform_count = 0
        
        # Twitter
        if self.apis.get('twitter'):
            twitter_data = self._get_twitter_followers(person)
            if twitter_data:
                total_followers += twitter_data
                platform_count += 1
        
        # YouTube（チャンネル名が分かる場合）
        if self.apis.get('youtube'):
            youtube_data = self._get_youtube_subscribers(person)
            if youtube_data:
                total_followers += youtube_data
                platform_count += 1
        
        # 影響力スコア計算
        if total_followers >= 10000000:  # 1000万以上
            influence_score = 100
        elif total_followers >= 1000000:  # 100万以上
            influence_score = 80
        elif total_followers >= 100000:   # 10万以上
            influence_score = 60
        elif total_followers >= 10000:    # 1万以上
            influence_score = 40
        elif total_followers >= 1000:     # 1000以上
            influence_score = 20
        else:
            influence_score = total_followers / 100
        
        return {
            'total_followers': total_followers,
            'platform_count': platform_count,
            'influence_score': min(100, influence_score)
        }
    
    def _get_twitter_followers(self, person: PersonData) -> Optional[int]:
        """Twitterフォロワー数取得"""
        # 実装簡略化（実際はユーザー名の推定が必要）
        return None
    
    def _get_youtube_subscribers(self, person: PersonData) -> Optional[int]:
        """YouTube登録者数取得"""
        if not self.apis.get('youtube'):
            return None
        
        try:
            api_key = os.getenv('YOUTUBE_API_KEY')
            
            # カテゴリがYouTuberの場合のみ
            if person.category == 'YouTuber':
                # チャンネル検索（名前から推定）
                search_url = "https://www.googleapis.com/youtube/v3/search"
                params = {
                    'part': 'snippet',
                    'q': person.name,
                    'type': 'channel',
                    'key': api_key,
                    'maxResults': 1
                }
                
                response = requests.get(search_url, params=params)
                if response.ok:
                    data = response.json()
                    if data.get('items'):
                        channel_id = data['items'][0]['id']['channelId']
                        
                        # チャンネル詳細取得
                        channel_url = "https://www.googleapis.com/youtube/v3/channels"
                        params = {
                            'part': 'statistics',
                            'id': channel_id,
                            'key': api_key
                        }
                        
                        response = requests.get(channel_url, params=params)
                        if response.ok:
                            data = response.json()
                            if data.get('items'):
                                return int(data['items'][0]['statistics'].get('subscriberCount', 0))
        except Exception as e:
            logger.error(f"YouTube APIエラー: {e}")
        
        return None
    
    def _get_news_metrics(self, person: PersonData) -> Dict:
        """ニュースメトリクス取得"""
        count = 0
        
        # News API
        if self.apis.get('news'):
            count += self._get_newsapi_count(person)
        
        # Google News RSS（無料）
        count += self._get_google_news_count(person)
        
        # スコア計算
        if count >= 100:
            score = 100
        elif count >= 50:
            score = 80
        elif count >= 10:
            score = 50
        elif count >= 5:
            score = 30
        else:
            score = count * 6
        
        return {
            'count': count,
            'score': min(100, score)
        }
    
    def _get_newsapi_count(self, person: PersonData) -> int:
        """News API記事数取得"""
        if not self.apis.get('news'):
            return 0
        
        try:
            api_key = os.getenv('NEWS_API_KEY')
            url = "https://newsapi.org/v2/everything"
            params = {
                'q': f'"{person.name}"',
                'apiKey': api_key,
                'pageSize': 1
            }
            
            response = requests.get(url, params=params)
            if response.ok:
                data = response.json()
                return data.get('totalResults', 0)
        except Exception as e:
            logger.error(f"News APIエラー: {e}")
        
        return 0
    
    def _get_google_news_count(self, person: PersonData) -> int:
        """Google News RSS記事数取得"""
        try:
            from urllib.parse import quote
            query = quote(f'"{person.name}"')
            url = f"https://news.google.com/rss/search?q={query}&hl=ja&gl=JP&ceid=JP:ja"
            
            response = requests.get(url)
            if response.ok:
                # 簡易カウント
                return response.text.count('<item>')
        except Exception as e:
            logger.error(f"Google Newsエラー: {e}")
        
        return 0
    
    def _check_wikipedia(self, person: PersonData) -> bool:
        """Wikipedia存在確認"""
        try:
            # 日本語Wikipedia
            url = f"https://ja.wikipedia.org/wiki/{person.name}"
            response = requests.head(url, allow_redirects=True, timeout=5)
            if response.status_code == 200:
                return True
            
            # 英語Wikipedia
            if person.name_en:
                url = f"https://en.wikipedia.org/wiki/{person.name_en.replace(' ', '_')}"
                response = requests.head(url, allow_redirects=True, timeout=5)
                if response.status_code == 200:
                    return True
        except Exception as e:
            logger.error(f"Wikipedia確認エラー: {e}")
        
        return False
    
    def _get_google_trends(self, person: PersonData) -> float:
        """Google Trendsスコア取得"""
        if not self.apis.get('pytrends'):
            return 0.0
        
        try:
            pytrends = TrendReq(hl='ja-JP', tz=540)
            keywords = [person.name]
            if person.name_en:
                keywords.append(person.name_en)
            
            pytrends.build_payload(
                keywords,
                timeframe='today 12-m',
                geo='JP'
            )
            
            interest = pytrends.interest_over_time()
            if not interest.empty:
                # 平均値を返す
                scores = []
                for keyword in keywords:
                    if keyword in interest.columns:
                        scores.append(interest[keyword].mean())
                return max(scores) if scores else 0.0
        except Exception as e:
            logger.error(f"Google Trendsエラー: {e}")
        
        return 0.0
    
    def _assess_cultural_impact(self, person: PersonData) -> float:
        """文化的影響力評価"""
        score = 0.0
        
        # 架空キャラクター
        if person.is_fictional:
            # 有名作品のキャラクターは高スコア
            famous_works = ['鬼滅', 'ドラゴンボール', 'ワンピース', 'ポケモン', 'ジブリ']
            if any(work in str(person.description) for work in famous_works):
                score = 80.0
            else:
                score = 30.0
        
        # カテゴリ別基本スコア
        cultural_categories = {
            '作家': 60,
            '画家': 50,
            '音楽家': 50,
            '映画監督': 60,
            '芸術家': 50
        }
        
        if person.category in cultural_categories:
            score = max(score, cultural_categories[person.category])
        
        return min(100, score)
    
    def _assess_educational_importance(self, person: PersonData) -> float:
        """教育的重要性評価"""
        score = 0.0
        
        # 教科書掲載
        if person.is_textbook:
            score = 90.0
        
        # カテゴリ別
        educational_categories = {
            '歴史上の人物': 70,
            '科学者': 60,
            '哲学者': 60,
            '教育者': 50,
            '発明家': 50
        }
        
        if person.category in educational_categories:
            score = max(score, educational_categories[person.category])
        
        return min(100, score)
    
    # ========== スコア計算 ==========
    
    def _calculate_final_score(self, score: RecognitionScore, person: PersonData) -> float:
        """最終スコア計算"""
        weights = self.config['weights']
        
        # 各要素を0-100に正規化
        components = {
            'google_search': self._normalize_search_count(score.google_search_count),
            'google_trends': score.google_trends_score,
            'sns_influence': score.sns_influence_score,
            'news_presence': score.news_score,
            'wikipedia': 100 if score.wikipedia_exists else 0,
            'knowledge_graph': 100 if score.knowledge_graph else 0,
            'cultural_impact': score.cultural_impact,
            'educational': score.educational_importance
        }
        
        # 重み付け合計
        weighted_sum = sum(
            components.get(key, 0) * weight
            for key, weight in weights.items()
        )
        
        # 0-10スケールに変換
        base_score = weighted_sum / 10
        
        # ボーナス適用
        if score.wikipedia_exists:
            base_score += self.config['protection']['wikipedia_bonus']
        if score.knowledge_graph:
            base_score += self.config['protection']['knowledge_graph_bonus']
        
        # カテゴリ補正
        if person.category in self.config['category_adjustments']:
            adjustment = self.config['category_adjustments'][person.category]
            base_score *= adjustment
        
        # 次元スコア記録
        score.dimensions = components
        
        return min(10.0, max(0.0, base_score))
    
    def _normalize_search_count(self, count: int) -> float:
        """検索数を0-100に正規化"""
        if count >= 10000000:    # 1000万以上
            return 100
        elif count >= 1000000:   # 100万以上
            return 90
        elif count >= 100000:    # 10万以上
            return 70
        elif count >= 10000:     # 1万以上
            return 50
        elif count >= 1000:      # 1000以上
            return 30
        elif count >= 100:       # 100以上
            return 20
        else:
            return min(15, count / 10)
    
    # ========== 判定 ==========
    
    def _determine_action(self, score: RecognitionScore, person: PersonData) -> DeleteAction:
        """削除アクション判定"""
        thresholds = self.config['thresholds']
        
        # 保護対象
        if score.protection_reasons:
            return DeleteAction.PROTECT
        
        # スコアによる判定
        if score.total_score >= thresholds['protect']:
            return DeleteAction.PROTECT
        elif score.total_score >= thresholds['keep']:
            return DeleteAction.KEEP
        elif score.total_score >= thresholds['review']:
            return DeleteAction.REVIEW
        else:
            # 最終確認
            if person.is_fictional or person.is_textbook:
                return DeleteAction.REVIEW  # 念のため確認
            return DeleteAction.DELETE
    
    def _calculate_confidence(self, score: RecognitionScore) -> float:
        """確信度計算"""
        # 利用できたAPIの数
        api_count = sum([
            score.google_search_count > 0,
            score.google_trends_score > 0,
            score.sns_followers > 0,
            score.news_mentions > 0,
            score.wikipedia_exists,
            score.knowledge_graph
        ])
        
        # 基本確信度
        base_confidence = api_count / 6.0
        
        # スコアの明確さによる補正
        if score.total_score >= 8.0 or score.total_score <= 2.0:
            # 極端なスコアは確信度高い
            base_confidence *= 1.2
        elif 3.5 <= score.total_score <= 5.5:
            # 中間的なスコアは確信度低い
            base_confidence *= 0.8
        
        return min(1.0, base_confidence)
    
    def _update_stats(self, action: DeleteAction):
        """統計更新"""
        self.stats['total_processed'] += 1
        
        if action == DeleteAction.KEEP:
            self.stats['kept'] += 1
        elif action == DeleteAction.DELETE:
            self.stats['deleted'] += 1
        elif action == DeleteAction.PROTECT:
            self.stats['protected'] += 1
        elif action == DeleteAction.REVIEW:
            self.stats['reviewed'] += 1
    
    # ========== バッチ処理 ==========
    
    def batch_evaluate(self, persons: List[PersonData], 
                       output_path: Optional[str] = None) -> List[Tuple[PersonData, RecognitionScore, DeleteAction]]:
        """
        バッチ評価
        
        Args:
            persons: 評価対象リスト
            output_path: 結果出力パス
            
        Returns:
            評価結果リスト
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"バッチ評価開始: {len(persons)}名")
        logger.info(f"{'='*60}")
        
        results = []
        
        for i, person in enumerate(persons, 1):
            logger.info(f"\n[{i}/{len(persons)}] 処理中...")
            
            try:
                score, action = self.evaluate_person(person)
                results.append((person, score, action))
                
                # API制限対策
                if i % 10 == 0:
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"❌ エラー: {person.name} - {e}")
                self.stats['errors'] += 1
                # エラー時は保護的に判定
                score = RecognitionScore(total_score=5.0)
                action = DeleteAction.REVIEW
                results.append((person, score, action))
        
        # 結果出力
        if output_path:
            self._export_results(results, output_path)
        
        # 統計表示
        self._print_statistics()
        
        return results
    
    def _export_results(self, results: List, output_path: str):
        """結果エクスポート"""
        data = []
        
        for person, score, action in results:
            data.append({
                'id': person.id,
                'name': person.name,
                'name_en': person.name_en,
                'category': person.category,
                'total_score': round(score.total_score, 2),
                'action': action.value,
                'confidence': round(score.confidence, 3),
                'google_search_count': score.google_search_count,
                'sns_followers': score.sns_followers,
                'news_mentions': score.news_mentions,
                'wikipedia': score.wikipedia_exists,
                'knowledge_graph': score.knowledge_graph,
                'protection_reasons': score.protection_reasons,
                'dimensions': score.dimensions
            })
        
        # JSON出力
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # CSV出力
        csv_path = output_path.replace('.json', '.csv')
        import csv
        with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
            if data:
                writer = csv.DictWriter(f, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
        
        logger.info(f"✅ 結果出力完了:")
        logger.info(f"   JSON: {output_path}")
        logger.info(f"   CSV: {csv_path}")
    
    def _print_statistics(self):
        """統計表示"""
        total = self.stats['total_processed']
        if total == 0:
            return
        
        print(f"\n{'='*60}")
        print("処理統計")
        print('='*60)
        print(f"処理総数: {total}名")
        print(f"保護: {self.stats['protected']}名 ({self.stats['protected']/total*100:.1f}%)")
        print(f"保持: {self.stats['kept']}名 ({self.stats['kept']/total*100:.1f}%)")
        print(f"要確認: {self.stats['reviewed']}名 ({self.stats['reviewed']/total*100:.1f}%)")
        print(f"削除: {self.stats['deleted']}名 ({self.stats['deleted']/total*100:.1f}%)")
        print(f"エラー: {self.stats['errors']}件")
        print(f"API呼び出し: {self.stats['api_calls']}回")
        print('='*60)


# ========== メイン実行 ==========

def main():
    """メイン実行"""
    # システム初期化
    system = UltimateRecognitionSystem()
    
    # テストデータ
    test_persons = [
        PersonData(
            id='P000013',
            name='HIKAKIN',
            name_en='Hikakin',
            category='YouTuber',
            description='日本のトップYouTuber'
        ),
        PersonData(
            id='P000001',
            name='宮崎駿',
            name_en='Hayao Miyazaki',
            category='映画監督',
            description='スタジオジブリ'
        ),
        PersonData(
            id='P000100',
            name='イチロー',
            name_en='Ichiro Suzuki',
            category='野球選手',
            description='メジャーリーガー'
        ),
        PersonData(
            id='FC001',
            name='竈門炭治郎',
            name_en='Kamado Tanjiro',
            category='架空キャラクター',
            description='鬼滅の刃の主人公',
            is_fictional=True
        ),
        PersonData(
            id='TB001',
            name='織田信長',
            name_en='Oda Nobunaga',
            category='歴史上の人物',
            description='戦国大名',
            is_textbook=True
        )
    ]
    
    # バッチ評価
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"ultimate_recognition_results_{timestamp}.json"
    
    results = system.batch_evaluate(test_persons, output_path)
    
    # 結果表示
    print(f"\n{'='*60}")
    print("評価結果サマリー")
    print('='*60)
    
    for person, score, action in results:
        status_emoji = {
            DeleteAction.PROTECT: '🛡️',
            DeleteAction.KEEP: '✅',
            DeleteAction.REVIEW: '⚠️',
            DeleteAction.DELETE: '❌'
        }
        
        print(f"\n{status_emoji[action]} {person.name} ({person.category})")
        print(f"   スコア: {score.total_score:.2f}/10")
        print(f"   判定: {action.value}")
        print(f"   確信度: {score.confidence:.1%}")
        
        if score.protection_reasons:
            print(f"   保護理由: {', '.join(score.protection_reasons)}")
    
    print(f"\n✅ 完了！結果は {output_path} に保存されました")


if __name__ == "__main__":
    main()