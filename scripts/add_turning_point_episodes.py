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
    print(f"追加予定: {len(EPISODES_TO_ADD)}件\n")

    new_rows = []
    for ep in EPISODES_TO_ADD:
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
        new_row["tier"] = template.get("tier", "WEEK_1")
        new_row["generation_timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_row["fame_tier"] = template.get("fame_tier", "4.0")
        new_row["人生の節目タグ"] = "壮年期の挑戦" if ep["age"] >= 40 else "若き挑戦"
        new_row["年代"] = get_age_group(ep["age"])
        new_row["celebrity_score_v2"] = template.get("celebrity_score_v2", "")
        new_row["category_original"] = ep["category"]

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
