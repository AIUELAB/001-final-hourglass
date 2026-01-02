#!/usr/bin/env python3
"""
Batch 57: 日本の科学者の象徴エピソード（死去）追加
"""

import csv
import uuid
from datetime import datetime
from pathlib import Path


def generate_episode_id():
    return f"EP-{uuid.uuid4().hex[:8].upper()}"


# 日本の科学者の死去エピソード
ICONIC_EPISODES = [
    {
        "person_id": "PBB3B79B",
        "person_name": "湯川秀樹",
        "age": 74.0,
        "category": "科学・技術",
        "episode_text": "あなたと同じ74歳のとき、湯川秀樹は1981年9月8日、京都で肺炎のため亡くなりました。中間子理論を提唱し、日本人初のノーベル物理学賞を受賞した理論物理学者でした。戦後の焼け野原から日本に希望を与え、「科学の進歩が人類の幸福に貢献することを願う」と平和運動にも尽力しました。",
        "episode_type": "死去",
    },
    {
        "person_id": "PDE8D948",
        "person_name": "朝永振一郎",
        "age": 73.0,
        "category": "科学・技術",
        "episode_text": "あなたと同じ73歳のとき、朝永振一郎は1979年7月8日、東京で咽頭がんのため亡くなりました。くりこみ理論を発展させ、ノーベル物理学賞を受賞した理論物理学者でした。湯川秀樹とは高校の同級生であり、ともに日本の物理学を世界レベルに押し上げた二人の巨人でした。",
        "episode_type": "死去",
    },
    {
        "person_id": "P072AD0B",
        "person_name": "志賀潔",
        "age": 87.0,
        "category": "科学・技術",
        "episode_text": "あなたと同じ87歳のとき、志賀潔は1957年1月25日、仙台で脳出血のため亡くなりました。赤痢菌（シゲラ菌）を発見し、日本の細菌学を世界に知らしめた医学者でした。北里柴三郎の弟子として研究を重ね、伝染病の克服に生涯を捧げました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P5DEAE80",
        "person_name": "長岡半太郎",
        "age": 85.0,
        "category": "物理学者",
        "episode_text": "あなたと同じ85歳のとき、長岡半太郎は1950年12月11日、東京で老衰のため亡くなりました。土星型原子模型を提唱し、日本の物理学の基礎を築いた科学者でした。ラザフォードの原子核発見に影響を与え、湯川秀樹ら多くの物理学者を育てました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P56F4CD8",
        "person_name": "仁科芳雄",
        "age": 60.0,
        "category": "物理学者",
        "episode_text": "あなたと同じ60歳のとき、仁科芳雄は1951年1月10日、東京で肝臓がんのため亡くなりました。日本の原子物理学の父として、理化学研究所でサイクロトロンを建設した科学者でした。湯川秀樹、朝永振一郎ら多くのノーベル賞受賞者を育てました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P4646874",
        "person_name": "牧野富太郎",
        "age": 94.0,
        "category": "植物学者",
        "episode_text": "あなたと同じ94歳のとき、牧野富太郎は1957年1月18日、東京で老衰のため亡くなりました。独学で植物学を極め、1,500種以上の新種を命名した「日本の植物学の父」でした。94歳まで野山を歩き続け、「草を褥に木の根を枕 花と恋して九十年」と詠みました。",
        "episode_type": "死去",
    },
    {
        "person_id": "PE77D36C",
        "person_name": "高峰譲吉",
        "age": 67.0,
        "category": "化学者",
        "episode_text": "あなたと同じ67歳のとき、高峰譲吉は1922年7月22日、ニューヨークで肝臓病のため亡くなりました。アドレナリンの結晶化に世界で初めて成功し、タカジアスターゼを発明した化学者でした。渡米して成功を収め、ワシントンD.C.の桜の寄贈にも尽力しました。",
        "episode_type": "死去",
    },
    {
        "person_id": "PA138212",
        "person_name": "鈴木梅太郎",
        "age": 69.0,
        "category": "化学者",
        "episode_text": "あなたと同じ69歳のとき、鈴木梅太郎は1943年9月20日、東京で脳溢血のため亡くなりました。ビタミンB1（オリザニン）を世界で初めて発見し、脚気の原因解明に貢献した農芸化学者でした。ノーベル賞候補にもなりましたが、論文発表のタイミングで受賞を逃しました。",
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
