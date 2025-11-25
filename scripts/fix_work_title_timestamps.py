#!/usr/bin/env python3
"""
work_titleフィールドのタイムスタンプ問題を修正するスクリプト

問題: 一部のREAL（実在）人物のwork_titleにタイムスタンプ（YYYY-MM-DD HH:MM:SS）が入っている
修正: person_type=REALの場合、work_titleを空にする
"""

import csv
import re
from datetime import datetime

CSV_FILE = "MASTER_EPISODES_CURRENT.csv"

def is_timestamp(value):
    """値がタイムスタンプ形式かチェック"""
    if not value:
        return False
    # YYYY-MM-DD HH:MM:SS 形式を検出
    timestamp_pattern = r'^\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}$'
    return bool(re.match(timestamp_pattern, value.strip()))

def main():
    print("=" * 80)
    print("work_title タイムスタンプ修正スクリプト")
    print("=" * 80)

    # CSVを読み込み
    with open(CSV_FILE, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames
        rows = list(reader)

    initial_count = len(rows)
    print(f"\n総エピソード数: {initial_count}件")

    # バックアップ作成
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"{CSV_FILE}.backup_{timestamp}"
    with open(backup_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)
    print(f"✅ バックアップ作成: {backup_file}")

    # 修正処理
    fixed_count = 0

    for row in rows:
        person_type = row.get('person_type', '').upper()
        work_title = row.get('work_title', '')

        # person_type=REALの場合、work_titleをクリア
        if person_type == 'REAL' or 'REAL' in person_type:
            if work_title and (is_timestamp(work_title) or work_title.strip()):
                # タイムスタンプまたは何らかの値が入っている場合のみカウント
                if is_timestamp(work_title):
                    print(f"  修正: {row['episode_id']} ({row['person_name']})")
                    print(f"    work_title: '{work_title}' → ''")
                    fixed_count += 1
                row['work_title'] = ''

    # CSVに書き戻し
    with open(CSV_FILE, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)

    print("\n" + "=" * 80)
    print("修正結果")
    print("=" * 80)
    print(f"タイムスタンプ修正: {fixed_count}件")
    print(f"✅ 保存完了: {CSV_FILE}")
    print("=" * 80)

if __name__ == "__main__":
    main()
