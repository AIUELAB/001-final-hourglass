#!/usr/bin/env python3
"""
Wikipedia API実装
実際のWikipedia APIを使用した存在確認機能
キャッシュ機構付きで効率的な検証を実現
"""

import requests
import json
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Tuple
from datetime import datetime, timedelta
import hashlib

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WikipediaValidator:
    """Wikipedia存在確認バリデーター"""

    def __init__(self, cache_file: str = "wikipedia_cache.json"):
        """初期化"""
        self.cache_file = Path(cache_file)
        self.cache = self._load_cache()
        self.api_calls = 0
        self.cache_hits = 0

        # Wikipedia API endpoints
        self.ja_endpoint = "https://ja.wikipedia.org/w/api.php"
        self.en_endpoint = "https://en.wikipedia.org/w/api.php"

    def _load_cache(self) -> Dict:
        """キャッシュ読み込み"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_cache(self):
        """キャッシュ保存"""
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)

    def _get_cache_key(self, name: str, occupation: str = None) -> str:
        """キャッシュキー生成"""
        key_str = f"{name}|{occupation or ''}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def _search_wikipedia(self, endpoint: str, query: str, limit: int = 5) -> bool:
        """Wikipedia検索API呼び出し"""
        params = {
            'action': 'query',
            'format': 'json',
            'list': 'search',
            'srsearch': query,
            'srlimit': limit,
            'utf8': 1
        }

        try:
            response = requests.get(endpoint, params=params, timeout=5)
            response.raise_for_status()

            data = response.json()
            search_results = data.get('query', {}).get('search', [])

            # 結果があれば存在すると判定
            return len(search_results) > 0

        except requests.exceptions.RequestException as e:
            logger.warning(f"Wikipedia API error: {e}")
            return False
        except Exception as e:
            logger.warning(f"Unexpected error: {e}")
            return False

    def check_existence(self, person_name: str, occupation: str = None,
                       nationality: str = None) -> Tuple[bool, str]:
        """
        Wikipedia存在確認

        Args:
            person_name: 人物名
            occupation: 職業（オプション）
            nationality: 国籍（オプション）

        Returns:
            (存在フラグ, 検証方法)
        """
        # キャッシュチェック
        cache_key = self._get_cache_key(person_name, occupation)

        if cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            # キャッシュ有効期限（7日間）
            cached_time = datetime.fromisoformat(cache_entry['timestamp'])
            if datetime.now() - cached_time < timedelta(days=7):
                self.cache_hits += 1
                return cache_entry['exists'], "cache"

        # API呼び出し
        self.api_calls += 1

        # まず複合検索（名前 + 職業）
        if occupation:
            query = f"{person_name} {occupation}"
            if self._search_wikipedia(self.ja_endpoint, query, 3):
                self._update_cache(cache_key, True)
                return True, "ja_wiki_compound"

        # 名前のみで検索（日本語）
        if self._search_wikipedia(self.ja_endpoint, person_name, 5):
            self._update_cache(cache_key, True)
            return True, "ja_wiki_name"

        # 英語版も確認（国際的な人物の可能性）
        if self._search_wikipedia(self.en_endpoint, person_name, 3):
            self._update_cache(cache_key, True)
            return True, "en_wiki"

        # 見つからない場合
        self._update_cache(cache_key, False)
        return False, "not_found"

    def _update_cache(self, cache_key: str, exists: bool):
        """キャッシュ更新"""
        self.cache[cache_key] = {
            'exists': exists,
            'timestamp': datetime.now().isoformat()
        }

        # 定期的に保存（100件ごと）
        if len(self.cache) % 100 == 0:
            self._save_cache()

    def get_stats(self) -> Dict:
        """統計情報取得"""
        return {
            'api_calls': self.api_calls,
            'cache_hits': self.cache_hits,
            'cache_size': len(self.cache),
            'hit_rate': self.cache_hits / (self.api_calls + self.cache_hits)
                        if (self.api_calls + self.cache_hits) > 0 else 0
        }

    def validate_batch(self, persons: list) -> Dict[str, bool]:
        """
        バッチ検証

        Args:
            persons: [{'name': str, 'occupation': str}] のリスト

        Returns:
            {person_name: exists} の辞書
        """
        results = {}

        for person in persons:
            name = person.get('name', '')
            occupation = person.get('occupation', '')

            # レート制限対策（0.5秒待機）
            if self.api_calls > 0 and self.api_calls % 10 == 0:
                time.sleep(0.5)

            exists, method = self.check_existence(name, occupation)
            results[name] = exists

            if exists:
                logger.info(f"✅ {name} ({occupation}) - Wikipedia確認済み [{method}]")
            else:
                logger.debug(f"❌ {name} ({occupation}) - Wikipedia未確認")

        # 最後にキャッシュ保存
        self._save_cache()

        return results


def test_validator():
    """バリデーターのテスト"""
    validator = WikipediaValidator()

    # テストケース
    test_cases = [
        {'name': '張本勲', 'occupation': '野球選手'},
        {'name': '張本智和', 'occupation': '卓球選手'},
        {'name': '為末大', 'occupation': '陸上選手'},
        {'name': '照ノ富士', 'occupation': '大相撲力士'},
        {'name': '錦織圭', 'occupation': 'テニス選手'},
        {'name': '鎌田大地', 'occupation': 'サッカー選手'},
        {'name': 'リーチ三郎', 'occupation': 'ラグビー選手'},  # 架空
        {'name': '高橋次郎', 'occupation': '野球選手'},  # 架空の可能性大
    ]

    logger.info("=" * 60)
    logger.info("Wikipedia存在確認テスト")
    logger.info("=" * 60)

    results = validator.validate_batch(test_cases)

    # 結果表示
    logger.info("\n📊 テスト結果:")
    for case in test_cases:
        name = case['name']
        exists = results[name]
        status = "✅ 存在" if exists else "❌ 未確認"
        logger.info(f"  {name}: {status}")

    # 統計表示
    stats = validator.get_stats()
    logger.info(f"\n📈 統計:")
    logger.info(f"  API呼び出し: {stats['api_calls']}回")
    logger.info(f"  キャッシュヒット: {stats['cache_hits']}回")
    logger.info(f"  キャッシュサイズ: {stats['cache_size']}件")
    logger.info(f"  ヒット率: {stats['hit_rate']:.1%}")


if __name__ == "__main__":
    test_validator()
