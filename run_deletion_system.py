#!/usr/bin/env python3
"""
知名度ベース統合削除システム - 実行ランナー
Knowledge-Based Integrated Deletion System - Execution Runner

このスクリプトは削除システムを実行するためのCLIインターフェースを提供します。
"""

import argparse
import sys
import os
import json
import pandas as pd
from datetime import datetime
import logging
from pathlib import Path
import shutil
from typing import Dict, List, Optional
import warnings
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

# 依存システムのインポート
from wikipedia_validator_ultimate import WikipediaValidator
from web_search_validator import WebSearchValidator
from metadata_quality_scorer import MetadataQualityScorer
from integrated_deletion_system import IntegratedDeletionSystem

# ロギング設定
def setup_logging(log_level: str = 'INFO', log_file: Optional[str] = None):
    """ロギングのセットアップ"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    handlers = [logging.StreamHandler(sys.stdout)]

    if log_file:
        log_dir = Path('deletion_logs')
        log_dir.mkdir(exist_ok=True)
        handlers.append(logging.FileHandler(log_dir / log_file))

    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=handlers
    )

    return logging.getLogger(__name__)

class DeletionSystemRunner:
    """削除システム実行ランナー"""

    def __init__(self, config_file: str = 'deletion_config.yaml'):
        """
        初期化

        Args:
            config_file: 設定ファイルパス
        """
        self.config_file = config_file
        self.logger = logging.getLogger(__name__)
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # 出力ディレクトリの準備
        self.output_dir = Path('deletion_results')
        self.output_dir.mkdir(exist_ok=True)

        self.backup_dir = Path('deletion_backups')
        self.backup_dir.mkdir(exist_ok=True)

        # 統合システムの初期化
        self.system = IntegratedDeletionSystem(config_file)

    def create_backup(self, csv_file: str) -> str:
        """
        データベースのバックアップ作成

        Args:
            csv_file: バックアップ対象のCSVファイル

        Returns:
            バックアップファイルパス
        """
        backup_file = self.backup_dir / f"backup_{self.timestamp}_{Path(csv_file).name}"
        shutil.copy2(csv_file, backup_file)
        self.logger.info(f"Backup created: {backup_file}")
        return str(backup_file)

    def load_data(self, csv_file: str, encoding: str = 'utf-8') -> pd.DataFrame:
        """
        CSVファイルの読み込み

        Args:
            csv_file: CSVファイルパス
            encoding: エンコーディング

        Returns:
            DataFrame
        """
        self.logger.info(f"Loading data from {csv_file}")

        try:
            df = pd.read_csv(csv_file, encoding=encoding)
            self.logger.info(f"Loaded {len(df)} records")

            # データ検証
            required_fields = ['person_id', 'person_name', 'person_name_display']
            missing_fields = [f for f in required_fields if f not in df.columns]

            if missing_fields:
                raise ValueError(f"Missing required fields: {missing_fields}")

            return df

        except Exception as e:
            self.logger.error(f"Failed to load data: {e}")
            raise

    def run_test_mode(self, csv_file: str, sample_size: int = 100):
        """
        テストモード実行

        Args:
            csv_file: CSVファイルパス
            sample_size: サンプルサイズ
        """
        self.logger.info("="*60)
        self.logger.info("Running in TEST MODE")
        self.logger.info("="*60)

        # データ読み込み
        df = self.load_data(csv_file)

        # サンプル抽出
        if len(df) > sample_size:
            self.logger.info(f"Sampling {sample_size} records for testing")
            df_sample = df.sample(n=sample_size, random_state=42)
        else:
            df_sample = df

        # 処理実行
        results = self.system.process_batch(df_sample)

        # 結果分析
        self.analyze_test_results(results)

        # テスト結果保存
        test_output = self.output_dir / f"test_results_{self.timestamp}.csv"
        results.to_csv(test_output, index=False, encoding='utf-8')
        self.logger.info(f"Test results saved to: {test_output}")

        return results

    def analyze_test_results(self, results: pd.DataFrame):
        """
        テスト結果の分析

        Args:
            results: 結果DataFrame
        """
        self.logger.info("\n" + "="*60)
        self.logger.info("TEST RESULTS ANALYSIS")
        self.logger.info("="*60)

        # 推奨アクションの分布
        recommendations = results['recommendation'].value_counts()

        self.logger.info("\n📊 Recommendation Distribution:")
        for rec, count in recommendations.items():
            percentage = (count / len(results)) * 100
            self.logger.info(f"  {rec}: {count} ({percentage:.1f}%)")

        # スコア統計
        self.logger.info("\n📈 Score Statistics:")
        score_cols = ['wikipedia_score', 'web_search_score', 'metadata_quality_score', 'integrated_score']

        for col in score_cols:
            if col in results.columns:
                stats = results[col].describe()
                self.logger.info(f"\n  {col}:")
                self.logger.info(f"    Mean: {stats['mean']:.2f}")
                self.logger.info(f"    Std:  {stats['std']:.2f}")
                self.logger.info(f"    Min:  {stats['min']:.2f}")
                self.logger.info(f"    Max:  {stats['max']:.2f}")

        # 削除候補のサンプル表示
        delete_candidates = results[
            results['recommendation'].isin(['DELETE_HIGH_CONFIDENCE', 'DELETE_MEDIUM_CONFIDENCE'])
        ]

        if not delete_candidates.empty:
            self.logger.info("\n🗑️ Sample Delete Candidates:")
            sample_size = min(10, len(delete_candidates))

            for _, row in delete_candidates.head(sample_size).iterrows():
                self.logger.info(f"  - {row['person_name_display']} (ID: {row['person_id']})")
                self.logger.info(f"    Score: {row['integrated_score']:.2f}, Rec: {row['recommendation']}")

        # 保護された人物のサンプル
        protected = results[results.get('safety_flags', '').str.contains('PROTECTED', na=False)]

        if not protected.empty:
            self.logger.info(f"\n🛡️ Protected Persons: {len(protected)}")
            for _, row in protected.head(5).iterrows():
                self.logger.info(f"  - {row['person_name_display']}: {row.get('safety_flags', '')}")

    def run_full_execution(self, csv_file: str, batch_size: int = 1000,
                          dry_run: bool = False):
        """
        本格実行

        Args:
            csv_file: CSVファイルパス
            batch_size: バッチサイズ
            dry_run: ドライラン（実際の削除を行わない）
        """
        self.logger.info("="*60)
        self.logger.info(f"Running FULL EXECUTION {'(DRY RUN)' if dry_run else ''}")
        self.logger.info("="*60)

        # バックアップ作成
        if not dry_run:
            backup_file = self.create_backup(csv_file)
            self.logger.info(f"Backup created: {backup_file}")

        # データ読み込み
        df = self.load_data(csv_file)
        total_records = len(df)

        # バッチ処理
        all_results = []

        for i in range(0, total_records, batch_size):
            batch_end = min(i + batch_size, total_records)
            batch_df = df.iloc[i:batch_end]

            self.logger.info(f"\nProcessing batch {i//batch_size + 1}: records {i+1}-{batch_end}")

            # バッチ処理
            batch_results = self.system.process_batch(batch_df)
            all_results.append(batch_results)

            # 中間保存
            if (i + batch_size) % (batch_size * 5) == 0:  # 5バッチごとに保存
                intermediate_file = self.output_dir / f"intermediate_{self.timestamp}_{i}.csv"
                pd.concat(all_results).to_csv(intermediate_file, index=False, encoding='utf-8')
                self.logger.info(f"Intermediate results saved: {intermediate_file}")

        # 全結果の結合
        final_results = pd.concat(all_results, ignore_index=True)

        # 最終結果の保存
        self.save_final_results(final_results, dry_run)

        # 削除実行（dry_runでない場合）
        if not dry_run:
            self.execute_deletions(df, final_results, csv_file)

        return final_results

    def save_final_results(self, results: pd.DataFrame, dry_run: bool):
        """
        最終結果の保存

        Args:
            results: 結果DataFrame
            dry_run: ドライランフラグ
        """
        # 詳細結果
        detailed_file = self.output_dir / f"deletion_analysis_complete_{self.timestamp}.csv"
        results.to_csv(detailed_file, index=False, encoding='utf-8')
        self.logger.info(f"Detailed results saved: {detailed_file}")

        # 削除候補リスト
        delete_candidates = results[
            results['recommendation'].isin(['DELETE_HIGH_CONFIDENCE', 'DELETE_MEDIUM_CONFIDENCE'])
        ]

        if not delete_candidates.empty:
            candidates_file = self.output_dir / f"delete_candidates_{self.timestamp}.csv"
            delete_candidates.to_csv(candidates_file, index=False, encoding='utf-8')
            self.logger.info(f"Delete candidates saved: {candidates_file}")

        # サマリーレポート
        self.generate_summary_report(results, dry_run)

    def generate_summary_report(self, results: pd.DataFrame, dry_run: bool):
        """
        サマリーレポートの生成

        Args:
            results: 結果DataFrame
            dry_run: ドライランフラグ
        """
        summary = {
            'execution_timestamp': self.timestamp,
            'mode': 'DRY_RUN' if dry_run else 'FULL_EXECUTION',
            'total_records': len(results),
            'recommendations': results['recommendation'].value_counts().to_dict(),
            'score_statistics': {},
            'safety_stats': {}
        }

        # スコア統計
        score_cols = ['integrated_score', 'wikipedia_score', 'web_search_score', 'metadata_quality_score']
        for col in score_cols:
            if col in results.columns:
                summary['score_statistics'][col] = {
                    'mean': float(results[col].mean()),
                    'std': float(results[col].std()),
                    'min': float(results[col].min()),
                    'max': float(results[col].max())
                }

        # 安全統計
        if 'safety_flags' in results.columns:
            protected = results[results['safety_flags'].str.contains('PROTECTED', na=False)]
            summary['safety_stats']['protected_count'] = len(protected)
            summary['safety_stats']['protection_reasons'] = (
                protected['safety_flags'].value_counts().head(10).to_dict()
            )

        # 保存
        summary_file = self.output_dir / f"deletion_summary_{self.timestamp}.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        self.logger.info(f"Summary report saved: {summary_file}")

        # コンソール出力
        self.logger.info("\n" + "="*60)
        self.logger.info("EXECUTION SUMMARY")
        self.logger.info("="*60)

        for rec, count in summary['recommendations'].items():
            percentage = (count / summary['total_records']) * 100
            self.logger.info(f"{rec}: {count} ({percentage:.1f}%)")

        if not dry_run:
            delete_count = sum(
                count for rec, count in summary['recommendations'].items()
                if 'DELETE' in rec
            )
            self.logger.info(f"\n🗑️ Total deletions: {delete_count}")

    def execute_deletions(self, original_df: pd.DataFrame, results: pd.DataFrame,
                         output_file: str):
        """
        削除の実行

        Args:
            original_df: 元のDataFrame
            results: 評価結果
            output_file: 出力ファイルパス
        """
        # 削除対象のIDリスト
        delete_ids = results[
            results['recommendation'].isin(['DELETE_HIGH_CONFIDENCE', 'DELETE_MEDIUM_CONFIDENCE'])
        ]['person_id'].tolist()

        if not delete_ids:
            self.logger.info("No records to delete")
            return

        self.logger.info(f"\n🗑️ Deleting {len(delete_ids)} records...")

        # 削除実行
        cleaned_df = original_df[~original_df['person_id'].isin(delete_ids)]

        # 結果保存
        cleaned_file = Path(output_file).parent / f"cleaned_{self.timestamp}_{Path(output_file).name}"
        cleaned_df.to_csv(cleaned_file, index=False, encoding='utf-8')

        self.logger.info(f"✅ Cleaned database saved: {cleaned_file}")
        self.logger.info(f"   Original records: {len(original_df)}")
        self.logger.info(f"   Deleted records: {len(delete_ids)}")
        self.logger.info(f"   Remaining records: {len(cleaned_df)}")


def main():
    """メイン実行関数"""
    parser = argparse.ArgumentParser(
        description='Knowledge-Based Integrated Deletion System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run test with 100 samples
  python run_deletion_system.py test data.csv --sample-size 100

  # Run full execution (dry run)
  python run_deletion_system.py full data.csv --dry-run

  # Run full execution with deletion
  python run_deletion_system.py full data.csv --batch-size 1000
        """
    )

    # サブコマンド
    subparsers = parser.add_subparsers(dest='mode', help='Execution mode')

    # テストモード
    test_parser = subparsers.add_parser('test', help='Run in test mode')
    test_parser.add_argument('csv_file', help='Input CSV file')
    test_parser.add_argument('--sample-size', type=int, default=100,
                            help='Number of samples for testing (default: 100)')

    # フル実行モード
    full_parser = subparsers.add_parser('full', help='Run full execution')
    full_parser.add_argument('csv_file', help='Input CSV file')
    full_parser.add_argument('--batch-size', type=int, default=1000,
                            help='Batch size for processing (default: 1000)')
    full_parser.add_argument('--dry-run', action='store_true',
                            help='Perform dry run without actual deletion')

    # 共通オプション
    parser.add_argument('--config', default='deletion_config.yaml',
                       help='Configuration file (default: deletion_config.yaml)')
    parser.add_argument('--log-level', default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level (default: INFO)')
    parser.add_argument('--log-file', help='Log file name')

    args = parser.parse_args()

    if not args.mode:
        parser.print_help()
        sys.exit(1)

    # ロギング設定
    logger = setup_logging(args.log_level, args.log_file)

    # 実行
    try:
        runner = DeletionSystemRunner(args.config)

        if args.mode == 'test':
            runner.run_test_mode(args.csv_file, args.sample_size)

        elif args.mode == 'full':
            runner.run_full_execution(args.csv_file, args.batch_size, args.dry_run)

        logger.info("\n✅ Execution completed successfully!")

    except KeyboardInterrupt:
        logger.warning("\n⚠️ Execution interrupted by user")
        sys.exit(1)

    except Exception as e:
        logger.error(f"\n❌ Execution failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
