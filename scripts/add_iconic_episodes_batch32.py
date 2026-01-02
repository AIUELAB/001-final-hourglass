#!/usr/bin/env python3
"""
Batch 32: 教育者・大学教授の象徴エピソード（死去）追加
"""

import csv
import uuid
from datetime import datetime
from pathlib import Path


def generate_episode_id():
    return f"EP-{uuid.uuid4().hex[:8].upper()}"


# 教育者・大学教授の死去エピソード
ICONIC_EPISODES = [
    {
        "person_id": "PBB9C4C1",
        "person_name": "津田梅子",
        "age": 64.0,
        "category": "教育者",
        "episode_text": "あなたと同じ64歳のとき、津田梅子は1929年8月16日、神奈川県鎌倉で脳出血のため亡くなりました。日本初の女子留学生として6歳で渡米し、帰国後は女子英学塾（現・津田塾大学）を創設した女子教育の先駆者でした。「女性にも高等教育を」という信念のもと、多くの女性リーダーを育成。2024年からは新五千円札の肖像に採用され、その功績が改めて評価されています。",
        "episode_type": "死去",
    },
    {
        "person_id": "P4E95933",
        "person_name": "大隈重信",
        "age": 83.0,
        "category": "政治家・教育者",
        "episode_text": "あなたと同じ83歳のとき、大隈重信は1922年1月10日、東京の自邸で亡くなりました。早稲田大学の創設者として日本の高等教育の発展に貢献し、二度の内閣総理大臣を務めた明治・大正期の巨人でした。「在野精神」「学問の独立」を掲げ、政府に依存しない私学の理念を確立。国民葬が執り行われ、日比谷公園には30万人が参列したと伝えられています。",
        "episode_type": "死去",
    },
    {
        "person_id": "P0BE5FCE",
        "person_name": "小林秀雄",
        "age": 80.0,
        "category": "文芸評論家",
        "episode_text": "あなたと同じ80歳のとき、小林秀雄は1983年3月1日、東京都内の病院で腎不全のため亡くなりました。「様々なる意匠」で文壇に登場し、近代日本の文芸批評を確立した「批評の神様」でした。ドストエフスキー、モーツァルト、本居宣長など幅広い対象を論じ、文学と思想の橋渡しを行いました。講演や対談でも名声を博し、日本の知識人に多大な影響を与え続けています。",
        "episode_type": "死去",
    },
    {
        "person_id": "PECB5C9D",
        "person_name": "河合隼雄",
        "age": 79.0,
        "category": "心理学者",
        "episode_text": "あなたと同じ79歳のとき、河合隼雄は2007年7月19日、脳梗塞のため兵庫県内の病院で亡くなりました。日本にユング心理学を紹介し、箱庭療法を広めた臨床心理学の第一人者でした。文化庁長官も務め、日本人の心の問題について広く発信。「ふたつよいことさてないものよ」など、難解な心理学を分かりやすく語る名言を多く残しました。",
        "episode_type": "死去",
    },
    {
        "person_id": "PC3663D2",
        "person_name": "加藤周一",
        "age": 89.0,
        "category": "評論家・作家",
        "episode_text": "あなたと同じ89歳のとき、加藤周一は2008年12月5日、東京都内の病院で亡くなりました。「日本文学史序説」「羊の歌」など多数の著作で知られる戦後日本を代表する知識人でした。医師でありながら文学・芸術・政治と幅広い分野で発言し、九条の会の呼びかけ人として平和運動にも尽力。ヨーロッパ的教養と日本文化への深い洞察を兼ね備えた稀有な存在でした。",
        "episode_type": "死去",
    },
    {
        "person_id": "P6AAC19F",
        "person_name": "マリア・モンテッソーリ",
        "age": 81.0,
        "category": "教育者・医師",
        "episode_text": "あなたと同じ81歳のとき、マリア・モンテッソーリは1952年5月6日、オランダ・ノールトウェイクで亡くなりました。イタリア初の女性医師の一人であり、「モンテッソーリ教育」を創始した教育改革者でした。子どもの自主性を尊重し、発達段階に応じた教育環境を整える方法論は世界中に広まり、今日でも多くの幼稚園・学校で実践されています。",
        "episode_type": "死去",
    },
    {
        "person_id": "PE150E53",
        "person_name": "ジョン・デューイ",
        "age": 92.0,
        "category": "哲学者・教育学者",
        "episode_text": "あなたと同じ92歳のとき、ジョン・デューイは1952年6月1日、ニューヨークで肺炎のため亡くなりました。プラグマティズム哲学の代表者として、「学ぶことは行うことである」という経験主義的教育理論を確立しました。「民主主義と教育」は教育学の古典として読み継がれ、進歩主義教育運動に多大な影響を与えました。20世紀アメリカを代表する思想家として、今も世界の教育に影響を与え続けています。",
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
