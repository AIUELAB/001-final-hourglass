#!/usr/bin/env python3
"""
マルチソースエピソード収集システム

複数のデータソース（Wikipedia、Wikidata、Brave Search、公式ページ）から
高品質なエピソードデータを収集する統合システム

Author: Claude
Date: 2025-09-18
Version: 1.0.0
"""

import json
import logging
import os
import re
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import hashlib
import requests
from dataclasses import dataclass, asdict
from enum import Enum

# ローカルインポート
try:
    from pdca_guardian import PDCAGuardian
except ImportError:
    PDCAGuardian = None

# API設定
WIKIPEDIA_API = "https://ja.wikipedia.org/w/api.php"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
BRAVE_API = "https://api.search.brave.com/res/v1/web/search"

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DataSource(Enum):
    """データソースの定義"""
    WIKIPEDIA = "wikipedia"
    WIKIDATA = "wikidata"
    BRAVE_SEARCH = "brave_search"
    OFFICIAL_PAGE = "official_page"
    NEWS = "news"
    BIOGRAPHY = "biography"

@dataclass
class EpisodeCandidate:
    """エピソード候補データ"""
    age: int
    year: Optional[int]
    month: Optional[int]
    day: Optional[int]
    content: str
    source: DataSource
    source_url: str
    quality_score: float
    impact_score: float
    specificity_score: float
    emotional_score: float
    keywords: List[str]
    raw_data: Dict[str, Any]

class MultiSourceEpisodeCollector:
    """マルチソースエピソード収集クラス"""

    def __init__(self, config_path: str = "config/api_config.json"):
        """
        初期化

        Args:
            config_path: API設定ファイルのパス
        """
        self.config = self._load_config(config_path)
        self.cache = {}
        self.rate_limiter = RateLimiter()
        self.pdca_guardian = PDCAGuardian() if PDCAGuardian else None

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """設定ファイルの読み込み"""
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)

        # デフォルト設定
        return {
            "brave_api_key": os.environ.get("BRAVE_API_KEY", ""),
            "max_retries": 3,
            "timeout": 30,
            "cache_expiry": 3600,
            "episode_limit_per_person": 10,
            "quality_threshold": 7.0
        }

    def collect_episodes(self, person_data: Dict[str, Any]) -> List[EpisodeCandidate]:
        """
        人物のエピソードデータを収集

        Args:
            person_data: 人物データ（person_name_ja, birth_year等を含む）

        Returns:
            エピソード候補のリスト
        """
        episodes = []
        person_name = person_data.get('person_name_ja', '')
        birth_year = person_data.get('birth_year')

        logger.info(f"エピソード収集開始: {person_name}")

        # 各データソースから収集
        sources = [
            (self._collect_from_wikipedia, DataSource.WIKIPEDIA),
            (self._collect_from_wikidata, DataSource.WIKIDATA),
            (self._collect_from_brave_search, DataSource.BRAVE_SEARCH),
            (self._collect_from_news, DataSource.NEWS)
        ]

        for collect_func, source in sources:
            try:
                source_episodes = collect_func(person_data)
                logger.info(f"{source.value}から{len(source_episodes)}件のエピソード候補を取得")
                episodes.extend(source_episodes)
            except Exception as e:
                logger.error(f"{source.value}からのデータ収集エラー: {e}")

        # 重複削除と品質評価
        episodes = self._deduplicate_episodes(episodes)
        episodes = self._evaluate_episode_quality(episodes, person_data)

        # 品質スコアで並び替え
        episodes.sort(key=lambda x: x.quality_score, reverse=True)

        # 上位エピソードのみ返す
        limit = self.config.get('episode_limit_per_person', 10)
        return episodes[:limit]

    def _collect_from_wikipedia(self, person_data: Dict[str, Any]) -> List[EpisodeCandidate]:
        """Wikipediaからエピソード収集"""
        episodes = []
        person_name = person_data.get('person_name_ja', '')

        if not person_name:
            return episodes

        # Wikipedia API呼び出し
        params = {
            'action': 'query',
            'format': 'json',
            'prop': 'revisions|pageprops',
            'titles': person_name,
            'rvprop': 'content',
            'rvslots': 'main'
        }

        try:
            response = requests.get(WIKIPEDIA_API, params=params, timeout=10)
            data = response.json()

            pages = data.get('query', {}).get('pages', {})
            for page_id, page_data in pages.items():
                if page_id != '-1':  # ページが存在する場合
                    content = self._extract_wikipedia_content(page_data)
                    episodes.extend(self._parse_wikipedia_episodes(content, person_data))
        except Exception as e:
            logger.error(f"Wikipedia API エラー: {e}")

        return episodes

    def _extract_wikipedia_content(self, page_data: Dict) -> str:
        """Wikipediaページからコンテンツを抽出"""
        try:
            revisions = page_data.get('revisions', [])
            if revisions:
                slots = revisions[0].get('slots', {})
                main_slot = slots.get('main', {})
                return main_slot.get('*', '')
        except Exception:
            pass
        return ''

    def _parse_wikipedia_episodes(self, content: str, person_data: Dict[str, Any]) -> List[EpisodeCandidate]:
        """Wikipediaコンテンツからエピソード解析"""
        episodes = []
        birth_year = person_data.get('birth_year')

        if not content or not birth_year:
            return episodes

        # 年表セクションを探す
        sections = re.split(r'\n=+\s*(.+?)\s*=+\n', content)

        for i, section in enumerate(sections):
            if '年表' in section or '経歴' in section or '生涯' in section:
                if i + 1 < len(sections):
                    timeline_text = sections[i + 1]
                    episodes.extend(self._extract_timeline_episodes(timeline_text, person_data))

        return episodes

    def _extract_timeline_episodes(self, text: str, person_data: Dict[str, Any]) -> List[EpisodeCandidate]:
        """年表テキストからエピソード抽出"""
        episodes = []
        birth_year = person_data.get('birth_year')

        # 年と出来事のパターン
        year_pattern = r'(\d{4})年.*?[:：]?\s*(.+?)(?=\d{4}年|$)'
        matches = re.findall(year_pattern, text, re.MULTILINE | re.DOTALL)

        for year_str, event_text in matches:
            try:
                year = int(year_str)
                age = year - birth_year

                if 0 <= age <= 100:  # 妥当な年齢範囲
                    episode = EpisodeCandidate(
                        age=age,
                        year=year,
                        month=None,
                        day=None,
                        content=self._clean_text(event_text),
                        source=DataSource.WIKIPEDIA,
                        source_url=f"https://ja.wikipedia.org/wiki/{person_data.get('person_name_ja', '')}",
                        quality_score=0.0,
                        impact_score=0.0,
                        specificity_score=0.0,
                        emotional_score=0.0,
                        keywords=self._extract_keywords(event_text),
                        raw_data={'year': year, 'text': event_text}
                    )
                    episodes.append(episode)
            except ValueError:
                continue

        return episodes

    def _collect_from_brave_search(self, person_data: Dict[str, Any]) -> List[EpisodeCandidate]:
        """Brave Searchからエピソード収集"""
        episodes = []
        person_name = person_data.get('person_name_ja', '')
        api_key = self.config.get('brave_api_key', '')

        if not person_name or not api_key:
            return episodes

        # 検索クエリのバリエーション
        queries = [
            f'"{person_name}" エピソード 偉業',
            f'"{person_name}" 転機 きっかけ',
            f'"{person_name}" 挫折 克服',
            f'"{person_name}" 記録 達成'
        ]

        headers = {
            'Accept': 'application/json',
            'X-Subscription-Token': api_key
        }

        for query in queries:
            try:
                params = {
                    'q': query,
                    'count': 10,
                    'mkt': 'ja-JP'
                }

                response = requests.get(BRAVE_API, params=params, headers=headers, timeout=10)

                if response.status_code == 200:
                    data = response.json()
                    results = data.get('web', {}).get('results', [])

                    for result in results:
                        episode = self._parse_brave_result(result, person_data)
                        if episode:
                            episodes.append(episode)

            except Exception as e:
                logger.error(f"Brave Search API エラー: {e}")

        return episodes

    def _parse_brave_result(self, result: Dict, person_data: Dict[str, Any]) -> Optional[EpisodeCandidate]:
        """Brave Search結果をパース"""
        try:
            description = result.get('description', '')
            title = result.get('title', '')
            url = result.get('url', '')

            # 年齢関連の情報を抽出
            age_match = re.search(r'(\d+)歳', description + title)
            if age_match:
                age = int(age_match.group(1))

                return EpisodeCandidate(
                    age=age,
                    year=None,
                    month=None,
                    day=None,
                    content=self._clean_text(description),
                    source=DataSource.BRAVE_SEARCH,
                    source_url=url,
                    quality_score=0.0,
                    impact_score=0.0,
                    specificity_score=0.0,
                    emotional_score=0.0,
                    keywords=self._extract_keywords(description),
                    raw_data={'title': title, 'description': description}
                )
        except Exception:
            pass

        return None

    def _collect_from_wikidata(self, person_data: Dict[str, Any]) -> List[EpisodeCandidate]:
        """Wikidataからエピソード収集"""
        episodes = []
        # Wikidata SPARQL クエリで重要な出来事を取得
        # 実装は省略（API制限を考慮）
        return episodes

    def _collect_from_news(self, person_data: Dict[str, Any]) -> List[EpisodeCandidate]:
        """ニュースソースからエピソード収集"""
        episodes = []
        # ニュースAPIからの収集
        # 実装は省略（API制限を考慮）
        return episodes

    def _deduplicate_episodes(self, episodes: List[EpisodeCandidate]) -> List[EpisodeCandidate]:
        """エピソードの重複削除"""
        seen = set()
        unique_episodes = []

        for episode in episodes:
            # コンテンツのハッシュで重複チェック
            content_hash = hashlib.md5(
                f"{episode.age}{episode.content[:100]}".encode()
            ).hexdigest()

            if content_hash not in seen:
                seen.add(content_hash)
                unique_episodes.append(episode)

        return unique_episodes

    def _evaluate_episode_quality(self, episodes: List[EpisodeCandidate],
                                 person_data: Dict[str, Any]) -> List[EpisodeCandidate]:
        """エピソードの品質評価"""
        for episode in episodes:
            # 具体性スコア
            episode.specificity_score = self._calculate_specificity_score(episode.content)

            # インパクトスコア
            episode.impact_score = self._calculate_impact_score(episode.content)

            # 感情スコア
            episode.emotional_score = self._calculate_emotional_score(episode.content)

            # 総合品質スコア
            episode.quality_score = (
                episode.specificity_score * 0.3 +
                episode.impact_score * 0.4 +
                episode.emotional_score * 0.3
            )

            # PDCAガーディアンでの検証（利用可能な場合）
            if self.pdca_guardian:
                episode_text = f"あなたと同じ{episode.age}歳のとき、{person_data.get('person_name_ja', '')}は{episode.content}"
                violations = self.pdca_guardian.check_episode_quality(episode_text, person_data)

                # 違反がある場合はスコア減点
                if violations:
                    episode.quality_score *= 0.7

        return episodes

    def _calculate_specificity_score(self, text: str) -> float:
        """具体性スコア計算"""
        score = 0.0

        # 作品名（「」『』で囲まれた名称）
        if re.search(r'「[^」]+」|『[^』]+』', text):
            score += 3.0

        # 数値データ
        if re.search(r'\d+', text):
            score += 2.0

        # 固有名詞（カタカナ、英字）
        if re.search(r'[ァ-ヴー]{3,}|[A-Z][a-z]+', text):
            score += 1.0

        # 具体的なキーワード
        concrete_keywords = ['記録', '優勝', '受賞', '発表', '設立', '結婚', '誕生']
        for keyword in concrete_keywords:
            if keyword in text:
                score += 0.5

        return min(score, 10.0)

    def _calculate_impact_score(self, text: str) -> float:
        """インパクトスコア計算"""
        score = 0.0

        # インパクトキーワードのカテゴリ
        impact_keywords = {
            'achievement': ['優勝', '受賞', 'MVP', '金メダル', '新記録', '世界一', '日本一', '史上初'],
            'challenge': ['困難', '逆境', '苦労', '努力', '克服', '乗り越え', '復活', '再起'],
            'emotion': ['感動', '涙', '感謝', '喜び', '希望', '勇気', '決意', '覚悟'],
            'milestone': ['デビュー', '転機', '独立', '結婚', '誕生', '引退', '卒業'],
            'historical': ['初', '史上', '革命', '歴史的', '画期的', '伝説', '前人未到']
        }

        for category, keywords in impact_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    score += 2.0
                    break

        return min(score, 10.0)

    def _calculate_emotional_score(self, text: str) -> float:
        """感情スコア計算"""
        score = 0.0

        # 感情を呼び起こすキーワード
        emotional_keywords = {
            'positive': ['成功', '達成', '実現', '夢', '希望', '喜び', '感謝', '幸せ'],
            'struggle': ['挫折', '失敗', '苦悩', '葛藤', '試練', '困難', '逆境'],
            'growth': ['成長', '進化', '変化', '覚醒', '開花', '飛躍', '突破'],
            'relationship': ['出会い', '別れ', '仲間', '師匠', '家族', '愛', '友情']
        }

        for category, keywords in emotional_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    score += 1.5

        return min(score, 10.0)

    def _extract_keywords(self, text: str) -> List[str]:
        """テキストからキーワード抽出"""
        keywords = []

        # 作品名
        keywords.extend(re.findall(r'「([^」]+)」|『([^』]+)』', text))

        # 重要そうな名詞（簡易的な実装）
        important_patterns = [
            r'[ァ-ヴー]{4,}',  # カタカナ4文字以上
            r'[一-龠]{2,}賞',   # ○○賞
            r'[一-龠]{2,}大会',  # ○○大会
        ]

        for pattern in important_patterns:
            keywords.extend(re.findall(pattern, text))

        # フラット化して重複削除
        flat_keywords = []
        for k in keywords:
            if isinstance(k, tuple):
                flat_keywords.extend([item for item in k if item])
            else:
                flat_keywords.append(k)

        return list(set(flat_keywords))[:10]  # 最大10個

    def _clean_text(self, text: str) -> str:
        """テキストのクリーニング"""
        # 改行やタブを削除
        text = re.sub(r'[\n\r\t]+', ' ', text)

        # 連続する空白を1つに
        text = re.sub(r'\s+', ' ', text)

        # Wikipediaの参照記号を削除
        text = re.sub(r'\[\d+\]', '', text)
        text = re.sub(r'\[要出典\]', '', text)

        return text.strip()

    def export_episodes(self, episodes: List[EpisodeCandidate], output_path: str):
        """エピソードをJSON形式でエクスポート"""
        export_data = []

        for episode in episodes:
            export_data.append({
                'age': episode.age,
                'year': episode.year,
                'month': episode.month,
                'day': episode.day,
                'content': episode.content,
                'source': episode.source.value,
                'source_url': episode.source_url,
                'quality_score': episode.quality_score,
                'impact_score': episode.impact_score,
                'specificity_score': episode.specificity_score,
                'emotional_score': episode.emotional_score,
                'keywords': episode.keywords
            })

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

        logger.info(f"エピソードを{output_path}にエクスポートしました")

class RateLimiter:
    """APIレート制限管理"""

    def __init__(self):
        self.last_call = {}
        self.min_interval = 1.0  # 最小間隔（秒）

    def wait_if_needed(self, api_name: str):
        """必要に応じて待機"""
        current_time = time.time()

        if api_name in self.last_call:
            elapsed = current_time - self.last_call[api_name]
            if elapsed < self.min_interval:
                time.sleep(self.min_interval - elapsed)

        self.last_call[api_name] = time.time()


def main():
    """メイン処理"""
    collector = MultiSourceEpisodeCollector()

    # テスト用の人物データ
    test_person = {
        'person_name_ja': '坂本龍馬',
        'birth_year': 1836,
        'person_id': 'P000001'
    }

    # エピソード収集
    episodes = collector.collect_episodes(test_person)

    # 結果表示
    print(f"\n収集されたエピソード数: {len(episodes)}")
    for i, episode in enumerate(episodes[:3], 1):
        print(f"\n--- エピソード {i} ---")
        print(f"年齢: {episode.age}歳")
        print(f"内容: {episode.content[:100]}...")
        print(f"品質スコア: {episode.quality_score:.2f}")
        print(f"ソース: {episode.source.value}")

    # エクスポート
    collector.export_episodes(episodes, "collected_episodes.json")


if __name__ == "__main__":
    main()
