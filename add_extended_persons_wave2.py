#!/usr/bin/env python3
"""
拡張人物リスト第2波をデータベースに追加
目標: 500名追加を達成するため追加200名以上を処理
"""

import pandas as pd
import csv
from datetime import datetime
import logging
from pathlib import Path
import sys
import time
from typing import Dict, List, Tuple

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)
logger = logging.getLogger(__name__)

# システムをインポート
sys.path.append(str(Path(__file__).parent))
from multi_api_recognition_system import MultiAPIRecognitionSystem
from extended_persons_wave2 import ExtendedPersonsWave2
from special_category_evaluator_v2 import SpecialCategoryEvaluatorV2

class ExtendedPersonAdderWave2:
    """拡張人物追加クラス第2波"""
    
    def __init__(self, existing_database_file: str):
        """
        初期化
        
        Args:
            existing_database_file: 既存データベースファイル
        """
        self.existing_db_file = existing_database_file
        self.multi_api_system = MultiAPIRecognitionSystem()
        self.category_evaluator = SpecialCategoryEvaluatorV2()
        self.extended_persons = ExtendedPersonsWave2()
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 既存データベースを読み込み
        logger.info(f"既存データベース読み込み: {existing_database_file}")
        self.existing_df = pd.read_csv(existing_database_file, encoding='utf-8-sig')
        logger.info(f"既存レコード数: {len(self.existing_df)}")
        
        # 次のperson_idを決定
        existing_ids = self.existing_df['person_id'].values
        max_id = 200000  # デフォルト開始値
        for pid in existing_ids:
            if pid.startswith('P2'):
                try:
                    num = int(pid[1:])
                    max_id = max(max_id, num)
                except:
                    pass
        self.next_id = max_id + 1
        logger.info(f"次のperson_id開始値: P{self.next_id}")
        
        # 統計
        self.stats = {
            'total_to_add': 0,
            'added_successfully': 0,
            'already_exists': 0,
            'api_found': 0,
            'api_not_found': 0,
            'categories': {}
        }
    
    def generate_person_id(self) -> str:
        """新しいperson_idを生成"""
        pid = f"P{self.next_id}"
        self.next_id += 1
        return pid
    
    def check_existing(self, name: str) -> bool:
        """既存データベースに存在するかチェック"""
        # 完全一致チェック
        if any(name == str(n) for n in self.existing_df['name'].values):
            return True
        # 部分一致チェック（括弧内除外）
        base_name = name.split('(')[0].strip() if '(' in name else name
        return any(base_name == str(n).split('(')[0].strip() for n in self.existing_df['name'].values)
    
    def process_person(self, name: str, occupation: str, 
                       description: str, min_score: float, 
                       category: str) -> Dict:
        """
        人物を処理してデータを生成
        
        Args:
            name: 人物名
            occupation: 職業
            description: 説明
            min_score: 最低スコア
            category: カテゴリ
            
        Returns:
            人物データ辞書
        """
        
        # マルチAPIで包括的スコアを計算
        logger.debug(f"マルチAPI検索: {name}")
        final_score, details = self.multi_api_system.calculate_comprehensive_score(
            name, occupation, description, min_score
        )
        
        wikipedia_found = details.get('wikipedia', {}).get('found', False)
        wikipedia_page = details.get('wikipedia', {}).get('page_title', '')
        
        if wikipedia_found or details.get('brave', {}).get('found', False):
            self.stats['api_found'] += 1
            logger.info(f"  ✅ {name}: スコア {final_score:.1f} (Wiki: {wikipedia_found}, Web: {details.get('brave', {}).get('result_count', 0)}件)")
        else:
            self.stats['api_not_found'] += 1
            logger.info(f"  ⚠️ {name}: 最低スコア適用 {final_score:.1f}")
        
        # 特別カテゴリ評価
        if wikipedia_page:
            final_score, reason = self.category_evaluator.evaluate(
                name=name,
                wikipedia_page=wikipedia_page,
                current_score=final_score
            )
        else:
            reason = f"カテゴリ: {category}"
        
        # データ作成
        person_data = {
            'person_id': self.generate_person_id(),
            'name': name,
            'occupation': occupation,
            'description': description,
            'category': category,
            'recognition_score': final_score,
            'wikipedia_found': wikipedia_found,
            'wikipedia_page': wikipedia_page,
            'evaluation_reason': reason,
            'original_min_score': min_score,
            'should_delete': final_score < 4.0,
            'protected': final_score >= 7.0,
            'added_date': datetime.now().isoformat(),
            'api_details': str(details.get('scores', {}))  # API詳細スコア
        }
        
        return person_data
    
    def add_all_persons(self, limit: int = None):
        """
        全拡張人物を処理
        
        Args:
            limit: 処理する最大人数（Noneで全員）
        """
        
        logger.info("=" * 60)
        logger.info("🎯 拡張人物追加処理開始【第2波】")
        logger.info("=" * 60)
        
        # 拡張人物リストを取得
        all_persons = self.extended_persons.get_all_persons()
        
        if limit:
            all_persons = all_persons[:limit]
        
        self.stats['total_to_add'] = len(all_persons)
        logger.info(f"追加対象: {self.stats['total_to_add']}名")
        
        # API状況確認
        api_status = self.multi_api_system.get_api_status()
        logger.info("API使用可能状況:")
        for api, status in api_status.items():
            logger.info(f"  {api}: {status['remaining']}件")
        
        # 追加する人物データ
        new_persons = []
        
        # 各人物を処理
        for i, (name, occupation, description, min_score, category) in enumerate(all_persons):
            # 進捗表示
            if (i + 1) % 10 == 0:
                logger.info(f"進捗: {i + 1}/{len(all_persons)}")
            
            # 既存チェック
            if self.check_existing(name):
                logger.debug(f"  ⏭️ {name}: 既存のためスキップ")
                self.stats['already_exists'] += 1
                continue
            
            # 人物データを処理
            try:
                person_data = self.process_person(
                    name, occupation, description, 
                    min_score, category
                )
                new_persons.append(person_data)
                self.stats['added_successfully'] += 1
                
                # カテゴリ統計
                if category not in self.stats['categories']:
                    self.stats['categories'][category] = 0
                self.stats['categories'][category] += 1
                
                # API制限対策（レート制限を考慮）
                time.sleep(0.3)
                
            except Exception as e:
                logger.error(f"  ❌ {name}: 処理エラー - {e}")
                continue
        
        # 新規人物データをデータフレーム化
        if new_persons:
            new_df = pd.DataFrame(new_persons)
            
            # 既存データベースと結合
            logger.info("\n📊 データベース結合中...")
            combined_df = pd.concat([self.existing_df, new_df], ignore_index=True)
            
            # ソート（スコア降順）
            combined_df = combined_df.sort_values('recognition_score', ascending=False)
            
            # 出力ファイル
            output_file = f"database_extended_wave2_{self.timestamp}.csv"
            combined_df.to_csv(output_file, index=False, encoding='utf-8-sig')
            
            logger.info(f"✅ 拡張データベース出力: {output_file}")
            logger.info(f"  総レコード数: {len(combined_df)}")
            
            # 新規追加分のみも出力
            added_file = f"extended_added_persons_wave2_{self.timestamp}.csv"
            new_df.to_csv(added_file, index=False, encoding='utf-8-sig')
            logger.info(f"📋 新規追加リスト: {added_file}")
            
            return output_file, added_file
        else:
            logger.warning("追加する人物がありませんでした")
            return None, None
    
    def show_statistics(self):
        """統計を表示"""
        
        logger.info("\n" + "=" * 60)
        logger.info("📊 追加処理統計【第2波】")
        logger.info("=" * 60)
        
        logger.info(f"追加対象総数: {self.stats['total_to_add']}名")
        logger.info(f"追加成功: {self.stats['added_successfully']}名")
        logger.info(f"既存スキップ: {self.stats['already_exists']}名")
        logger.info(f"API情報発見: {self.stats['api_found']}名")
        logger.info(f"API情報なし: {self.stats['api_not_found']}名")
        
        if self.stats['categories']:
            logger.info("\nカテゴリ別追加数:")
            for category, count in sorted(self.stats['categories'].items()):
                logger.info(f"  {category}: {count}名")
        
        # 成功率
        if self.stats['total_to_add'] > 0:
            if self.stats['total_to_add'] - self.stats['already_exists'] > 0:
                success_rate = (self.stats['added_successfully'] / 
                              (self.stats['total_to_add'] - self.stats['already_exists'])) * 100
                logger.info(f"\n追加成功率: {success_rate:.1f}%")
        
        # API状況最終確認
        final_api_status = self.multi_api_system.get_api_status()
        logger.info("\nAPI使用統計:")
        for api, status in final_api_status.items():
            logger.info(f"  {api}: {status['used']}/{status['limit']} 使用")
        
        # 累計追加数
        logger.info("\n" + "=" * 60)
        logger.info("🏆 累計追加実績")
        logger.info("=" * 60)
        logger.info(f"第1波: 58名追加済み")
        logger.info(f"第2波: {self.stats['added_successfully']}名追加")
        logger.info(f"合計: {58 + self.stats['added_successfully']}名追加")
        logger.info(f"目標500名に対する達成率: {((58 + self.stats['added_successfully']) / 500) * 100:.1f}%")


def main():
    """メイン処理"""
    import argparse
    
    parser = argparse.ArgumentParser(description='拡張人物追加処理【第2波】')
    parser.add_argument('--input', type=str,
                       default='database_extended_20250910_094522.csv',
                       help='既存データベースファイル')
    parser.add_argument('--limit', type=int, default=None,
                       help='処理する最大人数（テスト用）')
    parser.add_argument('--test', action='store_true',
                       help='テストモード（最初の10名のみ処理）')
    
    args = parser.parse_args()
    
    # 処理実行
    adder = ExtendedPersonAdderWave2(args.input)
    
    if args.test:
        logger.info("🧪 テストモード: 最初の10名のみ処理")
        limit = 10
    else:
        limit = args.limit
    
    # 追加処理
    output_file, added_file = adder.add_all_persons(limit=limit)
    
    # 統計表示
    adder.show_statistics()
    
    logger.info("\n🎉 第2波処理完了")


if __name__ == "__main__":
    main()