"""CSVデータローダー"""

import csv
from pathlib import Path
from typing import Optional


def get_default_csv_path() -> Path:
    """デフォルトCSVパスを取得"""
    # プロジェクトルートからの相対パス
    project_root = Path(__file__).parent.parent.parent.parent
    csv_path = project_root / "MASTER_EPISODES_CURRENT.csv"
    return csv_path


def import_csv_to_db(db, csv_path: str) -> int:
    """
    CSVファイルをデータベースにインポート

    Args:
        db: データベースインスタンス
        csv_path: CSVファイルパス

    Returns:
        インポート件数
    """
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
