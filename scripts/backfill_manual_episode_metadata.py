#!/usr/bin/env python3
"""
手動追加エピソード（TURNING_POINT_MANUAL）のメタデータ補完スクリプト

問題:
- TURNING_POINT_MANUALソースのエピソードは、person-levelメタデータが欠落している
- これによりepisode_fame_v6スコアが低くなる

解決:
- 同一人物の既存エピソードからperson-levelメタデータをコピー
"""

import csv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"

# Person-levelフィールド（同一人物で共通であるべき）
PERSON_LEVEL_FIELDS = [
    "celebrity_score_v2",
    "celebrity_rank_v2",
    "sitelinks_count",
    "multi_lang_pv",
    "wikipedia_pv",
    "fame_score_v2",
    "fame_score_v3",
    "fame_rank",
    "fame_rank_v3",
    "fame_tier",
    "google_hits",
    "is_japanese",
    "fame_score_japan",
]


def main(dry_run: bool = True):
    # CSV読み込み
    with open(MASTER_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames

    print(f"=== TURNING_POINT_MANUALメタデータ補完 {'(ドライラン)' if dry_run else '(実行)'} ===\n")
    print(f"総エピソード数: {len(rows)}")

    # 人物ごとにグループ化
    person_episodes = {}
    for row in rows:
        pid = row["person_id"]
        if pid not in person_episodes:
            person_episodes[pid] = []
        person_episodes[pid].append(row)

    # TURNING_POINT_MANUALエピソードを特定
    manual_eps = [r for r in rows if r.get("source") == "TURNING_POINT_MANUAL"]
    print(f"TURNING_POINT_MANUALエピソード数: {len(manual_eps)}\n")

    fixed_count = 0
    for ep in manual_eps:
        pid = ep["person_id"]
        pname = ep["person_name"]
        ep_id = ep["episode_id"]

        # 同一人物の他のエピソードを取得（TURNING_POINT_MANUAL以外）
        other_eps = [
            e
            for e in person_episodes.get(pid, [])
            if e.get("source") != "TURNING_POINT_MANUAL" and e["episode_id"] != ep_id
        ]

        if not other_eps:
            print(f"⚠️ {pname} ({pid}): 参照可能な既存エピソードなし")
            continue

        # 最もメタデータが充実しているエピソードを選択
        template = max(other_eps, key=lambda x: sum(1 for f in PERSON_LEVEL_FIELDS if x.get(f)))

        # 欠落フィールドを補完
        filled_fields = []
        for field in PERSON_LEVEL_FIELDS:
            current_val = ep.get(field, "").strip()
            template_val = template.get(field, "").strip()

            if not current_val and template_val:
                ep[field] = template_val
                filled_fields.append(field)

        if filled_fields:
            fixed_count += 1
            print(f"✓ {pname} - {ep_id}")
            print(f"  補完フィールド: {', '.join(filled_fields)}")
            # スコア情報表示
            if "sitelinks_count" in filled_fields:
                print(f"  sitelinks_count: {ep['sitelinks_count']}")
            if "multi_lang_pv" in filled_fields:
                print(f"  multi_lang_pv: {ep['multi_lang_pv']}")
            print()
        else:
            print(f"○ {pname} - {ep_id}: 補完不要（既に充足）")

    print("\n=== 結果 ===")
    print(f"補完対象: {fixed_count}/{len(manual_eps)}件")

    if dry_run:
        print("\n(ドライラン完了 - 変更なし)")
        return

    # 実行モード: CSV書き込み
    with open(MASTER_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("\n✅ CSV更新完了")


if __name__ == "__main__":
    dry_run = "--execute" not in sys.argv
    main(dry_run)
