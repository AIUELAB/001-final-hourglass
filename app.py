"""
Docker & n8n統合監視システム

このアプリケーションは、Dockerコンテナの監視とn8nワークフローの管理を
統合したWebベースのUIを提供します。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import threading
import time
import uuid

import docker
import requests
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

# 定数定義
DOCKER_CLIENT_ERROR_MSG = "Dockerクライアントが利用できません"
N8N_BASE_URL = "http://localhost:5678"  # n8nのデフォルトポート
N8N_API_KEY: Optional[str] = None  # 環境変数から取得可能

# Dockerクライアントの初期化
docker_client: Optional[Any] = None
try:
    docker_client = docker.from_env()
except Exception as e:
    print(f"Dockerクライアントの初期化に失敗: {e}")

def get_container_status() -> Dict[str, Any]:
    """Dockerコンテナのステータスを取得"""
    if not docker_client:
        return {"error": DOCKER_CLIENT_ERROR_MSG}

    try:
        containers = docker_client.containers.list(all=True)
        container_data: List[Dict[str, Any]] = []

        for container in containers:
            # コンテナの詳細情報を取得
            container_info: Dict[str, Any] = {
                "id": container.short_id,
                "name": container.name,
                "status": container.status,
                "image": container.image.tags[0] if container.image.tags else container.image.id[:12],
                "created": container.attrs['Created'],
                "ports": container.ports,
                "labels": container.labels
            }

            # ステータスに基づいてアイコンと色を設定
            if container.status == "running":
                container_info["status_icon"] = "running"
                container_info["status_color"] = "green"
            else:
                container_info["status_icon"] = "stopped"
                container_info["status_color"] = "red"

            container_data.append(container_info)

        return {
            "containers": container_data,
            "timestamp": datetime.now().isoformat(),
            "total": len(container_data)
        }

    except Exception as e:
        return {"error": f"コンテナ情報の取得に失敗: {str(e)}"}

def get_n8n_workflows() -> Dict[str, Any]:
    """n8nワークフローを取得"""
    try:
        # n8n APIからワークフローを取得
        headers: Dict[str, str] = {}
        if N8N_API_KEY:
            headers['X-N8N-API-KEY'] = N8N_API_KEY

        response = requests.get(f"{N8N_BASE_URL}/api/v1/workflows", headers=headers, timeout=10)
        response.raise_for_status()

        workflows = response.json()
        workflow_data = []

        for workflow in workflows:
            workflow_info = {
                "id": workflow.get('id'),
                "name": workflow.get('name'),
                "active": workflow.get('active', False),
                "nodes": len(workflow.get('nodes', [])),
                "connections": len(workflow.get('connections', {})),
                "created_at": workflow.get('createdAt'),
                "updated_at": workflow.get('updatedAt'),
                "tags": workflow.get('tags', [])
            }

            # アクティブ状態に基づいてアイコンと色を設定
            if workflow_info["active"]:
                workflow_info["status_icon"] = "active"
                workflow_info["status_color"] = "green"
            else:
                workflow_info["status_icon"] = "inactive"
                workflow_info["status_color"] = "red"

            workflow_data.append(workflow_info)

        return {
            "workflows": workflow_data,
            "timestamp": datetime.now().isoformat(),
            "total": len(workflow_data)
        }

    except requests.exceptions.RequestException as e:
        return {"error": f"n8n APIへの接続に失敗: {str(e)}"}
    except Exception as e:
        return {"error": f"ワークフロー情報の取得に失敗: {str(e)}"}

def get_n8n_executions(workflow_id: Optional[str] = None) -> Dict[str, Any]:
    """n8nワークフローの実行履歴を取得"""
    try:
        headers: Dict[str, str] = {}
        if N8N_API_KEY:
            headers['X-N8N-API-KEY'] = N8N_API_KEY

        url = f"{N8N_BASE_URL}/api/v1/executions"
        if workflow_id:
            url += f"?workflowId={workflow_id}"

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        executions = response.json()
        execution_data = []

        for execution in executions.get('data', []):
            execution_info = {
                "id": execution.get('id'),
                "workflow_id": execution.get('workflowId'),
                "workflow_name": execution.get('workflowName'),
                "status": execution.get('status'),
                "started_at": execution.get('startedAt'),
                "finished_at": execution.get('finishedAt'),
                "duration": execution.get('duration'),
                "error": execution.get('error')
            }

            # ステータスに基づいてアイコンと色を設定
            if execution_info["status"] == "success":
                execution_info["status_icon"] = "success"
                execution_info["status_color"] = "green"
            elif execution_info["status"] == "error":
                execution_info["status_icon"] = "error"
                execution_info["status_color"] = "red"
            else:
                execution_info["status_icon"] = "running"
                execution_info["status_color"] = "blue"

            execution_data.append(execution_info)

        return {
            "executions": execution_data,
            "timestamp": datetime.now().isoformat(),
            "total": len(execution_data)
        }

    except requests.exceptions.RequestException as e:
        return {"error": f"n8n APIへの接続に失敗: {str(e)}"}
    except Exception as e:
        return {"error": f"実行履歴の取得に失敗: {str(e)}"}

# ------------------------------
# 簡易ジョブ進捗トラッカー（メモリ管理）
# 本番用途では Redis/DB + ワーカー導入を推奨
# ------------------------------

# ジョブの状態を保持する辞書（メモリ）
jobs_lock = threading.Lock()
jobs_store: Dict[str, Dict[str, Any]] = {}


def _background_job(job_id: str) -> None:
    """バックグラウンドで進捗を更新する疑似ジョブ"""
    try:
        progress = 0
        message = "開始しました"
        with jobs_lock:
            jobs_store[job_id] = {"progress": progress, "status": "running", "message": message}

        # 疑似的に進捗を増加させる
        while progress < 100:
            time.sleep(0.9)
            progress = min(100, progress + 5 + int(10 * (time.time() % 1)))
            message = "集計中…" if progress < 100 else "完了しました"
            with jobs_lock:
                jobs_store[job_id] = {"progress": progress, "status": "running", "message": message}

        # 完了状態に更新
        with jobs_lock:
            jobs_store[job_id] = {"progress": 100, "status": "done", "message": "完了しました"}
    except Exception as e:
        # エラー時は status=error に更新
        with jobs_lock:
            jobs_store[job_id] = {"progress": 0, "status": "error", "message": f"エラー: {e}"}


@app.route('/api/jobs/start', methods=['POST'])
def api_job_start() -> Any:
    """ジョブを開始し、jobId を返す"""
    try:
        job_id = uuid.uuid4().hex
        # バックグラウンドスレッドで処理を実行
        thread = threading.Thread(target=_background_job, args=(job_id,), daemon=True)
        thread.start()
        return jsonify({"jobId": job_id}), 201
    except Exception as e:
        return jsonify({"error": f"ジョブの開始に失敗しました: {e}"}), 500


@app.route('/api/jobs/progress', methods=['POST'])
def api_job_progress() -> Any:
    """jobId を受け取って現在の進捗を返す"""
    try:
        body = request.get_json(silent=True) or {}
        job_id = body.get('jobId')
        if not job_id or not isinstance(job_id, str):
            return jsonify({"error": "jobId が不正です"}), 400

        with jobs_lock:
            job = jobs_store.get(job_id)

        if not job:
            return jsonify({"error": "ジョブが見つかりません"}), 404

        return jsonify({
            "jobId": job_id,
            "progress": job.get("progress", 0),
            "status": job.get("status", "running"),
            "message": job.get("message", "")
        })
    except Exception as e:
        return jsonify({"error": f"進捗の取得に失敗しました: {e}"}), 500

@app.route('/')
def index() -> Any:
    """メインページ"""
    return render_template('index.html')

@app.route('/api/containers')
def api_containers() -> Any:
    """コンテナステータスAPI"""
    return jsonify(get_container_status())

@app.route('/api/n8n/workflows')
def api_n8n_workflows() -> Any:
    """n8nワークフローAPI"""
    return jsonify(get_n8n_workflows())

@app.route('/api/n8n/executions')
def api_n8n_executions() -> Any:
    """n8n実行履歴API"""
    workflow_id = request.args.get('workflow_id')
    return jsonify(get_n8n_executions(workflow_id))

@app.route('/api/n8n/workflows/<workflow_id>/activate', methods=['POST'])
def activate_workflow(workflow_id: str) -> Any:
    """ワークフローを有効化"""
    try:
        headers: Dict[str, str] = {}
        if N8N_API_KEY:
            headers['X-N8N-API-KEY'] = N8N_API_KEY

        response = requests.post(
            f"{N8N_BASE_URL}/api/v1/workflows/{workflow_id}/activate",
            headers=headers,
            timeout=10
        )
        response.raise_for_status()

        return jsonify({"success": True, "message": "ワークフローを有効化しました"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/n8n/workflows/<workflow_id>/deactivate', methods=['POST'])
def deactivate_workflow(workflow_id: str) -> Any:
    """ワークフローを無効化"""
    try:
        headers: Dict[str, str] = {}
        if N8N_API_KEY:
            headers['X-N8N-API-KEY'] = N8N_API_KEY

        response = requests.post(
            f"{N8N_BASE_URL}/api/v1/workflows/{workflow_id}/deactivate",
            headers=headers,
            timeout=10
        )
        response.raise_for_status()

        return jsonify({"success": True, "message": "ワークフローを無効化しました"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/n8n/workflows/<workflow_id>/execute', methods=['POST'])
def execute_workflow(workflow_id: str) -> Any:
    """ワークフローを実行"""
    try:
        headers: Dict[str, str] = {}
        if N8N_API_KEY:
            headers['X-N8N-API-KEY'] = N8N_API_KEY

        # 実行データを取得
        data = request.get_json() or {}

        response = requests.post(
            f"{N8N_BASE_URL}/api/v1/workflows/{workflow_id}/execute",
            headers=headers,
            json=data,
            timeout=30
        )
        response.raise_for_status()

        result = response.json()
        return jsonify({
            "success": True,
            "message": "ワークフローを実行しました",
            "execution_id": result.get('id')
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/containers/<container_id>/start')
def start_container(container_id: str) -> Any:
    """コンテナを起動"""
    if not docker_client:
        return jsonify({"success": False, "error": DOCKER_CLIENT_ERROR_MSG}), 400

    try:
        container = docker_client.containers.get(container_id)
        container.start()
        return jsonify({"success": True, "message": f"コンテナ {container.name} を起動しました"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/containers/<container_id>/stop')
def stop_container(container_id: str) -> Any:
    """コンテナを停止"""
    if not docker_client:
        return jsonify({"success": False, "error": DOCKER_CLIENT_ERROR_MSG}), 400

    try:
        container = docker_client.containers.get(container_id)
        container.stop()
        return jsonify({"success": True, "message": f"コンテナ {container.name} を停止しました"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/containers/<container_id>/logs')
def get_container_logs(container_id: str) -> Any:
    """コンテナのログを取得"""
    if not docker_client:
        return jsonify({"error": DOCKER_CLIENT_ERROR_MSG}), 400

    try:
        container = docker_client.containers.get(container_id)
        logs = container.logs(tail=100, timestamps=True).decode('utf-8')
        return jsonify({"logs": logs})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
