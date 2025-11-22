"""データベース操作"""

import sqlite3
import csv
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

    def get_episode_category_stats(self) -> List[dict]:
        """
        エピソードカテゴリ統計取得（ジャンルの詳細分析）

        Returns:
            カテゴリごとの統計リスト
        """
        if not self.conn:
            raise RuntimeError("データベース未接続")

        cursor = self.conn.cursor()
        # 現在のデータベースにはepisode_categoryがないため、genreの上位カテゴリを抽出
        cursor.execute("""
            SELECT
                CASE
                    WHEN genre LIKE '%政治%' THEN '政治・行政'
                    WHEN genre LIKE '%科学%' OR genre LIKE '%技術%' THEN '科学・技術'
                    WHEN genre LIKE '%芸術%' OR genre LIKE '%音楽%' OR genre LIKE '%文学%' THEN '芸術・文化'
                    WHEN genre LIKE '%スポーツ%' THEN 'スポーツ'
                    WHEN genre LIKE '%漫画%' OR genre LIKE '%アニメ%' THEN '漫画・アニメ'
                    WHEN genre LIKE '%ビジネス%' OR genre LIKE '%経営%' THEN 'ビジネス'
                    ELSE 'その他'
                END as category,
                COUNT(*) as count,
                ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM characters), 1) as percentage
            FROM characters
            GROUP BY category
            ORDER BY count DESC
        """)

        return [dict(row) for row in cursor.fetchall()]

    def get_work_stats(self, limit: int = 20) -> List[dict]:
        """
        作品統計取得（上位N件）

        Args:
            limit: 取得件数

        Returns:
            作品ごとの統計リスト
        """
        if not self.conn:
            raise RuntimeError("データベース未接続")

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT
                work_title,
                COUNT(*) as count,
                ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM characters WHERE work_title != ''), 1) as percentage
            FROM characters
            WHERE work_title != ''
            GROUP BY work_title
            ORDER BY count DESC
            LIMIT ?
        """, (limit,))

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

    def get_fame_ranking(self, limit: int = 100, order_by: str = 'fame_score') -> Tuple[List[dict], int]:
        """
        有名度ランキング取得（CSVから直接読み取り）

        Args:
            limit: 取得件数
            order_by: ソートフィールド ('fame_score', 'composite_score')

        Returns:
            (ランキングリスト, 総件数)
        """
        # CSVファイルパス
        csv_path = Path(__file__).parent.parent.parent / "MASTER_EPISODES_CURRENT.csv"

        rankings = []
        row_id = 0

        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    # fame_scoreが存在し、空でない場合のみ追加
                    fame_score = row.get('fame_score', '')
                    if fame_score and fame_score.isdigit():
                        row_id += 1
                        rankings.append({
                            'id': row_id,
                            'person_name': row.get('person_name', ''),
                            'fame_tier': int(row.get('fame_tier', 0)),
                            'fame_score': int(fame_score),
                            'composite_score': int(row.get('composite_score', 0)) if row.get('composite_score', '').isdigit() else 0,
                            'wikipedia_ja': row.get('wikipedia_ja', '').upper() == 'TRUE',
                            'textbook': row.get('textbook', '').upper() == 'TRUE',
                            'award_level': int(row.get('award_level', 0)),
                            'notoriety': row.get('notoriety', '').upper() == 'TRUE',
                            'last_updated': row.get('fame_score_updated_at', ''),
                            'category': row.get('category', ''),
                            'person_type': row.get('person_type', ''),
                            'quality_score': float(row.get('quality_score', 0) or 0)
                        })

            # ソート
            if order_by == 'composite_score':
                rankings.sort(key=lambda x: x['composite_score'], reverse=True)
            else:
                rankings.sort(key=lambda x: x['fame_score'], reverse=True)

            total = len(rankings)

            # 上位N件取得
            rankings = rankings[:limit]

            return rankings, total

        except FileNotFoundError:
            print(f"❌ CSVファイルが見つかりません: {csv_path}")
            return [], 0
        except Exception as e:
            print(f"❌ ランキング取得エラー: {e}")
            return [], 0


# グローバルインスタンス
db = Database()
