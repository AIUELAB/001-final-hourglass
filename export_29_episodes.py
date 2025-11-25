#!/usr/bin/env python3
"""
29件の検証済みエピソードをCSVファイルとして出力
"""

import pandas as pd
from datetime import datetime

def export_episodes():
    """29件のエピソードをCSVファイルとして出力"""

    # 既存のCSVファイルを読み込み
    df = pd.read_csv('trusted_episodes_latest.csv', encoding='utf-8-sig')

    print(f"読み込んだエピソード数: {len(df)}件")

    # タイムスタンプを生成
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 出力ファイル名
    output_file = f'episodes_29_export_{timestamp}.csv'

    # UTF-8 BOM付きで出力（Excel対応）
    df.to_csv(output_file, index=False, encoding='utf-8-sig')

    print(f"\n✅ エピソードをCSVファイルに出力しました: {output_file}")
    print(f"   - エピソード数: {len(df)}件")
    print(f"   - エンコーディング: UTF-8 with BOM (Excel対応)")

    # 統計情報を表示
    print("\n📊 エピソード統計:")
    print(f"   - カテゴリ数: {df['category'].nunique()}")
    print(f"   - 平均文字数: {df['character_count'].mean():.1f}文字")
    print(f"   - 最小文字数: {df['character_count'].min()}文字")
    print(f"   - 最大文字数: {df['character_count'].max()}文字")

    # カテゴリ別の件数
    print("\n📂 カテゴリ別件数:")
    category_counts = df['category'].value_counts()
    for category, count in category_counts.items():
        print(f"   - {category}: {count}件")

    # 最初の3件をサンプル表示
    print("\n📋 サンプル（最初の3件）:")
    for idx, row in df.head(3).iterrows():
        print(f"\n{idx+1}. {row['person_name']}（{row['episode_age']}歳）")
        print(f"   カテゴリ: {row['category']}")
        print(f"   文字数: {row['character_count']}文字")
        print(f"   エピソード: {row['episode_text'][:50]}...")

    return output_file

if __name__ == "__main__":
    output_file = export_episodes()
    print(f"\n💾 ファイル '{output_file}' を確認してください。")
    print("   Excelで開いても文字化けしないように、UTF-8 BOM付きで保存されています。")
