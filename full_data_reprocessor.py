#!/usr/bin/env python3
"""
全データ段階的再処理システム
削除率を監視しながら段階的に処理
"""

import pandas as pd
import json
import time
from datetime import datetime
import logging
from pathlib import Path
import sys
from typing import List, Dict, Any

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)
logger = logging.getLogger(__name__)

# バッチ処理システムをインポート
sys.path.append(str(Path(__file__).parent))
from batch_wikipedia_processor import BatchWikipediaProcessor

class FullDataReprocessor:
    """全データ再処理システム"""
    
    def __init__(self, batch_size=500, max_workers=5):
        """
        初期化
        
        Args:
            batch_size: 1バッチのサイズ（デフォルト500）
            max_workers: 並列ワーカー数（デフォルト5）
        """
        self.batch_size = batch_size
        self.processor = BatchWikipediaProcessor(max_workers=max_workers)
        self.results = []
        self.stats = {
            'total_processed': 0,
            'wikipedia_found': 0,
            'score_improved': 0,
            'saved_from_deletion': 0,
            'deletion_rate': 0.0,
            'batches_processed': 0
        }
        
    def load_data(self, csv_file: str) -> pd.DataFrame:
        """データを読み込み"""
        try:
            df = pd.read_csv(csv_file, encoding='utf-8-sig')
            logger.info(f"データ読み込み完了: {len(df)}件")
            return df
        except Exception as e:
            logger.error(f"データ読み込みエラー: {e}")
            return None
    
    def prepare_batch_data(self, df: pd.DataFrame, offset: int, limit: int) -> List[Dict]:
        """バッチ用データを準備"""
        batch_df = df.iloc[offset:offset+limit]
        records = []
        
        for idx, row in batch_df.iterrows():
            records.append({
                'person_id': row['person_id'],
                'person_name': row['name'],
                'current_score': row.get('recognition_score', 0),
                'should_delete': row.get('should_delete', False)
            })
        
        return records
    
    def analyze_batch_results(self, results: List[Dict], batch_num: int) -> Dict[str, Any]:
        """バッチ結果を分析"""
        if not results:
            return {}
        
        df_batch = pd.DataFrame(results)
        
        # 統計計算
        found = df_batch['wikipedia_found'].sum()
        improved = len(df_batch[df_batch['improvement'] > 0])
        saved = len(df_batch[
            (df_batch['old_score'] == 0) & 
            (df_batch['new_score'] > 0)
        ])
        should_delete = df_batch['should_delete'].sum()
        deletion_rate = should_delete / len(df_batch) * 100 if len(df_batch) > 0 else 0
        
        # 統計更新
        self.stats['wikipedia_found'] += found
        self.stats['score_improved'] += improved
        self.stats['saved_from_deletion'] += saved
        
        logger.info(f"\n📊 バッチ #{batch_num} 結果:")
        logger.info(f"  処理件数: {len(df_batch)}")
        logger.info(f"  Wikipedia発見: {found} ({found/len(df_batch)*100:.1f}%)")
        logger.info(f"  スコア改善: {improved}")
        logger.info(f"  削除から救済: {saved}")
        logger.info(f"  削除率: {deletion_rate:.1f}%")
        
        # 削除率チェック
        if deletion_rate > 20:
            logger.warning(f"⚠️ 削除率が高い: {deletion_rate:.1f}%")
        else:
            logger.info(f"✅ 削除率正常: {deletion_rate:.1f}%")
        
        return {
            'batch_num': batch_num,
            'processed': len(df_batch),
            'found': found,
            'improved': improved,
            'saved': saved,
            'deletion_rate': deletion_rate
        }
    
    def save_checkpoint(self, results: List[Dict], batch_num: int):
        """チェックポイントを保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        checkpoint_file = f"checkpoint_batch{batch_num}_{timestamp}.csv"
        
        if results:
            df_checkpoint = pd.DataFrame(results)
            df_checkpoint.to_csv(checkpoint_file, index=False, encoding='utf-8-sig')
            logger.info(f"チェックポイント保存: {checkpoint_file}")
    
    def process_all_data(self, csv_file: str, start_offset: int = 0):
        """全データを段階的に処理"""
        
        logger.info("="*60)
        logger.info("🚀 全データ段階的再処理開始")
        logger.info("="*60)
        
        # データ読み込み
        df = self.load_data(csv_file)
        if df is None:
            return
        
        total_records = len(df)
        num_batches = (total_records - start_offset + self.batch_size - 1) // self.batch_size
        
        logger.info(f"総レコード数: {total_records}")
        logger.info(f"バッチサイズ: {self.batch_size}")
        logger.info(f"バッチ数: {num_batches}")
        logger.info(f"開始オフセット: {start_offset}")
        
        all_results = []
        batch_stats = []
        
        # バッチ処理
        for batch_num in range(num_batches):
            offset = start_offset + batch_num * self.batch_size
            
            # 最後のバッチのサイズ調整
            limit = min(self.batch_size, total_records - offset)
            
            if limit <= 0:
                break
            
            logger.info(f"\n{'='*60}")
            logger.info(f"📦 バッチ #{batch_num + 1}/{num_batches} 処理開始")
            logger.info(f"  範囲: {offset} - {offset + limit}")
            logger.info(f"{'='*60}")
            
            # バッチデータ準備
            batch_records = self.prepare_batch_data(df, offset, limit)
            
            # バッチ処理実行
            try:
                batch_results = self.processor.process_batch(batch_records)
                all_results.extend(batch_results)
                
                # バッチ結果分析
                batch_stat = self.analyze_batch_results(batch_results, batch_num + 1)
                batch_stats.append(batch_stat)
                
                # 統計更新
                self.stats['total_processed'] = offset + limit
                self.stats['batches_processed'] = batch_num + 1
                
                # 削除率の累積計算
                total_should_delete = sum(1 for r in all_results if r.get('should_delete', False))
                self.stats['deletion_rate'] = total_should_delete / len(all_results) * 100
                
                # 削除率が異常に高い場合は警告
                if self.stats['deletion_rate'] > 25:
                    logger.warning(f"⚠️ 累積削除率が高すぎます: {self.stats['deletion_rate']:.1f}%")
                    logger.warning("処理を継続しますが、結果を確認してください")
                
                # チェックポイント保存（5バッチごと）
                if (batch_num + 1) % 5 == 0:
                    self.save_checkpoint(all_results, batch_num + 1)
                
                # 進捗表示
                progress = (offset + limit) / total_records * 100
                logger.info(f"\n📈 全体進捗: {progress:.1f}% ({offset + limit}/{total_records})")
                logger.info(f"  累積削除率: {self.stats['deletion_rate']:.1f}%")
                
                # レート制限対策（バッチ間で短い休憩）
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"バッチ処理エラー: {e}")
                # エラー時もチェックポイント保存
                self.save_checkpoint(all_results, batch_num + 1)
                continue
        
        # 最終結果保存
        self.save_final_results(all_results, batch_stats)
        
        # 最終統計表示
        self.show_final_statistics()
    
    def save_final_results(self, results: List[Dict], batch_stats: List[Dict]):
        """最終結果を保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 全結果CSV
        if results:
            results_file = f"full_reprocessed_{timestamp}.csv"
            df_results = pd.DataFrame(results)
            df_results.to_csv(results_file, index=False, encoding='utf-8-sig')
            logger.info(f"\n✅ 全結果保存: {results_file}")
        
        # バッチ統計
        if batch_stats:
            stats_file = f"batch_statistics_{timestamp}.csv"
            df_stats = pd.DataFrame(batch_stats)
            df_stats.to_csv(stats_file, index=False, encoding='utf-8-sig')
            logger.info(f"📊 バッチ統計保存: {stats_file}")
        
        # 総合統計JSON
        summary = {
            'timestamp': timestamp,
            'total_processed': self.stats['total_processed'],
            'batches_processed': self.stats['batches_processed'],
            'wikipedia_found': self.stats['wikipedia_found'],
            'score_improved': self.stats['score_improved'],
            'saved_from_deletion': self.stats['saved_from_deletion'],
            'final_deletion_rate': self.stats['deletion_rate'],
            'success_rate': self.stats['wikipedia_found'] / self.stats['total_processed'] * 100 if self.stats['total_processed'] > 0 else 0
        }
        
        summary_file = f"reprocessing_summary_{timestamp}.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        logger.info(f"📝 総合統計保存: {summary_file}")
    
    def show_final_statistics(self):
        """最終統計を表示"""
        logger.info("\n" + "="*60)
        logger.info("🎯 全データ再処理完了")
        logger.info("="*60)
        logger.info(f"処理総数: {self.stats['total_processed']}件")
        logger.info(f"バッチ数: {self.stats['batches_processed']}")
        logger.info(f"Wikipedia発見: {self.stats['wikipedia_found']}件")
        logger.info(f"スコア改善: {self.stats['score_improved']}件")
        logger.info(f"削除から救済: {self.stats['saved_from_deletion']}件")
        logger.info(f"最終削除率: {self.stats['deletion_rate']:.1f}%")
        
        # 削除率の評価
        if self.stats['deletion_rate'] <= 20:
            logger.info("✅ 削除率は正常範囲内です")
        elif self.stats['deletion_rate'] <= 30:
            logger.warning("⚠️ 削除率がやや高めです")
        else:
            logger.error("❌ 削除率が異常に高いです。追加調査が必要です")

def main():
    """メイン処理"""
    import argparse
    
    parser = argparse.ArgumentParser(description='全データ段階的再処理')
    parser.add_argument('--batch-size', type=int, default=500, help='バッチサイズ（デフォルト: 500）')
    parser.add_argument('--workers', type=int, default=5, help='並列ワーカー数（デフォルト: 5）')
    parser.add_argument('--start-offset', type=int, default=0, help='開始オフセット（デフォルト: 0）')
    parser.add_argument('--csv-file', type=str, 
                       default='/Users/admin/Documents/AIUELAB/001-final-hourglass/recognition_results_ALL_20250908_224635.csv',
                       help='入力CSVファイル')
    
    args = parser.parse_args()
    
    # 再処理実行
    reprocessor = FullDataReprocessor(
        batch_size=args.batch_size,
        max_workers=args.workers
    )
    
    reprocessor.process_all_data(
        csv_file=args.csv_file,
        start_offset=args.start_offset
    )

if __name__ == "__main__":
    main()