#!/usr/bin/env python3
"""
Batch 26: アナウンサーの象徴エピソード（死去）追加
"""

import csv
import uuid
from datetime import datetime
from pathlib import Path


def generate_episode_id():
    return f"EP-{uuid.uuid4().hex[:8].upper()}"


# アナウンサーの死去エピソード（存命者除外）
ICONIC_EPISODES = [
    {
        "person_id": "PEBDD3B2",
        "person_name": "逸見政孝",
        "age": 48.0,
        "category": "アナウンサー",
        "episode_text": "あなたと同じ48歳のとき、逸見政孝は1993年12月25日、進行胃がんのため東京都内の病院で亡くなりました。フジテレビのアナウンサーとして「夜のヒットスタジオ」などの人気番組を担当し、その後フリーとなり「平成教育委員会」で国民的人気を獲得。がんの闘病を公表し、最後まで仕事への情熱を見せた姿は多くの人々に感動を与えました。クリスマスの日の死去は日本中に悲しみをもたらしました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P32FF357",
        "person_name": "小林麻央",
        "age": 34.0,
        "category": "アナウンサー・キャスター",
        "episode_text": "あなたと同じ34歳のとき、小林麻央は2017年6月22日、乳がんのため東京都内の自宅で亡くなりました。「NEWS ZERO」のキャスターとして活躍し、歌舞伎俳優・市川海老蔵との結婚で注目を集めました。がん闘病中に開設したブログ「KOKORO.」で前向きに生きる姿を発信し続け、多くの人々に勇気を与えました。最後まで家族への愛を貫いた姿は、日本中の心に深く刻まれています。",
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
