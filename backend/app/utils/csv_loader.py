"""
CSV インポートユーティリティ

MASTER_EPISODES_CURRENT.csv からデータベースへのインポート
"""

import csv
from pathlib import Path
from typing import Optional


def get_default_csv_path() -> Path:
    """
    デフォルトのCSVパスを取得

    Returns:
        CSVファイルのパス
    """
    # バックエンドディレクトリから実行される場合を考慮
    csv_path = Path("MASTER_EPISODES_CURRENT.csv")
    if not csv_path.exists():
        csv_path = Path("../MASTER_EPISODES_CURRENT.csv")
    if not csv_path.exists():
        csv_path = Path("../../MASTER_EPISODES_CURRENT.csv")
    return csv_path


def import_csv_to_db(db, csv_path: str, limit: Optional[int] = None) -> int:
    """
    CSVからデータベースへインポート

    Args:
        db: データベースインスタンス
        csv_path: CSVファイルパス
        limit: インポート件数制限（Noneの場合は全件）

    Returns:
        インポートされた件数
    """
    csv_path_obj = Path(csv_path)

    if not csv_path_obj.exists():
        print(f"⚠️  CSVファイルが見つかりません: {csv_path}")
        return 0

    # 既存データの確認
    characters, total = db.get_all_characters(page=1, page_size=1)
    if total > 0:
        print(f"ℹ️  既にデータが存在します（{total}件）。スキップします。")
        return total

    count = 0
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)

        for row in reader:
            # CSVのカラム名に合わせてマッピング
            character = {
                'character_name': row.get('person_name', ''),
                'work_title': row.get('work_title', ''),  # work_titleはそのまま
                'genre': row.get('category', ''),  # categoryをgenreとして使用
                'episode_category': row.get('episode_type', ''),  # episode_typeをepisode_categoryとして使用
                'episode_text': row.get('episode_text', '')
            }

            db.insert_character(character)
            count += 1

            if limit and count >= limit:
                break

    print(f"✅ {count}件のデータをインポートしました")
    return count
