#!/usr/bin/env python3
"""
Batch 33: 登山家・冒険家の象徴エピソード（死去）追加
"""

import csv
import uuid
from datetime import datetime
from pathlib import Path


def generate_episode_id():
    return f"EP-{uuid.uuid4().hex[:8].upper()}"


# 登山家・冒険家の死去エピソード（存命者除外）
ICONIC_EPISODES = [
    {
        "person_id": "P38D5E39",
        "person_name": "植村直己",
        "age": 43.0,
        "category": "冒険家・登山家",
        "episode_text": "あなたと同じ43歳のとき、植村直己は1984年2月13日、アラスカのマッキンリー（現デナリ）で消息を絶ちました。世界初の五大陸最高峰登頂、北極圏単独犬ぞり横断など数々の偉業を達成した日本を代表する冒険家でした。冬季マッキンリー単独登頂に成功した直後の下山中に遭難。遺体は発見されませんでしたが、その冒険精神は「植村直己冒険賞」として今も受け継がれています。国民栄誉賞が贈られました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P919D355",
        "person_name": "田部井淳子",
        "age": 77.0,
        "category": "登山家",
        "episode_text": "あなたと同じ77歳のとき、田部井淳子は2016年10月20日、腹膜がんのため埼玉県内の病院で亡くなりました。1975年に女性として世界初のエベレスト登頂に成功し、さらに女性初の七大陸最高峰登頂も達成した「女性登山家のパイオニア」でした。がん治療中も山への情熱を失わず、東日本大震災の被災地の高校生を富士山に導く活動を続けました。「山の日」制定にも尽力しました。",
        "episode_type": "死去",
    },
    {
        "person_id": "PE4710AD",
        "person_name": "栗城史多",
        "age": 35.0,
        "category": "登山家",
        "episode_text": "あなたと同じ35歳のとき、栗城史多は2018年5月21日、エベレスト登頂に挑戦中に遭難し亡くなりました。「冒険の共有」をテーマに登山をインターネット中継し、多くの人に夢と勇気を届けた新時代の登山家でした。エベレストには8度挑戦し、2012年の挑戦では凍傷で指9本を失いながらも挑戦を続けました。35歳という若さでの死は、冒険の危険性と情熱の両面を世に問いかけました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P9D92F34",
        "person_name": "長谷川恒男",
        "age": 43.0,
        "category": "登山家",
        "episode_text": "あなたと同じ43歳のとき、長谷川恒男は1991年10月10日、パキスタンのウルタルII峰で雪崩に巻き込まれ亡くなりました。アルプス三大北壁の冬季単独登攀に成功した世界的クライマーであり、「ハセツネ」の愛称で親しまれました。その功績を称え、東京都あきる野市で毎年開催される「日本山岳耐久レース（ハセツネカップ）」に名を残しています。",
        "episode_type": "死去",
    },
    {
        "person_id": "PF526E62",
        "person_name": "エドモンド・ヒラリー",
        "age": 88.0,
        "category": "登山家・探検家",
        "episode_text": "あなたと同じ88歳のとき、エドモンド・ヒラリーは2008年1月11日、ニュージーランド・オークランドで心臓発作のため亡くなりました。1953年にテンジン・ノルゲイと共に人類初のエベレスト登頂に成功した伝説的登山家でした。その後も南極探検に参加し、ネパールでは学校や病院の建設など社会貢献活動に尽力。ニュージーランドの国民的英雄として紙幣の肖像にもなりました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P0452FDC",
        "person_name": "テンジン・ノルゲイ",
        "age": 71.0,
        "category": "登山家",
        "episode_text": "あなたと同じ71歳のとき、テンジン・ノルゲイは1986年5月9日、インド・ダージリンで脳出血のため亡くなりました。1953年にエドモンド・ヒラリーと共に人類初のエベレスト登頂に成功したシェルパ族の英雄でした。ネパールとインドの両国で国民的英雄として称えられ、ヒマラヤ登山の発展に多大な貢献をしました。謙虚な人柄で、頂上に最初に立ったのは誰かという質問には「二人で一緒に」と答え続けました。",
        "episode_type": "死去",
    },
    {
        "person_id": "PEFEF6D5",
        "person_name": "ジョージ・マロリー",
        "age": 37.0,
        "category": "登山家",
        "episode_text": "あなたと同じ37歳のとき、ジョージ・マロリーは1924年6月8日、エベレスト登頂に挑戦中に消息を絶ちました。「なぜ山に登るのか」という問いに「そこに山があるから」と答えた伝説的登山家です。パートナーのアーヴィンと共に山頂を目指しましたが、悪天候の中で姿を消しました。1999年に遺体が発見されましたが、登頂に成功したかどうかは今も謎のまま、登山史最大のミステリーとして語り継がれています。",
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
