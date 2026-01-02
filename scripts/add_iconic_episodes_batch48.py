#!/usr/bin/env python3
"""
Batch 48: 海外の作家の象徴エピソード（死去）追加
"""

import csv
import uuid
from datetime import datetime
from pathlib import Path


def generate_episode_id():
    return f"EP-{uuid.uuid4().hex[:8].upper()}"


# 海外の作家の死去エピソード
ICONIC_EPISODES = [
    {
        "person_id": "P2595B54",
        "person_name": "アーネスト・ヘミングウェイ",
        "age": 61.0,
        "category": "小説家",
        "episode_text": "あなたと同じ61歳のとき、アーネスト・ヘミングウェイは1961年7月2日、アイダホ州ケチャムで猟銃自殺により亡くなりました。「老人と海」「武器よさらば」など簡潔で力強い文体で20世紀文学を代表し、1954年にノーベル文学賞を受賞しました。「氷山理論」と呼ばれる文体は世界中の作家に影響を与え続けています。",
        "episode_type": "死去",
    },
    {
        "person_id": "P5543A0D",
        "person_name": "F・スコット・フィッツジェラルド",
        "age": 44.0,
        "category": "小説家",
        "episode_text": "あなたと同じ44歳のとき、F・スコット・フィッツジェラルドは1940年12月21日、ハリウッドで心臓発作のため亡くなりました。「グレート・ギャツビー」で1920年代アメリカの繁栄と虚無を描き、「ジャズ・エイジ」の命名者として知られる作家でした。生前は不遇でしたが、死後「ギャツビー」はアメリカ文学最高傑作の一つに数えられるようになりました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P9BC758E",
        "person_name": "レフ・トルストイ",
        "age": 82.0,
        "category": "小説家",
        "episode_text": "あなたと同じ82歳のとき、レフ・トルストイは1910年11月20日、ロシアの小さな駅で肺炎のため亡くなりました。「戦争と平和」「アンナ・カレーニナ」など世界文学の最高峰を残した巨匠でした。晩年は私有財産を否定し、家出の途中で病に倒れました。その死は世界中に衝撃を与え、葬儀には数千人が参列しました。",
        "episode_type": "死去",
    },
    {
        "person_id": "PE88E31",
        "person_name": "フランツ・カフカ",
        "age": 40.0,
        "category": "小説家",
        "episode_text": "あなたと同じ40歳のとき、フランツ・カフカは1924年6月3日、オーストリアの療養所で喉頭結核のため亡くなりました。「変身」「審判」「城」など不条理な世界を描き、20世紀文学に決定的な影響を与えた作家でした。生前は無名に近く、遺稿の焼却を遺言しましたが、友人マックス・ブロートが出版し、死後に世界的評価を得ました。",
        "episode_type": "死去",
    },
    {
        "person_id": "PFBF0C13",
        "person_name": "アルベール・カミュ",
        "age": 46.0,
        "category": "小説家・哲学者",
        "episode_text": "あなたと同じ46歳のとき、アルベール・カミュは1960年1月4日、フランス・ヴィルブルヴァンで自動車事故により亡くなりました。「異邦人」「ペスト」など不条理の哲学を文学化し、1957年にノーベル文学賞を受賞した作家・思想家でした。ポケットには未使用の列車の切符があり、友人の車に同乗したことが悲劇につながりました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P6663CD5",
        "person_name": "ジェーン・オースティン",
        "age": 41.0,
        "category": "小説家",
        "episode_text": "あなたと同じ41歳のとき、ジェーン・オースティンは1817年7月18日、イギリス・ウィンチェスターでアジソン病とみられる病気のため亡くなりました。「高慢と偏見」「エマ」などイギリス社会を鋭い観察眼と機知で描いた作家でした。生前は匿名で出版され、死後に評価が高まり、今も世界中で愛読され続けています。",
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
