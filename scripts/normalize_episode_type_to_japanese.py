#!/usr/bin/env python3
"""
エピソードタイプを日本語に統一するスクリプト

英語表記を日本語に変換:
- LEGACY → レガシー
- ACHIEVEMENT → 達成
- TURNING_POINT → 転機
- CHALLENGE → 挑戦
"""

import pandas as pd
from pathlib import Path

# マッピング定義
EPISODE_TYPE_MAPPING = {
    "LEGACY": "レガシー",
    "ACHIEVEMENT": "達成",
    "TURNING_POINT": "転機",
    "CHALLENGE": "挑戦",
}


def normalize_episode_types():
    """episode_typeカラムの英語表記を日本語に統一"""

    # ファイルパス
    csv_path = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")

    if not csv_path.exists():
        print(f"❌ ファイルが見つかりません: {csv_path}")
        return

    # CSVを読み込み
    print(f"📖 CSVを読み込み中: {csv_path}")
    df = pd.read_csv(csv_path, encoding="utf-8-sig")

    print("\n現在のepisode_type分布:")
    print(df["episode_type"].value_counts())

    # 変換前の統計
    total_rows = len(df)
    english_types = df["episode_type"].isin(EPISODE_TYPE_MAPPING.keys())
    affected_count = english_types.sum()

    print(f"\n変換対象: {affected_count} / {total_rows} 行")

    if affected_count == 0:
        print("✅ 変換対象の英語表記はありませんでした")
        return

    # 変換実行
    print("\n🔄 変換を実行中...")
    df["episode_type"] = df["episode_type"].replace(EPISODE_TYPE_MAPPING)

    # 変換後の統計
    print("\n変換後のepisode_type分布:")
    print(df["episode_type"].value_counts())

    # バックアップ作成
    backup_path = csv_path.parent / f"{csv_path.stem}_backup_before_normalize.csv"
    print(f"\n💾 バックアップを作成: {backup_path}")
    df_backup = pd.read_csv(csv_path, encoding="utf-8-sig")
    df_backup.to_csv(backup_path, index=False, encoding="utf-8-sig")

    # 保存
    print(f"💾 変更を保存中: {csv_path}")
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    print(f"\n✅ 完了！{affected_count}行のepisode_typeを日本語に統一しました")

    # 変換内訳を表示
    print("\n📊 変換内訳:")
    for eng, jpn in EPISODE_TYPE_MAPPING.items():
        count = (df_backup["episode_type"] == eng).sum()
        if count > 0:
            print(f"  {eng} → {jpn}: {count}行")


if __name__ == "__main__":
    normalize_episode_types()
