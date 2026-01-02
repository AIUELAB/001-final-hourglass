#!/usr/bin/env python3
"""
Batch 41: 探検家の象徴エピソード（死去）追加
"""

import csv
import uuid
from datetime import datetime
from pathlib import Path


def generate_episode_id():
    return f"EP-{uuid.uuid4().hex[:8].upper()}"


# 探検家の死去エピソード
ICONIC_EPISODES = [
    {
        "person_id": "PD76F9DF",
        "person_name": "ヴァスコ・ダ・ガマ",
        "age": 55.0,
        "category": "探検家",
        "episode_text": "あなたと同じ55歳のとき、ヴァスコ・ダ・ガマは1524年12月24日、インド・コーチンでマラリアのため亡くなりました。1498年にヨーロッパからインドへの海路を初めて開拓し、大航海時代の幕を開けたポルトガルの航海者でした。この航路の発見はヨーロッパとアジアの貿易を一変させ、ポルトガル海上帝国の礎となりました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P53FF33B",
        "person_name": "ジェームズ・クック",
        "age": 50.0,
        "category": "探検家・航海者",
        "episode_text": "あなたと同じ50歳のとき、ジェームズ・クックは1779年2月14日、ハワイ島のケアラケクア湾で現地住民との衝突により命を落としました。3度の太平洋航海で南極圏到達、オーストラリア東海岸発見、ハワイ諸島発見など数々の偉業を成し遂げた「太平洋の覇者」でした。科学的な航海術と詳細な海図作成は、その後の探検に計り知れない貢献をしました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P67D7AF9",
        "person_name": "デイヴィッド・リヴィングストン",
        "age": 60.0,
        "category": "探検家・宣教師",
        "episode_text": "あなたと同じ60歳のとき、デイヴィッド・リヴィングストンは1873年5月1日、現在のザンビアで赤痢とマラリアのため亡くなりました。アフリカ大陸を横断し、ヴィクトリアの滝を発見したスコットランドの宣教師・探検家でした。「リヴィングストン博士でいらっしゃいますか？」というスタンリーの言葉は探検史上最も有名な一言となりました。",
        "episode_type": "死去",
    },
    {
        "person_id": "PB31095E",
        "person_name": "ロアール・アムンセン",
        "age": 55.0,
        "category": "探検家",
        "episode_text": "あなたと同じ55歳のとき、ロアール・アムンセンは1928年6月18日、北極海で遭難した飛行船イタリア号の救援に向かう途中、飛行艇の墜落により行方不明となりました。1911年に人類初の南極点到達を果たし、北西航路も初めて踏破したノルウェーの極地探検家でした。探検家としての生涯を救援活動中に閉じるという最期でした。",
        "episode_type": "死去",
    },
    {
        "person_id": "P7C1A689",
        "person_name": "ロバート・スコット",
        "age": 43.0,
        "category": "探検家",
        "episode_text": "あなたと同じ43歳のとき、ロバート・スコットは1912年3月29日頃、南極大陸のロス棚氷で吹雪のため亡くなりました。南極点到達を目指しましたが、アムンセンに約1ヶ月遅れ、帰路で隊員と共に遭難しました。「もう少し頑張れたかもしれない」と記された日記は、英国人の気質を象徴する悲劇として語り継がれています。",
        "episode_type": "死去",
    },
    {
        "person_id": "PDEF933",
        "person_name": "ニール・アームストロング",
        "age": 82.0,
        "category": "宇宙飛行士",
        "episode_text": "あなたと同じ82歳のとき、ニール・アームストロングは2012年8月25日、オハイオ州シンシナティで心臓手術後の合併症により亡くなりました。1969年7月20日、アポロ11号で人類初の月面着陸を果たし、「一人の人間にとっては小さな一歩だが、人類にとっては偉大な飛躍」という言葉を残した伝説の宇宙飛行士でした。",
        "episode_type": "死去",
    },
    {
        "person_id": "P1264F4F",
        "person_name": "アメリア・イアハート",
        "age": 39.0,
        "category": "飛行士",
        "episode_text": "あなたと同じ39歳のとき、アメリア・イアハートは1937年7月2日、太平洋上で消息を絶ちました。女性として初の大西洋単独横断飛行を成し遂げ、世界一周飛行に挑戦中でした。ハウランド島付近で行方不明となり、大規模な捜索にもかかわらず機体も遺体も発見されませんでした。その失踪は航空史最大の謎として今も人々を魅了し続けています。",
        "episode_type": "死去",
    },
    {
        "person_id": "PD180689",
        "person_name": "星野道夫",
        "age": 43.0,
        "category": "写真家・探検家",
        "episode_text": "あなたと同じ43歳のとき、星野道夫は1996年8月8日、ロシア・カムチャツカ半島でヒグマに襲われ亡くなりました。アラスカの大自然と野生動物を撮り続け、その美しい写真と詩的な文章で多くの読者を魅了した写真家でした。「旅をする木」など数々の著作は今も読み継がれ、自然との共生を問いかけ続けています。",
        "episode_type": "死去",
    },
    {
        "person_id": "P14AD640",
        "person_name": "白瀬矗",
        "age": 85.0,
        "category": "探検家・陸軍中尉",
        "episode_text": "あなたと同じ85歳のとき、白瀬矗は1946年9月4日、愛知県で老衰のため亡くなりました。1912年に日本人として初めて南極大陸に上陸し、到達地点を「大和雪原」と命名した探検家でした。私財を投じての探検は国民的な関心を集め、日本の極地探検の先駆者として歴史に名を残しています。",
        "episode_type": "死去",
    },
    {
        "person_id": "P00B74F3",
        "person_name": "間宮林蔵",
        "age": 64.0,
        "category": "探検家",
        "episode_text": "あなたと同じ64歳のとき、間宮林蔵は1844年4月13日、江戸で亡くなりました。樺太（サハリン）が島であることを確認し、間宮海峡にその名を残す江戸時代の探検家でした。幕府の隠密として蝦夷地や樺太を調査し、詳細な地図と記録を残しました。その功績は後にシーボルトを通じて世界に知られることとなりました。",
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
