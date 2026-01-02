#!/usr/bin/env python3
"""
Batch 31: IT起業家・技術者の象徴エピソード（死去）追加
"""

import csv
import uuid
from datetime import datetime
from pathlib import Path


def generate_episode_id():
    return f"EP-{uuid.uuid4().hex[:8].upper()}"


# IT起業家・技術者の死去エピソード
ICONIC_EPISODES = [
    {
        "person_id": "PD57371B",
        "person_name": "デニス・リッチー",
        "age": 70.0,
        "category": "コンピュータ科学者",
        "episode_text": "あなたと同じ70歳のとき、デニス・リッチーは2011年10月12日、ニュージャージー州の自宅で亡くなりました。C言語の開発者であり、ケン・トンプソンと共にUNIXオペレーティングシステムを創造した「現代コンピューティングの父」でした。C言語は今日のほぼすべてのソフトウェアの基盤となり、UNIXはLinux、macOS、Androidなど現代のOSの祖先となりました。スティーブ・ジョブズと同じ週に亡くなりましたが、彼の功績は人類の技術発展に計り知れない影響を与えています。",
        "episode_type": "死去",
    },
    {
        "person_id": "P7917F29",
        "person_name": "ポール・アレン",
        "age": 65.0,
        "category": "実業家・投資家",
        "episode_text": "あなたと同じ65歳のとき、ポール・アレンは2018年10月15日、非ホジキンリンパ腫の合併症のためシアトルで亡くなりました。ビル・ゲイツと共にマイクロソフトを創業し、パーソナルコンピュータ革命の立役者となった実業家でした。マイクロソフト退社後は投資家・慈善家として活躍し、シアトル・シーホークス（NFL）やポートランド・トレイルブレイザーズ（NBA）のオーナーも務めました。音楽や宇宙開発への情熱も持ち、多彩な分野で功績を残しました。",
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
