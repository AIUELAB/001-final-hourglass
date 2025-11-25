#!/usr/bin/env python3
"""
102人全員の完全データベースを作成
"""

import json
from pathlib import Path

def create_complete_database():
    """全データを統合して完全データベースを作成"""

    # v3データを読み込み
    v3_file = Path("expanded_person_facts_v3.json")
    with open(v3_file, 'r', encoding='utf-8') as f:
        v3_data = json.load(f)

    # 最終データを読み込み
    final_file = Path("final_missing_persons.json")
    with open(final_file, 'r', encoding='utf-8') as f:
        final_data = json.load(f)

    # 統合
    complete_persons = v3_data["persons"].copy()
    added_count = 0

    for person_name, person_data in final_data.items():
        if person_name not in complete_persons:
            complete_persons[person_name] = person_data
            print(f"✅ 追加: {person_name}")
            added_count += 1
        else:
            # 既存データの場合は更新（データが不完全な可能性があるため）
            existing_data = complete_persons[person_name]
            if not existing_data.get("facts") or not existing_data["facts"].get("achievements"):
                complete_persons[person_name] = person_data
                print(f"📝 更新: {person_name}")
                added_count += 1
            else:
                print(f"⏭️ スキップ（既存）: {person_name}")

    # 完全版として保存
    output_data = {"persons": complete_persons}
    output_file = "complete_person_facts.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    # 統計を表示
    print("\n" + "=" * 60)
    print("🎉 完全データベース作成完了！")
    print("=" * 60)
    print(f"総人数: {len(complete_persons)}人")
    print(f"新規/更新: {added_count}人")
    print(f"\n保存先: {output_file}")

    # 102人の完全性チェック
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

    missing = []
    for person in expected_persons:
        if person not in complete_persons:
            missing.append(person)

    if missing:
        print(f"\n⚠️ 未登録: {len(missing)}人")
        for person in missing:
            print(f"  - {person}")
    else:
        print("\n✅ 102人全員のデータが完備されました！")

    # カテゴリ別統計
    categories = {}
    for person_name, person_data in complete_persons.items():
        facts = person_data.get("facts", {})
        # カテゴリを推定
        if facts.get("works"):
            if any(word in str(facts.get("achievements", [])) for word in ["作家", "文学", "小説", "著書"]):
                category = "literature"
            elif any(word in str(facts.get("achievements", [])) for word in ["映画", "ドラマ", "音楽", "歌"]):
                category = "entertainment"
            else:
                category = "art"
        elif any(word in str(facts.get("achievements", [])) for word in ["メダル", "優勝", "選手", "記録"]):
            category = "sports"
        elif any(word in str(facts.get("achievements", [])) for word in ["創業", "CEO", "経営", "企業"]):
            category = "business"
        elif any(word in str(facts.get("achievements", [])) for word in ["ノーベル", "研究", "理論", "発見"]):
            category = "science"
        elif any(word in str(facts.get("achievements", [])) for word in ["大統領", "首相", "政治"]):
            category = "politics"
        elif any(word in str(facts.get("achievements", [])) for word in ["将軍", "幕府", "維新"]):
            category = "history"
        else:
            category = "other"

        categories[category] = categories.get(category, 0) + 1

    print("\nカテゴリ別統計:")
    for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        print(f"  {category}: {count}人")

    return output_file

if __name__ == "__main__":
    create_complete_database()
