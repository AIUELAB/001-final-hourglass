#!/usr/bin/env python3
"""
生成されたエピソードをマスターCSVに統合するスクリプト

使用方法:
    python3 scripts/integrate_generated_episodes.py \
        --input generated/phase8_teen_episodes_all.csv \
        --dry-run  # 実際に統合せずに確認のみ

    python3 scripts/integrate_generated_episodes.py \
        --input generated/phase8_teen_episodes_all.csv  # 実際に統合
"""

import argparse
import hashlib
import shutil
from datetime import datetime

import pandas as pd


def generate_episode_id(person_name: str, age: int, episode_text: str) -> str:
    """エピソードIDを生成"""
    content = f"{person_name}_{age}_{episode_text[:50]}"
    hash_obj = hashlib.md5(content.encode("utf-8"), usedforsecurity=False)
    hash_hex = hash_obj.hexdigest()[:8].upper()
    return f"E{hash_hex}"


def main():
    parser = argparse.ArgumentParser(description="生成されたエピソードをマスターCSVに統合")
    parser.add_argument("--input", required=True, help="入力CSVファイルパス")
    parser.add_argument(
        "--master",
        default="preserved/data/MASTER_EPISODES_CURRENT.csv",
        help="マスターCSVファイルパス",
    )
    parser.add_argument("--dry-run", action="store_true", help="実際に統合せずに確認のみ")

    args = parser.parse_args()

    print("=" * 70)
    print("📦 エピソード統合スクリプト")
    print("=" * 70)
    print(f"入力ファイル: {args.input}")
    print(f"マスターファイル: {args.master}")
    print(f"ドライラン: {'はい' if args.dry_run else 'いいえ'}")
    print("=" * 70)

    # 入力CSVを読み込み
    try:
        new_df = pd.read_csv(args.input)
        print(f"\n📥 入力ファイル読み込み: {len(new_df)}件")
    except FileNotFoundError:
        print(f"❌ 入力ファイルが見つかりません: {args.input}")
        return

    # マスターCSVを読み込み
    try:
        master_df = pd.read_csv(args.master)
        print(f"📂 マスターファイル読み込み: {len(master_df)}件")
    except FileNotFoundError:
        print(f"❌ マスターファイルが見つかりません: {args.master}")
        return

    # 既存のperson_name + ageの組み合わせを確認
    master_keys = set(zip(master_df["person_name"], master_df["age"]))
    print(f"📊 既存の組み合わせ: {len(master_keys)}件")

    # 重複チェック
    new_episodes = []
    duplicates = []
    for _, row in new_df.iterrows():
        key = (row["person_name"], row["age"])
        if key in master_keys:
            duplicates.append(row["person_name"])
        else:
            new_episodes.append(row)

    print("\n📊 統合対象:")
    print(f"  新規追加: {len(new_episodes)}件")
    print(f"  重複（スキップ）: {len(duplicates)}件")

    if duplicates:
        print("\n⚠️ 重複した人物（スキップ）:")
        for name in duplicates[:10]:
            print(f"  - {name}")
        if len(duplicates) > 10:
            print(f"  ... 他{len(duplicates) - 10}件")

    if not new_episodes:
        print("\n⚠️ 追加するエピソードがありません")
        return

    # 新規エピソードにepisode_idを付与
    new_episodes_df = pd.DataFrame(new_episodes)
    for idx in new_episodes_df.index:
        row = new_episodes_df.loc[idx]
        episode_id = generate_episode_id(row["person_name"], row["age"], row["episode_text"])
        new_episodes_df.loc[idx, "episode_id"] = episode_id

    # 統合前のサンプル表示
    print("\n📝 追加するエピソードのサンプル:")
    sample_df = new_episodes_df.head(5)
    for _, row in sample_df.iterrows():
        print(f"  - {row['person_name']} ({row['age']}歳): {row['episode_text'][:50]}...")

    if args.dry_run:
        print("\n🔍 ドライラン完了（実際の統合は行いません）")
        print(f"   統合実行時: {len(master_df)}件 → {len(master_df) + len(new_episodes)}件")
        return

    # バックアップ作成
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = args.master.replace(".csv", f"_backup_before_integrate_{timestamp}.csv")
    shutil.copy(args.master, backup_path)
    print(f"\n💾 バックアップ作成: {backup_path}")

    # 統合
    combined_df = pd.concat([master_df, new_episodes_df], ignore_index=True)
    combined_df.to_csv(args.master, index=False, encoding="utf-8-sig")

    print("\n✅ 統合完了:")
    print(f"   統合前: {len(master_df)}件")
    print(f"   追加: {len(new_episodes)}件")
    print(f"   統合後: {len(combined_df)}件")

    # 年代分布の確認
    print("\n📊 統合後の年代分布:")
    nendai_counts = combined_df["年代"].value_counts().sort_index()
    for nendai, count in nendai_counts.items():
        pct = count / len(combined_df) * 100
        print(f"  {nendai}: {count}件 ({pct:.1f}%)")

    print("\n" + "=" * 70)
    print("完了")
    print("=" * 70)


if __name__ == "__main__":
    main()
