#!/usr/bin/env python3
"""
Batch 29: 経済学者・社会学者の象徴エピソード（死去）追加
"""

import csv
import uuid
from datetime import datetime
from pathlib import Path


def generate_episode_id():
    return f"EP-{uuid.uuid4().hex[:8].upper()}"


# 経済学者・社会学者の死去エピソード（存命者除外）
ICONIC_EPISODES = [
    {
        "person_id": "PC31A4BC",
        "person_name": "アダム・スミス",
        "age": 67.0,
        "category": "経済学者・哲学者",
        "episode_text": "あなたと同じ67歳のとき、アダム・スミスは1790年7月17日、スコットランド・エディンバラで亡くなりました。「国富論」で自由市場経済の理論的基盤を築き、「経済学の父」と称される思想家でした。「見えざる手」の概念は資本主義経済の根幹をなす考え方となりました。道徳哲学者としても「道徳感情論」を著し、人間の共感能力についての洞察を残しています。",
        "episode_type": "死去",
    },
    {
        "person_id": "PCAE4108",
        "person_name": "ジョン・メイナード・ケインズ",
        "age": 62.0,
        "category": "経済学者",
        "episode_text": "あなたと同じ62歳のとき、ジョン・メイナード・ケインズは1946年4月21日、心臓発作のためイギリス・サセックスで亡くなりました。「雇用・利子および貨幣の一般理論」で経済学に革命をもたらし、政府の積極的な経済介入を理論化した20世紀最大の経済学者でした。大恐慌後の世界経済の回復に理論的指針を与え、戦後の国際通貨体制（ブレトンウッズ体制）の設計にも深く関わりました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P58A3909",
        "person_name": "ミルトン・フリードマン",
        "age": 94.0,
        "category": "経済学者",
        "episode_text": "あなたと同じ94歳のとき、ミルトン・フリードマンは2006年11月16日、心不全のためカリフォルニア州サンフランシスコで亡くなりました。「選択の自由」を掲げ、市場原理主義と小さな政府を提唱したシカゴ学派の巨頭でした。1976年にノーベル経済学賞を受賞。マネタリズムの理論家として、レーガン政権やサッチャー政権の経済政策に大きな影響を与えました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P4615DFF",
        "person_name": "フリードリヒ・ハイエク",
        "age": 92.0,
        "category": "経済学者・哲学者",
        "episode_text": "あなたと同じ92歳のとき、フリードリヒ・ハイエクは1992年3月23日、ドイツ・フライブルクで亡くなりました。「隷従への道」で社会主義計画経済を批判し、自由主義経済思想の復興に貢献した思想家でした。1974年にノーベル経済学賞を受賞。自生的秩序の概念を発展させ、政府の介入を最小限にすべきという主張は新自由主義の理論的基盤となりました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P532CE94",
        "person_name": "ドラッカー",
        "age": 95.0,
        "category": "経営学者",
        "episode_text": "あなたと同じ95歳のとき、ピーター・ドラッカーは2005年11月11日、カリフォルニア州クレアモントの自宅で老衰のため亡くなりました。「マネジメントの父」として、現代経営学を確立した巨人でした。「マネジメント」「プロフェッショナルの条件」など数多くの著作で、知識労働者の時代の到来を予見。「企業の目的は顧客の創造である」という言葉は経営の本質を突いた名言として知られています。",
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
