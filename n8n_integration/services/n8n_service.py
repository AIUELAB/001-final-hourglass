"""
n8n API操作サービス

このモジュールは、n8nワークフローエンジンとの通信を担当します。
GitHub CopilotやAIアシスタントが提案しやすい、明確なインターフェースを提供します。
"""

import requests
import logging
from typing import Dict, List, Any, Optional
from enum import Enum

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WorkflowStatus(Enum):
    """ワークフローのステータス"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"

class ExecutionStatus(Enum):
    """実行のステータス"""
    SUCCESS = "success"
    ERROR = "error"
    RUNNING = "running"
    WAITING = "waiting"
    CANCELED = "canceled"

class WorkflowInfo:
    """ワークフロー情報"""
    def __init__(self, id: str, name: str, active: bool, nodes: List[Dict[str, Any]],
                 connections: Dict[str, Any], created_at: str, updated_at: str,
                 tags: List[str], version_id: Optional[str] = None,
                 meta: Optional[Dict[str, Any]] = None):
        self.id = id
        self.name = name
        self.active = active
        self.nodes = nodes
        self.connections = connections
        self.created_at = created_at
        self.updated_at = updated_at
        self.tags = tags
        self.version_id = version_id
        self.meta = meta

class ExecutionInfo:
    """実行履歴情報"""
    def __init__(self, id: str, workflow_id: str, workflow_name: str,
                 status: ExecutionStatus, started_at: str,
                 finished_at: Optional[str] = None, duration: Optional[int] = None,
                 error: Optional[str] = None, data: Optional[Dict[str, Any]] = None):
        self.id = id
        self.workflow_id = workflow_id
        self.workflow_name = workflow_name
        self.status = status
        self.started_at = started_at
        self.finished_at = finished_at
        self.duration = duration
        self.error = error
        self.data = data

class N8nService:
    """
    n8n API操作サービス

    このクラスは、n8nワークフローエンジンとの通信を抽象化し、
    簡単に使用できるインターフェースを提供します。
    """

    def __init__(self, base_url: str, api_key: Optional[str] = None, timeout: int = 30):
        """
        n8nサービスを初期化

        Args:
            base_url: n8nのベースURL (例: http://localhost:5678)
            api_key: n8n APIキー（オプション）
            timeout: リクエストタイムアウト（秒）
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()

        # ヘッダー設定
        if self.api_key:
            self.session.headers.update({'X-N8N-API-KEY': self.api_key})

        # 接続テスト
        self._test_connection()

    def _test_connection(self) -> bool:
        """n8nへの接続をテスト"""
        try:
            response = self.session.get(f"{self.base_url}/api/v1/health", timeout=5)
            if response.status_code == 200:
                logger.info("n8n接続成功")
                return True
            else:
                logger.warning(f"n8n接続警告: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"n8n接続失敗: {e}")
            return False

    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """
        n8n APIへのリクエストを実行

        Args:
            method: HTTPメソッド (GET, POST, PUT, DELETE)
            endpoint: APIエンドポイント
            **kwargs: リクエストパラメータ

        Returns:
            requests.Response: レスポンスオブジェクト

        Raises:
            requests.RequestException: リクエストエラー
        """
        url = f"{self.base_url}{endpoint}"
        kwargs.setdefault('timeout', self.timeout)

        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            logger.error(f"n8n APIリクエスト失敗: {method} {endpoint} - {e}")
            raise

    # ワークフロー管理メソッド

    def get_workflows(self, active_only: bool = False) -> List[WorkflowInfo]:
        """
        ワークフロー一覧を取得

        Args:
            active_only: アクティブなワークフローのみ取得するか

        Returns:
            List[WorkflowInfo]: ワークフロー情報のリスト
        """
        try:
            response = self._make_request('GET', '/api/v1/workflows')
            workflows_data = response.json()

            workflows = []
            for workflow_data in workflows_data:
                workflow = WorkflowInfo(
                    id=workflow_data.get('id'),
                    name=workflow_data.get('name'),
                    active=workflow_data.get('active', False),
                    nodes=workflow_data.get('nodes', []),
                    connections=workflow_data.get('connections', {}),
                    created_at=workflow_data.get('createdAt'),
                    updated_at=workflow_data.get('updatedAt'),
                    tags=workflow_data.get('tags', []),
                    version_id=workflow_data.get('versionId'),
                    meta=workflow_data.get('meta')
                )

                if not active_only or workflow.active:
                    workflows.append(workflow)

            logger.info(f"{len(workflows)}件のワークフローを取得")
            return workflows

        except Exception as e:
            logger.error(f"ワークフロー取得失敗: {e}")
            raise

    def get_workflow(self, workflow_id: str) -> Optional[WorkflowInfo]:
        """
        特定のワークフローを取得

        Args:
            workflow_id: ワークフローID

        Returns:
            Optional[WorkflowInfo]: ワークフロー情報、見つからない場合はNone
        """
        try:
            response = self._make_request('GET', f'/api/v1/workflows/{workflow_id}')
            workflow_data = response.json()

            workflow = WorkflowInfo(
                id=workflow_data.get('id'),
                name=workflow_data.get('name'),
                active=workflow_data.get('active', False),
                nodes=workflow_data.get('nodes', []),
                connections=workflow_data.get('connections', {}),
                created_at=workflow_data.get('createdAt'),
                updated_at=workflow_data.get('updatedAt'),
                tags=workflow_data.get('tags', []),
                version_id=workflow_data.get('versionId'),
                meta=workflow_data.get('meta')
            )

            logger.info(f"ワークフロー '{workflow.name}' を取得")
            return workflow

        except Exception as e:
            logger.error(f"ワークフロー取得失敗 (ID: {workflow_id}): {e}")
            return None

    def activate_workflow(self, workflow_id: str) -> bool:
        """
        ワークフローを有効化

        Args:
            workflow_id: ワークフローID

        Returns:
            bool: 成功した場合はTrue
        """
        try:
            self._make_request('POST', f'/api/v1/workflows/{workflow_id}/activate')
            logger.info(f"ワークフロー {workflow_id} を有効化")
            return True
        except Exception as e:
            logger.error(f"ワークフロー有効化失敗 (ID: {workflow_id}): {e}")
            return False

    def deactivate_workflow(self, workflow_id: str) -> bool:
        """
        ワークフローを無効化

        Args:
            workflow_id: ワークフローID

        Returns:
            bool: 成功した場合はTrue
        """
        try:
            self._make_request('POST', f'/api/v1/workflows/{workflow_id}/deactivate')
            logger.info(f"ワークフロー {workflow_id} を無効化")
            return True
        except Exception as e:
            logger.error(f"ワークフロー無効化失敗 (ID: {workflow_id}): {e}")
            return False

    def execute_workflow(self, workflow_id: str, data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        ワークフローを実行

        Args:
            workflow_id: ワークフローID
            data: 実行データ（オプション）

        Returns:
            Optional[str]: 実行ID、失敗した場合はNone
        """
        try:
            payload = data or {}
            response = self._make_request('POST', f'/api/v1/workflows/{workflow_id}/execute', json=payload)
            result = response.json()
            execution_id = result.get('id')

            logger.info(f"ワークフロー {workflow_id} を実行 (実行ID: {execution_id})")
            return execution_id

        except Exception as e:
            logger.error(f"ワークフロー実行失敗 (ID: {workflow_id}): {e}")
            return None

    # 実行履歴管理メソッド

    def get_executions(self, workflow_id: Optional[str] = None, limit: int = 100) -> List[ExecutionInfo]:
        """
        実行履歴を取得

        Args:
            workflow_id: 特定のワークフローのみ取得する場合のID
            limit: 取得件数の上限

        Returns:
            List[ExecutionInfo]: 実行履歴のリスト
        """
        try:
            endpoint = '/api/v1/executions'
            params = {'limit': limit}

            if workflow_id:
                params['workflowId'] = workflow_id

            response = self._make_request('GET', endpoint, params=params)
            executions_data = response.json()

            executions = []
            for execution_data in executions_data.get('data', []):
                execution = ExecutionInfo(
                    id=execution_data.get('id'),
                    workflow_id=execution_data.get('workflowId'),
                    workflow_name=execution_data.get('workflowName'),
                    status=ExecutionStatus(execution_data.get('status', 'unknown')),
                    started_at=execution_data.get('startedAt'),
                    finished_at=execution_data.get('finishedAt'),
                    duration=execution_data.get('duration'),
                    error=execution_data.get('error'),
                    data=execution_data.get('data')
                )
                executions.append(execution)

            logger.info(f"{len(executions)}件の実行履歴を取得")
            return executions

        except Exception as e:
            logger.error(f"実行履歴取得失敗: {e}")
            raise

    def get_execution(self, execution_id: str) -> Optional[ExecutionInfo]:
        """
        特定の実行履歴を取得

        Args:
            execution_id: 実行ID

        Returns:
            Optional[ExecutionInfo]: 実行履歴、見つからない場合はNone
        """
        try:
            response = self._make_request('GET', f'/api/v1/executions/{execution_id}')
            execution_data = response.json()

            execution = ExecutionInfo(
                id=execution_data.get('id'),
                workflow_id=execution_data.get('workflowId'),
                workflow_name=execution_data.get('workflowName'),
                status=ExecutionStatus(execution_data.get('status', 'unknown')),
                started_at=execution_data.get('startedAt'),
                finished_at=execution_data.get('finishedAt'),
                duration=execution_data.get('duration'),
                error=execution_data.get('error'),
                data=execution_data.get('data')
            )

            logger.info(f"実行履歴 {execution_id} を取得")
            return execution

        except Exception as e:
            logger.error(f"実行履歴取得失敗 (ID: {execution_id}): {e}")
            return None

    # 統計・分析メソッド

    def get_workflow_stats(self) -> Dict[str, Any]:
        """
        ワークフローの統計情報を取得

        Returns:
            Dict[str, Any]: 統計情報
        """
        try:
            workflows = self.get_workflows()

            stats = {
                'total': len(workflows),
                'active': len([w for w in workflows if w.active]),
                'inactive': len([w for w in workflows if not w.active]),
                'total_nodes': sum(len(w.nodes) for w in workflows),
                'total_connections': sum(len(w.connections) for w in workflows),
                'tags': {}
            }

            # タグ統計
            for workflow in workflows:
                for tag in workflow.tags:
                    if tag in stats['tags']:
                        stats['tags'][tag] += 1
                    else:
                        stats['tags'][tag] = 1

            logger.info("ワークフロー統計を取得")
            return stats

        except Exception as e:
            logger.error(f"統計情報取得失敗: {e}")
            return {}

    def get_execution_stats(self, workflow_id: Optional[str] = None) -> Dict[str, Any]:
        """
        実行履歴の統計情報を取得

        Args:
            workflow_id: 特定のワークフローのみ統計を取得する場合のID

        Returns:
            Dict[str, Any]: 統計情報
        """
        try:
            executions = self.get_executions(workflow_id)

            stats = {
                'total': len(executions),
                'success': len([e for e in executions if e.status == ExecutionStatus.SUCCESS]),
                'error': len([e for e in executions if e.status == ExecutionStatus.ERROR]),
                'running': len([e for e in executions if e.status == ExecutionStatus.RUNNING]),
                'average_duration': 0
            }

            # 平均実行時間を計算
            completed_executions = [e for e in executions if e.duration is not None]
            if completed_executions:
                total_duration = sum(e.duration for e in completed_executions)
                stats['average_duration'] = total_duration / len(completed_executions)

            logger.info("実行履歴統計を取得")
            return stats

        except Exception as e:
            logger.error(f"実行履歴統計取得失敗: {e}")
            return {}

    # ユーティリティメソッド

    def search_workflows(self, query: str) -> List[WorkflowInfo]:
        """
        ワークフローを検索

        Args:
            query: 検索クエリ

        Returns:
            List[WorkflowInfo]: 検索結果
        """
        try:
            workflows = self.get_workflows()
            query_lower = query.lower()

            results = []
            for workflow in workflows:
                if (query_lower in workflow.name.lower() or
                    any(query_lower in tag.lower() for tag in workflow.tags)):
                    results.append(workflow)

            logger.info(f"ワークフロー検索: '{query}' -> {len(results)}件")
            return results

        except Exception as e:
            logger.error(f"ワークフロー検索失敗: {e}")
            return []

    def export_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        ワークフローをエクスポート

        Args:
            workflow_id: ワークフローID

        Returns:
            Optional[Dict[str, Any]]: エクスポートデータ、失敗した場合はNone
        """
        try:
            response = self._make_request('GET', f'/api/v1/workflows/{workflow_id}/export')
            export_data = response.json()

            logger.info(f"ワークフロー {workflow_id} をエクスポート")
            return export_data

        except Exception as e:
            logger.error(f"ワークフローエクスポート失敗 (ID: {workflow_id}): {e}")
            return None

    def import_workflow(self, workflow_data: Dict[str, Any]) -> Optional[str]:
        """
        ワークフローをインポート

        Args:
            workflow_data: インポートするワークフローデータ

        Returns:
            Optional[str]: インポートされたワークフローのID、失敗した場合はNone
        """
        try:
            response = self._make_request('POST', '/api/v1/workflows/import', json=workflow_data)
            result = response.json()
            workflow_id = result.get('id')

            logger.info(f"ワークフローをインポート (ID: {workflow_id})")
            return workflow_id

        except Exception as e:
            logger.error(f"ワークフローインポート失敗: {e}")
            return None

    def __enter__(self):
        """コンテキストマネージャー対応"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャー対応"""
        self.session.close()
