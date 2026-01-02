#!/usr/bin/env python3
"""
Batch 72: 数学者の象徴エピソード（死去）追加
"""

import csv
import uuid
from datetime import datetime
from pathlib import Path


def generate_episode_id():
    return f"EP-{uuid.uuid4().hex[:8].upper()}"


# 数学者の死去エピソード
ICONIC_EPISODES = [
    {
        "person_id": "PAF422C7",
        "person_name": "オイラー",
        "age": 76.0,
        "category": "科学・技術",
        "episode_text": "あなたと同じ76歳のとき、レオンハルト・オイラーは1783年9月18日、サンクトペテルブルクで脳出血のため亡くなりました。「数学の神様」と称され、解析学、数論、グラフ理論など数学のあらゆる分野で膨大な業績を残した数学者でした。晩年は失明しながらも驚異的な暗算能力で研究を続け、死の日の午後まで孫と遊び計算をしていたと伝えられます。",
        "episode_type": "死去",
    },
    {
        "person_id": "P6029CA5",
        "person_name": "リーマン",
        "age": 39.0,
        "category": "科学・技術",
        "episode_text": "あなたと同じ39歳のとき、ベルンハルト・リーマンは1866年7月20日、イタリアのセラスカで結核のため亡くなりました。リーマン幾何学を創始し、アインシュタインの一般相対性理論の数学的基礎を築いた数学者でした。「リーマン予想」は数学史上最も重要な未解決問題の一つとして、150年以上経った今も数学者を魅了し続けています。",
        "episode_type": "死去",
    },
]


def main():
    csv_path = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        existing = list(reader)
        fieldnames = reader.fieldnames

    print(f"既存エピソード数: {len(existing)}")

    template_row = existing[0].copy()
    new_episodes = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for ep in ICONIC_EPISODES:
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
        row["source"] = "ICONIC_MANUAL"
        row["generation_timestamp"] = timestamp
        row["person_type"] = "REAL"
        new_episodes.append(row)
        print(f"  追加: {ep['person_name']} ({ep['age']}歳) - {ep['episode_type']}")

    all_episodes = existing + new_episodes

    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_episodes)

    print(f"\n合計: {len(all_episodes)}件 (+{len(new_episodes)}件追加)")


if __name__ == "__main__":
    main()
