#!/usr/bin/env python3
"""
年代カラムの空値を埋めるスクリプト

年齢（age）から年代を生成:
- 0-9歳 → 0代
- 10-19歳 → 10代
- 20-29歳 → 20代
- ...
- 90歳以上 → 90代以上
"""

import pandas as pd
from pathlib import Path


def age_to_nendai(age):
    """年齢から年代を生成"""
    if pd.isna(age):
        return None

    age_int = int(age)

    if age_int < 10:
        return "0代"
    elif age_int < 20:
        return "10代"
    elif age_int < 30:
        return "20代"
    elif age_int < 40:
        return "30代"
    elif age_int < 50:
        return "40代"
    elif age_int < 60:
        return "50代"
    elif age_int < 70:
        return "60代"
    elif age_int < 80:
        return "70代"
    elif age_int < 90:
        return "80代"
    else:
        return "90代以上"


def fill_missing_nendai():
    """年代カラムの空値を埋める"""

    # ファイルパス
    csv_path = Path("/Users/admin/Documents/AIUELAB/001-final-hourglass/preserved/data/MASTER_EPISODES_CURRENT.csv")

    if not csv_path.exists():
        print(f"❌ ファイルが見つかりません: {csv_path}")
        return

    # CSVを読み込み
    print(f"📖 CSVを読み込み中: {csv_path}")
    df = pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)

    # 現在の統計
    total_rows = len(df)
    missing_nendai = df["年代"].isna().sum()

    print("\n📊 現在の状態:")
    print(f"総行数: {total_rows}")
    print(f"年代が空: {missing_nendai} 行 ({missing_nendai / total_rows * 100:.1f}%)")

    if missing_nendai == 0:
        print("✅ 年代カラムに空値はありません")
        return

    # 年代が空のレコードをサンプル表示
    print("\n🔍 年代が空のレコードサンプル（年齢順）:")
    missing_mask = df["年代"].isna()
    sample = df[missing_mask][["episode_id", "person_name", "age", "年代"]].sort_values("age").head(10)
    print(sample.to_string())

    # 年代を生成
    print("\n🔄 年代を生成中...")
    df.loc[missing_mask, "年代"] = df.loc[missing_mask, "age"].apply(age_to_nendai)

    # 生成後の統計
    still_missing = df["年代"].isna().sum()
    filled_count = missing_nendai - still_missing

    print("\n✅ 生成完了:")
    print(f"埋められた: {filled_count} 行")
    print(f"まだ空: {still_missing} 行")

    if filled_count > 0:
        # 生成された年代の分布
        print("\n📊 生成された年代の分布:")
        generated = df[missing_mask & df["年代"].notna()]["年代"].value_counts().sort_index()
        print(generated.to_string())

        # バックアップ作成
        backup_path = csv_path.parent / f"{csv_path.stem}_backup_before_fill_nendai.csv"
        print(f"\n💾 バックアップを作成: {backup_path.name}")
        df_backup = pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
        df_backup.to_csv(backup_path, index=False, encoding="utf-8-sig")

        # 保存
        print(f"💾 変更を保存中: {csv_path.name}")
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")

        print(f"\n✅ 完了！{filled_count}行の年代を埋めました")
    else:
        print("ℹ️ 変更はありません")

    # 最終的な年代分布
    print("\n📊 最終的な年代分布（上位15件）:")
    print(df["年代"].value_counts(dropna=False).head(15).to_string())


if __name__ == "__main__":
    fill_missing_nendai()
