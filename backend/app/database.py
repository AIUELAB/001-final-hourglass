"""
データベース接続・操作モジュール

SQLiteを使用したキャラクターデータベース管理
"""

import sqlite3
from typing import Optional
from pathlib import Path
from app.models import Character


class Database:
    """データベース接続・操作クラス"""

    def __init__(self, db_path: str = "database/characters.db"):
        """
        データベース初期化

        Args:
            db_path: データベースファイルパス
        """
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None

    def connect(self):
        """データベース接続"""
        # データベースディレクトリを作成
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        print(f"✅ データベース接続成功: {self.db_path}")

    def disconnect(self):
        """データベース切断"""
        if self.conn:
            self.conn.close()
            print("👋 データベース切断")

    def create_table(self):
        """テーブル作成"""
        if not self.conn:
            raise RuntimeError("データベース未接続")

        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS characters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                character_name TEXT NOT NULL,
                work_title TEXT NOT NULL,
                genre TEXT NOT NULL,
                episode_category TEXT NOT NULL,
                episode_text TEXT NOT NULL
            )
        """)
        self.conn.commit()
        print("✅ テーブル作成/確認完了")

    def insert_character(self, character: dict) -> int:
        """
        キャラクター挿入

        Args:
            character: キャラクターデータ（辞書）

        Returns:
            挿入されたキャラクターのID
        """
        if not self.conn:
            raise RuntimeError("データベース未接続")

        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO characters (character_name, work_title, genre, episode_category, episode_text)
            VALUES (?, ?, ?, ?, ?)
        """, (
            character['character_name'],
            character['work_title'],
            character['genre'],
            character['episode_category'],
            character['episode_text']
        ))
        self.conn.commit()
        return cursor.lastrowid

    def get_all_characters(self, page: int = 1, page_size: int = 20) -> tuple[list[Character], int]:
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

        # ページネーションクエリ
        offset = (page - 1) * page_size
        cursor.execute("""
            SELECT * FROM characters
            ORDER BY id
            LIMIT ? OFFSET ?
        """, (page_size, offset))

        rows = cursor.fetchall()
        characters = [
            Character(
                id=row['id'],
                character_name=row['character_name'],
                work_title=row['work_title'],
                genre=row['genre'],
                episode_category=row['episode_category'],
                episode_text=row['episode_text']
            )
            for row in rows
        ]

        return characters, total

    def get_character_by_id(self, character_id: int) -> Optional[Character]:
        """
        特定キャラクター取得

        Args:
            character_id: キャラクターID

        Returns:
            Characterオブジェクト、または None
        """
        if not self.conn:
            raise RuntimeError("データベース未接続")

        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM characters WHERE id = ?", (character_id,))
        row = cursor.fetchone()

        if not row:
            return None

        return Character(
            id=row['id'],
            character_name=row['character_name'],
            work_title=row['work_title'],
            genre=row['genre'],
            episode_category=row['episode_category'],
            episode_text=row['episode_text']
        )

    def search_characters(self, query: str) -> list[Character]:
        """
        キャラクター検索

        Args:
            query: 検索クエリ（キャラクター名または作品名）

        Returns:
            Characterオブジェクトのリスト
        """
        if not self.conn:
            raise RuntimeError("データベース未接続")

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM characters
            WHERE character_name LIKE ? OR work_title LIKE ?
            ORDER BY id
        """, (f"%{query}%", f"%{query}%"))

        rows = cursor.fetchall()
        return [
            Character(
                id=row['id'],
                character_name=row['character_name'],
                work_title=row['work_title'],
                genre=row['genre'],
                episode_category=row['episode_category'],
                episode_text=row['episode_text']
            )
            for row in rows
        ]

    def filter_characters(self, genre: Optional[str] = None, gender: Optional[str] = None) -> list[Character]:
        """
        キャラクターフィルタリング

        Args:
            genre: ジャンル（完全一致）
            gender: 性別（female/male）

        Returns:
            Characterオブジェクトのリスト
        """
        if not self.conn:
            raise RuntimeError("データベース未接続")

        cursor = self.conn.cursor()

        # 女性キャラクターリスト
        female_characters = {
            'フグ田サザエ', 'ナミ', 'ニコ・ロビン', '毛利蘭', '竈門禰豆子',
            '胡蝶しのぶ', '浅倉南', '月野うさぎ', '綾波レイ',
            '猪熊柔', '渚美都', '大林萬理子', '速水ヒロ', '恩田希', '猪野井香鈴',
            '鹿目まどか', '暁美ほむら', '美墨なぎさ（キュアブラック）', '平沢唯', '涼宮ハルヒ',
            '峰不二子', 'ナウシカ', '神楽', 'リナ・インバース',
            '咲', '田所恵', '見崎鳴',
            '春野サクラ', '灰原哀', 'アスナ（結城明日奈）'
        }

        query = "SELECT * FROM characters WHERE 1=1"
        params = []

        if genre:
            query += " AND genre = ?"
            params.append(genre)

        if gender:
            if gender == "female":
                placeholders = ','.join('?' for _ in female_characters)
                query += f" AND character_name IN ({placeholders})"
                params.extend(female_characters)
            elif gender == "male":
                placeholders = ','.join('?' for _ in female_characters)
                query += f" AND character_name NOT IN ({placeholders})"
                params.extend(female_characters)

        query += " ORDER BY id"

        cursor.execute(query, params)
        rows = cursor.fetchall()

        return [
            Character(
                id=row['id'],
                character_name=row['character_name'],
                work_title=row['work_title'],
                genre=row['genre'],
                episode_category=row['episode_category'],
                episode_text=row['episode_text']
            )
            for row in rows
        ]

    def get_genre_stats(self) -> list[dict]:
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

        rows = cursor.fetchall()
        return [
            {
                'genre': row['genre'],
                'count': row['count'],
                'percentage': row['percentage']
            }
            for row in rows
        ]


# グローバルインスタンス
db = Database()
