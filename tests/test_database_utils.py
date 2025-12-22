"""
tests/test_database_utils.py - database_utils.py ユニットテスト
"""

import importlib
import sqlite3
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# 他のテストファイルがsys.modulesにモックを設定している場合があるため、
# 実際のモジュールを強制的にリロードする
if "src.database_utils" in sys.modules:
    # モックかどうかを確認
    module = sys.modules["src.database_utils"]
    if isinstance(module, MagicMock) or not hasattr(module, "__file__"):
        del sys.modules["src.database_utils"]

import src.database_utils

importlib.reload(src.database_utils)

from src.database_utils import (
    PROJECT_ROOT,
    _normalize_sql_for_sqlite,
    _SQLiteCompatConnection,
    _SQLiteCompatCursor,
    get_connection,
)


class TestNormalizeSqlForSqlite:
    """_normalize_sql_for_sqlite関数テスト"""

    def test_auto_increment_to_autoincrement(self):
        """AUTO_INCREMENT を AUTOINCREMENT に変換"""
        sql = "CREATE TABLE test (id INTEGER PRIMARY KEY AUTO_INCREMENT)"
        result = _normalize_sql_for_sqlite(sql)
        assert "AUTOINCREMENT" in result
        assert "AUTO_INCREMENT" not in result

    def test_auto_increment_case_insensitive(self):
        """大文字小文字を問わず変換"""
        sql = "CREATE TABLE test (id INTEGER PRIMARY KEY auto_increment)"
        result = _normalize_sql_for_sqlite(sql)
        assert "AUTOINCREMENT" in result

    def test_mixed_case_auto_increment(self):
        """混合ケース"""
        sql = "CREATE TABLE test (id INTEGER PRIMARY KEY Auto_Increment)"
        result = _normalize_sql_for_sqlite(sql)
        assert "AUTOINCREMENT" in result

    def test_no_change_needed(self):
        """変換不要なSQL"""
        sql = "SELECT * FROM users WHERE id = 1"
        result = _normalize_sql_for_sqlite(sql)
        assert result == sql

    def test_empty_string(self):
        """空文字列"""
        result = _normalize_sql_for_sqlite("")
        assert result == ""

    def test_none_input(self):
        """Noneの入力"""
        result = _normalize_sql_for_sqlite(None)
        assert result is None

    def test_already_autoincrement(self):
        """既にAUTOINCREMENT"""
        sql = "CREATE TABLE test (id INTEGER PRIMARY KEY AUTOINCREMENT)"
        result = _normalize_sql_for_sqlite(sql)
        assert result == sql

    def test_multiple_auto_increment(self):
        """複数のAUTO_INCREMENT"""
        sql = "AUTO_INCREMENT AUTO_INCREMENT"
        result = _normalize_sql_for_sqlite(sql)
        assert result == "AUTOINCREMENT AUTOINCREMENT"


class TestSQLiteCompatCursor:
    """_SQLiteCompatCursorクラステスト"""

    def test_execute_normalizes_sql(self, tmp_path):
        """executeがSQLを正規化"""
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(db_path, factory=_SQLiteCompatConnection)
        cursor = conn.cursor()

        # AUTO_INCREMENTを含むSQLでエラーにならない
        cursor.execute("CREATE TABLE test (id INTEGER PRIMARY KEY AUTO_INCREMENT, name TEXT)")
        conn.commit()

        # テーブルが作成されたことを確認
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='test'")
        result = cursor.fetchone()
        assert result is not None
        assert result[0] == "test"

        conn.close()

    def test_execute_with_parameters(self, tmp_path):
        """パラメータ付きexecute"""
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(db_path, factory=_SQLiteCompatConnection)
        cursor = conn.cursor()

        cursor.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
        cursor.execute("INSERT INTO test (name) VALUES (?)", ("test_name",))
        conn.commit()

        cursor.execute("SELECT name FROM test WHERE id = ?", (1,))
        result = cursor.fetchone()
        assert result[0] == "test_name"

        conn.close()

    def test_executemany_normalizes_sql(self, tmp_path):
        """executemanyがSQLを正規化"""
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(db_path, factory=_SQLiteCompatConnection)
        cursor = conn.cursor()

        cursor.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
        cursor.executemany(
            "INSERT INTO test (name) VALUES (?)",
            [("name1",), ("name2",), ("name3",)],
        )
        conn.commit()

        cursor.execute("SELECT COUNT(*) FROM test")
        count = cursor.fetchone()[0]
        assert count == 3

        conn.close()


class TestSQLiteCompatConnection:
    """_SQLiteCompatConnectionクラステスト"""

    def test_cursor_returns_compat_cursor(self, tmp_path):
        """cursor()が互換Cursorを返す"""
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(db_path, factory=_SQLiteCompatConnection)
        cursor = conn.cursor()

        assert isinstance(cursor, _SQLiteCompatCursor)
        conn.close()


class TestGetConnection:
    """get_connection関数テスト"""

    def test_creates_connection(self, tmp_path):
        """接続を作成"""
        db_path = tmp_path / "test.db"
        conn = get_connection(db_path)

        assert conn is not None
        assert isinstance(conn, sqlite3.Connection)
        conn.close()

    def test_creates_parent_directory(self, tmp_path):
        """親ディレクトリを作成"""
        db_path = tmp_path / "subdir" / "nested" / "test.db"
        conn = get_connection(db_path)

        assert db_path.parent.exists()
        conn.close()

    def test_string_path(self, tmp_path):
        """文字列パス"""
        db_path = str(tmp_path / "test.db")
        conn = get_connection(db_path)

        assert conn is not None
        conn.close()

    def test_path_object(self, tmp_path):
        """Pathオブジェクト"""
        db_path = tmp_path / "test.db"
        conn = get_connection(db_path)

        assert conn is not None
        conn.close()

    def test_custom_timeout(self, tmp_path):
        """カスタムタイムアウト"""
        db_path = tmp_path / "test.db"
        conn = get_connection(db_path, timeout_seconds=60.0)

        assert conn is not None
        conn.close()

    def test_none_path_raises(self):
        """Noneパスでエラー"""
        with pytest.raises(ValueError, match="db_path が指定されていません"):
            get_connection(None)

    def test_empty_path_raises(self):
        """空パスでエラー"""
        with pytest.raises(ValueError, match="db_path が空です"):
            get_connection("")

    def test_whitespace_path_raises(self):
        """空白のみパスでエラー"""
        with pytest.raises(ValueError, match="db_path が空です"):
            get_connection("   ")

    def test_relative_path_uses_project_root(self):
        """相対パスはプロジェクトルート基準"""
        # 一時的なDBを作成してすぐ削除
        rel_path = "temp_test_db_for_unit_test.db"
        expected_path = PROJECT_ROOT / rel_path

        try:
            conn = get_connection(rel_path)
            conn.close()
            assert expected_path.exists()
        finally:
            # クリーンアップ
            if expected_path.exists():
                expected_path.unlink()

    def test_absolute_path_used_directly(self, tmp_path):
        """絶対パスはそのまま使用"""
        db_path = tmp_path / "absolute_test.db"
        conn = get_connection(db_path)

        assert db_path.exists()
        conn.close()

    def test_pragma_foreign_keys_enabled(self, tmp_path):
        """PRAGMA foreign_keys が有効"""
        db_path = tmp_path / "test.db"
        conn = get_connection(db_path)

        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys")
        result = cursor.fetchone()
        assert result[0] == 1  # ON

        conn.close()

    def test_returns_compat_connection(self, tmp_path):
        """互換Connectionを返す"""
        db_path = tmp_path / "test.db"
        conn = get_connection(db_path)

        assert isinstance(conn, _SQLiteCompatConnection)
        conn.close()

    def test_can_execute_mysql_style_ddl(self, tmp_path):
        """MySQL風DDLを実行可能"""
        db_path = tmp_path / "test.db"
        conn = get_connection(db_path)
        cursor = conn.cursor()

        # MySQL風のAUTO_INCREMENTを含むDDL
        cursor.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                name TEXT NOT NULL,
                email TEXT
            )
        """)
        conn.commit()

        # テーブルが正常に作成されたか確認
        cursor.execute("INSERT INTO users (name, email) VALUES (?, ?)", ("Alice", "alice@example.com"))
        conn.commit()

        cursor.execute("SELECT * FROM users")
        row = cursor.fetchone()
        assert row[1] == "Alice"

        conn.close()


class TestProjectRoot:
    """PROJECT_ROOT定数テスト"""

    def test_project_root_exists(self):
        """PROJECT_ROOTが存在"""
        assert PROJECT_ROOT.exists()

    def test_project_root_is_directory(self):
        """PROJECT_ROOTがディレクトリ"""
        assert PROJECT_ROOT.is_dir()

    def test_project_root_contains_src(self):
        """PROJECT_ROOTにsrcがある"""
        src_dir = PROJECT_ROOT / "src"
        assert src_dir.exists()


class TestConnectionErrors:
    """接続エラーテスト"""

    @patch("src.database_utils.sqlite3.connect")
    def test_connection_error_raises_runtime(self, mock_connect, tmp_path):
        """接続エラーでRuntimeError"""
        mock_connect.side_effect = sqlite3.Error("Connection failed")

        with pytest.raises(RuntimeError, match="データベース接続に失敗しました"):
            get_connection(tmp_path / "test.db")

    def test_invalid_directory_path(self):
        """無効なディレクトリパス（OSエラー）"""
        # /dev/null/test.db のような無効なパス
        if Path("/dev/null").exists():
            with pytest.raises(RuntimeError):
                get_connection("/dev/null/subdir/test.db")

    @patch.object(_SQLiteCompatConnection, "execute")
    def test_pragma_error_closes_connection(self, mock_execute, tmp_path):
        """PRAGMA設定エラーで接続をクローズ"""
        mock_execute.side_effect = sqlite3.Error("PRAGMA failed")

        with pytest.raises(RuntimeError, match="PRAGMA設定"):
            get_connection(tmp_path / "pragma_test.db")
