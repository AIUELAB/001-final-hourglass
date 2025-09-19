#!/usr/bin/env python3
"""
最適化されたWikidata誕生年取得システム
確定情報のみを効率的に収集
"""

import pandas as pd
import requests
import time
import json
import logging
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('wikidata_birth_collection.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class WikidataBirthCollector:
    """Wikidataから誕生年を確定的に取得するコレクター"""

    def __init__(self):
        self.endpoint = "https://query.wikidata.org/sparql"
        self.headers = {
            'User-Agent': 'UltraThinkHourglass/1.0 (Birth Year Collection) Python/3.11',
            'Accept': 'application/sparql-results+json'
        }
        self.cache_file = "wikidata_birth_cache.json"
        self.cache = self.load_cache()
        self.stats = {
            'queries': 0,
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

    def search_person_by_name(self, name: str, name_ja: str = None) -> Optional[Dict]:
        """名前から人物を検索して誕生年を取得"""

        # キャッシュチェック
        cache_key = self.get_cache_key(name)
        if cache_key in self.cache:
            self.stats['cache_hits'] += 1
            logger.debug(f"キャッシュヒット: {name}")
            return self.cache[cache_key]

        # 検索名を決定（日本語名優先）
        search_name = name_ja if name_ja else name

        # SPARQLクエリ
        query = """
        SELECT DISTINCT ?person ?personLabel ?birthDate ?deathDate ?description
        WHERE {
            ?person wdt:P31 wd:Q5 .  # 人間
            ?person rdfs:label ?label .
            FILTER(LANG(?label) = "ja" || LANG(?label) = "en")
            FILTER(CONTAINS(LCASE(?label), LCASE("%s")))

            # 生年月日（必須）
            ?person wdt:P569 ?birthDate .

            # 死亡日（オプション）
            OPTIONAL { ?person wdt:P570 ?deathDate }

            # 説明（オプション）
            OPTIONAL { ?person schema:description ?description FILTER(LANG(?description) = "ja") }

            SERVICE wikibase:label { bd:serviceParam wikibase:language "ja,en" }
        }
        LIMIT 10
        """ % search_name.replace('"', '\\"')

        try:
            self.stats['queries'] += 1
            response = requests.get(
                self.endpoint,
                params={'query': query, 'format': 'json'},
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()

            data = response.json()
            results = data.get('results', {}).get('bindings', [])

            if results:
                # 最も関連性の高い結果を選択
                best_match = self.select_best_match(results, search_name)
                if best_match:
                    birth_info = self.extract_birth_info(best_match)
                    self.cache[cache_key] = birth_info
                    self.stats['found'] += 1
                    logger.info(f"✅ 取得成功: {name} -> {birth_info.get('birth_year')}")
                    return birth_info

            self.stats['not_found'] += 1
            self.cache[cache_key] = None
            logger.debug(f"❌ 見つかりません: {name}")
            return None

        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"エラー: {name} - {str(e)}")
            return None

    def select_best_match(self, results: List[Dict], search_name: str) -> Optional[Dict]:
        """最も関連性の高い結果を選択"""
        if not results:
            return None

        # 完全一致を優先
        for result in results:
            label = result.get('personLabel', {}).get('value', '')
            if label.lower() == search_name.lower():
                return result

        # 部分一致で最初の結果を返す
        return results[0]

    def extract_birth_info(self, result: Dict) -> Dict:
        """結果から誕生情報を抽出"""
        birth_date_str = result.get('birthDate', {}).get('value', '')
        death_date_str = result.get('deathDate', {}).get('value', '')

        birth_date = None
        birth_year = None

        if birth_date_str:
            try:
                # ISO形式の日付をパース
                if 'T' in birth_date_str:
                    birth_date_str = birth_date_str.split('T')[0]

                if len(birth_date_str) >= 4:
                    birth_year = int(birth_date_str[:4])

                    if len(birth_date_str) == 10:  # YYYY-MM-DD
                        birth_date = birth_date_str
                    elif '-' in birth_date_str:
                        parts = birth_date_str.split('-')
                        if len(parts) >= 2:
                            birth_date = birth_date_str

            except (ValueError, IndexError):
                pass

        return {
            'wikidata_id': result.get('person', {}).get('value', ''),
            'name': result.get('personLabel', {}).get('value', ''),
            'birth_date': birth_date,
            'birth_year': birth_year,
            'death_date': death_date_str.split('T')[0] if death_date_str else None,
            'description': result.get('description', {}).get('value', '')
        }

    def process_batch(self, df_batch: pd.DataFrame) -> List[Dict]:
        """バッチ処理"""
        results = []

        for _, row in df_batch.iterrows():
            person_id = row['person_id']
            name = row['person_name']
            name_ja = row.get('person_name_ja', row.get('person_name_display', name))

            logger.info(f"処理中: {person_id} - {name}")

            # Wikidataから取得
            birth_info = self.search_person_by_name(name, name_ja)

            result = {
                'person_id': person_id,
                'person_name': name,
                'wikidata_birth_date': birth_info.get('birth_date') if birth_info else None,
                'wikidata_birth_year': birth_info.get('birth_year') if birth_info else None,
                'wikidata_id': birth_info.get('wikidata_id') if birth_info else None,
                'wikidata_retrieved_at': datetime.now().isoformat()
            }

            results.append(result)

            # レート制限対策
            time.sleep(0.5)

        return results

    def process_dataframe(self, df: pd.DataFrame, batch_size: int = 50) -> pd.DataFrame:
        """データフレーム全体を処理"""
        logger.info(f"📊 処理開始: {len(df)}件")

        # 既に誕生年がある行をスキップ
        has_birth_year = df['birth_year_int'].notna()
        df_todo = df[~has_birth_year].copy()
        df_done = df[has_birth_year].copy()

        logger.info(f"⏭️ スキップ: {len(df_done)}件（既に取得済み）")
        logger.info(f"🎯 処理対象: {len(df_todo)}件")

        if len(df_todo) == 0:
            logger.info("✅ すべて処理済みです")
            return df

        # バッチ処理
        all_results = []
        for i in range(0, len(df_todo), batch_size):
            batch = df_todo.iloc[i:i+batch_size]
            logger.info(f"バッチ {i//batch_size + 1}/{(len(df_todo) + batch_size - 1)//batch_size}")

            batch_results = self.process_batch(batch)
            all_results.extend(batch_results)

            # 定期的にキャッシュ保存
            if (i + batch_size) % 100 == 0:
                self.save_cache()
                logger.info(f"💾 キャッシュ保存: {len(self.cache)}件")

        # 結果をデータフレームにマージ
        results_df = pd.DataFrame(all_results)

        # マージ
        df_merged = df_todo.merge(
            results_df,
            on='person_id',
            how='left',
            suffixes=('', '_new')
        )

        # 誕生年を更新
        mask = df_merged['wikidata_birth_year'].notna()
        df_merged.loc[mask, 'birth_date'] = df_merged.loc[mask, 'wikidata_birth_date']
        df_merged.loc[mask, 'birth_year_int'] = df_merged.loc[mask, 'wikidata_birth_year']

        # 不要な列を削除
        columns_to_drop = [col for col in df_merged.columns if col.endswith('_new')]
        columns_to_drop.extend(['wikidata_birth_date', 'wikidata_birth_year', 'wikidata_id', 'wikidata_retrieved_at'])
        df_merged = df_merged.drop(columns=[col for col in columns_to_drop if col in df_merged.columns], errors='ignore')

        # 結合
        df_final = pd.concat([df_done, df_merged], ignore_index=True)

        # 最終キャッシュ保存
        self.save_cache()

        # 統計出力
        self.print_stats()

        return df_final

    def print_stats(self):
        """統計情報を出力"""
        logger.info("=" * 60)
        logger.info("📊 Wikidata取得統計")
        logger.info("=" * 60)
        logger.info(f"クエリ数: {self.stats['queries']}")
        logger.info(f"取得成功: {self.stats['found']}")
        logger.info(f"取得失敗: {self.stats['not_found']}")
        logger.info(f"エラー: {self.stats['errors']}")
        logger.info(f"キャッシュヒット: {self.stats['cache_hits']}")

        if self.stats['queries'] > 0:
            success_rate = (self.stats['found'] / self.stats['queries']) * 100
            logger.info(f"成功率: {success_rate:.1f}%")


def main():
    """メイン処理"""
    # 最新のCSVファイルを読み込み
    input_file = "ultra_think_WITH_BIRTH_YEARS_20250917_135652.csv"
    logger.info(f"📂 入力ファイル: {input_file}")

    # データ読み込み
    df = pd.read_csv(input_file, encoding='utf-8-sig')
    logger.info(f"✅ {len(df)}件のレコード読み込み")

    # Wikidataコレクター初期化
    collector = WikidataBirthCollector()

    # 処理実行
    df_result = collector.process_dataframe(df, batch_size=50)

    # 結果を保存
    output_file = f"ultra_think_WITH_WIKIDATA_BIRTHS_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df_result.to_csv(output_file, index=False, encoding='utf-8-sig')
    logger.info(f"💾 結果保存: {output_file}")

    # 取得率を計算
    total = len(df_result)
    has_birth_year = df_result['birth_year_int'].notna().sum()
    rate = (has_birth_year / total * 100) if total > 0 else 0

    logger.info("=" * 60)
    logger.info(f"🎯 最終結果: {has_birth_year}/{total}件 ({rate:.1f}%)")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()