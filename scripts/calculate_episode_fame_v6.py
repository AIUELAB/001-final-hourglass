#!/usr/bin/env python3
"""
Episode Fame Score v6 算出スクリプト

案A: バランス重視
- person_fame: 30%
- llm_quality: 25%
- historical_impact: 20%
- pv_signal: 15%
- episode_bonus: 10%

使用方法:
    # ドライラン（差分確認のみ）
    python scripts/calculate_episode_fame_v6.py

    # 実行（CSV更新）
    python scripts/calculate_episode_fame_v6.py --execute
"""

import argparse
import csv
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.score.episode_fame_v6.scorer import (
    EpisodeFameV6Scorer,
    apply_bias_control,
)
from scripts.score.episode_fame_v6.config import ANCHOR_PATTERNS

CSV_PATH = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
REPORTS_DIR = PROJECT_ROOT / "src/reports/logs"


def load_csv() -> tuple[list[dict], list[str]]:
    """CSVを読み込み"""
    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    return rows, fieldnames


def save_csv(rows: list[dict], fieldnames: list[str]) -> None:
    """CSVを保存"""
    with open(CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def add_columns_if_needed(fieldnames: list[str]) -> list[str]:
    """必要なカラムを追加"""
    new_cols = [
        "episode_fame_v6",
        "episode_fame_tier_v6",
        "episode_fame_v6_updated_at",
    ]
    for col in new_cols:
        if col not in fieldnames:
            fieldnames.append(col)
    return fieldnames


def validate_anchors(ranked_episodes: list[dict], top_n: int = 50) -> dict:
    """アンカー集合との一致を検証"""
    top_ids = {ep["episode_id"] for ep in ranked_episodes[:top_n]}
    top_names = {ep["person_name"] for ep in ranked_episodes[:top_n]}
    top_texts = [ep["episode_text"] for ep in ranked_episodes[:top_n]]

    results = {"found": [], "missing": []}

    for name, keyword in ANCHOR_PATTERNS["tier1_must_top50"]:
        found = False
        for i, ep in enumerate(ranked_episodes[:top_n]):
            if name in ep["person_name"] and keyword in ep["episode_text"]:
                results["found"].append((name, keyword, i + 1))
                found = True
                break
        if not found:
            results["missing"].append((name, keyword))

    return results


def main():
    parser = argparse.ArgumentParser(description="Episode Fame v6 スコア算出")
    parser.add_argument("--execute", action="store_true", help="CSV更新を実行")
    args = parser.parse_args()

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print("=" * 60)
    print("【Episode Fame v6 算出】")
    print("=" * 60)
    print(f"モード: {'★実行★' if args.execute else 'ドライラン'}")
    print()

    # CSV読み込み
    print("CSVデータ読み込み中...")
    rows, fieldnames = load_csv()
    print(f"エピソード数: {len(rows)}")

    # カラム追加
    fieldnames = add_columns_if_needed(fieldnames)

    # スコアラー初期化
    print("正規化パラメータ計算中...")
    scorer = EpisodeFameV6Scorer(rows)

    # 全エピソードをスコアリング
    print("スコア算出中...")
    for row in rows:
        breakdown = scorer.score_episode(row)
        row["episode_fame_v6"] = round(breakdown.total_score, 2)
        row["episode_fame_tier_v6"] = breakdown.tier
        row["episode_fame_v6_updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # スコア順にソート
    ranked = sorted(rows, key=lambda r: float(r.get("episode_fame_v6", 0)), reverse=True)

    # バイアス制御適用
    print("同一人物制限適用中...")
    ranked_controlled = apply_bias_control(ranked)

    # 統計
    scores = [float(r.get("episode_fame_v6", 0)) for r in rows]
    print("\n=== スコア統計 ===")
    print(f"  min: {min(scores):.1f}, max: {max(scores):.1f}, avg: {sum(scores)/len(scores):.1f}")

    # Top10表示
    print("\n=== Top10 (バイアス制御後) ===")
    for i, ep in enumerate(ranked_controlled[:10], 1):
        score = float(ep.get("episode_fame_v6", 0))
        name = ep.get("person_name", "")[:20]
        text = ep.get("episode_text", "")[:30]
        print(f"{i:2d}. {score:5.1f} | {name:20s} | {text}...")

    # 多様性チェック
    top100_persons = [ep.get("person_id") for ep in ranked_controlled[:100]]
    unique_persons = len(set(top100_persons))
    print("\n=== 多様性 ===")
    print(f"Top100ユニーク人物数: {unique_persons}/100")

    person_counts = Counter(top100_persons)
    print("Top5人物（出現回数）:")
    for pid, cnt in person_counts.most_common(5):
        name = next((ep["person_name"] for ep in rows if ep["person_id"] == pid), pid)
        print(f"  {name}: {cnt}件")

    # アンカー検証
    print("\n=== アンカー検証 (Top50) ===")
    anchor_results = validate_anchors(ranked_controlled, top_n=50)
    print(f"発見: {len(anchor_results['found'])}/10")
    for name, kw, rank in anchor_results["found"][:5]:
        print(f"  ✓ {name} ({kw}) → {rank}位")
    if anchor_results["missing"]:
        print(f"未発見: {len(anchor_results['missing'])}")
        for name, kw in anchor_results["missing"][:3]:
            print(f"  ✗ {name} ({kw})")

    # v1/v2との比較
    print("\n=== バージョン比較 (Top10重複) ===")
    v1_top10 = set(
        ep["episode_id"]
        for ep in sorted(rows, key=lambda r: float(r.get("episode_fame_score", 0) or 0), reverse=True)[:10]
    )
    v2_top10 = set(
        ep["episode_id"]
        for ep in sorted(rows, key=lambda r: float(r.get("episode_fame_v2", 0) or 0), reverse=True)[:10]
    )
    v6_top10 = set(ep["episode_id"] for ep in ranked_controlled[:10])
    print(f"  v1∩v6: {len(v1_top10 & v6_top10)}/10")
    print(f"  v2∩v6: {len(v2_top10 & v6_top10)}/10")

    # レポート保存
    report_path = REPORTS_DIR / f"episode_fame_v6_{timestamp}.csv"
    with open(report_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["rank", "episode_id", "person_name", "score_v6", "tier_v6", "episode_text"]
        )
        writer.writeheader()
        for i, ep in enumerate(ranked_controlled[:100], 1):
            writer.writerow(
                {
                    "rank": i,
                    "episode_id": ep.get("episode_id", ""),
                    "person_name": ep.get("person_name", ""),
                    "score_v6": ep.get("episode_fame_v6", 0),
                    "tier_v6": ep.get("episode_fame_tier_v6", 0),
                    "episode_text": ep.get("episode_text", "")[:100],
                }
            )
    print(f"\nレポート: {report_path}")

    # 実行モード
    if args.execute:
        print("\nCSV更新中...")
        save_csv(rows, fieldnames)
        print(f"✓ 更新完了: {CSV_PATH}")
    else:
        print("\n💡 ドライラン完了。--execute で更新を適用")

    print()
    print("=" * 60)


if __name__ == "__main__":
    main()
