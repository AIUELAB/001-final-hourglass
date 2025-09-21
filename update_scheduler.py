#!/usr/bin/env python3
"""
Update Scheduler
自動更新のスケジューリング管理
"""

import json
import asyncio
import schedule
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path
import logging
import sys
import threading

# モジュールのインポート
sys.path.append(str(Path(__file__).parent))
from auto_fact_updater import AutoFactUpdater
from fact_freshness_checker import FactFreshnessChecker

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [Scheduler] - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class UpdateScheduler:
    """更新スケジューラー"""

    def __init__(self, config_path: str = "config/update_config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.updater = AutoFactUpdater()
        self.freshness_checker = FactFreshnessChecker()
        self.running = False
        self.schedule_thread = None

        # スケジュール履歴
        self.execution_log = []
        self.log_file = Path("logs/schedule_log.json")
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def _load_config(self) -> Dict:
        """設定ファイルの読み込み"""
        default_config = {
            "schedules": {
                "daily": {
                    "enabled": True,
                    "time": "03:00",
                    "categories": ["スポーツ", "エンタメ"],
                    "max_persons": 5
                },
                "weekly": {
                    "enabled": True,
                    "day": "sunday",
                    "time": "04:00",
                    "categories": ["政治", "科学・技術", "文化・芸術"],
                    "max_persons": 10
                },
                "monthly": {
                    "enabled": False,
                    "day": 1,
                    "time": "05:00",
                    "categories": "all",
                    "max_persons": 20
                }
            },
            "immediate_update_triggers": {
                "keywords": ["速報", "優勝", "記録", "達成", "受賞"],
                "min_importance": 0.8
            },
            "rate_limits": {
                "max_daily_updates": 50,
                "max_concurrent": 5
            }
        }

        # 設定ファイルが存在しない場合はデフォルトを作成
        config_path = Path(self.config_path)
        if not config_path.exists():
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, ensure_ascii=False, indent=2)
            logger.info(f"Created default config: {config_path}")
            return default_config

        # 既存の設定を読み込み
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def setup_schedules(self):
        """スケジュールの設定"""
        schedules = self.config.get('schedules', {})

        # 日次スケジュール
        if schedules.get('daily', {}).get('enabled', False):
            daily_time = schedules['daily']['time']
            schedule.every().day.at(daily_time).do(
                self._run_scheduled_update,
                'daily',
                schedules['daily']
            )
            logger.info(f"Daily schedule set at {daily_time}")

        # 週次スケジュール
        if schedules.get('weekly', {}).get('enabled', False):
            weekly_day = schedules['weekly'].get('day', 'sunday')
            weekly_time = schedules['weekly']['time']

            if weekly_day.lower() == 'monday':
                schedule.every().monday.at(weekly_time).do(
                    self._run_scheduled_update, 'weekly', schedules['weekly']
                )
            elif weekly_day.lower() == 'sunday':
                schedule.every().sunday.at(weekly_time).do(
                    self._run_scheduled_update, 'weekly', schedules['weekly']
                )

            logger.info(f"Weekly schedule set for {weekly_day} at {weekly_time}")

        # 月次スケジュール（簡易実装）
        if schedules.get('monthly', {}).get('enabled', False):
            monthly_time = schedules['monthly']['time']
            # 毎日チェックして、月の特定日なら実行
            schedule.every().day.at(monthly_time).do(
                self._check_monthly_schedule,
                schedules['monthly']
            )
            logger.info(f"Monthly schedule set for day {schedules['monthly']['day']} at {monthly_time}")

    def _run_scheduled_update(self, schedule_type: str, config: Dict):
        """
        スケジュールされた更新の実行

        Args:
            schedule_type: スケジュールタイプ（daily/weekly/monthly）
            config: スケジュール設定
        """
        logger.info(f"Starting {schedule_type} update...")

        # 実行ログ記録
        execution_record = {
            'type': schedule_type,
            'start_time': datetime.now().isoformat(),
            'config': config
        }

        try:
            # 非同期タスクを同期的に実行
            asyncio.run(self._execute_update(config))

            execution_record['status'] = 'success'
            execution_record['end_time'] = datetime.now().isoformat()
            logger.info(f"✅ {schedule_type} update completed successfully")

        except Exception as e:
            execution_record['status'] = 'failed'
            execution_record['error'] = str(e)
            execution_record['end_time'] = datetime.now().isoformat()
            logger.error(f"❌ {schedule_type} update failed: {e}")

        # 実行ログ保存
        self.execution_log.append(execution_record)
        self._save_execution_log()

    def _check_monthly_schedule(self, config: Dict):
        """月次スケジュールのチェック"""
        today = datetime.now().day
        scheduled_day = config.get('day', 1)

        if today == scheduled_day:
            self._run_scheduled_update('monthly', config)

    async def _execute_update(self, config: Dict):
        """
        更新の実行

        Args:
            config: 更新設定
        """
        categories = config.get('categories', [])
        max_persons = config.get('max_persons', 10)

        # カテゴリ指定がある場合はフィルタリング
        if categories != 'all' and categories:
            # カテゴリに基づいて対象人物を絞る
            logger.info(f"Filtering by categories: {categories}")

        # 更新実行
        await self.updater.run_batch_update(max_persons=max_persons)

    def _save_execution_log(self):
        """実行ログの保存"""
        # 最新50件のみ保持
        recent_logs = self.execution_log[-50:]

        with open(self.log_file, 'w', encoding='utf-8') as f:
            json.dump(recent_logs, f, ensure_ascii=False, indent=2)

    def run_immediate_update(self, person_name: str, reason: str = "manual"):
        """
        即時更新の実行

        Args:
            person_name: 人物名
            reason: 更新理由
        """
        logger.info(f"Immediate update requested for {person_name} (reason: {reason})")

        try:
            # 単一人物の更新
            person_data = self.updater.database.get('verified_facts', {}).get(person_name)
            if person_data:
                asyncio.run(self.updater.update_person_facts(person_name, person_data))
                self.updater._save_database(self.updater.database)
                logger.info(f"✅ Immediate update completed for {person_name}")
            else:
                logger.warning(f"Person not found in database: {person_name}")

        except Exception as e:
            logger.error(f"Failed immediate update for {person_name}: {e}")

    def start(self):
        """スケジューラーの開始"""
        if self.running:
            logger.warning("Scheduler is already running")
            return

        self.running = True
        self.setup_schedules()

        # スケジュール実行スレッド
        def schedule_worker():
            while self.running:
                schedule.run_pending()
                time.sleep(60)  # 1分ごとにチェック

        self.schedule_thread = threading.Thread(target=schedule_worker, daemon=True)
        self.schedule_thread.start()

        logger.info("✅ Scheduler started")

    def stop(self):
        """スケジューラーの停止"""
        self.running = False
        if self.schedule_thread:
            self.schedule_thread.join(timeout=5)
        logger.info("⏹️ Scheduler stopped")

    def get_next_runs(self) -> List[Dict]:
        """次回実行予定の取得"""
        next_runs = []

        for job in schedule.jobs:
            next_run = job.next_run
            if next_run:
                next_runs.append({
                    'job': str(job),
                    'next_run': next_run.isoformat()
                })

        return next_runs

    def get_status(self) -> Dict:
        """スケジューラーのステータス取得"""
        return {
            'running': self.running,
            'next_runs': self.get_next_runs(),
            'total_executions': len(self.execution_log),
            'last_execution': self.execution_log[-1] if self.execution_log else None,
            'config': self.config
        }


def main():
    """メイン処理（デモンストレーション）"""
    print("=" * 60)
    print("Update Scheduler - 自動更新スケジューラー")
    print("=" * 60)

    scheduler = UpdateScheduler()

    # ステータス表示
    print("\n📊 Current Status:")
    status = scheduler.get_status()
    print(f"Running: {status['running']}")
    print(f"Total Executions: {status['total_executions']}")

    # スケジュール表示
    print("\n📅 Configured Schedules:")
    for schedule_type, config in status['config']['schedules'].items():
        if config.get('enabled'):
            print(f"  - {schedule_type}: {config}")

    # デモ：即時更新
    print("\n🚀 Demo: Immediate update for 大谷翔平")
    scheduler.run_immediate_update("大谷翔平", reason="demo")

    # スケジューラー開始（デモでは開始のみ）
    print("\n⏰ Starting scheduler...")
    scheduler.start()

    print("\n✅ Scheduler is now running in the background")
    print("   Next scheduled runs:")
    for next_run in scheduler.get_next_runs()[:3]:
        print(f"   - {next_run}")

    # デモなので5秒後に停止
    time.sleep(5)
    scheduler.stop()
    print("\n🛑 Scheduler stopped (demo ended)")


if __name__ == "__main__":
    main()