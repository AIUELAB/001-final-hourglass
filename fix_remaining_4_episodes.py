#!/usr/bin/env python3
"""
残り4件の年号違反を修正

Author: Claude Code
Date: 2025-10-01
"""

import csv
import re
from unified_validation_system_with_persistence import create_validator


def remove_years(text: str) -> str:
    """年号・日付を削除"""
    # 西暦年（例: 2004年、1992年）
    text = re.sub(r'\d{4}年', '', text)
    # 和暦年（例: 令和元年、平成30年）
    text = re.sub(r'(?:明治|大正|昭和|平成|令和)\d{1,2}年', '', text)
    # 連続する空白を削除
    text = re.sub(r'\s+', '', text)
    return text


def main():
    """メイン処理"""
    input_csv = "episodes_enriched_20251001_144345_validated.csv"
    output_csv = "episodes_final_validated_20251001.csv"

    validator = create_validator()

    # CSVを読み込み
    with open(input_csv, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # 不合格の4件を特定して修正
    failed_rows = [
        {"row": 21, "person_name": "伊調馨"},  # 2004年
        {"row": 30, "person_name": "吉田秀彦"},  # 1992年
        {"row": 43, "person_name": "宮里藍"},
        {"row": 55, "person_name": "本庶佑"}  # 1992年
    ]

    fixed_count = 0

    print("="*80)
    print("残り4件の年号違反を修正")
    print("="*80 + "\n")

    for failed in failed_rows:
        row_index = failed["row"] - 1
        if row_index < 0 or row_index >= len(rows):
            continue

        row = rows[row_index]
        person_name = row['person_name']
        original_text = row['episode_text']

        # 年号削除
        fixed_text = remove_years(original_text)

        print(f"修正中: {person_name}")
        print(f"  元: {original_text[:80]}...")
        print(f"  修正後: {fixed_text[:80]}...")
        print()

        # 検証
        episode_dict = {
            "episode_id": f"E{row_index+1:03d}",
            "person_name": person_name,
            "episode_text": fixed_text,
            "episode_age": int(row['episode_age']),
            "user_age": int(row['episode_age']),
            "category": row.get('category', '不明')
        }

        result = validator.validate_episode(episode_dict)

        if result.is_valid:
            rows[row_index]['episode_text'] = fixed_text
            rows[row_index]['character_count'] = len(fixed_text)
            rows[row_index]['is_valid'] = True
            rows[row_index]['violation_count'] = 0
            fixed_count += 1
            print(f"  ✅ 修正成功 ({len(fixed_text)}文字)\n")
        else:
            print(f"  ❌ 修正失敗\n")

    # 出力
    with open(output_csv, 'w', encoding='utf-8-sig', newline='') as f:
        fieldnames = list(rows[0].keys())
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    # 最終検証
    valid_count = sum(1 for row in rows if row['is_valid'] == 'True' or row['is_valid'] is True)

    print("="*80)
    print("修正完了")
    print("="*80)
    print(f"\n修正件数: {fixed_count}/4")
    print(f"最終合格率: {valid_count}/100 ({valid_count}%)")
    print(f"\n出力ファイル: {output_csv}")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
