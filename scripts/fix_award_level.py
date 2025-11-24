#!/usr/bin/env python3
"""
award_levelが'AWARD'の行を'INTERNATIONAL'に修正するスクリプト
"""

import csv
import sys
from datetime import datetime

MASTER_CSV = "MASTER_EPISODES_CURRENT.csv"

def main():
    print("=" * 80)
    print("award_level修正スクリプト")
    print("=" * 80)

    # マスターCSV読み込み
    try:
        with open(MASTER_CSV, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            header = reader.fieldnames
    except FileNotFoundError:
        print(f"❌ マスターCSVが見つかりません: {MASTER_CSV}")
        sys.exit(1)

    initial_count = len(rows)
    print(f"総エピソード数: {initial_count}件")

    # バックアップ作成
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"{MASTER_CSV}.backup_fix_award_{timestamp}"
    with open(backup_file, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)
    print(f"✅ バックアップ作成: {backup_file}")

    # 修正対象の人物名（ヴェネツィア関連）
    target_names = ["黒澤明", "北野武", "溝口健二", "稲垣浩"]

    # 修正処理
    fixed_count = 0
    for row in rows:
        person_name = row.get("person_name", "")
        award_level = row.get("award_level", "")

        # award_level='AWARD' かつ 対象人物名の場合、修正
        if award_level == "AWARD" and person_name in target_names:
            print(f"修正: {person_name} (age={row.get('age', '?')}) AWARD → INTERNATIONAL")
            row["award_level"] = "INTERNATIONAL"
            fixed_count += 1

    # 保存
    with open(MASTER_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)

    print("\n" + "=" * 80)
    print("📊 修正結果")
    print("=" * 80)
    print(f"修正件数: {fixed_count}件")
    print(f"総エピソード数: {len(rows)}件")
    print(f"\n✅ 保存完了: {MASTER_CSV}")

    # award_level統計
    print("\n" + "-" * 80)
    print("award_level統計")
    print("-" * 80)
    international_count = sum(1 for row in rows if row.get("award_level") == "INTERNATIONAL")
    international_top_count = sum(1 for row in rows if row.get("award_level") == "INTERNATIONAL_TOP")
    nobel_count = sum(1 for row in rows if row.get("award_level") == "NOBEL")
    award_count = sum(1 for row in rows if row.get("award_level") == "AWARD")
    print(f"INTERNATIONAL: {international_count}件")
    print(f"INTERNATIONAL_TOP: {international_top_count}件")
    print(f"NOBEL: {nobel_count}件")
    print(f"AWARD: {award_count}件")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
