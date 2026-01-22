#!/usr/bin/env python3
"""
カラム整理スクリプト
計画に基づき、不要カラム19個を削除して73→54カラムに整理
"""

import pandas as pd
from pathlib import Path

# 削除対象カラム（計画書から）
COLUMNS_TO_DROP = [
    # A. 廃止・レガシーカラム（9個 - v2は既に存在しない）
    "episode_fame_v5_keyphrase",  # 値がすべてNULL、廃止済み
    "quality_score",              # 7軸スコアで完全置換
    "priority_score",             # 未使用、古いシステム
    "fame_score_japan",           # celebrity_score_v2に統合済み
    "notoriety",                  # 未使用
    "wikipedia_ja",               # 未使用フラグ
    "slot",                       # ageから動的計算可能
    "年代",                       # ageから動的計算可能
    "affiliation",                # group_nameで代替済み

    # B. 機能未実装カラム（10個）
    "is_highlight",               # ハイライト機能未実装
    "highlight_rank",             # ハイライト機能未実装
    "char_count",                 # episode_text.lengthで代替可
    "fact_check_result",          # verification_statusで代替
    "fact_check_issues",          # verification_statusで代替
    "episode_authenticity",       # 検証詳細（非表示）
    "人生の節目タグ",               # 分析用（未実装）
    "award_level",                # 未使用
    "textbook",                   # 未使用フラグ
    "episode_content",            # episode_textと重複
]

def cleanup_columns():
    """カラム削除を実行"""
    input_path = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")
    output_path = input_path  # 上書き

    print("=" * 60)
    print("エピソードDBカラム整理")
    print("=" * 60)

    # CSVを読み込み
    print(f"\n📖 読み込み中: {input_path}")
    df = pd.read_csv(input_path, dtype=str)

    original_cols = len(df.columns)
    original_rows = len(df)
    print(f"   カラム数: {original_cols}")
    print(f"   行数: {original_rows:,}")

    # 存在するカラムのみ削除
    existing_cols_to_drop = [col for col in COLUMNS_TO_DROP if col in df.columns]
    missing_cols = [col for col in COLUMNS_TO_DROP if col not in df.columns]

    print(f"\n📋 削除対象カラム ({len(existing_cols_to_drop)}個):")
    for col in existing_cols_to_drop:
        print(f"   - {col}")

    if missing_cols:
        print(f"\n⚠️  既に存在しないカラム ({len(missing_cols)}個):")
        for col in missing_cols:
            print(f"   - {col}")

    # カラム削除
    df = df.drop(columns=existing_cols_to_drop)

    new_cols = len(df.columns)
    print(f"\n✅ 削除完了: {original_cols} → {new_cols} カラム")
    print(f"   削減数: {original_cols - new_cols}個 ({(original_cols - new_cols) / original_cols * 100:.1f}%)")

    # 保存
    print(f"\n💾 保存中: {output_path}")
    df.to_csv(output_path, index=False)

    # 検証
    df_check = pd.read_csv(output_path, dtype=str)
    assert len(df_check) == original_rows, "行数が変化しました！"
    assert len(df_check.columns) == new_cols, "カラム数が不一致！"

    print(f"\n✅ 検証完了")
    print(f"   行数: {len(df_check):,} (変化なし)")
    print(f"   カラム数: {len(df_check.columns)}")

    print("\n" + "=" * 60)
    print("残存カラム一覧:")
    print("=" * 60)
    for i, col in enumerate(df_check.columns, 1):
        print(f"  {i:2d}. {col}")

    print("\n🎉 カラム整理完了！")
    return df_check

if __name__ == "__main__":
    cleanup_columns()
