#!/usr/bin/env python3
"""
残り13人分のデータをexpanded_person_facts_v2.jsonに統合
"""

import json
from pathlib import Path

def merge_remaining_data():
    """残りのデータを統合"""

    # 既存のv2データを読み込み
    v2_file = Path("expanded_person_facts_v2.json")
    with open(v2_file, 'r', encoding='utf-8') as f:
        v2_data = json.load(f)

    # 残りのデータを読み込み
    remaining_file = Path("remaining_persons_data.json")
    with open(remaining_file, 'r', encoding='utf-8') as f:
        remaining_data = json.load(f)

    # 統合
    merged_persons = v2_data["persons"].copy()
    added_count = 0

    for person_name, person_data in remaining_data.items():
        if person_name not in merged_persons:
            merged_persons[person_name] = person_data
            print(f"✅ 追加: {person_name}")
            added_count += 1
        else:
            print(f"⏭️ スキップ（既存）: {person_name}")

    # v3として保存
    output_data = {"persons": merged_persons}
    output_file = "expanded_person_facts_v3.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    # 統計を表示
    print("\n" + "=" * 60)
    print("📊 データ統合完了（最終版）")
    print("=" * 60)
    print(f"v2データ: {len(v2_data['persons'])}人")
    print(f"新規追加: {added_count}人")
    print(f"v3データ: {len(merged_persons)}人")
    print(f"\n保存先: {output_file}")

    # 102人の完全リスト確認
    expected_persons = [
        "大谷翔平", "イチロー", "松井秀喜", "羽生結弦", "藤井聡太",
        "羽生善治", "久保建英", "平野美宇", "伊調馨", "室伏広治",
        "上田桃子", "宮里藍", "古賀稔彦", "吉田秀彦", "高橋尚子",
        "野村忠宏", "内村航平", "浅田真央", "北島康介", "錦織圭",
        "HIKAKIN", "北野武", "新海誠", "宮崎駿", "黒澤明",
        "手塚治虫", "坂本龍一", "岡田准一", "新垣結衣", "又吉直樹",
        "松田聖子", "松本人志", "櫻井翔", "渡辺謙", "田中圭",
        "星野源", "米津玄師", "Ado", "YOSHIKI", "あいみょん",
        "村上春樹", "大江健三郎", "三島由紀夫", "川端康成", "谷崎潤一郎",
        "夏目漱石", "芥川龍之介", "太宰治", "草間彌生", "奈良美智",
        "横山大観", "安藤忠雄", "孫正義", "松下幸之助", "本田宗一郎",
        "盛田昭夫", "豊田章男", "稲盛和夫", "柳井正", "三木谷浩史",
        "前澤友作", "堀江貴文", "山中伸弥", "遠藤章", "湯川秀樹",
        "朝永振一郎", "江崎玲於奈", "利根川進", "小柴昌俊", "南部陽一郎",
        "益川敏英", "小林誠", "スティーブ・ジョブズ", "ビル・ゲイツ", "イーロン・マスク",
        "マーク・ザッカーバーグ", "ジェフ・ベゾス", "ウォーレン・バフェット", "セルゲイ・ブリン", "ラリー・ペイジ",
        "スティーブ・ウォズニアック", "ピーター・ティール", "リチャード・ブランソン", "アルベルト・アインシュタイン", "マリー・キュリー",
        "トーマス・エジソン", "ニコラ・テスラ", "マザー・テレサ", "マーティン・ルーサー・キング・ジュニア", "ネルソン・マンデラ",
        "ウィンストン・チャーチル", "ジョン・F・ケネディ", "バラク・オバマ", "ヘレン・ケラー", "小澤征爾",
        "YMO細野晴臣", "坂本龍馬", "織田信長", "豊臣秀吉", "徳川家康",
        "西郷隆盛", "福沢諭吉"
    ]

    print(f"\n目標: 102人")
    missing_persons = []
    for person in expected_persons:
        if person not in merged_persons:
            missing_persons.append(person)

    if missing_persons:
        print(f"⚠️ 未登録: {len(missing_persons)}人")
        for person in missing_persons[:10]:  # 最初の10人のみ表示
            print(f"  - {person}")
        if len(missing_persons) > 10:
            print(f"  ... 他{len(missing_persons) - 10}人")
    else:
        print("✅ 102人全員のデータが登録されています！")

if __name__ == "__main__":
    merge_remaining_data()