#!/usr/bin/env python3
"""
エピソードデータベース統合システム

ultra_think_*.csvファイルとエピソードデータを統合し、
バッチ処理による効率的なエピソード生成と管理を行うシステム

Author: Claude
Date: 2025-09-18
Version: 1.0.0
"""

import json
import logging
import os
import glob
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import pandas as pd
import numpy as np
from dataclasses import dataclass, asdict
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed

# ローカルインポート
try:
    from premium_episode_generator import PremiumEpisodeGenerator, GeneratedEpisode
    from multi_source_episode_collector import MultiSourceEpisodeCollector
    from episode_quality_evaluator import EpisodeQualityEvaluator
    from pdca_guardian import PDCAGuardian
except ImportError:
    PremiumEpisodeGenerator = None
    MultiSourceEpisodeCollector = None
    EpisodeQualityEvaluator = None
    PDCAGuardian = None

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ProcessingStatus:
    """処理ステータス"""
    total_persons: int
    processed: int
    successful: int
    failed: int
    skipped: int
    start_time: datetime
    end_time: Optional[datetime]
    error_messages: List[str]
    api_costs: float

class EpisodeDatabaseIntegration:
    """エピソードデータベース統合クラス"""

    def __init__(self, database_path: str = "episode_database.db"):
        """
        初期化

        Args:
            database_path: SQLiteデータベースのパス
        """
        self.database_path = database_path
        self.generator = PremiumEpisodeGenerator() if PremiumEpisodeGenerator else None
        self.collector = MultiSourceEpisodeCollector() if MultiSourceEpisodeCollector else None
        self.evaluator = EpisodeQualityEvaluator() if EpisodeQualityEvaluator else None
        self.pdca_guardian = PDCAGuardian() if PDCAGuardian else None

        # データベース初期化
        self._initialize_database()

        # 処理ステータス
        self.processing_status = None

        # 設定
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """設定の読み込み"""
        return {
            "batch_size": 10,
            "max_workers": 3,
            "quality_threshold": 75.0,
            "episodes_per_person": 3,
            "priority_categories": [
                "歴史人物", "スポーツ選手", "芸能人", "科学者", "芸術家"
            ],
            "skip_existing": True,
            "auto_backup": True
        }

    def _initialize_database(self):
        """データベース初期化"""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()

        # 人物テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS persons (
                person_id TEXT PRIMARY KEY,
                person_name_ja TEXT NOT NULL,
                person_name_en TEXT,
                birth_year INTEGER,
                death_year INTEGER,
                category TEXT,
                recognition_score REAL,
                has_episodes BOOLEAN DEFAULT FALSE,
                last_updated TIMESTAMP,
                metadata TEXT
            )
        """)

        # エピソードテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS episodes (
                episode_id TEXT PRIMARY KEY,
                person_id TEXT NOT NULL,
                age INTEGER NOT NULL,
                episode_text TEXT NOT NULL,
                quality_score REAL,
                grade TEXT,
                source TEXT,
                keywords TEXT,
                emotion_tags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                metadata TEXT,
                FOREIGN KEY (person_id) REFERENCES persons(person_id)
            )
        """)

        # 処理ログテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processing_log (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_id TEXT,
                status TEXT,
                message TEXT,
                api_cost REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # インデックス作成
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_episodes_person ON episodes(person_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_episodes_quality ON episodes(quality_score)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_persons_category ON persons(category)")

        conn.commit()
        conn.close()

    def load_ultra_think_csv(self, csv_path: Optional[str] = None) -> pd.DataFrame:
        """
        ultra_think CSVファイルの読み込み

        Args:
            csv_path: CSVファイルのパス（Noneの場合は最新ファイルを自動検出）

        Returns:
            読み込んだDataFrame
        """
        if not csv_path:
            # 最新のultra_think_*.csvを検出
            csv_files = glob.glob("ultra_think_*.csv")
            if not csv_files:
                raise FileNotFoundError("ultra_think CSVファイルが見つかりません")

            csv_files.sort(key=os.path.getmtime, reverse=True)
            csv_path = csv_files[0]
            logger.info(f"最新のCSVファイルを使用: {csv_path}")

        # CSV読み込み
        df = pd.read_csv(csv_path, encoding='utf-8-sig')

        # 必要なカラムの確認
        required_columns = ['person_id', 'person_name_ja']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"必要なカラムが不足: {missing_columns}")

        logger.info(f"CSVファイルから{len(df)}件の人物データを読み込みました")

        return df

    def sync_persons_to_database(self, df: pd.DataFrame):
        """
        人物データをデータベースに同期

        Args:
            df: 人物データのDataFrame
        """
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()

        # 既存データの確認
        cursor.execute("SELECT person_id FROM persons")
        existing_ids = set(row[0] for row in cursor.fetchall())

        # 新規・更新データの処理
        new_count = 0
        update_count = 0

        for _, row in df.iterrows():
            person_id = row.get('person_id', '')
            person_data = {
                'person_id': person_id,
                'person_name_ja': row.get('person_name_ja', ''),
                'person_name_en': row.get('person_name_en', ''),
                # birth_year_intを優先、なければbirth_yearを使用
                'birth_year': row.get('birth_year_int') if pd.notna(row.get('birth_year_int'))
                             else (row.get('birth_year') if pd.notna(row.get('birth_year')) else None),
                'death_year': row.get('death_year') if pd.notna(row.get('death_year')) else None,
                'category': row.get('category', ''),
                'recognition_score': row.get('recognition_score', 0.0) if pd.notna(row.get('recognition_score')) else 0.0,
                'metadata': json.dumps({
                    'wikipedia_url': row.get('wikipedia_url', ''),
                    'occupation': row.get('occupation', ''),
                    'nationality': row.get('nationality', '')
                })
            }

            if person_id in existing_ids:
                # 更新
                cursor.execute("""
                    UPDATE persons
                    SET person_name_ja = ?, person_name_en = ?, birth_year = ?,
                        death_year = ?, category = ?, recognition_score = ?,
                        metadata = ?, last_updated = CURRENT_TIMESTAMP
                    WHERE person_id = ?
                """, (
                    person_data['person_name_ja'],
                    person_data['person_name_en'],
                    person_data['birth_year'],
                    person_data['death_year'],
                    person_data['category'],
                    person_data['recognition_score'],
                    person_data['metadata'],
                    person_id
                ))
                update_count += 1
            else:
                # 新規追加
                cursor.execute("""
                    INSERT INTO persons (person_id, person_name_ja, person_name_en,
                                      birth_year, death_year, category, recognition_score,
                                      metadata, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    person_id,
                    person_data['person_name_ja'],
                    person_data['person_name_en'],
                    person_data['birth_year'],
                    person_data['death_year'],
                    person_data['category'],
                    person_data['recognition_score'],
                    person_data['metadata']
                ))
                new_count += 1

        conn.commit()
        conn.close()

        logger.info(f"データベース同期完了: 新規{new_count}件、更新{update_count}件")

    def batch_generate_episodes(self, person_filter: Optional[Dict[str, Any]] = None,
                               limit: Optional[int] = None) -> ProcessingStatus:
        """
        バッチエピソード生成

        Args:
            person_filter: 人物フィルタ条件
            limit: 処理人数の上限

        Returns:
            処理ステータス
        """
        # 処理対象の人物を取得
        persons = self._get_persons_for_processing(person_filter, limit)

        if not persons:
            logger.warning("処理対象の人物がありません")
            return ProcessingStatus(
                total_persons=0, processed=0, successful=0, failed=0,
                skipped=0, start_time=datetime.now(), end_time=datetime.now(),
                error_messages=[], api_costs=0.0
            )

        # ===== APIクレジット事前確認（Rule 100対応） =====
        try:
            from api_credit_monitor import APICrediteMonitor

            monitor = APICrediteMonitor()
            # 処理に必要なクレジットを見積もり
            num_episodes_estimated = len(persons) * 2  # 1人あたり平均2エピソード
            estimated_cost, cost_message = monitor.estimate_cost(num_episodes_estimated)

            logger.info("="*60)
            logger.info("💳 APIクレジット事前確認")
            logger.info("="*60)
            logger.info(cost_message)

            # クレジットチェック（最低$1必要）
            min_required = max(1.0, estimated_cost)

            # クレジット状態を確認
            status = monitor.check_credits()

            if status.alert_level == "empty":
                logger.error(status.message)
                raise SystemError("APIクレジットが不足しています。処理を中止します。")

            if status.alert_level == "critical":
                logger.warning(status.message)
                # ユーザーに確認を促す
                logger.warning("⚠️ クレジット残高が少ないため、処理中に枯渇する可能性があります")

            if status.remaining_credits and status.remaining_credits < min_required:
                shortage = min_required - status.remaining_credits
                logger.error(f"""
🔴 クレジット不足により処理を開始できません
- 必要額: ${min_required:.2f}
- 現在の残高: ${status.remaining_credits:.2f}
- 不足額: ${shortage:.2f}

【対処方法】
1. https://console.anthropic.com/ でクレジットを購入
2. 最低${shortage + 5:.2f}の追加購入を推奨
3. 購入完了後、処理を再実行してください
""")
                raise SystemError(f"最低${min_required:.2f}のクレジットが必要です")

            logger.info("✅ クレジット確認完了: 処理を開始します")
            logger.info("="*60)

        except ImportError:
            logger.warning("⚠️ api_credit_monitor.pyが見つかりません。クレジットチェックをスキップします")
        except SystemError:
            # クレジット不足エラーは再スロー
            raise
        except Exception as e:
            logger.warning(f"クレジットチェック中にエラーが発生しました: {e}")
            # チェックに失敗しても処理は続行（警告のみ）

        # 処理ステータス初期化
        self.processing_status = ProcessingStatus(
            total_persons=len(persons),
            processed=0,
            successful=0,
            failed=0,
            skipped=0,
            start_time=datetime.now(),
            end_time=None,
            error_messages=[],
            api_costs=0.0
        )

        logger.info(f"エピソード生成開始: {len(persons)}人の処理を開始します")

        # バッチ処理
        batch_size = self.config.get('batch_size', 10)
        batches = [persons[i:i + batch_size] for i in range(0, len(persons), batch_size)]

        for batch_idx, batch in enumerate(batches):
            logger.info(f"バッチ {batch_idx + 1}/{len(batches)} を処理中")
            self._process_batch(batch)

            # 進捗表示
            progress = (self.processing_status.processed / self.processing_status.total_persons) * 100
            logger.info(f"進捗: {progress:.1f}% ({self.processing_status.processed}/{self.processing_status.total_persons})")

        # 処理完了
        self.processing_status.end_time = datetime.now()

        # サマリー出力
        self._output_processing_summary()

        return self.processing_status

    def _get_persons_for_processing(self, person_filter: Optional[Dict[str, Any]],
                                   limit: Optional[int]) -> List[Dict[str, Any]]:
        """処理対象の人物を取得"""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()

        # クエリ構築
        query = "SELECT * FROM persons WHERE 1=1"
        params = []

        # フィルタ条件適用
        if person_filter:
            if 'category' in person_filter:
                query += " AND category = ?"
                params.append(person_filter['category'])

            if 'min_recognition_score' in person_filter:
                query += " AND recognition_score >= ?"
                params.append(person_filter['min_recognition_score'])

            if 'has_birth_year' in person_filter and person_filter['has_birth_year']:
                query += " AND birth_year IS NOT NULL"

        # 既存エピソードをスキップ
        if self.config.get('skip_existing', True):
            query += " AND has_episodes = FALSE"

        # 優先順位でソート
        query += " ORDER BY recognition_score DESC, category"

        # 件数制限
        if limit:
            query += f" LIMIT {limit}"

        cursor.execute(query, params)
        columns = [description[0] for description in cursor.description]
        persons = [dict(zip(columns, row)) for row in cursor.fetchall()]

        conn.close()

        return persons

    def _process_batch(self, batch: List[Dict[str, Any]]):
        """バッチ処理"""
        with ThreadPoolExecutor(max_workers=self.config.get('max_workers', 3)) as executor:
            futures = {
                executor.submit(self._generate_person_episodes, person): person
                for person in batch
            }

            for future in as_completed(futures):
                person = futures[future]
                try:
                    result = future.result()
                    self.processing_status.processed += 1

                    if result['success']:
                        self.processing_status.successful += 1
                    else:
                        self.processing_status.failed += 1
                        if result.get('error'):
                            self.processing_status.error_messages.append(
                                f"{person['person_name_ja']}: {result['error']}"
                            )

                    # APIコスト加算
                    self.processing_status.api_costs += result.get('api_cost', 0.0)

                except Exception as e:
                    self.processing_status.failed += 1
                    self.processing_status.error_messages.append(
                        f"{person['person_name_ja']}: {str(e)}"
                    )
                    logger.error(f"エピソード生成エラー ({person['person_name_ja']}): {e}")

    def _generate_person_episodes(self, person: Dict[str, Any]) -> Dict[str, Any]:
        """個人のエピソード生成"""
        result = {
            'person_id': person['person_id'],
            'success': False,
            'episodes_generated': 0,
            'api_cost': 0.0,
            'error': None
        }

        try:
            if not self.generator:
                raise ValueError("エピソード生成器が初期化されていません")

            # メタデータのパース
            metadata = json.loads(person.get('metadata', '{}')) if isinstance(person.get('metadata'), str) else {}

            # 人物データの準備
            person_data = {
                'person_id': person['person_id'],
                'person_name_ja': person['person_name_ja'],
                'person_name_en': person.get('person_name_en'),
                'birth_year': person.get('birth_year'),
                'death_year': person.get('death_year'),
                'category': person.get('category'),
                'wikipedia_url': metadata.get('wikipedia_url'),
                'occupation': metadata.get('occupation')
            }

            # エピソード生成
            logger.info(f"エピソード生成中: {person['person_name_ja']}")
            episodes = self.generator.generate_premium_episodes(person_data)

            if episodes:
                # データベースに保存
                self._save_episodes_to_database(person['person_id'], episodes)

                # 人物テーブル更新
                self._update_person_has_episodes(person['person_id'], True)

                result['success'] = True
                result['episodes_generated'] = len(episodes)
                result['api_cost'] = 0.1 * len(episodes)  # 仮のAPIコスト

                logger.info(f"エピソード生成成功: {person['person_name_ja']} ({len(episodes)}件)")
            else:
                result['error'] = "エピソードが生成されませんでした"

        except Exception as e:
            result['error'] = str(e)
            logger.error(f"エピソード生成エラー: {e}")

        # 処理ログ記録
        self._log_processing(person['person_id'], result['success'], result.get('error'), result['api_cost'])

        return result

    def _save_episodes_to_database(self, person_id: str, episodes: List[GeneratedEpisode]):
        """エピソードをデータベースに保存"""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()

        for episode in episodes:
            episode_id = self._generate_episode_id(person_id, episode.age)

            # 既存チェック
            cursor.execute("SELECT episode_id FROM episodes WHERE episode_id = ?", (episode_id,))
            if cursor.fetchone():
                # 既存の場合は非アクティブ化
                cursor.execute("UPDATE episodes SET is_active = FALSE WHERE episode_id = ?", (episode_id,))

            # 新規挿入
            cursor.execute("""
                INSERT INTO episodes (episode_id, person_id, age, episode_text,
                                    quality_score, grade, source, keywords,
                                    emotion_tags, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                episode_id,
                person_id,
                episode.age,
                episode.episode_text,
                episode.quality_score,
                episode.grade,
                episode.strategy.value if hasattr(episode, 'strategy') else 'unknown',
                json.dumps(episode.keywords),
                json.dumps(episode.emotion_tags),
                json.dumps(episode.generation_metadata)
            ))

        conn.commit()
        conn.close()

    def _generate_episode_id(self, person_id: str, age: int) -> str:
        """エピソードIDの生成"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        hash_input = f"{person_id}_{age}_{timestamp}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:16]

    def _update_person_has_episodes(self, person_id: str, has_episodes: bool):
        """人物のエピソード有無フラグ更新"""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE persons SET has_episodes = ?, last_updated = CURRENT_TIMESTAMP WHERE person_id = ?",
            (has_episodes, person_id)
        )
        conn.commit()
        conn.close()

    def _log_processing(self, person_id: str, success: bool, error: Optional[str], api_cost: float):
        """処理ログ記録"""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO processing_log (person_id, status, message, api_cost)
            VALUES (?, ?, ?, ?)
        """, (
            person_id,
            'SUCCESS' if success else 'FAILED',
            error or 'OK',
            api_cost
        ))
        conn.commit()
        conn.close()

    def _output_processing_summary(self):
        """処理サマリー出力"""
        if not self.processing_status:
            return

        duration = (self.processing_status.end_time - self.processing_status.start_time).total_seconds()

        summary = f"""
=== エピソード生成処理サマリー ===
処理人数: {self.processing_status.total_persons}
成功: {self.processing_status.successful}
失敗: {self.processing_status.failed}
スキップ: {self.processing_status.skipped}
処理時間: {duration:.1f}秒
APIコスト: ${self.processing_status.api_costs:.2f}

成功率: {(self.processing_status.successful / max(self.processing_status.total_persons, 1)) * 100:.1f}%
平均処理時間: {duration / max(self.processing_status.total_persons, 1):.1f}秒/人
"""

        if self.processing_status.error_messages:
            summary += f"\nエラー詳細 (最初の5件):\n"
            for error in self.processing_status.error_messages[:5]:
                summary += f"  - {error}\n"

        logger.info(summary)

        # ファイルにも出力
        with open("episode_generation_summary.txt", "w", encoding='utf-8') as f:
            f.write(summary)

    def export_episodes_to_csv(self, output_path: str, include_metadata: bool = False):
        """エピソードをCSVにエクスポート"""
        conn = sqlite3.connect(self.database_path)

        # エピソードデータ取得
        query = """
            SELECT e.*, p.person_name_ja, p.birth_year, p.category
            FROM episodes e
            JOIN persons p ON e.person_id = p.person_id
            WHERE e.is_active = TRUE
            ORDER BY p.person_id, e.age
        """

        df = pd.read_sql_query(query, conn)
        conn.close()

        # メタデータ削除（オプション）
        if not include_metadata:
            df = df.drop(columns=['metadata'], errors='ignore')

        # CSV出力（Excel対応）
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        logger.info(f"エピソードを{output_path}にエクスポートしました（{len(df)}件）")

    def get_statistics(self) -> Dict[str, Any]:
        """統計情報の取得"""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()

        stats = {}

        # 人物統計
        cursor.execute("SELECT COUNT(*) FROM persons")
        stats['total_persons'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM persons WHERE has_episodes = TRUE")
        stats['persons_with_episodes'] = cursor.fetchone()[0]

        # エピソード統計
        cursor.execute("SELECT COUNT(*) FROM episodes WHERE is_active = TRUE")
        stats['total_episodes'] = cursor.fetchone()[0]

        cursor.execute("SELECT AVG(quality_score) FROM episodes WHERE is_active = TRUE")
        stats['average_quality_score'] = cursor.fetchone()[0] or 0

        # グレード分布
        cursor.execute("""
            SELECT grade, COUNT(*) as count
            FROM episodes
            WHERE is_active = TRUE
            GROUP BY grade
        """)
        stats['grade_distribution'] = dict(cursor.fetchall())

        # カテゴリ別統計
        cursor.execute("""
            SELECT p.category, COUNT(DISTINCT e.person_id) as persons_with_episodes
            FROM persons p
            LEFT JOIN episodes e ON p.person_id = e.person_id
            WHERE e.is_active = TRUE OR e.is_active IS NULL
            GROUP BY p.category
        """)
        stats['category_stats'] = dict(cursor.fetchall())

        conn.close()

        return stats


def main():
    """メイン処理"""
    integration = EpisodeDatabaseIntegration()

    # CSVファイル読み込み
    df = integration.load_ultra_think_csv()

    # データベース同期
    integration.sync_persons_to_database(df)

    # 統計情報表示
    stats = integration.get_statistics()
    print("\n=== データベース統計 ===")
    print(f"総人物数: {stats['total_persons']}")
    print(f"エピソード保有人物: {stats['persons_with_episodes']}")
    print(f"総エピソード数: {stats['total_episodes']}")
    print(f"平均品質スコア: {stats['average_quality_score']:.1f}")

    # バッチ処理テスト（10人限定）
    print("\n=== バッチエピソード生成テスト ===")
    status = integration.batch_generate_episodes(
        person_filter={'has_birth_year': True},
        limit=10
    )

    # CSVエクスポート
    integration.export_episodes_to_csv("generated_episodes_export.csv")

    # 最終統計
    final_stats = integration.get_statistics()
    print("\n=== 処理後の統計 ===")
    print(f"エピソード保有人物: {final_stats['persons_with_episodes']}")
    print(f"総エピソード数: {final_stats['total_episodes']}")
    print(f"グレード分布: {final_stats['grade_distribution']}")


if __name__ == "__main__":
    main()