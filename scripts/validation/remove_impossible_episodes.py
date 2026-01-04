#!/usr/bin/env python3
"""死亡年齢を超えた不可能なエピソードを削除するスクリプト

対象:
- EP-2512181850581845: 手塚治虫 61歳（60歳で死亡）→ 60歳に修正
- EP-000001746: 夏目漱石 54歳（49歳で死亡）→ 削除（本文が「存在していませんでした」）
- EP-2512181850581763: 坂本龍馬 64歳（33歳で死亡）→ 削除（本文が「史実に基づいて記述できない」）
- EP-000001293: 坂本龍馬 67歳（33歳で死亡）→ 削除（本文が「もし生きていたら」）
"""

import csv
from datetime import datetime
from pathlib import Path

MASTER_CSV = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")

# 削除対象（本文自体が不可能性を認めている）
DELETE_EPISODES = {
    "EP-000001746",  # 夏目漱石 54歳
    "EP-2512181850581763",  # 坂本龍馬 64歳
    "EP-000001293",  # 坂本龍馬 67歳
}

# 年齢修正対象
FIX_AGE_EPISODES = {
    "EP-2512181850581845": {
        "new_age": 60,
        "reason": "手塚治虫は60歳で死亡。本文の内容は60歳の出来事として適切",
    },
}


def process_episodes():
    """エピソードを処理（削除または修正）"""
    rows = []
    deleted = []
    fixed = []

    with open(MASTER_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames

        for row in reader:
            ep_id = row["episode_id"]

            # 削除対象
            if ep_id in DELETE_EPISODES:
                deleted.append(
                    {
                        "episode_id": ep_id,
                        "person_name": row["person_name"],
                        "age": row["age"],
                        "text_preview": row["episode_text"][:80],
                    }
                )
                continue  # スキップ（削除）

            # 年齢修正対象
            if ep_id in FIX_AGE_EPISODES:
                old_age = row["age"]
                fix_info = FIX_AGE_EPISODES[ep_id]
                row["age"] = str(float(fix_info["new_age"]))
                row["last_modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                fixed.append(
                    {
                        "episode_id": ep_id,
                        "person_name": row["person_name"],
                        "old_age": old_age,
                        "new_age": fix_info["new_age"],
                        "reason": fix_info["reason"],
                    }
                )

            rows.append(row)

    # 書き込み
    with open(MASTER_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return deleted, fixed


def main():
    print("=" * 60)
    print("不可能なエピソードの削除・修正")
    print("=" * 60)

    deleted, fixed = process_episodes()

    print(f"\n削除: {len(deleted)}件")
    for item in deleted:
        print(f"  ❌ {item['episode_id']}: {item['person_name']} ({item['age']}歳)")
        print(f"     {item['text_preview']}...")

    print(f"\n年齢修正: {len(fixed)}件")
    for item in fixed:
        print(f"  ✏️ {item['episode_id']}: {item['person_name']} {item['old_age']}歳 → {item['new_age']}歳")
        print(f"     理由: {item['reason']}")

    print("\n✅ 処理完了")


if __name__ == "__main__":
    main()
