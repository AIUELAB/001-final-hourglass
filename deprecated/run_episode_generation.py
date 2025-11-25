#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
エピソード生成システム実行スクリプト

高品質エピソードの生成を実行する
メインエントリーポイント
"""

import sys
import os
import logging
from datetime import datetime
from pathlib import Path

# .envファイルから環境変数を読み込み
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️ python-dotenvがインストールされていません")

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'episode_generation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def check_environment():
    """環境チェック"""
    logger.info("="*60)
    logger.info("🔍 環境チェック")
    logger.info("="*60)

    # APIキーチェック
    api_keys = {
        'ANTHROPIC_API_KEY': os.getenv('ANTHROPIC_API_KEY'),
        'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
        'BRAVE_API_KEY': os.getenv('BRAVE_API_KEY')
    }

    missing_keys = []
    for key_name, key_value in api_keys.items():
        if key_value:
            logger.info(f"✅ {key_name}: 設定済み")
        else:
            logger.warning(f"⚠️ {key_name}: 未設定")
            if key_name == 'ANTHROPIC_API_KEY':
                missing_keys.append(key_name)

    # CSVファイルチェック
    csv_files = list(Path('.').glob('ultra_think_*.csv'))
    if csv_files:
        latest_csv = max(csv_files, key=lambda f: f.stat().st_mtime)
        logger.info(f"✅ データベースCSV: {latest_csv}")
    else:
        logger.error("❌ ultra_think_*.csvファイルが見つかりません")
        return False

    # 必須モジュールチェック
    required_modules = [
        'premium_episode_generator',
        'episode_database_integration',
        'pdca_guardian',
        'api_credit_monitor'
    ]

    for module_name in required_modules:
        module_file = f"{module_name}.py"
        if Path(module_file).exists():
            logger.info(f"✅ {module_file}: 存在")
        else:
            logger.error(f"❌ {module_file}: 見つかりません")
            return False

    if missing_keys:
        logger.error(f"❌ 必須APIキーが設定されていません: {missing_keys}")
        logger.error("  .envファイルを確認してください")
        return False

    logger.info("✅ 環境チェック完了")
    return True


def run_episode_generation(test_mode=False, limit=None):
    """
    エピソード生成実行

    Args:
        test_mode: テストモード（少数のサンプルで実行）
        limit: 処理人数の上限
    """
    logger.info("\n" + "="*60)
    logger.info("🚀 エピソード生成システム開始")
    logger.info("="*60)

    # 環境チェック
    if not check_environment():
        logger.error("環境チェックに失敗しました。処理を中止します。")
        return False

    try:
        # モジュールインポート
        from episode_database_integration import EpisodeDatabaseIntegration
        from api_credit_monitor import APICrediteMonitor

        # クレジット事前確認
        logger.info("\n" + "="*60)
        logger.info("💳 APIクレジット確認")
        logger.info("="*60)

        monitor = APICrediteMonitor()
        monitor.display_status()

        # テストモードの設定
        if test_mode:
            logger.info("\n📝 テストモード: 5人のサンプルで実行します")
            limit = 5

        # データベース統合システム初期化
        integration = EpisodeDatabaseIntegration()

        # 最新のCSVファイルを検出
        csv_files = list(Path('.').glob('ultra_think_*.csv'))
        if not csv_files:
            logger.error("CSVファイルが見つかりません")
            return False

        latest_csv = max(csv_files, key=lambda f: f.stat().st_mtime)
        logger.info(f"\n📂 使用するCSVファイル: {latest_csv}")

        # データベース同期
        logger.info("\n" + "="*60)
        logger.info("🔄 データベース同期")
        logger.info("="*60)

        # CSVファイルを読み込み
        import pandas as pd
        df = pd.read_csv(str(latest_csv), encoding='utf-8')
        logger.info(f"📊 CSVファイル読み込み完了: {len(df)}件")

        # データベースに同期
        integration.sync_persons_to_database(df)

        # フィルタ設定（高認知度の人物を優先）
        if test_mode:
            # テストモード: 認知度スコア上位5人
            person_filter = {
                'recognition_score': {'$gte': 8.0},
                'birth_year': {'$not_null': True}
            }
        else:
            # 本番モード: birth_yearがある全員
            person_filter = {
                'birth_year': {'$not_null': True}
            }

        # エピソード生成実行
        logger.info("\n" + "="*60)
        logger.info("🎬 エピソード生成開始")
        logger.info("="*60)

        status = integration.batch_generate_episodes(
            person_filter=person_filter,
            limit=limit
        )

        # 結果サマリー
        logger.info("\n" + "="*60)
        logger.info("📊 生成結果サマリー")
        logger.info("="*60)
        logger.info(f"総人数: {status.total_persons}")
        logger.info(f"処理済み: {status.processed}")
        logger.info(f"成功: {status.successful}")
        logger.info(f"失敗: {status.failed}")
        logger.info(f"スキップ: {status.skipped}")

        if status.successful > 0:
            success_rate = (status.successful / status.processed) * 100
            logger.info(f"成功率: {success_rate:.1f}%")

        if status.api_costs > 0:
            logger.info(f"推定APIコスト: ${status.api_costs:.2f}")

        # エピソード品質分析
        logger.info("\n" + "="*60)
        logger.info("🎯 エピソード品質分析")
        logger.info("="*60)

        integration.analyze_episode_quality()

        # エクスポート
        if status.successful > 0:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # CSV出力
            csv_file = f"output/episodes_{timestamp}.csv"
            integration.export_episodes_to_csv(csv_file)
            logger.info(f"✅ CSVエクスポート: {csv_file}")

            # JSON出力
            json_file = f"output/episodes_{timestamp}.json"
            integration.export_episodes_to_json(json_file)
            logger.info(f"✅ JSONエクスポート: {json_file}")

            # レポート出力
            report_file = f"output/generation_report_{timestamp}.txt"
            integration.generate_report(report_file)
            logger.info(f"✅ レポート生成: {report_file}")

        logger.info("\n" + "="*60)
        logger.info("✨ エピソード生成完了")
        logger.info("="*60)

        return True

    except Exception as e:
        logger.error(f"エピソード生成中にエラーが発生しました: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def main():
    """メイン関数"""
    import argparse

    parser = argparse.ArgumentParser(description='エピソード生成システム')
    parser.add_argument(
        '--test',
        action='store_true',
        help='テストモード（5人のサンプルで実行）'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='処理人数の上限'
    )

    args = parser.parse_args()

    # 実行
    success = run_episode_generation(
        test_mode=args.test,
        limit=args.limit
    )

    if success:
        logger.info("🎉 処理が正常に完了しました")
        sys.exit(0)
    else:
        logger.error("❌ 処理中にエラーが発生しました")
        sys.exit(1)


if __name__ == "__main__":
    main()
