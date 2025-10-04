#!/usr/bin/env python3
"""
エピソード生成自動スケジューラー
週次バッチ生成と統合を自動化
"""

import os
import csv
import json
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import schedule
import time

class EpisodeScheduler:
    def __init__(self):
        self.config_file = "scheduler_config.json"
        self.log_file = "scheduler_log.txt"
        self.load_config()

    def load_config(self) -> None:
        """設定ファイルを読み込み"""
        default_config = {
            "schedule": {
                "weekly_generation": {
                    "enabled": True,
                    "day": "monday",
                    "time": "09:00"
                },
                "weekly_merge": {
                    "enabled": True,
                    "day": "monday",
                    "time": "09:30"
                },
                "daily_check": {
                    "enabled": True,
                    "time": "08:00"
                }
            },
            "targets": {
                "phase1": 100,
                "phase2": 500,
                "phase3": 1000
            },
            "batch_size": 10,
            "auto_run": False
        }

        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        else:
            self.config = default_config
            self.save_config()

    def save_config(self) -> None:
        """設定をファイルに保存"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

    def log_message(self, message: str) -> None:
        """ログメッセージを記録"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"

        print(log_entry.strip())

        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)

    def get_current_count(self) -> int:
        """現在のエピソード数を取得"""
        master_file = "master/episodes_master_current.csv"
        if not os.path.exists(master_file):
            # 代替ファイルを検索
            files = [f for f in os.listdir('.') if 'episodes' in f and f.endswith('.csv')]
            if not files:
                return 0
            master_file = sorted(files)[-1]

        try:
            with open(master_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                count = sum(1 for _ in reader)
                return count
        except Exception as e:
            self.log_message(f"❌ エラー: ファイル読み込み失敗 - {e}")
            return 0

    def check_phase_progress(self) -> Dict:
        """フェーズ進捗を確認"""
        current = self.get_current_count()
        targets = self.config['targets']

        progress = {
            "current_count": current,
            "current_phase": None,
            "next_target": None,
            "remaining": None,
            "weeks_to_target": None
        }

        if current < targets['phase1']:
            progress['current_phase'] = "Phase 1"
            progress['next_target'] = targets['phase1']
        elif current < targets['phase2']:
            progress['current_phase'] = "Phase 2"
            progress['next_target'] = targets['phase2']
        elif current < targets['phase3']:
            progress['current_phase'] = "Phase 3"
            progress['next_target'] = targets['phase3']
        else:
            progress['current_phase'] = "Complete"
            progress['next_target'] = None

        if progress['next_target']:
            progress['remaining'] = progress['next_target'] - current
            progress['weeks_to_target'] = progress['remaining'] / self.config['batch_size']

        return progress

    def run_weekly_generation(self) -> bool:
        """週次バッチ生成を実行"""
        self.log_message("🚀 週次バッチ生成を開始")

        try:
            result = subprocess.run(
                ["python3", "weekly_episode_generator_fixed.py"],
                capture_output=True,
                text=True,
                timeout=300  # 5分タイムアウト
            )

            if result.returncode == 0:
                self.log_message("✅ バッチ生成成功")
                # 出力から生成件数を抽出
                lines = result.stdout.split('\n')
                for line in lines:
                    if "有効率" in line:
                        self.log_message(f"   {line.strip()}")
                return True
            else:
                self.log_message(f"❌ バッチ生成失敗: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            self.log_message("❌ バッチ生成タイムアウト")
            return False
        except Exception as e:
            self.log_message(f"❌ バッチ生成エラー: {e}")
            return False

    def run_auto_merge(self) -> bool:
        """自動統合を実行"""
        self.log_message("🔄 自動統合を開始")

        try:
            result = subprocess.run(
                ["python3", "auto_merge_system.py"],
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                self.log_message("✅ 統合成功")
                # 統合結果を抽出
                lines = result.stdout.split('\n')
                for line in lines:
                    if "新規追加" in line or "総件数" in line:
                        self.log_message(f"   {line.strip()}")
                return True
            else:
                self.log_message(f"❌ 統合失敗: {result.stderr}")
                return False

        except Exception as e:
            self.log_message(f"❌ 統合エラー: {e}")
            return False

    def daily_status_check(self) -> None:
        """日次ステータスチェック"""
        self.log_message("📊 日次ステータスチェック")

        progress = self.check_phase_progress()

        self.log_message(f"   現在のエピソード数: {progress['current_count']}件")
        self.log_message(f"   現在のフェーズ: {progress['current_phase']}")

        if progress['next_target']:
            self.log_message(f"   次の目標: {progress['next_target']}件")
            self.log_message(f"   残り: {progress['remaining']}件")
            self.log_message(f"   推定完了: {progress['weeks_to_target']:.1f}週間")

        # カテゴリーバランスチェック
        self.check_category_balance()

    def check_category_balance(self) -> None:
        """カテゴリーバランスをチェック"""
        master_file = "master/episodes_master_current.csv"
        if not os.path.exists(master_file):
            return

        categories = {}
        total = 0

        with open(master_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                category = row.get('category', '不明')
                categories[category] = categories.get(category, 0) + 1
                total += 1

        if total > 0:
            # 10%未満のカテゴリーを特定
            underrepresented = []
            for category, count in categories.items():
                percentage = count / total * 100
                if percentage < 10:
                    underrepresented.append(f"{category}({percentage:.1f}%)")

            if underrepresented:
                self.log_message(f"   ⚠️ 強化が必要: {', '.join(underrepresented)}")

    def run_scheduled_task(self, task_name: str) -> None:
        """スケジュールされたタスクを実行"""
        self.log_message(f"⏰ スケジュールタスク実行: {task_name}")

        if task_name == "weekly_generation":
            if self.run_weekly_generation():
                time.sleep(10)  # 10秒待機
                self.run_auto_merge()

        elif task_name == "daily_check":
            self.daily_status_check()

    def setup_schedule(self) -> None:
        """スケジュールを設定"""
        schedule_config = self.config['schedule']

        # 週次生成
        if schedule_config['weekly_generation']['enabled']:
            day = schedule_config['weekly_generation']['day']
            time_str = schedule_config['weekly_generation']['time']

            if day == "monday":
                schedule.every().monday.at(time_str).do(
                    self.run_scheduled_task, "weekly_generation"
                )
                self.log_message(f"📅 週次生成スケジュール設定: 毎週月曜 {time_str}")

        # 日次チェック
        if schedule_config['daily_check']['enabled']:
            time_str = schedule_config['daily_check']['time']
            schedule.every().day.at(time_str).do(
                self.run_scheduled_task, "daily_check"
            )
            self.log_message(f"📅 日次チェックスケジュール設定: 毎日 {time_str}")

    def manual_menu(self) -> None:
        """手動実行メニュー"""
        while True:
            print("\n" + "="*60)
            print("📋 エピソード管理システム")
            print("="*60)

            progress = self.check_phase_progress()
            print(f"\n現在の状態:")
            print(f"  エピソード数: {progress['current_count']}件")
            print(f"  フェーズ: {progress['current_phase']}")
            if progress['remaining']:
                print(f"  目標まで: {progress['remaining']}件")

            print("\n選択してください:")
            print("  1. 週次バッチ生成を実行")
            print("  2. 自動統合を実行")
            print("  3. ステータスチェック")
            print("  4. 次週候補者リスト生成")
            print("  5. スケジューラー開始（自動モード）")
            print("  0. 終了")

            choice = input("\n選択 [0-5]: ")

            if choice == "1":
                self.run_weekly_generation()
            elif choice == "2":
                self.run_auto_merge()
            elif choice == "3":
                self.daily_status_check()
            elif choice == "4":
                subprocess.run(["python3", "next_week_candidates.py"])
            elif choice == "5":
                self.run_scheduler()
            elif choice == "0":
                print("👋 終了します")
                break
            else:
                print("❌ 無効な選択です")

    def run_scheduler(self) -> None:
        """スケジューラーを実行"""
        self.log_message("🤖 自動スケジューラー開始")
        self.setup_schedule()

        print("\n⏳ スケジューラー実行中... (Ctrl+C で停止)")
        print("次回実行予定:")

        jobs = schedule.get_jobs()
        for job in jobs:
            print(f"  - {job}")

        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # 1分ごとにチェック
        except KeyboardInterrupt:
            self.log_message("⏹️ スケジューラー停止")
            print("\n👋 スケジューラーを停止しました")

    def run(self) -> None:
        """メイン実行"""
        if self.config.get('auto_run', False):
            self.run_scheduler()
        else:
            self.manual_menu()

def main():
    scheduler = EpisodeScheduler()
    scheduler.run()

if __name__ == "__main__":
    main()