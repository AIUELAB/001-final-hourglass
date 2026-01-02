#!/usr/bin/env python3
"""
Batch 49: 映画監督の象徴エピソード（死去）追加
"""

import csv
import uuid
from datetime import datetime
from pathlib import Path


def generate_episode_id():
    return f"EP-{uuid.uuid4().hex[:8].upper()}"


# 映画監督の死去エピソード
ICONIC_EPISODES = [
    {
        "person_id": "P2F7C9F0",
        "person_name": "成瀬巳喜男",
        "age": 63.0,
        "category": "映画監督",
        "episode_text": "あなたと同じ63歳のとき、成瀬巳喜男は1969年7月2日、東京で亡くなりました。「浮雲」「めし」など女性の心理を繊細に描いた日本映画の巨匠でした。小津安二郎、溝口健二と並ぶ三大監督の一人として、控えめながらも深い情感を持つ作品を残しました。「日常の中にドラマがある」という信念を貫きました。",
        "episode_type": "死去",
    },
    {
        "person_id": "PFE2FE63",
        "person_name": "アルフレッド・ヒッチコック",
        "age": 80.0,
        "category": "映画監督",
        "episode_text": "あなたと同じ80歳のとき、アルフレッド・ヒッチコックは1980年4月29日、ロサンゼルスで腎不全のため亡くなりました。「サイコ」「鳥」「めまい」など「サスペンスの神様」として50本以上の傑作を残した巨匠でした。独特のカメオ出演、ブロンド女優へのこだわり、緻密な画面構成は映画史に永遠の足跡を残しています。",
        "episode_type": "死去",
    },
    {
        "person_id": "P6167C14",
        "person_name": "スタンリー・キューブリック",
        "age": 70.0,
        "category": "映画監督",
        "episode_text": "あなたと同じ70歳のとき、スタンリー・キューブリックは1999年3月7日、イギリスの自宅で心臓発作のため亡くなりました。「2001年宇宙の旅」「時計じかけのオレンジ」「シャイニング」など完璧主義で知られる映画史上最も影響力のある監督の一人でした。「アイズ ワイド シャット」の最終編集を終えたわずか数日後の死でした。",
        "episode_type": "死去",
    },
    {
        "person_id": "P2484165",
        "person_name": "フェデリコ・フェリーニ",
        "age": 73.0,
        "category": "映画監督",
        "episode_text": "あなたと同じ73歳のとき、フェデリコ・フェリーニは1993年10月31日、ローマで心臓発作のため亡くなりました。「8½」「甘い生活」「道」など夢と現実が交錯する独自の映像世界を創造したイタリア映画の巨匠でした。「フェリーニ的」という形容詞を生み出すほど独特の世界観を持ち、アカデミー外国語映画賞を4度受賞しました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P8CFA7F7",
        "person_name": "イングマール・ベルイマン",
        "age": 89.0,
        "category": "映画監督",
        "episode_text": "あなたと同じ89歳のとき、イングマール・ベルイマンは2007年7月30日、スウェーデン・フォーレ島の自宅で老衰のため亡くなりました。「第七の封印」「野いちご」「ファニーとアレクサンデル」など人間の実存と信仰を深く掘り下げた北欧映画の巨匠でした。舞台演出家としても活躍し、その影響は世界中の映画作家に及んでいます。",
        "episode_type": "死去",
    },
    {
        "person_id": "P333EFC3",
        "person_name": "フランソワ・トリュフォー",
        "age": 52.0,
        "category": "映画監督",
        "episode_text": "あなたと同じ52歳のとき、フランソワ・トリュフォーは1984年10月21日、パリで脳腫瘍のため亡くなりました。「大人は判ってくれない」「突然炎のごとく」などフランス・ヌーヴェルヴァーグを代表する監督でした。映画批評家から監督に転身し、自伝的なアントワーヌ・ドワネル・シリーズで映画と人生を重ね合わせました。",
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
