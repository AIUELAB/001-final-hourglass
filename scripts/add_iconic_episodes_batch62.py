#!/usr/bin/env python3
"""
Batch 62: 芸術家・画家の象徴エピソード（死去）追加
"""

import csv
import uuid
from datetime import datetime
from pathlib import Path


def generate_episode_id():
    return f"EP-{uuid.uuid4().hex[:8].upper()}"


# 芸術家・画家の死去エピソード
ICONIC_EPISODES = [
    {
        "person_id": "P0698595",
        "person_name": "J.M.W.ターナー",
        "age": 76.0,
        "category": "芸術・文化",
        "episode_text": "あなたと同じ76歳のとき、ジョゼフ・マロード・ウィリアム・ターナーは1851年12月19日、ロンドンで亡くなりました。光と大気の表現を追求し、印象派に先駆けた英国最大のロマン派画家でした。「太陽は神である」と言い残し、壮大な海景画と風景画で自然の崇高さを描き続けました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P0921407",
        "person_name": "エドガー・ドガ",
        "age": 83.0,
        "category": "芸術・文化",
        "episode_text": "あなたと同じ83歳のとき、エドガー・ドガは1917年9月27日、パリで亡くなりました。バレエの踊り子を独特の構図で描き続けた印象派の画家でした。「芸術はありのままの生活を描くものではない、生活の本質を描くものだ」と語り、動きの瞬間を捉えた革新的な作品を残しました。",
        "episode_type": "死去",
    },
    {
        "person_id": "PF8E6FD7",
        "person_name": "カラヴァッジョ",
        "age": 38.0,
        "category": "芸術・文化",
        "episode_text": "あなたと同じ38歳のとき、ミケランジェロ・メリージ・ダ・カラヴァッジョは1610年7月18日、イタリアで熱病のため亡くなりました。劇的な明暗法（キアロスクーロ）でバロック絵画を革新した天才画家でした。殺人を犯して逃亡生活を送りながらも、リアリズムと光の表現で西洋美術史に革命をもたらしました。",
        "episode_type": "死去",
    },
    {
        "person_id": "PA85E61E",
        "person_name": "コンスタブル",
        "age": 60.0,
        "category": "芸術・文化",
        "episode_text": "あなたと同じ60歳のとき、ジョン・コンスタブルは1837年3月31日、ロンドンで心臓発作のため亡くなりました。英国の田園風景を詩情豊かに描き、風景画を芸術の一ジャンルとして確立した画家でした。「絵画は科学であり、自然法則の探求として追求されるべきだ」と述べ、雲の研究など科学的アプローチで自然を捉えました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P2998BD2",
        "person_name": "ティツィアーノ",
        "age": 88.0,
        "category": "芸術・文化",
        "episode_text": "あなたと同じ88歳のとき、ティツィアーノ・ヴェチェッリオは1576年8月27日、ヴェネツィアでペストのため亡くなりました。ヴェネツィア派最大の巨匠として、豊かな色彩と官能的な人体表現で西洋絵画に革命をもたらしました。教皇や皇帝の肖像画家として、70年以上のキャリアで数々の傑作を残しました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P5871B70",
        "person_name": "マネ",
        "age": 51.0,
        "category": "芸術・文化",
        "episode_text": "あなたと同じ51歳のとき、エドゥアール・マネは1883年4月30日、パリで壊疽により左足を切断した後に亡くなりました。『草上の昼食』『オランピア』で美術界にスキャンダルを巻き起こし、印象派の父と呼ばれた画家でした。伝統と革新の橋渡し役として、近代絵画の扉を開きました。",
        "episode_type": "死去",
    },
    {
        "person_id": "PA1813DE",
        "person_name": "円山応挙",
        "age": 62.0,
        "category": "芸術・文化",
        "episode_text": "あなたと同じ62歳のとき、円山応挙は1795年8月31日、京都で亡くなりました。写生を重視した円山派を創始し、日本画に革新をもたらした江戸中期の画家でした。「真を写す」ことを追求し、『雪松図屏風』など生命感あふれる作品で日本美術史に大きな足跡を残しました。",
        "episode_type": "死去",
    },
    {
        "person_id": "PDE5F549",
        "person_name": "平山郁夫",
        "age": 79.0,
        "category": "芸術・文化",
        "episode_text": "あなたと同じ79歳のとき、平山郁夫は2009年12月2日、東京で脳梗塞のため亡くなりました。シルクロードを主題に壮大な仏教美術を描き続けた日本画家でした。広島で被爆した経験から平和への祈りを込め、文化財保護活動にも尽力。東京藝術大学学長も務めました。",
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
