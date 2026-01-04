#!/usr/bin/env python3
"""
スコア逆転検出スクリプト

同一人物内で「客観イベントが強いのに低順位」な逆転候補を検出

検出ロジック:
- 社会的影響度キーワード（万部、ベストセラー、金メダル、ノーベル等）を含むエピソードが
  同一人物内で上位にいない場合に警告

v2改善 (2026-01-04):
- 1位もTier1キーワードを含む場合は逆転としてカウントしない（両方重要なので順位差は許容）
- 差分閾値を導入（5点以上の差がある場合のみ逆転）
"""

import csv
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


CSV_PATH = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
REPORT_PATH = PROJECT_ROOT / "src" / "reports" / "score_inversions.md"

# Tier1: 客観的に最重要（これが低順位なら明らかな逆転）
TIER1_KEYWORDS = [
    # 国際賞・最高賞
    "ノーベル賞",
    "ノーベル物理学賞",
    "ノーベル化学賞",
    "ノーベル文学賞",
    "ノーベル平和賞",
    "ノーベル医学・生理学賞",
    "ノーベル経済学賞",
    "アカデミー賞",
    "グラミー賞",
    "フィールズ賞",
    # オリンピック
    "オリンピック金メダル",
    "金メダル獲得",
    # 政治最高職
    "大統領就任",
    "大統領に就任",
    "首相就任",
    "首相に就任",
    "即位",
    "皇位継承",
    # 歴史的偉業
    "世界初",
    "史上初",
    "世界記録樹立",
]

# Tier2: 重要だが汎用的（逆転検出には使用しない）
# 参考用: "万部", "ベストセラー", "大ヒット", "革命", "独立", "解放", "CEO", "創業者"

# v2改善: 差分閾値（この点差以上の場合のみ逆転とみなす）
SCORE_DIFF_THRESHOLD = 5.0


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

        # 1位のエピソード情報を取得
        top_ep = sorted_eps[0]
        top_v6 = float(top_ep.get("episode_fame_v6") or 0)
        top_text = top_ep.get("episode_text", "")
        top_keywords = [kw for kw in TIER1_KEYWORDS if kw in top_text]

        # 各エピソードの高影響度キーワードをカウント
        for rank, ep in enumerate(sorted_eps, 1):
            if rank == 1:
                continue  # 1位はスキップ

            text = ep.get("episode_text", "")
            matched_keywords = [kw for kw in TIER1_KEYWORDS if kw in text]

            # 高影響度キーワードがあるのに2位以下の場合
            if not matched_keywords:
                continue

            current_v6 = float(ep.get("episode_fame_v6") or 0)
            score_diff = top_v6 - current_v6

            # v2改善: 1位もTier1キーワードを含む場合は逆転としてカウントしない
            if top_keywords:
                continue  # 両方重要なエピソードなので順位差は許容

            # v2改善: 差分が閾値未満の場合も逆転としてカウントしない
            if score_diff < SCORE_DIFF_THRESHOLD:
                continue  # 僅差なので許容

            # 1位より多くのキーワードを持っているのに低順位
            if len(matched_keywords) > len(top_keywords):
                inversions.append(
                    {
                        "person_name": ep.get("person_name", ""),
                        "person_id": person_id,
                        "episode_id": ep.get("episode_id", ""),
                        "rank": rank,
                        "v6_score": current_v6,
                        "keywords": matched_keywords,
                        "top_episode_id": top_ep.get("episode_id", ""),
                        "top_v6_score": top_v6,
                        "top_keywords": top_keywords,
                        "score_diff": score_diff,
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
        lines.append("")
        lines.append("検出条件:")
        lines.append(f"- 差分閾値: {SCORE_DIFF_THRESHOLD}点以上")
        lines.append("- 1位がTier1キーワードを含む場合は除外")
    else:
        lines.append("| 人物名 | 逆転EP | 順位 | v6 | 差分 | キーワード | 1位EP | 1位v6 |")
        lines.append("|--------|--------|------|-----|------|-----------|-------|-------|")
        for inv in inversions[:20]:  # 上位20件
            keywords = ", ".join(inv["keywords"][:3])
            score_diff = inv.get("score_diff", 0)
            lines.append(
                f"| {inv['person_name']} | {inv['episode_id']} | {inv['rank']}位 | "
                f"{inv['v6_score']:.2f} | {score_diff:.2f} | {keywords} | {inv['top_episode_id']} | {inv['top_v6_score']:.2f} |"
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
