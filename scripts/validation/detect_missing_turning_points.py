#!/usr/bin/env python3
"""
転機エピソード欠落検出スクリプト

対象: celebrity_score_v2 上位100人物
目的: 重要な転機エピソードが欠落している人物を特定

職種別必須転機パターン:
- 政治家: 大統領/首相/総理 就任・当選
- アスリート: オリンピック金メダル、世界記録、世界選手権優勝
- 科学者: ノーベル賞、代表的発見
- 芸術家: 代表作発表、世界的受賞
- 実業家: 創業、上場、CEO就任

出力: src/reports/missing_turning_points.json
"""

import csv
import json
import re
from datetime import datetime
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).parent.parent.parent
CSV_PATH = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
REPORT_PATH = PROJECT_ROOT / "src/reports/missing_turning_points.json"


# 職種別必須転機キーワード
TURNING_POINT_PATTERNS = {
    "政治家": {
        "keywords": ["大統領", "首相", "総理大臣", "総理", "当選", "就任", "初当選", "政権"],
        "required": ["大統領就任", "首相就任", "初当選"],  # 重要度高
    },
    "スポーツ選手": {
        "keywords": ["オリンピック", "金メダル", "世界記録", "世界選手権", "優勝", "MVP", "タイトル"],
        "required": ["オリンピック金メダル", "世界記録", "メジャー優勝"],
    },
    "科学者": {
        "keywords": ["ノーベル賞", "発見", "発明", "理論", "法則", "受賞"],
        "required": ["ノーベル賞受賞", "代表的発見"],
    },
    "芸術家": {
        "keywords": ["受賞", "デビュー", "代表作", "初演", "発表", "グラミー賞", "アカデミー賞"],
        "required": ["代表作発表", "主要賞受賞"],
    },
    "実業家": {
        "keywords": ["創業", "設立", "上場", "CEO", "会長", "社長", "起業"],
        "required": ["会社設立", "上場", "経営者就任"],
    },
    "作家": {
        "keywords": ["デビュー", "受賞", "ノーベル文学賞", "芥川賞", "直木賞", "代表作"],
        "required": ["デビュー作", "主要文学賞"],
    },
    "音楽家": {
        "keywords": ["デビュー", "グラミー賞", "ヒット", "アルバム", "ツアー", "受賞"],
        "required": ["デビュー", "代表曲発表"],
    },
    "映画監督": {
        "keywords": ["監督作", "初監督", "受賞", "カンヌ", "ヴェネツィア", "アカデミー賞", "金獅子賞"],
        "required": ["監督デビュー", "代表作発表"],
    },
}

# カテゴリから職種を推定するマッピング
CATEGORY_TO_OCCUPATION = {
    "政治・社会": "政治家",
    "スポーツ": "スポーツ選手",
    "科学・技術": "科学者",
    "芸術・文化": "芸術家",
    "ビジネス・経済": "実業家",
    "エンタメ": "音楽家",  # デフォルト
}


def load_episodes():
    """エピソード読み込み"""
    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader)


def get_top_persons(episodes, top_n=100):
    """celebrity_score_v2上位N人物を取得"""
    person_scores = {}
    person_info = {}

    for row in episodes:
        person_id = row.get("person_id", "")
        person_name = row.get("person_name", "")

        # celebrity_score_v2を取得
        try:
            score = float(row.get("celebrity_score_v2", 0) or 0)
        except (ValueError, TypeError):
            score = 0

        if person_id and score > 0:
            if person_id not in person_scores or score > person_scores[person_id]:
                person_scores[person_id] = score
                person_info[person_id] = {
                    "person_id": person_id,
                    "person_name": person_name,
                    "category": row.get("category", ""),
                    "person_type": row.get("person_type", ""),
                }

    # スコア順でソート
    sorted_persons = sorted(person_scores.items(), key=lambda x: -x[1])

    result = []
    for person_id, score in sorted_persons[:top_n]:
        info = person_info[person_id]
        info["celebrity_score_v2"] = score
        result.append(info)

    return result


def get_person_episodes(episodes, person_id):
    """指定person_idのエピソード一覧を取得"""
    return [row for row in episodes if row.get("person_id") == person_id]


def infer_occupation(person_info, episodes):
    """人物の職種を推定"""
    category = person_info.get("category", "")
    person_name = person_info.get("person_name", "")

    # 特定人物の職種を直接指定（有名人物）
    known_occupations = {
        "パブロ・ピカソ": "芸術家",
        "葛飾北斎": "芸術家",
        "レオナルド・ダ・ヴィンチ": "芸術家",
        "フィンセント・ファン・ゴッホ": "芸術家",
        "松尾芭蕉": "作家",
        "小泉八雲": "作家",
        "村上春樹": "作家",
        "川端康成": "作家",
        "三島由紀夫": "作家",
        "夏目漱石": "作家",
        "マイケル・ジャクソン": "音楽家",
        "ビートルズ": "音楽家",
        "黒澤明": "映画監督",
        "三船敏郎": "芸術家",  # 俳優
        "アルベルト・アインシュタイン": "科学者",
        "アインシュタイン": "科学者",
    }

    if person_name in known_occupations:
        return known_occupations[person_name]

    # カテゴリから推定
    occupation = CATEGORY_TO_OCCUPATION.get(category, None)

    # エピソードテキストからも補完
    all_text = " ".join(row.get("episode_text", "") for row in episodes)

    # 職種キーワードで判定
    occupation_scores = defaultdict(int)
    for occ, patterns in TURNING_POINT_PATTERNS.items():
        for kw in patterns["keywords"]:
            if kw in all_text:
                occupation_scores[occ] += 1

    if occupation_scores:
        best_occ = max(occupation_scores.items(), key=lambda x: x[1])[0]
        if occupation_scores[best_occ] >= 2:
            occupation = best_occ

    return occupation or "不明"


def check_turning_points(person_info, episodes, occupation):
    """転機エピソードの有無をチェック"""
    patterns = TURNING_POINT_PATTERNS.get(occupation, {})
    keywords = patterns.get("keywords", [])

    # 全エピソードテキストを結合
    all_text = " ".join(row.get("episode_text", "") for row in episodes)

    # 各キーワードのヒット状況
    found_keywords = []
    missing_keywords = []

    for kw in keywords:
        if kw in all_text:
            found_keywords.append(kw)
        else:
            missing_keywords.append(kw)

    # 重要キーワードの欠落を特定（より緩い判定）
    # required内のキーワードが部分的に含まれていればOK
    required = patterns.get("required", [])
    critical_missing = []

    for req in required:
        # 必須パターンの個別単語をチェック
        req_words = req.replace("就任", " 就任").replace("受賞", " 受賞").replace("発表", " 発表").split()
        found = any(word in all_text for word in req_words if len(word) >= 2)
        if not found:
            critical_missing.append(req)

    return {
        "found": found_keywords,
        "missing": missing_keywords,
        "critical_missing": critical_missing,
        "coverage": len(found_keywords) / len(keywords) if keywords else 1.0,
    }


def analyze_specific_turning_points(person_name, occupation, all_text):
    """人物固有の転機を分析（有名人物向け）"""
    suggestions = []

    # 特定人物の転機候補（Wikipedia/一般常識ベース）
    # 実際のシステムでは外部DBを参照すべきだが、主要人物はハードコード
    specific_turning_points = {
        "大谷翔平": [
            ("MLB二刀流シーズンMVP", "MVP"),
            ("ホームラン王", "本塁打王"),
            ("投手勝利", "勝利"),
        ],
        "イチロー": [
            ("MLB最多安打記録", "262安打"),
            ("3000本安打", "3000本"),
            ("MLB殿堂入り", "殿堂"),
        ],
        "アルベルト・アインシュタイン": [
            ("相対性理論発表", "相対性理論"),
            ("ノーベル物理学賞", "ノーベル"),
            ("奇跡の年", "1905年"),
        ],
        "スティーブ・ジョブズ": [
            ("Apple創業", "創業"),
            ("iPhone発表", "iPhone"),
            ("Appleへの復帰", "復帰"),
        ],
        "ウラジーミル・プーチン": [
            ("大統領初当選", "大統領"),
            ("KGB入局", "KGB"),
        ],
        "黒澤明": [
            ("羅生門ヴェネツィア金獅子賞", "金獅子賞"),
            ("七人の侍完成", "七人の侍"),
            ("監督デビュー", "デビュー"),
        ],
        "ドナルド・トランプ": [
            ("大統領就任", "大統領"),
            ("トランプタワー建設", "タワー"),
        ],
        "イーロン・マスク": [
            ("SpaceX設立", "SpaceX"),
            ("Tesla CEO就任", "Tesla"),
            ("Twitter買収", "Twitter"),
        ],
    }

    if person_name in specific_turning_points:
        for tp_name, keyword in specific_turning_points[person_name]:
            if keyword not in all_text:
                suggestions.append(tp_name)

    return suggestions


def main():
    print("=" * 60)
    print("転機エピソード欠落検出")
    print("=" * 60)

    # エピソード読み込み
    episodes = load_episodes()
    print(f"総エピソード数: {len(episodes)}")

    # 上位100人物を取得
    top_persons = get_top_persons(episodes, top_n=100)
    print(f"対象人物数: {len(top_persons)}")

    # 各人物を分析
    results = []
    missing_count = 0

    for person in top_persons:
        person_id = person["person_id"]
        person_name = person["person_name"]

        # 人物のエピソード取得
        person_episodes = get_person_episodes(episodes, person_id)
        ep_count = len(person_episodes)

        # 職種推定
        occupation = infer_occupation(person, person_episodes)

        # 転機チェック
        tp_check = check_turning_points(person, person_episodes, occupation)

        # 全テキスト
        all_text = " ".join(row.get("episode_text", "") for row in person_episodes)

        # 人物固有の転機分析
        specific_missing = analyze_specific_turning_points(person_name, occupation, all_text)

        # 欠落があるか判定
        has_missing = (
            tp_check["coverage"] < 0.5  # カバレッジ50%未満
            or len(tp_check["critical_missing"]) > 0  # 重要転機欠落
            or len(specific_missing) > 0  # 固有転機欠落
        )

        if has_missing:
            missing_count += 1

        result = {
            "person_id": person_id,
            "person_name": person_name,
            "celebrity_score_v2": person["celebrity_score_v2"],
            "category": person["category"],
            "occupation": occupation,
            "episode_count": ep_count,
            "turning_point_coverage": tp_check["coverage"],
            "found_keywords": tp_check["found"],
            "missing_keywords": tp_check["missing"],
            "critical_missing": tp_check["critical_missing"],
            "specific_missing": specific_missing,
            "has_missing": has_missing,
        }
        results.append(result)

    # 欠落ありをスコア順でソート
    missing_results = [r for r in results if r["has_missing"]]
    missing_results.sort(key=lambda x: -x["celebrity_score_v2"])

    # レポート生成
    report = {
        "scan_timestamp": datetime.now().isoformat(),
        "total_persons_checked": len(top_persons),
        "persons_with_missing": missing_count,
        "missing_rate": missing_count / len(top_persons) if top_persons else 0,
        "missing_turning_points": missing_results,
        "all_results": results,
    }

    # レポート保存
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 画面出力
    print()
    print("【検出結果】")
    print(f"  転機欠落あり: {missing_count}人 / {len(top_persons)}人")
    print(f"  欠落率: {report['missing_rate']:.1%}")
    print()
    print(f"レポート: {REPORT_PATH}")

    # 上位10件を表示
    print()
    print("【転機欠落人物（上位10件）】")
    for r in missing_results[:10]:
        print(f"  {r['person_name']} (score={r['celebrity_score_v2']:.1f}, eps={r['episode_count']})")
        if r["specific_missing"]:
            print(f"    欠落: {', '.join(r['specific_missing'][:3])}")
        elif r["critical_missing"]:
            print(f"    欠落: {', '.join(r['critical_missing'][:3])}")

    return report


if __name__ == "__main__":
    main()
