#!/usr/bin/env python3
"""
MASTER_EPISODES_CURRENT.csvの空episode_idにIDを生成するスクリプト
"""

import csv
import random
import string
import sys

MASTER_CSV = "MASTER_EPISODES_CURRENT.csv"


def generate_episode_id() -> str:
    """エピソードIDを生成

    Returns:
        ユニークなエピソードID（E + 6桁16進数）
    """
    hex_chars = string.hexdigits.upper()[:16]  # 0-9, A-F
    random_hex = "".join(random.choice(hex_chars) for _ in range(6))
    return f"E{random_hex}"


def main():
    print("=" * 80)
    print("Episode ID生成スクリプト")
    print("=" * 80)

    # CSV読み込み
    try:
        with open(MASTER_CSV, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            header = next(reader)
            rows = list(reader)
    except FileNotFoundError:
        print(f"❌ ファイルが見つかりません: {MASTER_CSV}")
        sys.exit(1)

    # episode_idカラムのインデックスを取得
    try:
        episode_id_index = header.index("episode_id")
    except ValueError:
        print("❌ episode_id列が見つかりません")
        sys.exit(1)

    print(f"\n総エピソード数: {len(rows)}件")

    # 既存のepisode_idを収集
    existing_ids = set()
    for row in rows:
        episode_id = row[episode_id_index]
        if episode_id and episode_id.strip():
            existing_ids.add(episode_id)

    print(f"既存episode_id数: {len(existing_ids)}件")

    # 空のepisode_idにIDを生成
    generated_count = 0

    for row in rows:
        episode_id = row[episode_id_index]

        if not episode_id or not episode_id.strip():
            # 新しいIDを生成（重複チェック）
            while True:
                new_id = generate_episode_id()
                if new_id not in existing_ids:
                    break

            row[episode_id_index] = new_id
            existing_ids.add(new_id)
            generated_count += 1

    # CSV書き戻し
    if generated_count > 0:
        with open(MASTER_CSV, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)

        print(f"\n✅ 生成完了: {generated_count}件の新しいepisode_idを生成")
        print(f"✅ 保存完了: {MASTER_CSV}")
    else:
        print("\n⚠️  生成が必要なepisode_idはありません")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
