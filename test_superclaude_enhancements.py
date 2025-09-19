#!/usr/bin/env python3
"""
SuperClaude Enhancements Test Script
改善機能のテストと動作確認
"""

import sys
import json
from pathlib import Path

# システムパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from src.superclaude_metrics import MetricsTracker, metrics_tracker
from src.superclaude_learning import LearningSystem, learning_system  
from src.superclaude_project_config import ProjectConfigManager, config_manager


def test_metrics_system():
    """メトリクス追跡システムのテスト"""
    print("\n" + "="*60)
    print("📊 メトリクス追跡システムのテスト")
    print("="*60)
    
    # 新しいトラッカーインスタンスを作成
    tracker = MetricsTracker()
    
    # セッション開始
    session_id = tracker.start_session("test_session_001")
    print(f"✅ セッション開始: {session_id}")
    
    # タスク1: データ処理（並列）
    tracker.start_task("データ処理", parallel_count=5)
    tracker.track_tool_usage("mcp__serena__search")
    tracker.track_tool_usage("mcp__github__get_issue")
    tracker.track_mode_usage("orchestration")
    tracker.track_file_operation("read", "ultra_think_data.csv")
    tracker.end_task(success=True, tokens_used=250)
    print("✅ タスク1完了: データ処理（並列5）")
    
    # タスク2: ファイル更新
    tracker.start_task("ファイル更新", parallel_count=1)
    tracker.track_tool_usage("MultiEdit")
    tracker.track_mode_usage("token_efficiency")
    tracker.end_task(success=True, tokens_used=100)
    print("✅ タスク2完了: ファイル更新")
    
    # タスク3: エラーケース
    tracker.start_task("エラータスク", parallel_count=1)
    tracker.end_task(success=False, error="Test error", tokens_used=50)
    print("✅ タスク3完了: エラータスク（失敗）")
    
    # セッション終了とサマリー取得
    summary = tracker.end_session()
    print("\n📊 セッションサマリー:")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    
    # パフォーマンスインサイト取得
    insights = tracker.get_performance_insights()
    print("\n💡 パフォーマンスインサイト:")
    print(json.dumps(insights, indent=2, ensure_ascii=False))
    
    return True


def test_learning_system():
    """学習システムのテスト"""
    print("\n" + "="*60)
    print("🧠 学習システムのテスト")
    print("="*60)
    
    learner = LearningSystem()
    
    # 成功パターンの学習
    context1 = {
        "session_id": "test_001",
        "project_path": "/Users/admin/Documents/AIUELAB/001-final-hourglass",
        "file_path": "ultra_think_data.csv",
        "tool": "python",
        "operation": "sync"
    }
    
    entry_id1 = learner.learn_from_success(
        context=context1,
        action="python3 auto_startup_sync.py",
        result="同期成功: 5558行を更新"
    )
    print(f"✅ 成功パターン学習: {entry_id1}")
    
    # エラーパターンの学習
    context2 = {
        "session_id": "test_001",
        "project_path": "/Users/admin/Documents/AIUELAB/001-final-hourglass",
        "error_type": "ImportError"
    }
    
    entry_id2 = learner.learn_from_error(
        context=context2,
        error="No module named 'pandas'",
        solution="pip install pandas"
    )
    print(f"✅ エラーパターン学習: {entry_id2}")
    
    # プロジェクト規約の学習
    project_path = "/Users/admin/Documents/AIUELAB/001-final-hourglass"
    learner.learn_project_convention(project_path, "test_command", "pytest tests/ -v")
    learner.learn_project_convention(project_path, "format_command", "ruff format src/")
    print("✅ プロジェクト規約学習完了")
    
    # 頻繁な操作の学習
    operation = {
        "command": "python3 auto_startup_sync.py",
        "description": "Google Sheetsと同期",
        "category": "sync"
    }
    learner.learn_frequent_operation(project_path, operation)
    print("✅ 頻繁な操作学習完了")
    
    # 類似パターンの取得
    test_context = {
        "project_path": project_path,
        "operation": "sync"
    }
    similar_patterns = learner.get_similar_patterns(test_context, limit=3)
    print(f"\n🔍 類似パターン発見: {len(similar_patterns)}件")
    
    for pattern in similar_patterns:
        print(f"  - Pattern {pattern.pattern_id}: {pattern.solution[:50]}...")
        print(f"    成功率: {pattern.success_rate:.1%}, 使用回数: {pattern.usage_count}")
    
    # プロジェクト知識の取得
    knowledge = learner.get_project_knowledge(project_path)
    if knowledge:
        print(f"\n📚 プロジェクト知識:")
        print(f"  規約: {knowledge.conventions}")
        print(f"  テストコマンド: {knowledge.test_commands}")
        print(f"  頻繁な操作: {len(knowledge.frequent_operations)}件")
    
    # 学習統計の表示
    stats = learner.get_learning_stats()
    print("\n📈 学習統計:")
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    
    return True


def test_project_config():
    """プロジェクト設定システムのテスト"""
    print("\n" + "="*60)
    print("⚙️ プロジェクト設定システムのテスト")
    print("="*60)
    
    manager = ProjectConfigManager()
    project_path = "/Users/admin/Documents/AIUELAB/001-final-hourglass"
    
    # 既存設定の検出
    config = manager.detect_project_config(project_path)
    if config:
        print(f"✅ 既存設定を検出: {config.project_name}")
    else:
        print("ℹ️ 既存設定なし、新規作成します")
        
        # 新規設定の作成
        config = manager.create_project_config(
            project_path,
            {
                "default_flags": ["--ultrathink", "--parallel"],
                "default_mode": "orchestration",
                "enabled_mcp_servers": ["serena", "github", "context7"],
                "auto_sync": True,
                "auto_test": True,
                "max_parallel_tasks": 15
            }
        )
        print(f"✅ 新規設定作成: {config.project_name}")
    
    # プロジェクトサマリーの表示
    summary = manager.get_project_summary(project_path)
    print("\n📋 プロジェクト設定サマリー:")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    
    # カスタムルールの追加
    rule = {
        "name": "auto_sync_test",
        "trigger": "*.csv change",
        "action": "sync",
        "enabled": True
    }
    manager.add_custom_rule(project_path, rule)
    print("\n✅ カスタムルール追加: auto_sync_test")
    
    # ツールショートカットの設定
    manager.set_tool_shortcut(project_path, "quick_test", "pytest tests/ -v --tb=short")
    print("✅ ショートカット追加: quick_test")
    
    # アクティブな設定の取得（マージ済み）
    active_config = manager.get_active_config(project_path)
    print("\n🔧 アクティブな設定（マージ済み）:")
    print(f"  デフォルトフラグ: {active_config.get('default_flags', [])}")
    print(f"  有効MCPサーバー: {active_config.get('enabled_mcp_servers', [])}")
    print(f"  並列タスク上限: {active_config.get('max_parallel_tasks', 10)}")
    print(f"  自動同期: {active_config.get('auto_sync', False)}")
    
    return True


def main():
    """メインテスト実行"""
    print("\n" + "="*60)
    print("🚀 SuperClaude Enhanced Framework テスト開始")
    print("="*60)
    
    results = []
    
    # 各システムのテスト
    try:
        results.append(("メトリクス追跡", test_metrics_system()))
    except Exception as e:
        print(f"❌ メトリクステストエラー: {e}")
        results.append(("メトリクス追跡", False))
    
    try:
        results.append(("学習システム", test_learning_system()))
    except Exception as e:
        print(f"❌ 学習システムエラー: {e}")
        results.append(("学習システム", False))
    
    try:
        results.append(("プロジェクト設定", test_project_config()))
    except Exception as e:
        print(f"❌ プロジェクト設定エラー: {e}")
        results.append(("プロジェクト設定", False))
    
    # 結果サマリー
    print("\n" + "="*60)
    print("📊 テスト結果サマリー")
    print("="*60)
    
    for name, success in results:
        status = "✅ 成功" if success else "❌ 失敗"
        print(f"{name}: {status}")
    
    # 総合評価
    success_count = sum(1 for _, s in results if s)
    total_count = len(results)
    success_rate = success_count / total_count * 100
    
    print(f"\n総合成功率: {success_rate:.0f}% ({success_count}/{total_count})")
    
    if success_rate == 100:
        print("\n🎉 すべてのテストが成功しました！")
        print("SuperClaude Enhanced Frameworkは正常に動作しています。")
    elif success_rate >= 66:
        print("\n⚠️ 一部のテストが失敗しました。")
        print("ログを確認して問題を修正してください。")
    else:
        print("\n❌ 多くのテストが失敗しました。")
        print("セットアップを確認してください。")
    
    return success_rate == 100


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)