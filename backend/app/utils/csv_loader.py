"""CSVデータローダー"""

import csv
import os
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime


def get_default_csv_path() -> Path:
    """デフォルトCSVパスを取得"""
    # プロジェクトルートからの相対パス
    project_root = Path(__file__).parent.parent.parent.parent
    csv_path = project_root / "MASTER_EPISODES_CURRENT.csv"
    return csv_path


def get_csv_modification_time(csv_path: str) -> float:
    """
    CSVファイルの最終更新時刻を取得

    Args:
        csv_path: CSVファイルパス

    Returns:
        UNIXタイムスタンプ（エポック秒）
    """
    try:
        return os.path.getmtime(csv_path)
    except OSError:
        return 0


def import_csv_to_db(db, csv_path: str, force: bool = False) -> int:
    """
    CSVファイルをデータベースにインポート

    Args:
        db: データベースインスタンス
        csv_path: CSVファイルパス
        force: True の場合、既存データを削除して強制再インポート

    Returns:
        インポート件数
    """
    # 既存データ確認
    cursor = db.conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM characters")
    existing_count = cursor.fetchone()[0]

    if existing_count > 0 and not force:
        print(f"⚠️  既存データあり ({existing_count}件) - インポートスキップ")
        print("💡 強制再インポートする場合は force=True を指定してください")
        return 0

    # 強制再インポートの場合は既存データを削除
    if force and existing_count > 0:
        print(f"🔄 既存データ削除中 ({existing_count}件)...")
        cursor.execute("DELETE FROM characters")
        db.conn.commit()
        print("✅ 既存データ削除完了")

    count = 0

    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)

            for row in reader:
                try:
                    # person_nameがあるレコードのみ処理
                    if not row.get('person_name'):
                        continue

                    # データベースに挿入（既存スキーマに合わせる）
                    db.insert_character({
                        'character_name': row.get('person_name', ''),
                        'work_title': row.get('work_title', '不明'),
                        'genre': row.get('category', '未分類'),
                        'age_in_story': str(int(float(row.get('age', 0)))) if row.get('age') else '不明',
                        'key_episode': row.get('episode_text', '')[:500],  # 最初の500文字
                        'detailed_achievements': row.get('episode_text', ''),
                        'story_events': '',
                        'growth_narrative': '',
                        'wikipedia_url': '',
                        'validation_status': row.get('fact_check_result', 'PENDING'),
                        'curator_notes': f"Type: {row.get('person_type', 'REAL')}, Episode: {row.get('episode_type', '')}",
                    })
                    count += 1
                except Exception as e:
                    # 個別レコードのエラーはスキップ
                    print(f"⚠️  レコードスキップ: {row.get('person_name', 'Unknown')} - {e}")
                    continue

    except FileNotFoundError:
        print(f"❌ CSVファイルが見つかりません: {csv_path}")
        return 0
    except Exception as e:
        print(f"❌ CSVインポートエラー: {e}")
        return 0

    return count
