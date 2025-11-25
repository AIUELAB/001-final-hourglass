#!/usr/bin/env python3
"""
詳細な言語分析 - 中国語・韓国語・英語名の正確な検出
"""

import pandas as pd
import re

def detailed_language_analysis(csv_path: str):
    """より正確な言語分析を実行"""

    df = pd.read_csv(csv_path)
    print(f"📊 詳細言語分析 - {len(df):,} レコード")
    print("-" * 80)

    # より正確なパターン定義
    patterns = {
        # 英語：アルファベットのみで構成される名前
        '純英語名': r'^[A-Za-z\s\-\.\']+$',

        # 中国語：漢字のみ（日本語の漢字も含むが、ひらがな・カタカナと組み合わせでない場合）
        '漢字名': r'^[\u4e00-\u9fff\s・]+$',

        # 韓国語：ハングル文字
        '韓国語名': r'[\uac00-\ud7af]',

        # カタカナ表記：カタカナのみ
        'カタカナ表記': r'^[\u30a0-\u30ff\s・\-]+$',

        # 英語＋カタカナ混在
        '英語カタカナ混在': r'[A-Za-z].*[\u30a0-\u30ff]|[\u30a0-\u30ff].*[A-Za-z]',
    }

    results = {}

    for pattern_name, pattern in patterns.items():
        mask = df['person_name_display'].str.contains(pattern, na=False, regex=True)
        count = mask.sum()
        results[pattern_name] = count

        print(f"{pattern_name}: {count:,} 件")

        if count > 0 and count <= 10:
            # 件数が少ない場合は全て表示
            samples = df[mask]['person_name_display'].tolist()
            print(f"  全件: {', '.join(samples)}")
        elif count > 0:
            # 件数が多い場合はサンプル表示
            samples = df[mask]['person_name_display'].head(5).tolist()
            print(f"  サンプル: {', '.join(samples)}")
        print()

    # 日本語（ひらがな・カタカナ・漢字混在）の識別
    japanese_pattern = r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]'
    pure_japanese = df['person_name_display'].str.contains(r'^[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff\s・\-（）]+$', na=False, regex=True)
    japanese_count = pure_japanese.sum()

    print(f"日本語名（ひらがな・カタカナ・漢字）: {japanese_count:,} 件")
    if japanese_count > 0:
        samples = df[pure_japanese]['person_name_display'].head(5).tolist()
        print(f"  サンプル: {', '.join(samples)}")

    print("-" * 80)

    # 国籍別の分析
    print("🌏 国籍別分析")
    nationality_counts = df['nationality'].value_counts().head(10)
    for nationality, count in nationality_counts.items():
        print(f"  {nationality}: {count:,} 件")

    return results

if __name__ == "__main__":
    csv_file = "/Users/admin/Documents/AIUELAB/001-final-hourglass/ultra_think_CONVERTED_20250827_224054.csv"
    detailed_language_analysis(csv_file)
