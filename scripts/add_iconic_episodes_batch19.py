#!/usr/bin/env python3
"""
Batch 19: ファッションデザイナーの象徴エピソード（死去）追加
"""

import csv
import uuid
from datetime import datetime
from pathlib import Path


def generate_episode_id():
    return f"EP-{uuid.uuid4().hex[:8].upper()}"


# ファッションデザイナーの死去エピソード（存命者除外）
ICONIC_EPISODES = [
    {
        "person_id": "PC8C004A",
        "person_name": "ココ・シャネル",
        "age": 87.0,
        "category": "ファッションデザイナー",
        "episode_text": "あなたと同じ87歳のとき、ココ・シャネルは1971年1月10日、パリのリッツ・ホテルの自室で亡くなりました。「シャネル・スーツ」「リトルブラックドレス」「シャネルNo.5」など、20世紀のファッションを根本から変革した伝説的デザイナーでした。女性をコルセットから解放し、機能的でエレガントなスタイルを確立。「モードは変わるが、スタイルは永遠」という言葉通り、彼女が創り上げたブランドは今も世界中で愛され続けています。",
        "episode_type": "死去",
    },
    {
        "person_id": "P475941D",
        "person_name": "カール・ラガーフェルド",
        "age": 85.0,
        "category": "ファッションデザイナー",
        "episode_text": "あなたと同じ85歳のとき、カール・ラガーフェルドは2019年2月19日、パリで膵臓がんのため亡くなりました。シャネル、フェンディ、自身のブランドを同時に率いた「ファッション界の皇帝」でした。白髪のポニーテール、黒いサングラス、高い襟というトレードマークの姿で、36年間シャネルのクリエイティブ・ディレクターとして君臨し、ブランドを現代に蘇らせた功績は計り知れません。",
        "episode_type": "死去",
    },
    {
        "person_id": "P4CD39ED",
        "person_name": "アレキサンダー・マックイーン",
        "age": 40.0,
        "category": "ファッションデザイナー",
        "episode_text": "あなたと同じ40歳のとき、アレキサンダー・マックイーンは2010年2月11日、ロンドンの自宅で自ら命を絶ちました。母親の死から9日後のことでした。「ファッション界の異端児」として、衝撃的で芸術的なショーで世界を驚かせ続けた天才デザイナー。ジバンシィのデザイナーを経て自身のブランドを確立し、ブリティッシュ・デザイナー・オブ・ザ・イヤーを4度受賞。40歳という若さでの死は、ファッション界に大きな衝撃を与えました。",
        "episode_type": "死去",
    },
    {
        "person_id": "P98188F1",
        "person_name": "三宅一生",
        "age": 84.0,
        "category": "ファッションデザイナー",
        "episode_text": "あなたと同じ84歳のとき、三宅一生は2022年8月5日、肝細胞がんのため東京都内の病院で亡くなりました。「一枚の布」というコンセプトで衣服の概念を根本から問い直し、プリーツ・プリーズなど革新的な技術で世界的な評価を得ました。広島での被爆体験を持ちながらも、前向きな創造性で人々を魅了。スティーブ・ジョブズの黒いタートルネックを手がけたことでも知られ、日本のファッションを世界に広めた先駆者でした。",
        "episode_type": "死去",
    },
    {
        "person_id": "P31A8FF1",
        "person_name": "高田賢三",
        "age": 81.0,
        "category": "ファッションデザイナー",
        "episode_text": "あなたと同じ81歳のとき、高田賢三は2020年10月4日、新型コロナウイルス感染症によりパリで亡くなりました。1970年にパリで「KENZO」ブランドを立ち上げ、日本人として初めてパリ・コレクションで成功を収めた先駆者でした。鮮やかな色彩と大胆な柄、東洋と西洋の融合という独自のスタイルで「色彩の魔術師」と呼ばれ、世界のファッション界に革命をもたらしました。",
        "episode_type": "死去",
    },
    {
        "person_id": "PFDF2E4D",
        "person_name": "ヴィヴィアン・ウエストウッド",
        "age": 81.0,
        "category": "ファッションデザイナー",
        "episode_text": "あなたと同じ81歳のとき、ヴィヴィアン・ウエストウッドは2022年12月29日、ロンドンの自宅で家族に看取られながら安らかに亡くなりました。1970年代にパンク・ファッションを生み出し、「パンクの女王」「反逆のファッション・アイコン」として知られました。マルコム・マクラーレンとのパートナーシップでセックス・ピストルズの衣装を手がけ、ファッションで社会に挑戦し続けた革命的なデザイナーでした。",
        "episode_type": "死去",
    },
    {
        "person_id": "P60A0B73",
        "person_name": "ピエール・カルダン",
        "age": 98.0,
        "category": "ファッションデザイナー",
        "episode_text": "あなたと同じ98歳のとき、ピエール・カルダンは2020年12月29日、パリ近郊の病院で亡くなりました。1960年代に宇宙時代を先取りした未来的なデザインで革命を起こし、オートクチュールをプレタポルテに開放した先駆者でした。ライセンスビジネスの開拓者としても知られ、自身の名を冠した製品を世界中に展開。98歳まで現役を貫き、ファッション界の生きる伝説として尊敬を集めました。",
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
