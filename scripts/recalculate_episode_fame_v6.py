#!/usr/bin/env python3
"""
Episode Fame v6 全件再計算スクリプト

修正内容:
1. episode_countを正しい値に修正
2. TYPE_MAPPINGを適用してタイプボーナスを有効化
3. HISTORICAL_KEYWORDS拡充を反映
"""

import csv
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.score.episode_fame_v6.scorer import EpisodeFameV6Scorer

CSV_PATH = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
BACKUP_PATH = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_BACKUP_20260103.csv"


def main():
    print("=== Episode Fame v6 全件再計算 ===")
    print(f"開始: {datetime.now()}")
    print()

    # CSV読み込み
    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        all_eps = list(reader)

    print(f"総エピソード数: {len(all_eps)}")

    # バックアップ作成
    print(f"バックアップ作成: {BACKUP_PATH}")
    with open(BACKUP_PATH, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_eps)

    # Step 1: episode_count修正
    print("\n[Step 1] episode_count修正...")
    actual_counts = Counter(e.get("person_id", "") for e in all_eps)

    count_fixed = 0
    for ep in all_eps:
        person_id = ep.get("person_id", "")
        actual = actual_counts[person_id]
        current = int(float(ep.get("episode_count") or 0))
        if current != actual:
            ep["episode_count"] = str(actual)
            count_fixed += 1

    print(f"  episode_count修正: {count_fixed}件")

    # Step 2: episode_fame_v6再計算
    print("\n[Step 2] episode_fame_v6再計算...")
    scorer = EpisodeFameV6Scorer(all_eps)

    score_changed = 0
    for i, ep in enumerate(all_eps):
        breakdown = scorer.score_episode(ep)

        old_score = float(ep.get("episode_fame_v6") or 0)
        new_score = round(breakdown.total_score, 2)
        new_tier = breakdown.tier

        if abs(old_score - new_score) > 0.01:
            score_changed += 1

        ep["episode_fame_v6"] = str(new_score)
        ep["episode_fame_tier_v6"] = str(new_tier)
        ep["episode_fame_v6_updated_at"] = datetime.now().isoformat()

        if (i + 1) % 2000 == 0:
            print(f"  処理中: {i + 1}/{len(all_eps)}")

    print(f"  スコア変動: {score_changed}件")

    # Step 3: CSV書き出し
    print("\n[Step 3] CSV書き出し...")
    with open(CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_eps)

    print(f"  書き出し完了: {CSV_PATH}")

    # Step 4: 村上春樹の結果確認
    print("\n[Step 4] 村上春樹の結果確認...")
    murakami = [e for e in all_eps if e.get("person_name") == "村上春樹"]
    murakami_sorted = sorted(murakami, key=lambda x: float(x.get("episode_fame_v6") or 0), reverse=True)

    print("  順位 | episode_id | v6スコア | Tier | 本文")
    print("  " + "-" * 70)
    for i, ep in enumerate(murakami_sorted, 1):
        ep_id = ep.get("episode_id", "")
        v6 = ep.get("episode_fame_v6", "0")
        tier = ep.get("episode_fame_tier_v6", "0")
        text = ep.get("episode_text", "")[:40]
        marker = "⭐" if ep_id == "EP-000002037" else ""
        print(f"  {i}. {ep_id} | {v6} | T{tier} | {text}... {marker}")

    print(f"\n完了: {datetime.now()}")


if __name__ == "__main__":
    main()
