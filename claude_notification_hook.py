#!/usr/bin/env python3
"""
Claude Code用通知フック
タスク完了時とユーザー入力待機時に自動的に音を鳴らす
"""

import functools
import sys
import time

from simple_notification import notify_complete, notify_error, notify_success, notify_waiting


class ClaudeNotificationHook:
    """Claude Code用の通知フックシステム"""
    
    def __init__(self):
        self.task_running = False
        self.start_time = None
        
    def task_start(self, task_name: str = "タスク"):
        """タスク開始時"""
        self.task_running = True
        self.start_time = time.time()
        print(f"🚀 {task_name}を開始します...")
        
    def task_complete(self, task_name: str = "タスク", success: bool = True):
        """タスク完了時"""
        if self.task_running:
            elapsed = time.time() - self.start_time if self.start_time else 0
            self.task_running = False
            
            if success:
                notify_complete(f"{task_name}が完了しました (所要時間: {elapsed:.1f}秒)")
            else:
                notify_error(f"{task_name}が失敗しました")
                
    def waiting_for_input(self):
        """ユーザー入力待機時"""
        notify_waiting("Claude Codeがユーザーの入力を待っています...")

# グローバルフック
_hook = ClaudeNotificationHook()

def with_notification(task_name: str = "処理"):
    """通知付きデコレータ"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            _hook.task_start(task_name)
            try:
                result = func(*args, **kwargs)
                _hook.task_complete(task_name, success=True)
                return result
            except Exception as e:
                _hook.task_complete(task_name, success=False)
                raise e
        return wrapper
    return decorator

def notify_claude_waiting():
    """Claude Codeが待機状態になったことを通知"""
    notify_waiting()
    notify_complete("Claude Codeの処理が完了しました。入力をお待ちしています。")

# データ品質チェック用の統合
@with_notification("データ品質監査")
def run_data_quality_audit():
    """データ品質監査を実行"""
    import json

    from data_quality_audit_improved import ImprovedDataQualityAuditor
    
    # データ読み込み
    with open('final_12410_firebase_20250822_201828.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 監査実行
    auditor = ImprovedDataQualityAuditor()
    report = auditor.audit_data(data)
    
    # 結果表示
    print(f"📊 品質スコア: {((report['summary']['total_records'] - report['summary']['issues_found']) / report['summary']['total_records'] * 100):.1f}%")
    
    return report

# テストスクリプト用の統合
@with_notification("テストスイート実行")
def run_tests():
    """テストを実行"""
    import subprocess
    result = subprocess.run(
        ["python", "test_data_quality_improved.py"],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        notify_success("すべてのテストが成功しました！")
    else:
        notify_error("テストに失敗がありました")
        
    return result.returncode

# 実行例
if __name__ == "__main__":
    print("🎵 Claude Code通知フックのデモ")
    print("=" * 50)
    
    # タスク実行のシミュレーション
    @with_notification("サンプルタスク")
    def sample_task():
        print("処理中...")
        time.sleep(2)
        print("処理完了")
        
    sample_task()
    
    # 待機状態の通知
    print("\n入力待機のシミュレーション...")
    time.sleep(1)
    notify_claude_waiting()
    
    print("\n✅ 通知フックが正常に動作しています！")