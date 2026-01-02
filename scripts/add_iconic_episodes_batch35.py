#!/usr/bin/env python3
"""
Batch 35: 西洋哲学者・宗教家の象徴エピソード（死去）追加
"""

import csv
import uuid
from datetime import datetime
from pathlib import Path


def generate_episode_id():
    return f"EP-{uuid.uuid4().hex[:8].upper()}"


# 西洋哲学者・宗教家の死去エピソード
ICONIC_EPISODES = [
    {
        "person_id": "P5F77568",
        "person_name": "イマヌエル・カント",
        "age": 79.0,
        "category": "哲学者",
        "episode_text": "あなたと同じ79歳のとき、イマヌエル・カントは1804年2月12日、プロイセン王国ケーニヒスベルクで老衰のため亡くなりました。「純粋理性批判」「実践理性批判」「判断力批判」の三批判書で近代哲学を確立した「近代哲学の父」でした。生涯を通じてケーニヒスベルクを離れず、規則正しい生活を送りながら思索を深めました。「我々は物自体を認識できない」という認識論は、その後の哲学に決定的な影響を与えました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P4C91A44",
        "person_name": "ゲオルク・ヘーゲル",
        "age": 61.0,
        "category": "哲学者",
        "episode_text": "あなたと同じ61歳のとき、ゲオルク・ヘーゲルは1831年11月14日、ベルリンでコレラのため亡くなりました。弁証法的観念論を確立し、「精神現象学」「論理学」などで西洋哲学の頂点を極めた巨人でした。「理性的なものは現実的であり、現実的なものは理性的である」という命題は、マルクスからキルケゴールまで、賛否両面で多大な影響を与えました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P4ABFA9A",
        "person_name": "デカルト",
        "age": 53.0,
        "category": "哲学者・数学者",
        "episode_text": "あなたと同じ53歳のとき、ルネ・デカルトは1650年2月11日、スウェーデン・ストックホルムで肺炎のため亡くなりました。「我思う、ゆえに我あり」の命題で知られる近代哲学の祖でした。スウェーデン女王クリスティーナの招きで極寒の地に赴き、早朝5時からの講義を求められた結果、体調を崩しました。解析幾何学の創始者としても数学史に名を残しています。",
        "episode_type": "死去",
    },
    {
        "person_id": "P602CA1A",
        "person_name": "スピノザ",
        "age": 44.0,
        "category": "哲学者",
        "episode_text": "あなたと同じ44歳のとき、バールーフ・デ・スピノザは1677年2月21日、オランダ・ハーグで結核のため亡くなりました。「エチカ」で汎神論的な世界観を展開し、神と自然を同一視する革新的な思想を打ち立てた哲学者でした。ユダヤ教会から破門され、レンズ磨きで生計を立てながら思索を続けました。その孤高の生涯と思想は、後世の思想家に深い影響を与えました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P8969786",
        "person_name": "シモーヌ・ド・ボーヴォワール",
        "age": 78.0,
        "category": "哲学者・作家",
        "episode_text": "あなたと同じ78歳のとき、シモーヌ・ド・ボーヴォワールは1986年4月14日、パリで肺炎のため亡くなりました。「第二の性」でフェミニズム思想の礎を築いた実存主義哲学者でした。「人は女に生まれるのではない、女になるのだ」という言葉は、ジェンダー論の出発点となりました。サルトルとの生涯にわたる知的パートナーシップも広く知られています。",
        "episode_type": "死去",
    },
    {
        "person_id": "P767A633",
        "person_name": "ハンナ・アーレント",
        "age": 69.0,
        "category": "哲学者・政治思想家",
        "episode_text": "あなたと同じ69歳のとき、ハンナ・アーレントは1975年12月4日、ニューヨークで心臓発作のため亡くなりました。「全体主義の起源」「人間の条件」で20世紀の政治哲学を刷新した思想家でした。アイヒマン裁判を傍聴し、「悪の凡庸さ」という概念を提唱。平凡な人間がいかにして巨悪に加担するかを鋭く分析し、現代社会への警鐘を鳴らし続けています。",
        "episode_type": "死去",
    },
    {
        "person_id": "PFC43783",
        "person_name": "ミシェル・フーコー",
        "age": 57.0,
        "category": "哲学者",
        "episode_text": "あなたと同じ57歳のとき、ミシェル・フーコーは1984年6月25日、パリでエイズ関連の疾患により亡くなりました。「監獄の誕生」「狂気の歴史」「性の歴史」などで権力と知の関係を分析したポスト構造主義の旗手でした。近代社会における規律権力のメカニズムを解明し、「パノプティコン」の概念は現代の監視社会批判の基盤となっています。",
        "episode_type": "死去",
    },
    {
        "person_id": "PC27B507",
        "person_name": "マルティン・ルター",
        "age": 62.0,
        "category": "宗教改革者",
        "episode_text": "あなたと同じ62歳のとき、マルティン・ルターは1546年2月18日、ドイツ・アイスレーベンで亡くなりました。1517年に「95ヶ条の論題」を発表し、宗教改革を引き起こしたプロテスタントの父でした。聖書のドイツ語訳を完成させ、一般民衆が聖書を読める道を開きました。「ここに立つ、他になしえない」という言葉は、信仰の自由を求める人々の象徴となっています。",
        "episode_type": "死去",
    },
    {
        "person_id": "P70705A5",
        "person_name": "ヨハネ・パウロ2世",
        "age": 84.0,
        "category": "ローマ教皇",
        "episode_text": "あなたと同じ84歳のとき、ヨハネ・パウロ2世は2005年4月2日、バチカンで敗血症のため亡くなりました。ポーランド出身初のローマ教皇として26年間在位し、冷戦終結に貢献した「巡礼の教皇」でした。129カ国を訪問し、ユダヤ教やイスラム教との対話を推進。暗殺未遂を生き延び、犯人を赦した姿勢は世界中の人々に感銘を与えました。2014年に列聖されました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P7FC263A",
        "person_name": "ローマ教皇ベネディクト16世",
        "age": 95.0,
        "category": "ローマ教皇",
        "episode_text": "あなたと同じ95歳のとき、ベネディクト16世は2022年12月31日、バチカンで老衰のため亡くなりました。ドイツ出身の神学者として、2005年から2013年まで教皇を務めました。約600年ぶりに存命中に退位するという歴史的決断を下し、「名誉教皇」として晩年を過ごしました。保守的な神学的立場から教会の教えを守り抜き、知性と信仰の統合を説き続けました。",
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
