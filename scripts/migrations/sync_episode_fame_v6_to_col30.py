#!/usr/bin/env python3
"""
episode_fame_score (col30) を episode_fame_v6 (col98) で同期更新

EP-3947C4DE（アインシュタイン奇跡の年）問題の修正
"""

import csv
import shutil
from datetime import datetime
from pathlib import Path

CSV_PATH = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")
BACKUP_PATH = CSV_PATH.with_suffix(f".csv.bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}")


def main():
    # バックアップ作成
    shutil.copy(CSV_PATH, BACKUP_PATH)
    print(f"バックアップ作成: {BACKUP_PATH}")

    # CSV読み込み
    with open(CSV_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    # 同期更新
    updated_count = 0
    for row in rows:
        v6 = row.get("episode_fame_v6")
        col30 = row.get("episode_fame_score")

        if v6 and v6.strip():
            try:
                v6_val = float(v6)
                col30_val = float(col30) if col30 and col30.strip() else 0

                if abs(v6_val - col30_val) > 0.01:
                    row["episode_fame_score"] = str(round(v6_val, 2))
                    updated_count += 1
            except ValueError:
                pass

    # CSV書き出し
    with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"同期完了: {updated_count}件更新")

    # 検証: アインシュタインのスコア確認
    print("\n=== アインシュタイン (P93F1DB1) 検証 ===")
    einstein_eps = [r for r in rows if r.get("person_id") == "P93F1DB1"]
    einstein_sorted = sorted(
        einstein_eps,
        key=lambda x: float(x.get("episode_fame_score") or 0),
        reverse=True,
    )

    for i, ep in enumerate(einstein_sorted, 1):
        eid = ep.get("\ufeffepisode_id") or ep.get("episode_id")
        age = ep.get("age")
        score = ep.get("episode_fame_score")
        print(f"  {i}位: {eid} (age={age}) score={score}")


if __name__ == "__main__":
    main()
