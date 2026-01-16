#!/usr/bin/env python3
"""
birth_year / death_year 修正スクリプト

修正内容:
1. birth_year修正（person_nameで検索）
2. death_year削除（存命者）
3. 美空ひばり age=53 を age=52 に修正
"""

import pandas as pd
import shutil
from datetime import datetime
from pathlib import Path
import numpy as np

# パス設定
CSV_PATH = Path("/Users/admin/Documents/AIUELAB/001-final-hourglass/preserved/data/MASTER_EPISODES_CURRENT.csv")
BACKUP_DIR = Path("/Users/admin/Documents/AIUELAB/001-final-hourglass/preserved/data/backups")

def main():
    # バックアップディレクトリ作成
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    # バックアップ作成
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"MASTER_EPISODES_CURRENT_backup_{timestamp}.csv"
    shutil.copy2(CSV_PATH, backup_path)
    print(f"✅ バックアップ作成: {backup_path}")

    # CSV読み込み
    df = pd.read_csv(CSV_PATH, dtype=str)
    original_count = len(df)
    print(f"📊 総レコード数: {original_count}")

    # 修正カウンター
    fixes = {
        "birth_year": 0,
        "death_year": 0,
        "age": 0
    }

    # === 1. birth_year修正 ===
    birth_year_fixes = {
        "エルヴィス・プレスリー": ("1965", "1935"),
        "スタンリー・キューブリック": ("1931", "1928"),
        "大谷翔平": ("1991", "1994"),
        "マイケル・ジャクソン": ("1959", "1958"),
        "ナポレオン・ボナパルト": ("1789", "1769"),
        "ベートーヴェン": ("1771", "1770"),
    }

    print("\n=== birth_year修正 ===")
    for person_name, (old_val, new_val) in birth_year_fixes.items():
        mask = df["person_name"] == person_name
        count = mask.sum()
        if count > 0:
            # 現在値確認
            current_vals = df.loc[mask, "birth_year"].unique()
            print(f"  {person_name}: {count}件 (現在値: {current_vals})")

            # 修正実行
            df.loc[mask, "birth_year"] = new_val
            fixes["birth_year"] += count
            print(f"    → {new_val} に修正")
        else:
            print(f"  ⚠️ {person_name}: 該当なし")

    # === 2. death_year削除（存命者） ===
    death_year_removes = {
        "ダライ・ラマ14世": "2024",
        "ウォーレン・バフェット": "2025",
    }

    print("\n=== death_year削除（存命者） ===")
    for person_name, old_val in death_year_removes.items():
        mask = df["person_name"] == person_name
        count = mask.sum()
        if count > 0:
            # 現在値確認
            current_vals = df.loc[mask, "death_year"].unique()
            print(f"  {person_name}: {count}件 (現在値: {current_vals})")

            # NaNに設定
            df.loc[mask, "death_year"] = ""
            fixes["death_year"] += count
            print(f"    → 空欄(NaN)に修正")
        else:
            print(f"  ⚠️ {person_name}: 該当なし")

    # === 3. 美空ひばり age=53 を age=52 に修正 ===
    print("\n=== 美空ひばり age修正 ===")
    # CSVでは "53.0" として格納されている可能性がある
    mask = (df["person_name"] == "美空ひばり") & (df["age"].isin(["53", "53.0"]))
    count = mask.sum()
    if count > 0:
        print(f"  美空ひばり (age=53): {count}件")
        df.loc[mask, "age"] = "52"
        fixes["age"] += count
        print(f"    → age=52 に修正")
    else:
        print(f"  ⚠️ 美空ひばり (age=53): 該当なし")

    # CSV保存
    df.to_csv(CSV_PATH, index=False)
    print(f"\n✅ CSV保存完了: {CSV_PATH}")

    # 修正サマリー
    print("\n" + "=" * 50)
    print("📋 修正サマリー")
    print("=" * 50)
    print(f"  birth_year修正: {fixes['birth_year']}件")
    print(f"  death_year削除: {fixes['death_year']}件")
    print(f"  age修正: {fixes['age']}件")
    print(f"  合計: {sum(fixes.values())}件")
    print("=" * 50)

if __name__ == "__main__":
    main()
