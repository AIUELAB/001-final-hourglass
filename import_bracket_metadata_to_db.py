#!/usr/bin/env python3
"""
収集データをデータベースに反映

目的:
1. Phase 3で収集した各種メタデータをデータベースに統合
2. 架空キャラクター判定結果の反映
3. お笑い芸人グループ情報の反映
4. バンド・YouTuber情報の反映

入力ファイル:
- fictional_character_classification.json
- comedian_group_info.json
- band_youtuber_info.json
"""

import sqlite3
import json
import logging
from typing import Dict, List
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ================================================================================
# データインポートエンジン
# ================================================================================

class BracketMetadataImporter:
    """括弧メタデータインポートエンジン"""

    def __init__(self, db_path: str = "episode_database.db"):
        """
        初期化

        Args:
            db_path: データベースパス
        """
        self.db_path = db_path
        self.logger = logging.getLogger(__name__ + '.BracketMetadataImporter')

        # 統計
        self.stats = {
            'fictional_characters': 0,
            'comedians': 0,
            'bands': 0,
            'youtubers': 0,
            'total_updated': 0,
            'errors': 0
        }

    def import_fictional_characters(self, json_path: str = "fictional_character_classification.json"):
        """
        架空キャラクター判定結果をインポート

        Args:
            json_path: JSONファイルパス
        """
        self.logger.info(f"架空キャラクター判定結果をインポート: {json_path}")

        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            self.logger.warning(f"ファイルが見つかりません: {json_path}")
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for item in data:
            if item['entity_type'] != 'fictional_character':
                continue

            person_id = item['person_id']
            primary_work = item.get('primary_work')

            try:
                cursor.execute("""
                    UPDATE persons
                    SET
                        entity_type = 'fictional_character',
                        primary_work = ?,
                        show_group_in_bracket = ?,
                        bracket_display_text = ?,
                        bracket_data_updated_at = ?
                    WHERE person_id = ?
                """, (
                    primary_work,
                    1 if primary_work else 0,
                    primary_work or '',
                    datetime.now().isoformat(),
                    person_id
                ))

                if cursor.rowcount > 0:
                    self.stats['fictional_characters'] += 1
                    self.logger.debug(f"更新: {item['person_name']} → fictional_character")

            except Exception as e:
                self.logger.error(f"エラー: {item['person_name']} - {e}")
                self.stats['errors'] += 1

        conn.commit()
        conn.close()

        self.logger.info(f"架空キャラクター: {self.stats['fictional_characters']}件更新")

    def import_comedian_groups(self, json_path: str = "comedian_group_info.json"):
        """
        お笑い芸人グループ情報をインポート

        Args:
            json_path: JSONファイルパス
        """
        self.logger.info(f"お笑い芸人グループ情報をインポート: {json_path}")

        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            self.logger.warning(f"ファイルが見つかりません: {json_path}")
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for item in data:
            if not item.get('group_name'):
                continue

            person_id = item['person_id']
            group_name = item['group_name']
            group_status = item.get('group_status')
            fame_level = item.get('fame_level')
            show_bracket = item.get('show_group_in_bracket', 0)
            bracket_text = item.get('bracket_display_text', '')

            try:
                cursor.execute("""
                    UPDATE persons
                    SET
                        entity_type = 'real_person',
                        group_affiliation = ?,
                        group_status = ?,
                        fame_level = ?,
                        show_group_in_bracket = ?,
                        bracket_display_text = ?,
                        bracket_data_updated_at = ?
                    WHERE person_id = ?
                """, (
                    group_name,
                    group_status,
                    fame_level,
                    show_bracket,
                    bracket_text,
                    datetime.now().isoformat(),
                    person_id
                ))

                if cursor.rowcount > 0:
                    self.stats['comedians'] += 1
                    self.logger.debug(f"更新: {item['person_name']} → {group_name}")

            except Exception as e:
                self.logger.error(f"エラー: {item['person_name']} - {e}")
                self.stats['errors'] += 1

        conn.commit()
        conn.close()

        self.logger.info(f"お笑い芸人: {self.stats['comedians']}件更新")

    def import_band_youtuber_groups(self, json_path: str = "band_youtuber_info.json"):
        """
        バンド・YouTuberグループ情報をインポート

        Args:
            json_path: JSONファイルパス
        """
        self.logger.info(f"バンド・YouTuberグループ情報をインポート: {json_path}")

        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            self.logger.warning(f"ファイルが見つかりません: {json_path}")
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for item in data:
            person_id = item['person_id']
            group_name = item['group_name']
            group_status = item.get('group_status')
            fame_level = item.get('fame_level')
            show_bracket = item.get('show_group_in_bracket', 0)
            bracket_text = item.get('bracket_display_text', '')
            group_type = item.get('group_type', 'band')

            try:
                cursor.execute("""
                    UPDATE persons
                    SET
                        entity_type = 'real_person',
                        group_affiliation = ?,
                        group_status = ?,
                        fame_level = ?,
                        show_group_in_bracket = ?,
                        bracket_display_text = ?,
                        bracket_data_updated_at = ?
                    WHERE person_id = ?
                """, (
                    group_name,
                    group_status,
                    fame_level,
                    show_bracket,
                    bracket_text,
                    datetime.now().isoformat(),
                    person_id
                ))

                if cursor.rowcount > 0:
                    if group_type == 'band':
                        self.stats['bands'] += 1
                    else:
                        self.stats['youtubers'] += 1
                    self.logger.debug(f"更新: {item['person_name']} → {group_name} [{group_type}]")

            except Exception as e:
                self.logger.error(f"エラー: {item['person_name']} - {e}")
                self.stats['errors'] += 1

        conn.commit()
        conn.close()

        self.logger.info(f"バンド: {self.stats['bands']}件、YouTuber: {self.stats['youtubers']}件更新")

    def run_import_all(self):
        """すべてのインポート処理を実行"""
        print("="*80)
        print("括弧メタデータ一括インポート")
        print("="*80)

        # 1. 架空キャラクター
        self.import_fictional_characters()

        # 2. お笑い芸人
        self.import_comedian_groups()

        # 3. バンド・YouTuber
        self.import_band_youtuber_groups()

        # 統計表示
        self.stats['total_updated'] = (
            self.stats['fictional_characters'] +
            self.stats['comedians'] +
            self.stats['bands'] +
            self.stats['youtubers']
        )

        print("\n" + "="*80)
        print("インポート結果")
        print("="*80)
        print(f"架空キャラクター: {self.stats['fictional_characters']}件")
        print(f"お笑い芸人: {self.stats['comedians']}件")
        print(f"バンド: {self.stats['bands']}件")
        print(f"YouTuber: {self.stats['youtubers']}件")
        print(f"合計更新件数: {self.stats['total_updated']}件")
        print(f"エラー: {self.stats['errors']}件")

    def verify_import(self):
        """インポート結果の検証"""
        print("\n" + "="*80)
        print("インポート検証")
        print("="*80)

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 括弧表示対象の確認
        cursor.execute("""
            SELECT
                person_name_ja,
                entity_type,
                group_affiliation,
                primary_work,
                bracket_display_text,
                show_group_in_bracket
            FROM persons
            WHERE show_group_in_bracket = 1
            ORDER BY recognition_score DESC
            LIMIT 20
        """)

        results = cursor.fetchall()

        print(f"\n括弧表示対象一覧（上位20件）:")
        print(f"{'人物名':<25} {'種類':<20} {'括弧テキスト':<25}")
        print("-" * 80)

        for row in results:
            person_name = row['person_name_ja']
            entity_type = row['entity_type']
            bracket_text = row['bracket_display_text'] or ''

            print(f"{person_name:<25} {entity_type:<20} {bracket_text:<25}")

        conn.close()


# ================================================================================
# メイン処理
# ================================================================================

def main():
    """メイン処理"""
    import argparse

    parser = argparse.ArgumentParser(description='括弧メタデータインポート')
    parser.add_argument('--db', default='episode_database.db', help='データベースパス')

    args = parser.parse_args()

    # インポート実行
    importer = BracketMetadataImporter(args.db)
    importer.run_import_all()

    # 検証
    importer.verify_import()

    print("\n✅ インポート完了！")


if __name__ == '__main__':
    main()
