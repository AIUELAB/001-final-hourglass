#!/usr/bin/env python3
"""
DB拡張マイグレーション: quota_tracker, search_log テーブル追加

Phase 2 Google検索の無料枠管理用テーブルを追加する。
"""

import sqlite3
from datetime import datetime
from pathlib import Path

# プロジェクトルートからの相対パス
PROJECT_ROOT = Path(__file__).parent.parent.parent
CACHE_DB_PATH = PROJECT_ROOT / "data" / "cache" / "fame_score.db"


def get_connection() -> sqlite3.Connection:
    """DB接続を取得"""
    return sqlite3.connect(CACHE_DB_PATH)


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    """テーブルが存在するか確認"""
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    )
    return cursor.fetchone() is not None


def create_quota_tracker(conn: sqlite3.Connection) -> bool:
    """quota_trackerテーブルを作成"""
    if table_exists(conn, "quota_tracker"):
        print("  quota_tracker: 既に存在します（スキップ）")
        return False

    conn.execute("""
        CREATE TABLE quota_tracker (
            date TEXT PRIMARY KEY,
            total_queries INTEGER DEFAULT 0,
            quota_limit INTEGER DEFAULT 100,
            last_updated TEXT,
            status TEXT DEFAULT 'active'
        )
    """)

    # インデックス作成
    conn.execute("""
        CREATE INDEX idx_quota_tracker_status ON quota_tracker(status)
    """)

    print("  quota_tracker: 作成完了")
    return True


def create_search_log(conn: sqlite3.Connection) -> bool:
    """search_logテーブルを作成"""
    if table_exists(conn, "search_log"):
        print("  search_log: 既に存在します（スキップ）")
        return False

    conn.execute("""
        CREATE TABLE search_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id TEXT NOT NULL,
            query TEXT NOT NULL,
            google_hits INTEGER,
            status TEXT,
            error_message TEXT,
            timestamp TEXT,
            processing_time_ms INTEGER
        )
    """)

    # インデックス作成
    conn.execute("""
        CREATE INDEX idx_search_log_person_id ON search_log(person_id)
    """)
    conn.execute("""
        CREATE INDEX idx_search_log_timestamp ON search_log(timestamp)
    """)
    conn.execute("""
        CREATE INDEX idx_search_log_status ON search_log(status)
    """)

    print("  search_log: 作成完了")
    return True


def run_migration() -> None:
    """マイグレーションを実行"""
    print("=== DB拡張マイグレーション ===")
    print(f"DB: {CACHE_DB_PATH}")
    print()

    if not CACHE_DB_PATH.exists():
        print(f"エラー: DBファイルが存在しません: {CACHE_DB_PATH}")
        return

    conn = get_connection()
    try:
        created_count = 0

        print("テーブル作成:")
        if create_quota_tracker(conn):
            created_count += 1
        if create_search_log(conn):
            created_count += 1

        conn.commit()

        print()
        print(f"=== 完了: {created_count}テーブル作成 ===")

        # 確認
        print()
        print("テーブル一覧:")
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        for row in cursor:
            print(f"  - {row[0]}")

    except Exception as e:
        conn.rollback()
        print(f"エラー: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    run_migration()
