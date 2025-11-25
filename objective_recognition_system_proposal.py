#!/usr/bin/env python3
"""
Wikipedia API活用による客観的知名度評価システム提案
根本問題解決のための新アーキテクチャ
"""

import asyncio
import aiohttp
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@dataclass
class ObjectiveRecognitionScore:
    """客観的知名度スコア（Wikipedia API基準）"""
    person_id: str
    person_name: str

    # Wikipedia存在確認（基本指標）
    wikipedia_exists: bool = False
    wikipedia_languages: int = 0  # 多言語対応数

    # Wikipedia記事品質（信頼性指標）
    article_length: int = 0  # 文字数
    references_count: int = 0  # 参考文献数
    categories_count: int = 0  # カテゴリ数
    inbound_links: int = 0  # 被リンク数（他記事からの参照）

    # 社会的影響度（活動性指標）
    edit_frequency: float = 0.0  # 編集頻度（月間平均）
    page_views: int = 0  # 月間閲覧数
    discussion_activity: int = 0  # ディスカッションページ活動

    # 検証可能性（透明性指標）
    creation_date: Optional[str] = None  # 記事作成日
    last_edit_date: Optional[str] = None  # 最終編集日
    protection_status: str = "none"  # 保護ステータス

    # 品質フラグ
    is_stub: bool = False  # スタブ記事
    has_maintenance_tags: bool = False  # メンテナンスタグ有無
    is_disambiguation: bool = False  # 曖昧さ回避ページ

    # 計算済みスコア
    reliability_score: float = 0.0  # 信頼性スコア（0-10）
    social_impact_score: float = 0.0  # 社会的影響度スコア（0-10）
    final_score: float = 0.0  # 最終知名度スコア（0-10）

    # メタデータ
    evaluation_method: str = "wikipedia_api"
    confidence_level: float = 0.0
    timestamp: str = ""

class ObjectiveRecognitionEvaluator:
    """客観的知名度評価システム（Wikipedia API基準）"""

    def __init__(self):
        self.session = aiohttp.ClientSession()
        self.api_calls = 0
        self.cache = {}

        # 重み設定（透明性のため外部化可能）
        self.weights = {
            'wikipedia_existence': 3.0,      # Wikipedia記事存在（基礎点）
            'article_quality': 2.5,          # 記事品質（文字数、参考文献等）
            'social_impact': 2.0,           # 社会的影響（閲覧数、編集頻度）
            'international_recognition': 1.5, # 国際認知（多言語対応）
            'authority_validation': 1.0      # 権威性（保護ステータス等）
        }

    async def get_wikipedia_basic_info(self, person_name: str, lang: str = 'ja') -> Dict:
        """Wikipedia基本情報取得"""
        api_url = f"https://{lang}.wikipedia.org/w/api.php"

        params = {
            'action': 'query',
            'format': 'json',
            'titles': person_name,
            'prop': 'info|categories|links|pageviews|revisions',
            'inprop': 'protection|talkid',
            'clshow': '!hidden',  # 隠されていないカテゴリのみ
            'pllimit': 500,  # リンク数上限
            'rvprop': 'timestamp|user|size',  # リビジョン情報
            'rvlimit': 50,  # 最新50回の編集
            'pvipdays': 30  # 過去30日のページビュー
        }

        try:
            async with self.session.get(api_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    self.api_calls += 1
                    return self.parse_wikipedia_response(data)
                else:
                    logger.warning(f"Wikipedia API error: {response.status}")
                    return {}
        except Exception as e:
            logger.error(f"Wikipedia API call failed: {e}")
            return {}

    def parse_wikipedia_response(self, data: Dict) -> Dict:
        """Wikipedia APIレスポンス解析"""
        if 'query' not in data or 'pages' not in data['query']:
            return {'exists': False}

        pages = data['query']['pages']
        page_id = list(pages.keys())[0]

        if page_id == '-1':
            return {'exists': False}

        page = pages[page_id]

        # 基本情報抽出
        result = {
            'exists': True,
            'page_id': page_id,
            'title': page.get('title', ''),
            'length': page.get('length', 0),
            'categories_count': len(page.get('categories', [])),
            'links_count': len(page.get('links', [])),
            'is_redirect': 'redirect' in page,
        }

        # 編集履歴分析
        if 'revisions' in page:
            revisions = page['revisions']
            result['revisions_count'] = len(revisions)
            result['creation_date'] = revisions[-1]['timestamp'] if revisions else None
            result['last_edit_date'] = revisions[0]['timestamp'] if revisions else None

            # 編集頻度計算（月間平均）
            if len(revisions) > 1:
                first_edit = datetime.fromisoformat(revisions[-1]['timestamp'].replace('Z', '+00:00'))
                last_edit = datetime.fromisoformat(revisions[0]['timestamp'].replace('Z', '+00:00'))
                days_span = (last_edit - first_edit).days
                if days_span > 0:
                    result['edit_frequency'] = len(revisions) / (days_span / 30)

        # ページビュー（30日間）
        if 'pageviews' in page:
            result['page_views'] = sum(page['pageviews'].values())

        # 保護状況
        if 'protection' in page:
            result['protection_level'] = len(page['protection'])

        return result

    async def get_multilingual_presence(self, person_name: str) -> int:
        """多言語版Wikipedia存在確認"""
        languages = ['en', 'zh', 'fr', 'de', 'es', 'ru', 'ko']  # 主要言語
        tasks = []

        for lang in languages:
            task = self.check_wikipedia_exists(person_name, lang)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)
        language_count = sum(1 for result in results if result and not isinstance(result, Exception))

        return language_count

    async def check_wikipedia_exists(self, person_name: str, lang: str) -> bool:
        """Wikipedia記事存在確認（軽量版）"""
        api_url = f"https://{lang}.wikipedia.org/w/api.php"

        params = {
            'action': 'query',
            'format': 'json',
            'titles': person_name,
            'prop': 'info'
        }

        try:
            async with self.session.get(api_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    pages = data.get('query', {}).get('pages', {})
                    return '-1' not in pages
                return False
        except:
            return False

    async def calculate_reliability_score(self, wikipedia_data: Dict) -> float:
        """信頼性スコア計算"""
        if not wikipedia_data.get('exists', False):
            return 0.0

        score = 0.0

        # 記事の長さ（0-3点）
        length = wikipedia_data.get('length', 0)
        if length > 10000:  # 詳細な記事
            score += 3.0
        elif length > 5000:  # 中程度の記事
            score += 2.0
        elif length > 1000:  # 基本的な記事
            score += 1.0

        # カテゴリ数（0-2点）
        categories = wikipedia_data.get('categories_count', 0)
        score += min(2.0, categories / 5)

        # 編集履歴（0-2点）
        revisions = wikipedia_data.get('revisions_count', 0)
        if revisions > 100:
            score += 2.0
        elif revisions > 20:
            score += 1.0
        elif revisions > 5:
            score += 0.5

        # 保護レベル（権威性）（0-1点）
        protection = wikipedia_data.get('protection_level', 0)
        if protection > 0:
            score += 1.0

        # リンク数（0-2点）
        links = wikipedia_data.get('links_count', 0)
        score += min(2.0, links / 100)

        return min(10.0, score)

    async def calculate_social_impact_score(self, wikipedia_data: Dict, multilingual_count: int) -> float:
        """社会的影響度スコア計算"""
        if not wikipedia_data.get('exists', False):
            return 0.0

        score = 0.0

        # ページビュー（0-4点）
        page_views = wikipedia_data.get('page_views', 0)
        if page_views > 100000:  # 月間10万PV以上
            score += 4.0
        elif page_views > 50000:
            score += 3.0
        elif page_views > 10000:
            score += 2.0
        elif page_views > 1000:
            score += 1.0

        # 編集頻度（0-3点）
        edit_frequency = wikipedia_data.get('edit_frequency', 0)
        if edit_frequency > 10:  # 月間10回以上編集
            score += 3.0
        elif edit_frequency > 3:
            score += 2.0
        elif edit_frequency > 1:
            score += 1.0

        # 国際認知度（0-3点）
        score += min(3.0, multilingual_count / 3)

        return min(10.0, score)

    async def evaluate_person(self, person_name: str) -> ObjectiveRecognitionScore:
        """個人の客観的知名度評価"""
        logger.info(f"評価開始: {person_name}")

        # 1. Wikipedia基本情報取得
        wikipedia_data = await self.get_wikipedia_basic_info(person_name)

        # 2. 多言語対応確認
        multilingual_count = 0
        if wikipedia_data.get('exists', False):
            multilingual_count = await self.get_multilingual_presence(person_name)

        # 3. 信頼性スコア計算
        reliability_score = await self.calculate_reliability_score(wikipedia_data)

        # 4. 社会的影響度スコア計算
        social_impact_score = await self.calculate_social_impact_score(wikipedia_data, multilingual_count)

        # 5. 最終スコア計算（重み付け平均）
        final_score = (reliability_score * 0.6 + social_impact_score * 0.4)

        # 6. 品質フラグ設定
        is_stub = wikipedia_data.get('length', 0) < 1000
        is_disambiguation = 'disambiguation' in wikipedia_data.get('title', '').lower()

        # 7. 信頼度計算
        confidence = 0.9 if wikipedia_data.get('exists', False) else 0.1
        if wikipedia_data.get('page_views', 0) > 10000:
            confidence += 0.05
        if multilingual_count > 2:
            confidence += 0.05
        confidence = min(1.0, confidence)

        # 8. スコアオブジェクト生成
        score = ObjectiveRecognitionScore(
            person_id=f"eval_{hash(person_name) % 1000000:06d}",
            person_name=person_name,
            wikipedia_exists=wikipedia_data.get('exists', False),
            wikipedia_languages=multilingual_count,
            article_length=wikipedia_data.get('length', 0),
            categories_count=wikipedia_data.get('categories_count', 0),
            inbound_links=wikipedia_data.get('links_count', 0),
            edit_frequency=wikipedia_data.get('edit_frequency', 0.0),
            page_views=wikipedia_data.get('page_views', 0),
            creation_date=wikipedia_data.get('creation_date'),
            last_edit_date=wikipedia_data.get('last_edit_date'),
            protection_status="protected" if wikipedia_data.get('protection_level', 0) > 0 else "none",
            is_stub=is_stub,
            is_disambiguation=is_disambiguation,
            reliability_score=reliability_score,
            social_impact_score=social_impact_score,
            final_score=final_score,
            confidence_level=confidence,
            timestamp=datetime.now().isoformat()
        )

        logger.info(f"評価完了: {person_name} -> {final_score:.2f}")
        return score

    async def close(self):
        """セッション終了"""
        await self.session.close()

# 使用例とテスト
async def test_objective_system():
    """システムテスト"""
    evaluator = ObjectiveRecognitionEvaluator()

    test_persons = [
        "大谷翔平",  # 確実に高スコア期待
        "HIKAKIN",   # YouTuber、高スコア期待
        "アインシュタイン",  # 歴史的人物、最高スコア期待
        "TestPerson_9999",  # 存在しない人物、0スコア期待
        "山田太郎"   # 一般的な名前、低スコア期待
    ]

    results = []
    for person in test_persons:
        try:
            score = await evaluator.evaluate_person(person)
            results.append(score)
            print(f"{person}: {score.final_score:.2f} (信頼度: {score.confidence_level:.2f})")
        except Exception as e:
            print(f"評価エラー {person}: {e}")

    await evaluator.close()
    return results

if __name__ == "__main__":
    # テスト実行
    print("客観的知名度評価システム テスト開始")
    asyncio.run(test_objective_system())
