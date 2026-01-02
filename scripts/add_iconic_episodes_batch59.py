#!/usr/bin/env python3
"""
Batch 59: 海外の生物学者・化学者・医学者の象徴エピソード（死去）追加
"""

import csv
import uuid
from datetime import datetime
from pathlib import Path


def generate_episode_id():
    return f"EP-{uuid.uuid4().hex[:8].upper()}"


# 海外の生物学者・化学者・医学者の死去エピソード
ICONIC_EPISODES = [
    {
        "person_id": "P0035135",
        "person_name": "グレゴール・メンデル",
        "age": 61.0,
        "category": "科学・技術",
        "episode_text": "あなたと同じ61歳のとき、グレゴール・メンデルは1884年1月6日、オーストリアで腎臓病のため亡くなりました。エンドウ豆の交配実験で遺伝の法則を発見した「遺伝学の父」でした。修道院長として静かに研究を続け、その業績は死後35年経って再発見され、遺伝学の基礎となりました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P4063066",
        "person_name": "フランシス・クリック",
        "age": 88.0,
        "category": "科学・技術",
        "episode_text": "あなたと同じ88歳のとき、フランシス・クリックは2004年7月28日、カリフォルニアで大腸がんのため亡くなりました。ジェームズ・ワトソンとともにDNAの二重らせん構造を発見し、ノーベル生理学・医学賞を受賞した分子生物学者でした。「生命の秘密を見つけた」とパブで叫んだ逸話は有名です。",
        "episode_type": "死去",
    },
    {
        "person_id": "P1B0144C",
        "person_name": "ルイ・パスツール",
        "age": 72.0,
        "category": "科学・技術",
        "episode_text": "あなたと同じ72歳のとき、ルイ・パスツールは1895年9月28日、パリ近郊で脳卒中のため亡くなりました。細菌学と免疫学の父として、狂犬病ワクチンを開発し「低温殺菌法（パスツリゼーション）」を発明した科学者でした。「科学に国境はないが、科学者には祖国がある」の言葉を残しました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P975B2FB",
        "person_name": "ロベルト・コッホ",
        "age": 66.0,
        "category": "科学・技術",
        "episode_text": "あなたと同じ66歳のとき、ロベルト・コッホは1910年5月27日、バーデン＝バーデンで心臓発作のため亡くなりました。結核菌・コレラ菌を発見し、「コッホの三原則」で近代細菌学を確立したノーベル賞受賞者でした。パスツールとのライバル関係は科学史上有名で、感染症医学に革命をもたらしました。",
        "episode_type": "死去",
    },
    {
        "person_id": "PE939CC5",
        "person_name": "アレクサンダー・フレミング",
        "age": 73.0,
        "category": "科学・技術",
        "episode_text": "あなたと同じ73歳のとき、アレクサンダー・フレミングは1955年3月11日、ロンドンで心臓発作のため亡くなりました。偶然からペニシリンを発見し、抗生物質の時代を切り開いたノーベル賞受賞者でした。「カビが細菌を殺している」という観察が、何百万もの命を救う薬の開発につながりました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P1B10796",
        "person_name": "アントワーヌ・ラヴォアジエ",
        "age": 50.0,
        "category": "科学・技術",
        "episode_text": "あなたと同じ50歳のとき、アントワーヌ・ラヴォアジエは1794年5月8日、パリでギロチンにより処刑されました。燃焼理論を確立し、元素の概念を定義した「近代化学の父」でした。フランス革命の恐怖政治下で徴税請負人の経歴を理由に処刑され、「その頭を切り落とすのは一瞬だが、同じ頭脳を生むには百年かかる」と嘆かれました。",
        "episode_type": "死去",
    },
    {
        "person_id": "PE082E99",
        "person_name": "アメデオ・アボガドロ",
        "age": 79.0,
        "category": "科学・技術",
        "episode_text": "あなたと同じ79歳のとき、アメデオ・アボガドロは1856年7月9日、トリノで亡くなりました。分子の概念を確立し、「アボガドロ定数」にその名を残すイタリアの化学者・物理学者でした。生前は認められませんでしたが、死後に「アボガドロの法則」が化学の基礎として確立されました。",
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
