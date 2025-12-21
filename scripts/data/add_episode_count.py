#!/usr/bin/env python3
"""
エピソード数カウント機能
各人物のエピソード数をカラムとして追加
"""

import hashlib
from datetime import datetime
from pathlib import Path

import pandas as pd


def generate_person_id(row: pd.Series) -> str:
    """人物名+識別情報からユニークIDを生成（同姓同名対応）"""
    person_name = str(row.get("person_name", ""))

    # work_titleがあれば使用、なければcategoryを使用
    work_title = str(row.get("work_title", "")) if pd.notna(row.get("work_title")) else ""
    category = str(row.get("category", "")) if pd.notna(row.get("category")) else ""

    # 識別子を決定（架空キャラはwork_title、実在人物はcategory）
    identifier = work_title if work_title and work_title != "nan" else category

    # 組み合わせでハッシュ生成
    combined = f"{person_name}:{identifier}"
    return "P" + hashlib.md5(combined.encode(), usedforsecurity=False).hexdigest()[:7].upper()


def add_episode_count(input_csv: str = None, output_csv: str = None):
    """エピソード数カラムを追加"""

    # 最新CSVを自動検出
    if input_csv is None:
        csv_files = list(Path(".").glob("MASTER_EPISODES*.csv"))
        if not csv_files:
            raise FileNotFoundError("MASTER_EPISODES*.csv が見つかりません")
        input_csv = str(max(csv_files, key=lambda f: f.stat().st_mtime))

    print(f"📂 読み込み: {input_csv}")
    df = pd.read_csv(input_csv, encoding="utf-8-sig")
    print(f"📊 総エピソード数: {len(df)}")

    # 既存のperson_id, episode_countカラムを削除（再生成するため）
    for col in ["person_id", "episode_count"]:
        if col in df.columns:
            df = df.drop(columns=[col])

    # person_idを生成（同姓同名対応）
    df["person_id"] = df.apply(generate_person_id, axis=1)

    # 各人物のエピソード数をカウント（person_idベース）
    episode_counts = df.groupby("person_id").size().reset_index(name="episode_count")

    # マージ
    df = df.merge(episode_counts, on="person_id", how="left")

    # 統計表示
    print("\n📈 統計:")
    print(f"  ユニーク人物数（名前）: {df['person_name'].nunique()}")
    print(f"  ユニーク人物数（ID）: {df['person_id'].nunique()}")
    print(f"  総エピソード数: {len(df)}")

    # 同姓同名検出
    same_name_diff_id = df.groupby("person_name")["person_id"].nunique()
    same_name_cases = same_name_diff_id[same_name_diff_id > 1]
    if len(same_name_cases) > 0:
        print(f"\n⚠️ 同姓同名別人物検出: {len(same_name_cases)}組")
        for name in same_name_cases.head(5).index:
            ids = df[df["person_name"] == name]["person_id"].unique()
            print(f"  {name}: {len(ids)}人")

    # エピソード数分布
    count_dist = df.drop_duplicates("person_id").groupby("episode_count").size()
    print("\n📊 エピソード数分布:")
    for count, num_people in count_dist.items():
        print(f"  {count}エピソード: {num_people}人")

    # 複数エピソード持ちの人物
    multi_ep = df[df["episode_count"] > 1].drop_duplicates("person_id")
    if len(multi_ep) > 0:
        print("\n👥 複数エピソード持ち（上位10名）:")
        top10 = multi_ep.nlargest(10, "episode_count")[["person_name", "person_id", "episode_count"]]
        for _, row in top10.iterrows():
            print(f"  {row['person_name']} ({row['person_id']}): {row['episode_count']}件")

    # 出力
    if output_csv is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_csv = f"MASTER_EPISODES_WITH_COUNT_{timestamp}.csv"

    # カラム順序を整理
    cols = ["person_id", "person_name", "episode_count"] + [
        c for c in df.columns if c not in ["person_id", "person_name", "episode_count"]
    ]
    df = df[cols]

    df.to_csv(output_csv, index=False, encoding="utf-8-sig")
    print(f"\n✅ 保存完了: {output_csv}")

    return df


def main():
    import sys

    print("=" * 50)
    print("🔢 エピソード数カウント追加")
    print("=" * 50)

    input_csv = sys.argv[1] if len(sys.argv) > 1 else "MASTER_EPISODES_AWARDS_20251119_125954.csv"
    df = add_episode_count(input_csv=input_csv)

    print("\n🎉 完了!")


if __name__ == "__main__":
    main()
