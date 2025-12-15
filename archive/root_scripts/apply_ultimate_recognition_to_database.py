#!/usr/bin/env python3
"""
究極知名度選定システムによるデータベース再評価
Apply Ultimate Recognition System to Database

古いcalibrated_scoreを無視し、最新の多次元評価システムで
全レコードを再評価して削除候補を科学的に選定
"""

import os
import sys
import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import pandas as pd
from collections import defaultdict

# Ultimate Recognition Systemのインポート
from ultimate_recognition_system import (
    UltimateRecognitionSystem,
    PersonData,
    RecognitionScore,
    DeleteAction
)

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('recognition_evaluation.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DatabaseRecognitionEvaluator:
    """データベース全体の知名度再評価システム"""

    def __init__(self, database_path: str, output_dir: str = "削除候補"):
        """
        初期化

        Args:
            database_path: 評価対象のCSVファイルパス
            output_dir: 出力ディレクトリ
        """
        self.database_path = database_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # バックアップ作成
        self._create_backup()

        # Ultimate Recognition Systemの初期化
        logger.info("🚀 究極知名度選定システムを初期化中...")
        self.recognition_system = UltimateRecognitionSystem()

        # 統計情報
        self.stats = {
            'total': 0,
            'processed': 0,
            'errors': 0,
            'deleted_high': 0,
            'deleted_review': 0,
            'deleted_low': 0,
            'kept': 0,
            'protected': 0
        }

        # 結果格納
        self.results = []
        self.deletion_candidates = {
            'high': [],      # スコア < 3.0
            'review': [],    # スコア 3.0-4.0
            'low': []        # スコア 4.0-5.0
        }

        # 検証用有名人リスト
        self.verification_persons = [
            'HIKAKIN', 'ヒカキン',
            '大谷翔平', 'Ohtani',
            '安倍晋三', 'Abe Shinzo',
            'Ado', 'YOASOBI',
            '竈門炭治郎', '孫悟空'
        ]

    def _create_backup(self):
        """バックアップ作成"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = Path(f"backup_{timestamp}_{Path(self.database_path).name}")

        import shutil
        shutil.copy2(self.database_path, backup_path)
        logger.info(f"📦 バックアップ作成: {backup_path}")

    def load_database(self) -> pd.DataFrame:
        """データベース読み込み"""
        logger.info(f"📂 データベース読み込み: {self.database_path}")

        try:
            # UTF-8 with BOMで読み込み
            df = pd.read_csv(self.database_path, encoding='utf-8-sig')
            self.stats['total'] = len(df)
            logger.info(f"✅ {self.stats['total']}件のレコードを読み込みました")
            return df
        except Exception as e:
            logger.error(f"❌ データベース読み込みエラー: {e}")
            raise

    def evaluate_record(self, row: pd.Series) -> Tuple[float, DeleteAction, Dict]:
        """
        個別レコードの評価

        Returns:
            (スコア, アクション, 詳細情報)
        """
        try:
            # PersonDataオブジェクト作成
            person = PersonData(
                id=row.get('person_id', f"P{self.stats['processed']:06d}"),
                name=row.get('person_name', ''),
                name_en=row.get('person_name_display', ''),
                category=row.get('category', ''),
                birth_year=None,  # birth_yearフィールドがない場合
                description=row.get('occupation', ''),
                is_fictional=self._check_fictional(row),
                is_textbook=self._check_textbook(row)
            )

            # 知名度評価
            score, action = self.recognition_system.evaluate_person(person)

            # 詳細情報
            details = {
                'person_id': person.id,
                'name': person.name,
                'name_display': person.name_en,
                'category': person.category,
                'old_calibrated_score': row.get('name_recognition', 0),
                'new_recognition_score': score.total_score,
                'google_search_count': score.google_search_count,
                'sns_followers': score.sns_followers,
                'news_mentions': score.news_mentions,
                'wikipedia_exists': score.wikipedia_exists,
                'action': action.value,
                'confidence': score.confidence,
                'protection_reasons': ', '.join(score.protection_reasons) if score.protection_reasons else ''
            }

            return score.total_score, action, details

        except Exception as e:
            logger.error(f"❌ 評価エラー ({row.get('person_name', 'Unknown')}): {e}")
            self.stats['errors'] += 1
            return 0.0, DeleteAction.REVIEW, {'error': str(e)}

    def _check_fictional(self, row: pd.Series) -> bool:
        """架空キャラクターチェック"""
        extended_data = row.get('extended_data', '{}')
        if isinstance(extended_data, str):
            try:
                data = json.loads(extended_data)
                return data.get('is_fictional', 'FALSE') == 'TRUE'
            except:
                pass

        # カテゴリで判定
        category = row.get('category', '')
        return '架空' in category or 'キャラクター' in category

    def _check_textbook(self, row: pd.Series) -> bool:
        """教科書人物チェック"""
        name = row.get('person_name_ja', row.get('person_name', ''))

        textbook_persons = [
            '織田信長', '豊臣秀吉', '徳川家康', '聖徳太子',
            '紫式部', '源頼朝', '平清盛', '卑弥呼'
        ]

        return any(person in name for person in textbook_persons)

    def process_database(self, sample_size: Optional[int] = None):
        """
        データベース全体を処理

        Args:
            sample_size: テスト用のサンプルサイズ（Noneで全件）
        """
        logger.info("="*60)
        logger.info("🎯 知名度再評価開始")
        logger.info("="*60)

        # データ読み込み
        df = self.load_database()

        # サンプリング（テスト用）
        if sample_size:
            df = df.sample(min(sample_size, len(df)))
            logger.info(f"🔬 サンプルモード: {len(df)}件を処理")

        # 進捗表示の準備
        total = len(df)
        checkpoint = max(1, total // 20)  # 5%ごとに進捗表示

        # 各レコードを評価
        for idx, row in df.iterrows():
            self.stats['processed'] += 1

            # 進捗表示
            if self.stats['processed'] % checkpoint == 0:
                progress = (self.stats['processed'] / total) * 100
                logger.info(f"📊 進捗: {progress:.1f}% ({self.stats['processed']}/{total})")

            # 評価実行
            score, action, details = self.evaluate_record(row)

            # 結果格納
            result = {**row.to_dict(), **details}
            self.results.append(result)

            # アクション別に分類
            if action == DeleteAction.DELETE:
                if score < 3.0:
                    self.deletion_candidates['high'].append(result)
                    self.stats['deleted_high'] += 1
                elif score < 4.0:
                    self.deletion_candidates['review'].append(result)
                    self.stats['deleted_review'] += 1
                else:
                    self.deletion_candidates['low'].append(result)
                    self.stats['deleted_low'] += 1
            elif action == DeleteAction.REVIEW:
                self.deletion_candidates['review'].append(result)
                self.stats['deleted_review'] += 1
            elif action == DeleteAction.PROTECT:
                self.stats['protected'] += 1
            else:
                self.stats['kept'] += 1

            # 検証対象のチェック
            if any(v in row.get('person_name', '') or v in row.get('person_name_ja', '')
                   for v in self.verification_persons):
                logger.info(f"🔍 検証: {details['name']} → スコア: {score:.2f}, アクション: {action.value}")

        logger.info("✅ 評価完了")
        self._show_statistics()

    def _show_statistics(self):
        """統計情報表示"""
        logger.info("\n" + "="*60)
        logger.info("📊 評価結果統計")
        logger.info("="*60)

        total = self.stats['total']
        logger.info(f"総レコード数: {total:,}")
        logger.info(f"処理済み: {self.stats['processed']:,}")
        logger.info(f"エラー: {self.stats['errors']:,}")
        logger.info("")

        # 削除候補
        deleted_total = (self.stats['deleted_high'] +
                        self.stats['deleted_review'] +
                        self.stats['deleted_low'])
        logger.info(f"🗑️ 削除候補合計: {deleted_total:,} ({deleted_total/total*100:.1f}%)")
        logger.info(f"  - 高優先（<3.0）: {self.stats['deleted_high']:,} ({self.stats['deleted_high']/total*100:.1f}%)")
        logger.info(f"  - 要確認（3-4）: {self.stats['deleted_review']:,} ({self.stats['deleted_review']/total*100:.1f}%)")
        logger.info(f"  - 低優先（4-5）: {self.stats['deleted_low']:,} ({self.stats['deleted_low']/total*100:.1f}%)")
        logger.info("")

        # 保持・保護
        logger.info(f"✅ 保持: {self.stats['kept']:,} ({self.stats['kept']/total*100:.1f}%)")
        logger.info(f"🛡️ 保護: {self.stats['protected']:,} ({self.stats['protected']/total*100:.1f}%)")

    def save_results(self):
        """結果をCSVファイルに保存"""
        logger.info("\n📝 結果保存中...")

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # 1. 削除候補（高優先）
        if self.deletion_candidates['high']:
            high_path = self.output_dir / f"deletion_candidates_priority_HIGH_{timestamp}.csv"
            df_high = pd.DataFrame(self.deletion_candidates['high'])
            df_high = df_high.sort_values('new_recognition_score')
            df_high.to_csv(high_path, index=False, encoding='utf-8-sig')
            logger.info(f"✅ 高優先削除候補: {high_path} ({len(df_high)}件)")

        # 2. 要確認リスト
        if self.deletion_candidates['review']:
            review_path = self.output_dir / f"deletion_candidates_REVIEW_{timestamp}.csv"
            df_review = pd.DataFrame(self.deletion_candidates['review'])
            df_review = df_review.sort_values('new_recognition_score')
            df_review.to_csv(review_path, index=False, encoding='utf-8-sig')
            logger.info(f"✅ 要確認リスト: {review_path} ({len(df_review)}件)")

        # 3. 低優先削除候補
        if self.deletion_candidates['low']:
            low_path = self.output_dir / f"deletion_candidates_LOW_{timestamp}.csv"
            df_low = pd.DataFrame(self.deletion_candidates['low'])
            df_low = df_low.sort_values('new_recognition_score')
            df_low.to_csv(low_path, index=False, encoding='utf-8-sig')
            logger.info(f"✅ 低優先削除候補: {low_path} ({len(df_low)}件)")

        # 4. 全体ランキング
        full_path = self.output_dir / f"recognition_ranking_FULL_{timestamp}.csv"
        df_full = pd.DataFrame(self.results)
        df_full = df_full.sort_values('new_recognition_score', ascending=False)
        df_full.to_csv(full_path, index=False, encoding='utf-8-sig')
        logger.info(f"✅ 全体ランキング: {full_path} ({len(df_full)}件)")

        # 5. サマリーレポート
        self._save_summary_report(timestamp)

    def _save_summary_report(self, timestamp: str):
        """サマリーレポート作成"""
        report_path = self.output_dir / f"deletion_summary_report_{timestamp}.md"

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# 知名度選定システム - 削除候補レポート\n\n")
            f.write(f"生成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}\n\n")

            f.write("## 📊 統計サマリー\n\n")
            f.write(f"- 総レコード数: {self.stats['total']:,}\n")
            f.write(f"- 処理済み: {self.stats['processed']:,}\n")
            f.write(f"- エラー: {self.stats['errors']:,}\n\n")

            f.write("## 🗑️ 削除候補\n\n")
            deleted_total = sum([self.stats['deleted_high'],
                               self.stats['deleted_review'],
                               self.stats['deleted_low']])
            f.write(f"**合計: {deleted_total:,}件 ({deleted_total/self.stats['total']*100:.1f}%)**\n\n")

            f.write("| 優先度 | スコア範囲 | 件数 | 割合 |\n")
            f.write("|--------|-----------|------|------|\n")
            f.write(f"| 高 | < 3.0 | {self.stats['deleted_high']:,} | {self.stats['deleted_high']/self.stats['total']*100:.1f}% |\n")
            f.write(f"| 中 | 3.0-4.0 | {self.stats['deleted_review']:,} | {self.stats['deleted_review']/self.stats['total']*100:.1f}% |\n")
            f.write(f"| 低 | 4.0-5.0 | {self.stats['deleted_low']:,} | {self.stats['deleted_low']/self.stats['total']*100:.1f}% |\n\n")

            f.write("## ✅ 保持・保護\n\n")
            f.write(f"- 保持: {self.stats['kept']:,}件 ({self.stats['kept']/self.stats['total']*100:.1f}%)\n")
            f.write(f"- 保護: {self.stats['protected']:,}件 ({self.stats['protected']/self.stats['total']*100:.1f}%)\n\n")

            # 検証結果
            f.write("## 🔍 有名人検証結果\n\n")
            f.write("| 名前 | 旧スコア | 新スコア | アクション |\n")
            f.write("|------|---------|---------|------------|\n")

            # HIKAKINなどの検証結果を表示
            for result in self.results[:100]:  # 最初の100件から検証対象を探す
                name = result.get('person_name', '')
                if any(v in name for v in self.verification_persons[:5]):
                    f.write(f"| {name} | {result.get('old_calibrated_score', 'N/A')} | "
                           f"{result.get('new_recognition_score', 0):.2f} | "
                           f"{result.get('action', 'N/A')} |\n")

        logger.info(f"✅ サマリーレポート: {report_path}")


def main():
    """メイン処理"""
    import argparse

    parser = argparse.ArgumentParser(description='究極知名度選定システムによる削除候補選定')
    parser.add_argument('--input', '-i',
                       default='ultra_think_EPISODE_FINAL_20250901_020106_fixed.csv',
                       help='入力CSVファイル')
    parser.add_argument('--output', '-o',
                       default='削除候補',
                       help='出力ディレクトリ')
    parser.add_argument('--sample', '-s',
                       type=int,
                       help='サンプルサイズ（テスト用）')
    parser.add_argument('--dry-run',
                       action='store_true',
                       help='ドライラン（保存なし）')

    args = parser.parse_args()

    # 実行
    try:
        evaluator = DatabaseRecognitionEvaluator(args.input, args.output)
        evaluator.process_database(sample_size=args.sample)

        if not args.dry_run:
            evaluator.save_results()
            logger.info("\n✨ 処理完了！削除候補が生成されました。")
        else:
            logger.info("\n🔬 ドライラン完了（ファイル保存なし）")

    except Exception as e:
        logger.error(f"❌ 致命的エラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
