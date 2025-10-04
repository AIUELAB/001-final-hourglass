#!/usr/bin/env python3
"""
人物データをCSV出力（括弧表示メタデータ付き）

目的:
1. episode_database.db の persons テーブルをCSVに出力
2. 括弧表示システムに必要な新カラムを追加（初期値）
3. Excelで確認・編集可能な形式で出力
"""

import csv
import sqlite3
from datetime import datetime
from typing import List, Dict


def export_persons_to_csv(
    db_path: str = "episode_database.db",
    output_path: str = None
) -> str:
    """
    personsテーブルをCSV出力

    Args:
        db_path: データベースファイルパス
        output_path: 出力CSVパス（Noneの場合は自動生成）

    Returns:
        出力ファイルパス
    """
    if not output_path:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f"persons_with_bracket_metadata_{timestamp}.csv"

    print(f"="*80)
    print(f"人物データCSV出力（括弧表示メタデータ付き）")
    print(f"="*80)
    print(f"データベース: {db_path}")
    print(f"出力先: {output_path}\n")

    # データベース接続
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # personsテーブルから全データ取得
    cursor.execute("""
        SELECT
            person_id,
            person_name_ja,
            person_name_en,
            birth_year,
            death_year,
            category,
            recognition_score
        FROM persons
        ORDER BY recognition_score DESC, person_name_ja
    """)

    rows = cursor.fetchall()
    print(f"取得件数: {len(rows)}件\n")

    # CSVに出力
    fieldnames = [
        # 既存カラム
        'person_id',
        'person_name_ja',
        'person_name_en',
        'birth_year',
        'death_year',
        'category',
        'recognition_score',

        # 新規カラム（括弧表示システム用）
        'entity_type',              # 'real_person' or 'fictional_character'
        'group_affiliation',        # 所属グループ名
        'primary_work',             # 架空キャラクターの作品名
        'show_group_in_bracket',    # 0 or 1
        'group_status',             # 'active', 'disbanded', 'hiatus'
        'fame_level',               # 'personal_more_famous', 'group_more_famous', 'equal'
        'bracket_display_text',     # 実際に表示するテキスト
        'notes'                     # メモ欄
    ]

    with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for row in rows:
            # 既存データ
            row_dict = {
                'person_id': row['person_id'],
                'person_name_ja': row['person_name_ja'],
                'person_name_en': row['person_name_en'],
                'birth_year': row['birth_year'] or '',
                'death_year': row['death_year'] or '',
                'category': row['category'] or '',
                'recognition_score': row['recognition_score'] or 0.0,

                # 新規カラム（初期値）
                'entity_type': 'real_person',  # デフォルトは実在人物
                'group_affiliation': '',
                'primary_work': '',
                'show_group_in_bracket': 0,
                'group_status': '',
                'fame_level': '',
                'bracket_display_text': '',
                'notes': ''
            }

            writer.writerow(row_dict)

    conn.close()

    print(f"✅ CSV出力完了: {output_path}")
    print(f"\n【次のステップ】")
    print(f"1. CSVをExcelで開く")
    print(f"2. 以下のカラムを手動/自動で埋める:")
    print(f"   - entity_type: 架空キャラクターの場合は 'fictional_character'")
    print(f"   - group_affiliation: グループ名（例: ダウンタウン、X JAPAN）")
    print(f"   - primary_work: 作品名（架空キャラクターの場合のみ）")
    print(f"   - show_group_in_bracket: 表示する場合は 1")
    print(f"   - group_status: 'active', 'disbanded', 'hiatus'")
    print(f"   - fame_level: 'personal_more_famous', 'group_more_famous', 'equal'")
    print(f"3. 保存して import_persons_from_csv.py で取り込み")

    return output_path


def generate_sample_data_csv(output_path: str = "sample_bracket_metadata.csv"):
    """
    サンプルデータCSV生成（記入例）

    Args:
        output_path: 出力CSVパス
    """
    print(f"\n{'='*80}")
    print(f"サンプルデータCSV生成")
    print(f"{'='*80}\n")

    sample_data = [
        # 架空キャラクター
        {
            'person_id': 'sample_001',
            'person_name_ja': 'モンキー・D・ルフィ',
            'person_name_en': 'Monkey D. Luffy',
            'birth_year': '',
            'death_year': '',
            'category': '架空キャラクター',
            'recognition_score': 9.5,
            'entity_type': 'fictional_character',
            'group_affiliation': '',
            'primary_work': 'ONE PIECE',
            'show_group_in_bracket': 1,
            'group_status': '',
            'fame_level': '',
            'bracket_display_text': 'ONE PIECE',
            'notes': '架空キャラクターは必ず作品名を表示'
        },
        # 現役お笑いコンビ
        {
            'person_id': 'sample_002',
            'person_name_ja': '又吉直樹',
            'person_name_en': 'Naoki Matayoshi',
            'birth_year': 1980,
            'death_year': '',
            'category': 'お笑い芸人',
            'recognition_score': 8.5,
            'entity_type': 'real_person',
            'group_affiliation': 'ピース',
            'primary_work': '',
            'show_group_in_bracket': 1,
            'group_status': 'active',
            'fame_level': 'equal',
            'bracket_display_text': 'ピース',
            'notes': '現役コンビで活動中'
        },
        # 解散バンド（表示しない）
        {
            'person_id': 'sample_003',
            'person_name_ja': 'YOSHIKI',
            'person_name_en': 'Yoshiki',
            'birth_year': 1965,
            'death_year': '',
            'category': 'ミュージシャン',
            'recognition_score': 8.7,
            'entity_type': 'real_person',
            'group_affiliation': 'X JAPAN',
            'primary_work': '',
            'show_group_in_bracket': 0,
            'group_status': 'disbanded',
            'fame_level': 'personal_more_famous',
            'bracket_display_text': '',
            'notes': '解散済みバンド、本人の方が有名'
        },
        # 本人の方が有名（表示しない）
        {
            'person_id': 'sample_004',
            'person_name_ja': 'HIKAKIN',
            'person_name_en': 'HIKAKIN',
            'birth_year': 1989,
            'death_year': '',
            'category': 'YouTuber',
            'recognition_score': 8.3,
            'entity_type': 'real_person',
            'group_affiliation': 'HIKAKIN & SEIKIN',
            'primary_work': '',
            'show_group_in_bracket': 0,
            'group_status': 'active',
            'fame_level': 'personal_more_famous',
            'bracket_display_text': '',
            'notes': '個人チャンネルの方が圧倒的に有名'
        },
        # 現役ダウンタウン（表示する）
        {
            'person_id': 'sample_005',
            'person_name_ja': '松本人志',
            'person_name_en': 'Hitoshi Matsumoto',
            'birth_year': 1963,
            'death_year': '',
            'category': 'お笑い芸人',
            'recognition_score': 8.8,
            'entity_type': 'real_person',
            'group_affiliation': 'ダウンタウン',
            'primary_work': '',
            'show_group_in_bracket': 1,
            'group_status': 'active',
            'fame_level': 'group_more_famous',
            'bracket_display_text': 'ダウンタウン',
            'notes': '現役コンビで活動中、コンビ名の方が有名'
        }
    ]

    fieldnames = [
        'person_id', 'person_name_ja', 'person_name_en', 'birth_year', 'death_year',
        'category', 'recognition_score', 'entity_type', 'group_affiliation',
        'primary_work', 'show_group_in_bracket', 'group_status', 'fame_level',
        'bracket_display_text', 'notes'
    ]

    with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sample_data)

    print(f"✅ サンプルCSV生成完了: {output_path}")
    print(f"\n【サンプル内容】")
    print(f"  - モンキー・D・ルフィ(ONE PIECE) - 架空キャラクター")
    print(f"  - 又吉直樹(ピース) - 現役お笑いコンビ")
    print(f"  - YOSHIKI - 解散バンド（括弧なし）")
    print(f"  - HIKAKIN - 個人の方が有名（括弧なし）")
    print(f"  - 松本人志(ダウンタウン) - 現役コンビ")


def main():
    """メイン処理"""
    import argparse

    parser = argparse.ArgumentParser(description='人物データCSV出力')
    parser.add_argument('--db', default='episode_database.db', help='データベースパス')
    parser.add_argument('--output', help='出力CSVパス')
    parser.add_argument('--sample', action='store_true', help='サンプルCSV生成')

    args = parser.parse_args()

    if args.sample:
        # サンプルCSV生成
        generate_sample_data_csv()
    else:
        # 実データCSV出力
        export_persons_to_csv(args.db, args.output)


if __name__ == '__main__':
    main()
