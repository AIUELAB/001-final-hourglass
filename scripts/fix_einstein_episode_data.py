#!/usr/bin/env python3
"""
EP-3947C4DE（アインシュタイン 奇跡の年）のperson-level項目修正

問題: テンプレートコピーにより誤ったcelebrity_score_v2が設定された
修正: 同一人物の他エピソードから正しい値を取得して更新
"""

import csv
from pathlib import Path


CSV_PATH = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")
TARGET_EPISODE_ID = "EP-3947C4DE"
PERSON_ID = "P93F1DB1"  # アインシュタイン

# person-level項目（同一人物で統一すべき項目）
PERSON_LEVEL_COLUMNS = [
    "celebrity_score_v2",
    "sitelinks_count",
    "multi_lang_pv",
    "fame_score_v2",
    "fame_score_v3",
    "fame_rank",
    "fame_rank_v3",
    "celebrity_rank_v2",
    "google_hits",
    "fame_score_japan",
    "wikipedia_pv",
]


def main():
    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames

    # 同一人物の他エピソードから正しい値を取得
    reference_row = None
    target_idx = None

    for idx, row in enumerate(rows):
        if row.get("person_id") == PERSON_ID:
            if row.get("episode_id") == TARGET_EPISODE_ID:
                target_idx = idx
            elif reference_row is None:
                reference_row = row

    if target_idx is None:
        print(f"エラー: {TARGET_EPISODE_ID} が見つかりません")
        return

    if reference_row is None:
        print(f"エラー: {PERSON_ID} の参照エピソードが見つかりません")
        return

    target_row = rows[target_idx]

    print(f"=== {TARGET_EPISODE_ID} 修正 ===")
    print(f"参照元: {reference_row['episode_id']}")
    print()
    print("修正内容:")

    changes = []
    for col in PERSON_LEVEL_COLUMNS:
        if col in fieldnames:
            old_val = target_row.get(col, "")
            new_val = reference_row.get(col, "")
            if old_val != new_val:
                print(f"  {col}: {old_val} → {new_val}")
                target_row[col] = new_val
                changes.append(col)

    if not changes:
        print("  変更なし")
        return

    # 保存
    with open(CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print()
    print(f"完了: {len(changes)}項目を修正しました")
    print("次のステップ: fame_v6を再計算してください")


if __name__ == "__main__":
    main()
