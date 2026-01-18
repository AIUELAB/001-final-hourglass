#!/usr/bin/env python3
"""slot再配分スクリプト（クォンタイル方式）

slot 60に46%が集中している問題を解決するため、
年齢をクォンタイル（分位数）で60分割し、各slotに均等配分する。
"""

import pandas as pd
from pathlib import Path


def main():
    csv_path = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")

    print("=== slot再配分（クォンタイル方式） ===")

    # 読み込み
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    print(f"読み込み: {len(df)}件")

    # 変更前の分布
    print("\n[変更前slot分布]")
    before_dist = df["slot"].value_counts().sort_index()
    print(f"使用slot数: {len(before_dist)}")
    print(f"最大: slot {before_dist.idxmax()} = {before_dist.max()}件")
    print(f"最小: slot {before_dist.idxmin()} = {before_dist.min()}件")
    print(f"偏り倍率: {before_dist.max() / before_dist.min():.2f}倍")

    # クォンタイルベースでslot再配分
    # qcut: 件数が均等になるように分割
    # duplicates='drop': 同じ年齢が多い場合に対応
    try:
        df["slot"] = pd.qcut(df["age"], q=60, labels=False, duplicates="drop") + 1
    except ValueError as e:
        print(f"警告: qcutでエラー ({e})")
        print("代替方式: 年齢を直接slotにマッピング")
        # 年齢の最小値と最大値を取得し、60分割
        age_min, age_max = df["age"].min(), df["age"].max()
        df["slot"] = ((df["age"] - age_min) / (age_max - age_min) * 59).round().astype(int) + 1

    df["slot"] = df["slot"].astype(int)

    # 変更後の分布
    print("\n[変更後slot分布]")
    after_dist = df["slot"].value_counts().sort_index()
    print(f"使用slot数: {len(after_dist)}")
    print(f"最大: slot {after_dist.idxmax()} = {after_dist.max()}件")
    print(f"最小: slot {after_dist.idxmin()} = {after_dist.min()}件")
    print(f"偏り倍率: {after_dist.max() / after_dist.min():.2f}倍")

    # 改善度
    before_ratio = before_dist.max() / before_dist.min()
    after_ratio = after_dist.max() / after_dist.min()
    print(f"\n改善: {before_ratio:.2f}倍 → {after_ratio:.2f}倍 ({(1 - after_ratio/before_ratio)*100:.1f}%改善)")

    # 保存
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"\n保存完了: {csv_path}")


if __name__ == "__main__":
    main()
