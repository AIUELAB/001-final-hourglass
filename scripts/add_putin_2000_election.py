#!/usr/bin/env python3
"""
プーチン「2000年 大統領初当選」エピソード追加

事実根拠:
- 選挙日: 2000年3月26日
- 得票率: 53.4%（第1回投票で過半数）
- 就任日: 2000年5月7日
- 生年月日: 1952年10月7日 → 選挙時47歳
"""

import csv
import uuid
from datetime import datetime
from pathlib import Path


def generate_episode_id():
    return f"EP-{uuid.uuid4().hex[:8].upper()}"


PUTIN_2000_EPISODE = {
    "person_id": "PA254CB0",
    "person_name": "ウラジーミル・プーチン",
    "age": 47.0,
    "category": "政治・社会",
    "episode_text": (
        "あなたと同じ47歳のとき、ウラジーミル・プーチンは2000年3月26日に行われた"
        "ロシア連邦大統領選挙で初当選を果たしました。得票率53.4%で第1回投票での当選を決め、"
        "同年5月7日に正式に大統領に就任しました。エリツィン前大統領の辞任に伴い"
        "1999年12月から大統領代行を務めていたプーチンは、この選挙で国民からの信任を得て、"
        "ロシアの新たなリーダーとしての地位を確立しました。"
    ),
    "episode_type": "達成",
}


def main():
    csv_path = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        existing = list(reader)
        fieldnames = reader.fieldnames

    print(f"既存エピソード数: {len(existing)}")

    # 重複チェック: 同一人物で同一年齢のエピソードがないか確認
    ep = PUTIN_2000_EPISODE
    duplicates = [
        row
        for row in existing
        if row.get("person_id") == ep["person_id"] and abs(float(row.get("age") or 0) - ep["age"]) < 1
    ]
    if duplicates:
        print("警告: 同一人物・同一年齢のエピソードが既に存在します")
        for dup in duplicates:
            print(f"  - {dup['episode_id']}: {dup['episode_text'][:50]}...")
        print("追加をスキップします。")
        return

    # テンプレート行を取得
    template_row = existing[0].copy()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 新規エピソード作成
    row = template_row.copy()
    row["episode_id"] = generate_episode_id()
    row["person_id"] = ep["person_id"]
    row["person_name"] = ep["person_name"]
    row["age"] = str(ep["age"])
    row["category"] = ep["category"]
    row["char_count"] = str(len(ep["episode_text"]))
    row["episode_text"] = ep["episode_text"]
    row["episode_type"] = ep["episode_type"]
    row["fact_check_result"] = "確認済み"
    row["source"] = "TURNING_POINT_MANUAL"
    row["generation_timestamp"] = timestamp
    row["person_type"] = "REAL"

    print("\n追加するエピソード:")
    print(f"  ID: {row['episode_id']}")
    print(f"  人物: {ep['person_name']} (ID: {ep['person_id']})")
    print(f"  年齢: {ep['age']}歳")
    print(f"  タイプ: {ep['episode_type']}")
    print(f"  本文: {ep['episode_text'][:80]}...")

    all_episodes = existing + [row]

    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_episodes)

    print(f"\n合計: {len(all_episodes)}件 (+1件追加)")
    print("完了: プーチン「2000年 大統領初当選」エピソードを追加しました")


if __name__ == "__main__":
    main()
