#!/usr/bin/env python3
"""
Web検索による知名度測定システム - 実装プロトタイプ
Google Search APIとWeb検索による知名度測定システムの完全実装版

使用方法:
    python web_recognition_system.py --mode brave --batch-size 50
    python web_recognition_system.py --mode google --api-key YOUR_KEY
    python web_recognition_system.py --mode scraping --rate-limit 5
"""

import asyncio
import json
import sqlite3
from src.database_utils import get_connection
import pandas as pd
import requests
import time
import argparse
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import os

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class WebRecognitionSystem:
    """Web検索による知名度測定システムのメインクラス"""

    def __init__(self, cache_duration_hours: int = 168):
        self.cache_duration = timedelta(hours=cache_duration_hours)
        self.cache_db = Path("recognition_cache.db")
        self.setup_cache_db()

    def setup_cache_db(self):
        """キャッシュデータベースセットアップ"""
        conn = get_connection(self.cache_db)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS recognition_cache (
                person_name TEXT PRIMARY KEY,
                person_id TEXT,
                nationality TEXT,
                occupation TEXT,
                search_provider TEXT,
                recognition_score INTEGER,
                search_results_count INTEGER,
                relevance_score REAL,
                raw_data TEXT,
                cached_at TIMESTAMP,
                query_cost REAL
            )
        ''')

        # インデックス作成
        conn.execute('CREATE INDEX IF NOT EXISTS idx_cached_at ON recognition_cache(cached_at)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_provider ON recognition_cache(search_provider)')
        conn.commit()
        conn.close()

    def get_cached_result(self, person_name: str, provider: str = "") -> Optional[Dict]:
        """キャッシュから結果取得"""
        conn = get_connection(self.cache_db)
        cursor = conn.cursor()

        cutoff_time = datetime.now() - self.cache_duration

        query = 'SELECT * FROM recognition_cache WHERE person_name = ? AND cached_at > ?'
        params = [person_name, cutoff_time]

        if provider:
            query += ' AND search_provider = ?'
            params.append(provider)

        cursor.execute(query, params)
        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                'person_name': row[0],
                'person_id': row[1],
                'nationality': row[2],
                'occupation': row[3],
                'search_provider': row[4],
                'recognition_score': row[5],
                'search_results_count': row[6],
                'relevance_score': row[7],
                'raw_data': json.loads(row[8]) if row[8] else {},
                'cached_at': row[9],
                'query_cost': row[10],
                'from_cache': True
            }
        return None

    def cache_result(self, result_data: Dict):
        """結果をキャッシュに保存"""
        conn = get_connection(self.cache_db)

        conn.execute('''
            INSERT OR REPLACE INTO recognition_cache
            (person_name, person_id, nationality, occupation, search_provider,
             recognition_score, search_results_count, relevance_score, raw_data, cached_at, query_cost)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            result_data.get('person_name', ''),
            result_data.get('person_id', ''),
            result_data.get('nationality', ''),
            result_data.get('occupation', ''),
            result_data.get('search_provider', ''),
            result_data.get('recognition_score', 0),
            result_data.get('search_results_count', 0),
            result_data.get('relevance_score', 0.0),
            json.dumps(result_data.get('raw_data', {})),
            datetime.now(),
            result_data.get('query_cost', 0.0)
        ))

        conn.commit()
        conn.close()


class BraveSearchProvider:
    """Brave Search MCP統合プロバイダー（デモ版）"""

    def __init__(self, api_key: str = ""):
        self.api_key = api_key

    async def search_person(self, person_name: str, nationality: str = "", occupation: str = "") -> Dict:
        """
        Brave Search MCPを使用した人物検索
        実際の実装では mcp__brave-search__brave_web_search を呼び出し
        """

        # 検索クエリ生成
        search_queries = self._generate_queries(person_name, nationality, occupation)

        search_results = {
            'person_name': person_name,
            'search_provider': 'brave',
            'queries': search_queries,
            'results': [],
            'total_results': 0,
            'relevance_score': 0.0,
            'query_cost': 0.0  # Brave Searchの実際のコストは不明
        }

        # 各クエリで検索実行（デモ版では模擬結果）
        for query in search_queries:
            # 実装時: result = await call_mcp_brave_search(query)
            mock_result = self._mock_brave_search(query)
            search_results['results'].append(mock_result)
            search_results['total_results'] += len(mock_result.get('web', []))

            # レート制限
            await asyncio.sleep(1)

        # 関連度とスコア計算
        search_results['relevance_score'] = self._calculate_relevance(search_results, person_name)
        search_results['recognition_score'] = self._calculate_recognition_score(search_results)

        return search_results

    def _generate_queries(self, name: str, nationality: str, occupation: str) -> List[str]:
        """検索クエリ生成"""
        queries = [f'"{name}"']

        if occupation:
            queries.append(f'"{name}" {occupation}')
        if nationality and occupation:
            queries.append(f'"{name}" {occupation} {nationality}')

        return queries[:2]  # コスト考慮で最大2クエリ

    def _mock_brave_search(self, query: str) -> Dict:
        """Brave Search結果のモック（実装時は実際のMCP呼び出しに置換）"""
        return {
            'query': query,
            'web': [
                {'title': f'Sample result for {query}', 'url': 'https://example.com', 'description': f'Description for {query}'},
                {'title': f'Another result for {query}', 'url': 'https://example2.com', 'description': f'More info about {query}'}
            ],
            'total_estimated': 1000  # 推定結果数
        }

    def _calculate_relevance(self, search_results: Dict, person_name: str) -> float:
        """検索結果の関連度計算"""
        if not search_results.get('results'):
            return 0.0

        total_relevance = 0.0
        total_results = 0

        for result in search_results['results']:
            for web_result in result.get('web', []):
                title = web_result.get('title', '').lower()
                desc = web_result.get('description', '').lower()
                name_lower = person_name.lower()

                relevance = 0.0
                if name_lower in title:
                    relevance += 1.0
                if name_lower in desc:
                    relevance += 0.5

                total_relevance += relevance
                total_results += 1

        return total_relevance / max(total_results, 1)

    def _calculate_recognition_score(self, search_results: Dict) -> int:
        """知名度スコア計算（0-100）"""
        total_results = search_results.get('total_results', 0)
        relevance_score = search_results.get('relevance_score', 0.0)

        if total_results == 0:
            return 0

        # ログスケールベーススコア + 関連度ボーナス
        import math
        base_score = min(math.log10(max(total_results, 1)) * 25, 80)
        relevance_bonus = relevance_score * 20

        return min(int(base_score + relevance_bonus), 100)


class GoogleSearchProvider:
    """Google Custom Search API プロバイダー"""

    def __init__(self, api_key: str, search_engine_id: str):
        self.api_key = api_key
        self.search_engine_id = search_engine_id
        self.base_url = "https://customsearch.googleapis.com/customsearch/v1"

    async def search_person(self, person_name: str, nationality: str = "", occupation: str = "") -> Dict:
        """Google Custom Search APIによる人物検索"""

        query = f'"{person_name}"'
        if occupation:
            query += f' {occupation}'

        params = {
            'key': self.api_key,
            'cx': self.search_engine_id,
            'q': query,
            'num': 10
        }

        try:
            response = requests.get(self.base_url, params=params)
            data = response.json()

            if 'error' in data:
                raise Exception(f"Google API Error: {data['error']['message']}")

            total_results = int(data.get('searchInformation', {}).get('totalResults', 0))

            result = {
                'person_name': person_name,
                'search_provider': 'google',
                'total_results': total_results,
                'search_results_count': len(data.get('items', [])),
                'items': data.get('items', []),
                'recognition_score': self._calculate_google_score(total_results),
                'query_cost': 0.005,  # $5/1000 queries
                'raw_data': data
            }

            return result

        except Exception as e:
            logger.error(f"Google Search error for {person_name}: {e}")
            return {
                'person_name': person_name,
                'search_provider': 'google',
                'error': str(e),
                'recognition_score': 0,
                'query_cost': 0.005
            }

    def _calculate_google_score(self, total_results: int) -> int:
        """Google検索結果数から知名度スコア計算"""
        if total_results == 0:
            return 0
        elif total_results < 100:
            return 15
        elif total_results < 1000:
            return 30
        elif total_results < 10000:
            return 50
        elif total_results < 100000:
            return 75
        else:
            return 95


class BatchRecognitionProcessor:
    """大規模データの知名度測定バッチ処理システム"""

    def __init__(self, max_concurrent: int = 3, rate_limit_seconds: float = 2.0):
        self.max_concurrent = max_concurrent
        self.rate_limit = rate_limit_seconds
        self.recognition_system = WebRecognitionSystem()

    async def process_csv_database(self,
                                 csv_file_path: str,
                                 provider: str = "brave",
                                 batch_size: int = 50,
                                 start_from: int = 0,
                                 **provider_kwargs) -> Dict:
        """CSVデータベースのバッチ処理"""

        # CSVファイル読み込み
        if not os.path.exists(csv_file_path):
            raise FileNotFoundError(f"CSV file not found: {csv_file_path}")

        df = pd.read_csv(csv_file_path)
        total_records = len(df)

        # 処理範囲
        end_index = min(start_from + batch_size, total_records)
        process_df = df.iloc[start_from:end_index]

        logger.info(f"バッチ処理開始: {len(process_df)} 件 ({start_from}-{end_index})")

        # プロバイダー初期化
        if provider == "brave":
            search_provider = BraveSearchProvider()
        elif provider == "google":
            search_provider = GoogleSearchProvider(
                provider_kwargs.get('api_key', ''),
                provider_kwargs.get('search_engine_id', '')
            )
        else:
            raise ValueError(f"Unknown provider: {provider}")

        # バッチ統計
        batch_stats = {
            'provider': provider,
            'start_time': datetime.now(),
            'total_records': len(process_df),
            'processed': 0,
            'from_cache': 0,
            'new_queries': 0,
            'errors': 0,
            'total_cost': 0.0,
            'results': []
        }

        # 並行処理制御
        semaphore = asyncio.Semaphore(self.max_concurrent)

        # タスク生成と実行
        tasks = []
        for index, row in process_df.iterrows():
            task = self._process_single_person(
                semaphore, search_provider, row, batch_stats
            )
            tasks.append(task)

        # 並行実行
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 結果処理
        successful_results = [r for r in results if not isinstance(r, Exception)]
        error_results = [r for r in results if isinstance(r, Exception)]

        batch_stats['results'] = successful_results
        batch_stats['errors'] = len(error_results)
        batch_stats['end_time'] = datetime.now()
        batch_stats['processing_time'] = (batch_stats['end_time'] - batch_stats['start_time']).total_seconds()

        # 結果保存
        await self._save_results(batch_stats, csv_file_path)

        return batch_stats

    async def _process_single_person(self,
                                   semaphore: asyncio.Semaphore,
                                   search_provider,
                                   person_row: pd.Series,
                                   batch_stats: Dict) -> Dict:
        """個人の知名度測定処理"""

        async with semaphore:
            person_name = person_row.get('person_name', '').strip()

            if not person_name:
                return {'error': 'Empty person name'}

            try:
                # キャッシュチェック
                cached_result = self.recognition_system.get_cached_result(
                    person_name, search_provider.__class__.__name__.lower().replace('provider', '')
                )

                if cached_result:
                    batch_stats['from_cache'] += 1
                    return cached_result

                # 新規検索実行
                batch_stats['new_queries'] += 1

                result = await search_provider.search_person(
                    person_name,
                    person_row.get('nationality', ''),
                    person_row.get('occupation', '')
                )

                # 追加情報セット
                result.update({
                    'person_id': person_row.get('person_id', ''),
                    'nationality': person_row.get('nationality', ''),
                    'occupation': person_row.get('occupation', ''),
                    'original_recognition': person_row.get('name_recognition', 0),
                    'processed_at': datetime.now().isoformat()
                })

                # キャッシュ保存
                self.recognition_system.cache_result(result)

                # コスト集計
                batch_stats['total_cost'] += result.get('query_cost', 0.0)
                batch_stats['processed'] += 1

                # レート制限
                await asyncio.sleep(self.rate_limit)

                return result

            except Exception as e:
                logger.error(f"Process error for {person_name}: {e}")
                return {
                    'person_name': person_name,
                    'error': str(e),
                    'processed_at': datetime.now().isoformat()
                }

    async def _save_results(self, batch_stats: Dict, original_csv: str):
        """バッチ処理結果をファイル保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 結果CSV
        if batch_stats['results']:
            results_df = pd.DataFrame(batch_stats['results'])
            results_file = f"recognition_results_{batch_stats['provider']}_{timestamp}.csv"
            results_df.to_csv(results_file, index=False, encoding='utf-8')
            logger.info(f"結果保存: {results_file}")

        # 統計JSON
        stats_copy = batch_stats.copy()
        stats_copy['start_time'] = stats_copy['start_time'].isoformat()
        stats_copy['end_time'] = stats_copy['end_time'].isoformat()
        stats_copy.pop('results', None)  # 大きなデータは除外

        stats_file = f"batch_stats_{batch_stats['provider']}_{timestamp}.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats_copy, f, ensure_ascii=False, indent=2)

        logger.info(f"統計保存: {stats_file}")

        # サマリー出力
        print(f"\n=== バッチ処理完了 ===")
        print(f"プロバイダー: {batch_stats['provider']}")
        print(f"処理件数: {batch_stats['processed']}")
        print(f"キャッシュヒット: {batch_stats['from_cache']}")
        print(f"新規クエリ: {batch_stats['new_queries']}")
        print(f"エラー件数: {batch_stats['errors']}")
        print(f"処理時間: {batch_stats['processing_time']:.2f}秒")
        print(f"推定コスト: ${batch_stats['total_cost']:.3f}")


# メイン実行部
async def main():
    """メイン実行関数"""
    parser = argparse.ArgumentParser(description='Web検索による知名度測定システム')
    parser.add_argument('--mode', choices=['brave', 'google', 'scraping'], default='brave',
                        help='使用する検索プロバイダー')
    parser.add_argument('--csv-file', type=str,
                        default='ultra_think_YOUTUBER_GROUPS_FIXED_20250828_201154.csv',
                        help='処理対象CSVファイル')
    parser.add_argument('--batch-size', type=int, default=50, help='バッチサイズ')
    parser.add_argument('--start-from', type=int, default=0, help='開始インデックス')
    parser.add_argument('--rate-limit', type=float, default=2.0, help='レート制限（秒）')
    parser.add_argument('--max-concurrent', type=int, default=3, help='最大並行数')

    # Google API用オプション
    parser.add_argument('--google-api-key', type=str, help='Google API Key')
    parser.add_argument('--google-search-engine-id', type=str, help='Google Search Engine ID')

    args = parser.parse_args()

    # プロセッサー初期化
    processor = BatchRecognitionProcessor(
        max_concurrent=args.max_concurrent,
        rate_limit_seconds=args.rate_limit
    )

    # プロバイダー固有パラメーター
    provider_kwargs = {}
    if args.mode == 'google':
        if not args.google_api_key or not args.google_search_engine_id:
            print("Google API使用時は --google-api-key と --google-search-engine-id が必要です")
            return
        provider_kwargs = {
            'api_key': args.google_api_key,
            'search_engine_id': args.google_search_engine_id
        }

    try:
        # バッチ処理実行
        result = await processor.process_csv_database(
            csv_file_path=args.csv_file,
            provider=args.mode,
            batch_size=args.batch_size,
            start_from=args.start_from,
            **provider_kwargs
        )

        print("\n=== 処理完了 ===")
        print(json.dumps({
            k: v for k, v in result.items()
            if k not in ['results']  # 大きなデータは表示しない
        }, indent=2, ensure_ascii=False, default=str))

    except Exception as e:
        logger.error(f"処理エラー: {e}")
        print(f"エラーが発生しました: {e}")


if __name__ == "__main__":
    asyncio.run(main())
