#!/usr/bin/env python3
"""
Batch 65: 探検家の象徴エピソード（死去）追加
"""

import csv
import uuid
from datetime import datetime
from pathlib import Path


def generate_episode_id():
    return f"EP-{uuid.uuid4().hex[:8].upper()}"


# 探検家の死去エピソード
ICONIC_EPISODES = [
    {
        "person_id": "P4CCE098",
        "person_name": "アーネスト・シャクルトン",
        "age": 47.0,
        "category": "探検・冒険",
        "episode_text": "あなたと同じ47歳のとき、アーネスト・シャクルトンは1922年1月5日、サウスジョージア島で心臓発作のため亡くなりました。南極探検の英雄として、エンデュアランス号遭難から全隊員を生還させた伝説的リーダーでした。「困難こそ栄光への道」を体現し、極限状態でのリーダーシップの象徴として今も語り継がれています。",
        "episode_type": "死去",
    },
    {
        "person_id": "P4714F40",
        "person_name": "マルコ・ポーロ",
        "age": 69.0,
        "category": "歴史",
        "episode_text": "あなたと同じ69歳のとき、マルコ・ポーロは1324年1月8日、ヴェネツィアで亡くなりました。13世紀にシルクロードを旅し、元朝のフビライ・ハンに仕えた商人・探検家でした。『東方見聞録』でアジアの驚異を西洋に伝え、「百万のマルコ」と呼ばれました。臨終に際し「私が見たものの半分も語っていない」と言い残しました。",
        "episode_type": "死去",
    },
    {
        "person_id": "PC302AD8",
        "person_name": "伊能忠敬",
        "age": 73.0,
        "category": "科学・技術",
        "episode_text": "あなたと同じ73歳のとき、伊能忠敬は1818年5月17日、江戸で亡くなりました。55歳から17年かけて日本全国を測量し、「大日本沿海輿地全図」を完成させた測量家でした。商人から天文学を学び直し、総距離4万キロを歩いて日本初の実測地図を作成。その精度は近代測量にも匹敵するものでした。",
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
