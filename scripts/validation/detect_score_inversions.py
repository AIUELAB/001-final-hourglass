#!/usr/bin/env python3
"""
スコア逆転検出スクリプト

同一人物内で「客観イベントが強いのに低順位」な逆転候補を検出

検出ロジック:
- 社会的影響度キーワード（万部、ベストセラー、金メダル、ノーベル等）を含むエピソードが
  同一人物内で上位にいない場合に警告
"""

import csv
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


CSV_PATH = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
REPORT_PATH = PROJECT_ROOT / "src" / "reports" / "score_inversions.md"

# 社会的影響度の高いキーワード
HIGH_IMPACT_KEYWORDS = [
    # 販売実績
    "万部",
    "ミリオンセラー",
    "ベストセラー",
    "大ヒット",
    "興行収入",
    # 受賞・記録
    "ノーベル賞",
    "アカデミー賞",
    "金メダル",
    "世界記録",
    "日本記録",
    # 歴史的イベント
    "世界初",
    "史上初",
    "日本初",
    "革命",
    "独立",
    "解放",
    # 役職
    "大統領",
    "首相",
    "CEO",
    "創業者",
]


def detect_inversions(all_eps: list[dict]) -> list[dict]:
    """逆転候補を検出"""
    inversions = []

    # 人物別にグループ化
    by_person = defaultdict(list)
    for ep in all_eps:
        person_id = ep.get("person_id", "")
        if person_id:
            by_person[person_id].append(ep)

    for person_id, eps in by_person.items():
        if len(eps) < 2:
            continue

        # v6スコアでソート
        sorted_eps = sorted(eps, key=lambda x: float(x.get("episode_fame_v6") or 0), reverse=True)

        # 各エピソードの高影響度キーワードをカウント
        for rank, ep in enumerate(sorted_eps, 1):
            text = ep.get("episode_text", "")
            matched_keywords = [kw for kw in HIGH_IMPACT_KEYWORDS if kw in text]

            # 高影響度キーワードがあるのに2位以下の場合
            if matched_keywords and rank > 1:
                top_ep = sorted_eps[0]
                top_keywords = [kw for kw in HIGH_IMPACT_KEYWORDS if kw in top_ep.get("episode_text", "")]

                # 1位より多くのキーワードを持っているのに低順位
                if len(matched_keywords) > len(top_keywords):
                    inversions.append(
                        {
                            "person_name": ep.get("person_name", ""),
                            "person_id": person_id,
                            "episode_id": ep.get("episode_id", ""),
                            "rank": rank,
                            "v6_score": float(ep.get("episode_fame_v6") or 0),
                            "keywords": matched_keywords,
                            "top_episode_id": top_ep.get("episode_id", ""),
                            "top_v6_score": float(top_ep.get("episode_fame_v6") or 0),
                            "top_keywords": top_keywords,
                        }
                    )

    return inversions


def generate_report(inversions: list[dict]) -> str:
    """レポート生成"""
    lines = [
        "# スコア逆転検出レポート",
        "",
        f"検出日時: {__import__('datetime').datetime.now().isoformat()}",
        "",
        f"## 検出件数: {len(inversions)}件",
        "",
    ]

    if not inversions:
        lines.append("✅ 逆転候補なし")
    else:
        lines.append("| 人物名 | 逆転EP | 順位 | v6 | キーワード | 1位EP | 1位v6 |")
        lines.append("|--------|--------|------|-----|-----------|-------|-------|")
        for inv in inversions[:20]:  # 上位20件
            keywords = ", ".join(inv["keywords"][:3])
            lines.append(
                f"| {inv['person_name']} | {inv['episode_id']} | {inv['rank']}位 | "
                f"{inv['v6_score']:.2f} | {keywords} | {inv['top_episode_id']} | {inv['top_v6_score']:.2f} |"
            )

    return "\n".join(lines)


def main():
    print("=== スコア逆転検出 ===")

    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        all_eps = list(reader)

    print(f"総エピソード数: {len(all_eps)}")

    inversions = detect_inversions(all_eps)
    print(f"逆転候補: {len(inversions)}件")

    report = generate_report(inversions)

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"レポート出力: {REPORT_PATH}")

    # 結果サマリー
    if inversions:
        print("\n⚠️ 逆転候補あり（上位5件）:")
        for inv in inversions[:5]:
            print(f"  {inv['person_name']} / {inv['episode_id']} (順位{inv['rank']}) キーワード: {inv['keywords']}")
    else:
        print("\n✅ 逆転候補なし")


if __name__ == "__main__":
    main()
