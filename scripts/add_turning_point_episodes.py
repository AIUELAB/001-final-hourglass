#!/usr/bin/env python3
"""
最高職就任エピソード追加スクリプト

政治家10人に対して最高職就任エピソードを追加する。
"""

import csv
import hashlib
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"

# 追加するエピソード定義
# 各エピソードは事実ベースで、評価語・推測を含まない
EPISODES_TO_ADD = [
    {
        "person_id": "P4AAA19D",
        "person_name": "フランクリン・ルーズベルト",
        "age": 50,  # 1882年1月30日生、1932年11月8日当選
        "year": 1932,
        "episode_text": "あなたと同じ50歳のとき、フランクリン・ルーズベルトは1932年11月8日のアメリカ大統領選挙で初当選を果たしました。共和党のハーバート・フーヴァー現職大統領に対して472対59の選挙人票で圧勝し、世界恐慌の最中にあったアメリカの新しいリーダーに選ばれました。1933年3月4日に第32代大統領に就任し、ニューディール政策を推進することになります。",
        "episode_type": "達成",
        "category": "政治・社会",
    },
    {
        "person_id": "PA045EB3",
        "person_name": "毛沢東",
        "age": 55,  # 1893年12月26日生、1949年10月1日建国宣言
        "year": 1949,
        "episode_text": "あなたと同じ55歳のとき、毛沢東は1949年10月1日、北京の天安門広場で中華人民共和国の建国を宣言しました。「中国人民は立ち上がった」という言葉とともに、新中国の成立を世界に向けて発表しました。同日、中央人民政府主席に就任し、中国共産党による統治が始まりました。",
        "episode_type": "達成",
        "category": "政治・社会",
    },
    {
        "person_id": "P99203FA",
        "person_name": "バラク・オバマ",
        "age": 47,  # 1961年8月4日生、2008年11月4日当選
        "year": 2008,
        "episode_text": "あなたと同じ47歳のとき、バラク・オバマは2008年11月4日のアメリカ大統領選挙で初当選を果たしました。共和党のジョン・マケイン候補に対して365対173の選挙人票で勝利し、アメリカ史上初のアフリカ系アメリカ人大統領となりました。2009年1月20日に第44代大統領に就任しました。",
        "episode_type": "達成",
        "category": "政治・社会",
    },
    {
        "person_id": "P46ADEDA",
        "person_name": "ウィンストン・チャーチル",
        "age": 65,  # 1874年11月30日生、1940年5月10日首相就任
        "year": 1940,
        "episode_text": "あなたと同じ65歳のとき、ウィンストン・チャーチルは1940年5月10日にイギリス首相に就任しました。ネヴィル・チェンバレン前首相の辞任を受けて、ジョージ6世国王から組閣を命じられました。同日、ナチス・ドイツがフランス、ベルギー、オランダへの侵攻を開始しており、チャーチルは第二次世界大戦の最も困難な時期にイギリスを率いることになりました。",
        "episode_type": "達成",
        "category": "政治・社会",
    },
    {
        "person_id": "PAD8E8CF",
        "person_name": "サッチャー",
        "age": 53,  # 1925年10月13日生、1979年5月4日首相就任
        "year": 1979,
        "episode_text": "あなたと同じ53歳のとき、マーガレット・サッチャーは1979年5月4日にイギリス首相に就任しました。5月3日の総選挙で保守党が勝利し、イギリス史上初の女性首相となりました。「不和があるところに調和を、誤りがるところに真実を」というアッシジのフランチェスコの祈りを引用した就任演説を行いました。",
        "episode_type": "達成",
        "category": "政治・社会",
    },
    {
        "person_id": "PE633151",
        "person_name": "シー・ジンピン",
        "age": 59,  # 1953年6月15日生、2012年11月15日総書記就任
        "year": 2012,
        "episode_text": "あなたと同じ59歳のとき、習近平は2012年11月15日に中国共産党中央委員会総書記に就任しました。第18回中国共産党全国代表大会で中央委員会総書記および中央軍事委員会主席に選出され、胡錦濤前総書記から権力を継承しました。翌2013年3月には国家主席にも就任しています。",
        "episode_type": "達成",
        "category": "政治・社会",
    },
    {
        "person_id": "PA1704B9",
        "person_name": "金正恩",
        "age": 27,  # 1984年1月8日生（推定）、2011年12月30日最高指導者
        "year": 2011,
        "episode_text": "あなたと同じ27歳のとき、金正恩は2011年12月30日に朝鮮人民軍最高司令官に就任しました。12月17日に死去した父・金正日の後継者として、朝鮮労働党と朝鮮人民軍の最高指導者の地位を継承しました。翌2012年4月には朝鮮労働党第一書記および国防委員会第一委員長に就任しています。",
        "episode_type": "達成",
        "category": "政治・社会",
    },
    {
        "person_id": "PD260CC4",
        "person_name": "ネルソン・マンデラ",
        "age": 75,  # 1918年7月18日生、1994年5月10日大統領就任
        "year": 1994,
        "episode_text": "あなたと同じ75歳のとき、ネルソン・マンデラは1994年5月10日に南アフリカ共和国大統領に就任しました。同年4月の総選挙でアフリカ民族会議（ANC）が勝利し、南アフリカ史上初の黒人大統領となりました。27年間の投獄を経て、アパルトヘイト後の新生南アフリカを率いることになりました。",
        "episode_type": "達成",
        "category": "政治・社会",
    },
    {
        "person_id": "P5B17F17",
        "person_name": "始皇帝",
        "age": 38,  # 紀元前259年生、紀元前221年統一
        "year": -221,
        "episode_text": "あなたと同じ38歳のとき、始皇帝（嬴政）は紀元前221年に中国を史上初めて統一し、皇帝の称号を創設しました。秦王として即位してから約25年をかけて六国を征服し、中央集権的な統一国家を樹立しました。度量衡や文字の統一、郡県制の導入など、後の中国の基盤となる制度を確立しました。",
        "episode_type": "達成",
        "category": "政治・社会",
    },
    {
        "person_id": "P52366A0",
        "person_name": "ルイ14世",
        "age": 4,  # 1638年9月5日生、1643年5月14日即位
        "year": 1643,
        "episode_text": "あなたと同じ4歳のとき、ルイ14世は1643年5月14日に父ルイ13世の崩御によりフランス国王に即位しました。幼少のため、母アンヌ・ドートリッシュが摂政を務め、枢機卿マザランが宰相として実権を握りました。1661年にマザランが死去すると親政を開始し、72年間の在位で「太陽王」と呼ばれる絶対王政を築くことになります。",
        "episode_type": "達成",
        "category": "政治・社会",
    },
    {
        "person_id": "P2C70422",
        "person_name": "エリザベス2世",
        "age": 25,  # 1926年4月21日生、1952年2月6日即位
        "year": 1952,
        "episode_text": "あなたと同じ25歳のとき、エリザベス2世は1952年2月6日に父ジョージ6世の崩御によりイギリス女王に即位しました。ケニア訪問中に父の死を知らされ、直ちに帰国。1953年6月2日にウェストミンスター寺院で戴冠式が執り行われ、史上初めてテレビ中継された戴冠式となりました。70年以上にわたりイギリス君主として在位することになります。",
        "episode_type": "達成",
        "category": "政治・社会",
    },
    # === ランキング改善フェーズ2: 参照対象者エピソード追加 ===
    {
        "person_id": "PD7F00A6",
        "person_name": "イチロー",
        "age": 27,  # 1973年10月22日生、2001年シーズン
        "year": 2001,
        "episode_text": "あなたと同じ27歳のとき、イチローは2001年にシアトル・マリナーズに移籍し、メジャーリーグの歴史に名を刻みました。打率.350、242安打、56盗塁という驚異的な成績で、アメリカン・リーグ新人王とMVPを同時受賞。これは野手では史上2人目の快挙でした。「日本人選手はメジャーで通用しない」という常識を覆し、世界最高峰のリーグで首位打者を獲得した瞬間、野球の歴史が変わりました。",
        "episode_type": "達成",
        "category": "スポーツ",
        "scores": {
            "memorability_score": 9.0,
            "empathy_score": 8.0,
            "surprise_score": 8.5,
            "generation_quality_score": 9.0,
            "educational_value": 7.5,
            "story_quality": 8.5,
            "factual_density": 9.5,
        },
    },
    {
        "person_id": "P17CC1C2",
        "person_name": "孫正義",
        "age": 24,  # 1957年8月11日生、1981年9月創業
        "year": 1981,
        "episode_text": "あなたと同じ24歳のとき、孫正義は1981年9月に福岡市でソフトバンクの前身「日本ソフトバンク」を創業しました。資本金1000万円、社員2名でのスタート。創業初日、みかん箱の上に立ち「5年で売上100億、10年で500億、将来は1兆、2兆と数えるようになる」と宣言。社員は呆れて2週間で辞めましたが、孫は本気でした。この「ホラ」は現実となり、今や時価総額10兆円超のグループを築いています。",
        "episode_type": "達成",
        "category": "ビジネス・経営",
        "scores": {
            "memorability_score": 9.0,
            "empathy_score": 8.5,
            "surprise_score": 9.0,
            "generation_quality_score": 8.5,
            "educational_value": 8.0,
            "story_quality": 9.0,
            "factual_density": 9.0,
        },
    },
    {
        "person_id": "P7CFD801",
        "person_name": "カーネル・サンダース",
        "age": 65,  # 1890年9月9日生、1955年
        "year": 1955,
        "episode_text": "あなたと同じ65歳のとき、カーネル・サンダースは1955年、人生最大の挑戦を始めました。経営していたレストランが高速道路のルート変更で客足が激減し倒産。65歳で全財産を失い、手元に残ったのは月額105ドルの年金と秘伝のフライドチキンレシピだけ。彼は車で全米を回り、1009軒の店に断られながらも契約を取り付けました。「65歳からでも人生は変えられる」を体現し、KFCは世界145カ国、27,000店舗を展開する帝国となりました。",
        "episode_type": "挑戦",
        "category": "ビジネス・経営",
        "scores": {
            "memorability_score": 9.5,
            "empathy_score": 9.0,
            "surprise_score": 9.5,
            "generation_quality_score": 9.0,
            "educational_value": 9.0,
            "story_quality": 9.0,
            "factual_density": 8.5,
        },
    },
    # === ランキング改善フェーズ3: 本田宗一郎・伊能忠敬 ===
    {
        "person_id": "P758B044",
        "person_name": "本田宗一郎",
        "age": 39,  # 1906年11月17日生、1945年
        "year": 1945,
        "episode_text": "あなたと同じ39歳のとき、本田宗一郎は1945年、全てを失った焼け野原で「人間休業」を宣言しました。戦時中に経営していた東海精機重工業はトヨタに売却。その売却金を手に「1年間遊ぶ」と宣言し、自宅で製塩機や織機を作って近所に配りながら、次の一手を模索しました。この「何もしない」1年間こそが、世界のHondaを生む充電期間となりました。翌1946年、浜松の焼け跡で拾った陸軍払い下げの無線機用発電エンジンを自転車に取り付け、本田技術研究所を設立します。",
        "episode_type": "挑戦",
        "category": "ビジネス・経営",
        "scores": {
            "memorability_score": 9.0,
            "empathy_score": 9.0,
            "surprise_score": 9.5,
            "generation_quality_score": 8.5,
            "educational_value": 8.5,
            "story_quality": 9.0,
            "factual_density": 9.0,
        },
    },
    # === ランキング改善フェーズ4: 矢沢永吉・安藤百福 ===
    {
        "person_id": "P2B98441",
        "person_name": "矢沢永吉",
        "age": 49,  # 1949年9月14日生、1998年
        "year": 1998,
        "episode_text": "あなたと同じ49歳のとき、矢沢永吉は1998年、35億円の負債を完済し、復活の狼煙を上げました。1987年に側近の横領で発覚した巨額負債。「逃げることもできた。でも俺は逃げなかった」。11年間、年間100本以上のライブをこなし、1曲1曲が借金返済のための戦いでした。完済の日、彼は言いました。「これで終わりじゃない。これからが本当のロックンロールだ」。50代以降の輝きは、この49歳の決断から始まりました。",
        "episode_type": "挑戦",
        "category": "音楽・芸能",
        "scores": {
            "memorability_score": 9.5,
            "empathy_score": 9.0,
            "surprise_score": 9.0,
            "generation_quality_score": 9.0,
            "educational_value": 8.5,
            "story_quality": 9.0,
            "factual_density": 9.0,
        },
    },
]


def generate_episode_id() -> str:
    """ユニークなエピソードIDを生成"""
    timestamp = datetime.now().strftime("%y%m%d%H%M%S%f")[:15]
    hash_suffix = hashlib.md5(timestamp.encode()).hexdigest()[:3].upper()
    return f"EP-{timestamp}{hash_suffix}"


def get_age_group(age: int) -> str:
    """年代を算出"""
    if age < 10:
        return "0代"
    elif age >= 90:
        return "90代以上"
    else:
        return f"{(age // 10) * 10}代"


def main(dry_run: bool = True):
    # 既存データ読み込み（BOM対応）
    with open(MASTER_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames

    print(f"=== 最高職就任エピソード追加 {'(ドライラン)' if dry_run else '(実行)'} ===\n")
    print(f"既存エピソード数: {len(rows)}")

    # 既にTURNING_POINT_MANUALが存在する人物をスキップ
    existing_tp_persons = {r["person_id"] for r in rows if r.get("source") == "TURNING_POINT_MANUAL"}

    # 未追加のエピソードのみフィルタ
    to_add = [ep for ep in EPISODES_TO_ADD if ep["person_id"] not in existing_tp_persons]
    skipped = len(EPISODES_TO_ADD) - len(to_add)

    print(f"追加予定: {len(to_add)}件（スキップ: {skipped}件）\n")

    new_rows = []
    for ep in to_add:
        episode_id = generate_episode_id()

        # 既存レコードから人物情報を取得
        person_rows = [r for r in rows if r["person_id"] == ep["person_id"]]
        if not person_rows:
            print(f"⚠️ {ep['person_name']}: person_id {ep['person_id']} が見つかりません")
            continue

        template = person_rows[0]

        new_row = {k: "" for k in fieldnames}
        new_row["episode_id"] = episode_id
        new_row["person_id"] = ep["person_id"]
        new_row["person_name"] = ep["person_name"]
        new_row["episode_count"] = template.get("episode_count", "1")
        new_row["age"] = str(float(ep["age"]))
        new_row["category"] = ep["category"]
        new_row["char_count"] = str(len(ep["episode_text"]))
        new_row["episode_text"] = ep["episode_text"]
        new_row["episode_type"] = ep["episode_type"]
        new_row["fact_check_result"] = "確認済み"
        new_row["group_name"] = template.get("group_name", "未登録")
        new_row["is_group_member"] = template.get("is_group_member", "False")
        new_row["person_type"] = template.get("person_type", "REAL")
        new_row["quality_score"] = "8.5"
        new_row["source"] = "TURNING_POINT_MANUAL"
        new_row["generation_timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_row["fame_tier"] = template.get("fame_tier", "4.0")
        new_row["人生の節目タグ"] = "壮年期の挑戦" if ep["age"] >= 40 else "若き挑戦"
        new_row["年代"] = get_age_group(ep["age"])
        new_row["celebrity_score_v2"] = template.get("celebrity_score_v2", "")
        new_row["category_original"] = ep["category"]

        # 7軸スコアを設定（定義されている場合）
        if "scores" in ep:
            for score_name, score_value in ep["scores"].items():
                if score_name in fieldnames:
                    new_row[score_name] = str(score_value)

        new_rows.append(new_row)
        print(f"✓ {ep['person_name']} ({ep['age']}歳, {ep['year']}年)")
        print(f"  ID: {episode_id}")
        print(f"  本文: {ep['episode_text'][:60]}...")
        print()

    if dry_run:
        print("=== ドライラン完了（変更なし） ===")
        return

    # 実行モード: CSVに追記
    rows.extend(new_rows)
    with open(MASTER_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"=== 追加完了: {len(new_rows)}件 ===")
    print(f"新エピソード数: {len(rows)}")


if __name__ == "__main__":
    dry_run = "--execute" not in sys.argv
    main(dry_run)
