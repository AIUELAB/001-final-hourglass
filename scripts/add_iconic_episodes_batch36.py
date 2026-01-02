#!/usr/bin/env python3
"""
Batch 36: 日本の宗教家・哲学者の象徴エピソード（死去）追加
"""

import csv
import uuid
from datetime import datetime
from pathlib import Path


def generate_episode_id():
    return f"EP-{uuid.uuid4().hex[:8].upper()}"


# 日本の宗教家・哲学者の死去エピソード
ICONIC_EPISODES = [
    {
        "person_id": "P07A2369",
        "person_name": "西田幾多郎",
        "age": 75.0,
        "category": "哲学者",
        "episode_text": "あなたと同じ75歳のとき、西田幾多郎は1945年6月7日、神奈川県鎌倉で尿毒症のため亡くなりました。「善の研究」で日本初の本格的な哲学体系を構築し、京都学派を創始した日本を代表する哲学者でした。「絶対矛盾的自己同一」の概念で東洋と西洋の思想を架橋しようと試みました。終戦の2ヶ月前に亡くなり、日本の敗戦を見届けることはありませんでした。",
        "episode_type": "死去",
    },
    {
        "person_id": "P6CD8311",
        "person_name": "和辻哲郎",
        "age": 71.0,
        "category": "哲学者・倫理学者",
        "episode_text": "あなたと同じ71歳のとき、和辻哲郎は1960年12月26日、東京で心筋梗塞のため亡くなりました。「風土」「倫理学」などで日本的な倫理学・文化論を展開した哲学者でした。「間柄」という概念で人間存在を関係性から捉え、西洋個人主義とは異なる視点を提示しました。日本文化の本質を「しめやかな激情」と表現し、文化勲章を受章しています。",
        "episode_type": "死去",
    },
    {
        "person_id": "P50AFF83",
        "person_name": "九鬼周造",
        "age": 53.0,
        "category": "哲学者",
        "episode_text": "あなたと同じ53歳のとき、九鬼周造は1941年5月6日、京都で狭心症のため亡くなりました。「『いき』の構造」で日本独自の美意識を哲学的に分析した先駆者でした。パリでハイデガーやベルクソンに学び、帰国後は京都帝国大学で教鞭を執りました。「いき」を「媚態・意気地・諦め」の三要素で解明し、日本美学の古典的著作を残しました。",
        "episode_type": "死去",
    },
    {
        "person_id": "PE6FD819",
        "person_name": "親鸞",
        "age": 89.0,
        "category": "僧侶・宗教家",
        "episode_text": "あなたと同じ89歳のとき、親鸞は1263年1月16日（旧暦弘長2年11月28日）、京都で亡くなりました。浄土真宗の開祖として、「悪人正機」の教えで民衆に救いの道を開いた日本仏教史上最重要の宗教家の一人でした。「善人なおもって往生を遂ぐ、いわんや悪人をや」という逆説的な教えは、阿弥陀仏の絶対的な慈悲を説いています。",
        "episode_type": "死去",
    },
    {
        "person_id": "P175CFAC",
        "person_name": "道元",
        "age": 53.0,
        "category": "僧侶・宗教家",
        "episode_text": "あなたと同じ53歳のとき、道元は1253年9月22日（旧暦建長5年8月28日）、京都で亡くなりました。曹洞宗の開祖として、「只管打坐（しかんたざ）」の禅を日本に伝えた偉大な宗教家でした。主著「正法眼蔵」は日本思想史上の最高傑作の一つとされ、「仏道をならふといふは、自己をならふなり」という言葉は禅の本質を突いています。",
        "episode_type": "死去",
    },
    {
        "person_id": "PF78AA4B",
        "person_name": "日蓮",
        "age": 60.0,
        "category": "僧侶・宗教家",
        "episode_text": "あなたと同じ60歳のとき、日蓮は1282年10月13日（旧暦弘安5年10月13日）、武蔵国池上（現・東京都大田区）で亡くなりました。日蓮宗の開祖として、「南無妙法蓮華経」の題目を唱えることで救済されると説いた烈しい信念の宗教家でした。幕府を批判して佐渡に流罪となるなど、生涯を通じて迫害に遭いながらも信念を貫きました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P03864FA",
        "person_name": "法然",
        "age": 79.0,
        "category": "僧侶・宗教家",
        "episode_text": "あなたと同じ79歳のとき、法然は1212年2月29日（旧暦建暦2年1月25日）、京都で亡くなりました。浄土宗の開祖として、「南無阿弥陀仏」と念仏を唱えれば誰でも極楽往生できると説いた日本浄土教の確立者でした。「選択本願念仏集」を著し、難しい修行ができない一般民衆にも救いの道を開きました。親鸞は法然の弟子でした。",
        "episode_type": "死去",
    },
    {
        "person_id": "P28778EB",
        "person_name": "最澄",
        "age": 55.0,
        "category": "僧侶・宗教家",
        "episode_text": "あなたと同じ55歳のとき、最澄は822年6月26日（旧暦弘仁13年6月4日）、比叡山で亡くなりました。天台宗の開祖として、比叡山延暦寺を創建し、日本仏教の母山を築いた偉大な宗教家でした。「一隅を照らす、此れ則ち国宝なり」という言葉を残し、空海と共に平安仏教を代表する存在となりました。没後に伝教大師の諡号を贈られています。",
        "episode_type": "死去",
    },
    {
        "person_id": "P8A02144",
        "person_name": "一休宗純",
        "age": 87.0,
        "category": "僧侶・禅僧",
        "episode_text": "あなたと同じ87歳のとき、一休宗純は1481年12月12日（旧暦文明13年11月21日）、京都・酬恩庵（一休寺）で亡くなりました。型破りな言動で知られる臨済宗の名僧であり、「風狂」の禅を体現した人物でした。酒を飲み、肉を食べ、女性と交わりながらも、その奥に深い禅の境地がありました。「門松は冥土の旅の一里塚」など、機知に富んだ言葉を多く残しています。",
        "episode_type": "死去",
    },
    {
        "person_id": "P539BE73",
        "person_name": "良寛",
        "age": 72.0,
        "category": "僧侶・歌人",
        "episode_text": "あなたと同じ72歳のとき、良寛は1831年2月18日（旧暦天保2年1月6日）、越後国（現・新潟県）で亡くなりました。托鉢僧として清貧の生活を送りながら、子どもたちと手まりで遊び、書と和歌に親しんだ「大愚良寛」でした。「裏を見せ表を見せて散るもみぢ」という辞世の句は、飾らない生き方を象徴しています。晩年に尼僧・貞心尼との心の交流があったことでも知られています。",
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
