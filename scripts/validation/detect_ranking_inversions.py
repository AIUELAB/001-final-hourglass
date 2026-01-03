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

# 重要イベントキーワード（ティア別）
# Tier1: 厳格チェック（ノーベル賞等は85点以上、2位以内期待）
TIER1_KEYWORDS = [
    "ノーベル賞",
    "ノーベル平和賞",
    "ノーベル物理学賞",
    "ノーベル化学賞",
    "世界初",
    "史上初",
    "奇跡の年",
    "アカデミー賞",
    "グラミー賞",
    "大統領就任",
    "首相就任",
    "オリンピック金メダル",
]

# Tier2: 中程度チェック（70点以上、3位以内期待）
TIER2_KEYWORDS = [
    "歴史的",
    "画期的",
    "金メダル",
    "大統領",
    "首相",
    "発明",
    "創業",
    "独立運動",
]

# Tier3: 緩和チェック（60点以上、5位以内期待）
# 偽陽性が多いキーワード（比喩的使用・個人的体験が多い）
TIER3_KEYWORDS = [
    "発見",
    "革命",
    "独立",
]

# ティア別閾値
TIER_THRESHOLDS = {
    1: {"min_score": 78.0, "max_rank": 3},  # 80→78, 2→3に緩和（複数重要EPがある人物に対応）
    2: {"min_score": 70.0, "max_rank": 3},
    3: {"min_score": 60.0, "max_rank": 5},
}


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

            # ティア別にキーワードチェック
            tier = None
            found_keywords = []

            for kw in TIER1_KEYWORDS:
                if kw in text:
                    tier = 1
                    found_keywords.append(kw)
                    break  # Tier1が見つかれば最優先

            if tier is None:
                for kw in TIER2_KEYWORDS:
                    if kw in text:
                        tier = 2
                        found_keywords.append(kw)
                        break

            if tier is None:
                for kw in TIER3_KEYWORDS:
                    if kw in text:
                        tier = 3
                        found_keywords.append(kw)

            if found_keywords and tier:
                thresholds = TIER_THRESHOLDS[tier]
                min_score = thresholds["min_score"]
                max_rank = thresholds["max_rank"]

                # 重要イベントなのに順位が低い場合
                is_inversion = False
                reason = []

                if rank > max_rank:
                    is_inversion = True
                    reason.append(f"v6順位が{rank}位（{max_rank}位以内期待）")

                if v6 < min_score:
                    is_inversion = True
                    reason.append(f"v6スコアが{v6:.1f}（{min_score}以上期待）")

                # col30がv6と大きく乖離している場合
                if abs(col30 - v6) > 10:
                    is_inversion = True
                    reason.append(f"col30({col30:.1f})とv6({v6:.1f})が乖離")

                if is_inversion:
                    inversions.append(
                        {
                            "person_id": pid,
                            "person_name": person_name,
                            "episode_id": ep.get("\ufeffepisode_id") or ep.get("episode_id"),
                            "age": ep.get("age"),
                            "keywords": found_keywords,
                            "tier": tier,
                            "v6_score": v6,
                            "v6_rank": rank,
                            "col30_score": col30,
                            "reason": reason,
                            "text_head": text[:80] + "...",
                        }
                    )

    return inversions


def main():
    inversions = detect_inversions()

    # 高優先度: Tier1キーワードで逆転 or 複数理由
    # 中優先度: Tier2で逆転 or 1理由のみ
    # 低優先度: Tier3で逆転
    high_priority = [i for i in inversions if i.get("tier") == 1 or len(i["reason"]) >= 2]
    medium_priority = [i for i in inversions if i.get("tier") == 2 and len(i["reason"]) == 1]
    low_priority = [i for i in inversions if i.get("tier") == 3 and len(i["reason"]) == 1]

    report = {
        "timestamp": datetime.now().isoformat(),
        "total_inversions": len(inversions),
        "high_priority": high_priority,
        "medium_priority": medium_priority,
        "low_priority": low_priority,
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("=== ランキング逆転検出結果 ===")
    print(f"検出件数: {len(inversions)}")
    print(f"  高優先度（Tier1 or 複数理由）: {len(report['high_priority'])}")
    print(f"  中優先度（Tier2）: {len(report['medium_priority'])}")
    print(f"  低優先度（Tier3）: {len(report['low_priority'])}")
    print(f"\nレポート: {REPORT_PATH}")

    if report["high_priority"]:
        print("\n【高優先度の例（最大5件）】")
        for inv in report["high_priority"][:5]:
            print(f"  {inv['person_name']} ({inv['episode_id']}) [Tier{inv.get('tier', '?')}]")
            print(f"    キーワード: {inv['keywords']}")
            print(f"    理由: {inv['reason']}")


if __name__ == "__main__":
    main()
