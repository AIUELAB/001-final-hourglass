#!/usr/bin/env python3
"""
validate_importance_score.py - 重要度スコア整合性検証

目的: 具体的偉業エピソードが物語的転機エピソードより
      importance_scoreが低い場合を検出する

ルール:
- ワールドシリーズ制覇、本塁打王、MVP等の具体的偉業は importance >= 8.5
- 同一人物内で「失敗/挫折」エピソードより偉業エピソードが低いのは異常

使用例:
    python scripts/validation/validate_importance_score.py
    python scripts/validation/validate_importance_score.py --fix
"""

import csv
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Optional

# 具体的偉業キーワード（高importance_scoreを期待）
# ティア1: 最高レベル偉業（importance >= 9.5）
TIER1_ACHIEVEMENTS = {
    "ワールドシリーズ制覇": 9.5,
    "ワールドシリーズ優勝": 9.5,
    "三冠王": 9.5,
    "ノーベル賞": 10.0,
}

# ティア2: 高レベル偉業（importance >= 9.0）
TIER2_ACHIEVEMENTS = {
    "本塁打王": 9.0,
    "MVP": 9.0,  # ただし転機文脈では8.5
    "殿堂入り": 9.5,
}

ACHIEVEMENT_KEYWORDS = {
    # 野球
    "ワールドシリーズ制覇": 9.5,
    "ワールドシリーズ優勝": 9.5,
    "本塁打王": 9.0,
    "三冠王": 9.5,
    "MVP": 9.0,
    "サイ・ヤング賞": 9.0,
    "殿堂入り": 9.5,
    "ノーヒットノーラン": 8.5,
    "完全試合": 9.0,
    # 一般スポーツ
    "オリンピック金メダル": 9.5,
    "世界記録": 9.0,
    "世界選手権優勝": 8.5,
    # 学術・科学
    "ノーベル賞": 10.0,
    "ノーベル物理学賞": 10.0,
    "ノーベル化学賞": 10.0,
    "ノーベル医学賞": 10.0,
    "ノーベル文学賞": 10.0,
    "ノーベル平和賞": 10.0,
    "フィールズ賞": 9.5,
    "奇跡の年": 10.0,  # アインシュタイン1905年
    "E=mc²": 10.0,  # 質量エネルギー等価
    "特殊相対性理論": 10.0,
    "一般相対性理論": 10.0,
    "相対性理論": 9.5,
    "量子力学": 9.5,
    "万有引力": 9.5,
    "進化論": 9.5,
    "DNA二重らせん": 9.5,
    # ビジネス
    "IPO": 8.0,
    "時価総額1兆": 9.0,
    # 芸術
    "アカデミー賞": 9.0,
    "グラミー賞": 8.5,
}

# 物語的転機キーワード（高importanceが不適切な可能性）
NARRATIVE_KEYWORDS = [
    "失敗",
    "挫折",
    "断念",
    "落選",
    "敗北",
    "転機",
    "きっかけ",
    "原点",
    "始まり",
    "悩み",
    "苦悩",
    "葛藤",
]


def load_episodes(csv_path: Path) -> list[dict]:
    """CSVからエピソードを読み込む"""
    episodes = []
    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            episodes.append(row)
    return episodes


def detect_achievement(text: str) -> tuple[bool, str, float]:
    """テキストから具体的偉業を検出"""
    for keyword, expected_score in ACHIEVEMENT_KEYWORDS.items():
        if keyword in text:
            return True, keyword, expected_score
    return False, "", 0.0


def detect_narrative(text: str) -> tuple[bool, str]:
    """テキストから物語的転機を検出"""
    for keyword in NARRATIVE_KEYWORDS:
        if keyword in text:
            return True, keyword
    return False, ""


def validate_importance_scores(csv_path: Path) -> dict:
    """importance_scoreの整合性を検証"""
    episodes = load_episodes(csv_path)

    # 人物ごとにグループ化
    person_episodes: dict[str, list[dict]] = {}
    for ep in episodes:
        person_id = ep.get("person_id", "")
        if person_id:
            if person_id not in person_episodes:
                person_episodes[person_id] = []
            person_episodes[person_id].append(ep)

    issues = []
    suggestions = []

    for person_id, eps in person_episodes.items():
        # 各エピソードを分類
        achievements = []
        narratives = []

        for ep in eps:
            text = ep.get("episode_text", "")
            importance = float(ep.get("episode_importance_score", 0) or 0)
            ep_id = ep.get("episode_id", "")

            is_achievement, ach_keyword, expected = detect_achievement(text)
            is_narrative, nar_keyword = detect_narrative(text)

            if is_achievement:
                achievements.append(
                    {
                        "episode_id": ep_id,
                        "keyword": ach_keyword,
                        "importance": importance,
                        "expected": expected,
                        "text": text[:100],
                    }
                )

            if is_narrative and not is_achievement:
                narratives.append(
                    {
                        "episode_id": ep_id,
                        "keyword": nar_keyword,
                        "importance": importance,
                        "text": text[:100],
                    }
                )

        # 問題検出: 偉業が期待値より低い
        for ach in achievements:
            if ach["importance"] < ach["expected"]:
                issues.append(
                    {
                        "type": "achievement_undervalued",
                        "person_id": person_id,
                        "person_name": eps[0].get("person_name", ""),
                        "episode_id": ach["episode_id"],
                        "keyword": ach["keyword"],
                        "current_importance": ach["importance"],
                        "expected_importance": ach["expected"],
                        "text_preview": ach["text"],
                    }
                )
                suggestions.append(
                    {
                        "episode_id": ach["episode_id"],
                        "field": "episode_importance_score",
                        "current": ach["importance"],
                        "suggested": ach["expected"],
                        "reason": f"「{ach['keyword']}」は高い歴史的重要性を持つ",
                    }
                )

        # 問題検出: 物語的転機が偉業より高い
        if achievements and narratives:
            max_narrative = max(n["importance"] for n in narratives)
            for ach in achievements:
                if ach["importance"] < max_narrative:
                    # 同一人物内で物語が偉業より高い
                    narrative_ep = next(n for n in narratives if n["importance"] == max_narrative)
                    issues.append(
                        {
                            "type": "narrative_over_achievement",
                            "person_id": person_id,
                            "person_name": eps[0].get("person_name", ""),
                            "achievement_ep": ach["episode_id"],
                            "achievement_importance": ach["importance"],
                            "narrative_ep": narrative_ep["episode_id"],
                            "narrative_importance": narrative_ep["importance"],
                            "narrative_keyword": narrative_ep["keyword"],
                        }
                    )

    return {
        "total_episodes": len(episodes),
        "total_persons": len(person_episodes),
        "issues_count": len(issues),
        "issues": issues,
        "suggestions": suggestions,
        "checked_at": datetime.now().isoformat(),
    }


def apply_fixes(csv_path: Path, suggestions: list[dict], issues: list[dict] = None) -> int:
    """修正を適用"""
    # 修正マップを作成
    fix_map = {}
    for s in suggestions:
        fix_map[s["episode_id"]] = s["suggested"]

    # narrative_over_achievement問題も修正
    if issues:
        for issue in issues:
            if issue["type"] == "narrative_over_achievement":
                # 物語的転機エピソードのimportanceを下げる
                nar_ep = issue["narrative_ep"]
                nar_imp = issue["narrative_importance"]
                ach_imp = issue["achievement_importance"]
                # 物語は偉業より0.5以上低くする
                if nar_imp > ach_imp:
                    new_imp = max(7.0, ach_imp - 0.5)
                    fix_map[nar_ep] = new_imp

    if not fix_map:
        return 0

    # CSVを読み込み
    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    # 修正を適用
    fixed_count = 0
    for row in rows:
        ep_id = row.get("episode_id", "")
        if ep_id in fix_map:
            row["episode_importance_score"] = str(fix_map[ep_id])
            fixed_count += 1

    # CSVを書き戻し
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return fixed_count


def main():
    import argparse

    parser = argparse.ArgumentParser(description="importance_score整合性検証")
    parser.add_argument("--fix", action="store_true", help="検出した問題を自動修正")
    parser.add_argument(
        "--csv", type=Path, default=Path("preserved/data/MASTER_EPISODES_CURRENT.csv"), help="CSVファイルパス"
    )
    parser.add_argument(
        "--output", type=Path, default=Path("src/reports/importance_score_validation.json"), help="レポート出力先"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("importance_score 整合性検証")
    print("=" * 60)

    result = validate_importance_scores(args.csv)

    print(f"\n総エピソード数: {result['total_episodes']}")
    print(f"総人物数: {result['total_persons']}")
    print(f"検出された問題: {result['issues_count']}件")

    if result["issues"]:
        print("\n--- 問題一覧 (上位10件) ---")
        for issue in result["issues"][:10]:
            if issue["type"] == "achievement_undervalued":
                print(f"  [{issue['episode_id']}] {issue['person_name']}")
                print(f"    「{issue['keyword']}」importance={issue['current_importance']}")
                print(f"    期待値: {issue['expected_importance']}")
            elif issue["type"] == "narrative_over_achievement":
                print(f"  [{issue['achievement_ep']}] vs [{issue['narrative_ep']}]")
                print(f"    偉業({issue['achievement_importance']}) < 物語({issue['narrative_importance']})")

    # レポート保存
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\nレポート保存: {args.output}")

    if args.fix and (result["suggestions"] or result["issues"]):
        print("\n--- 自動修正を実行 ---")
        fixed = apply_fixes(args.csv, result["suggestions"], result["issues"])
        print(f"修正完了: {fixed}件")

    return 0 if result["issues_count"] == 0 else 1


if __name__ == "__main__":
    exit(main())
