#!/usr/bin/env python3
"""
ランキング逆転検出ツール

同一人物内で「重要イベントっぽいのに下位」な逆転候補を検出
EP-3947C4DE（アインシュタイン奇跡の年）問題の再発防止
"""

import csv
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

CSV_PATH = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")
REPORT_PATH = Path("src/reports/ranking_inversions_report.json")

# 重要イベントキーワード
IMPORTANT_KEYWORDS = [
    "ノーベル賞", "ノーベル平和賞", "世界初", "史上初", "奇跡の年",
    "革命", "歴史的", "画期的", "大統領", "首相", "金メダル",
    "アカデミー賞", "グラミー賞", "発見", "発明", "創業", "独立",
]

# 逆転判定閾値
MIN_IMPORTANT_SCORE = 85.0  # 重要イベントは最低これ以上あるべき
MAX_RANK_FOR_IMPORTANT = 2  # 重要イベントは2位以内であるべき


def detect_inversions():
    """逆転候補を検出"""
    with open(CSV_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # 人物ごとにグループ化
    by_person = defaultdict(list)
    for r in rows:
        pid = r.get("person_id")
        if pid:
            by_person[pid].append(r)

    inversions = []

    for pid, episodes in by_person.items():
        if len(episodes) < 2:
            continue

        person_name = episodes[0].get("person_name", "不明")

        # v6スコア順にソート
        sorted_eps = sorted(
            episodes,
            key=lambda x: float(x.get("episode_fame_v6") or 0),
            reverse=True,
        )

        # 各エピソードについて逆転チェック
        for rank, ep in enumerate(sorted_eps, 1):
            text = ep.get("episode_text", "")
            v6 = float(ep.get("episode_fame_v6") or 0)
            col30 = float(ep.get("episode_fame_score") or 0)

            # 重要キーワードを含むか
            found_keywords = [kw for kw in IMPORTANT_KEYWORDS if kw in text]

            if found_keywords:
                # 重要イベントなのに順位が低い場合
                is_inversion = False
                reason = []

                if rank > MAX_RANK_FOR_IMPORTANT:
                    is_inversion = True
                    reason.append(f"v6順位が{rank}位（2位以内期待）")

                if v6 < MIN_IMPORTANT_SCORE:
                    is_inversion = True
                    reason.append(f"v6スコアが{v6:.1f}（85以上期待）")

                # col30がv6と大きく乖離している場合
                if abs(col30 - v6) > 10:
                    is_inversion = True
                    reason.append(f"col30({col30:.1f})とv6({v6:.1f})が乖離")

                if is_inversion:
                    inversions.append({
                        "person_id": pid,
                        "person_name": person_name,
                        "episode_id": ep.get("\ufeffepisode_id") or ep.get("episode_id"),
                        "age": ep.get("age"),
                        "keywords": found_keywords,
                        "v6_score": v6,
                        "v6_rank": rank,
                        "col30_score": col30,
                        "reason": reason,
                        "text_head": text[:80] + "...",
                    })

    return inversions


def main():
    inversions = detect_inversions()

    report = {
        "timestamp": datetime.now().isoformat(),
        "total_inversions": len(inversions),
        "high_priority": [i for i in inversions if len(i["reason"]) >= 2],
        "medium_priority": [i for i in inversions if len(i["reason"]) == 1],
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"=== ランキング逆転検出結果 ===")
    print(f"検出件数: {len(inversions)}")
    print(f"  高優先度: {len(report['high_priority'])}")
    print(f"  中優先度: {len(report['medium_priority'])}")
    print(f"\nレポート: {REPORT_PATH}")

    if report["high_priority"]:
        print(f"\n【高優先度の例（最大5件）】")
        for inv in report["high_priority"][:5]:
            print(f"  {inv['person_name']} ({inv['episode_id']})")
            print(f"    キーワード: {inv['keywords']}")
            print(f"    理由: {inv['reason']}")


if __name__ == "__main__":
    main()
