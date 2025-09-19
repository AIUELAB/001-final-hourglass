#!/usr/bin/env python3
"""
API制限なしで全人物を再評価するスクリプト
"""

import pandas as pd
import logging
from datetime import datetime
from pathlib import Path
import sys
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.append(str(Path(__file__).parent))
from multi_api_recognition_system import MultiAPIRecognitionSystem

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# API制限解除設定を読み込み
with open('api_unlimited_config.json', 'r') as f:
    config = json.load(f)

class UnlimitedProcessor:
    """API制限なしの処理クラス"""
    
    def __init__(self, database_file: str):
        self.database_file = database_file
        self.df = pd.read_csv(database_file, encoding='utf-8-sig')
        self.multi_api = MultiAPIRecognitionSystem()
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.processed = 0
        self.improved = 0
        
        # 並列処理の設定
        self.max_workers = config['api_settings']['max_parallel']
        
        logger.info("="*60)
        logger.info("🚀 API制限なし処理モード")
        logger.info("="*60)
        logger.info(f"データベース: {database_file}")
        logger.info(f"レコード数: {len(self.df)}")
        logger.info(f"並列処理数: {self.max_workers}")
    
    def process_person(self, idx, row):
        """1人分を処理"""
        try:
            name = row['person_name_ja']
            current_score = row['recognition_score']
            
            # すべてのAPIを使用して評価
            score, details = self.multi_api.calculate_comprehensive_score(
                name=name,
                occupation=row.get('occupation', ''),
                description=row.get('description', ''),
                min_score=0  # 最低スコア制限なし
            )
            
            if score > current_score:
                return idx, score, details, True
            else:
                return idx, current_score, details, False
                
        except Exception as e:
            logger.error(f"エラー: {name} - {e}")
            return idx, current_score, {}, False
    
    def process_all_parallel(self):
        """全員を並列処理"""
        logger.info("\n📊 並列処理開始")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            
            # すべてのタスクを投入
            for idx, row in self.df.iterrows():
                future = executor.submit(self.process_person, idx, row)
                futures[future] = idx
            
            # 結果を収集
            for future in as_completed(futures):
                idx, score, details, improved = future.result()
                
                if improved:
                    self.df.at[idx, 'recognition_score'] = score
                    self.improved += 1
                
                self.processed += 1
                
                if self.processed % 100 == 0:
                    logger.info(f"  処理済み: {self.processed}/{len(self.df)} (改善: {self.improved})")
        
        logger.info(f"✅ 処理完了: {self.processed}件 (改善: {self.improved}件)")
    
    def save_results(self):
        """結果を保存"""
        output_file = f"database_unlimited_api_{self.timestamp}.csv"
        self.df.to_csv(output_file, index=False, encoding='utf-8-sig')
        
        logger.info(f"\n💾 出力ファイル: {output_file}")
        logger.info(f"  改善率: {(self.improved/self.processed)*100:.1f}%")
        
        return output_file

def main():
    """メイン処理"""
    import glob
    
    # 最新のデータベースを取得
    db_files = glob.glob("database_category_improved_*.csv")
    if not db_files:
        db_files = glob.glob("database_episode_format_*.csv")
    if not db_files:
        db_files = glob.glob("database_*.csv")
    
    if not db_files:
        logger.error("データベースファイルが見つかりません")
        return
    
    latest_db = sorted(db_files)[-1]
    
    # 処理実行
    processor = UnlimitedProcessor(latest_db)
    processor.process_all_parallel()
    output_file = processor.save_results()
    
    logger.info("\n" + "="*60)
    logger.info("✅ API制限なし処理完了")
    logger.info("="*60)

if __name__ == "__main__":
    main()
