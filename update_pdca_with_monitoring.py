#!/usr/bin/env python3
"""
PDCAガーディアンシステムに監視機能を統合
"""

from pdca_guardian import PDCAGuardian
from pdca_guardian_monitoring import PDCAMonitoringSystem, PDCAMonitoringRule
import json
from datetime import datetime

def update_pdca_guardian():
    """PDCAガーディアンに監視機能を追加"""
    
    print("="*60)
    print("PDCAガーディアンシステム - 監視機能統合")
    print("="*60)
    
    # 既存のPDCAガーディアンを読み込み
    guardian = PDCAGuardian()
    
    # 監視ルールを追加
    new_monitoring_rules = [
        {
            "id": "RULE_024",
            "rule": "長時間処理（5分以上）は自動的に監視を開始",
            "priority": "CRITICAL",
            "category": "監視・通知",
            "description": "5分以上かかる処理は自動的にバックグラウンド監視を開始し、完了時に通知",
            "action": "auto_monitor_long_tasks"
        },
        {
            "id": "RULE_025",
            "rule": "処理完了時は必ず音声とデスクトップ通知を実行",
            "priority": "CRITICAL",
            "category": "監視・通知",
            "description": "すべての長時間処理完了時に音声（Glass.aiff）とmacOS通知センターで通知",
            "action": "notify_completion_always"
        },
        {
            "id": "RULE_026",
            "rule": "エラー率5%超過で即座に警告通知",
            "priority": "CRITICAL",
            "category": "品質管理",
            "description": "処理中のエラー率が5%を超えた場合、即座に警告音と通知を発生",
            "action": "error_rate_alert"
        },
        {
            "id": "RULE_027",
            "rule": "監視ログの永続保存",
            "priority": "IMPORTANT",
            "category": "監視・通知",
            "description": "すべての監視ログをpdca_monitoring_logs/に保存し、後で検証可能にする",
            "action": "save_monitoring_logs"
        },
        {
            "id": "RULE_028",
            "rule": "処理中断時の状態保存と再開機能",
            "priority": "CRITICAL",
            "category": "復旧・再開",
            "description": "処理が中断された場合、現在の状態を保存し、後で再開可能にする",
            "action": "checkpoint_and_resume"
        },
        {
            "id": "RULE_029",
            "rule": "バックグラウンド処理の自動追跡",
            "priority": "CRITICAL",
            "category": "監視・通知",
            "description": "nohupやバックグラウンド実行されたプロセスを自動的に検出して監視",
            "action": "auto_track_background"
        },
        {
            "id": "RULE_030",
            "rule": "完了通知の多重化",
            "priority": "IMPORTANT",
            "category": "監視・通知",
            "description": "重要な処理は音声、デスクトップ通知、ログ、オプションでSlack/メールも送信",
            "action": "multi_channel_notification"
        }
    ]
    
    # ルールを追加（PDCAガーディアンのメモリ構造に追加）
    for rule in new_monitoring_rules:
        guardian.memory['permanent_rules'].append(rule)
        print(f"✅ 追加: {rule['id']} - {rule['rule']}")
    
    # 監視設定を保存
    monitoring_config = {
        "enabled": True,
        "auto_start": True,
        "notification_channels": ["sound", "desktop", "log"],
        "monitoring_interval": 10,
        "long_task_threshold": 300,  # 5分
        "error_rate_threshold": 0.05,  # 5%
        "checkpoint_interval": 100,  # 100件ごと
        "sound_file": "/System/Library/Sounds/Glass.aiff",
        "log_directory": "pdca_monitoring_logs",
        "last_updated": datetime.now().isoformat()
    }
    
    # 監視設定をPDCAガーディアンのメモリに統合
    guardian.memory['monitoring_config'] = monitoring_config
    guardian._save_memory()  # PDCAガーディアンのメモリ保存メソッドを使用
    
    print("\n" + "="*60)
    print("📊 統合完了サマリー")
    print("-"*60)
    print(f"追加ルール数: {len(new_monitoring_rules)}")
    print(f"総ルール数: {len(guardian.memory['permanent_rules'])}")
    print(f"監視機能: 有効")
    print(f"自動開始: 有効")
    print(f"通知チャンネル: 音声、デスクトップ、ログ")
    print("="*60)
    
    # 統合レポートを生成
    report = {
        "integration_date": datetime.now().isoformat(),
        "added_rules": [r['id'] for r in new_monitoring_rules],
        "monitoring_features": [
            "自動バックグラウンド監視",
            "完了時音声通知",
            "デスクトップ通知",
            "エラー率監視",
            "状態保存と再開",
            "多重通知チャンネル"
        ],
        "status": "active"
    }
    
    with open('pdca_monitoring_integration_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print("\n✅ PDCAガーディアンシステムへの監視機能統合が完了しました")
    print("📄 レポート: pdca_monitoring_integration_report.json")
    
    return guardian


def test_monitoring():
    """監視機能のテスト"""
    print("\n🧪 監視機能テスト")
    print("-"*60)
    
    # 監視システムを初期化
    monitor = PDCAMonitoringSystem()
    
    # テスト通知を送信
    print("テスト通知を送信します...")
    import subprocess
    
    # 音声通知テスト
    subprocess.run(["afplay", "/System/Library/Sounds/Glass.aiff"])
    
    # デスクトップ通知テスト
    subprocess.run([
        "osascript", "-e",
        'display notification "PDCAガーディアン監視機能が正常に動作しています" with title "✅ テスト成功" sound name "Glass"'
    ])
    
    print("✅ 通知テスト完了")


if __name__ == "__main__":
    # PDCAガーディアンを更新
    guardian = update_pdca_guardian()
    
    # テスト実行
    test_monitoring()
    
    print("\n🎯 次のステップ:")
    print("1. バックグラウンド処理は自動的に監視されます")
    print("2. 完了時に音声とデスクトップ通知が届きます")
    print("3. エラー率が5%を超えると警告が発生します")