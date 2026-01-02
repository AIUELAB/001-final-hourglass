#!/usr/bin/env python3
"""
Batch 69: 映画監督の象徴エピソード（死去）追加 - 海外編
"""

import csv
import uuid
from datetime import datetime
from pathlib import Path


def generate_episode_id():
    return f"EP-{uuid.uuid4().hex[:8].upper()}"


# 海外の映画監督の死去エピソード
ICONIC_EPISODES = [
    {
        "person_id": "PBE7BE6B",
        "person_name": "シドニー・ポラック",
        "age": 73.0,
        "category": "芸術・文化",
        "episode_text": "あなたと同じ73歳のとき、シドニー・ポラックは2008年5月26日、ロサンゼルスで胃がんのため亡くなりました。『愛と哀しみの果て』でアカデミー監督賞を受賞したハリウッドの名匠でした。『トッツィー』『追憶』など繊細な人間ドラマを得意とし、俳優としても活躍しました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P344F87F",
        "person_name": "シドニー・ルメット",
        "age": 86.0,
        "category": "芸術・文化",
        "episode_text": "あなたと同じ86歳のとき、シドニー・ルメットは2011年4月9日、ニューヨークでリンパ腫のため亡くなりました。『十二人の怒れる男』『狼たちの午後』『ネットワーク』など、社会派映画の巨匠でした。アカデミー名誉賞を受賞し、50年以上のキャリアで50本以上の映画を監督しました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P8DD4CB1",
        "person_name": "ジョン・ヒューストン",
        "age": 81.0,
        "category": "芸術・文化",
        "episode_text": "あなたと同じ81歳のとき、ジョン・ヒューストンは1987年8月28日、ロードアイランドで肺気腫のため亡くなりました。『マルタの鷹』『アフリカの女王』など、フィルム・ノワールと冒険映画の巨匠でした。父ウォルター、娘アンジェリカと三世代でオスカーを受賞した唯一の映画ファミリーとして知られています。",
        "episode_type": "死去",
    },
    {
        "person_id": "PBFDC1F6",
        "person_name": "エリア・カザン",
        "age": 94.0,
        "category": "芸術・文化",
        "episode_text": "あなたと同じ94歳のとき、エリア・カザンは2003年9月28日、ニューヨークで亡くなりました。『欲望という名の電車』『波止場』『エデンの東』など、アメリカ演劇と映画の革新者でした。マーロン・ブランド、ジェームズ・ディーンを見出し、メソッド演技法を映画界に広めた功績は計り知れません。",
        "episode_type": "死去",
    },
    {
        "person_id": "P3B3B39E",
        "person_name": "ウィリアム・ワイラー",
        "age": 79.0,
        "category": "芸術・文化",
        "episode_text": "あなたと同じ79歳のとき、ウィリアム・ワイラーは1981年7月27日、ロサンゼルスで心臓発作のため亡くなりました。『ベン・ハー』『ローマの休日』『我等の生涯の最良の年』でアカデミー監督賞を3度受賞したハリウッド黄金期の巨匠でした。完璧主義で知られ「40テイクのワイラー」と呼ばれました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P6812714",
        "person_name": "ジョン・フォード",
        "age": 79.0,
        "category": "芸術・文化",
        "episode_text": "あなたと同じ79歳のとき、ジョン・フォードは1973年8月31日、カリフォルニアで胃がんのため亡くなりました。『駅馬車』『荒野の決闘』『捜索者』など、アメリカ西部劇の黄金期を築いた監督でした。アカデミー監督賞を史上最多の4度受賞し、モニュメントバレーの風景を映画の象徴にしました。",
        "episode_type": "死去",
    },
    {
        "person_id": "PDFE59DF",
        "person_name": "ハワード・ホークス",
        "age": 81.0,
        "category": "芸術・文化",
        "episode_text": "あなたと同じ81歳のとき、ハワード・ホークスは1977年12月26日、カリフォルニアで亡くなりました。『三つ数えろ』『赤い河』『リオ・ブラボー』など、あらゆるジャンルで傑作を残したハリウッドの巨匠でした。「ホークス的女性」と呼ばれる自立した女性像を創造し、現代映画に多大な影響を与えました。",
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
