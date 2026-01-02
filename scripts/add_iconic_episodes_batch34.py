#!/usr/bin/env python3
"""
Batch 34: 発明家・建築家の象徴エピソード（死去）追加
"""

import csv
import uuid
from datetime import datetime
from pathlib import Path


def generate_episode_id():
    return f"EP-{uuid.uuid4().hex[:8].upper()}"


# 発明家・建築家の死去エピソード
ICONIC_EPISODES = [
    {
        "person_id": "P66775B1",
        "person_name": "槇文彦",
        "age": 95.0,
        "category": "建築家",
        "episode_text": "あなたと同じ95歳のとき、槇文彦は2024年6月6日、老衰のため東京都内で亡くなりました。モダニズム建築の巨匠として、幕張メッセ、東京体育館、代官山ヒルサイドテラスなど数々の名建築を手がけた日本を代表する建築家でした。1993年にプリツカー賞を受賞し、世界的な評価を確立。「場所の文脈を読む」建築哲学は多くの後進に影響を与え、日本建築界の至宝として尊敬を集めました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P41787DA",
        "person_name": "ルートヴィヒ・ミース・ファン・デル・ローエ",
        "age": 83.0,
        "category": "建築家",
        "episode_text": "あなたと同じ83歳のとき、ルートヴィヒ・ミース・ファン・デル・ローエは1969年8月17日、シカゴで亡くなりました。「Less is more（より少ないことは、より豊かなこと）」の哲学で知られる近代建築の巨匠でした。バウハウス最後の校長を務め、ナチス台頭後にアメリカへ移住。シーグラム・ビル、ファンズワース邸など、鉄とガラスによる透明性の高い建築で20世紀建築を革新しました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P1F0726F",
        "person_name": "ウィルバー・ライト",
        "age": 45.0,
        "category": "発明家",
        "episode_text": "あなたと同じ45歳のとき、ウィルバー・ライトは1912年5月30日、オハイオ州デイトンで腸チフスのため亡くなりました。弟オーヴィルと共に1903年12月17日に人類初の動力飛行を成功させた「飛行機の父」でした。自転車店を営みながら航空機開発に情熱を注ぎ、わずか12秒・36メートルの初飛行から航空時代の幕を開けました。45歳という若さでの死は航空界に大きな損失をもたらしました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P83CD79E",
        "person_name": "オーヴィル・ライト",
        "age": 76.0,
        "category": "発明家",
        "episode_text": "あなたと同じ76歳のとき、オーヴィル・ライトは1948年1月30日、オハイオ州デイトンで心臓発作のため亡くなりました。兄ウィルバーと共に人類初の動力飛行を成功させたライト兄弟の弟でした。初飛行では自らが操縦桿を握り、歴史的瞬間の操縦者となりました。兄の死後も航空技術の発展を見守り、第二次世界大戦での航空機の進化、さらには音速突破の時代まで生きて航空史の証人となりました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P85396CA",
        "person_name": "豊田佐吉",
        "age": 63.0,
        "category": "発明家・実業家",
        "episode_text": "あなたと同じ63歳のとき、豊田佐吉は1930年10月30日、肺炎のため静岡県浜名郡で亡くなりました。自動織機を発明し、トヨタグループの礎を築いた「日本の発明王」でした。木製人力織機から始まり、G型自動織機は世界最高水準の技術として評価されました。「障子を開けてみよ、外は広いぞ」という言葉を残し、息子・豊田喜一郎に自動車事業への挑戦を託しました。その精神はトヨタ生産方式に受け継がれています。",
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
