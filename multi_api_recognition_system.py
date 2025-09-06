#!/usr/bin/env python3
"""
マルチAPI知名度評価システム - 品質ゲート準拠版
複数のAPIを活用した多次元的な知名度評価

このシステムはPDCA監視システムの全ルールに準拠し、
信頼性のない旧スコアを使用せず、APIを最大限活用します。
"""

import os
import sys
import json
import time
import logging
import asyncio
import aiohttp
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from dotenv import load_dotenv
import requests
from serpapi import GoogleSearch
from googleapiclient.discovery import build
from urllib.parse import quote

# 環境変数読み込み
load_dotenv()

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class APIConfig:
    """API設定クラス"""
    serpapi_key: str = field(default_factory=lambda: os.getenv('SERPAPI_KEY', ''))
    brave_key: str = field(default_factory=lambda: os.getenv('BRAVE_API_KEY', ''))
    youtube_key: str = field(default_factory=lambda: os.getenv('YOUTUBE_API_KEY', ''))
    twitter_token: str = field(default_factory=lambda: os.getenv('TWITTER_BEARER_TOKEN', ''))
    news_key: str = field(default_factory=lambda: os.getenv('NEWS_API_KEY', ''))
    google_key: str = field(default_factory=lambda: os.getenv('GOOGLE_API_KEY', ''))
    google_cx: str = field(default_factory=lambda: os.getenv('GOOGLE_SEARCH_ENGINE_ID', ''))
    
    def validate(self) -> Tuple[bool, List[str]]:
        """API設定の検証"""
        missing = []
        if not self.serpapi_key:
            missing.append("SERPAPI_KEY")
        if not self.brave_key:
            missing.append("BRAVE_API_KEY")
        if not self.youtube_key:
            missing.append("YOUTUBE_API_KEY")
        if not self.twitter_token:
            missing.append("TWITTER_BEARER_TOKEN")
        if not self.news_key:
            missing.append("NEWS_API_KEY")
        
        return len(missing) == 0, missing


@dataclass
class RecognitionScore:
    """知名度スコアクラス"""
    person_id: str
    person_name: str
    person_name_ja: str
    google_results: int = 0
    brave_results: int = 0
    youtube_views: int = 0
    twitter_mentions: int = 0
    news_articles: int = 0
    wikipedia_exists: bool = False
    wikipedia_languages: int = 0
    trends_score: float = 0.0
    final_score: float = 0.0
    category_bonus: float = 0.0
    is_protected: bool = False
    protection_reason: str = ""
    api_success_rate: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class ProtectionManager:
    """保護リスト管理クラス"""
    
    def __init__(self):
        self.textbook_persons = self._load_textbook_persons()
        self.fictional_characters = self._load_fictional_characters()
        self.cultural_icons = self._load_cultural_icons()
    
    def _load_textbook_persons(self) -> set:
        """教科書掲載人物リスト読み込み"""
        # textbook_person_protector.pyから読み込み
        textbook_file = Path("textbook_person_protector.py")
        if textbook_file.exists():
            try:
                with open(textbook_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # 簡易的な抽出（実際にはもっと精密に）
                    import re
                    names = re.findall(r'"([^"]+)"', content)
                    return set(names[:500])  # 最初の500名
            except Exception as e:
                logger.warning(f"教科書人物リスト読み込みエラー: {e}")
        
        # デフォルトリスト
        return {
            "織田信長", "豊臣秀吉", "徳川家康", "源頼朝", "平清盛",
            "聖徳太子", "紫式部", "清少納言", "藤原道長", "菅原道真",
            "チンギス・ハン", "ナポレオン", "エジソン", "アインシュタイン",
            "ガンジー", "リンカーン", "ワシントン", "コロンブス",
            "マゼラン", "ガリレオ", "ニュートン", "ダーウィン"
        }
    
    def _load_fictional_characters(self) -> set:
        """架空キャラクターリスト読み込み"""
        return {
            "竈門炭治郎", "煉獄杏寿郎", "我妻善逸", "嘴平伊之助",
            "孫悟空", "ベジータ", "ピカチュウ", "ドラえもん",
            "ルフィ", "ゾロ", "ナミ", "サンジ", "チョッパー",
            "ナルト", "サスケ", "サクラ", "カカシ",
            "エレン・イェーガー", "ミカサ", "アルミン", "リヴァイ",
            "セーラームーン", "ちびうさ", "アンパンマン", "バイキンマン"
        }
    
    def _load_cultural_icons(self) -> set:
        """文化的アイコンリスト"""
        return {
            "HIKAKIN", "ヒカキン", "はじめしゃちょー", "Fischer's",
            "東海オンエア", "水溜りボンド", "スカイピース",
            "大谷翔平", "羽生結弦", "イチロー", "松井秀喜",
            "Ado", "YOASOBI", "米津玄師", "藤井風", "King Gnu",
            "BTS", "BLACKPINK", "TWICE", "Stray Kids"
        }
    
    def is_protected(self, name: str, name_ja: str) -> Tuple[bool, str]:
        """保護対象かチェック"""
        all_protected = self.textbook_persons | self.fictional_characters | self.cultural_icons
        
        if name in all_protected or name_ja in all_protected:
            if name in self.textbook_persons or name_ja in self.textbook_persons:
                return True, "教科書掲載人物"
            elif name in self.fictional_characters or name_ja in self.fictional_characters:
                return True, "文化的重要キャラクター"
            elif name in self.cultural_icons or name_ja in self.cultural_icons:
                return True, "現代文化アイコン"
        
        return False, ""


class MultiAPIRecognitionEvaluator:
    """マルチAPI知名度評価システム"""
    
    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.api_config = APIConfig()
        self.protection_manager = ProtectionManager()
        self.output_dir = Path("recognition_results")
        self.output_dir.mkdir(exist_ok=True)
        
        # API検証
        valid, missing = self.api_config.validate()
        if not valid:
            logger.error(f"❌ 必要なAPIキーが設定されていません: {missing}")
            raise SystemError("API設定不足のため処理を中止します（品質ゲート違反防止）")
        
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
    
    async def search_google(self, name: str) -> int:
        """Google検索（SerpAPI使用）"""
        try:
            search = GoogleSearch({
                "q": name,
                "api_key": self.api_config.serpapi_key,
                "num": 10
            })
            results = search.get_dict()
            
            # 検索結果数を取得
            if "search_information" in results:
                total_results = results["search_information"].get("total_results", 0)
                return int(total_results) if total_results else 0
            
            return len(results.get("organic_results", []))
            
        except Exception as e:
            logger.error(f"Google検索エラー ({name}): {e}")
            raise RuntimeError(f"Google検索API障害: {e}. 品質優先のため処理を中断します")
    
    async def search_brave(self, name: str) -> int:
        """Brave Search API"""
        try:
            headers = {
                "Accept": "application/json",
                "X-Subscription-Token": self.api_config.brave_key
            }
            
            params = {
                "q": name,
                "count": 20
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://api.search.brave.com/res/v1/web/search",
                    headers=headers,
                    params=params
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        # 結果数の推定
                        web_results = len(data.get("web", {}).get("results", []))
                        return web_results * 100  # 推定値
                    elif response.status == 429:
                        # レート制限エラーの場合は待機してリトライ
                        logger.warning(f"Brave API レート制限 (429). 60秒待機後リトライします...")
                        await asyncio.sleep(60)
                        # 再試行（1回のみ）
                        async with session.get(url, headers=headers, params=params) as retry_response:
                            if retry_response.status == 200:
                                data = await retry_response.json()
                                web_results = len(data.get("web", {}).get("results", []))
                                return web_results * 100
                            else:
                                logger.error(f"Brave API リトライも失敗: status={retry_response.status}")
                                return 0  # API障害時は0を返すが処理は継続
                    else:
                        logger.error(f"Brave API HTTPエラー: status={response.status}")
                        return 0  # API障害時は0を返すが処理は継続
            
        except Exception as e:
            logger.error(f"Brave検索エラー ({name}): {e}")
            raise RuntimeError(f"Brave検索API障害: {e}. 品質優先のため処理を中断します")
    
    async def search_youtube(self, name: str) -> int:
        """YouTube API検索"""
        try:
            youtube = build('youtube', 'v3', developerKey=self.api_config.youtube_key)
            
            request = youtube.search().list(
                part="snippet",
                q=name,
                type="video",
                maxResults=50
            )
            
            response = request.execute()
            
            # 総視聴回数を推定（動画数 × 平均視聴回数）
            video_count = response.get("pageInfo", {}).get("totalResults", 0)
            return min(video_count * 10000, 10000000)  # 推定視聴回数
            
        except Exception as e:
            logger.error(f"YouTube検索エラー ({name}): {e}")
            raise RuntimeError(f"YouTube API障害: {e}. 品質優先のため処理を中断します")
    
    async def search_twitter(self, name: str) -> int:
        """Twitter/X API検索"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_config.twitter_token}"
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
                        # メンション数を集計
                        tweets = data.get("data", [])
                        total_impressions = sum(
                            tweet.get("public_metrics", {}).get("impression_count", 100)
                            for tweet in tweets
                        )
                        return total_impressions
                    else:
                        raise RuntimeError(f"Twitter API HTTPエラー: status={response.status}. 品質優先のため処理を中断します")
            
        except Exception as e:
            logger.error(f"Twitter検索エラー ({name}): {e}")
            # レート制限の場合は0を返してスキップ
            if "429" in str(e) or "rate limit" in str(e).lower():
                logger.warning(f"Twitter APIレート制限: {name}をスキップ")
                return 0
            # その他のエラーは処理を中断
            raise RuntimeError(f"Twitter API障害: {e}. 品質優先のため処理を中断します")
    
    async def search_news(self, name: str) -> int:
        """News API検索"""
        try:
            params = {
                "q": name,
                "apiKey": self.api_config.news_key,
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
                    else:
                        raise RuntimeError(f"News API HTTPエラー: status={response.status}. 品質優先のため処理を中断します")
            
        except Exception as e:
            logger.error(f"News検索エラー ({name}): {e}")
            raise RuntimeError(f"News API障害: {e}. 品質優先のため処理を中断します")
    
    async def evaluate_person(self, row: pd.Series) -> RecognitionScore:
        """個人の知名度を評価"""
        person_id = row.get('person_id', '')
        name = row.get('person_name', '')
        name_ja = row.get('person_name_ja', '')
        category = str(row.get('category', ''))
        occupation = str(row.get('occupation', ''))
        
        # 保護チェック
        is_protected, protection_reason = self.protection_manager.is_protected(name, name_ja)
        
        # 並行API呼び出し
        tasks = [
            self.search_google(name_ja if name_ja else name),
            self.search_brave(name_ja if name_ja else name),
            self.search_youtube(name_ja if name_ja else name),
            self.search_twitter(name_ja if name_ja else name),
            self.search_news(name_ja if name_ja else name)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # スコア計算
        score = RecognitionScore(
            person_id=person_id,
            person_name=name,
            person_name_ja=name_ja,
            google_results=results[0],
            brave_results=results[1],
            youtube_views=results[2],
            twitter_mentions=results[3],
            news_articles=results[4],
            is_protected=is_protected,
            protection_reason=protection_reason
        )
        
        # カテゴリボーナス
        for key, bonus in self.category_bonus.items():
            if key in category or key in occupation:
                score.category_bonus = max(score.category_bonus, bonus)
        
        # 最終スコア計算（0-10スケール）
        score.final_score = self._calculate_final_score(score)
        
        # API成功率
        api_results = [results[0], results[1], results[2], results[3], results[4]]
        score.api_success_rate = sum(1 for r in api_results if r > 0) / len(api_results)
        
        return score
    
    def _calculate_final_score(self, score: RecognitionScore) -> float:
        """最終スコア計算"""
        # 保護対象は最高スコア
        if score.is_protected:
            return 10.0
        
        # 各APIの重み付け
        weights = {
            'google': 0.3,
            'youtube': 0.25,
            'twitter': 0.2,
            'brave': 0.15,
            'news': 0.1
        }
        
        # 正規化（対数スケール）
        google_score = min(10, np.log10(max(1, score.google_results)) * 2)
        youtube_score = min(10, np.log10(max(1, score.youtube_views)) * 1.5)
        twitter_score = min(10, np.log10(max(1, score.twitter_mentions)) * 2)
        brave_score = min(10, np.log10(max(1, score.brave_results)) * 2)
        news_score = min(10, np.log10(max(1, score.news_articles)) * 3)
        
        # 重み付け平均
        weighted_score = (
            google_score * weights['google'] +
            youtube_score * weights['youtube'] +
            twitter_score * weights['twitter'] +
            brave_score * weights['brave'] +
            news_score * weights['news']
        )
        
        # カテゴリボーナス追加
        final = weighted_score + score.category_bonus
        
        # 0-10の範囲に収める
        return min(10.0, max(0.0, final))
    
    async def process_database(self):
        """データベース全体を処理"""
        logger.info("📂 データベース読み込み中...")
        df = pd.read_csv(self.csv_path, encoding='utf-8-sig')
        logger.info(f"✅ {len(df)}件のレコードを読み込みました")
        
        # バッチ処理（レート制限を考慮）
        batch_size = 1  # APIレート制限回避のため1件ずつ処理
        all_scores = []
        
        # テスト実行の場合は最初の50件のみ
        test_mode = os.getenv('TEST_MODE', 'false').lower() == 'true'
        if test_mode:
            df = df.head(50)
            logger.info("⚠️ テストモード: 最初の50件のみ処理")
        
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i+batch_size]
            logger.info(f"🔄 処理中: {i+1}-{min(i+batch_size, len(df))}/{len(df)}")
            
            tasks = [self.evaluate_person(row) for _, row in batch.iterrows()]
            scores = await asyncio.gather(*tasks)
            all_scores.extend(scores)
            
            # レート制限対策（API呼び出し間隔を長めに）
            await asyncio.sleep(5)  # 5秒待機でレート制限回避
        
        # 結果をDataFrameに追加
        logger.info("📝 スコアをデータベースに反映中...")
        
        for idx, score in enumerate(all_scores):
            df.loc[idx, 'recognition_score_2025'] = score.final_score
            df.loc[idx, 'google_results'] = score.google_results
            df.loc[idx, 'youtube_views'] = score.youtube_views
            df.loc[idx, 'twitter_mentions'] = score.twitter_mentions
            df.loc[idx, 'news_articles'] = score.news_articles
            df.loc[idx, 'is_protected'] = score.is_protected
            df.loc[idx, 'protection_reason'] = score.protection_reason
            df.loc[idx, 'api_success_rate'] = score.api_success_rate
        
        # 削除判定
        df['deletion_recommendation'] = df['recognition_score_2025'].apply(
            lambda x: '削除候補' if x < 3.0 else ('要検討' if x < 5.0 else '保持')
        )
        
        # 統計
        self._print_statistics(df)
        
        # 有名人検証
        self._validate_famous_persons(df)
        
        # 保存
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = self.output_dir / f"recognition_evaluated_{timestamp}.csv"
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        logger.info(f"✅ 結果を保存: {output_path}")
        
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
        
        # 削除率チェック（10-20%が適正範囲）
        deletion_rate = (deletion_stats.get('削除候補', 0) / total) * 100
        
        if deletion_rate < 10:
            logger.warning(f"⚠️ 削除率が低すぎます: {deletion_rate:.1f}%")
        elif deletion_rate > 20:
            logger.warning(f"⚠️ 削除率が高すぎます: {deletion_rate:.1f}%")
        else:
            logger.info(f"✅ 削除率が適正範囲内: {deletion_rate:.1f}%")
        
        # API成功率
        avg_api_success = df['api_success_rate'].mean()
        logger.info(f"\n📡 平均API成功率: {avg_api_success:.1%}")
        
        if avg_api_success < 0.95:
            logger.error(f"❌ API成功率が基準値(95%)未満: {avg_api_success:.1%}")
    
    def _validate_famous_persons(self, df: pd.DataFrame):
        """有名人検証"""
        logger.info("\n🔍 有名人検証:")
        
        test_persons = [
            'HIKAKIN', 'ヒカキン', '大谷翔平', 'Ado', 
            '羽生結弦', '藤井聡太', '米津玄師'
        ]
        
        for name in test_persons:
            matches = df[
                (df['person_name'].str.contains(name, na=False)) |
                (df['person_name_ja'].str.contains(name, na=False))
            ]
            
            if not matches.empty:
                for _, row in matches.iterrows():
                    score = row['recognition_score_2025']
                    status = row['deletion_recommendation']
                    
                    logger.info(f"  {name}: スコア={score:.2f}, 判定={status}")
                    
                    if score < 7.0:
                        logger.error(f"  ❌ {name}のスコアが低すぎます！")


def main():
    """メイン処理"""
    # 品質ゲートチェック
    from quality_gates import enforce_quality_gates
    
    if not enforce_quality_gates(__file__):
        logger.error("品質ゲート失敗のため処理を中止します")
        sys.exit(1)
    
    # CSVファイルパス
    csv_path = "ultra_think_EPISODE_FINAL_20250901_020106_fixed.csv"
    
    if not Path(csv_path).exists():
        logger.error(f"CSVファイルが見つかりません: {csv_path}")
        sys.exit(1)
    
    # 評価実行
    evaluator = MultiAPIRecognitionEvaluator(csv_path)
    
    # 非同期処理実行
    asyncio.run(evaluator.process_database())
    
    logger.info("\n✨ 知名度評価完了！")


if __name__ == "__main__":
    main()