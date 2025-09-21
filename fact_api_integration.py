#!/usr/bin/env python3
"""
Fact API Integration Layer
各種APIとMCPツールを統合してデータを取得
"""

import json
import asyncio
import aiohttp
from datetime import datetime
from typing import Dict, List, Optional, Any
import re
from pathlib import Path
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FactAPIIntegration:
    """統合APIレイヤー"""

    def __init__(self):
        self.wikipedia_base = "https://ja.wikipedia.org/api/rest_v1"
        self.session = None
        self.rate_limits = {
            'wikipedia': {'calls': 0, 'limit': 100, 'reset_time': None},
            'brave_search': {'calls': 0, 'limit': 50, 'reset_time': None}
        }

    async def __aenter__(self):
        """非同期コンテキストマネージャー開始"""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """非同期コンテキストマネージャー終了"""
        if self.session:
            await self.session.close()

    async def fetch_wikipedia_summary(self, person_name: str) -> Optional[Dict]:
        """
        Wikipedia APIから人物の要約を取得

        Args:
            person_name: 人物名

        Returns:
            要約データ
        """
        try:
            # Wikipedia APIエンドポイント
            url = f"{self.wikipedia_base}/page/summary/{person_name}"

            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()

                    return {
                        'source': 'wikipedia',
                        'title': data.get('title', ''),
                        'extract': data.get('extract', ''),
                        'description': data.get('description', ''),
                        'timestamp': datetime.now().isoformat(),
                        'confidence': 0.9  # Wikipedia信頼度
                    }
                else:
                    logger.warning(f"Wikipedia API error for {person_name}: {response.status}")
                    return None

        except Exception as e:
            logger.error(f"Error fetching Wikipedia data for {person_name}: {e}")
            return None

    async def search_recent_news(self, person_name: str, year: int = 2024) -> List[Dict]:
        """
        最近のニュースを検索（Brave Search APIシミュレーション）

        Args:
            person_name: 人物名
            year: 検索年

        Returns:
            ニュース記事リスト
        """
        # 実際のMCP Brave Searchツールを使用する場合はここで呼び出し
        # ここではシミュレーションデータを返す

        news_data = []

        # 既知の2024年の偉業（ハードコード）
        known_achievements_2024 = {
            '大谷翔平': [
                {
                    'title': '大谷翔平が史上初の50-50を達成',
                    'date': '2024-09-19',
                    'fact': '54本塁打、59盗塁で史上初の50本塁打50盗塁を達成',
                    'source': 'ESPN',
                    'keywords': ['50-50', '史上初', '54本塁打', '59盗塁']
                },
                {
                    'title': '大谷翔平、ワールドシリーズ初優勝',
                    'date': '2024-10-30',
                    'fact': 'ドジャースでワールドシリーズ初優勝を達成',
                    'source': 'MLB公式',
                    'keywords': ['ワールドシリーズ', '優勝', 'ドジャース']
                }
            ],
            '藤井聡太': [
                {
                    'title': '藤井聡太八冠達成',
                    'date': '2024-10-11',
                    'fact': '史上最年少で八冠独占を達成',
                    'source': '日本将棋連盟',
                    'keywords': ['八冠', '史上最年少', '独占']
                }
            ]
        }

        if person_name in known_achievements_2024:
            for achievement in known_achievements_2024[person_name]:
                news_data.append({
                    'source': 'news_api',
                    'title': achievement['title'],
                    'date': achievement['date'],
                    'fact': achievement['fact'],
                    'keywords': achievement['keywords'],
                    'confidence': 0.95,
                    'year': 2024
                })

        return news_data

    async def extract_facts_from_text(self, text: str, person_name: str) -> List[Dict]:
        """
        テキストから事実を抽出

        Args:
            text: 分析対象テキスト
            person_name: 人物名

        Returns:
            抽出された事実リスト
        """
        facts = []

        # 年齢と偉業のパターンを抽出
        age_pattern = r'(\d+)歳[のとき時]?[にで、]([^。]+)'
        year_pattern = r'(19|20)\d{2}年[にで、]([^。]+)'

        # 年齢ベースの事実抽出
        for match in re.finditer(age_pattern, text):
            age = int(match.group(1))
            fact_text = match.group(2)

            facts.append({
                'age': age,
                'fact': fact_text,
                'source_type': 'age_based'
            })

        # 年ベースの事実抽出
        for match in re.finditer(year_pattern, text):
            year = int(match.group(0)[:4])
            fact_text = match.group(2)

            # 生年から年齢を計算（仮定値）
            estimated_age = year - 1990  # 仮の生年

            facts.append({
                'year': year,
                'age': estimated_age,
                'fact': fact_text,
                'source_type': 'year_based'
            })

        return facts

    def calculate_scores(self, fact: Dict) -> Dict:
        """
        事実のスコアを計算

        Args:
            fact: 事実データ

        Returns:
            スコア付き事実データ
        """
        # キーワードベースのスコア計算
        keywords = fact.get('keywords', [])
        fact_text = fact.get('fact', '')

        # 感情スコア（偉業の重要度）
        emotional_keywords = ['史上初', '世界初', '優勝', '金メダル', '記録']
        emotional_score = 0.7
        for keyword in emotional_keywords:
            if keyword in fact_text or keyword in keywords:
                emotional_score += 0.1
        emotional_score = min(1.0, emotional_score)

        # 教育スコア（学習価値）
        educational_keywords = ['達成', '開発', '発明', '貢献', '革新']
        educational_score = 0.7
        for keyword in educational_keywords:
            if keyword in fact_text or keyword in keywords:
                educational_score += 0.1
        educational_score = min(1.0, educational_score)

        fact['emotional_score'] = emotional_score
        fact['educational_score'] = educational_score

        return fact

    async def fetch_person_facts(self, person_name: str) -> Dict:
        """
        人物の事実を統合的に取得

        Args:
            person_name: 人物名

        Returns:
            統合された事実データ
        """
        all_facts = []

        # Wikipedia データ取得
        wiki_data = await self.fetch_wikipedia_summary(person_name)
        if wiki_data:
            wiki_facts = await self.extract_facts_from_text(
                wiki_data.get('extract', ''),
                person_name
            )
            for fact in wiki_facts:
                fact['sources'] = ['Wikipedia']
                fact = self.calculate_scores(fact)
                all_facts.append(fact)

        # 最新ニュース取得
        news_data = await self.search_recent_news(person_name, 2024)
        for news in news_data:
            fact = {
                'fact': news['fact'],
                'year': news.get('year', 2024),
                'keywords': news.get('keywords', []),
                'sources': [news.get('source', 'news')],
                'confidence': news.get('confidence', 0.8)
            }
            fact = self.calculate_scores(fact)
            all_facts.append(fact)

        # 重複排除と優先順位付け
        unique_facts = self._deduplicate_facts(all_facts)

        return {
            'person_name': person_name,
            'facts': unique_facts,
            'last_updated': datetime.now().isoformat(),
            'sources_used': list(set(sum([f.get('sources', []) for f in unique_facts], [])))
        }

    def _deduplicate_facts(self, facts: List[Dict]) -> List[Dict]:
        """
        事実の重複を排除

        Args:
            facts: 事実リスト

        Returns:
            重複排除済みリスト
        """
        seen = set()
        unique = []

        for fact in facts:
            # 事実テキストの最初の20文字をキーとして使用
            key = fact.get('fact', '')[:20]
            if key and key not in seen:
                seen.add(key)
                unique.append(fact)

        # スコアでソート
        unique.sort(
            key=lambda f: f.get('emotional_score', 0) * f.get('educational_score', 0),
            reverse=True
        )

        return unique


async def test_integration():
    """統合テスト"""
    async with FactAPIIntegration() as api:
        print("=" * 60)
        print("Fact API Integration Test")
        print("=" * 60)

        # 大谷翔平のデータ取得テスト
        person_name = "大谷翔平"
        print(f"\n📊 {person_name}のデータ取得中...")

        facts_data = await api.fetch_person_facts(person_name)

        print(f"\n✅ 取得した事実数: {len(facts_data['facts'])}")
        print(f"📚 使用したソース: {', '.join(facts_data['sources_used'])}")

        # 上位3件の事実を表示
        print("\n🏆 上位3件の事実:")
        for i, fact in enumerate(facts_data['facts'][:3], 1):
            print(f"\n{i}. {fact.get('fact', '')[:100]}...")
            print(f"   スコア: 感情 {fact.get('emotional_score', 0):.2f}, "
                  f"教育 {fact.get('educational_score', 0):.2f}")
            print(f"   ソース: {', '.join(fact.get('sources', []))}")


if __name__ == "__main__":
    # テスト実行
    asyncio.run(test_integration())