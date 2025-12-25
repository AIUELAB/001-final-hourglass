#!/usr/bin/env python3
"""
Google検索API クォータ管理モジュール

日次100クエリの無料枠を厳守するための管理クラス。
"""

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

# プロジェクトルートからの相対パス
PROJECT_ROOT = Path(__file__).parent.parent.parent
CACHE_DB_PATH = PROJECT_ROOT / "data" / "cache" / "fame_score.db"

# デフォルト日次上限
DEFAULT_DAILY_LIMIT = 100


@dataclass
class QuotaStatus:
    """クォータ状態"""

    date: str
    total_queries: int
    quota_limit: int
    remaining: int
    status: str  # active | paused | completed
    last_updated: Optional[str]


class GoogleQuotaManager:
    """Google検索API クォータ管理クラス"""

    def __init__(self, db_path: Optional[Path] = None, daily_limit: int = DEFAULT_DAILY_LIMIT):
        """
        初期化

        Args:
            db_path: DBファイルパス（省略時はデフォルト）
            daily_limit: 日次クエリ上限（デフォルト100）
        """
        self.db_path = db_path or CACHE_DB_PATH
        self.daily_limit = daily_limit

    def _get_connection(self) -> sqlite3.Connection:
        """DB接続を取得"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _get_today(self) -> str:
        """今日の日付をYYYY-MM-DD形式で取得"""
        return datetime.now().strftime("%Y-%m-%d")

    def _ensure_today_record(self, conn: sqlite3.Connection, date: str) -> None:
        """今日のレコードが存在しない場合は作成"""
        cursor = conn.execute("SELECT 1 FROM quota_tracker WHERE date = ?", (date,))
        if cursor.fetchone() is None:
            conn.execute(
                """
                INSERT INTO quota_tracker (date, total_queries, quota_limit, last_updated, status)
                VALUES (?, 0, ?, ?, 'active')
                """,
                (date, self.daily_limit, datetime.now().isoformat()),
            )
            conn.commit()

    def get_remaining_quota(self, date: Optional[str] = None) -> int:
        """
        残りクエリ数を取得

        Args:
            date: 日付（省略時は今日）

        Returns:
            残りクエリ数（0以上）
        """
        date = date or self._get_today()
        conn = self._get_connection()
        try:
            self._ensure_today_record(conn, date)
            cursor = conn.execute("SELECT total_queries FROM quota_tracker WHERE date = ?", (date,))
            row = cursor.fetchone()
            used = row["total_queries"] if row else 0
            return max(0, self.daily_limit - used)
        finally:
            conn.close()

    def can_make_request(self, date: Optional[str] = None) -> bool:
        """
        リクエスト可能か判定

        Args:
            date: 日付（省略時は今日）

        Returns:
            True: リクエスト可能, False: 上限到達
        """
        date = date or self._get_today()
        conn = self._get_connection()
        try:
            self._ensure_today_record(conn, date)
            cursor = conn.execute(
                "SELECT total_queries, status FROM quota_tracker WHERE date = ?",
                (date,),
            )
            row = cursor.fetchone()
            if row is None:
                return True  # レコードなし = 0クエリ

            if row["status"] == "paused":
                return False  # 手動停止中

            return row["total_queries"] < self.daily_limit
        finally:
            conn.close()

    def increment_quota(self, date: Optional[str] = None) -> int:
        """
        クエリカウントをインクリメント

        Args:
            date: 日付（省略時は今日）

        Returns:
            更新後のクエリ数
        """
        date = date or self._get_today()
        conn = self._get_connection()
        try:
            self._ensure_today_record(conn, date)

            # アトミックに更新
            conn.execute(
                """
                UPDATE quota_tracker
                SET total_queries = total_queries + 1,
                    last_updated = ?
                WHERE date = ?
                """,
                (datetime.now().isoformat(), date),
            )
            conn.commit()

            # 更新後の値を取得
            cursor = conn.execute("SELECT total_queries FROM quota_tracker WHERE date = ?", (date,))
            row = cursor.fetchone()
            new_count = row["total_queries"]

            # 上限到達時は自動停止
            if new_count >= self.daily_limit:
                self.set_status(date, "paused")

            return new_count
        finally:
            conn.close()

    def get_status(self, date: Optional[str] = None) -> QuotaStatus:
        """
        クォータ状態を取得

        Args:
            date: 日付（省略時は今日）

        Returns:
            QuotaStatus オブジェクト
        """
        date = date or self._get_today()
        conn = self._get_connection()
        try:
            self._ensure_today_record(conn, date)
            cursor = conn.execute("SELECT * FROM quota_tracker WHERE date = ?", (date,))
            row = cursor.fetchone()

            total = row["total_queries"]
            limit = row["quota_limit"]

            return QuotaStatus(
                date=row["date"],
                total_queries=total,
                quota_limit=limit,
                remaining=max(0, limit - total),
                status=row["status"],
                last_updated=row["last_updated"],
            )
        finally:
            conn.close()

    def set_status(self, date: Optional[str], status: str) -> None:
        """
        ステータスを設定

        Args:
            date: 日付（省略時は今日）
            status: active | paused | completed
        """
        if status not in ("active", "paused", "completed"):
            raise ValueError(f"Invalid status: {status}")

        date = date or self._get_today()
        conn = self._get_connection()
        try:
            self._ensure_today_record(conn, date)
            conn.execute(
                """
                UPDATE quota_tracker
                SET status = ?, last_updated = ?
                WHERE date = ?
                """,
                (status, datetime.now().isoformat(), date),
            )
            conn.commit()
        finally:
            conn.close()

    def log_search(
        self,
        person_id: str,
        query: str,
        google_hits: Optional[int],
        status: str,
        error_message: Optional[str] = None,
        processing_time_ms: Optional[int] = None,
    ) -> None:
        """
        検索ログを記録

        Args:
            person_id: 人物ID
            query: 検索クエリ
            google_hits: ヒット数（エラー時はNone）
            status: success | error | cached
            error_message: エラーメッセージ（エラー時のみ）
            processing_time_ms: 処理時間（ミリ秒）
        """
        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO search_log
                (person_id, query, google_hits, status, error_message, timestamp, processing_time_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    person_id,
                    query,
                    google_hits,
                    status,
                    error_message,
                    datetime.now().isoformat(),
                    processing_time_ms,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_daily_stats(self, date: Optional[str] = None) -> dict:
        """
        日次統計を取得

        Args:
            date: 日付（省略時は今日）

        Returns:
            統計情報の辞書
        """
        date = date or self._get_today()
        conn = self._get_connection()
        try:
            # 日付範囲を設定
            start = f"{date}T00:00:00"
            end = f"{date}T23:59:59"

            # 検索ログから集計
            cursor = conn.execute(
                """
                SELECT
                    COUNT(*) as total_searches,
                    COUNT(CASE WHEN status = 'success' THEN 1 END) as success_count,
                    COUNT(CASE WHEN status = 'error' THEN 1 END) as error_count,
                    COUNT(CASE WHEN status = 'cached' THEN 1 END) as cached_count,
                    AVG(processing_time_ms) as avg_time_ms
                FROM search_log
                WHERE timestamp BETWEEN ? AND ?
                """,
                (start, end),
            )
            row = cursor.fetchone()

            quota_status = self.get_status(date)

            return {
                "date": date,
                "quota": {
                    "used": quota_status.total_queries,
                    "remaining": quota_status.remaining,
                    "limit": quota_status.quota_limit,
                    "status": quota_status.status,
                },
                "searches": {
                    "total": row["total_searches"] or 0,
                    "success": row["success_count"] or 0,
                    "error": row["error_count"] or 0,
                    "cached": row["cached_count"] or 0,
                    "avg_time_ms": round(row["avg_time_ms"] or 0, 2),
                },
            }
        finally:
            conn.close()


def main():
    """テスト実行"""
    print("=== GoogleQuotaManager テスト ===\n")

    manager = GoogleQuotaManager()
    today = manager._get_today()

    print(f"日付: {today}")
    print(f"日次上限: {manager.daily_limit}")
    print()

    # 状態確認
    status = manager.get_status()
    print("クォータ状態:")
    print(f"  使用済み: {status.total_queries}")
    print(f"  残り: {status.remaining}")
    print(f"  ステータス: {status.status}")
    print()

    # リクエスト可否
    can_request = manager.can_make_request()
    print(f"リクエスト可能: {can_request}")
    print()

    # 日次統計
    stats = manager.get_daily_stats()
    print("日次統計:")
    print(f"  検索総数: {stats['searches']['total']}")
    print(f"  成功: {stats['searches']['success']}")
    print(f"  エラー: {stats['searches']['error']}")
    print(f"  キャッシュ: {stats['searches']['cached']}")


if __name__ == "__main__":
    main()
