#!/usr/bin/env python3
"""
Batch 40: 王族・皇室の象徴エピソード（死去）追加
"""

import csv
import uuid
from datetime import datetime
from pathlib import Path


def generate_episode_id():
    return f"EP-{uuid.uuid4().hex[:8].upper()}"


# 王族・皇室の死去エピソード
ICONIC_EPISODES = [
    {
        "person_id": "P06C7670",
        "person_name": "明治天皇",
        "age": 59.0,
        "category": "皇室",
        "episode_text": "あなたと同じ59歳のとき、明治天皇は1912年7月30日、東京の皇居で尿毒症のため崩御されました。明治維新から45年間にわたり日本の近代化を見守り、大日本帝国憲法の発布、日清・日露戦争の勝利など、日本が列強の仲間入りを果たす激動の時代を象徴する存在でした。崩御に際しては乃木希典大将が殉死し、一つの時代の終わりを告げました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P89609D6",
        "person_name": "大正天皇",
        "age": 47.0,
        "category": "皇室",
        "episode_text": "あなたと同じ47歳のとき、大正天皇は1926年12月25日、神奈川県葉山の御用邸で心臓麻痺のため崩御されました。生来の病弱から公務の負担が重く、晩年は摂政を置くこととなりましたが、大正デモクラシーの時代を象徴する存在でした。文学や芸術を愛し、国民に親しまれる皇室像の礎を築きました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P97AF510",
        "person_name": "昭和天皇",
        "age": 87.0,
        "category": "皇室",
        "episode_text": "あなたと同じ87歳のとき、昭和天皇は1989年1月7日、東京の皇居で十二指腸癌のため崩御されました。62年余りの在位は日本史上最長であり、第二次世界大戦の終結を告げる玉音放送、戦後復興、高度経済成長と、激動の昭和を象徴する存在でした。「堪え難きを堪え、忍び難きを忍び」の言葉は日本人の心に深く刻まれています。",
        "episode_type": "死去",
    },
    {
        "person_id": "PBE355C2",
        "person_name": "香淳皇后",
        "age": 97.0,
        "category": "皇室",
        "episode_text": "あなたと同じ97歳のとき、香淳皇后は2000年6月16日、東京の皇居・吹上大宮御所で老衰のため崩御されました。昭和天皇の皇后として戦前・戦中・戦後を生き抜き、日本の皇室を支え続けた存在でした。戦後は積極的に福祉活動に取り組み、国民から「良子さま」と親しまれました。",
        "episode_type": "死去",
    },
    {
        "person_id": "PD730316",
        "person_name": "三笠宮崇仁",
        "age": 100.0,
        "category": "皇室",
        "episode_text": "あなたと同じ100歳のとき、三笠宮崇仁親王は2016年10月27日、東京の病院で心不全のため薨去されました。大正天皇の第四皇子として生まれ、皇族でありながらオリエント史の研究者として学術界でも活躍されました。戦時中の軍人としての経験から平和を願い、100歳まで生きられた皇族として多くの国民に敬愛されました。",
        "episode_type": "死去",
    },
    {
        "person_id": "PBE44B57",
        "person_name": "高松宮宣仁親王",
        "age": 82.0,
        "category": "皇室",
        "episode_text": "あなたと同じ82歳のとき、高松宮宣仁親王は1987年2月3日、東京の病院で肺癌のため薨去されました。大正天皇の第三皇子として海軍軍人の道を歩み、終戦時には和平工作にも関わりました。戦後はスポーツ振興に尽力し、「スポーツの宮様」として親しまれました。高松宮殿下記念世界文化賞は今も続いています。",
        "episode_type": "死去",
    },
    {
        "person_id": "P8B4B9CA",
        "person_name": "エリザベス1世",
        "age": 69.0,
        "category": "女王",
        "episode_text": "あなたと同じ69歳のとき、エリザベス1世は1603年3月24日、イングランド・リッチモンド宮殿で亡くなりました。「処女王」として45年間イングランドを統治し、スペイン無敵艦隊を撃破、シェイクスピア文学が花開く黄金時代を築いた「グロリアーナ（栄光の女王）」でした。結婚せず後継者を指名しなかったため、テューダー朝は終焉を迎えました。",
        "episode_type": "死去",
    },
    {
        "person_id": "PD1276D6",
        "person_name": "ヴィクトリア女王",
        "age": 81.0,
        "category": "女王",
        "episode_text": "あなたと同じ81歳のとき、ヴィクトリア女王は1901年1月22日、イギリス・ワイト島のオズボーン・ハウスで亡くなりました。63年7ヶ月の在位は当時の英国史上最長であり、大英帝国の最盛期「ヴィクトリア朝」を象徴する存在でした。「ヨーロッパの祖母」と呼ばれるほど多くの王族と血縁関係を持ち、その影響は今日の欧州王室にまで及んでいます。",
        "episode_type": "死去",
    },
    {
        "person_id": "P52366A0",
        "person_name": "ルイ14世",
        "age": 76.0,
        "category": "国王",
        "episode_text": "あなたと同じ76歳のとき、ルイ14世は1715年9月1日、フランス・ヴェルサイユ宮殿で壊疽のため亡くなりました。「太陽王」として72年間フランスに君臨し、絶対王政の頂点を極めた史上最も長く在位した君主でした。ヴェルサイユ宮殿を建設し、芸術と文化の黄金時代を築きましたが、度重なる戦争と贅沢は後の財政危機の遠因となりました。",
        "episode_type": "死去",
    },
    {
        "person_id": "PA87E849",
        "person_name": "ルイ16世",
        "age": 38.0,
        "category": "国王",
        "episode_text": "あなたと同じ38歳のとき、ルイ16世は1793年1月21日、パリのコンコルド広場でギロチンにより処刑されました。フランス革命により王政が倒され、「ルイ・カペー」として市民として裁かれた最後のフランス国王でした。善良な性格で国民を愛しましたが、時代の激流に抗うことができませんでした。最後の言葉は「私は無実のまま死ぬ」とされています。",
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
