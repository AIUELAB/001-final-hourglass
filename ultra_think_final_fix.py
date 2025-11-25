#!/usr/bin/env python3
"""
Ultra Think 最終修正 - 残存違反の完全排除
"""
import csv
from datetime import datetime

def fix_remaining_violations():
    """残存する英語表記を修正"""
    input_file = "ultra_think_fixed_20250827_042853.csv"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"ultra_think_perfect_{timestamp}.csv"

    fixed_count = 0

    # 追加の修正辞書
    additional_fixes = {
        'Yukichi': '福沢諭吉',
        'Test Person': 'テスト人物',
        # 念のため他のパターンも
        'Fukuzawa': '福沢諭吉',
        'Nobunaga': '織田信長',
        'Hideyoshi': '豊臣秀吉',
        'Ieyasu': '徳川家康',
    }

    with open(input_file, 'r', encoding='utf-8-sig') as infile, \
         open(output_file, 'w', encoding='utf-8-sig', newline='') as outfile:

        reader = csv.DictReader(infile)
        writer = csv.DictWriter(outfile, fieldnames=reader.fieldnames)
        writer.writeheader()

        for row in reader:
            display_name = row.get('person_name_display', '')

            # 英語表記チェック（アルファベットが含まれている）
            if any(c.isalpha() and ord(c) < 128 for c in display_name):
                # 辞書から修正を試みる
                if display_name in additional_fixes:
                    row['person_name_display'] = additional_fixes[display_name]
                    fixed_count += 1
                    print(f"修正: {display_name} → {row['person_name_display']}")
                # person_name_jaから取得
                elif row.get('person_name_ja'):
                    row['person_name_display'] = row['person_name_ja']
                    fixed_count += 1
                    print(f"修正: {display_name} → {row['person_name_display']}")

            writer.writerow(row)

    print(f"\n✅ Ultra Think 最終修正完了")
    print(f"  修正件数: {fixed_count}件")
    print(f"  出力ファイル: {output_file}")

    return output_file

if __name__ == "__main__":
    fix_remaining_violations()
