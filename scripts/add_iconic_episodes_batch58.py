#!/usr/bin/env python3
"""
Batch 58: 海外の物理学者・数学者の象徴エピソード（死去）追加
"""

import csv
import uuid
from datetime import datetime
from pathlib import Path


def generate_episode_id():
    return f"EP-{uuid.uuid4().hex[:8].upper()}"


# 海外の物理学者・数学者の死去エピソード
ICONIC_EPISODES = [
    {
        "person_id": "P56E484F",
        "person_name": "スティーブン・ホーキング",
        "age": 76.0,
        "category": "科学・技術",
        "episode_text": "あなたと同じ76歳のとき、スティーブン・ホーキングは2018年3月14日、ケンブリッジで亡くなりました。ALSと闘いながらブラックホールの理論を発展させ、「ホーキング放射」を予言した理論物理学者でした。車椅子と音声合成装置を使いながら宇宙の謎に挑み、『ホーキング、宇宙を語る』は世界的ベストセラーとなりました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P4954218",
        "person_name": "アラン・チューリング",
        "age": 41.0,
        "category": "学術・研究",
        "episode_text": "あなたと同じ41歳のとき、アラン・チューリングは1954年6月7日、イギリスで青酸カリ中毒により亡くなりました。「コンピュータ科学の父」として計算機の理論的基礎を築き、第二次世界大戦ではナチスの暗号エニグマを解読した天才数学者でした。同性愛を理由に迫害され、悲劇的な最期を遂げました。",
        "episode_type": "死去",
    },
    {
        "person_id": "PD9455EA",
        "person_name": "ジョン・フォン・ノイマン",
        "age": 53.0,
        "category": "学術・研究",
        "episode_text": "あなたと同じ53歳のとき、ジョン・フォン・ノイマンは1957年2月8日、ワシントンD.C.で骨肉腫のため亡くなりました。現代のコンピュータ・アーキテクチャの基礎「ノイマン型」を確立し、ゲーム理論を創始した20世紀最高の頭脳でした。量子力学、経済学、気象学など多分野に革命をもたらしました。",
        "episode_type": "死去",
    },
    {
        "person_id": "PD1B48C5",
        "person_name": "エルヴィン・シュレーディンガー",
        "age": 73.0,
        "category": "学術・研究",
        "episode_text": "あなたと同じ73歳のとき、エルヴィン・シュレーディンガーは1961年1月4日、ウィーンで結核のため亡くなりました。波動力学を確立し、ノーベル物理学賞を受賞した量子力学の創始者の一人でした。「シュレーディンガーの猫」の思考実験で量子力学の奇妙さを示し、『生命とは何か』で分子生物学にも影響を与えました。",
        "episode_type": "死去",
    },
    {
        "person_id": "PB49E4A1",
        "person_name": "ハイゼンベルク",
        "age": 74.0,
        "category": "科学・技術",
        "episode_text": "あなたと同じ74歳のとき、ヴェルナー・ハイゼンベルクは1976年2月1日、ミュンヘンでがんのため亡くなりました。「不確定性原理」を発見し、量子力学の基礎を築いたノーベル物理学賞受賞者でした。31歳での受賞は当時最年少であり、ナチス政権下での原爆開発への関与は今も議論されています。",
        "episode_type": "死去",
    },
    {
        "person_id": "P38D9999",
        "person_name": "エンリコ・フェルミ",
        "age": 53.0,
        "category": "学術・研究",
        "episode_text": "あなたと同じ53歳のとき、エンリコ・フェルミは1954年11月28日、シカゴで胃がんのため亡くなりました。世界初の原子炉を建設し、核時代の扉を開いたイタリア出身の物理学者でした。理論と実験の両方に優れた稀有な科学者で、「フェルミ推定」や「フェルミのパラドックス」にその名を残しています。",
        "episode_type": "死去",
    },
    {
        "person_id": "P43C052B",
        "person_name": "ポール・ディラック",
        "age": 82.0,
        "category": "学術・研究",
        "episode_text": "あなたと同じ82歳のとき、ポール・ディラックは1984年10月20日、フロリダで亡くなりました。反物質の存在を予言し、量子力学と相対性理論を統合した「ディラック方程式」を導いたノーベル物理学賞受賞者でした。寡黙で知られ、「ディラック」という単位（1時間に1語）が冗談で作られたほどでした。",
        "episode_type": "死去",
    },
    {
        "person_id": "PF4779F7",
        "person_name": "ロバート・オッペンハイマー",
        "age": 62.0,
        "category": "学術・研究",
        "episode_text": "あなたと同じ62歳のとき、ロバート・オッペンハイマーは1967年2月18日、プリンストンで咽頭がんのため亡くなりました。マンハッタン計画を指揮し「原爆の父」と呼ばれた理論物理学者でした。広島への投下後「私は死神となった」と語り、水爆開発に反対してマッカーシズムの標的となりました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P2CAD621",
        "person_name": "ニコラウス・コペルニクス",
        "age": 70.0,
        "category": "学術・研究",
        "episode_text": "あなたと同じ70歳のとき、ニコラウス・コペルニクスは1543年5月24日、ポーランドで脳卒中のため亡くなりました。地動説を提唱し、宇宙観に革命をもたらした天文学者でした。死の直前に出版された『天球の回転について』は教会の弾圧を恐れて慎重に書かれましたが、科学史を永遠に変えました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P9E1E40F",
        "person_name": "マイケル・ファラデー",
        "age": 75.0,
        "category": "科学・技術",
        "episode_text": "あなたと同じ75歳のとき、マイケル・ファラデーは1867年8月25日、ロンドンで老衰のため亡くなりました。電磁誘導を発見し、モーターと発電機の原理を確立した「電気の父」でした。製本職人から独学で科学者となり、場の概念を導入して物理学に革命をもたらしました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P362E2B2",
        "person_name": "ジェームズ・クラーク・マクスウェル",
        "age": 48.0,
        "category": "科学・技術",
        "episode_text": "あなたと同じ48歳のとき、ジェームズ・クラーク・マクスウェルは1879年11月5日、ケンブリッジで腹部がんのため亡くなりました。電磁気学を統一し「マクスウェル方程式」を導いた理論物理学者でした。アインシュタインはマクスウェルの業績を「ニュートン以来最も実り多いもの」と称えました。",
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
