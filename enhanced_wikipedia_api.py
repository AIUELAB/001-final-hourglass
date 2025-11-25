#!/usr/bin/env python3
"""
強化版Wikipedia API実装
Google検索トップ結果に準拠した表示名取得
"""

import requests
import json
import time
import logging
from typing import Optional, Dict, Tuple
from pathlib import Path
import hashlib

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EnhancedWikipediaAPI:
    """強化版Wikipedia API"""

    def __init__(self):
        """初期化"""
        self.ja_endpoint = "https://ja.wikipedia.org/w/api.php"
        self.en_endpoint = "https://en.wikipedia.org/w/api.php"
        self.ko_endpoint = "https://ko.wikipedia.org/w/api.php"

        # キャッシュディレクトリ
        self.cache_dir = Path("wikipedia_cache")
        self.cache_dir.mkdir(exist_ok=True)

        # セッション作成（接続再利用）
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Ultra Think Database Validator/1.0)'
        })

        # レート制限
        self.last_request_time = 0
        self.min_request_interval = 0.5  # 500ms間隔

    def _rate_limit(self):
        """レート制限"""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()

    def _get_cache_key(self, query: str, lang: str) -> str:
        """キャッシュキー生成"""
        return hashlib.md5(f"{lang}:{query}".encode()).hexdigest()

    def _load_cache(self, cache_key: str) -> Optional[Dict]:
        """キャッシュ読み込み"""
        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            # キャッシュが24時間以内なら使用
            if time.time() - cache_file.stat().st_mtime < 86400:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        return None

    def _save_cache(self, cache_key: str, data: Dict):
        """キャッシュ保存"""
        cache_file = self.cache_dir / f"{cache_key}.json"
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def search_wikipedia(self, query: str, lang: str = 'ja') -> Optional[Dict]:
        """
        Wikipedia検索

        Args:
            query: 検索クエリ
            lang: 言語コード（ja/en/ko）

        Returns:
            検索結果の辞書
        """
        # キャッシュチェック
        cache_key = self._get_cache_key(query, lang)
        cached = self._load_cache(cache_key)
        if cached:
            logger.info(f"📦 キャッシュヒット: {query} ({lang})")
            return cached

        # エンドポイント選択
        endpoint = {
            'ja': self.ja_endpoint,
            'en': self.en_endpoint,
            'ko': self.ko_endpoint
        }.get(lang, self.ja_endpoint)

        # レート制限
        self._rate_limit()

        try:
            # 検索API呼び出し
            search_params = {
                'action': 'query',
                'format': 'json',
                'list': 'search',
                'srsearch': query,
                'srlimit': 5,
                'srprop': 'snippet|titlesnippet|size|wordcount|timestamp'
            }

            response = self.session.get(endpoint, params=search_params, timeout=10)
            response.raise_for_status()

            data = response.json()
            search_results = data.get('query', {}).get('search', [])

            if not search_results:
                logger.info(f"❌ 検索結果なし: {query} ({lang})")
                return None

            # 最初の結果からページ情報取得
            page_title = search_results[0]['title']

            # ページ詳細取得
            page_params = {
                'action': 'query',
                'format': 'json',
                'prop': 'info|extracts|pageimages',
                'titles': page_title,
                'inprop': 'url|displaytitle',
                'exintro': True,
                'explaintext': True,
                'exsentences': 3,
                'piprop': 'thumbnail',
                'pithumbsize': 200
            }

            response = self.session.get(endpoint, params=page_params, timeout=10)
            response.raise_for_status()

            page_data = response.json()
            pages = page_data.get('query', {}).get('pages', {})

            if pages:
                page_id = list(pages.keys())[0]
                page_info = pages[page_id]

                result = {
                    'title': page_info.get('title'),
                    'display_title': page_info.get('displaytitle', page_info.get('title')),
                    'url': page_info.get('fullurl'),
                    'extract': page_info.get('extract'),
                    'lang': lang,
                    'timestamp': time.time()
                }

                # キャッシュ保存
                self._save_cache(cache_key, result)

                logger.info(f"✅ Wikipedia取得成功: {result['display_title']} ({lang})")
                return result

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Wikipedia API エラー: {e}")

        except Exception as e:
            logger.error(f"❌ 予期しないエラー: {e}")

        return None

    def get_display_name(self, person_name: str, occupation: str = None) -> Tuple[str, str]:
        """
        Google検索トップ準拠の表示名取得

        Args:
            person_name: 人物名
            occupation: 職業（オプション）

        Returns:
            (表示名, 取得元) のタプル
        """
        # 特殊ケース処理
        special_cases = {
            'PSY': ('PSY', 'known_format'),
            'MrBeast': ('MrBeast', 'known_format'),
            'HIKAKIN': ('HIKAKIN', 'known_format'),
            'IKKO': ('IKKO', 'known_format'),
            'GACKT': ('GACKT', 'known_format'),
            'hyde': ('hyde', 'known_format'),
            'Ado': ('Ado', 'known_format')
        }

        if person_name in special_cases:
            return special_cases[person_name]

        # 日本語Wikipedia検索
        ja_result = self.search_wikipedia(person_name, 'ja')
        if ja_result:
            display_name = ja_result['display_title']

            # ひらがな表記チェック（芸名以外は漢字優先）
            if self._is_hiragana_only(display_name) and not self._is_stage_name(person_name, occupation):
                # 元の名前が漢字なら漢字を使用
                if self._has_kanji(person_name):
                    return (person_name, 'original_kanji')

            return (display_name, 'wikipedia_ja')

        # 英語Wikipedia検索（K-POP等）
        if self._is_kpop_or_foreign(person_name, occupation):
            en_result = self.search_wikipedia(person_name, 'en')
            if en_result:
                return (en_result['display_title'], 'wikipedia_en')

            # 韓国語Wikipedia検索
            ko_result = self.search_wikipedia(person_name, 'ko')
            if ko_result:
                # 韓国人の場合は英語表記を優先
                return (person_name, 'original_name')

        # デフォルト: 元の名前を使用
        return (person_name, 'default')

    def _is_hiragana_only(self, text: str) -> bool:
        """ひらがなのみかチェック"""
        import unicodedata
        for char in text:
            if char == ' ' or char == '　':
                continue
            category = unicodedata.category(char)
            name = unicodedata.name(char, '')
            if 'HIRAGANA' not in name:
                return False
        return True

    def _has_kanji(self, text: str) -> bool:
        """漢字を含むかチェック"""
        import unicodedata
        for char in text:
            name = unicodedata.name(char, '')
            if 'CJK UNIFIED IDEOGRAPH' in name:
                return True
        return False

    def _is_stage_name(self, name: str, occupation: str = None) -> bool:
        """芸名かどうか判定"""
        # 明らかな芸名パターン
        stage_name_patterns = [
            'あいみょん', 'きゃりーぱみゅぱみゅ', 'ふかわりょう',
            'おぎやはぎ', 'よゐこ', 'ゆりやんレトリィバァ'
        ]

        if name in stage_name_patterns:
            return True

        # 職業による判定
        if occupation and 'お笑い' in occupation:
            # お笑い芸人の単名は芸名の可能性高い
            if len(name) <= 5 and not self._has_kanji(name):
                return True

        return False

    def _is_kpop_or_foreign(self, name: str, occupation: str = None) -> bool:
        """K-POPまたは外国人判定"""
        # K-POPグループメンバーパターン
        kpop_patterns = ['BTS', 'SEVENTEEN', 'Stray Kids', 'ENHYPEN', 'TXT', 'NCT']

        if occupation:
            for pattern in kpop_patterns:
                if pattern in occupation:
                    return True

        # 英語名パターン
        if name.replace(' ', '').isalpha() and name.isascii():
            return True

        return False


def test_api():
    """APIテスト"""
    api = EnhancedWikipediaAPI()

    test_cases = [
        ('PSY', '歌手'),
        ('染谷将太', '俳優'),
        ('岡田将生', '俳優'),
        ('MrBeast', 'YouTuber'),
        ('いかりや長介', 'コメディアン'),
        ('三浦知良', 'サッカー選手')
    ]

    for name, occupation in test_cases:
        display_name, source = api.get_display_name(name, occupation)
        logger.info(f"📝 {name} → {display_name} (source: {source})")


if __name__ == "__main__":
    test_api()
