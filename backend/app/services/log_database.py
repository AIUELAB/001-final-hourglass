"""
ログ専用SQLiteデータベース

Phase 2: バックエンドログ収集システム

既存のcharacters.dbとは分離したlogs.dbを使用
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class LogDatabase:
    """ログ専用SQLiteデータベースクラス"""

    def __init__(self, db_path: str = None):
        """
        初期化

        Args:
            db_path: データベースファイルパス
        """
        if db_path is None:
            db_path = str(Path(__file__).parent.parent.parent / "logs.db")
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None

    def connect(self):
        """データベース接続"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        print(f"[LogDB] 接続完了: {self.db_path}")

    def disconnect(self):
        """データベース切断"""
        if self.conn:
            self.conn.close()
            self.conn = None
            print("[LogDB] 切断完了")

    def create_tables(self):
        """テーブル作成（既存の場合はスキップ）"""
        if not self.conn:
            raise RuntimeError("データベース未接続")

        cursor = self.conn.cursor()

        # log_sessions テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS log_sessions (
                session_id TEXT PRIMARY KEY,
                start_time TEXT NOT NULL,
                end_time TEXT,
                user_agent TEXT,
                url TEXT,
                metadata TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_start
            ON log_sessions(start_time)
        """)

        # log_entries テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS log_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                operation_id TEXT,
                timestamp TEXT NOT NULL,
                timestamp_ms INTEGER NOT NULL,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                raw_args TEXT,
                context TEXT,
                url TEXT,
                pathname TEXT,
                error_type TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (session_id) REFERENCES log_sessions(session_id)
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_entries_session
            ON log_entries(session_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_entries_timestamp
            ON log_entries(timestamp)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_entries_level
            ON log_entries(level)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_entries_operation
            ON log_entries(operation_id)
        """)

        # log_operations テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS log_operations (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                type TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                status TEXT DEFAULT 'in_progress',
                metadata TEXT,
                error TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (session_id) REFERENCES log_sessions(session_id)
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ops_session
            ON log_operations(session_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ops_type
            ON log_operations(type)
        """)

        self.conn.commit()
        print("[LogDB] テーブル作成完了")

    # ========================================
    # セッション操作
    # ========================================

    def create_session(
        self,
        session_id: str,
        start_time: str,
        user_agent: Optional[str] = None,
        url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        セッション作成（存在しない場合のみ）

        Returns:
            作成された場合True、既存の場合False
        """
        if not self.conn:
            raise RuntimeError("データベース未接続")

        cursor = self.conn.cursor()

        # 既存チェック
        cursor.execute("SELECT 1 FROM log_sessions WHERE session_id = ?", (session_id,))
        if cursor.fetchone():
            return False

        cursor.execute(
            """
            INSERT INTO log_sessions (session_id, start_time, user_agent, url, metadata)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                session_id,
                start_time,
                user_agent,
                url,
                json.dumps(metadata, ensure_ascii=False) if metadata else None,
            ),
        )
        self.conn.commit()
        return True

    def ensure_session(self, session_id: str) -> None:
        """セッションが存在しない場合は自動作成"""
        if not self.conn:
            raise RuntimeError("データベース未接続")

        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM log_sessions WHERE session_id = ?", (session_id,))
        if not cursor.fetchone():
            cursor.execute(
                """
                INSERT INTO log_sessions (session_id, start_time)
                VALUES (?, ?)
                """,
                (session_id, datetime.utcnow().isoformat()),
            )
            self.conn.commit()

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """セッション取得"""
        if not self.conn:
            raise RuntimeError("データベース未接続")

        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT
                s.*,
                (SELECT COUNT(*) FROM log_entries WHERE session_id = s.session_id) as log_count,
                (SELECT COUNT(*) FROM log_entries WHERE session_id = s.session_id AND level = 'error') as error_count
            FROM log_sessions s
            WHERE s.session_id = ?
            """,
            (session_id,),
        )
        row = cursor.fetchone()

        if row:
            result = dict(row)
            if result.get("metadata"):
                result["metadata"] = json.loads(result["metadata"])
            return result
        return None

    def get_sessions(
        self,
        page: int = 1,
        page_size: int = 20,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        セッション一覧取得

        Returns:
            (セッションリスト, 総件数)
        """
        if not self.conn:
            raise RuntimeError("データベース未接続")

        cursor = self.conn.cursor()

        # 条件構築
        where_clauses = []
        params = []

        if start_date:
            where_clauses.append("start_time >= ?")
            params.append(start_date)
        if end_date:
            where_clauses.append("start_time <= ?")
            params.append(end_date)

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        # 総件数 (where_clausesは固定文字列、ユーザー入力はparams経由でバインド)
        cursor.execute(f"SELECT COUNT(*) FROM log_sessions WHERE {where_sql}", params)  # nosec B608
        total = cursor.fetchone()[0]

        # ページネーション
        offset = (page - 1) * page_size
        params.extend([page_size, offset])

        cursor.execute(
            f"""
            SELECT
                s.*,
                (SELECT COUNT(*) FROM log_entries WHERE session_id = s.session_id) as log_count,
                (SELECT COUNT(*) FROM log_entries WHERE session_id = s.session_id AND level = 'error') as error_count
            FROM log_sessions s
            WHERE {where_sql}
            ORDER BY start_time DESC
            LIMIT ? OFFSET ?
            """,
            params,
        )  # nosec B608

        sessions = []
        for row in cursor.fetchall():
            session = dict(row)
            if session.get("metadata"):
                session["metadata"] = json.loads(session["metadata"])
            sessions.append(session)

        return sessions, total

    def update_session_end_time(self, session_id: str, end_time: str) -> bool:
        """セッション終了時刻を更新"""
        if not self.conn:
            raise RuntimeError("データベース未接続")

        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE log_sessions SET end_time = ? WHERE session_id = ?",
            (end_time, session_id),
        )
        self.conn.commit()
        return cursor.rowcount > 0

    # ========================================
    # ログエントリ操作
    # ========================================

    def insert_log_entries(self, entries: List[Dict[str, Any]]) -> int:
        """
        ログエントリをバッチ挿入

        Args:
            entries: ログエントリのリスト

        Returns:
            挿入件数
        """
        if not self.conn:
            raise RuntimeError("データベース未接続")

        if not entries:
            return 0

        cursor = self.conn.cursor()

        # セッションID抽出して自動作成
        session_ids = set(e.get("sessionId") or e.get("session_id") for e in entries)
        for sid in session_ids:
            if sid:
                self.ensure_session(sid)

        # バッチ挿入
        insert_data = []
        for entry in entries:
            insert_data.append(
                (
                    entry.get("sessionId") or entry.get("session_id"),
                    entry.get("operationId") or entry.get("operation_id"),
                    entry.get("timestamp"),
                    entry.get("timestampMs") or entry.get("timestamp_ms"),
                    entry.get("level"),
                    entry.get("message"),
                    json.dumps(entry.get("rawArgs") or entry.get("raw_args"), ensure_ascii=False)
                    if entry.get("rawArgs") or entry.get("raw_args")
                    else None,
                    json.dumps(entry.get("context"), ensure_ascii=False) if entry.get("context") else None,
                    entry.get("url"),
                    entry.get("pathname"),
                    entry.get("errorType") or entry.get("error_type"),
                )
            )

        cursor.executemany(
            """
            INSERT INTO log_entries
            (session_id, operation_id, timestamp, timestamp_ms, level, message, raw_args, context, url, pathname, error_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            insert_data,
        )
        self.conn.commit()

        return len(insert_data)

    def get_log_entries(
        self,
        session_id: Optional[str] = None,
        operation_id: Optional[str] = None,
        level: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        ログエントリ取得

        Returns:
            (エントリリスト, 総件数)
        """
        if not self.conn:
            raise RuntimeError("データベース未接続")

        cursor = self.conn.cursor()

        # 条件構築
        where_clauses = []
        params = []

        if session_id:
            where_clauses.append("session_id = ?")
            params.append(session_id)
        if operation_id:
            where_clauses.append("operation_id = ?")
            params.append(operation_id)
        if level:
            where_clauses.append("level = ?")
            params.append(level)
        if start_time:
            where_clauses.append("timestamp >= ?")
            params.append(start_time)
        if end_time:
            where_clauses.append("timestamp <= ?")
            params.append(end_time)

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        # 総件数
        cursor.execute(f"SELECT COUNT(*) FROM log_entries WHERE {where_sql}", params)  # nosec B608
        total = cursor.fetchone()[0]

        # ページネーション
        offset = (page - 1) * page_size
        params.extend([page_size, offset])

        cursor.execute(
            f"""
            SELECT * FROM log_entries
            WHERE {where_sql}
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
            """,
            params,
        )  # nosec B608

        entries = []
        for row in cursor.fetchall():
            entry = dict(row)
            if entry.get("raw_args"):
                try:
                    entry["raw_args"] = json.loads(entry["raw_args"])
                except json.JSONDecodeError:
                    pass
            if entry.get("context"):
                try:
                    entry["context"] = json.loads(entry["context"])
                except json.JSONDecodeError:
                    pass
            entries.append(entry)

        return entries, total

    # ========================================
    # 操作（オペレーション）操作
    # ========================================

    def create_operation(
        self,
        operation_id: str,
        session_id: str,
        op_type: str,
        start_time: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """操作作成"""
        if not self.conn:
            raise RuntimeError("データベース未接続")

        # セッション確保
        self.ensure_session(session_id)

        cursor = self.conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO log_operations (id, session_id, type, start_time, metadata)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    operation_id,
                    session_id,
                    op_type,
                    start_time,
                    json.dumps(metadata, ensure_ascii=False) if metadata else None,
                ),
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            # 既存の場合
            return False

    def update_operation(
        self,
        operation_id: str,
        end_time: Optional[str] = None,
        status: Optional[str] = None,
        error: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """操作更新"""
        if not self.conn:
            raise RuntimeError("データベース未接続")

        cursor = self.conn.cursor()

        set_clauses = []
        params = []

        if end_time:
            set_clauses.append("end_time = ?")
            params.append(end_time)
        if status:
            set_clauses.append("status = ?")
            params.append(status)
        if error is not None:
            set_clauses.append("error = ?")
            params.append(json.dumps(error, ensure_ascii=False))

        if not set_clauses:
            return False

        params.append(operation_id)

        cursor.execute(
            f"UPDATE log_operations SET {', '.join(set_clauses)} WHERE id = ?",
            params,
        )  # nosec B608
        self.conn.commit()
        return cursor.rowcount > 0

    def get_operations(
        self,
        session_id: Optional[str] = None,
        op_type: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """操作一覧取得"""
        if not self.conn:
            raise RuntimeError("データベース未接続")

        cursor = self.conn.cursor()

        # 条件構築
        where_clauses = []
        params = []

        if session_id:
            where_clauses.append("session_id = ?")
            params.append(session_id)
        if op_type:
            where_clauses.append("type = ?")
            params.append(op_type)
        if status:
            where_clauses.append("status = ?")
            params.append(status)

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        # 総件数
        cursor.execute(f"SELECT COUNT(*) FROM log_operations WHERE {where_sql}", params)  # nosec B608
        total = cursor.fetchone()[0]

        # ページネーション
        offset = (page - 1) * page_size
        params.extend([page_size, offset])

        cursor.execute(
            f"""
            SELECT * FROM log_operations
            WHERE {where_sql}
            ORDER BY start_time DESC
            LIMIT ? OFFSET ?
            """,
            params,
        )  # nosec B608

        operations = []
        for row in cursor.fetchall():
            op = dict(row)
            if op.get("metadata"):
                try:
                    op["metadata"] = json.loads(op["metadata"])
                except json.JSONDecodeError:
                    pass
            if op.get("error"):
                try:
                    op["error"] = json.loads(op["error"])
                except json.JSONDecodeError:
                    pass
            operations.append(op)

        return operations, total

    # ========================================
    # 統計
    # ========================================

    def get_stats(self) -> Dict[str, Any]:
        """統計情報取得"""
        if not self.conn:
            raise RuntimeError("データベース未接続")

        cursor = self.conn.cursor()

        # 総件数
        cursor.execute("SELECT COUNT(*) FROM log_entries")
        total_logs = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM log_sessions")
        total_sessions = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM log_operations")
        total_operations = cursor.fetchone()[0]

        # レベル別件数
        cursor.execute("""
            SELECT level, COUNT(*) as count
            FROM log_entries
            GROUP BY level
        """)
        by_level = {row["level"]: row["count"] for row in cursor.fetchall()}

        # エラー率
        error_count = by_level.get("error", 0)
        error_rate = error_count / total_logs if total_logs > 0 else 0.0

        # 時間範囲
        cursor.execute("""
            SELECT MIN(timestamp) as start, MAX(timestamp) as end
            FROM log_entries
        """)
        time_range_row = cursor.fetchone()
        time_range = {
            "start": time_range_row["start"] if time_range_row else None,
            "end": time_range_row["end"] if time_range_row else None,
        }

        # 操作タイプ別トップ10
        cursor.execute("""
            SELECT type, COUNT(*) as count
            FROM log_operations
            GROUP BY type
            ORDER BY count DESC
            LIMIT 10
        """)
        top_operation_types = [{"type": row["type"], "count": row["count"]} for row in cursor.fetchall()]

        return {
            "total_logs": total_logs,
            "total_sessions": total_sessions,
            "total_operations": total_operations,
            "by_level": {
                "log": by_level.get("log", 0),
                "info": by_level.get("info", 0),
                "warn": by_level.get("warn", 0),
                "error": by_level.get("error", 0),
                "debug": by_level.get("debug", 0),
            },
            "error_rate": error_rate,
            "time_range": time_range,
            "top_operation_types": top_operation_types,
        }

    # ========================================
    # メンテナンス
    # ========================================

    def prune_old_entries(self, days: int = 30) -> int:
        """
        古いログを削除

        Args:
            days: 保持日数

        Returns:
            削除件数
        """
        if not self.conn:
            raise RuntimeError("データベース未接続")

        threshold = (datetime.utcnow() - timedelta(days=days)).isoformat()

        cursor = self.conn.cursor()

        # ログエントリ削除
        cursor.execute("DELETE FROM log_entries WHERE timestamp < ?", (threshold,))
        deleted_entries = cursor.rowcount

        # 空のセッションも削除
        cursor.execute(
            """
            DELETE FROM log_sessions
            WHERE session_id NOT IN (SELECT DISTINCT session_id FROM log_entries)
            AND start_time < ?
        """,
            (threshold,),
        )

        # 孤立した操作も削除
        cursor.execute("""
            DELETE FROM log_operations
            WHERE session_id NOT IN (SELECT session_id FROM log_sessions)
        """)

        self.conn.commit()
        print(f"[LogDB] プルーニング完了: {deleted_entries}件削除")

        return deleted_entries


# グローバルインスタンス
log_db = LogDatabase()
