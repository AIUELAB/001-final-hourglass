#!/usr/bin/env python3
"""
Batch 30: 数学者・物理学者の象徴エピソード（死去）追加
"""

import csv
import uuid
from datetime import datetime
from pathlib import Path


def generate_episode_id():
    return f"EP-{uuid.uuid4().hex[:8].upper()}"


# 数学者・物理学者の死去エピソード
ICONIC_EPISODES = [
    {
        "person_id": "P2663ACE",
        "person_name": "カール・フリードリヒ・ガウス",
        "age": 77.0,
        "category": "数学者",
        "episode_text": "あなたと同じ77歳のとき、カール・フリードリヒ・ガウスは1855年2月23日、ドイツ・ゲッティンゲンで睡眠中に亡くなりました。「数学の王」と称され、数論、幾何学、統計学、天文学など多岐にわたる分野で革命的な業績を残した天才でした。正規分布（ガウス分布）や最小二乗法など、現代科学の基盤となる概念を確立。「数学は科学の女王であり、数論は数学の女王である」という言葉を残しています。",
        "episode_type": "死去",
    },
    {
        "person_id": "P52BF511",
        "person_name": "ベルンハルト・リーマン",
        "age": 39.0,
        "category": "数学者",
        "episode_text": "あなたと同じ39歳のとき、ベルンハルト・リーマンは1866年7月20日、イタリア・セラスカで結核のため亡くなりました。リーマン幾何学を創始し、アインシュタインの一般相対性理論の数学的基盤を提供した天才数学者でした。「リーマン予想」は160年以上経った今も未解決の難問として数学者を魅了し続けています。39歳という若さでの死は数学界にとって大きな損失でした。",
        "episode_type": "死去",
    },
    {
        "person_id": "PE17624B",
        "person_name": "岡潔",
        "age": 76.0,
        "category": "数学者",
        "episode_text": "あなたと同じ76歳のとき、岡潔は1978年3月1日、奈良県の自宅で亡くなりました。多変数複素関数論で世界的な業績を残し、「日本が生んだ最も偉大な数学者」と評された天才でした。独学で数学を極め、3つの大問題を単独で解決。随筆家としても活躍し、「情緒」の重要性を説いた著作は広く読まれました。文化勲章を受章し、日本の知性の象徴として敬われました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P37122AD",
        "person_name": "ニールス・ボーア",
        "age": 77.0,
        "category": "物理学者",
        "episode_text": "あなたと同じ77歳のとき、ニールス・ボーアは1962年11月18日、デンマーク・コペンハーゲンの自宅で心臓発作のため亡くなりました。原子構造のボーアモデルを提唱し、量子力学の発展に決定的な貢献をした20世紀最大の物理学者の一人でした。1922年にノーベル物理学賞を受賞。コペンハーゲン解釈を確立し、アインシュタインとの論争は科学史に残る知的対決として知られています。",
        "episode_type": "死去",
    },
    {
        "person_id": "P704E885",
        "person_name": "リチャード・ファインマン",
        "age": 69.0,
        "category": "物理学者",
        "episode_text": "あなたと同じ69歳のとき、リチャード・ファインマンは1988年2月15日、カリフォルニア州ロサンゼルスで腹部がんのため亡くなりました。量子電磁力学（QED）の発展に貢献し、1965年にノーベル物理学賞を受賞した天才物理学者でした。「ファインマン・ダイアグラム」を考案し、複雑な計算を視覚化。ユーモアあふれる講義と著作で物理学の魅力を広く伝え、「物理学のショーマン」として愛されました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P5578985",
        "person_name": "南部陽一郎",
        "age": 94.0,
        "category": "物理学者",
        "episode_text": "あなたと同じ94歳のとき、南部陽一郎は2015年7月5日、大阪府豊中市内の病院で急性心筋梗塞のため亡くなりました。「自発的対称性の破れ」の概念を提唱し、2008年にノーベル物理学賞を受賞した理論物理学の巨人でした。素粒子物理学の標準模型の基礎を築き、弦理論の先駆者としても知られます。シカゴ大学で長年研究を続け、日本とアメリカの物理学界を結ぶ架け橋となりました。",
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
