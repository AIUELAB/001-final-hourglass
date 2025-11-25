#!/usr/bin/env python3
"""
特別カテゴリ評価を適用してデータベースを再評価
"""

import pandas as pd
from datetime import datetime
import logging
from pathlib import Path
import sys

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)
logger = logging.getLogger(__name__)

# システムをインポート
sys.path.append(str(Path(__file__).parent))
from special_category_evaluator import SpecialCategoryEvaluator

class SpecialCategoryProcessor:
    """特別カテゴリ処理クラス"""

    def __init__(self, deletion_threshold: float = 4.0):
        """
        初期化

        Args:
            deletion_threshold: 削除しきい値（デフォルト4.0）
        """
        self.evaluator = SpecialCategoryEvaluator()
        self.deletion_threshold = deletion_threshold
        self.stats = {
            'total_processed': 0,
            'score_improved': 0,
            'saved_from_deletion': 0,
            'special_categories': {},
            'new_deletion_count': 0
        }

    def process_database(self, input_file: str):
        """データベースを処理"""

        logger.info("="*60)
        logger.info("🎯 特別カテゴリ評価適用開始")
        logger.info("="*60)

        # データ読み込み
        logger.info(f"データ読み込み: {input_file}")
        df = pd.read_csv(input_file, encoding='utf-8-sig')
        total_records = len(df)
        logger.info(f"総レコード数: {total_records}")

        # 現在の削除候補数
        old_deletion_count = (df['recognition_score'] < self.deletion_threshold).sum()
        logger.info(f"現在の削除候補（<{self.deletion_threshold}）: {old_deletion_count}件")

        # 処理対象の例を表示
        logger.info("\n📋 処理対象例:")
        target_names = [
            'ガンジー', '松本薫', '斎藤司', 'ランジャタイ',
            'LUNA SEA', '水溜りボンド', '井上貴子'
        ]
        for target in target_names:
            matches = df[df['name'].str.contains(target, na=False)]
            if not matches.empty:
                for idx, row in matches.head(2).iterrows():
                    logger.info(f"  - {row['person_id']}: {row['name']} (現在: {row['recognition_score']})")

        # 各レコードを処理
        logger.info("\n🔄 特別カテゴリ評価実行中...")
        results = []

        for idx, row in df.iterrows():
            # 進捗表示
            if idx % 500 == 0:
                logger.info(f"  処理中: {idx}/{total_records}")

            # 特別カテゴリ評価
            new_score, reason = self.evaluator.evaluate(
                name=row['name'],
                wikipedia_page=row.get('wikipedia_page', ''),
                current_score=row['recognition_score']
            )

            # スコアが改善された場合
            if new_score > row['recognition_score']:
                self.stats['score_improved'] += 1

                # カテゴリ別統計
                if reason not in self.stats['special_categories']:
                    self.stats['special_categories'][reason] = 0
                self.stats['special_categories'][reason] += 1

                # 削除から救済された場合
                if row['recognition_score'] < self.deletion_threshold and new_score >= self.deletion_threshold:
                    self.stats['saved_from_deletion'] += 1
                    logger.debug(f"  救済: {row['name']} ({row['recognition_score']:.1f} → {new_score:.1f})")

            # 結果を保存
            result = row.to_dict()
            result['original_score'] = row['recognition_score']
            result['recognition_score'] = new_score
            result['evaluation_reason'] = reason
            result['score_improvement'] = new_score - row['recognition_score']
            result['should_delete'] = new_score < self.deletion_threshold
            results.append(result)

            self.stats['total_processed'] += 1

        # データフレーム作成
        df_results = pd.DataFrame(results)

        # 新しい削除候補数
        self.stats['new_deletion_count'] = df_results['should_delete'].sum()

        # 重要人物の確認
        logger.info("\n✅ 重要人物の評価結果:")
        important_people = [
            ('P000439', 'ガンジー'),
            ('P003743', '松本薫'),
            ('P003405', '斎藤司'),
            ('P001927', '伊藤幸司 (ランジャタイ)'),
            ('P004532', '真矢 (LUNA SEA)'),
            ('P000417', 'カンタ (水溜りボンド)'),
            ('P005510', '井上貴子')
        ]

        for person_id, name in important_people:
            person = df_results[df_results['person_id'] == person_id]
            if not person.empty:
                row = person.iloc[0]
                status = "✅ 保護" if not row['should_delete'] else "❌ 削除対象"
                logger.info(f"  {name}: {row['original_score']:.1f} → {row['recognition_score']:.1f} ({row['evaluation_reason']}) {status}")

        # 結果ファイル保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"database_special_evaluated_{timestamp}.csv"
        df_results.to_csv(output_file, index=False, encoding='utf-8-sig')

        # 統計レポート
        self.show_statistics(old_deletion_count)

        logger.info(f"\n✅ 評価済みデータベース: {output_file}")

        return output_file

    def show_statistics(self, old_deletion_count: int):
        """統計を表示"""

        logger.info("\n" + "="*60)
        logger.info("📊 処理統計")
        logger.info("="*60)

        logger.info(f"処理件数: {self.stats['total_processed']}")
        logger.info(f"スコア改善: {self.stats['score_improved']}件")
        logger.info(f"削除から救済: {self.stats['saved_from_deletion']}件")

        # 削除候補の変化
        logger.info(f"\n削除候補の変化:")
        logger.info(f"  改善前: {old_deletion_count}件")
        logger.info(f"  改善後: {self.stats['new_deletion_count']}件")
        logger.info(f"  削減数: {old_deletion_count - self.stats['new_deletion_count']}件")

        # カテゴリ別改善
        if self.stats['special_categories']:
            logger.info(f"\nカテゴリ別改善:")
            for category, count in sorted(self.stats['special_categories'].items(),
                                         key=lambda x: x[1], reverse=True)[:10]:
                logger.info(f"  {category}: {count}件")

def main():
    """メイン処理"""
    import argparse

    parser = argparse.ArgumentParser(description='特別カテゴリ評価適用')
    parser.add_argument('--input', type=str,
                       default='database_cleaned_20250910_033514.csv',
                       help='入力CSVファイル')
    parser.add_argument('--threshold', type=float,
                       default=4.0,
                       help='削除しきい値（デフォルト: 4.0）')

    args = parser.parse_args()

    # 処理実行
    processor = SpecialCategoryProcessor(deletion_threshold=args.threshold)
    output_file = processor.process_database(args.input)

    logger.info("\n🎉 全処理完了")

if __name__ == "__main__":
    main()
