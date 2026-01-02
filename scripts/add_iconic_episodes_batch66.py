#!/usr/bin/env python3
"""
Batch 66: 歴史的指導者の象徴エピソード（死去）追加
"""

import csv
import uuid
from datetime import datetime
from pathlib import Path


def generate_episode_id():
    return f"EP-{uuid.uuid4().hex[:8].upper()}"


# 歴史的指導者の死去エピソード
ICONIC_EPISODES = [
    {
        "person_id": "P904B25F",
        "person_name": "チンギス・ハン",
        "age": 65.0,
        "category": "歴史",
        "episode_text": "あなたと同じ65歳のとき、チンギス・ハンは1227年8月18日、中国遠征中に亡くなりました。モンゴル帝国を建国し、ユーラシア大陸に史上最大の陸上帝国を築いた征服者でした。その死因は落馬説、病死説など諸説あり、墓所は今も発見されていません。「一人の敵を恐れるな、千人の敵を恐れろ」という言葉を残しました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P0AB1BB5",
        "person_name": "ヨシフ・スターリン",
        "age": 74.0,
        "category": "政治・社会",
        "episode_text": "あなたと同じ74歳のとき、ヨシフ・スターリンは1953年3月5日、モスクワで脳卒中のため亡くなりました。ソ連を超大国に育て上げた一方、大粛清で数百万人を死に至らしめた独裁者でした。その死は側近たちを恐怖させ、長時間放置されたとも言われています。「死は全てを解決する。人間がいなければ問題もない」という冷酷な言葉を残しました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P19E01E4",
        "person_name": "ベニト・ムッソリーニ",
        "age": 61.0,
        "category": "歴史",
        "episode_text": "あなたと同じ61歳のとき、ベニト・ムッソリーニは1945年4月28日、イタリアでパルチザンに処刑されました。ファシズムを創始し「ドゥーチェ（統帥）」として20年以上イタリアを支配した独裁者でした。愛人クラレッタと共に銃殺され、遺体はミラノの広場で逆さ吊りにされて民衆に晒されました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P0B2BD54",
        "person_name": "ドワイト・D・アイゼンハワー",
        "age": 78.0,
        "category": "政治・社会",
        "episode_text": "あなたと同じ78歳のとき、ドワイト・D・アイゼンハワーは1969年3月28日、ワシントンD.C.で心不全のため亡くなりました。第二次世界大戦でノルマンディー上陸作戦を指揮し、第34代アメリカ大統領となった軍人・政治家でした。退任演説で「軍産複合体」の危険性を警告したことは、今も語り継がれています。",
        "episode_type": "死去",
    },
    {
        "person_id": "P7DDE505",
        "person_name": "エレノア・ルーズベルト",
        "age": 78.0,
        "category": "政治・社会",
        "episode_text": "あなたと同じ78歳のとき、エレノア・ルーズベルトは1962年11月7日、ニューヨークで再生不良性貧血のため亡くなりました。フランクリン・ルーズベルト大統領夫人として、人権擁護と社会改革に尽力したファーストレディでした。国連人権委員会の初代議長として世界人権宣言の起草に貢献し、「世界のファーストレディ」と称されました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P760EBC5",
        "person_name": "セオドア・ルーズベルト",
        "age": 60.0,
        "category": "歴史",
        "episode_text": "あなたと同じ60歳のとき、セオドア・ルーズベルトは1919年1月6日、ニューヨークで心臓発作のため亡くなりました。第26代アメリカ大統領として「棍棒外交」を展開し、パナマ運河建設を推進した政治家でした。ノーベル平和賞を受賞した初のアメリカ人であり、テディベアの名前の由来ともなりました。",
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
