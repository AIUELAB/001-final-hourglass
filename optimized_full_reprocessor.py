#!/usr/bin/env python3
"""
最適化された全データ再処理システム
キャッシュを最大限活用して高速処理
"""

import pandas as pd
import json
import time
from datetime import datetime
import logging
from pathlib import Path
import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
import hashlib

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)
logger = logging.getLogger(__name__)

# システムをインポート
sys.path.append(str(Path(__file__).parent))
from wikipedia_recognition_system_v2 import WikipediaRecognitionSystemV2

class OptimizedFullReprocessor:
    """最適化された全データ再処理システム"""
    
    def __init__(self, batch_size=200, max_workers=10):
        """
        初期化
        
        Args:
            batch_size: バッチサイズ（デフォルト200）
            max_workers: 並列ワーカー数（デフォルト10）
        """
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.wiki_system = WikipediaRecognitionSystemV2()
        self.cache_dir = Path("cache/wikipedia")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 統計情報
        self.stats = {
            'total_processed': 0,
            'wikipedia_found': 0,
            'deleted_count': 0,
            'saved_count': 0,
            'cache_hits': 0,
            'api_calls': 0,
            'errors': 0
        }
        
    def get_cache_key(self, name: str) -> str:
        """キャッシュキーを生成"""
        return hashlib.md5(name.encode('utf-8')).hexdigest()
    
    def check_cache(self, name: str) -> Dict:
        """キャッシュをチェック"""
        cache_key = self.get_cache_key(name)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.stats['cache_hits'] += 1
                    return data
            except:
                pass
        return None
    
    def process_single(self, row: pd.Series) -> Dict:
        """単一レコードを処理"""
        try:
            name = row['name']
            person_id = row['person_id']
            old_score = row.get('recognition_score', 0)
            
            # キャッシュチェック
            cached = self.check_cache(name)
            if cached:
                score = cached.get('recognition_score', 0)
                found = cached.get('found', False)
                page = cached.get('page_title', '')
            else:
                # API呼び出し
                self.stats['api_calls'] += 1
                result = self.wiki_system.search_wikipedia(name)
                score = result.get('recognition_score', 0)
                found = result.get('found', False)
                page = result.get('page_title', '')
            
            # 削除判定
            should_delete = not found and score < 3.0
            
            # 統計更新
            if found:
                self.stats['wikipedia_found'] += 1
            if should_delete:
                self.stats['deleted_count'] += 1
            elif old_score == 0 and score > 0:
                self.stats['saved_count'] += 1
            
            return {
                'person_id': person_id,
                'name': name,
                'recognition_score': score,
                'wikipedia_found': found,
                'should_delete': should_delete,
                'reason': 'Wikipediaページなし' if should_delete else f'知名度スコア: {score:.1f}',
                'wikipedia_page': page,
                'protected': not should_delete,
                'old_score': old_score,
                'improvement': score - old_score
            }
            
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"処理エラー: {row.get('name', 'Unknown')} - {e}")
            return None
    
    def process_batch(self, df_batch: pd.DataFrame) -> List[Dict]:
        """バッチを並列処理"""
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            for idx, row in df_batch.iterrows():
                future = executor.submit(self.process_single, row)
                futures.append(future)
            
            for future in as_completed(futures):
                result = future.result()
                if result:
                    results.append(result)
                    self.stats['total_processed'] += 1
                    
                    # 進捗表示（100件ごと）
                    if self.stats['total_processed'] % 100 == 0:
                        self.show_progress()
        
        return results
    
    def show_progress(self):
        """進捗を表示"""
        total = self.stats['total_processed']
        found = self.stats['wikipedia_found']
        deleted = self.stats['deleted_count']
        saved = self.stats['saved_count']
        cache_rate = self.stats['cache_hits'] / total * 100 if total > 0 else 0
        deletion_rate = deleted / total * 100 if total > 0 else 0
        
        logger.info(f"進捗: {total}件処理 | "
                   f"削除率: {deletion_rate:.1f}% | "
                   f"Wikipedia: {found} | "
                   f"救済: {saved} | "
                   f"キャッシュ: {cache_rate:.1f}%")
        
        # 削除率チェック
        if deletion_rate > 25:
            logger.warning(f"⚠️ 削除率が高い: {deletion_rate:.1f}%")
    
    def process_all(self, csv_file: str, output_file: str = None):
        """全データを処理"""
        
        logger.info("="*60)
        logger.info("🚀 最適化された全データ再処理開始")
        logger.info("="*60)
        
        # データ読み込み
        try:
            df = pd.read_csv(csv_file, encoding='utf-8-sig')
            total_records = len(df)
            logger.info(f"データ読み込み: {total_records}件")
        except Exception as e:
            logger.error(f"データ読み込みエラー: {e}")
            return
        
        # 処理設定
        logger.info(f"バッチサイズ: {self.batch_size}")
        logger.info(f"並列ワーカー: {self.max_workers}")
        
        all_results = []
        start_time = time.time()
        
        # バッチ処理
        for i in range(0, total_records, self.batch_size):
            batch_end = min(i + self.batch_size, total_records)
            df_batch = df.iloc[i:batch_end]
            
            logger.info(f"\n📦 バッチ処理: {i+1}-{batch_end}/{total_records}")
            
            # バッチ処理
            batch_results = self.process_batch(df_batch)
            all_results.extend(batch_results)
            
            # チェックポイント（1000件ごと）
            if len(all_results) % 1000 == 0:
                self.save_checkpoint(all_results)
            
            # レート制限対策
            time.sleep(0.5)
        
        # 処理時間
        elapsed = time.time() - start_time
        
        # 最終結果保存
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"reprocessed_ALL_{timestamp}.csv"
        
        df_results = pd.DataFrame(all_results)
        df_results.to_csv(output_file, index=False, encoding='utf-8-sig')
        
        # 統計レポート
        self.show_final_report(elapsed, total_records, output_file)
        
        return df_results
    
    def save_checkpoint(self, results: List[Dict]):
        """チェックポイント保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        checkpoint_file = f"checkpoint_{len(results)}_{timestamp}.csv"
        df_checkpoint = pd.DataFrame(results)
        df_checkpoint.to_csv(checkpoint_file, index=False, encoding='utf-8-sig')
        logger.info(f"チェックポイント保存: {checkpoint_file}")
    
    def show_final_report(self, elapsed: float, total: int, output_file: str):
        """最終レポート表示"""
        logger.info("\n" + "="*60)
        logger.info("📊 最終レポート")
        logger.info("="*60)
        
        # 基本統計
        logger.info(f"処理件数: {self.stats['total_processed']}/{total}")
        logger.info(f"処理時間: {elapsed:.1f}秒")
        logger.info(f"処理速度: {total/elapsed:.1f}件/秒")
        
        # 結果統計
        deletion_rate = self.stats['deleted_count'] / self.stats['total_processed'] * 100
        logger.info(f"削除率: {deletion_rate:.1f}%")
        logger.info(f"Wikipedia発見: {self.stats['wikipedia_found']}")
        logger.info(f"削除から救済: {self.stats['saved_count']}")
        
        # キャッシュ統計
        cache_rate = self.stats['cache_hits'] / self.stats['total_processed'] * 100
        logger.info(f"キャッシュヒット率: {cache_rate:.1f}%")
        logger.info(f"API呼び出し: {self.stats['api_calls']}")
        
        # エラー
        if self.stats['errors'] > 0:
            logger.warning(f"エラー: {self.stats['errors']}件")
        
        # 削除率評価
        if deletion_rate <= 20:
            logger.info("✅ 削除率は正常範囲内です")
        elif deletion_rate <= 30:
            logger.warning("⚠️ 削除率がやや高めです")
        else:
            logger.error("❌ 削除率が異常に高いです")
        
        logger.info(f"\n✅ 結果ファイル: {output_file}")
        
        # 統計をJSONで保存
        stats_file = output_file.replace('.csv', '_stats.json')
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, ensure_ascii=False, indent=2)
        logger.info(f"📊 統計ファイル: {stats_file}")

def main():
    """メイン処理"""
    import argparse
    
    parser = argparse.ArgumentParser(description='最適化された全データ再処理')
    parser.add_argument('--input', type=str,
                       default='/Users/admin/Documents/AIUELAB/001-final-hourglass/recognition_results_ALL_20250908_224635.csv',
                       help='入力CSVファイル')
    parser.add_argument('--output', type=str, default=None,
                       help='出力CSVファイル（省略時は自動命名）')
    parser.add_argument('--batch-size', type=int, default=200,
                       help='バッチサイズ（デフォルト: 200）')
    parser.add_argument('--workers', type=int, default=10,
                       help='並列ワーカー数（デフォルト: 10）')
    
    args = parser.parse_args()
    
    # 処理実行
    processor = OptimizedFullReprocessor(
        batch_size=args.batch_size,
        max_workers=args.workers
    )
    
    processor.process_all(
        csv_file=args.input,
        output_file=args.output
    )

if __name__ == "__main__":
    main()