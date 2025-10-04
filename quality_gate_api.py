#!/usr/bin/env python3
"""
Quality Gate API Integration Layer

外部APIとの統合を管理し、事実確認と検証を行います。
Wikipedia、Google Trends等の外部サービスと連携。
"""

import asyncio
import aiohttp
import json
import hashlib
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import os
from pathlib import Path


@dataclass
class PersonInfo:
    """人物情報"""
    name: str
    exists: bool
    birth_year: Optional[int]
    death_year: Optional[int]
    occupation: Optional[str]
    notable_works: List[str]
    popularity_score: float
    wikipedia_url: Optional[str]


@dataclass
class MilestoneInfo:
    """節目情報"""
    age: int
    event: str
    year: int
    importance_score: float
    is_debut: bool
    is_achievement: bool
    source: str


class CacheManager:
    """APIレスポンスのキャッシュ管理"""

    def __init__(self, cache_dir: str = ".cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_ttl = timedelta(hours=24)

    def _get_cache_key(self, api_name: str, params: Dict) -> str:
        """キャッシュキーを生成"""
        param_str = json.dumps(params, sort_keys=True)
        hash_str = hashlib.md5(f"{api_name}:{param_str}".encode()).hexdigest()
        return hash_str

    def get(self, api_name: str, params: Dict) -> Optional[Dict]:
        """キャッシュから取得"""
        cache_key = self._get_cache_key(api_name, params)
        cache_file = self.cache_dir / f"{api_name}_{cache_key}.json"

        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)

                # TTLチェック
                cached_at = datetime.fromisoformat(cache_data['cached_at'])
                if datetime.now() - cached_at < self.cache_ttl:
                    return cache_data['data']
            except Exception:
                pass

        return None

    def set(self, api_name: str, params: Dict, data: Dict):
        """キャッシュに保存"""
        cache_key = self._get_cache_key(api_name, params)
        cache_file = self.cache_dir / f"{api_name}_{cache_key}.json"

        cache_data = {
            'cached_at': datetime.now().isoformat(),
            'params': params,
            'data': data
        }

        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False)


class WikipediaAPI:
    """Wikipedia API統合"""

    BASE_URL = "https://ja.wikipedia.org/api/rest_v1"

    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager

    async def check_person_existence(self, name: str) -> PersonInfo:
        """人物の実在性を確認"""
        # キャッシュチェック
        cached = self.cache.get('wikipedia', {'name': name})
        if cached:
            return PersonInfo(**cached)

        try:
            async with aiohttp.ClientSession() as session:
                # ページの存在確認
                url = f"{self.BASE_URL}/page/summary/{name}"
                async with session.get(url) as response:
                    if response.status == 404:
                        return PersonInfo(
                            name=name,
                            exists=False,
                            birth_year=None,
                            death_year=None,
                            occupation=None,
                            notable_works=[],
                            popularity_score=0.0,
                            wikipedia_url=None
                        )

                    data = await response.json()

                    # 人物情報を解析
                    person_info = PersonInfo(
                        name=name,
                        exists=True,
                        birth_year=self._extract_year(data.get('extract', ''), '生'),
                        death_year=self._extract_year(data.get('extract', ''), '没'),
                        occupation=self._extract_occupation(data.get('extract', '')),
                        notable_works=[],
                        popularity_score=self._calculate_popularity(data),
                        wikipedia_url=data.get('content_urls', {}).get('desktop', {}).get('page')
                    )

                    # キャッシュ保存
                    self.cache.set('wikipedia', {'name': name}, person_info.__dict__)

                    return person_info

        except Exception as e:
            print(f"Wikipedia API エラー: {e}")
            return PersonInfo(
                name=name,
                exists=False,
                birth_year=None,
                death_year=None,
                occupation=None,
                notable_works=[],
                popularity_score=0.0,
                wikipedia_url=None
            )

    def _extract_year(self, text: str, keyword: str) -> Optional[int]:
        """テキストから年を抽出"""
        import re
        pattern = rf"{keyword}.*?(\d{{4}})年"
        match = re.search(pattern, text)
        if match:
            return int(match.group(1))
        return None

    def _extract_occupation(self, text: str) -> Optional[str]:
        """職業を抽出"""
        occupations = [
            '俳優', '女優', '歌手', '作家', '画家', '政治家',
            '実業家', 'スポーツ選手', '科学者', '医師', '教授'
        ]
        for occupation in occupations:
            if occupation in text:
                return occupation
        return None

    def _calculate_popularity(self, data: Dict) -> float:
        """人気度スコアを計算"""
        score = 5.0  # 基準スコア

        # ページビュー数があれば加点
        if 'pageviews' in data:
            views = data['pageviews']
            if views > 10000:
                score += 2.0
            elif views > 1000:
                score += 1.0

        # 抜粋の長さで加点
        extract_length = len(data.get('extract', ''))
        if extract_length > 500:
            score += 1.5
        elif extract_length > 200:
            score += 0.5

        return min(10.0, score)


class GoogleTrendsAPI:
    """Google Trends API統合（簡易実装）"""

    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager

    async def get_popularity_trend(self, name: str) -> Dict[str, float]:
        """人気度トレンドを取得"""
        # キャッシュチェック
        cached = self.cache.get('trends', {'name': name})
        if cached:
            return cached

        # 簡易的なモックデータ（実際にはGoogle Trends APIを使用）
        trend_data = {
            'current_score': 0.0,
            'peak_score': 0.0,
            'average_score': 0.0,
            'trending': False
        }

        # 有名人リストでシミュレート
        famous_people = {
            '大谷翔平': {'current_score': 95, 'peak_score': 100, 'trending': True},
            '藤井聡太': {'current_score': 85, 'peak_score': 90, 'trending': True},
            '羽生結弦': {'current_score': 80, 'peak_score': 95, 'trending': False},
            'HIKAKIN': {'current_score': 75, 'peak_score': 85, 'trending': False},
            '新垣結衣': {'current_score': 70, 'peak_score': 85, 'trending': False},
        }

        if name in famous_people:
            trend_data.update(famous_people[name])
            trend_data['average_score'] = (
                trend_data['current_score'] + trend_data['peak_score']) / 2

        # キャッシュ保存
        self.cache.set('trends', {'name': name}, trend_data)

        return trend_data


class FactDatabase:
    """事実データベース（ローカル）"""

    def __init__(self, db_path: str = "verified_facts_database_103persons.json"):
        self.db_path = db_path
        self.data = self._load_database()

    def _load_database(self) -> Dict:
        """データベースを読み込み"""
        if Path(self.db_path).exists():
            with open(self.db_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def get_person_facts(self, name: str) -> Optional[Dict]:
        """人物の事実情報を取得"""
        return self.data.get(name)

    def get_milestones(self, name: str) -> List[MilestoneInfo]:
        """人物の節目情報を取得"""
        person_data = self.data.get(name, {})
        milestones = []

        if 'milestones' in person_data:
            for milestone in person_data['milestones']:
                milestones.append(MilestoneInfo(
                    age=milestone.get('age', 0),
                    event=milestone.get('event', ''),
                    year=milestone.get('year', 0),
                    importance_score=milestone.get('importance', 5.0),
                    is_debut=any(keyword in milestone.get('event', '')
                               for keyword in ['デビュー', '開始', '初']),
                    is_achievement=any(keyword in milestone.get('event', '')
                                     for keyword in ['受賞', '達成', '優勝']),
                    source=milestone.get('source', 'local_db')
                ))

        return milestones

    def verify_age_milestone(self, name: str, age: int, event: str) -> bool:
        """年齢と節目の妥当性を確認"""
        milestones = self.get_milestones(name)

        for milestone in milestones:
            if milestone.age == age:
                # イベントの類似性チェック
                if any(keyword in event for keyword in event.split() if keyword in milestone.event):
                    return True

        return False


class QualityGateAPI:
    """Quality Gate API統合メインクラス"""

    def __init__(self):
        self.cache = CacheManager()
        self.wikipedia = WikipediaAPI(self.cache)
        self.trends = GoogleTrendsAPI(self.cache)
        self.fact_db = FactDatabase()

    async def validate_person(self, name: str) -> Dict[str, Any]:
        """
        人物の完全検証

        Args:
            name: 人物名

        Returns:
            検証結果の辞書
        """
        results = {}

        # 並列で各種APIを呼び出し
        wiki_task = self.wikipedia.check_person_existence(name)
        trend_task = self.trends.get_popularity_trend(name)

        wiki_info, trend_info = await asyncio.gather(wiki_task, trend_task)

        # ローカルデータベースから事実情報を取得
        local_facts = self.fact_db.get_person_facts(name)

        # 結果を統合
        results['exists'] = wiki_info.exists or local_facts is not None
        results['wikipedia'] = wiki_info.__dict__
        results['trends'] = trend_info
        results['local_facts'] = local_facts
        results['confidence_score'] = self._calculate_confidence(
            wiki_info, trend_info, local_facts
        )

        return results

    async def validate_milestone(self, name: str, age: int, event: str) -> Dict[str, Any]:
        """
        節目の妥当性を検証

        Args:
            name: 人物名
            age: 年齢
            event: イベント内容

        Returns:
            検証結果
        """
        # データベースから節目情報を取得
        milestones = self.fact_db.get_milestones(name)

        if not milestones:
            return {
                'valid': False,
                'reason': '節目情報が見つかりません',
                'suggestion': 'データベースを確認してください'
            }

        # 最適な節目を選択
        best_milestone = None
        best_score = 0

        for milestone in milestones:
            score = milestone.importance_score
            if milestone.is_debut:
                score += 3.0
            if milestone.is_achievement:
                score += 2.0

            if score > best_score:
                best_score = score
                best_milestone = milestone

        # 提供された節目との比較
        is_optimal = (best_milestone and
                     best_milestone.age == age and
                     any(keyword in event for keyword in best_milestone.event.split()))

        return {
            'valid': is_optimal,
            'best_milestone': best_milestone.__dict__ if best_milestone else None,
            'provided_age': age,
            'provided_event': event,
            'score': best_score,
            'suggestion': (
                f"より重要な節目: {best_milestone.age}歳 - {best_milestone.event}"
                if best_milestone and not is_optimal else None
            )
        }

    def _calculate_confidence(self, wiki_info: PersonInfo,
                            trend_info: Dict, local_facts: Optional[Dict]) -> float:
        """信頼度スコアを計算"""
        score = 0.0

        # Wikipediaに存在
        if wiki_info.exists:
            score += 4.0

        # Google Trendsで人気
        if trend_info.get('average_score', 0) > 50:
            score += 3.0

        # ローカルデータベースに存在
        if local_facts:
            score += 3.0

        return min(10.0, score)

    async def batch_validate(self, episodes: List[Dict]) -> List[Dict]:
        """
        複数エピソードを並列検証

        Args:
            episodes: エピソードリスト

        Returns:
            検証結果リスト
        """
        tasks = []
        for episode in episodes:
            person_task = self.validate_person(episode['person_name'])
            milestone_task = self.validate_milestone(
                episode['person_name'],
                episode['episode_age'],
                episode['episode_content']
            )
            tasks.append(asyncio.gather(person_task, milestone_task))

        results = await asyncio.gather(*tasks)

        validation_results = []
        for i, (person_result, milestone_result) in enumerate(results):
            validation_results.append({
                'episode': episodes[i],
                'person_validation': person_result,
                'milestone_validation': milestone_result,
                'overall_valid': (
                    person_result['exists'] and
                    milestone_result['valid']
                )
            })

        return validation_results


async def test_api():
    """APIテスト"""
    api = QualityGateAPI()

    # 人物検証テスト
    print("人物検証テスト:")
    result = await api.validate_person("大谷翔平")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # 節目検証テスト
    print("\n節目検証テスト:")
    milestone_result = await api.validate_milestone(
        "大谷翔平", 23, "メジャーリーグデビュー"
    )
    print(json.dumps(milestone_result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(test_api())