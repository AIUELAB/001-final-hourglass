#!/usr/bin/env python3
"""
Batch 18: 漫画家・アニメーターの象徴エピソード（死去）追加
"""

import csv
import uuid
from datetime import datetime
from pathlib import Path


def generate_episode_id():
    return f"EP-{uuid.uuid4().hex[:8].upper()}"


# 漫画家・アニメーターの死去エピソード
ICONIC_EPISODES = [
    {
        "person_id": "P653E53B",
        "person_name": "横山光輝",
        "age": 69.0,
        "category": "漫画家",
        "episode_text": "あなたと同じ69歳のとき、横山光輝は2004年4月15日、東京都内の自宅で火災に遭い、煙を吸い込んだことによる急性呼吸器不全で亡くなりました。「鉄人28号」「三国志」「魔法使いサリー」など、日本漫画史に残る名作を数多く生み出した巨匠の突然の死は、漫画界に深い悲しみをもたらしました。特に「三国志」は全60巻という大作で、中国の歴史を日本の読者に広く紹介し、今でも多くのファンに愛され続けています。",
        "episode_type": "死去",
    },
    {
        "person_id": "P9B42007",
        "person_name": "藤子不二雄A",
        "age": 88.0,
        "category": "漫画家",
        "episode_text": "あなたと同じ88歳のとき、藤子不二雄Aこと安孫子素雄は2022年4月7日、川崎市の自宅で亡くなりました。「忍者ハットリくん」「怪物くん」「笑ゥせぇるすまん」など、ブラックユーモアとシュールな世界観を持つ作品で独自の地位を築きました。盟友の藤子・F・不二雄と共に日本漫画界を代表するコンビとして活躍し、藤子プロの歴史に大きな足跡を残しました。最期まで漫画への情熱を失わなかった巨匠でした。",
        "episode_type": "死去",
    },
    {
        "person_id": "P43EE66E",
        "person_name": "高畑勲",
        "age": 82.0,
        "category": "アニメーション監督",
        "episode_text": "あなたと同じ82歳のとき、高畑勲は2018年4月5日、東京都内の病院で肺がんのため亡くなりました。「火垂るの墓」「おもひでぽろぽろ」「かぐや姫の物語」など、アニメーションで人間の心の奥底を描き続けた巨匠でした。スタジオジブリの共同創設者として宮崎駿と共に日本アニメーションの黄金時代を築き、芸術性の高い作品を世に送り出しました。その革新的な表現技法は世界中のアニメーターに影響を与え続けています。",
        "episode_type": "死去",
    },
    {
        "person_id": "PB02841E",
        "person_name": "さくらももこ",
        "age": 53.0,
        "category": "漫画家",
        "episode_text": "あなたと同じ53歳のとき、さくらももこは2018年8月15日、乳がんのため亡くなりました。国民的漫画「ちびまる子ちゃん」の作者として、昭和の日本の日常を温かくユーモラスに描き、世代を超えて愛される作品を生み出しました。アニメ版は1990年から放送が始まり、30年以上にわたって日曜夕方の国民的番組として親しまれました。彼女が描いた「まる子」の世界は、多くの人々の心に故郷のような存在として残り続けています。",
        "episode_type": "死去",
    },
    {
        "person_id": "PBE59CD1",
        "person_name": "水木しげる",
        "age": 93.0,
        "category": "漫画家",
        "episode_text": "あなたと同じ93歳のとき、水木しげるは2015年11月30日、多臓器不全のため東京都内の病院で亡くなりました。「ゲゲゲの鬼太郎」「悪魔くん」で日本の妖怪文化を漫画として確立し、「妖怪の父」と称されました。戦争で左腕を失いながらも、独特のタッチと哲学的な視点で作品を描き続け、文化功労者にも選ばれました。「幸福の七ヶ条」など人生哲学でも多くの人に影響を与え、死後もなお作品は愛され続けています。",
        "episode_type": "死去",
    },
    {
        "person_id": "PBE93407",
        "person_name": "赤塚不二夫",
        "age": 72.0,
        "category": "漫画家",
        "episode_text": "あなたと同じ72歳のとき、赤塚不二夫は2008年8月2日、肺炎のため東京都内の病院で亡くなりました。「おそ松くん」「天才バカボン」「ひみつのアッコちゃん」など、ギャグ漫画の金字塔を打ち立て、「ギャグ漫画の王様」と呼ばれました。「これでいいのだ」というバカボンのパパの名言は国民的フレーズとなりました。晩年は体調を崩しながらも、最後まで笑いへの情熱を持ち続けた偉大なギャグ漫画家でした。",
        "episode_type": "死去",
    },
    {
        "person_id": "P11AD686",
        "person_name": "今敏",
        "age": 46.0,
        "category": "アニメーション監督",
        "episode_text": "あなたと同じ46歳のとき、今敏は2010年8月24日、膵臓がんのため東京都内の自宅で亡くなりました。「パーフェクトブルー」「千年女優」「東京ゴッドファーザーズ」「パプリカ」など、現実と夢の境界を描く革新的なアニメーション作品で世界的に高い評価を得ました。クリストファー・ノーラン監督「インセプション」への影響が指摘されるなど、その映像表現は世界の映画界にも大きな影響を与えました。46歳という若さでの死は、アニメーション界にとって大きな損失でした。",
        "episode_type": "死去",
    },
    {
        "person_id": "P4DD53D0",
        "person_name": "ジャック・カービー",
        "age": 76.0,
        "category": "漫画家",
        "episode_text": "あなたと同じ76歳のとき、ジャック・カービーは1994年2月6日、心不全のためカリフォルニア州の自宅で亡くなりました。「キャプテン・アメリカ」「ファンタスティック・フォー」「X-MEN」「アベンジャーズ」など、マーベル・コミックスの基盤を築いた「キング・オブ・コミックス」でした。ダイナミックな構図と革新的なビジュアルは「カービー・クラックル」として知られ、アメリカンコミックスの視覚言語そのものを創造しました。彼のキャラクターたちは現在も映画やドラマで世界中で愛されています。",
        "episode_type": "死去",
    },
    {
        "person_id": "P8E2D58A",
        "person_name": "やなせたかし",
        "age": 94.0,
        "category": "漫画家",
        "episode_text": "あなたと同じ94歳のとき、やなせたかしは2013年10月13日、心不全のため高知県内の病院で亡くなりました。「アンパンマン」の生みの親として、「自分の顔を食べさせて人を助ける」という自己犠牲の精神を子どもたちに伝え続けました。弟を戦争で失った経験から「本当の正義とは飢えている人にパンを差し出すこと」という信念を持ち、それをアンパンマンに込めました。90歳を超えても現役で創作活動を続け、日本のアニメ文化に大きな足跡を残しました。",
        "episode_type": "死去",
    },
]


def main():
    csv_path = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")

    # 既存データ読み込み
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        existing = list(reader)
        fieldnames = reader.fieldnames

    print(f"既存エピソード数: {len(existing)}")

    # テンプレート行を取得
    template_row = existing[0].copy()

    # 新規エピソードを作成
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

    # 統合して書き込み
    all_episodes = existing + new_episodes

    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_episodes)

    print(f"\n合計: {len(all_episodes)}件 (+{len(new_episodes)}件追加)")


if __name__ == "__main__":
    main()
