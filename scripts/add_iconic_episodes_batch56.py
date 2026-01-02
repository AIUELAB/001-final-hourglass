#!/usr/bin/env python3
"""
Batch 56: 海外の政治家・実業家の象徴エピソード（死去）追加
"""

import csv
import uuid
from datetime import datetime
from pathlib import Path


def generate_episode_id():
    return f"EP-{uuid.uuid4().hex[:8].upper()}"


# 海外の政治家・実業家の死去エピソード
ICONIC_EPISODES = [
    {
        "person_id": "P53F3AE2",
        "person_name": "エイブラハム・リンカーン",
        "age": 56.0,
        "category": "政治家",
        "episode_text": "あなたと同じ56歳のとき、エイブラハム・リンカーンは1865年4月15日、ワシントンD.C.で暗殺されました。第16代アメリカ合衆国大統領として南北戦争を指揮し、奴隷解放宣言を発した「偉大な解放者」でした。フォード劇場で観劇中にジョン・ウィルクス・ブースに撃たれ、アメリカ史上最も尊敬される大統領の一人となりました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P0C4F00C",
        "person_name": "ケネディ",
        "age": 46.0,
        "category": "政治家",
        "episode_text": "あなたと同じ46歳のとき、ジョン・F・ケネディは1963年11月22日、テキサス州ダラスで暗殺されました。第35代アメリカ合衆国大統領として「ニューフロンティア」を掲げ、キューバ危機を乗り越えた若きリーダーでした。パレード中の暗殺は世界に衝撃を与え、その死の真相は今も議論され続けています。",
        "episode_type": "死去",
    },
    {
        "person_id": "PDD944E6",
        "person_name": "リチャード・ニクソン",
        "age": 81.0,
        "category": "政治家",
        "episode_text": "あなたと同じ81歳のとき、リチャード・ニクソンは1994年4月22日、ニューヨークで脳卒中のため亡くなりました。第37代アメリカ合衆国大統領として中国との国交正常化を実現しましたが、ウォーターゲート事件で辞任に追い込まれた唯一の大統領でもありました。「私は詐欺師ではない」という言葉が皮肉にも記憶されています。",
        "episode_type": "死去",
    },
    {
        "person_id": "P94661CE",
        "person_name": "ロックフェラー",
        "age": 97.0,
        "category": "実業家",
        "episode_text": "あなたと同じ97歳のとき、ジョン・D・ロックフェラーは1937年5月23日、フロリダで心臓発作のため亡くなりました。スタンダード・オイルを創設し、史上最大の富豪となった「石油王」でした。独占禁止法で会社は分割されましたが、晩年は慈善活動に注力し、ロックフェラー財団を通じて教育・医療に貢献しました。",
        "episode_type": "死去",
    },
    {
        "person_id": "PF655E36",
        "person_name": "ハワード・ヒューズ",
        "age": 70.0,
        "category": "実業家・映画製作者",
        "episode_text": "あなたと同じ70歳のとき、ハワード・ヒューズは1976年4月5日、飛行機内で腎不全のため亡くなりました。航空機・映画・カジノ産業で成功を収めたアメリカの大富豪でした。自ら設計した飛行艇「スプルース・グース」を操縦し、世界速度記録も樹立。晩年は強迫性障害に苦しみ、隠遁生活を送りました。",
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
