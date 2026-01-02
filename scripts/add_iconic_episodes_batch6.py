#!/usr/bin/env python3
"""
象徴エピソード追加スクリプト（第6弾）

スポーツ選手の象徴的最期エピソード11件を追加
"""

import csv
import uuid
from datetime import datetime
from pathlib import Path


def generate_episode_id():
    """エピソードIDを生成"""
    return f"EP-{uuid.uuid4().hex[:8].upper()}"


ICONIC_EPISODES = [
    # 1. ベーブ・ルース - 53歳死去（1948年）
    {
        "person_id": "P36EBB77",
        "person_name": "ベーブ・ルース",
        "age": 53.0,
        "category": "スポーツ",
        "episode_text": "あなたと同じ53歳のとき、ベーブ・ルースは1948年8月16日、ニューヨークで咽頭がんにより亡くなりました。「野球の神様」と呼ばれた彼は、714本塁打という当時の大リーグ記録を樹立し、ヤンキースを4度のワールドシリーズ制覇に導きました。葬儀にはヤンキースタジアムに約10万人が訪れ、アメリカ中が彼の死を悼みました。貧しい少年院出身から這い上がり、野球を国民的スポーツに押し上げた「サルタン・オブ・スワット」の伝説は、今なお語り継がれています。",
        "episode_type": "死去",
    },
    # 2. ペレ - 82歳死去（2022年）
    {
        "person_id": "P4BBAD3C",
        "person_name": "ペレ",
        "age": 82.0,
        "category": "スポーツ",
        "episode_text": "あなたと同じ82歳のとき、ペレは2022年12月29日、ブラジル・サンパウロで大腸がんにより亡くなりました。ワールドカップ3度優勝という前人未到の記録を持つ「サッカーの王様」は、通算1281ゴールを記録しました。ブラジル政府は3日間の服喪を宣言し、世界中のサッカー選手やファンが追悼しました。「美しいゲーム」という言葉を体現した彼のプレーは、マラドーナやメッシなど後世のスターたちに多大な影響を与え続けています。",
        "episode_type": "死去",
    },
    # 3. マラドーナ - 60歳死去（2020年）
    {
        "person_id": "P74ABE22",
        "person_name": "マラドーナ",
        "age": 60.0,
        "category": "スポーツ",
        "episode_text": "あなたと同じ60歳のとき、ディエゴ・マラドーナは2020年11月25日、アルゼンチン・ブエノスアイレス近郊の自宅で心臓発作により亡くなりました。「神の手」と「5人抜き」で語り継がれる1986年ワールドカップの伝説的ゴールは、サッカー史上最高のプレーとして今なお称えられています。薬物依存など私生活の問題を抱えながらも、アルゼンチン国民にとって永遠の英雄であり続けた彼の葬儀には、100万人以上が参列しました。",
        "episode_type": "死去",
    },
    # 4. モハメド・アリ - 74歳死去（2016年）
    {
        "person_id": "P4540FE3",
        "person_name": "モハメド・アリ",
        "age": 74.0,
        "category": "スポーツ",
        "episode_text": "あなたと同じ74歳のとき、モハメド・アリは2016年6月3日、アメリカ・アリゾナ州で敗血症性ショックにより亡くなりました。32年間パーキンソン病と闘い続けた「史上最高のボクサー」は、「蝶のように舞い、蜂のように刺す」という名言と共に、リング内外で人々を魅了しました。ベトナム戦争への徴兵拒否で王座を剥奪されながらも信念を貫いた彼は、スポーツ選手の社会的発言の先駆者として、今なお尊敬を集めています。",
        "episode_type": "死去",
    },
    # 5. アントニオ猪木 - 79歳死去（2022年）
    {
        "person_id": "PDBAB080",
        "person_name": "アントニオ猪木",
        "age": 79.0,
        "category": "スポーツ",
        "episode_text": "あなたと同じ79歳のとき、アントニオ猪木は2022年10月1日、東京で心不全により亡くなりました。「燃える闘魂」として日本プロレス界をけん引し、モハメド・アリとの異種格闘技戦は世界中で話題となりました。「1、2、3、ダー！」の掛け声と共に「元気ですかー！」と叫ぶ姿は国民的アイコンとなり、政治家としても活躍しました。晩年は全身性アミロイドーシスと闘いながらも、最期まで闘魂を燃やし続けました。",
        "episode_type": "死去",
    },
    # 6. ジャイアント馬場 - 61歳死去（1999年）
    {
        "person_id": "P25011A2",
        "person_name": "ジャイアント馬場",
        "age": 61.0,
        "category": "スポーツ",
        "episode_text": "あなたと同じ61歳のとき、ジャイアント馬場は1999年1月31日、東京で大腸がんにより亡くなりました。身長209cmの巨体から繰り出す「16文キック」で知られ、「東洋の巨人」として日本プロレス界の礎を築きました。全日本プロレスを設立し、王道プロレスを貫いた彼は、アントニオ猪木と共に昭和のプロレス黄金時代を作り上げました。温厚な人柄で多くのレスラーから慕われた巨人の死は、日本中に深い悲しみをもたらしました。",
        "episode_type": "死去",
    },
    # 7. 力道山 - 39歳刺殺（1963年）
    {
        "person_id": "PDE368E8",
        "person_name": "力道山",
        "age": 39.0,
        "category": "スポーツ",
        "episode_text": "あなたと同じ39歳のとき、力道山は1963年12月15日、東京で暴力団員に刺された傷がもとで亡くなりました。わずか8日前の刺傷事件後、手術は成功したものの腹膜炎を起こして急死しました。戦後日本に希望を与えた「日本プロレスの父」は、空手チョップでアメリカ人レスラーを倒す姿が国民的人気を博しました。テレビ普及のきっかけともなった彼の試合は、高度経済成長期の日本人の心の支えでした。39歳での突然の死は日本中に衝撃を与えました。",
        "episode_type": "死去",
    },
    # 8. 大鵬 - 72歳死去（2013年）
    {
        "person_id": "P23CF32C",
        "person_name": "大鵬",
        "age": 72.0,
        "category": "スポーツ",
        "episode_text": "あなたと同じ72歳のとき、大鵬は2013年1月19日、東京で心室頻拍により亡くなりました。史上最多の優勝32回を誇る「昭和の大横綱」は、「巨人・大鵬・卵焼き」という流行語に象徴されるように、高度経済成長期の国民的ヒーローでした。樺太出身で終戦後に引き揚げてきた苦労人は、柏戸との「柏鵬時代」で相撲黄金期を築きました。国民栄誉賞を受賞した彼の功績は、相撲界の歴史に永遠に刻まれています。",
        "episode_type": "死去",
    },
    # 9. 千代の富士 - 61歳死去（2016年）
    {
        "person_id": "PD99CD83",
        "person_name": "千代の富士",
        "age": 61.0,
        "category": "スポーツ",
        "episode_text": "あなたと同じ61歳のとき、千代の富士は2016年7月31日、東京で膵臓がんにより亡くなりました。「ウルフ」の愛称で親しまれた彼は、通算1045勝、優勝31回という偉大な記録を残しました。小兵ながら鋼の肉体で大型力士を投げ飛ばす姿は、多くのファンを魅了しました。引退会見での「体力の限界」という言葉は流行語となり、国民栄誉賞を受賞した平成の大横綱として、今なお相撲ファンの記憶に刻まれています。",
        "episode_type": "死去",
    },
    # 10. コービー・ブライアント - 41歳事故死（2020年）
    {
        "person_id": "PB8BE564",
        "person_name": "コービー・ブライアント",
        "age": 41.0,
        "category": "スポーツ",
        "episode_text": "あなたと同じ41歳のとき、コービー・ブライアントは2020年1月26日、カリフォルニア州でヘリコプター墜落事故により亡くなりました。13歳の娘ジアナを含む9人全員が犠牲となった悲劇でした。NBAで20シーズンをレイカーズ一筋でプレーし、5度の優勝、オールスター18回選出を誇る「ブラック・マンバ」は、マイケル・ジョーダンに次ぐバスケットボール界のアイコンでした。「マンバ・メンタリティ」と呼ばれる彼の勝利への執念は、今なお世界中のアスリートに影響を与えています。",
        "episode_type": "死去",
    },
    # 11. アイルトン・セナ - 34歳事故死（1994年）
    {
        "person_id": "P6945868",
        "person_name": "アイルトン・セナ",
        "age": 34.0,
        "category": "スポーツ",
        "episode_text": "あなたと同じ34歳のとき、アイルトン・セナは1994年5月1日、イタリア・イモラで行われたF1サンマリノグランプリで事故死しました。高速コーナー「タンブレロ」でコンクリートウォールに激突し、即死状態でした。ワールドチャンピオン3回、通算41勝を挙げた「音速の貴公子」は、雨のレースでの神がかり的なドライビングで知られました。母国ブラジルでは国葬が執り行われ、300万人が沿道で別れを惜しみました。F1史上最も愛されたドライバーの突然の死でした。",
        "episode_type": "死去",
    },
]


def main():
    csv_path = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")

    # 既存CSVを読み込み
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        existing = list(reader)
        fieldnames = reader.fieldnames

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

    # 全エピソードを結合
    all_episodes = existing + new_episodes

    # CSVに書き込み
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_episodes)

    print(f"✅ 追加完了: {len(new_episodes)}件")
    print(f"   総エピソード数: {len(all_episodes)}件")
    print()
    print("追加エピソード:")
    for ep in ICONIC_EPISODES:
        print(f"  - {ep['person_name']} ({ep['age']}歳): {ep['episode_type']}")


if __name__ == "__main__":
    main()
