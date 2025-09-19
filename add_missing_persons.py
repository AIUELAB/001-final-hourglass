#!/usr/bin/env python3
"""
不足している重要人物をデータベースに追加
Wikipedia APIで情報を収集し、知名度スコアを計算
"""

import pandas as pd
import csv
from datetime import datetime
import logging
from pathlib import Path
import sys
from typing import Dict, List, Tuple
import time

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)
logger = logging.getLogger(__name__)

# システムをインポート
sys.path.append(str(Path(__file__).parent))
from wikipedia_recognition_system_v2 import WikipediaRecognitionSystemV2
from special_category_evaluator_v2 import SpecialCategoryEvaluatorV2
from must_add_persons import MustAddPersons

class PersonAdder:
    """人物追加クラス"""
    
    def __init__(self, existing_database_file: str):
        """
        初期化
        
        Args:
            existing_database_file: 既存データベースファイル
        """
        self.existing_db_file = existing_database_file
        self.wikipedia_system = WikipediaRecognitionSystemV2()
        self.category_evaluator = SpecialCategoryEvaluatorV2()
        self.must_add = MustAddPersons()
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 既存データベースを読み込み
        logger.info(f"既存データベース読み込み: {existing_database_file}")
        self.existing_df = pd.read_csv(existing_database_file, encoding='utf-8-sig')
        logger.info(f"既存レコード数: {len(self.existing_df)}")
        
        # 統計
        self.stats = {
            'total_to_add': 0,
            'added_successfully': 0,
            'already_exists': 0,
            'wikipedia_found': 0,
            'wikipedia_not_found': 0,
            'categories': {}
        }
    
    def check_existing(self, name: str) -> bool:
        """既存データベースに存在するかチェック"""
        return any(name in str(n) for n in self.existing_df['name'].values)
    
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
        
        # Wikipedia情報を取得
        logger.debug(f"Wikipedia検索: {name}")
        wikipedia_result = self.wikipedia_system.search_wikipedia(name)
        wikipedia_found = wikipedia_result.get('found', False)
        wikipedia_page = wikipedia_result.get('page_title', '')
        
        if wikipedia_found:
            # Wikipediaから知名度スコアを計算
            score = self.wikipedia_system.calculate_recognition_score(wikipedia_result)
            self.stats['wikipedia_found'] += 1
            logger.info(f"  ✅ {name}: Wikipedia発見 (スコア: {score:.1f})")
        else:
            # Wikipediaがない場合は最低スコアを使用
            score = min_score
            self.stats['wikipedia_not_found'] += 1
            logger.info(f"  ⚠️ {name}: Wikipedia未発見 (最低スコア: {score:.1f})")
            wikipedia_page = ""
        
        # 特別カテゴリ評価
        final_score, reason = self.category_evaluator.evaluate(
            name=name,
            wikipedia_page=wikipedia_page,
            current_score=score
        )
        
        # データ作成
        person_data = {
            'person_id': self.must_add.generate_person_id(
                self.stats['added_successfully'], 
                base=200000  # 新規追加は200000番台
            ),
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
            'added_date': datetime.now().isoformat()
        }
        
        return person_data
    
    def add_all_persons(self):
        """全必須追加人物を処理"""
        
        logger.info("=" * 60)
        logger.info("🎯 人物追加処理開始")
        logger.info("=" * 60)
        
        # 必須追加人物リストを取得
        all_persons = self.must_add.get_all_persons()
        self.stats['total_to_add'] = len(all_persons)
        logger.info(f"追加対象: {self.stats['total_to_add']}名")
        
        # 追加する人物データ
        new_persons = []
        
        # カテゴリ別に処理
        categories = {
            '国民栄誉賞': self.must_add.national_honor_recipients,
            '歴代総理': self.must_add.prime_ministers,
            '漫画家': self.must_add.manga_artists,
            '社会貢献者': self.must_add.social_contributors,
            '起業家': self.must_add.modern_innovators,
            'エンタメ': self.must_add.entertainment_legends,
            'スポーツ': self.must_add.new_sports_stars,
            '文化人': self.must_add.cultural_figures,
            '世界的日本人': self.must_add.global_japanese
        }
        
        for category_name, person_list in categories.items():
            logger.info(f"\n📂 {category_name}カテゴリ処理中...")
            category_count = 0
            
            for name, occupation, description, min_score in person_list:
                # 既存チェック
                if self.check_existing(name):
                    logger.debug(f"  ⏭️ {name}: 既存のためスキップ")
                    self.stats['already_exists'] += 1
                    continue
                
                # 人物データを処理
                try:
                    person_data = self.process_person(
                        name, occupation, description, 
                        min_score, category_name
                    )
                    new_persons.append(person_data)
                    self.stats['added_successfully'] += 1
                    category_count += 1
                    
                    # API制限対策
                    time.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"  ❌ {name}: 処理エラー - {e}")
                    continue
            
            self.stats['categories'][category_name] = category_count
            logger.info(f"  {category_name}: {category_count}名追加")
        
        # 新規人物データをデータフレーム化
        if new_persons:
            new_df = pd.DataFrame(new_persons)
            
            # 既存データベースと結合
            logger.info("\n📊 データベース結合中...")
            combined_df = pd.concat([self.existing_df, new_df], ignore_index=True)
            
            # ソート（スコア降順）
            combined_df = combined_df.sort_values('recognition_score', ascending=False)
            
            # 出力ファイル
            output_file = f"database_expanded_{self.timestamp}.csv"
            combined_df.to_csv(output_file, index=False, encoding='utf-8-sig')
            
            logger.info(f"✅ 拡張データベース出力: {output_file}")
            logger.info(f"  総レコード数: {len(combined_df)}")
            
            # 新規追加分のみも出力
            added_file = f"newly_added_persons_{self.timestamp}.csv"
            new_df.to_csv(added_file, index=False, encoding='utf-8-sig')
            logger.info(f"📋 新規追加リスト: {added_file}")
            
            return output_file, added_file
        else:
            logger.warning("追加する人物がありませんでした")
            return None, None
    
    def show_statistics(self):
        """統計を表示"""
        
        logger.info("\n" + "=" * 60)
        logger.info("📊 追加処理統計")
        logger.info("=" * 60)
        
        logger.info(f"追加対象総数: {self.stats['total_to_add']}名")
        logger.info(f"追加成功: {self.stats['added_successfully']}名")
        logger.info(f"既存スキップ: {self.stats['already_exists']}名")
        logger.info(f"Wikipedia発見: {self.stats['wikipedia_found']}名")
        logger.info(f"Wikipedia未発見: {self.stats['wikipedia_not_found']}名")
        
        if self.stats['categories']:
            logger.info("\nカテゴリ別追加数:")
            for category, count in self.stats['categories'].items():
                logger.info(f"  {category}: {count}名")
        
        # 成功率
        if self.stats['total_to_add'] > 0:
            success_rate = (self.stats['added_successfully'] / 
                          (self.stats['total_to_add'] - self.stats['already_exists'])) * 100
            logger.info(f"\n追加成功率: {success_rate:.1f}%")

def main():
    """メイン処理"""
    import argparse
    
    parser = argparse.ArgumentParser(description='不足人物追加処理')
    parser.add_argument('--input', type=str,
                       default='database_special_evaluated_20250910_042310.csv',
                       help='既存データベースファイル')
    parser.add_argument('--test', action='store_true',
                       help='テストモード（最初の5名のみ処理）')
    
    args = parser.parse_args()
    
    # 処理実行
    adder = PersonAdder(args.input)
    
    if args.test:
        logger.info("🧪 テストモード: 最初の5名のみ処理")
        # テスト用に人物リストを制限
        adder.must_add.national_honor_recipients = adder.must_add.national_honor_recipients[:2]
        adder.must_add.prime_ministers = adder.must_add.prime_ministers[:2]
        adder.must_add.manga_artists = adder.must_add.manga_artists[:1]
        adder.must_add.social_contributors = []
        adder.must_add.modern_innovators = []
        adder.must_add.entertainment_legends = []
        adder.must_add.new_sports_stars = []
        adder.must_add.cultural_figures = []
        adder.must_add.global_japanese = []
    
    # 追加処理
    output_file, added_file = adder.add_all_persons()
    
    # 統計表示
    adder.show_statistics()
    
    logger.info("\n🎉 全処理完了")

if __name__ == "__main__":
    main()