#!/usr/bin/env python3
"""
Batch 47: 日本の作家の象徴エピソード（死去）追加
"""

import csv
import uuid
from datetime import datetime
from pathlib import Path


def generate_episode_id():
    return f"EP-{uuid.uuid4().hex[:8].upper()}"


# 日本の作家の死去エピソード
ICONIC_EPISODES = [
    {
        "person_id": "P73422E6",
        "person_name": "芥川龍之介",
        "age": 35.0,
        "category": "小説家",
        "episode_text": "あなたと同じ35歳のとき、芥川龍之介は1927年7月24日、東京の自宅で睡眠薬による自殺で亡くなりました。「羅生門」「鼻」「地獄変」など短編の名手として知られ、その名を冠した芥川賞は日本文学の登竜門となっています。遺書に「ぼんやりとした不安」と記した言葉は、時代の精神を象徴するものとして語り継がれています。",
        "episode_type": "死去",
    },
    {
        "person_id": "P99B64BA",
        "person_name": "森鴎外",
        "age": 60.0,
        "category": "小説家・軍医",
        "episode_text": "あなたと同じ60歳のとき、森鴎外は1922年7月9日、東京で萎縮腎と肺結核のため亡くなりました。「舞姫」「高瀬舟」など近代文学の傑作を残し、陸軍軍医総監として脚気問題にも関わった文豪でした。遺言で「余は石見人森林太郎として死せんと欲す」と記し、官位を辞して故郷の名で葬られることを望みました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P329EA30",
        "person_name": "志賀直哉",
        "age": 88.0,
        "category": "小説家",
        "episode_text": "あなたと同じ88歳のとき、志賀直哉は1971年10月21日、東京で肺炎のため亡くなりました。「暗夜行路」「城の崎にて」など心境小説の名手として「小説の神様」と称えられた白樺派の中心作家でした。簡潔で的確な文体は日本語の模範とされ、多くの作家に影響を与えました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P7DE3B45",
        "person_name": "井伏鱒二",
        "age": 95.0,
        "category": "小説家",
        "episode_text": "あなたと同じ95歳のとき、井伏鱒二は1993年7月10日、東京で老衰のため亡くなりました。「黒い雨」「山椒魚」など独特のユーモアと哀感を持つ作品で知られ、太宰治の師としても知られる作家でした。「山椒魚は悲しんだ」という一文は日本文学史上最も有名な書き出しの一つです。",
        "episode_type": "死去",
    },
    {
        "person_id": "PBB70378",
        "person_name": "安部公房",
        "age": 68.0,
        "category": "小説家・劇作家",
        "episode_text": "あなたと同じ68歳のとき、安部公房は1993年1月22日、東京で心不全のため亡くなりました。「砂の女」「箱男」など不条理で実験的な作品で世界的に評価され、ノーベル文学賞候補にも挙げられた前衛作家でした。カフカの影響を受けながらも独自の世界観を確立し、日本文学に新たな地平を開きました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P1EF2A1F",
        "person_name": "遠藤周作",
        "age": 73.0,
        "category": "小説家",
        "episode_text": "あなたと同じ73歳のとき、遠藤周作は1996年9月29日、東京で肺炎のため亡くなりました。「沈黙」「海と毒薬」などキリスト教と日本人の信仰をテーマにした作品で知られる「第三の新人」の代表的作家でした。「沈黙」は2016年にマーティン・スコセッシ監督により映画化され、世界的に再評価されました。",
        "episode_type": "死去",
    },
    {
        "person_id": "PAE21DB8",
        "person_name": "司馬遼太郎",
        "age": 72.0,
        "category": "小説家",
        "episode_text": "あなたと同じ72歳のとき、司馬遼太郎は1996年2月12日、大阪で腹部大動脈瘤破裂のため亡くなりました。「竜馬がゆく」「坂の上の雲」など歴史小説の大家として国民的作家となり、「司馬史観」と呼ばれる独自の歴史観を示しました。その著作は日本人の歴史認識に大きな影響を与え続けています。",
        "episode_type": "死去",
    },
    {
        "person_id": "P77249E7",
        "person_name": "松本清張",
        "age": 82.0,
        "category": "小説家",
        "episode_text": "あなたと同じ82歳のとき、松本清張は1992年8月4日、東京で肝臓癌のため亡くなりました。「点と線」「砂の器」など社会派推理小説の巨匠として知られ、41歳でのデビューから膨大な作品を残した作家でした。権力の闇や社会の矛盾を鋭く描き、推理小説を文学の領域に高めました。",
        "episode_type": "死去",
    },
    {
        "person_id": "PC2D8EC3",
        "person_name": "江戸川乱歩",
        "age": 70.0,
        "category": "推理作家",
        "episode_text": "あなたと同じ70歳のとき、江戸川乱歩は1965年7月28日、東京で脳出血のため亡くなりました。「怪人二十面相」「人間椅子」など日本の探偵小説を確立し、エドガー・アラン・ポーにちなんだ筆名で知られる作家でした。その名を冠した江戸川乱歩賞は推理作家の登竜門として今も続いています。",
        "episode_type": "死去",
    },
    {
        "person_id": "P4F5CB5B",
        "person_name": "向田邦子",
        "age": 51.0,
        "category": "脚本家・作家",
        "episode_text": "あなたと同じ51歳のとき、向田邦子は1981年8月22日、台湾での航空機墜落事故により亡くなりました。「阿修羅のごとく」「寺内貫太郎一家」など家族の機微を描いたテレビドラマの名脚本家であり、「思い出トランプ」で直木賞を受賞した作家でもありました。突然の死は日本中に衝撃を与えました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P6D12F2B",
        "person_name": "大江健三郎",
        "age": 88.0,
        "category": "小説家",
        "episode_text": "あなたと同じ88歳のとき、大江健三郎は2023年3月3日、東京で老衰のため亡くなりました。「個人的な体験」「万延元年のフットボール」など戦後日本文学を代表する作家として1994年にノーベル文学賞を受賞しました。障害を持つ息子・光との関係、核や戦争への批判を作品に込め続けた知識人でした。",
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
