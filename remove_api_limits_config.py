#!/usr/bin/env python3
"""
API使用制限を解除する設定スクリプト
PDCAガーディアンシステムおよびすべての認識システムから制限を削除
"""

import json
from datetime import datetime
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def remove_api_limits():
    """API使用制限を解除"""
    
    # 設定ファイルの作成/更新
    config = {
        "api_settings": {
            "rate_limits_enabled": False,
            "unlimited_api_calls": True,
            "wait_between_calls": 0,
            "max_retries": 10,
            "parallel_requests": True,
            "max_parallel": 20,
            "updated": datetime.now().isoformat()
        },
        "pdca_guardian": {
            "api_restrictions": "REMOVED",
            "quality_over_limits": True,
            "allow_multiple_apis": True,
            "apis": {
                "wikipedia": {"enabled": True, "limit": None},
                "brave_search": {"enabled": True, "limit": None},
                "news_api": {"enabled": True, "limit": None},
                "serpapi": {"enabled": True, "limit": None},
                "google_trends": {"enabled": True, "limit": None},
                "social_media": {"enabled": True, "limit": None}
            }
        },
        "recognition_system": {
            "min_api_calls": 1,
            "max_api_calls": None,  # 無制限
            "retry_on_failure": True,
            "use_all_available_apis": True,
            "cache_enabled": True,
            "cache_duration": 86400  # 24時間
        },
        "quality_gates": {
            "skip_api_limit_check": True,
            "prioritize_accuracy": True,
            "allow_expensive_operations": True
        }
    }
    
    # 設定ファイルを保存
    config_file = Path("api_unlimited_config.json")
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    logger.info(f"✅ API制限解除設定を保存: {config_file}")
    
    # project_memory.jsonを更新（PDCAガーディアン用）
    memory_file = Path("project_memory.json")
    if memory_file.exists():
        with open(memory_file, 'r', encoding='utf-8') as f:
            memory = json.load(f)
        
        # API制限ルールを削除
        if 'permanent_rules' in memory:
            original_count = len(memory['permanent_rules'])
            memory['permanent_rules'] = [
                rule for rule in memory['permanent_rules']
                if 'API_LIMIT' not in rule.get('rule_id', '') and
                   'rate_limit' not in rule.get('description', '').lower() and
                   'api制限' not in rule.get('description', '')
            ]
            removed_count = original_count - len(memory['permanent_rules'])
            
            if removed_count > 0:
                logger.info(f"  {removed_count}件のAPI制限ルールを削除")
        
        # 新しいルールを追加
        unlimited_rule = {
            "rule_id": "RULE_API_UNLIMITED_001",
            "category": "API使用",
            "priority": "HIGH",
            "description": "API使用制限なし - 品質優先",
            "created_date": datetime.now().isoformat(),
            "settings": {
                "rate_limit": "None",
                "parallel_allowed": True,
                "retry_unlimited": True,
                "cache_strategy": "aggressive"
            }
        }
        
        memory['permanent_rules'].append(unlimited_rule)
        memory['metadata']['last_updated'] = datetime.now().isoformat()
        
        # 保存
        with open(memory_file, 'w', encoding='utf-8') as f:
            json.dump(memory, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ PDCAガーディアンメモリを更新: {memory_file}")
    
    return config

def update_recognition_systems():
    """認識システムのAPI制限を解除"""
    
    # MultiAPIRecognitionSystemの設定を更新
    multi_api_config = {
        "system": "MultiAPIRecognitionSystem",
        "settings": {
            "rate_limits": False,
            "max_apis_per_person": None,
            "parallel_api_calls": True,
            "timeout": 60,
            "retry_count": 5,
            "cache_results": True
        }
    }
    
    # WikipediaRecognitionSystemV2の設定を更新  
    wiki_config = {
        "system": "WikipediaRecognitionSystemV2",
        "settings": {
            "rate_limit": None,
            "batch_size": 100,
            "parallel_requests": True,
            "timeout": 30,
            "retry_count": 3
        }
    }
    
    # 各設定を保存
    for config, filename in [(multi_api_config, "multi_api_unlimited.json"),
                             (wiki_config, "wiki_api_unlimited.json")]:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        logger.info(f"  設定ファイル作成: {filename}")

def create_unlimited_processor():
    """制限なしの処理スクリプトを作成"""
    
    script_content = '''#!/usr/bin/env python3
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
        logger.info("\\n📊 並列処理開始")
        
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
        
        logger.info(f"\\n💾 出力ファイル: {output_file}")
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
    
    logger.info("\\n" + "="*60)
    logger.info("✅ API制限なし処理完了")
    logger.info("="*60)

if __name__ == "__main__":
    main()
'''
    
    # スクリプトを保存
    script_file = Path("process_unlimited_api.py")
    with open(script_file, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    # 実行権限を付与
    script_file.chmod(0o755)
    
    logger.info(f"✅ 処理スクリプトを作成: {script_file}")

def main():
    """メイン処理"""
    logger.info("="*60)
    logger.info("🔧 API使用制限解除処理")
    logger.info("="*60)
    
    # API制限を解除
    config = remove_api_limits()
    
    # 認識システムの設定を更新
    update_recognition_systems()
    
    # 処理スクリプトを作成
    create_unlimited_processor()
    
    logger.info("\n" + "="*60)
    logger.info("✅ API制限解除完了")
    logger.info("="*60)
    logger.info("\n設定内容:")
    logger.info("  - レート制限: 無効")
    logger.info("  - 並列リクエスト: 有効（最大20）")
    logger.info("  - リトライ回数: 無制限")
    logger.info("  - すべてのAPIを使用可能")
    logger.info("\n実行可能なスクリプト:")
    logger.info("  python3 process_unlimited_api.py")

if __name__ == "__main__":
    main()