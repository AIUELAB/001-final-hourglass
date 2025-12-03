"""
ログ収集API用Pydanticモデル

Phase 2: バックエンドログ収集システム
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# ========================================
# コンテキスト・エントリモデル（受信用）
# ========================================


class LogContext(BaseModel):
    """ログコンテキスト"""

    activeTab: Optional[str] = None
    resultCount: Optional[str] = None
    currentPage: Optional[int] = None
    searchQuery: Optional[str] = None


class LogEntryCreate(BaseModel):
    """ログエントリ作成用（受信データ）"""

    timestamp: str = Field(..., description="ISO 8601形式のタイムスタンプ")
    timestampMs: int = Field(..., description="ミリ秒精度のタイムスタンプ")
    level: str = Field(..., description="ログレベル (log/info/warn/error/debug)")
    message: str = Field(..., description="ログメッセージ")
    rawArgs: Optional[List[Any]] = Field(None, description="元の引数（JSON形式）")
    sessionId: str = Field(..., description="セッションID")
    operationId: Optional[str] = Field(None, description="操作ID")
    context: Optional[LogContext] = Field(None, description="コンテキスト情報")
    url: Optional[str] = Field(None, description="現在のURL")
    pathname: Optional[str] = Field(None, description="パス名")
    errorType: Optional[str] = Field(None, description="エラータイプ")


class LogBatchCreate(BaseModel):
    """ログバッチ作成用（一括送信）"""

    sessionId: str = Field(..., description="セッションID")
    entries: List[LogEntryCreate] = Field(..., description="ログエントリのリスト")


# ========================================
# セッションモデル
# ========================================


class LogSessionCreate(BaseModel):
    """セッション作成用"""

    sessionId: str = Field(..., description="セッションID")
    startTime: str = Field(..., description="開始時刻 (ISO 8601)")
    userAgent: Optional[str] = Field(None, description="ユーザーエージェント")
    url: Optional[str] = Field(None, description="初期URL")
    metadata: Optional[Dict[str, Any]] = Field(None, description="追加メタデータ")


class LogSession(BaseModel):
    """セッション情報"""

    session_id: str
    start_time: str
    end_time: Optional[str] = None
    user_agent: Optional[str] = None
    url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: str
    log_count: int = 0
    error_count: int = 0


class LogSessionList(BaseModel):
    """セッション一覧レスポンス"""

    total: int
    sessions: List[LogSession]


# ========================================
# 操作（オペレーション）モデル
# ========================================


class LogOperationCreate(BaseModel):
    """操作作成用"""

    id: str = Field(..., description="操作ID")
    sessionId: str = Field(..., description="セッションID")
    type: str = Field(..., description="操作タイプ (search/filter/sort/tabSwitch等)")
    startTime: str = Field(..., description="開始時刻 (ISO 8601)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="追加メタデータ")


class LogOperationUpdate(BaseModel):
    """操作更新用"""

    endTime: Optional[str] = Field(None, description="終了時刻 (ISO 8601)")
    status: Optional[Literal["in_progress", "success", "error"]] = Field(None, description="ステータス")
    error: Optional[Dict[str, Any]] = Field(None, description="エラー情報")


class LogOperation(BaseModel):
    """操作情報"""

    id: str
    session_id: str
    type: str
    start_time: str
    end_time: Optional[str] = None
    status: str = "in_progress"
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    created_at: str


class LogOperationList(BaseModel):
    """操作一覧レスポンス"""

    total: int
    operations: List[LogOperation]


# ========================================
# ログエントリモデル（レスポンス用）
# ========================================


class LogEntry(BaseModel):
    """ログエントリ（取得用）"""

    id: int
    session_id: str
    operation_id: Optional[str] = None
    timestamp: str
    timestamp_ms: int
    level: str
    message: str
    raw_args: Optional[List[Any]] = None
    context: Optional[Dict[str, Any]] = None
    url: Optional[str] = None
    pathname: Optional[str] = None
    error_type: Optional[str] = None
    created_at: str


class LogEntryList(BaseModel):
    """ログエントリ一覧レスポンス"""

    total: int
    page: int
    page_size: int
    entries: List[LogEntry]


# ========================================
# 統計モデル
# ========================================


class LevelStats(BaseModel):
    """レベル別統計"""

    log: int = 0
    info: int = 0
    warn: int = 0
    error: int = 0
    debug: int = 0


class OperationTypeStats(BaseModel):
    """操作タイプ別統計"""

    type: str
    count: int


class LogStats(BaseModel):
    """ログ統計情報"""

    total_logs: int
    total_sessions: int
    total_operations: int
    by_level: LevelStats
    error_rate: float = Field(description="エラー率 (0-1)")
    time_range: Dict[str, Optional[str]] = Field(description="時間範囲 (start/end)")
    top_operation_types: List[OperationTypeStats]


# ========================================
# レスポンスモデル
# ========================================


class LogReceiveResponse(BaseModel):
    """ログ受信レスポンス"""

    success: bool
    received_count: int
    message: str


class SessionCreateResponse(BaseModel):
    """セッション作成レスポンス"""

    success: bool
    session_id: str
    message: str


class OperationCreateResponse(BaseModel):
    """操作作成レスポンス"""

    success: bool
    operation_id: str
    message: str


class OperationUpdateResponse(BaseModel):
    """操作更新レスポンス"""

    success: bool
    operation_id: str
    status: str
    message: str
