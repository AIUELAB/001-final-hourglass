#!/usr/bin/env python3
"""
Batch 60: 日本の思想家・哲学者の象徴エピソード（死去）追加
"""

import csv
import uuid
from datetime import datetime
from pathlib import Path


def generate_episode_id():
    return f"EP-{uuid.uuid4().hex[:8].upper()}"


# 日本の思想家・哲学者の死去エピソード
ICONIC_EPISODES = [
    {
        "person_id": "PAD83A47",
        "person_name": "中江兆民",
        "age": 54.0,
        "category": "歴史",
        "episode_text": "あなたと同じ54歳のとき、中江兆民は1901年12月13日、大阪で喉頭がんのため亡くなりました。ルソーの『社会契約論』を翻訳し「東洋のルソー」と呼ばれた自由民権運動の理論的指導者でした。余命1年半と宣告されてから『一年有半』を執筆し、死を見つめながら思索を続けた思想家でした。",
        "episode_type": "死去",
    },
    {
        "person_id": "P43F9981",
        "person_name": "新渡戸稲造",
        "age": 71.0,
        "category": "歴史",
        "episode_text": "あなたと同じ71歳のとき、新渡戸稲造は1933年10月15日、カナダのビクトリアで肺炎のため亡くなりました。『武士道』を英語で著し、日本人の精神を世界に伝えた国際人でした。国際連盟事務次長として平和に尽力し、「太平洋の架け橋」になることを生涯の使命としました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P9474218",
        "person_name": "内村鑑三",
        "age": 69.0,
        "category": "思想・哲学",
        "episode_text": "あなたと同じ69歳のとき、内村鑑三は1930年3月28日、東京で心臓病のため亡くなりました。無教会主義を唱え、日本的キリスト教を追求した思想家でした。教育勅語への敬礼を拒否した「不敬事件」で教職を追われながらも、「二つのJ（JesusとJapan）」への愛を貫きました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P85620CD",
        "person_name": "岡倉天心",
        "age": 50.0,
        "category": "芸術・文化",
        "episode_text": "あなたと同じ50歳のとき、岡倉天心は1913年9月2日、新潟で心臓病のため亡くなりました。『茶の本』『東洋の理想』を英語で著し、日本美術を世界に紹介した思想家でした。「アジアは一つ」と唱え、ボストン美術館で東洋美術部門を指導しながら日本文化の真髄を伝えました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P6CD8311",
        "person_name": "和辻哲郎",
        "age": 71.0,
        "category": "哲学者",
        "episode_text": "あなたと同じ71歳のとき、和辻哲郎は1960年12月26日、東京で心筋梗塞のため亡くなりました。『風土』『倫理学』で日本の風土と文化を哲学的に考察した思想家でした。「間柄」の概念で人間存在を捉え、日本独自の倫理学を構築しました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P0BE5FCE",
        "person_name": "小林秀雄",
        "age": 80.0,
        "category": "文学",
        "episode_text": "あなたと同じ80歳のとき、小林秀雄は1983年3月1日、東京で腎不全のため亡くなりました。『様々なる意匠』で近代日本文芸批評を確立し、「批評の神様」と呼ばれた評論家でした。本居宣長に傾倒し、晩年は『本居宣長』の執筆に11年を費やしました。",
        "episode_type": "死去",
    },
    {
        "person_id": "PF56B983",
        "person_name": "アルフレッド・アドラー",
        "age": 67.0,
        "category": "学術・研究",
        "episode_text": "あなたと同じ67歳のとき、アルフレッド・アドラーは1937年5月28日、スコットランドのアバディーンで心臓発作のため亡くなりました。「個人心理学」を創始し、劣等感の克服と共同体感覚を説いた心理学者でした。フロイト、ユングと並ぶ三大心理学者として、現代の自己啓発に大きな影響を与えています。",
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
