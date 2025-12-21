#!/usr/bin/env python3
"""
slot欠損値修正スクリプト

1,168件のslot欠損値をslot 13-365にバランスよく割り当てる
"""

from pathlib import Path

import numpy as np
import pandas as pd

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent
CSV_PATH = PROJECT_ROOT / "MASTER_EPISODES_CURRENT.csv"
BACKUP_PATH = PROJECT_ROOT / "MASTER_EPISODES_CURRENT_backup_before_slot_fix.csv"


def fix_slot_missing_values():
    """slot欠損値を修正"""

    print("📋 CSVファイル読み込み中...")
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")

    # バックアップ作成
    print(f"💾 バックアップ作成: {BACKUP_PATH}")
    df.to_csv(BACKUP_PATH, index=False, encoding="utf-8-sig")

    # 欠損値の確認
    missing_count = df["slot"].isna().sum()
    print("\n📊 修正前の状況:")
    print(f"  - 総行数: {len(df)}")
    print(f"  - slot欠損: {missing_count}件 ({missing_count / len(df) * 100:.2f}%)")
    print(f"  - slot範囲: {df['slot'].min():.0f} - {df['slot'].max():.0f}")

    if missing_count == 0:
        print("\n✅ slot欠損値はありません")
        return

    # 欠損値のインデックスを取得
    missing_indices = df[df["slot"].isna()].index.tolist()

    # slot 13-365の範囲にランダムに割り当て
    # より均等な分布を目指す
    available_slots = list(range(13, 366))  # slot 13-365

    # 各slotに均等に割り当てるための配列を作成
    # 1,168件を353スロットに分散: 各スロット約3.3件
    slots_to_assign = []
    per_slot = missing_count // len(available_slots)  # 基本割り当て数
    remainder = missing_count % len(available_slots)  # 余り

    for i, slot_num in enumerate(available_slots):
        # 余りを最初のスロットに1件ずつ追加
        count = per_slot + (1 if i < remainder else 0)
        slots_to_assign.extend([slot_num] * count)

    # シャッフルしてランダム性を確保
    np.random.seed(42)  # 再現性のため
    np.random.shuffle(slots_to_assign)

    # 欠損値に割り当て
    print("\n🔄 slot欠損値を修正中...")
    for idx, slot_value in zip(missing_indices, slots_to_assign):
        df.at[idx, "slot"] = slot_value

    # 修正後の確認
    missing_after = df["slot"].isna().sum()
    print("\n📊 修正後の状況:")
    print(f"  - slot欠損: {missing_after}件 ({missing_after / len(df) * 100:.2f}%)")
    print(f"  - slot範囲: {df['slot'].min():.0f} - {df['slot'].max():.0f}")
    print(f"  - ユニークなslot数: {df['slot'].nunique()}")

    # slot分布の確認
    print("\n📈 slot分布:")
    slot_distribution = df["slot"].value_counts().sort_index()
    print(f"  - 最小エピソード数/slot: {slot_distribution.min()}")
    print(f"  - 最大エピソード数/slot: {slot_distribution.max()}")
    print(f"  - 平均エピソード数/slot: {slot_distribution.mean():.2f}")

    # 新しいslot範囲（13-365）の統計
    new_slots = df[df["slot"] >= 13]["slot"]
    if len(new_slots) > 0:
        print("\n📊 新規割り当てslot（13-365）:")
        print(f"  - エピソード数: {len(new_slots)}")
        new_slot_dist = new_slots.value_counts()
        print(f"  - 最小: {new_slot_dist.min()}件/slot")
        print(f"  - 最大: {new_slot_dist.max()}件/slot")
        print(f"  - 平均: {new_slot_dist.mean():.2f}件/slot")

    # CSVを保存
    print(f"\n💾 CSVファイル保存中: {CSV_PATH}")
    df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")

    print("\n✅ slot欠損値の修正が完了しました！")
    print(f"   修正件数: {missing_count}件")
    print(f"   バックアップ: {BACKUP_PATH}")


if __name__ == "__main__":
    fix_slot_missing_values()
