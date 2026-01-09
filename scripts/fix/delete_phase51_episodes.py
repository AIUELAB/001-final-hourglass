#!/usr/bin/env python3
"""
Phase 51: HIGH重複エピソードの削除

削除対象:
- EP-000003504: ヴァージニア・ウルフ 40歳（『灯台へ』は45歳で完成が正確）
- EP-2512181850582521: カーネル・サンダース 86歳（81歳EPと重複内容、低スコア）
- EP-000001915: 司馬遼太郎 76歳（没年72歳なので存在不可能）
"""

import csv
import json
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
MASTER_CSV = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
LOG_PATH = PROJECT_ROOT / "src/reports/logs/phase51_deleted_episodes.json"

EPISODES_TO_DELETE = [
    "EP-000003504",  # ヴァージニア・ウルフ 40歳（45歳が正確）
    "EP-2512181850582521",  # カーネル・サンダース 86歳（重複内容）
    "EP-000001915",  # 司馬遼太郎 76歳（没年超過）
]


def main():
    print("=" * 60)
    print("Phase 51: HIGH重複エピソード削除")
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
        "phase": "51",
        "reason": "HIGH重複（年齢誤り・重複内容・没年超過）",
        "total_deleted": len(deleted_episodes),
        "deleted_episodes": deleted_episodes,
    }
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)

    print(f"\n削除対象: {len(deleted_episodes)}件")
    for ep in deleted_episodes:
        print(f"  - {ep['episode_id']}: {ep['person_name']} ({ep['age']}歳)")
        print(f"    理由: {ep['reason']}")

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
        "EP-000003504": "『灯台へ』は1927年完成、ウルフ45歳。40歳は不正確",
        "EP-2512181850582521": "81歳EPと重複内容（年間25万マイル移動）、低スコア",
        "EP-000001915": "司馬遼太郎は1996年没（72歳）。76歳エピソードは存在不可能",
    }
    return reasons.get(episode_id, "不明")


if __name__ == "__main__":
    main()
