#!/usr/bin/env python3
"""
Batch 28: 医師・医学者の象徴エピソード（死去）追加
"""

import csv
import uuid
from datetime import datetime
from pathlib import Path


def generate_episode_id():
    return f"EP-{uuid.uuid4().hex[:8].upper()}"


# 医師・医学者の死去エピソード（存命者除外）
ICONIC_EPISODES = [
    {
        "person_id": "P02FA518",
        "person_name": "北里柴三郎",
        "age": 78.0,
        "category": "医学者",
        "episode_text": "あなたと同じ78歳のとき、北里柴三郎は1931年6月13日、脳溢血のため東京の自宅で亡くなりました。破傷風菌の純粋培養に成功し、血清療法を確立した「近代日本医学の父」でした。ペスト菌の発見でも知られ、伝染病研究所（現・東京大学医科学研究所）を設立。慶應義塾大学医学部の創設にも尽力し、日本の医学教育の基盤を築きました。2024年からは新千円札の肖像にも採用されています。",
        "episode_type": "死去",
    },
    {
        "person_id": "PCFA4BEC",
        "person_name": "日野原重明",
        "age": 105.0,
        "category": "医師",
        "episode_text": "あなたと同じ105歳のとき、日野原重明は2017年7月18日、呼吸不全のため東京都内の自宅で亡くなりました。聖路加国際病院名誉院長として生涯現役を貫き、100歳を超えても講演や執筆活動を続けた「生涯現役」の象徴でした。「生活習慣病」という言葉の提唱者としても知られ、予防医学の重要性を広く啓蒙。「いのちの授業」で子どもたちに命の大切さを伝え続けました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P0E83A71",
        "person_name": "カール・ユング",
        "age": 85.0,
        "category": "精神科医・心理学者",
        "episode_text": "あなたと同じ85歳のとき、カール・グスタフ・ユングは1961年6月6日、スイス・チューリッヒ近郊の自宅で亡くなりました。分析心理学の創始者として、集合的無意識、元型、ペルソナなどの概念を提唱し、深層心理学に革命をもたらしました。フロイトとの決別後、独自の理論体系を構築。夢分析や性格類型論は現代の心理学やビジネスにも大きな影響を与え続けています。",
        "episode_type": "死去",
    },
    {
        "person_id": "PC4022E3",
        "person_name": "ジョナス・ソーク",
        "age": 80.0,
        "category": "医学者",
        "episode_text": "あなたと同じ80歳のとき、ジョナス・ソークは1995年6月23日、心不全のためカリフォルニア州ラホヤで亡くなりました。ポリオワクチンを開発し、世界中で恐れられていた小児麻痺の撲滅に貢献した英雄的医学者でした。特許を取得せずワクチンを公開し、「太陽に特許はない」という言葉を残しました。その無私の精神は医学倫理の模範として語り継がれています。",
        "episode_type": "死去",
    },
    {
        "person_id": "P90872B1",
        "person_name": "アルベルト・シュヴァイツァー",
        "age": 90.0,
        "category": "医師・神学者",
        "episode_text": "あなたと同じ90歳のとき、アルベルト・シュヴァイツァーは1965年9月4日、アフリカ・ガボンのランバレネで亡くなりました。「密林の聖者」として知られ、アフリカで医療活動を行いながら「生命への畏敬」の哲学を説きました。オルガン奏者、バッハ研究者としても一流で、1952年にはノーベル平和賞を受賞。多彩な才能を人類への奉仕に捧げた20世紀を代表する人道主義者でした。",
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
