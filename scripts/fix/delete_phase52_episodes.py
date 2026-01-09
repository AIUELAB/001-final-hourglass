#!/usr/bin/env python3
"""
Phase 52: MEDIUM重複エピソードの削除（ベティ・ホワイト）

削除対象:
- EP-70278EAEE644: ベティ・ホワイト 92歳（ギネス記録重複、95歳EPを残す）
- EP-000002726: ベティ・ホワイト 93歳（ギネス記録重複、低スコア）

残す:
- EP-251219D0897C: ベティ・ホワイト 95歳（最高齢で活躍、同率最高スコア8.09）
"""

import csv
import json
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
MASTER_CSV = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
LOG_PATH = PROJECT_ROOT / "src/reports/logs/phase52_deleted_episodes.json"

EPISODES_TO_DELETE = [
    "EP-70278EAEE644",  # ベティ・ホワイト 92歳（ギネス記録重複）
    "EP-000002726",  # ベティ・ホワイト 93歳（ギネス記録重複、低スコア）
]


def main():
    print("=" * 60)
    print("Phase 52: MEDIUM重複エピソード削除（ベティ・ホワイト）")
    print("=" * 60)

    # 読み込み
    with open(MASTER_CSV, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    original_count = len(rows)
    print(f"元のエピソード数: {original_count}")

    # 削除対象を抽出・ログ
    deleted_episodes = []
    remaining_rows = []

    for row in rows:
        episode_id = row.get("episode_id", "")
        if episode_id in EPISODES_TO_DELETE:
            deleted_episodes.append(
                {
                    "episode_id": episode_id,
                    "person_name": row.get("person_name", ""),
                    "age": row.get("age", ""),
                    "composite_score": row.get("composite_score", ""),
                    "reason": get_deletion_reason(episode_id),
                    "episode_text_snippet": row.get("episode_text", "")[:200],
                }
            )
        else:
            remaining_rows.append(row)

    # ログ保存
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    log_data = {
        "deleted_at": datetime.now().isoformat(),
        "phase": "52",
        "reason": "MEDIUM重複（ベティ・ホワイト ギネス記録3件→1件）",
        "kept_episode": "EP-251219D0897C (95歳, score: 8.09)",
        "total_deleted": len(deleted_episodes),
        "deleted_episodes": deleted_episodes,
    }
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)

    print(f"\n削除対象: {len(deleted_episodes)}件")
    for ep in deleted_episodes:
        print(f"  - {ep['episode_id']}: {ep['person_name']} ({ep['age']}歳)")
        print(f"    スコア: {ep['composite_score']}, 理由: {ep['reason']}")

    print("\n残すEP: EP-251219D0897C (95歳, score: 8.09)")

    # CSV書き戻し
    with open(MASTER_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(remaining_rows)

    final_count = len(remaining_rows)
    print(f"\n削除後のエピソード数: {final_count}")
    print(f"削減: {original_count - final_count}件")
    print(f"\n✅ ログ: {LOG_PATH}")


def get_deletion_reason(episode_id: str) -> str:
    reasons = {
        "EP-70278EAEE644": "ギネス記録重複（95歳EPを残す）",
        "EP-000002726": "ギネス記録重複（低スコア7.86）",
    }
    return reasons.get(episode_id, "不明")


if __name__ == "__main__":
    main()
