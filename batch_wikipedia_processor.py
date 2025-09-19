#!/usr/bin/env python3
"""
Wikipedia検索バッチ処理システム
並列処理とキャッシュ活用で高速化
"""

import pandas as pd
import json
import time
from datetime import datetime
import logging
from pathlib import Path
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import hashlib

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)
logger = logging.getLogger(__name__)

# 改善版システムをインポート
sys.path.append(str(Path(__file__).parent))
from wikipedia_recognition_system_v2 import WikipediaRecognitionSystemV2

class BatchWikipediaProcessor:
    """バッチ処理用Wikipediaプロセッサー"""
    
    def __init__(self, max_workers=5):
        """
        初期化
        
        Args:
            max_workers: 並列処理のワーカー数（デフォルト5）
        """
        self.max_workers = max_workers
        self.wiki_system = WikipediaRecognitionSystemV2()
        self.results_lock = Lock()
        self.progress_lock = Lock()
        self.results = []
        self.processed_count = 0
        self.cache_hits = 0
        self.cache_dir = Path("cache/wikipedia")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    def get_cache_key(self, name):
        """キャッシュキーを生成"""
        return hashlib.md5(name.encode('utf-8')).hexdigest()
    
    def check_cache(self, name):
        """キャッシュをチェック"""
        cache_key = self.get_cache_key(name)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 成功したキャッシュのみ使用（失敗は再試行）
                    if data.get('found', False):
                        self.cache_hits += 1
                        return data
            except:
                pass
        return None
    
    def process_single_record(self, record):
        """単一レコードを処理"""
        try:
            name = record['person_name']
            
            # キャッシュチェック
            cached = self.check_cache(name)
            if cached:
                with self.progress_lock:
                    self.processed_count += 1
                    if self.processed_count % 10 == 0:
                        logger.info(f"進捗: {self.processed_count}/{self.total_records} ({self.processed_count/self.total_records*100:.1f}%) - キャッシュヒット: {self.cache_hits}")
                
                return {
                    'person_id': record['person_id'],
                    'person_name': name,
                    'old_score': record['current_score'],
                    'new_score': cached.get('recognition_score', 0),
                    'wikipedia_found': cached.get('found', False),
                    'wikipedia_page': cached.get('page_title', ''),
                    'successful_variant': cached.get('successful_variant', ''),
                    'should_delete': not cached.get('found', False) and cached.get('recognition_score', 0) < 3.0,
                    'improvement': cached.get('recognition_score', 0) - record['current_score'],
                    'from_cache': True
                }
            
            # Wikipedia検索
            result = self.wiki_system.search_wikipedia(name)
            
            new_score = result.get('recognition_score', 0)
            found = result.get('found', False)
            
            with self.progress_lock:
                self.processed_count += 1
                if self.processed_count % 10 == 0:
                    logger.info(f"進捗: {self.processed_count}/{self.total_records} ({self.processed_count/self.total_records*100:.1f}%) - キャッシュヒット: {self.cache_hits}")
            
            return {
                'person_id': record['person_id'],
                'person_name': name,
                'old_score': record['current_score'],
                'new_score': new_score,
                'wikipedia_found': found,
                'wikipedia_page': result.get('page_title', ''),
                'successful_variant': result.get('successful_variant', ''),
                'should_delete': not found and new_score < 3.0,
                'improvement': new_score - record['current_score'],
                'from_cache': False
            }
            
        except Exception as e:
            logger.error(f"エラー処理中: {record.get('person_name', 'Unknown')} - {e}")
            return None
    
    def process_batch(self, records):
        """バッチ処理を実行"""
        self.total_records = len(records)
        self.processed_count = 0
        self.cache_hits = 0
        results = []
        
        logger.info(f"バッチ処理開始: {self.total_records}件")
        logger.info(f"並列ワーカー数: {self.max_workers}")
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # タスクを投入
            future_to_record = {
                executor.submit(self.process_single_record, record): record 
                for record in records
            }
            
            # 結果を収集
            for future in as_completed(future_to_record):
                result = future.result()
                if result:
                    with self.results_lock:
                        results.append(result)
        
        elapsed_time = time.time() - start_time
        
        logger.info("="*60)
        logger.info(f"バッチ処理完了")
        logger.info(f"処理時間: {elapsed_time:.1f}秒")
        logger.info(f"処理速度: {self.total_records/elapsed_time:.1f}件/秒")
        logger.info(f"キャッシュヒット率: {self.cache_hits/self.total_records*100:.1f}%")
        logger.info("="*60)
        
        return results

def identify_priority_records(df, limit=None):
    """優先度の高いレコードを特定"""
    
    priority_records = []
    
    # 有名人リスト（確実にWikipediaがあるはず）
    famous_names = [
        "ヒカキン", "HIKAKIN",
        "はじめしゃちょー",
        "フィッシャーズ",
        "東海オンエア",
        "水溜りボンド",
        "吉田美和", "DREAMS COME TRUE",
        "PSY", "サイ",
        "ル・セラフィム", "LE SSERAFIM",
        "BTS", "防弾少年団",
        "TWICE", "トゥワイス"
    ]
    
    # 1. 有名人で削除対象
    for name in famous_names:
        matches = df[
            (df['name'].str.contains(name, case=False, na=False)) & 
            (df['should_delete'] == True)
        ]
        for idx, row in matches.iterrows():
            priority_records.append({
                'person_id': row['person_id'],
                'person_name': row['name'],
                'current_score': row.get('recognition_score', 0),
                'priority': 'high',
                'reason': f'有名人: {name}'
            })
    
    # 2. 括弧付き名前
    parentheses = df[
        df['name'].str.contains(r'[（(]', na=False) &
        (df['should_delete'] == True)
    ]
    
    for idx, row in parentheses.iterrows():
        priority_records.append({
            'person_id': row['person_id'],
            'person_name': row['name'],
            'current_score': row.get('recognition_score', 0),
            'priority': 'medium',
            'reason': '括弧付き名前'
        })
    
    # 重複を除去
    seen = set()
    unique_records = []
    for record in priority_records:
        if record['person_id'] not in seen:
            seen.add(record['person_id'])
            unique_records.append(record)
    
    # 制限を適用
    if limit:
        unique_records = unique_records[:limit]
    
    logger.info(f"優先レコード: {len(unique_records)}件")
    return unique_records

def analyze_results(df_results):
    """結果を分析"""
    
    logger.info("="*60)
    logger.info("📊 バッチ処理結果分析")
    logger.info("="*60)
    
    # 基本統計
    total = len(df_results)
    found = df_results['wikipedia_found'].sum()
    improved = len(df_results[df_results['improvement'] > 0])
    saved = len(df_results[(df_results['old_score'] == 0) & (df_results['new_score'] > 0)])
    from_cache = df_results['from_cache'].sum() if 'from_cache' in df_results.columns else 0
    
    logger.info(f"処理件数: {total}")
    logger.info(f"Wikipedia発見: {found} ({found/total*100:.1f}%)")
    logger.info(f"スコア改善: {improved} ({improved/total*100:.1f}%)")
    logger.info(f"削除から救済: {saved} ({saved/total*100:.1f}%)")
    logger.info(f"キャッシュ使用: {from_cache} ({from_cache/total*100:.1f}%)" if from_cache > 0 else "キャッシュ使用: 0")
    
    # 改善例
    if saved > 0:
        logger.info("\n✅ 削除から救済された例（上位5件）:")
        for _, row in df_results[
            (df_results['old_score'] == 0) & 
            (df_results['new_score'] > 0)
        ].head(5).iterrows():
            logger.info(f"  - {row['person_name']}: {row['old_score']:.0f} → {row['new_score']:.1f}")
    
    # 統計
    avg_improvement = df_results['improvement'].mean()
    max_improvement = df_results['improvement'].max()
    
    logger.info(f"\n📈 統計:")
    logger.info(f"  平均改善: +{avg_improvement:.2f}")
    logger.info(f"  最大改善: +{max_improvement:.1f}")

def main():
    """メイン処理"""
    
    logger.info("🚀 Wikipedia検索バッチ処理システム")
    logger.info("="*60)
    
    # データ読み込み
    csv_file = "/Users/admin/Documents/AIUELAB/001-final-hourglass/recognition_results_ALL_20250908_224635.csv"
    
    try:
        df = pd.read_csv(csv_file, encoding='utf-8-sig')
        logger.info(f"データ読み込み: {len(df)}件")
    except Exception as e:
        logger.error(f"データ読み込みエラー: {e}")
        return
    
    # 優先レコード特定（最初の50件でテスト）
    priority_records = identify_priority_records(df, limit=50)
    
    if not priority_records:
        logger.info("処理対象レコードがありません")
        return
    
    # バッチ処理実行
    processor = BatchWikipediaProcessor(max_workers=5)
    results = processor.process_batch(priority_records)
    
    # 結果をDataFrame化
    df_results = pd.DataFrame(results)
    
    # 分析
    analyze_results(df_results)
    
    # 結果保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"batch_processed_{timestamp}.csv"
    df_results.to_csv(output_file, index=False, encoding='utf-8-sig')
    logger.info(f"\n✅ 結果保存: {output_file}")
    
    # 統計情報保存
    stats = {
        'timestamp': timestamp,
        'total_processed': len(df_results),
        'wikipedia_found': int(df_results['wikipedia_found'].sum()),
        'saved_from_deletion': len(df_results[(df_results['old_score'] == 0) & (df_results['new_score'] > 0)]),
        'average_improvement': float(df_results['improvement'].mean()),
        'max_improvement': float(df_results['improvement'].max()),
        'cache_hit_rate': float(processor.cache_hits / len(priority_records) * 100) if len(priority_records) > 0 else 0
    }
    
    stats_file = f"batch_stats_{timestamp}.json"
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    logger.info(f"統計情報: {stats_file}")

if __name__ == "__main__":
    main()