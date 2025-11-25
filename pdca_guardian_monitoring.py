#!/usr/bin/env python3
"""
PDCAガーディアン - 処理監視・通知システム
長時間処理の自動監視と完了通知を実装
"""

import json
import time
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import threading
import os

class PDCAMonitoringSystem:
    """PDCAガーディアン処理監視システム"""

    def __init__(self):
        self.config_file = 'pdca_monitoring_config.json'
        self.monitoring_threads = {}
        self.load_config()

    def load_config(self):
        """監視設定を読み込み"""
        default_config = {
            "monitoring_rules": {
                "auto_monitor_long_tasks": True,
                "notification_enabled": True,
                "sound_enabled": True,
                "desktop_notification": True,
                "monitoring_interval": 10,  # 秒
                "completion_check_patterns": [
                    "処理完了",
                    "全件処理完了",
                    "4701/4701",
                    "100.0%"
                ]
            },
            "notification_settings": {
                "sound_file": "/System/Library/Sounds/Glass.aiff",
                "notification_title": "✅ 処理完了",
                "notification_subtitle": "PDCAガーディアンシステム",
                "slack_webhook": None,  # Optional
                "email_notification": None  # Optional
            },
            "monitoring_tasks": []
        }

        if Path(self.config_file).exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        else:
            self.config = default_config
            self.save_config()

    def save_config(self):
        """設定を保存"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

    def register_task(self, task_name: str, process_id: int = None,
                     log_file: str = None, target_count: int = None):
        """監視タスクを登録"""
        task = {
            "name": task_name,
            "process_id": process_id,
            "log_file": log_file,
            "target_count": target_count,
            "start_time": datetime.now().isoformat(),
            "status": "monitoring",
            "progress": 0
        }

        self.config['monitoring_tasks'].append(task)
        self.save_config()

        # 監視スレッドを開始
        if self.config['monitoring_rules']['auto_monitor_long_tasks']:
            thread = threading.Thread(
                target=self._monitor_task,
                args=(task,),
                daemon=True
            )
            thread.start()
            self.monitoring_threads[task_name] = thread

        return task

    def _monitor_task(self, task: Dict):
        """タスクを監視"""
        print(f"🔍 監視開始: {task['name']}")

        while task['status'] == 'monitoring':
            # プロセス確認
            if task.get('process_id'):
                if not self._check_process(task['process_id']):
                    task['status'] = 'process_ended'
                    self._notify_completion(task, "プロセスが終了しました")
                    break

            # ログファイル確認
            if task.get('log_file') and Path(task['log_file']).exists():
                progress, completed = self._check_log_progress(
                    task['log_file'],
                    task.get('target_count')
                )

                task['progress'] = progress

                if completed:
                    task['status'] = 'completed'
                    self._notify_completion(task, "処理が正常に完了しました")
                    break

            # 監視間隔で待機
            time.sleep(self.config['monitoring_rules']['monitoring_interval'])

        # タスク状態を更新
        self._update_task_status(task)

    def _check_process(self, pid: int) -> bool:
        """プロセスが実行中か確認"""
        try:
            result = subprocess.run(
                ["ps", "-p", str(pid)],
                capture_output=True,
                text=True
            )
            return str(pid) in result.stdout
        except:
            return False

    def _check_log_progress(self, log_file: str, target_count: int = None):
        """ログファイルから進捗を確認"""
        progress = 0
        completed = False

        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

                # 最後の100行から進捗を探す
                for line in reversed(lines[-100:]):
                    # 完了パターンチェック
                    for pattern in self.config['monitoring_rules']['completion_check_patterns']:
                        if pattern in line:
                            completed = True
                            progress = 100
                            break

                    # 進捗パターンチェック
                    if '進捗:' in line and not completed:
                        try:
                            parts = line.split('進捗:')[1].strip()
                            # "1234/4701 (26.3%)" のようなパターンを解析
                            if '/' in parts:
                                current = int(parts.split('/')[0])
                                total = int(parts.split('/')[1].split()[0])
                                progress = (current / total) * 100
                        except:
                            pass

                    if completed:
                        break
        except:
            pass

        return progress, completed

    def _notify_completion(self, task: Dict, message: str):
        """完了通知を送信"""
        print(f"\n{'='*60}")
        print(f"✅ {task['name']} - {message}")
        print(f"{'='*60}")

        if not self.config['notification_settings']['notification_enabled']:
            return

        # デスクトップ通知
        if self.config['notification_settings']['desktop_notification']:
            self._send_desktop_notification(task, message)

        # 音声通知
        if self.config['notification_settings']['sound_enabled']:
            self._play_sound()

        # Slack通知（設定されている場合）
        if self.config['notification_settings'].get('slack_webhook'):
            self._send_slack_notification(task, message)

        # 結果ファイルの確認と表示
        self._display_results(task)

    def _send_desktop_notification(self, task: Dict, message: str):
        """デスクトップ通知を送信"""
        try:
            title = self.config['notification_settings']['notification_title']
            subtitle = self.config['notification_settings']['notification_subtitle']

            script = f'''
            display notification "{message}" with title "{title}" subtitle "{task['name']}" sound name "Glass"
            '''

            subprocess.run(["osascript", "-e", script])
        except:
            pass

    def _play_sound(self):
        """音声を再生"""
        try:
            sound_file = self.config['notification_settings']['sound_file']
            subprocess.run(["afplay", sound_file])
        except:
            pass

    def _send_slack_notification(self, task: Dict, message: str):
        """Slack通知を送信"""
        # 実装は省略（必要に応じて追加）
        pass

    def _display_results(self, task: Dict):
        """結果ファイルを表示"""
        # 結果ファイルを探す
        result_patterns = [
            'recognition_results_ALL_*.csv',
            'recognition_results_ALL_*_stats.json',
            'FINAL_REPORT_*.md'
        ]

        print("\n📁 生成ファイル:")
        for pattern in result_patterns:
            files = list(Path('.').glob(pattern))
            if files:
                latest = max(files, key=lambda f: f.stat().st_mtime)
                print(f"  {latest}")

                # 統計情報を表示
                if pattern.endswith('_stats.json'):
                    try:
                        with open(latest, 'r', encoding='utf-8') as f:
                            stats = json.load(f)
                            if 'stats' in stats:
                                s = stats['stats']
                                print(f"\n📊 処理統計:")
                                print(f"  処理件数: {s.get('total_processed', 0):,}")
                                print(f"  削除候補: {s.get('deletion_candidates', 0):,}")
                                print(f"  削除率: {s.get('deletion_candidates', 0) / max(s.get('total_processed', 1), 1) * 100:.1f}%")
                                print(f"  Wikipedia発見: {s.get('wikipedia_found', 0):,}")
                    except:
                        pass

    def _update_task_status(self, task: Dict):
        """タスク状態を更新"""
        # 設定ファイルのタスクリストを更新
        for i, t in enumerate(self.config['monitoring_tasks']):
            if t['name'] == task['name']:
                self.config['monitoring_tasks'][i] = task
                break

        self.save_config()

    def list_active_tasks(self) -> List[Dict]:
        """アクティブな監視タスクをリスト"""
        active_tasks = [
            task for task in self.config['monitoring_tasks']
            if task['status'] == 'monitoring'
        ]
        return active_tasks

    def stop_monitoring(self, task_name: str):
        """特定タスクの監視を停止"""
        for task in self.config['monitoring_tasks']:
            if task['name'] == task_name:
                task['status'] = 'stopped'
                break

        self.save_config()


# PDCAガーディアンルールとして追加
class PDCAMonitoringRule:
    """PDCAガーディアン監視ルール"""

    MONITORING_RULES = [
        {
            "id": "RULE_024",
            "rule": "長時間処理（5分以上）は自動的に監視を開始",
            "priority": "CRITICAL",
            "action": "auto_monitor",
            "threshold": 300  # 秒
        },
        {
            "id": "RULE_025",
            "rule": "処理完了時は必ず音声とデスクトップ通知を実行",
            "priority": "CRITICAL",
            "action": "notify_completion",
            "notification_types": ["sound", "desktop", "log"]
        },
        {
            "id": "RULE_026",
            "rule": "エラー率が5%を超えた場合は即座に警告通知",
            "priority": "CRITICAL",
            "action": "error_alert",
            "error_threshold": 0.05
        },
        {
            "id": "RULE_027",
            "rule": "監視ログは常に保存し、後で検証可能にする",
            "priority": "IMPORTANT",
            "action": "save_monitoring_log"
        },
        {
            "id": "RULE_028",
            "rule": "処理中断時は状態を保存して再開可能にする",
            "priority": "CRITICAL",
            "action": "save_checkpoint"
        }
    ]

    @staticmethod
    def apply_rules(monitoring_system: PDCAMonitoringSystem):
        """監視ルールを適用"""
        print("📋 PDCAガーディアン監視ルールを適用中...")

        # ルールを設定に反映
        monitoring_system.config['pdca_rules'] = PDCAMonitoringRule.MONITORING_RULES
        monitoring_system.save_config()

        print(f"✅ {len(PDCAMonitoringRule.MONITORING_RULES)}個の監視ルールを適用しました")


def main():
    """使用例"""
    # 監視システムを初期化
    monitor = PDCAMonitoringSystem()

    # PDCAルールを適用
    PDCAMonitoringRule.apply_rules(monitor)

    # 現在の処理を監視登録
    task = monitor.register_task(
        task_name="Wikipedia知名度評価（4,701件）",
        process_id=71408,  # 実際のPID
        log_file="recognition_full_20250908_202451.log",
        target_count=4701
    )

    print(f"✅ タスク '{task['name']}' の監視を開始しました")
    print(f"   PID: {task['process_id']}")
    print(f"   ログ: {task['log_file']}")
    print(f"   目標: {task['target_count']}件")

    # アクティブタスクを表示
    active = monitor.list_active_tasks()
    if active:
        print(f"\n📋 監視中のタスク: {len(active)}個")
        for t in active:
            print(f"  - {t['name']} (進捗: {t['progress']:.1f}%)")


if __name__ == "__main__":
    main()
