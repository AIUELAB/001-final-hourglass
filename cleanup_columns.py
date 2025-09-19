#!/usr/bin/env python3
"""
不要なカラムを削除してCSVファイルを整理
"""

import pandas as pd
from datetime import datetime
import os

def cleanup_columns():
    print("=" * 80)
    print("📊 CSVファイル カラム整理")
    print("=" * 80)

    # 入力ファイル
    input_file = 'ultra_think_100_PERCENT_COMPLETE_20250915_190404.csv'

    if not os.path.exists(input_file):
        print(f"❌ ファイルが見つかりません: {input_file}")
        return

    print(f"\n📂 ファイル読み込み: {input_file}")
    df = pd.read_csv(input_file)
    print(f"✅ 読み込み完了: {len(df):,}行 × {len(df.columns)}列")

    # 削除するカラムのリスト
    columns_to_drop = [
        'episode_hash',           # 1. 内部処理用ハッシュ
        'episode_id',             # 2. エピソードID
        'episode_text',           # 3. エピソードテキスト（大容量）
        'episode_title',          # 4. エピソードタイトル
        'episode_type',           # 5. エピソードタイプ
        'episode_date',           # 6. エピソード日付
        'episode_year',           # 7. エピソード年
        'era',                    # 8. 時代（エピソード関連）
        'is_published',           # 9. 公開フラグ（用途不明）
        'recognition_metadata',   # 10. メタデータ（JSON形式で重い）
        'extended_data',          # 11. 拡張データ（大容量の可能性）
        'accuracy_score',         # 12. recognition_scoreと重複
        'impact_score',           # 13. 使用用途不明
        'content_score',          # 14. Wikipedia関連と重複
        'category_score',         # 15. カテゴリで判定可能
        'priority_score',         # 16. 優先度は他で判定可能
        'news_score',             # 17. search_result_countで代替可能
        'academic_score',         # 18. 特定分野のみ必要
        'norm_recognition'        # 19. recognition_scoreの正規化版（重複）
    ]

    print(f"\n🗑️ 削除対象カラム数: {len(columns_to_drop)}個")

    # 実際に存在するカラムのみを削除対象とする
    existing_columns_to_drop = [col for col in columns_to_drop if col in df.columns]
    missing_columns = [col for col in columns_to_drop if col not in df.columns]

    if missing_columns:
        print(f"\n⚠️ 存在しないカラム（スキップ）:")
        for col in missing_columns:
            print(f"  - {col}")

    print(f"\n✅ 実際に削除するカラム: {len(existing_columns_to_drop)}個")
    for i, col in enumerate(existing_columns_to_drop, 1):
        print(f"  {i:2d}. {col}")

    # カラムを削除
    df_cleaned = df.drop(columns=existing_columns_to_drop)

    print(f"\n📊 整理後のデータ:")
    print(f"  行数: {len(df_cleaned):,}行")
    print(f"  列数: {len(df_cleaned.columns)}列（{len(df.columns)}列 → {len(df_cleaned.columns)}列）")
    print(f"  削減率: {(1 - len(df_cleaned.columns)/len(df.columns))*100:.1f}%")

    # 残ったカラムを表示
    print(f"\n📋 保持されたカラム（{len(df_cleaned.columns)}個）:")
    for i, col in enumerate(df_cleaned.columns, 1):
        print(f"  {i:2d}. {col}")

    # ファイルサイズの比較
    original_size = df.memory_usage(deep=True).sum() / (1024 * 1024)  # MB
    cleaned_size = df_cleaned.memory_usage(deep=True).sum() / (1024 * 1024)  # MB

    print(f"\n💾 メモリ使用量:")
    print(f"  整理前: {original_size:.2f} MB")
    print(f"  整理後: {cleaned_size:.2f} MB")
    print(f"  削減量: {original_size - cleaned_size:.2f} MB ({(1 - cleaned_size/original_size)*100:.1f}%削減)")

    # 出力ファイル名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'ultra_think_CLEANED_COLUMNS_{timestamp}.csv'

    # CSV保存（BOM付きUTF-8）
    print(f"\n💾 整理済みファイルを保存...")
    with open(output_file, 'w', encoding='utf-8-sig') as f:
        df_cleaned.to_csv(f, index=False)

    print(f"✅ 保存完了: {output_file}")

    # ファイルサイズ確認
    output_size = os.path.getsize(output_file) / (1024 * 1024)  # MB
    input_size = os.path.getsize(input_file) / (1024 * 1024)  # MB

    print(f"\n📁 ファイルサイズ:")
    print(f"  整理前: {input_size:.2f} MB")
    print(f"  整理後: {output_size:.2f} MB")
    print(f"  削減量: {input_size - output_size:.2f} MB ({(1 - output_size/input_size)*100:.1f}%削減)")

    # サマリー
    print("\n" + "=" * 80)
    print("✅ カラム整理完了！")
    print("=" * 80)
    print(f"\n📊 整理結果:")
    print(f"  削除カラム数: {len(existing_columns_to_drop)}個")
    print(f"  保持カラム数: {len(df_cleaned.columns)}個")
    print(f"  ファイルサイズ削減: {(1 - output_size/input_size)*100:.1f}%")
    print(f"\n📁 出力ファイル: {output_file}")

    return output_file, df_cleaned

if __name__ == "__main__":
    output_file, df_cleaned = cleanup_columns()

    # Brave Search統計の確認
    if 'search_source' in df_cleaned.columns:
        brave_count = df_cleaned[df_cleaned['search_source'].str.contains('brave', na=False)]
        print(f"\n🔍 Brave Search統計（整理後）:")
        print(f"  実データ: {len(brave_count):,}件")
        print(f"  完成率: {len(brave_count)/len(df_cleaned)*100:.1f}%")