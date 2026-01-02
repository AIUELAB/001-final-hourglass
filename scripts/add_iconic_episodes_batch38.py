#!/usr/bin/env python3
"""
Batch 38: ダンサー・バレエダンサーの象徴エピソード（死去）追加
"""

import csv
import uuid
from datetime import datetime
from pathlib import Path


def generate_episode_id():
    return f"EP-{uuid.uuid4().hex[:8].upper()}"


# ダンサー・バレエダンサーの死去エピソード
ICONIC_EPISODES = [
    {
        "person_id": "P56B3F2E",
        "person_name": "イサドラ・ダンカン",
        "age": 50.0,
        "category": "ダンサー",
        "episode_text": "あなたと同じ50歳のとき、イサドラ・ダンカンは1927年9月14日、フランス・ニースで自動車事故により亡くなりました。コルセットやトウシューズを捨て、素足で踊る「モダンダンスの母」でした。巻いていた長いスカーフが車輪に巻き込まれるという衝撃的な最期を遂げました。「さようなら、友よ。私は栄光に向かう」が最後の言葉だったとされています。",
        "episode_type": "死去",
    },
    {
        "person_id": "PC71A829",
        "person_name": "フレッド・アステア",
        "age": 88.0,
        "category": "ダンサー・俳優",
        "episode_text": "あなたと同じ88歳のとき、フレッド・アステアは1987年6月22日、カリフォルニア州ロサンゼルスで肺炎のため亡くなりました。ハリウッド黄金期を代表するダンサーであり、タップダンスを芸術の域に高めた「ダンスの神様」でした。ジンジャー・ロジャースとのコンビで数々の名作ミュージカル映画を残し、優雅で洗練されたダンスは今も映画史に輝いています。",
        "episode_type": "死去",
    },
    {
        "person_id": "P24B4003",
        "person_name": "ジーン・ケリー",
        "age": 83.0,
        "category": "ダンサー・俳優",
        "episode_text": "あなたと同じ83歳のとき、ジーン・ケリーは1996年2月2日、カリフォルニア州ビバリーヒルズで脳卒中のため亡くなりました。「雨に唄えば」の雨中のダンスシーンで映画史に残る名場面を創造した、アスレチックで力強いダンスの革新者でした。振付師・監督としても活躍し、ミュージカル映画の黄金時代を築きました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P27E9AC6",
        "person_name": "ルドルフ・ヌレエフ",
        "age": 54.0,
        "category": "バレエダンサー",
        "episode_text": "あなたと同じ54歳のとき、ルドルフ・ヌレエフは1993年1月6日、パリでエイズ関連の疾患により亡くなりました。1961年にソ連から亡命し、西側で最も偉大なバレエダンサーの一人となった伝説的存在でした。マーゴ・フォンテインとの伝説的なパートナーシップで世界を魅了。パリ・オペラ座バレエ団の芸術監督も務め、男性バレエの地位を革命的に高めました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P55B45C6",
        "person_name": "マーゴ・フォンテイン",
        "age": 71.0,
        "category": "バレエダンサー",
        "episode_text": "あなたと同じ71歳のとき、マーゴ・フォンテインは1991年2月21日、パナマで癌のため亡くなりました。英国ロイヤル・バレエ団のプリマ・バレリーナとして、20世紀最高のバレリーナの一人と称えられた存在です。ルドルフ・ヌレエフとの年齢差19歳のパートナーシップは、バレエ史上最も伝説的なコンビとして語り継がれています。",
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
