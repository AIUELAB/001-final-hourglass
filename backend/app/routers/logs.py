"""
ログ収集APIルーター

Phase 2: バックエンドログ収集システム

認証なし設計 - フロントエンドからのログ収集を担当
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from sse_starlette.sse import EventSourceResponse

from app.log_models import (
    LogBatchCreate,
    LogEntry,
    LogEntryList,
    LogOperation,
    LogOperationCreate,
    LogOperationList,
    LogOperationUpdate,
    LogReceiveResponse,
    LogSession,
    LogSessionCreate,
    LogSessionList,
    LogStats,
    OperationCreateResponse,
    OperationUpdateResponse,
    SessionCreateResponse,
)
from app.services.log_database import log_db
from app.services.log_sse import log_sse_manager

router = APIRouter()


# ========================================
# ログ受信API（認証なし）
# ========================================


@router.post("", response_model=LogReceiveResponse)
async def receive_logs(batch: LogBatchCreate):
    """
    ログバッチ受信

    フロントエンドからのログエントリを一括で受信し、
    データベースに保存します。

    Args:
        batch: ログバッチ（セッションID + エントリリスト）

    Returns:
        LogReceiveResponse: 受信結果
    """
    try:
        # バッチ挿入
        entries_data = [entry.model_dump() for entry in batch.entries]
        count = log_db.insert_log_entries(entries_data)

        # SSEブロードキャスト（リアルタイム配信）
        await log_sse_manager.broadcast_batch(entries_data)

        return LogReceiveResponse(
            success=True,
            received_count=count,
            message=f"{count}件のログエントリを受信しました",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ログ受信エラー: {str(e)}")


@router.post("/session", response_model=SessionCreateResponse)
async def create_session(session: LogSessionCreate):
    """
    セッション登録

    新しいセッションを登録します。
    既存のセッションIDの場合は無視されます。

    Args:
        session: セッション情報

    Returns:
        SessionCreateResponse: 作成結果
    """
    try:
        created = log_db.create_session(
            session_id=session.sessionId,
            start_time=session.startTime,
            user_agent=session.userAgent,
            url=session.url,
            metadata=session.metadata,
        )

        if created:
            return SessionCreateResponse(
                success=True,
                session_id=session.sessionId,
                message="セッションを登録しました",
            )
        else:
            return SessionCreateResponse(
                success=True,
                session_id=session.sessionId,
                message="セッションは既に存在します",
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"セッション登録エラー: {str(e)}")


@router.post("/operation", response_model=OperationCreateResponse)
async def create_operation(operation: LogOperationCreate):
    """
    操作登録

    ユーザー操作（検索、フィルタ、ソート等）を登録します。

    Args:
        operation: 操作情報

    Returns:
        OperationCreateResponse: 作成結果
    """
    try:
        created = log_db.create_operation(
            operation_id=operation.id,
            session_id=operation.sessionId,
            op_type=operation.type,
            start_time=operation.startTime,
            metadata=operation.metadata,
        )

        # SSEブロードキャスト
        await log_sse_manager.broadcast_operation(
            {
                "id": operation.id,
                "session_id": operation.sessionId,
                "type": operation.type,
                "start_time": operation.startTime,
                "metadata": operation.metadata,
            },
            event_type="operation_start",
        )

        if created:
            return OperationCreateResponse(
                success=True,
                operation_id=operation.id,
                message="操作を登録しました",
            )
        else:
            return OperationCreateResponse(
                success=True,
                operation_id=operation.id,
                message="操作は既に存在します",
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"操作登録エラー: {str(e)}")


@router.put("/operation/{operation_id}", response_model=OperationUpdateResponse)
async def update_operation(operation_id: str, update: LogOperationUpdate):
    """
    操作更新

    操作の終了時刻やステータスを更新します。

    Args:
        operation_id: 操作ID
        update: 更新内容

    Returns:
        OperationUpdateResponse: 更新結果
    """
    try:
        updated = log_db.update_operation(
            operation_id=operation_id,
            end_time=update.endTime,
            status=update.status,
            error=update.error,
        )

        if updated:
            # SSEブロードキャスト
            await log_sse_manager.broadcast_operation(
                {
                    "id": operation_id,
                    "end_time": update.endTime,
                    "status": update.status,
                    "error": update.error,
                },
                event_type="operation_end",
            )

            return OperationUpdateResponse(
                success=True,
                operation_id=operation_id,
                status=update.status or "updated",
                message="操作を更新しました",
            )
        else:
            raise HTTPException(status_code=404, detail=f"操作が見つかりません: {operation_id}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"操作更新エラー: {str(e)}")


# ========================================
# ログ取得API
# ========================================


@router.get("", response_model=LogEntryList)
async def get_logs(
    session_id: Optional[str] = Query(None, description="セッションID"),
    operation_id: Optional[str] = Query(None, description="操作ID"),
    level: Optional[str] = Query(None, description="ログレベル"),
    start_time: Optional[str] = Query(None, description="開始時刻 (ISO 8601)"),
    end_time: Optional[str] = Query(None, description="終了時刻 (ISO 8601)"),
    page: int = Query(1, ge=1, description="ページ番号"),
    page_size: int = Query(100, ge=1, le=1000, description="ページサイズ"),
):
    """
    ログ一覧取得

    フィルタリングとページネーション対応でログエントリを取得します。

    Args:
        session_id: セッションIDフィルタ
        operation_id: 操作IDフィルタ
        level: ログレベルフィルタ（log/info/warn/error/debug）
        start_time: 開始時刻
        end_time: 終了時刻
        page: ページ番号
        page_size: ページサイズ

    Returns:
        LogEntryList: ログエントリ一覧
    """
    entries, total = log_db.get_log_entries(
        session_id=session_id,
        operation_id=operation_id,
        level=level,
        start_time=start_time,
        end_time=end_time,
        page=page,
        page_size=page_size,
    )

    return LogEntryList(
        total=total,
        page=page,
        page_size=page_size,
        entries=[LogEntry(**entry) for entry in entries],
    )


@router.get("/sessions", response_model=LogSessionList)
async def get_sessions(
    start_date: Optional[str] = Query(None, description="開始日 (ISO 8601)"),
    end_date: Optional[str] = Query(None, description="終了日 (ISO 8601)"),
    page: int = Query(1, ge=1, description="ページ番号"),
    page_size: int = Query(20, ge=1, le=100, description="ページサイズ"),
):
    """
    セッション一覧取得

    日付範囲でフィルタリングしてセッション一覧を取得します。

    Args:
        start_date: 開始日
        end_date: 終了日
        page: ページ番号
        page_size: ページサイズ

    Returns:
        LogSessionList: セッション一覧
    """
    sessions, total = log_db.get_sessions(
        page=page,
        page_size=page_size,
        start_date=start_date,
        end_date=end_date,
    )

    return LogSessionList(
        total=total,
        sessions=[LogSession(**session) for session in sessions],
    )


@router.get("/sessions/{session_id}", response_model=LogSession)
async def get_session(session_id: str):
    """
    セッション詳細取得

    セッションIDでセッション情報を取得します。

    Args:
        session_id: セッションID

    Returns:
        LogSession: セッション情報
    """
    session = log_db.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail=f"セッションが見つかりません: {session_id}")

    return LogSession(**session)


@router.get("/operations", response_model=LogOperationList)
async def get_operations(
    session_id: Optional[str] = Query(None, description="セッションID"),
    op_type: Optional[str] = Query(None, description="操作タイプ"),
    status: Optional[str] = Query(None, description="ステータス"),
    page: int = Query(1, ge=1, description="ページ番号"),
    page_size: int = Query(100, ge=1, le=1000, description="ページサイズ"),
):
    """
    操作一覧取得

    フィルタリング条件で操作一覧を取得します。

    Args:
        session_id: セッションIDフィルタ
        op_type: 操作タイプフィルタ
        status: ステータスフィルタ
        page: ページ番号
        page_size: ページサイズ

    Returns:
        LogOperationList: 操作一覧
    """
    operations, total = log_db.get_operations(
        session_id=session_id,
        op_type=op_type,
        status=status,
        page=page,
        page_size=page_size,
    )

    return LogOperationList(
        total=total,
        operations=[LogOperation(**op) for op in operations],
    )


@router.get("/stats", response_model=LogStats)
async def get_stats():
    """
    ログ統計情報取得

    総ログ数、レベル別統計、エラー率などの統計情報を取得します。

    Returns:
        LogStats: 統計情報
    """
    stats = log_db.get_stats()

    return LogStats(**stats)


# ========================================
# SSEリアルタイムストリーム
# ========================================


@router.get("/stream")
async def stream_logs(
    request: Request,
    level: Optional[str] = Query(None, description="監視するレベル（カンマ区切り、例: error,warn）"),
    session_id: Optional[str] = Query(None, description="監視するセッションID"),
):
    """
    SSEリアルタイムログストリーム

    ログエントリをリアルタイムで受信します。
    レベルやセッションIDでフィルタリング可能です。

    Args:
        level: 監視するログレベル（カンマ区切り）
        session_id: 監視するセッションID

    Returns:
        EventSourceResponse: SSEストリーム

    Events:
        - log: 新しいログエントリ
        - operation_start: 操作開始
        - operation_end: 操作終了
        - heartbeat: 接続維持用ハートビート
    """
    # レベルフィルタをリストに変換
    level_filter = level.split(",") if level else None

    client = await log_sse_manager.connect(
        level_filter=level_filter,
        session_filter=session_id,
    )

    async def generate():
        try:
            async for event in log_sse_manager.event_generator(client):
                if await request.is_disconnected():
                    break
                yield event
        finally:
            log_sse_manager.disconnect(client.client_id)

    return EventSourceResponse(generate())


# ========================================
# メンテナンスAPI
# ========================================


@router.delete("/prune")
async def prune_logs(days: int = Query(30, ge=1, le=365, description="保持日数")):
    """
    古いログを削除

    指定日数より古いログエントリを削除します。

    Args:
        days: 保持日数（デフォルト30日）

    Returns:
        削除件数
    """
    deleted = log_db.prune_old_entries(days=days)

    return {
        "success": True,
        "deleted_count": deleted,
        "message": f"{deleted}件の古いログを削除しました（{days}日以前）",
    }


@router.get("/clients")
async def get_sse_clients():
    """
    SSE接続クライアント情報取得

    現在接続中のSSEクライアント一覧を取得します。

    Returns:
        クライアント一覧
    """
    return {
        "total": log_sse_manager.get_client_count(),
        "clients": log_sse_manager.get_client_info(),
    }


# ========================================
# LLM分析API（Phase 4）
# ========================================


@router.get("/analyze/patterns")
async def analyze_error_patterns(
    max_logs: int = Query(100, ge=10, le=500, description="分析対象のログ件数"),
):
    """
    エラーパターン分析

    LLMを使用してエラー/警告ログのパターンを分析し、
    根本原因と改善提案を生成します。

    Args:
        max_logs: 分析対象の最大ログ件数

    Returns:
        分析結果（パターン、サマリー、優先アクション）
    """
    from app.services.log_analyzer import log_analyzer

    if not log_analyzer.is_available():
        return {
            "success": False,
            "error": "LLM API is not configured. Set ANTHROPIC_API_KEY environment variable.",
            "patterns": [],
            "summary": {"total_errors": 0, "unique_patterns": 0, "critical_issues": 0, "health_score": 100},
            "priority_actions": [],
        }

    # エラー/警告ログを取得
    logs, _ = log_db.get_log_entries(level="error", page_size=max_logs)
    warn_logs, _ = log_db.get_log_entries(level="warn", page_size=max_logs)

    all_logs = logs + warn_logs

    # 分析実行
    result = log_analyzer.analyze_error_patterns(all_logs, max_logs=max_logs)

    if result.success:
        return {
            "success": True,
            "patterns": [
                {
                    "id": p.id,
                    "name": p.name,
                    "count": p.count,
                    "severity": p.severity,
                    "description": p.description,
                    "sample_messages": p.sample_messages,
                    "root_cause": p.root_cause,
                    "impact": p.impact,
                    "suggestion": p.suggestion,
                }
                for p in result.patterns
            ],
            "summary": {
                "total_errors": result.summary.total_errors,
                "unique_patterns": result.summary.unique_patterns,
                "critical_issues": result.summary.critical_issues,
                "health_score": result.summary.health_score,
            },
            "priority_actions": result.priority_actions,
            "analyzed_at": result.analyzed_at,
        }
    else:
        return {
            "success": False,
            "error": result.error_message,
            "patterns": [],
            "summary": {"total_errors": 0, "unique_patterns": 0, "critical_issues": 0, "health_score": 100},
            "priority_actions": [],
        }


@router.get("/analyze/epup-plan")
async def generate_epup_plan():
    """
    EPUP改善計画生成

    検出されたエラーパターンに基づいて、
    EPUP 7ステップに沿った改善計画を生成します。

    Returns:
        EPUP改善計画
    """
    from app.services.log_analyzer import log_analyzer

    if not log_analyzer.is_available():
        return {
            "success": False,
            "error": "LLM API is not configured",
        }

    # まずパターン分析を実行
    logs, _ = log_db.get_log_entries(level="error", page_size=100)
    warn_logs, _ = log_db.get_log_entries(level="warn", page_size=100)

    result = log_analyzer.analyze_error_patterns(logs + warn_logs)

    if not result.success or not result.patterns:
        return {
            "success": False,
            "error": "No error patterns detected or analysis failed",
        }

    # EPUP計画生成
    plan = log_analyzer.generate_epup_plan(result.patterns)

    if plan:
        return {
            "success": True,
            "epup_plan": {
                "root_cause_analysis": plan.root_cause_analysis,
                "system_fix": plan.system_fix,
                "individual_fix": plan.individual_fix,
                "similar_search": plan.similar_search,
                "batch_fix": plan.batch_fix,
                "prevention": plan.prevention,
                "monitoring": plan.monitoring,
            },
            "estimated_effort": plan.estimated_effort,
            "priority": plan.priority,
            "source_patterns": len(result.patterns),
        }
    else:
        return {
            "success": False,
            "error": "Failed to generate EPUP plan",
        }


@router.get("/analyze/session/{session_id}")
async def analyze_session(session_id: str):
    """
    セッション分析

    特定セッションのユーザー行動パターンと問題点を分析します。

    Args:
        session_id: 分析対象のセッションID

    Returns:
        セッション分析結果
    """
    from app.services.log_analyzer import log_analyzer

    if not log_analyzer.is_available():
        return {
            "success": False,
            "error": "LLM API is not configured",
        }

    # セッション情報取得
    session = log_db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    # セッションのログ取得
    logs, _ = log_db.get_log_entries(session_id=session_id, page_size=200)

    # 分析実行
    result = log_analyzer.analyze_session(
        session_id=session_id,
        start_time=session.get("start_time", ""),
        logs=logs,
    )

    return result


@router.get("/analyze/status")
async def get_analyzer_status():
    """
    分析機能のステータス取得

    LLM分析機能の利用可否と使用統計を取得します。

    Returns:
        ステータス情報
    """
    from app.services.log_analyzer import log_analyzer

    return {
        "available": log_analyzer.is_available(),
        "usage": log_analyzer.get_usage_stats(),
    }


# ========================================
# EPUP自動実行API（Phase 5）
# ========================================


@router.post("/epup/run")
async def run_epup_cycle():
    """
    EPUPサイクルを手動実行

    エラー検出→分析→計画生成→実行追跡のサイクルを
    手動でトリガーします。

    Returns:
        EPUPジョブ情報
    """
    from app.services.epup_engine import epup_engine

    job = await epup_engine.run_cycle(trigger="manual")
    return job.to_dict()


@router.get("/epup/jobs")
async def list_epup_jobs(
    limit: int = Query(20, ge=1, le=100, description="取得件数"),
):
    """
    EPUPジョブ一覧取得

    過去のEPUPジョブ一覧を取得します。

    Args:
        limit: 取得件数

    Returns:
        ジョブ一覧
    """
    from app.services.epup_engine import epup_engine

    jobs = epup_engine.list_jobs(limit=limit)
    return {
        "total": len(jobs),
        "jobs": [j.to_dict() for j in jobs],
    }


@router.get("/epup/jobs/{job_id}")
async def get_epup_job(job_id: str):
    """
    EPUPジョブ詳細取得

    特定のジョブの詳細情報を取得します。

    Args:
        job_id: ジョブID

    Returns:
        ジョブ詳細
    """
    from app.services.epup_engine import epup_engine

    job = epup_engine.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return job.to_dict()


@router.post("/epup/jobs/{job_id}/cancel")
async def cancel_epup_job(job_id: str):
    """
    EPUPジョブをキャンセル

    実行中のジョブをキャンセルします。

    Args:
        job_id: ジョブID

    Returns:
        キャンセル結果
    """
    from app.services.epup_engine import epup_engine

    success = epup_engine.cancel_job(job_id)
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel job: {job_id} (not found or already completed)",
        )
    return {"success": True, "message": f"Job {job_id} cancelled"}


@router.post("/epup/auto/start")
async def start_auto_mode(
    interval: int = Query(300, ge=60, le=3600, description="チェック間隔（秒）"),
    threshold: int = Query(5, ge=1, le=100, description="トリガーエラー数"),
):
    """
    自動モードを開始

    定期的にエラーをチェックし、閾値を超えた場合に
    自動でEPUPサイクルを実行します。

    Args:
        interval: チェック間隔（秒）
        threshold: EPUPトリガーのエラー閾値

    Returns:
        開始結果
    """
    from app.services.epup_engine import epup_engine

    await epup_engine.start_auto_mode(interval=interval, threshold=threshold)
    return {
        "success": True,
        "message": "Auto mode started",
        "interval": interval,
        "threshold": threshold,
    }


@router.post("/epup/auto/stop")
async def stop_auto_mode():
    """
    自動モードを停止

    自動EPUPサイクルを停止します。

    Returns:
        停止結果
    """
    from app.services.epup_engine import epup_engine

    await epup_engine.stop_auto_mode()
    return {"success": True, "message": "Auto mode stopped"}


@router.get("/epup/stats")
async def get_epup_stats():
    """
    EPUP統計取得

    EPUPエンジンの統計情報を取得します。

    Returns:
        統計情報
    """
    from app.services.epup_engine import epup_engine

    return epup_engine.get_stats()
