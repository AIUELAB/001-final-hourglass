"""
n8n統合システムの使用例

このファイルは、n8n統合システムの基本的な使用方法を示しています。
GitHub CopilotやAIアシスタントが提案しやすい、実用的なコード例を提供します。
"""

import os
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# n8nサービスをインポート
try:
    from n8n_integration.services.n8n_service import N8nService, WorkflowInfo, ExecutionInfo
except ImportError:
    print("n8nサービスが見つかりません。パスを確認してください。")
    sys.exit(1)

def main():
    """メイン実行関数"""
    print("🚀 n8n統合システム - 使用例")
    print("=" * 50)

    # 環境変数から設定を取得
    n8n_url = os.getenv('N8N_BASE_URL', 'http://localhost:5678')
    n8n_api_key = os.getenv('N8N_API_KEY')

    print(f"n8n URL: {n8n_url}")
    print(f"API Key: {'設定済み' if n8n_api_key else '未設定'}")
    print()

    # n8nサービスを初期化
    try:
        n8n_service = N8nService(n8n_url, n8n_api_key)
        print("✅ n8nサービスに接続しました")
    except Exception as e:
        print(f"❌ n8nサービスへの接続に失敗: {e}")
        return

    # 基本的な操作例
    demonstrate_basic_operations(n8n_service)

    # ワークフロー管理例
    demonstrate_workflow_management(n8n_service)

    # 実行履歴管理例
    demonstrate_execution_management(n8n_service)

    # 統計・分析例
    demonstrate_analytics(n8n_service)

def demonstrate_basic_operations(n8n_service: N8nService):
    """基本的な操作のデモンストレーション"""
    print("\n📋 基本的な操作")
    print("-" * 30)

    # ワークフロー一覧取得
    try:
        workflows = n8n_service.get_workflows()
        print(f"📊 ワークフロー数: {len(workflows)}")

        if workflows:
            print("最初のワークフロー:")
            workflow = workflows[0]
            print(f"  - 名前: {workflow.name}")
            print(f"  - ステータス: {'アクティブ' if workflow.active else '非アクティブ'}")
            print(f"  - ノード数: {len(workflow.nodes)}")
            print(f"  - タグ: {', '.join(workflow.tags) if workflow.tags else 'なし'}")
    except Exception as e:
        print(f"❌ ワークフロー取得失敗: {e}")

def demonstrate_workflow_management(n8n_service: N8nService):
    """ワークフロー管理のデモンストレーション"""
    print("\n🔧 ワークフロー管理")
    print("-" * 30)

    try:
        # アクティブなワークフローのみ取得
        active_workflows = n8n_service.get_workflows(active_only=True)
        print(f"アクティブなワークフロー: {len(active_workflows)}件")

        # 非アクティブなワークフローのみ取得
        inactive_workflows = [w for w in n8n_service.get_workflows() if not w.active]
        print(f"非アクティブなワークフロー: {len(inactive_workflows)}件")

        # ワークフロー検索
        if active_workflows:
            search_results = n8n_service.search_workflows("test")
            print(f"検索結果 ('test'): {len(search_results)}件")

    except Exception as e:
        print(f"❌ ワークフロー管理失敗: {e}")

def demonstrate_execution_management(n8n_service: N8nService):
    """実行履歴管理のデモンストレーション"""
    print("\n📈 実行履歴管理")
    print("-" * 30)

    try:
        # 実行履歴取得
        executions = n8n_service.get_executions(limit=10)
        print(f"最新の実行履歴: {len(executions)}件")

        if executions:
            # 成功した実行の数
            success_count = len([e for e in executions if e.status.value == 'success'])
            error_count = len([e for e in executions if e.status.value == 'error'])
            running_count = len([e for e in executions if e.status.value == 'running'])

            print(f"  - 成功: {success_count}件")
            print(f"  - エラー: {error_count}件")
            print(f"  - 実行中: {running_count}件")

            # 最新の実行詳細
            latest_execution = executions[0]
            print(f"\n最新の実行:")
            print(f"  - ワークフロー: {latest_execution.workflow_name}")
            print(f"  - ステータス: {latest_execution.status.value}")
            print(f"  - 開始時刻: {latest_execution.started_at}")
            if latest_execution.duration:
                print(f"  - 実行時間: {latest_execution.duration}ms")

    except Exception as e:
        print(f"❌ 実行履歴管理失敗: {e}")

def demonstrate_analytics(n8n_service: N8nService):
    """統計・分析のデモンストレーション"""
    print("\n📊 統計・分析")
    print("-" * 30)

    try:
        # ワークフロー統計
        workflow_stats = n8n_service.get_workflow_stats()
        print("ワークフロー統計:")
        print(f"  - 総数: {workflow_stats.get('total', 0)}")
        print(f"  - アクティブ: {workflow_stats.get('active', 0)}")
        print(f"  - 非アクティブ: {workflow_stats.get('inactive', 0)}")
        print(f"  - 総ノード数: {workflow_stats.get('total_nodes', 0)}")
        print(f"  - 総接続数: {workflow_stats.get('total_connections', 0)}")

        # タグ統計
        tags = workflow_stats.get('tags', {})
        if tags:
            print("  - タグ分布:")
            for tag, count in sorted(tags.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"    {tag}: {count}件")

        # 実行履歴統計
        execution_stats = n8n_service.get_execution_stats()
        print(f"\n実行履歴統計:")
        print(f"  - 総実行数: {execution_stats.get('total', 0)}")
        print(f"  - 成功: {execution_stats.get('success', 0)}")
        print(f"  - エラー: {execution_stats.get('error', 0)}")
        print(f"  - 実行中: {execution_stats.get('running', 0)}")
        print(f"  - 平均実行時間: {execution_stats.get('average_duration', 0):.2f}ms")

    except Exception as e:
        print(f"❌ 統計・分析失敗: {e}")

def demonstrate_workflow_operations(n8n_service: N8nService):
    """ワークフロー操作のデモンストレーション"""
    print("\n⚙️ ワークフロー操作")
    print("-" * 30)

    try:
        workflows = n8n_service.get_workflows()
        if not workflows:
            print("操作可能なワークフローがありません")
            return

        # 最初のワークフローで操作をデモ
        workflow = workflows[0]
        print(f"対象ワークフロー: {workflow.name} (ID: {workflow.id})")
        print(f"現在のステータス: {'アクティブ' if workflow.active else '非アクティブ'}")

        # 注意: 実際の操作はコメントアウト
        print("\n⚠️ 以下の操作は実際には実行されません（デモ用）")

        # ワークフロー有効化/無効化
        if workflow.active:
            print(f"  - 無効化: n8n_service.deactivate_workflow('{workflow.id}')")
        else:
            print(f"  - 有効化: n8n_service.activate_workflow('{workflow.id}')")

        # ワークフロー実行
        print(f"  - 実行: n8n_service.execute_workflow('{workflow.id}')")

        # ワークフローエクスポート
        print(f"  - エクスポート: n8n_service.export_workflow('{workflow.id}')")

    except Exception as e:
        print(f"❌ ワークフロー操作失敗: {e}")

def create_sample_workflow():
    """サンプルワークフローの作成例"""
    print("\n📝 サンプルワークフロー作成")
    print("-" * 30)

    sample_workflow = {
        "name": "サンプルワークフロー",
        "nodes": [
            {
                "id": "start",
                "name": "開始",
                "type": "n8n-nodes-base.start",
                "typeVersion": 1,
                "position": [240, 300]
            },
            {
                "id": "http_request",
                "name": "HTTPリクエスト",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4,
                "position": [460, 300],
                "parameters": {
                    "url": "https://api.example.com/data",
                    "method": "GET"
                }
            }
        ],
        "connections": {
            "開始": {
                "main": [
                    [
                        {
                            "node": "HTTPリクエスト",
                            "type": "main",
                            "index": 0
                        }
                    ]
                ]
            }
        },
        "active": False,
        "tags": ["サンプル", "デモ"]
    }

    print("サンプルワークフロー構造:")
    print(f"  - 名前: {sample_workflow['name']}")
    print(f"  - ノード数: {len(sample_workflow['nodes'])}")
    print(f"  - タグ: {', '.join(sample_workflow['tags'])}")

    return sample_workflow

if __name__ == "__main__":
    try:
        main()
        print("\n✅ デモンストレーション完了")
    except KeyboardInterrupt:
        print("\n\n⏹️ ユーザーによって中断されました")
    except Exception as e:
        print(f"\n❌ 予期しないエラー: {e}")
        import traceback
        traceback.print_exc()
