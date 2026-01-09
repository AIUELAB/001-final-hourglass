#!/usr/bin/env python3
"""
Phase 48: 死去年違反・人物ID衝突エピソードの削除

削除対象:
- EP-260105225818577416: 竹久夢二 70歳（没年齢49歳超過）
- EP-260105225818578630: 竹久夢二 75歳（没年齢49歳超過）
- EP-260108214102016: 立原正秋 75歳（没年齢52歳超過）
- EP-260108205242597: 木村一八 80歳（人物ID衝突・別人）
"""

import csv
import json
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
MASTER_CSV = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
LOG_PATH = PROJECT_ROOT / "src/reports/logs/phase48_deleted_episodes.json"

EPISODES_TO_DELETE = [
    "EP-260105225818577416",  # 竹久夢二 70歳（没年齢49歳超過）
    "EP-260105225818578630",  # 竹久夢二 75歳（没年齢49歳超過）
    "EP-260108214102016",  # 立原正秋 75歳（没年齢52歳超過）
    "EP-260108205242597",  # 木村一八 80歳（人物ID衝突・別人）
]


def main():
    print("=" * 60)
    print("Phase 48: 死去年違反・人物ID衝突エピソード削除")
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
                    "episode_text_snippet": row.get("episode_text", "")[:200],
                }
            )
        else:
            remaining_rows.append(row)

    # ログ保存
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    log_data = {
        "deleted_at": datetime.now().isoformat(),
        "phase": "48",
        "reason": "死去年違反・人物ID衝突",
        "total_deleted": len(deleted_episodes),
        "deleted_episodes": deleted_episodes,
    }
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)

    print(f"\n削除対象: {len(deleted_episodes)}件")
    for ep in deleted_episodes:
        print(f"  - {ep['episode_id']}: {ep['person_name']} ({ep['age']}歳)")

    # CSV書き戻し
    with open(MASTER_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(remaining_rows)

    final_count = len(remaining_rows)
    print(f"\n削除後のエピソード数: {final_count}")
    print(f"削減: {original_count - final_count}件")
    print(f"\n✅ ログ: {LOG_PATH}")


if __name__ == "__main__":
    main()
