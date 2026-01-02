#!/usr/bin/env python3
"""
Batch 42: 革命家・政治指導者の象徴エピソード（死去）追加
"""

import csv
import uuid
from datetime import datetime
from pathlib import Path


def generate_episode_id():
    return f"EP-{uuid.uuid4().hex[:8].upper()}"


# 革命家・政治指導者の死去エピソード
ICONIC_EPISODES = [
    {
        "person_id": "P944DF29",
        "person_name": "ウラジーミル・レーニン",
        "age": 53.0,
        "category": "革命家・政治家",
        "episode_text": "あなたと同じ53歳のとき、ウラジーミル・レーニンは1924年1月21日、モスクワ近郊のゴールキで脳卒中の合併症により亡くなりました。1917年のロシア革命を指導し、世界初の社会主義国家ソビエト連邦を建国した革命家でした。その遺体は今もモスクワの赤の広場に安置されています。マルクス主義を実践に移し、20世紀の世界史を大きく変えた人物です。",
        "episode_type": "死去",
    },
    {
        "person_id": "P3EE76E9",
        "person_name": "フィデル・カストロ",
        "age": 90.0,
        "category": "革命家・政治家",
        "episode_text": "あなたと同じ90歳のとき、フィデル・カストロは2016年11月25日、キューバ・ハバナで亡くなりました。1959年のキューバ革命を成功させ、約50年にわたりキューバを率いた「最高司令官」でした。米国と対立しながらも独自の社会主義路線を貫き、中南米の反米運動の象徴となりました。数百回もの暗殺未遂を生き延びたことでも知られています。",
        "episode_type": "死去",
    },
    {
        "person_id": "P9C55FBE",
        "person_name": "ホー・チ・ミン",
        "age": 79.0,
        "category": "革命家・政治家",
        "episode_text": "あなたと同じ79歳のとき、ホー・チ・ミンは1969年9月2日、ハノイで心臓発作のため亡くなりました。ベトナム独立運動を指導し、フランス・アメリカという大国に抵抗し続けた「ベトナム建国の父」でした。「ホーおじさん」と親しまれ、質素な生活を送りながら国民を導きました。南北統一を見届けることなく亡くなりましたが、その遺志は1975年に実現しました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P7FFB8CA",
        "person_name": "孫文",
        "age": 58.0,
        "category": "革命家・政治家",
        "episode_text": "あなたと同じ58歳のとき、孫文は1925年3月12日、北京で肝臓癌のため亡くなりました。辛亥革命を指導して清朝を倒し、中華民国を建国した「国父」でした。三民主義（民族・民権・民生）を唱え、アジアの民族解放運動に大きな影響を与えました。「革命尚未成功、同志仍須努力（革命いまだ成らず、同志よ努力せよ）」という遺言は今も語り継がれています。",
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
