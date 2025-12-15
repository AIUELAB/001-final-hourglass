#!/usr/bin/env python3
"""
肩書き・組織名混入パターンを検出
"""

import pandas as pd
from pathlib import Path


def main():
    csv_path = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")
    df = pd.read_csv(csv_path, encoding="utf-8-sig")

    # 肩書きパターン
    title_patterns = ["建築家・", "画家・", "作曲家・", "映画監督・", "小説家・", "詩人・", "哲学者・"]

    print("=" * 60)
    print("肩書き混入パターン検出")
    print("=" * 60)

    results = []

    for pattern in title_patterns:
        title_entries = df[df["person_name"].str.contains(pattern, na=False, regex=False)]

        for _, row in title_entries.iterrows():
            person_name = row["person_name"]
            person_id = row["person_id"]
            episode_id = row["episode_id"]

            # 肩書きを除去
            clean_name = person_name.replace(pattern, "")

            # クリーン版が存在するか
            clean_entries = df[df["person_name"] == clean_name]

            if len(clean_entries) > 0:
                clean_ids = clean_entries["person_id"].unique()
                clean_ep_count = len(clean_entries)
                results.append(
                    {
                        "contaminated": person_name,
                        "contaminated_id": person_id,
                        "contaminated_ep": episode_id,
                        "clean": clean_name,
                        "clean_id": clean_ids[0],
                        "clean_ep_count": clean_ep_count,
                    }
                )

    if results:
        print(f"\n検出件数: {len(results)}\n")
        for i, r in enumerate(results, 1):
            print(f"{i}. {r['contaminated']} (ID: {r['contaminated_id']}, Ep: {r['contaminated_ep']})")
            print(f"   → {r['clean']} (ID: {r['clean_id']}, {r['clean_ep_count']}ep)\n")
    else:
        print("検出なし")

    print("=" * 60)


if __name__ == "__main__":
    main()
