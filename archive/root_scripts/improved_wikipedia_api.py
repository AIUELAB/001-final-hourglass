#!/usr/bin/env python3
"""
改善版Wikipedia API実装
人物記事の正確な特定と表示名取得
"""

import requests
import json
import time
import logging
from typing import Optional, Dict, Tuple, List
from pathlib import Path
import hashlib
import re

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ImprovedWikipediaAPI:
    """改善版Wikipedia API - 人物記事を正確に特定"""

    def __init__(self):
        """初期化"""
        self.ja_endpoint = "https://ja.wikipedia.org/w/api.php"
        self.en_endpoint = "https://en.wikipedia.org/w/api.php"
        self.ko_endpoint = "https://ko.wikipedia.org/w/api.php"

        # キャッシュディレクトリ
        self.cache_dir = Path("wikipedia_cache_v2")
        self.cache_dir.mkdir(exist_ok=True)

        # セッション作成
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Ultra Think Database Validator/2.0)'
        })

        # レート制限
        self.last_request_time = 0
        self.min_request_interval = 0.5

        # 人物判定用カテゴリパターン
        self.person_categories = {
            'ja': [
                '人物', '存命人物', '歌手', '俳優', '女優', 'タレント',
                'お笑い芸人', 'YouTuber', 'スポーツ選手', '政治家',
                '実業家', 'アイドル', 'ミュージシャン', '声優',
                '年生', '年没', '出身'
            ],
            'en': [
                'births', 'deaths', 'people', 'Living people',
                'singers', 'actors', 'actresses', 'musicians',
                'YouTubers', 'politicians', 'businesspeople'
            ]
        }

    def _rate_limit(self):
        """レート制限"""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()

    def _get_cache_key(self, query: str, lang: str, search_type: str = 'person') -> str:
        """キャッシュキー生成"""
        return hashlib.md5(f"{lang}:{search_type}:{query}".encode()).hexdigest()

    def _load_cache(self, cache_key: str) -> Optional[Dict]:
        """キャッシュ読み込み"""
        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            if time.time() - cache_file.stat().st_mtime < 86400:  # 24時間
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        return None

    def _save_cache(self, cache_key: str, data: Dict):
        """キャッシュ保存"""
        cache_file = self.cache_dir / f"{cache_key}.json"
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _is_person_page(self, page_data: Dict, lang: str = 'ja') -> bool:
        """
        ページが人物記事かどうか判定

        Args:
            page_data: ページデータ
            lang: 言語コード

        Returns:
            人物記事ならTrue
        """
        # カテゴリチェック
        categories = page_data.get('categories', [])
        category_titles = [cat.get('title', '') for cat in categories]

        # 人物カテゴリパターンとマッチング
        person_patterns = self.person_categories.get(lang, self.person_categories['ja'])
        for pattern in person_patterns:
            for cat_title in category_titles:
                if pattern in cat_title:
                    return True

        # Infoboxチェック（人物系テンプレート）
        if 'revisions' in page_data:
            content = page_data['revisions'][0].get('*', '')
            person_infoboxes = [
                'Infobox 人物', 'Infobox 芸人', 'Infobox 歌手',
                'Infobox 俳優', 'Infobox サッカー選手', 'Infobox 野球選手',
                'Infobox person', 'Infobox musical artist', 'Infobox actor'
            ]
            for infobox in person_infoboxes:
                if infobox.lower() in content.lower():
                    return True

        return False

    def search_person_wikipedia(self, person_name: str, lang: str = 'ja',
                               occupation: str = None) -> Optional[Dict]:
        """
        人物に特化したWikipedia検索

        Args:
            person_name: 人物名
            lang: 言語コード
            occupation: 職業（検索精度向上用）

        Returns:
            人物記事の情報（見つからない場合None）
        """
        # キャッシュチェック
        cache_key = self._get_cache_key(person_name, lang, 'person')
        cached = self._load_cache(cache_key)
        if cached:
            logger.info(f"📦 キャッシュヒット: {person_name} ({lang})")
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
            # 検索クエリの構築（職業情報を追加して精度向上）
            search_query = person_name
            if occupation and lang == 'ja':
                # 職業キーワードを追加（ただし汎用的すぎるものは除外）
                if occupation not in ['その他', '一般人', '不明']:
                    search_query = f"{person_name} {occupation}"

            # Step 1: タイトル検索（完全一致優先）
            title_params = {
                'action': 'query',
                'format': 'json',
                'titles': person_name,
                'prop': 'info|categories|revisions',
                'inprop': 'url|displaytitle',
                'cllimit': 50,
                'rvprop': 'content',
                'rvslots': 'main',
                'rvsection': 0  # 導入部のみ
            }

            response = self.session.get(endpoint, params=title_params, timeout=10)
            response.raise_for_status()
            data = response.json()

            pages = data.get('query', {}).get('pages', {})
            for page_id, page_data in pages.items():
                if page_id != '-1' and self._is_person_page(page_data, lang):
                    # 人物記事が見つかった
                    result = self._extract_page_info(page_data, lang)
                    self._save_cache(cache_key, result)
                    logger.info(f"✅ 人物記事取得（完全一致）: {result['display_title']} ({lang})")
                    return result

            # Step 2: 検索API（完全一致が見つからない場合）
            search_params = {
                'action': 'query',
                'format': 'json',
                'list': 'search',
                'srsearch': search_query,
                'srlimit': 10,  # より多くの候補を確認
                'srprop': 'snippet|titlesnippet'
            }

            response = self.session.get(endpoint, params=search_params, timeout=10)
            response.raise_for_status()

            search_data = response.json()
            search_results = search_data.get('query', {}).get('search', [])

            # 検索結果から人物記事を探す
            for result in search_results:
                page_title = result['title']

                # 明らかに違うものを除外
                exclude_patterns = [
                    '空港', '駅', '市', '町', '村', '県', '国',
                    'ブロックチェーン', '製品', '会社', '企業',
                    '作品', '曲', 'アルバム', '映画', 'ドラマ'
                ]

                if any(pattern in page_title for pattern in exclude_patterns):
                    continue

                # ページ詳細取得して人物記事か確認
                page_params = {
                    'action': 'query',
                    'format': 'json',
                    'titles': page_title,
                    'prop': 'info|categories|pageimages|extracts',
                    'inprop': 'url|displaytitle',
                    'cllimit': 50,
                    'exintro': True,
                    'explaintext': True,
                    'exsentences': 3
                }

                response = self.session.get(endpoint, params=page_params, timeout=10)
                response.raise_for_status()

                page_data = response.json()
                pages = page_data.get('query', {}).get('pages', {})

                for page_id, page_info in pages.items():
                    if page_id != '-1' and self._is_person_page(page_info, lang):
                        # 人物記事確認
                        result = self._extract_page_info(page_info, lang)

                        # 名前の一致度を確認
                        if self._name_similarity_check(person_name, result['title']):
                            self._save_cache(cache_key, result)
                            logger.info(f"✅ 人物記事取得（検索）: {result['display_title']} ({lang})")
                            return result

            logger.info(f"❌ 人物記事が見つかりません: {person_name} ({lang})")
            return None

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Wikipedia API エラー: {e}")
        except Exception as e:
            logger.error(f"❌ 予期しないエラー: {e}")

        return None

    def _extract_page_info(self, page_data: Dict, lang: str) -> Dict:
        """ページ情報を抽出"""
        return {
            'title': page_data.get('title'),
            'display_title': page_data.get('displaytitle', page_data.get('title')),
            'url': page_data.get('fullurl'),
            'extract': page_data.get('extract', ''),
            'categories': [cat.get('title', '') for cat in page_data.get('categories', [])],
            'lang': lang,
            'timestamp': time.time()
        }

    def _name_similarity_check(self, query_name: str, found_name: str) -> bool:
        """
        名前の類似性チェック

        Args:
            query_name: 検索した名前
            found_name: 見つかった記事の名前

        Returns:
            類似している場合True
        """
        # 正規化
        query_normalized = re.sub(r'[・\s　]+', '', query_name.lower())
        found_normalized = re.sub(r'[・\s　]+', '', found_name.lower())

        # 完全一致
        if query_normalized == found_normalized:
            return True

        # 部分一致（クエリが記事名に含まれる）
        if query_normalized in found_normalized:
            # ただし、明らかに違う場合は除外
            # 例: "木村" が "木村カエラ" にマッチしないように
            name_parts = query_name.split()
            if len(name_parts) >= 2:  # フルネームの場合
                # 姓名が両方含まれているか確認
                return all(part in found_name for part in name_parts)
            return True

        # 記事名がクエリに含まれる（愛称や略称の場合）
        if found_normalized in query_normalized:
            return True

        return False

    def get_display_name(self, person_name: str, occupation: str = None) -> Tuple[str, str]:
        """
        Google検索トップ準拠の表示名取得（改善版）

        Args:
            person_name: 人物名
            occupation: 職業

        Returns:
            (表示名, 取得元) のタプル
        """
        # 特殊ケース処理（変更なし）
        special_cases = {
            'PSY': ('PSY', 'known_format'),
            'MrBeast': ('MrBeast', 'known_format'),
            'HIKAKIN': ('HIKAKIN', 'known_format'),
            'IKKO': ('IKKO', 'known_format'),
            'GACKT': ('GACKT', 'known_format'),
            'hyde': ('hyde', 'known_format'),
            'Ado': ('Ado', 'known_format'),
            'YOSHIKI': ('YOSHIKI', 'known_format'),
            'Toshl': ('Toshl', 'known_format')
        }

        if person_name in special_cases:
            return special_cases[person_name]

        # 芸名リスト（ひらがな表記が正しい）
        valid_stage_names = {
            'あいみょん', 'きゃりーぱみゅぱみゅ', 'ふかわりょう',
            'よゐこ', 'おぎやはぎ', 'ゆりやんレトリィバァ',
            'かなで', 'しずちゃん', 'ゆめっち', 'みちお',
            'あやなん', 'あやののの', 'きまぐれクック'
        }

        if person_name in valid_stage_names:
            return (person_name, 'valid_stage_name')

        # 改善版Wikipedia検索（人物記事のみ）
        ja_result = self.search_person_wikipedia(person_name, 'ja', occupation)
        if ja_result:
            display_name = ja_result['display_title']

            # ひらがな表記チェック
            if self._is_hiragana_only(display_name):
                # 芸名でなく、元の名前が漢字なら漢字を使用
                if display_name not in valid_stage_names and self._has_kanji(person_name):
                    return (person_name, 'original_kanji')

            return (display_name, 'wikipedia_ja')

        # 英語圏の人物
        if self._is_foreign_name(person_name):
            en_result = self.search_person_wikipedia(person_name, 'en', occupation)
            if en_result:
                # 英語名はそのまま使用（カタカナ変換しない）
                if person_name.replace(' ', '').isalpha() and person_name.isascii():
                    return (person_name, 'original_english')
                return (en_result['display_title'], 'wikipedia_en')

        # K-POP関連
        if self._is_kpop_related(person_name, occupation):
            # 韓国系アーティストは元の表記を維持
            return (person_name, 'kpop_original')

        # デフォルト: 元の名前を使用
        return (person_name, 'default')

    def _is_hiragana_only(self, text: str) -> bool:
        """ひらがなのみかチェック"""
        import unicodedata
        for char in text:
            if char in ' 　（）':
                continue
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

    def _is_foreign_name(self, name: str) -> bool:
        """外国人名かどうか判定"""
        # アルファベットのみ
        if name.replace(' ', '').replace('.', '').replace('-', '').isalpha() and name.isascii():
            return True

        # カタカナのみ（外国人名の可能性）
        import unicodedata
        katakana_count = 0
        for char in name:
            if char in ' 　・':
                continue
            name_u = unicodedata.name(char, '')
            if 'KATAKANA' in name_u:
                katakana_count += 1

        if katakana_count > 0 and katakana_count == len(name.replace(' ', '').replace('　', '').replace('・', '')):
            return True

        return False

    def _is_kpop_related(self, name: str, occupation: str = None) -> bool:
        """K-POP関連かどうか判定"""
        kpop_keywords = [
            'BTS', 'BLACKPINK', 'SEVENTEEN', 'Stray Kids', 'ENHYPEN',
            'TXT', 'NCT', 'TWICE', 'ITZY', 'aespa', 'K-POP', 'K-pop'
        ]

        if occupation:
            for keyword in kpop_keywords:
                if keyword.lower() in occupation.lower():
                    return True

        # 名前にグループ名が含まれる
        for keyword in kpop_keywords:
            if keyword in name:
                return True

        return False


def test_improved_api():
    """改善版APIのテスト"""
    api = ImprovedWikipediaAPI()

    # 問題があったケースをテスト
    test_cases = [
        ('Nnamdi Azikiwe', '大統領'),  # 空港ではなく人物記事を取得すべき
        ('Charles Hoskinson', 'Cardano創設者'),  # ブロックチェーンではなく人物
        ('木村大翔', 'モデル'),  # 木村カエラではなく木村大翔
        ('PSY', '歌手'),  # PSYのまま
        ('染谷将太', '俳優'),  # 漢字表記
        ('岡田将生', '俳優'),  # 漢字表記
        ('MrBeast', 'YouTuber'),  # MrBeastのまま
        ('あいみょん', '歌手'),  # ひらがなのまま（芸名）
    ]

    logger.info("=" * 60)
    logger.info("改善版Wikipedia APIテスト")
    logger.info("=" * 60)

    for name, occupation in test_cases:
        display_name, source = api.get_display_name(name, occupation)
        logger.info(f"📝 {name} ({occupation}) → {display_name} [source: {source}]")
        time.sleep(0.5)  # レート制限


if __name__ == "__main__":
    test_improved_api()
