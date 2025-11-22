"""データベース操作"""

import sqlite3
from typing import Optional, List, Tuple
from pathlib import Path


class Database:
    """SQLiteデータベースクラス"""

    def __init__(self, db_path: str = None):
        """
        初期化

        Args:
            db_path: データベースファイルパス
        """
        if db_path is None:
            # backend/app から見た相対パス
            db_path = str(Path(__file__).parent.parent / "characters.db")
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None

    def connect(self):
        """データベース接続"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        print(f"✅ データベース接続: {self.db_path}")

    def disconnect(self):
        """データベース切断"""
        if self.conn:
            self.conn.close()
            print("✅ データベース切断")

    def create_table(self):
        """テーブル作成（既存の場合はスキップ）"""
        if not self.conn:
            raise RuntimeError("データベース未接続")

        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS characters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                character_name TEXT NOT NULL,
                work_title TEXT NOT NULL,
                genre TEXT NOT NULL,
                age_in_story TEXT NOT NULL,
                key_episode TEXT NOT NULL,
                detailed_achievements TEXT NOT NULL,
                story_events TEXT NOT NULL,
                growth_narrative TEXT NOT NULL,
                wikipedia_url TEXT NOT NULL,
                validation_status TEXT NOT NULL,
                curator_notes TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_character_name
            ON characters(character_name)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_genre
            ON characters(genre)
        """)
        self.conn.commit()

    def get_all_characters(self, page: int = 1, page_size: int = 20) -> Tuple[List[dict], int]:
        """
        全キャラクター取得（ページネーション対応）

        Args:
            page: ページ番号（1始まり）
            page_size: ページサイズ

        Returns:
            (キャラクターリスト, 総件数)
        """
        if not self.conn:
            raise RuntimeError("データベース未接続")

        cursor = self.conn.cursor()

        # 総件数取得
        cursor.execute("SELECT COUNT(*) FROM characters")
        total = cursor.fetchone()[0]

        # ページネーション
        offset = (page - 1) * page_size
        cursor.execute(
            "SELECT * FROM characters ORDER BY id LIMIT ? OFFSET ?",
            (page_size, offset)
        )

        characters = [dict(row) for row in cursor.fetchall()]
        return characters, total

    def get_character_by_id(self, character_id: int) -> Optional[dict]:
        """
        ID指定でキャラクター取得

        Args:
            character_id: キャラクターID

        Returns:
            キャラクター情報（存在しない場合はNone）
        """
        if not self.conn:
            raise RuntimeError("データベース未接続")

        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM characters WHERE id = ?", (character_id,))
        row = cursor.fetchone()

        return dict(row) if row else None

    def search_characters(self, query: str) -> List[dict]:
        """
        キャラクター検索

        Args:
            query: 検索クエリ

        Returns:
            検索結果リスト
        """
        if not self.conn:
            raise RuntimeError("データベース未接続")

        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM characters
            WHERE character_name LIKE ? OR work_title LIKE ?
            ORDER BY id
            """,
            (f"%{query}%", f"%{query}%")
        )

        return [dict(row) for row in cursor.fetchall()]

    def filter_characters(self, genre: Optional[str] = None, gender: Optional[str] = None) -> List[dict]:
        """
        キャラクターフィルタリング

        Args:
            genre: ジャンル
            gender: 性別（未実装）

        Returns:
            フィルタリング結果
        """
        if not self.conn:
            raise RuntimeError("データベース未接続")

        cursor = self.conn.cursor()

        # ジャンルフィルタのみ実装（性別情報が DB にないため）
        if genre:
            cursor.execute(
                "SELECT * FROM characters WHERE genre = ? ORDER BY id",
                (genre,)
            )
        else:
            cursor.execute("SELECT * FROM characters ORDER BY id")

        return [dict(row) for row in cursor.fetchall()]

    def get_genre_stats(self) -> List[dict]:
        """
        ジャンル統計取得

        Returns:
            ジャンル統計リスト
        """
        if not self.conn:
            raise RuntimeError("データベース未接続")

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT
                genre,
                COUNT(*) as count,
                ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM characters), 1) as percentage
            FROM characters
            GROUP BY genre
            ORDER BY count DESC
        """)

        return [dict(row) for row in cursor.fetchall()]

    def insert_character(self, data: dict):
        """
        キャラクター挿入

        Args:
            data: キャラクターデータ
        """
        if not self.conn:
            raise RuntimeError("データベース未接続")

        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO characters (
                character_name, work_title, genre, age_in_story,
                key_episode, detailed_achievements, story_events,
                growth_narrative, wikipedia_url, validation_status, curator_notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get('character_name', ''),
            data.get('work_title', ''),
            data.get('genre', ''),
            data.get('age_in_story', ''),
            data.get('key_episode', ''),
            data.get('detailed_achievements', ''),
            data.get('story_events', ''),
            data.get('growth_narrative', ''),
            data.get('wikipedia_url', ''),
            data.get('validation_status', 'PENDING'),
            data.get('curator_notes', ''),
        ))
        self.conn.commit()


# グローバルインスタンス
db = Database()
