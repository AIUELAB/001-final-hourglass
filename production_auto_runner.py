#!/usr/bin/env python3
"""
本番環境用自動実行スクリプト
日次バッチ処理、エラー回復、進捗レポート機能付き
"""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional, Dict, List
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pickle
import schedule

# ログ設定
def setup_logging():
    """本番環境用ログ設定"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    log_file = log_dir / f"production_{datetime.now().strftime('%Y%m%d')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - [%(levelname)s] - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()


class ProductionRunner:
    """本番環境実行管理クラス"""

    def __init__(self, config_file="production_config.json"):
        """初期化"""
        self.config = self.load_config(config_file)
        self.state_file = "production_state.pkl"
        self.state = self.load_state()
        self.metrics = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'api_calls': 0,
            'cache_hits': 0,
            'start_time': None,
            'errors': []
        }

    def load_config(self, config_file):
        """設定ファイル読み込み"""
        default_config = {
            'batch_size': 100,
            'max_retries': 3,
            'checkpoint_interval': 50,
            'api_limits': {
                'youtube': 100,  # per hour
                'twitter': 180,  # per 15 min
                'news': 500      # per day
            },
            'notification': {
                'enabled': True,
                'email': 'admin@example.com',
                'slack_webhook': None
            },
            'schedule': {
                'daily_run': '02:00',
                'report_time': '08:00'
            }
        }

        if Path(config_file).exists():
            with open(config_file, 'r') as f:
                user_config = json.load(f)
                default_config.update(user_config)

        return default_config

    def load_state(self):
        """実行状態の復元"""
        if Path(self.state_file).exists():
            try:
                with open(self.state_file, 'rb') as f:
                    state = pickle.load(f)
                    logger.info(f"✅ 状態復元: {state['processed_count']}件処理済み")
                    return state
            except Exception as e:
                logger.error(f"❌ 状態復元失敗: {e}")

        return {
            'processed_count': 0,
            'last_checkpoint': None,
            'failed_records': [],
            'api_usage': {}
        }

    def save_state(self):
        """実行状態の保存"""
        try:
            with open(self.state_file, 'wb') as f:
                pickle.dump(self.state, f)
            logger.debug("💾 状態保存完了")
        except Exception as e:
            logger.error(f"❌ 状態保存失敗: {e}")

    async def process_batch(self, batch_df):
        """バッチ処理実行"""
        results = []

        for idx, row in batch_df.iterrows():
            try:
                # APIクォータチェック
                if not self.check_api_quota():
                    logger.warning("⚠️ APIクォータ制限到達、次回実行まで待機")
                    break

                # 評価実行（実際のシステムを呼び出し）
                result = await self.evaluate_person(row)
                results.append(result)

                self.metrics['successful'] += 1
                self.state['processed_count'] += 1

                # チェックポイント
                if self.state['processed_count'] % self.config['checkpoint_interval'] == 0:
                    self.save_state()
                    logger.info(f"📌 チェックポイント: {self.state['processed_count']}件完了")

            except Exception as e:
                logger.error(f"❌ 処理失敗 [{row.get('person_id')}]: {e}")
                self.metrics['failed'] += 1
                self.state['failed_records'].append({
                    'person_id': row.get('person_id'),
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })

        return results

    async def evaluate_person(self, row):
        """個別評価（簡略版）"""
        # 実際の評価システムを呼び出す
        from run_recognition_evaluation import OptimizedEvaluationSystem

        system = OptimizedEvaluationSystem(test_mode=False)
        result = await system.evaluate_single(
            row['person_name_ja'],
            row.get('category', 'その他')
        )

        return {
            'person_id': row['person_id'],
            'recognition_score': result.get('score', 0),
            'data_completeness': result.get('completeness', 0),
            'evaluation_method': result.get('method', 'unknown')
        }

    def check_api_quota(self):
        """APIクォータチェック"""
        current_hour = datetime.now().hour

        # YouTube: 時間あたり100回
        youtube_usage = self.state['api_usage'].get(f'youtube_{current_hour}', 0)
        if youtube_usage >= self.config['api_limits']['youtube']:
            return False

        # Twitter: 15分あたり180回
        current_quarter = datetime.now().minute // 15
        twitter_usage = self.state['api_usage'].get(f'twitter_{current_hour}_{current_quarter}', 0)
        if twitter_usage >= self.config['api_limits']['twitter']:
            return False

        return True

    def send_notification(self, message, level="INFO"):
        """通知送信"""
        if not self.config['notification']['enabled']:
            return

        # Email通知
        if self.config['notification'].get('email'):
            self.send_email(message, level)

        # Slack通知
        if self.config['notification'].get('slack_webhook'):
            self.send_slack(message, level)

    def send_email(self, message, level):
        """メール送信"""
        try:
            msg = MIMEMultipart()
            msg['Subject'] = f"[Recognition System] {level}: 処理状況通知"
            msg['From'] = "system@example.com"
            msg['To'] = self.config['notification']['email']

            body = f"""
            処理状況レポート
            ================

            {message}

            詳細:
            - 処理済み: {self.metrics['successful']}件
            - 失敗: {self.metrics['failed']}件
            - API呼び出し: {self.metrics['api_calls']}回
            - キャッシュヒット: {self.metrics['cache_hits']}回

            生成時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """

            msg.attach(MIMEText(body, 'plain'))

            # SMTP設定（環境変数から取得）
            smtp_server = os.getenv('SMTP_SERVER', 'localhost')
            smtp_port = int(os.getenv('SMTP_PORT', '25'))

            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.send_message(msg)

            logger.info("📧 メール通知送信完了")

        except Exception as e:
            logger.error(f"❌ メール送信失敗: {e}")

    def send_slack(self, message, level):
        """Slack通知"""
        import requests

        try:
            webhook_url = self.config['notification']['slack_webhook']

            emoji = {
                'INFO': ':information_source:',
                'WARNING': ':warning:',
                'ERROR': ':x:',
                'SUCCESS': ':white_check_mark:'
            }.get(level, ':speech_balloon:')

            payload = {
                'text': f"{emoji} *Recognition System {level}*",
                'attachments': [{
                    'color': {
                        'INFO': '#36a64f',
                        'WARNING': '#ff9900',
                        'ERROR': '#ff0000',
                        'SUCCESS': '#00ff00'
                    }.get(level, '#808080'),
                    'text': message,
                    'footer': 'Recognition System',
                    'ts': int(time.time())
                }]
            }

            response = requests.post(webhook_url, json=payload)
            if response.status_code == 200:
                logger.info("💬 Slack通知送信完了")

        except Exception as e:
            logger.error(f"❌ Slack送信失敗: {e}")

    def generate_report(self):
        """処理レポート生成"""
        elapsed_time = (datetime.now() - datetime.fromisoformat(
            self.metrics['start_time']
        )).total_seconds() if self.metrics['start_time'] else 0

        report = f"""
        ========================================
        📊 知名度評価システム - 本番処理レポート
        ========================================

        実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

        📈 処理統計:
        ----------------
        総処理数: {self.metrics['successful'] + self.metrics['failed']}件
        成功: {self.metrics['successful']}件
        失敗: {self.metrics['failed']}件
        成功率: {(self.metrics['successful'] / max(1, self.metrics['successful'] + self.metrics['failed']) * 100):.1f}%

        ⚡ パフォーマンス:
        ----------------
        処理時間: {elapsed_time / 3600:.1f}時間
        処理速度: {self.metrics['successful'] / max(1, elapsed_time) * 3600:.0f}件/時
        API呼び出し: {self.metrics['api_calls']}回
        キャッシュヒット率: {(self.metrics['cache_hits'] / max(1, self.metrics['cache_hits'] + self.metrics['api_calls']) * 100):.1f}%

        🔍 エラー詳細:
        ----------------
        """

        if self.state['failed_records']:
            for error in self.state['failed_records'][-10:]:  # 最新10件
                report += f"- [{error['person_id']}] {error['error']}\n"
        else:
            report += "エラーなし\n"

        report += """
        ========================================
        """

        return report

    async def run_daily(self):
        """日次処理実行"""
        logger.info("=" * 60)
        logger.info("🚀 日次処理開始")
        logger.info("=" * 60)

        self.metrics['start_time'] = datetime.now().isoformat()

        try:
            # データ読み込み
            df = pd.read_csv('ultra_think_EPISODE_FINAL_20250901_020106_fixed.csv')

            # 未処理レコードの抽出
            if self.state['processed_count'] > 0:
                df = df.iloc[self.state['processed_count']:]
                logger.info(f"📌 続きから処理: {self.state['processed_count']}件目から")

            total_records = len(df)
            logger.info(f"📊 処理対象: {total_records}件")

            # バッチ処理
            batch_size = self.config['batch_size']
            for i in range(0, total_records, batch_size):
                batch = df.iloc[i:i+batch_size]
                logger.info(f"🔄 バッチ処理: {i+1}-{min(i+batch_size, total_records)}/{total_records}")

                results = await self.process_batch(batch)

                # 結果保存
                if results:
                    self.save_results(results)

                # 進捗通知
                if (i + batch_size) % 500 == 0:
                    progress = (i + batch_size) / total_records * 100
                    self.send_notification(
                        f"処理進捗: {progress:.1f}% ({i+batch_size}/{total_records}件)",
                        "INFO"
                    )

            # 完了処理
            logger.info("✅ 日次処理完了")
            self.send_notification(self.generate_report(), "SUCCESS")

            # 状態リセット（翌日用）
            self.state['processed_count'] = 0
            self.state['failed_records'] = []
            self.save_state()

        except Exception as e:
            logger.error(f"❌ 日次処理エラー: {e}")
            self.send_notification(f"処理エラー発生: {e}", "ERROR")

    def save_results(self, results):
        """結果保存"""
        output_file = f"production_results_{datetime.now().strftime('%Y%m%d')}.csv"

        df = pd.DataFrame(results)

        # 既存ファイルがあれば追記
        if Path(output_file).exists():
            existing_df = pd.read_csv(output_file)
            df = pd.concat([existing_df, df], ignore_index=True)

        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        logger.debug(f"💾 結果保存: {output_file}")

    def schedule_jobs(self):
        """スケジュール設定"""
        # 日次処理
        daily_time = self.config['schedule']['daily_run']
        schedule.every().day.at(daily_time).do(
            lambda: asyncio.run(self.run_daily())
        )

        # レポート送信
        report_time = self.config['schedule']['report_time']
        schedule.every().day.at(report_time).do(
            lambda: self.send_notification(self.generate_report(), "INFO")
        )

        logger.info(f"⏰ スケジュール設定完了")
        logger.info(f"  - 日次処理: {daily_time}")
        logger.info(f"  - レポート: {report_time}")

    def run(self):
        """メインループ"""
        logger.info("🎯 本番環境自動実行システム起動")

        # スケジュール設定
        self.schedule_jobs()

        # 起動通知
        self.send_notification("システム起動完了", "INFO")

        # メインループ
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # 1分ごとにチェック

        except KeyboardInterrupt:
            logger.info("⚠️ システム停止要求")
            self.send_notification("システム停止", "WARNING")
        except Exception as e:
            logger.error(f"❌ システムエラー: {e}")
            self.send_notification(f"システムエラー: {e}", "ERROR")


def main():
    """メイン実行"""
    runner = ProductionRunner()

    # コマンドライン引数処理
    if len(sys.argv) > 1:
        if sys.argv[1] == '--once':
            # 単発実行
            asyncio.run(runner.run_daily())
        elif sys.argv[1] == '--report':
            # レポートのみ
            print(runner.generate_report())
        elif sys.argv[1] == '--test':
            # テスト実行
            runner.config['batch_size'] = 10
            asyncio.run(runner.run_daily())
        else:
            print("Usage: python production_auto_runner.py [--once|--report|--test]")
    else:
        # 通常のスケジュール実行
        runner.run()


if __name__ == "__main__":
    main()
