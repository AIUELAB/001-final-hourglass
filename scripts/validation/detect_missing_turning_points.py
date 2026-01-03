#!/usr/bin/env python3
"""
重要転機エピソード欠落検出スクリプト

職種別の「必須転機候補」を定義し、上位著名人に対して
転機がカバーされているかを点検する。
"""

import csv
from collections import defaultdict
from pathlib import Path


CSV_PATH = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")


# 職種別の必須転機キーワード
TURNING_POINT_REQUIREMENTS = {
    "政治家": {
        "keywords": ["大統領", "首相", "総理", "主席", "書記長", "総統", "国王", "女王", "皇帝"],
        "description": "最高職への就任/当選",
    },
    "科学者": {
        "keywords": ["ノーベル", "発見", "発明", "理論", "証明"],
        "description": "ノーベル賞/代表的発見",
    },
    "アスリート": {
        "keywords": ["金メダル", "オリンピック", "世界記録", "世界選手権", "優勝", "制覇"],
        "description": "五輪/世界大会優勝、世界記録",
    },
    "映画監督": {
        "keywords": ["アカデミー賞", "カンヌ", "パルム・ドール", "金獅子", "ベルリン", "代表作"],
        "description": "世界的受賞/代表作発表",
    },
    "作家": {
        "keywords": ["ノーベル文学賞", "芥川賞", "直木賞", "ベストセラー", "代表作"],
        "description": "文学賞/代表作発表",
    },
    "音楽家": {
        "keywords": ["グラミー", "オリコン1位", "ビルボード", "アルバム", "デビュー"],
        "description": "主要賞/大ヒット",
    },
    "実業家": {
        "keywords": ["創業", "設立", "上場", "IPO", "CEO"],
        "description": "会社創業/上場",
    },
}

# 著名人物とそのカテゴリ・期待される転機（手動定義）
CRITICAL_PERSONS = [
    # 政治家
    ("ウラジーミル・プーチン", "政治家", ["大統領"]),
    ("バラク・オバマ", "政治家", ["大統領"]),
    ("ドナルド・トランプ", "政治家", ["大統領"]),
    ("ネルソン・マンデラ", "政治家", ["大統領", "釈放"]),
    ("マーガレット・サッチャー", "政治家", ["首相"]),
    ("安倍晋三", "政治家", ["首相", "総理"]),
    ("毛沢東", "政治家", ["主席", "革命"]),
    ("ウィンストン・チャーチル", "政治家", ["首相"]),
    ("アドルフ・ヒトラー", "政治家", ["総統", "ドイツ"]),
    # 科学者
    ("アルベルト・アインシュタイン", "科学者", ["相対性理論", "ノーベル"]),
    ("マリー・キュリー", "科学者", ["ノーベル", "ラジウム"]),
    ("スティーブン・ホーキング", "科学者", ["ブラックホール", "宇宙"]),
    ("湯川秀樹", "科学者", ["ノーベル", "中間子"]),
    # アスリート
    ("大谷翔平", "アスリート", ["二刀流", "MVP", "メジャー"]),
    ("イチロー", "アスリート", ["ヒット", "記録", "メジャー"]),
    ("羽生結弦", "アスリート", ["金メダル", "オリンピック"]),
    ("マイケル・ジョーダン", "アスリート", ["NBA", "優勝", "チャンピオン"]),
    ("リオネル・メッシ", "アスリート", ["ワールドカップ", "バロンドール"]),
    # 映画監督
    ("黒澤明", "映画監督", ["七人の侍", "羅生門", "アカデミー"]),
    ("スティーヴン・スピルバーグ", "映画監督", ["アカデミー", "ジョーズ", "ET"]),
    ("宮崎駿", "映画監督", ["千と千尋", "アカデミー"]),
    # 作家
    ("村上春樹", "作家", ["ノルウェイの森", "代表作"]),
    ("川端康成", "作家", ["ノーベル文学賞"]),
    ("大江健三郎", "作家", ["ノーベル文学賞"]),
    # 音楽家
    ("ビートルズ", "音楽家", ["デビュー", "ヒット"]),
    ("マイケル・ジャクソン", "音楽家", ["スリラー", "グラミー"]),
    # 実業家
    ("スティーブ・ジョブズ", "実業家", ["Apple", "iPhone", "創業"]),
    ("イーロン・マスク", "実業家", ["Tesla", "SpaceX", "創業"]),
    ("ビル・ゲイツ", "実業家", ["マイクロソフト", "Microsoft", "創業"]),
    ("孫正義", "実業家", ["ソフトバンク", "創業"]),
]


def load_episodes():
    """エピソードをロード"""
    episodes = []
    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            episodes.append(row)
    return episodes


def get_person_episodes(episodes, person_name):
    """特定人物のエピソードを取得"""
    return [ep for ep in episodes if ep.get("person_name") == person_name]


def check_turning_point_coverage(person_episodes, expected_keywords):
    """転機キーワードがカバーされているかチェック"""
    all_text = " ".join(ep.get("episode_text", "") for ep in person_episodes)

    covered = []
    missing = []

    for kw in expected_keywords:
        if kw in all_text:
            covered.append(kw)
        else:
            missing.append(kw)

    return covered, missing


def main():
    print("=" * 70)
    print("重要転機エピソード欠落検出")
    print("=" * 70)

    episodes = load_episodes()
    print(f"総エピソード数: {len(episodes)}")

    # 人物別にグループ化
    person_map = defaultdict(list)
    for ep in episodes:
        name = ep.get("person_name", "")
        if name:
            person_map[name].append(ep)

    print(f"人物数: {len(person_map)}")
    print()

    # 欠落検出結果
    missing_list = []
    covered_list = []
    not_found_list = []

    for person_name, category, expected_keywords in CRITICAL_PERSONS:
        person_eps = person_map.get(person_name, [])

        if not person_eps:
            not_found_list.append((person_name, category, expected_keywords))
            continue

        covered, missing = check_turning_point_coverage(person_eps, expected_keywords)

        if missing:
            missing_list.append(
                {
                    "person_name": person_name,
                    "category": category,
                    "episode_count": len(person_eps),
                    "covered": covered,
                    "missing": missing,
                }
            )
        else:
            covered_list.append(
                {
                    "person_name": person_name,
                    "category": category,
                    "episode_count": len(person_eps),
                    "covered": covered,
                }
            )

    # 結果出力
    print("=" * 70)
    print("【欠落あり】重要転機がカバーされていない人物")
    print("=" * 70)
    for item in missing_list:
        print(f"\n{item['person_name']} ({item['category']}, {item['episode_count']}件)")
        print(f"  カバー済み: {', '.join(item['covered']) or 'なし'}")
        print(f"  欠落キーワード: {', '.join(item['missing'])}")

    print()
    print("=" * 70)
    print("【データなし】エピソードが存在しない人物")
    print("=" * 70)
    for person_name, category, keywords in not_found_list:
        print(f"  {person_name} ({category}) - 期待: {', '.join(keywords)}")

    print()
    print("=" * 70)
    print("【OK】転機がカバーされている人物")
    print("=" * 70)
    for item in covered_list:
        print(f"  {item['person_name']}: {', '.join(item['covered'])}")

    # サマリー
    print()
    print("=" * 70)
    print("サマリー")
    print("=" * 70)
    print(f"  チェック対象: {len(CRITICAL_PERSONS)}人")
    print(f"  欠落あり: {len(missing_list)}人")
    print(f"  データなし: {len(not_found_list)}人")
    print(f"  カバー済み: {len(covered_list)}人")

    # 欠落追加候補を提案
    if missing_list:
        print()
        print("=" * 70)
        print("追加候補（承認待ち）")
        print("=" * 70)
        for item in missing_list:
            for kw in item["missing"]:
                print(f"  - {item['person_name']}: 「{kw}」関連エピソード")

    return missing_list, not_found_list


if __name__ == "__main__":
    main()
