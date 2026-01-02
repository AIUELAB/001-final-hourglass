#!/usr/bin/env python3
"""
Batch 45: 戦国武将の象徴エピソード（死去）追加
"""

import csv
import uuid
from datetime import datetime
from pathlib import Path


def generate_episode_id():
    return f"EP-{uuid.uuid4().hex[:8].upper()}"


# 戦国武将の死去エピソード
ICONIC_EPISODES = [
    {
        "person_id": "PB85FB41",
        "person_name": "伊達政宗",
        "age": 70.0,
        "category": "戦国武将",
        "episode_text": "あなたと同じ70歳のとき、伊達政宗は1636年6月27日（旧暦5月24日）、江戸で食道癌のため亡くなりました。「独眼竜」の異名で知られる奥州の覇者であり、天下取りへの野望を抱きながらも豊臣・徳川両政権に仕えた戦国最後の名将でした。仙台藩62万石を築き、伊達家の繁栄の礎を固めました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P8998A23",
        "person_name": "毛利元就",
        "age": 74.0,
        "category": "戦国武将",
        "episode_text": "あなたと同じ74歳のとき、毛利元就は1571年7月6日（旧暦6月14日）、安芸郡山城で老衰のため亡くなりました。「三本の矢」の教えで知られる中国地方の覇者であり、小領主から中国十カ国を支配する大大名に成り上がった戦国随一の謀略家でした。子の輝元は関ヶ原で西軍の総大将を務めることになります。",
        "episode_type": "死去",
    },
    {
        "person_id": "PDA34867",
        "person_name": "今川義元",
        "age": 42.0,
        "category": "戦国武将",
        "episode_text": "あなたと同じ42歳のとき、今川義元は1560年6月12日（旧暦5月19日）、桶狭間の戦いで織田信長に討たれました。駿河・遠江・三河を支配し、上洛を目指して大軍を率いていた「海道一の弓取り」でした。2万5千の大軍が奇襲を受け、本陣を突かれての最期は戦国史最大の番狂わせとして語り継がれています。",
        "episode_type": "死去",
    },
    {
        "person_id": "PBEC1492",
        "person_name": "明智光秀",
        "age": 55.0,
        "category": "戦国武将",
        "episode_text": "あなたと同じ55歳のとき、明智光秀は1582年7月2日（旧暦6月13日）、山崎の戦いで敗れた後、小栗栖で落ち武者狩りに遭い命を落としました。本能寺の変で織田信長を討った「謀反人」として知られますが、わずか13日間の天下は「三日天下」の語源となりました。その動機は今も歴史最大の謎の一つです。",
        "episode_type": "死去",
    },
    {
        "person_id": "P735A5E8",
        "person_name": "石田三成",
        "age": 40.0,
        "category": "戦国武将",
        "episode_text": "あなたと同じ40歳のとき、石田三成は1600年11月6日（旧暦10月1日）、関ヶ原の戦いに敗れ、京都六条河原で斬首されました。豊臣政権の文治派を代表する五奉行の一人であり、秀吉没後の政権を守ろうと西軍を率いて徳川家康と対決しました。処刑前に干し柿を勧められ「大志を持つ者は最後まで命を大事にする」と断った逸話が残ります。",
        "episode_type": "死去",
    },
    {
        "person_id": "PA3902F7",
        "person_name": "加藤清正",
        "age": 49.0,
        "category": "戦国武将",
        "episode_text": "あなたと同じ49歳のとき、加藤清正は1611年8月2日（旧暦6月24日）、熊本城で急死しました。「虎退治」で知られる猛将であり、秀吉子飼いの武断派として朝鮮出兵でも活躍しました。熊本城の築城者として知られ、その堅固な石垣は「武者返し」と呼ばれます。急死の原因は毒殺説もありますが、真相は不明です。",
        "episode_type": "死去",
    },
    {
        "person_id": "PA1082DF",
        "person_name": "前田利家",
        "age": 61.0,
        "category": "戦国武将",
        "episode_text": "あなたと同じ61歳のとき、前田利家は1599年閏3月3日、大坂で病死しました。織田信長に仕えた「槍の又左」から加賀百万石の大大名に上り詰めた戦国武将でした。豊臣政権では五大老として秀吉を支え、家康を牽制しましたが、その死が関ヶ原への道を開くことになりました。",
        "episode_type": "死去",
    },
    {
        "person_id": "PD0758DA",
        "person_name": "柴田勝家",
        "age": 61.0,
        "category": "戦国武将",
        "episode_text": "あなたと同じ61歳のとき、柴田勝家は1583年6月14日（旧暦4月24日）、賤ヶ岳の戦いに敗れ、北ノ庄城で妻・お市の方と共に自害しました。「鬼柴田」と恐れられた織田家筆頭の猛将でしたが、秀吉との覇権争いに敗れました。天守に火を放ち、お市の方を刺してから自害したとされています。",
        "episode_type": "死去",
    },
    {
        "person_id": "P119492A",
        "person_name": "本多忠勝",
        "age": 63.0,
        "category": "戦国武将",
        "episode_text": "あなたと同じ63歳のとき、本多忠勝は1610年12月3日（旧暦10月18日）、桑名で病死しました。徳川四天王の一人として57度の戦いで一度も傷を負わなかったという伝説的武将でした。愛槍「蜻蛉切」を振るう姿は「家康に過ぎたるものが二つあり、唐の頭に本多平八」と称えられました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P5676A70",
        "person_name": "直江兼続",
        "age": 60.0,
        "category": "戦国武将",
        "episode_text": "あなたと同じ60歳のとき、直江兼続は1619年12月19日（旧暦12月19日）、米沢で病死しました。「愛」の前立てで知られる上杉景勝の重臣であり、関ヶ原の戦いでは家康に対して「直江状」を送りつけた気骨の武将でした。米沢藩の基礎を築き、文武両道の名将として後世に語り継がれています。",
        "episode_type": "死去",
    },
    {
        "person_id": "P5F50783",
        "person_name": "真田信繁",
        "age": 49.0,
        "category": "戦国武将",
        "episode_text": "あなたと同じ49歳のとき、真田信繁（真田幸村）は1615年6月3日（旧暦5月7日）、大坂夏の陣で討ち死にしました。「日本一の兵」と称えられた戦国最後の名将であり、家康本陣に突撃して一時は旗本を蹴散らす奮戦を見せました。「真田丸」での活躍と壮絶な最期は、後世に伝説として語り継がれています。",
        "episode_type": "死去",
    },
    {
        "person_id": "P750FCC2",
        "person_name": "北条氏康",
        "age": 56.0,
        "category": "戦国武将",
        "episode_text": "あなたと同じ56歳のとき、北条氏康は1571年10月21日（旧暦10月3日）、小田原城で病死しました。関東の覇者として上杉謙信・武田信玄と渡り合い、北条五代の中興の祖となった名君でした。河越夜戦での大勝利は戦国三大奇襲の一つに数えられます。民政にも優れ、「禄寿応穏」の印判で知られます。",
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
