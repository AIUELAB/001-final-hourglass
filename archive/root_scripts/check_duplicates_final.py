#!/usr/bin/env python3
"""
キャラクター重複チェック

100件データベースの重複を検出・分析
"""

import csv
from pathlib import Path
from collections import Counter
from typing import List, Dict


def check_duplicates():
    """重複キャラクターをチェック"""

    project_root = Path(__file__).parent
    csv_file = project_root / "phase5_outputs" / "sports_manga_characters_phase3_batch5_FIXED.csv"

    print("=" * 70)
    print("🔍 キャラクター重複チェック")
    print("=" * 70)
    print()

    # CSVを読み込み
    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        characters = list(reader)

    print(f"📂 総キャラクター数: {len(characters)}件")
    print()

    # 名前でカウント
    name_counter = Counter(char['character_name'] for char in characters)

    # 重複を検出
    duplicates = {name: count for name, count in name_counter.items() if count > 1}

    if not duplicates:
        print("✅ 重複なし！すべてのキャラクターがユニークです")
        print()
        return

    print("=" * 70)
    print(f"⚠️  重複検出：{len(duplicates)}件")
    print("=" * 70)
    print()

    # 重複の詳細を表示
    for name, count in sorted(duplicates.items(), key=lambda x: x[1], reverse=True):
        print(f"📌 {name}: {count}回")
        print()

        # 該当する行をすべて表示
        for i, char in enumerate(characters, 1):
            if char['character_name'] == name:
                print(f"  位置 {i:3d}: {char['work_title']} | {char['genre']} | {char['age_in_story']}")
        print()

    print("=" * 70)
    print("📊 重複統計")
    print("=" * 70)
    print()
    print(f"重複キャラクター数: {len(duplicates)}種類")
    print(f"重複インスタンス総数: {sum(duplicates.values())}件")
    print(f"重複による余分な件数: {sum(duplicates.values()) - len(duplicates)}件")
    print()
    print(f"実質ユニークキャラクター数: {len(name_counter)}件")
    print(f"重複を除くと不足: {100 - len(name_counter)}件")
    print()


if __name__ == "__main__":
    check_duplicates()
