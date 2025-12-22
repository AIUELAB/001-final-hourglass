#!/usr/bin/env python3
"""
src/database_utils.py

このプロジェクトで利用するデータベース接続ユーティリティ。

背景:
- 複数モジュールが `from src.database_utils import get_connection` を参照しているが、
  本ファイルが存在しないため ImportError になっていた。
- DBは `unified_quality.db` を前提としており、実態はSQLiteとして扱う。

注意:
- 一部コードはMySQL風の `AUTO_INCREMENT` をDDLに含めているため、
  SQLite互換の `AUTOINCREMENT` に自動変換して実行できるようにしている。
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Final, Union

# `src/` の1つ上がプロジェクトルート（unified_quality.db の想定場所）
PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parent.parent


def _normalize_sql_for_sqlite(sql: str) -> str:
    """SQLiteで実行できるように、DDL等のSQLを最小限正規化する。

    現状の対象:
    - MySQL風の `AUTO_INCREMENT` → SQLiteの `AUTOINCREMENT`
    """
    if not isinstance(sql, str) or not sql:
        return sql

    # `AUTO_INCREMENT` は SQLite では `AUTOINCREMENT`（大文字小文字は問わない）
    return re.sub(r"\bAUTO_INCREMENT\b", "AUTOINCREMENT", sql, flags=re.IGNORECASE)


class _SQLiteCompatCursor(sqlite3.Cursor):
    """SQLをSQLite互換に変換してから実行するCursor。"""

    def execute(self, sql: str, parameters: Union[tuple, dict] = ()) -> sqlite3.Cursor:  # type: ignore[override]
        normalized_sql = _normalize_sql_for_sqlite(sql)
        return super().execute(normalized_sql, parameters)

    def executemany(self, sql: str, seq_of_parameters) -> sqlite3.Cursor:  # type: ignore[override]
        normalized_sql = _normalize_sql_for_sqlite(sql)
        return super().executemany(normalized_sql, seq_of_parameters)


class _SQLiteCompatConnection(sqlite3.Connection):
    """SQLite互換Cursorを返すConnection。"""

    def cursor(self, factory=_SQLiteCompatCursor):  # type: ignore[override]
        return super().cursor(factory)


def get_connection(db_path: Union[str, Path], timeout_seconds: float = 30.0) -> sqlite3.Connection:
    """SQLiteデータベースへの接続を取得する。

    Args:
        db_path: DBファイルのパス（相対パスの場合はプロジェクトルート基準で解決）
        timeout_seconds: ロック待ちタイムアウト（秒）

    Returns:
        sqlite3.Connection: 利用者側で commit/close を行うこと

    Raises:
        ValueError: db_path が空/不正な場合
        RuntimeError: 接続確立に失敗した場合
    """
    if db_path is None:
        raise ValueError("db_path が指定されていません")

    db_path_str = str(db_path).strip()
    if not db_path_str:
        raise ValueError("db_path が空です")

    resolved_path = Path(db_path_str)
    if not resolved_path.is_absolute():
        # 実行ディレクトリに依存しないように、プロジェクトルート基準に統一
        resolved_path = PROJECT_ROOT / resolved_path

    # DBの親ディレクトリを作成（存在していれば何もしない）
    try:
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise RuntimeError(f"データベース用ディレクトリ作成に失敗しました: {resolved_path.parent}") from exc

    try:
        conn = sqlite3.connect(
            resolved_path,
            timeout=timeout_seconds,
            # 同一プロセス内で別スレッドから触られる可能性があるため安全側に倒す
            check_same_thread=False,
            # MySQL風DDLの互換変換を有効化
            factory=_SQLiteCompatConnection,
        )
    except sqlite3.Error as exc:
        raise RuntimeError(f"データベース接続に失敗しました: {resolved_path}") from exc

    # 最低限のPRAGMA（失敗時は即クローズして例外）
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        # 競合が出やすい環境向け（既存運用に合わせる）
        conn.execute("PRAGMA busy_timeout = 5000;")  # 5秒
    except sqlite3.Error as exc:
        conn.close()
        raise RuntimeError("データベース初期化（PRAGMA設定）に失敗しました") from exc

    return conn
