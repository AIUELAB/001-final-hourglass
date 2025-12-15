#!/usr/bin/env python3
"""
強化版Wikipedia誕生年取得システム
確定情報のみを高速・確実に収集
"""

import pandas as pd
import requests
import time
import re
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Tuple
import hashlib

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('wikipedia_birth_collection.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class WikipediaBirthCollector:
    """Wikipedia APIから誕生年を確実に取得"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'UltraThinkHourglass/1.0 (Birth Year Collection) Python/3.11'
        })
        self.cache_file = "wikipedia_birth_cache.json"
        self.cache = self.load_cache()
        self.stats = {
            'api_calls': 0,
            'found': 0,
            'not_found': 0,
            'errors': 0,
            'cache_hits': 0
        }

    def load_cache(self) -> Dict:
        """キャッシュをロード"""
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_cache(self):
        """キャッシュを保存"""
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)

    def get_cache_key(self, name: str) -> str:
        """キャッシュキーを生成"""
        return hashlib.md5(name.encode()).hexdigest()

    def extract_birth_from_infobox(self, wikitext: str) -> Tuple[Optional[str], Optional[int]]:
        """Wikitextから誕生年月日を抽出"""

        # パターン集（優先順位順）
        patterns = [
            # 完全な日付パターン
            (r'生年月日\s*=\s*\{\{生年月日と年齢\|(\d{4})\|(\d{1,2})\|(\d{1,2})', 'full'),
            (r'生年月日\s*=\s*\{\{Birth date and age\|(\d{4})\|(\d{1,2})\|(\d{1,2})', 'full'),
            (r'生年月日\s*=\s*(\d{4})年(\d{1,2})月(\d{1,2})日', 'full'),
            (r'birth_date\s*=\s*\{\{.*?\|(\d{4})\|(\d{1,2})\|(\d{1,2})', 'full'),
            (r'生誕\s*=\s*(\d{4})年(\d{1,2})月(\d{1,2})日', 'full'),

            # 年のみのパターン
            (r'生年月日\s*=\s*(\d{4})年', 'year'),
            (r'生誕\s*=\s*(\d{4})年', 'year'),
            (r'birth_year\s*=\s*(\d{4})', 'year'),
            (r'生年\s*=\s*(\d{4})', 'year'),

            # 死亡年からの推定（活動期間がある場合）
            (r'死亡年月日\s*=\s*(\d{4})年.*?活動期間.*?(\d{2,3})年', 'death_estimate'),
        ]

        for pattern, pattern_type in patterns:
            match = re.search(pattern, wikitext, re.IGNORECASE | re.DOTALL)
            if match:
                if pattern_type == 'full':
                    year = int(match.group(1))
                    month = int(match.group(2))
                    day = int(match.group(3))
                    # 妥当性チェック
                    if 1000 <= year <= 2024 and 1 <= month <= 12 and 1 <= day <= 31:
                        return f"{year:04d}-{month:02d}-{day:02d}", year
                elif pattern_type == 'year':
                    year = int(match.group(1))
                    if 1000 <= year <= 2024:
                        return None, year

        return None, None

    def get_wikipedia_page(self, name: str, name_ja: str = None) -> Optional[Dict]:
        """Wikipedia APIから人物ページを取得"""

        # キャッシュチェック
        cache_key = self.get_cache_key(name)
        if cache_key in self.cache:
            self.stats['cache_hits'] += 1
            logger.debug(f"キャッシュヒット: {name}")
            return self.cache[cache_key]

        # 日本語Wikipedia優先
        search_names = []
        if name_ja:
            search_names.append((name_ja, 'ja'))
        search_names.append((name, 'en'))
        search_names.append((name, 'ja'))

        for search_name, lang in search_names:
            base_url = f"https://{lang}.wikipedia.org/w/api.php"

            # ステップ1: ページタイトル検索
            search_params = {
                'action': 'query',
                'list': 'search',
                'srsearch': search_name,
                'format': 'json',
                'srlimit': 1
            }

            try:
                self.stats['api_calls'] += 1
                response = self.session.get(base_url, params=search_params, timeout=10)
                response.raise_for_status()
                data = response.json()

                search_results = data.get('query', {}).get('search', [])
                if not search_results:
                    continue

                page_title = search_results[0]['title']

                # ステップ2: ページ内容取得
                content_params = {
                    'action': 'query',
                    'titles': page_title,
                    'prop': 'revisions',
                    'rvprop': 'content',
                    'format': 'json'
                }

                self.stats['api_calls'] += 1
                response = self.session.get(base_url, params=content_params, timeout=10)
                response.raise_for_status()
                data = response.json()

                pages = data.get('query', {}).get('pages', {})
                for page_id, page_data in pages.items():
                    if page_id == '-1':
                        continue

                    revisions = page_data.get('revisions', [])
                    if revisions:
                        wikitext = revisions[0].get('*', '')
                        birth_date, birth_year = self.extract_birth_from_infobox(wikitext)

                        if birth_year:
                            result = {
                                'birth_date': birth_date,
                                'birth_year': birth_year,
                                'wikipedia_title': page_title,
                                'wikipedia_lang': lang
                            }
                            self.cache[cache_key] = result
                            self.stats['found'] += 1
                            logger.info(f"✅ 取得成功: {name} -> {birth_year} ({lang})")
                            return result

            except Exception as e:
                self.stats['errors'] += 1
                logger.error(f"エラー: {name} ({lang}) - {str(e)}")

        # 見つからなかった場合
        self.stats['not_found'] += 1
        self.cache[cache_key] = None
        logger.debug(f"❌ 見つかりません: {name}")
        return None

    def process_dataframe(self, df: pd.DataFrame, batch_size: int = 100) -> pd.DataFrame:
        """データフレームを処理"""
        logger.info(f"📊 処理開始: {len(df)}件")

        # 既に誕生年がある行をスキップ
        has_birth = df['birth_year_int'].notna()
        df_done = df[has_birth].copy()
        df_todo = df[~has_birth].copy()

        logger.info(f"⏭️ スキップ: {len(df_done)}件（既に取得済み）")
        logger.info(f"🎯 処理対象: {len(df_todo)}件")

        if len(df_todo) == 0:
            return df

        # 処理
        for idx, (_, row) in enumerate(df_todo.iterrows()):
            if idx % 10 == 0:
                logger.info(f"進捗: {idx}/{len(df_todo)} ({idx/len(df_todo)*100:.1f}%)")

            person_id = row['person_id']
            name = row['person_name']
            name_ja = row.get('person_name_ja', row.get('person_name_display', name))

            # Wikipedia から取得
            result = self.get_wikipedia_page(name, name_ja)

            if result:
                df_todo.loc[df_todo['person_id'] == person_id, 'birth_date'] = result['birth_date']
                df_todo.loc[df_todo['person_id'] == person_id, 'birth_year_int'] = result['birth_year']

            # レート制限対策
            time.sleep(0.2)

            # 定期的にキャッシュ保存
            if idx % 50 == 0:
                self.save_cache()

        # 最終結果を結合
        df_final = pd.concat([df_done, df_todo], ignore_index=True)

        # キャッシュ保存
        self.save_cache()

        # 統計出力
        self.print_stats()

        return df_final

    def print_stats(self):
        """統計情報を出力"""
        logger.info("=" * 60)
        logger.info("📊 Wikipedia取得統計")
        logger.info("=" * 60)
        logger.info(f"API呼び出し: {self.stats['api_calls']}")
        logger.info(f"取得成功: {self.stats['found']}")
        logger.info(f"取得失敗: {self.stats['not_found']}")
        logger.info(f"エラー: {self.stats['errors']}")
        logger.info(f"キャッシュヒット: {self.stats['cache_hits']}")

        if self.stats['api_calls'] > 0:
            success_rate = (self.stats['found'] / (self.stats['found'] + self.stats['not_found'])) * 100
            logger.info(f"成功率: {success_rate:.1f}%")


def main():
    """メイン処理"""
    # テストデータ
    test_data = pd.DataFrame([
        {'person_id': 'P000543', 'person_name': 'Kobe Bryant', 'person_name_ja': 'コービー・ブライアント', 'birth_year_int': None},
        {'person_id': 'P001365', 'person_name': 'Ulysses S. Grant', 'person_name_ja': 'ユリシーズ・グラント', 'birth_year_int': None},
        {'person_id': 'P002884', 'person_name': '小林陵侑', 'person_name_ja': '小林陵侑', 'birth_year_int': None},
        {'person_id': 'P015812', 'person_name': 'Félix Tshisekedi', 'person_name_ja': 'フェリックス・チセケディ', 'birth_year_int': None},
        {'person_id': 'P000001', 'person_name': 'Ado', 'person_name_ja': 'Ado', 'birth_year_int': 2002.0}  # 既知データ
    ])

    print("🧪 Wikipedia誕生年取得テスト")
    print("=" * 60)

    # コレクター初期化
    collector = WikipediaBirthCollector()

    # 処理実行
    result = collector.process_dataframe(test_data)

    # 結果表示
    print("\n📊 テスト結果:")
    print("=" * 60)
    for _, row in result.iterrows():
        if pd.notna(row.get('birth_year_int')):
            print(f"✅ {row['person_id']}: {row['person_name_ja']} -> {int(row['birth_year_int'])}")
        else:
            print(f"❌ {row['person_id']}: {row['person_name_ja']} -> 未取得")

    # 統計
    total = len(result)
    found = result['birth_year_int'].notna().sum()
    print("=" * 60)
    print(f"成功率: {found}/{total} ({found/total*100:.1f}%)")


if __name__ == "__main__":
    main()
