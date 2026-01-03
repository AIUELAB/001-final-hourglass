#!/usr/bin/env python3
"""
全カラムの空値を補完するスクリプト

補完戦略:
1. 完全に空（100%）のカラムは削除
2. Boolean/フラグ系はデフォルト値（False）
3. 数値系スコアは中央値
4. テキスト系は空文字または"未確認"
5. 日時系は現在時刻
"""

import pandas as pd
from pathlib import Path
from datetime import datetime


def fill_all_null_values():
    """全カラムの空値を補完"""

    # ファイルパス
    csv_path = Path("/Users/admin/Documents/AIUELAB/001-final-hourglass/preserved/data/MASTER_EPISODES_CURRENT.csv")

    if not csv_path.exists():
        print(f"❌ ファイルが見つかりません: {csv_path}")
        return

    # CSVを読み込み
    print(f"📖 CSVを読み込み中: {csv_path.name}")
    df = pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)

    print(f"\n総レコード数: {len(df)}")
    print(f"総カラム数: {len(df.columns)}")

    # 補完前の空値統計
    total_nulls_before = df.isna().sum().sum()
    print(f"\n補完前の総空値数: {total_nulls_before:,}")

    # バックアップ作成
    backup_path = csv_path.parent / f"{csv_path.stem}_backup_before_fill_all.csv"
    print(f"\n💾 バックアップを作成: {backup_path.name}")
    df.to_csv(backup_path, index=False, encoding="utf-8-sig")

    print("\n" + "=" * 80)
    print("🔄 空値補完を開始")
    print("=" * 80)

    changes = []

    # 1. 完全に空のカラムを削除
    print("\n1️⃣ 完全に空（≥99.9%）のカラムを削除中...")
    columns_to_drop = []
    for col in df.columns:
        null_pct = (df[col].isna().sum() / len(df)) * 100
        if null_pct >= 99.9:
            columns_to_drop.append(col)

    if columns_to_drop:
        print(f"削除するカラム（{len(columns_to_drop)}個）:")
        for col in columns_to_drop:
            print(f"  - {col}")
        df = df.drop(columns=columns_to_drop)
        changes.append(f"削除: {len(columns_to_drop)}カラム")

    # 2. Boolean/フラグ系をデフォルト値で埋める
    print("\n2️⃣ Boolean/フラグ系をFalseで埋める...")
    boolean_cols = ["textbook", "notoriety", "wikipedia_ja", "is_group_member"]
    for col in boolean_cols:
        if col in df.columns:
            before = df[col].isna().sum()
            df[col] = df[col].fillna(False)
            if before > 0:
                print(f"  {col}: {before}個を埋めた")
                changes.append(f"{col}: {before}個")

    # 3. fact_check_resultを"未確認"で埋める
    print("\n3️⃣ fact_check_resultを'未確認'で埋める...")
    if "fact_check_result" in df.columns:
        before = df["fact_check_result"].isna().sum()
        df["fact_check_result"] = df["fact_check_result"].fillna("未確認")
        if before > 0:
            print(f"  fact_check_result: {before}個を埋めた")
            changes.append(f"fact_check_result: {before}個")

    # 4. 数値系スコアを中央値で埋める
    print("\n4️⃣ 数値系スコアを中央値で埋める...")
    numeric_score_cols = [
        "quality_score",
        "surprise_score",
        "fame_score",
        "episode_fame_score",
        "composite_score",
        "impressiveness_score",
        "priority_score",
        "記憶性スコア",
        "共感性スコア",
        "意外性スコア",
        "生成品質スコア",
        "教育的価値",
        "ストーリー品質",
        "事実密度",
        "事実密度_float",
        "episode_importance_score",
        "fame_tier",
        "episode_fame_tier",
        "episode_count",
        "char_count",
        "slot",
        "highlight_rank",
        "is_highlight",
        "教育的価値_original",
        "ストーリー品質_original",
        "事実密度_original",
        "episode_fame_score_original",
    ]

    for col in numeric_score_cols:
        if col in df.columns:
            before = df[col].isna().sum()
            if before > 0:
                # 数値型に変換できるものだけ処理
                numeric_values = pd.to_numeric(df[col], errors="coerce")
                median_val = numeric_values.median()
                if not pd.isna(median_val):
                    df[col] = df[col].fillna(median_val)
                    print(f"  {col}: {before}個を中央値 {median_val:.2f} で埋めた")
                    changes.append(f"{col}: {before}個")
                else:
                    print(f"  ⚠️ {col}: 数値の中央値を計算できませんでした")

    # 4.5. award_levelを最頻値またはデフォルト値で埋める
    print("\n4️⃣-2 award_levelを最頻値で埋める...")
    if "award_level" in df.columns:
        before = df["award_level"].isna().sum()
        if before > 0:
            mode_val = df["award_level"].mode()
            if len(mode_val) > 0:
                df["award_level"] = df["award_level"].fillna(mode_val[0])
                print(f"  award_level: {before}個を最頻値 {mode_val[0]} で埋めた")
            else:
                df["award_level"] = df["award_level"].fillna("0")
                print(f"  award_level: {before}個をデフォルト値 '0' で埋めた")
            changes.append(f"award_level: {before}個")

    # 5. tierとweekを最頻値で埋める
    print("\n5️⃣ tier/weekを最頻値で埋める...")
    categorical_cols = ["tier", "week"]
    for col in categorical_cols:
        if col in df.columns:
            before = df[col].isna().sum()
            if before > 0:
                mode_val = df[col].mode()[0] if len(df[col].mode()) > 0 else 0
                df[col] = df[col].fillna(mode_val)
                print(f"  {col}: {before}個を最頻値 {mode_val} で埋めた")
                changes.append(f"{col}: {before}個")

    # 6. 日時系を現在時刻で埋める
    print("\n6️⃣ 日時系を現在時刻で埋める...")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    datetime_cols = ["fame_score_updated_at", "episode_fame_score_updated_at", "generated_at"]
    for col in datetime_cols:
        if col in df.columns:
            before = df[col].isna().sum()
            if before > 0:
                df[col] = df[col].fillna(now)
                print(f"  {col}: {before}個を現在時刻で埋めた")
                changes.append(f"{col}: {before}個")

    # 7. generation_timestampをデフォルト値で埋める
    print("\n7️⃣ generation_timestampをデフォルト値で埋める...")
    if "generation_timestamp" in df.columns:
        before = df["generation_timestamp"].isna().sum()
        if before > 0:
            default_timestamp = "1900-01-01 00:00:00"
            df["generation_timestamp"] = df["generation_timestamp"].fillna(default_timestamp)
            print(f"  generation_timestamp: {before}個をデフォルト値で埋めた")
            changes.append(f"generation_timestamp: {before}個")

    # 8. テキスト系を空文字で埋める
    print("\n8️⃣ テキスト系を空文字で埋める...")
    text_cols = [
        "group_name",
        "work_title",
        "affiliation",
        "title",
        "name_raw",
        "source",
        "category_original",
        "episode_id_original",
        "display_name_original",
        "人生の節目タグ",
        "highlight_selection_method",
    ]
    for col in text_cols:
        if col in df.columns:
            before = df[col].isna().sum()
            if before > 0:
                df[col] = df[col].fillna("")
                print(f"  {col}: {before}個を空文字で埋めた")
                changes.append(f"{col}: {before}個")

    # 補完後の空値統計
    total_nulls_after = df.isna().sum().sum()

    print("\n" + "=" * 80)
    print("✅ 補完完了")
    print("=" * 80)
    print(f"\n補完前の総空値数: {total_nulls_before:,}")
    print(f"補完後の総空値数: {total_nulls_after:,}")
    print(f"埋めた空値数: {total_nulls_before - total_nulls_after:,}")
    print(f"削減率: {(total_nulls_before - total_nulls_after) / total_nulls_before * 100:.1f}%")

    # まだ空値があるカラムを表示
    if total_nulls_after > 0:
        print("\n⚠️ まだ空値があるカラム:")
        remaining_nulls = df.isna().sum()
        remaining_nulls = remaining_nulls[remaining_nulls > 0].sort_values(ascending=False)
        for col, count in remaining_nulls.items():
            pct = (count / len(df)) * 100
            print(f"  {col}: {count}個 ({pct:.1f}%)")

    # 保存
    print(f"\n💾 変更を保存中: {csv_path.name}")
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    print("\n✅ 完了！")
    print(f"最終カラム数: {len(df.columns)}")
    print(f"最終レコード数: {len(df)}")


if __name__ == "__main__":
    fill_all_null_values()
