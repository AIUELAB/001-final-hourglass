#!/usr/bin/env python3
"""
B1_name_not_in_text 不整合修正スクリプト

エピソードテキスト先頭に人物名がない問題を修正。
各EPの具体的なパターンに応じて修正を適用。
"""

import csv
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"

# 修正定義: episode_id -> (old_pattern, new_pattern)
FIXES = {
    # 市川海老蔵: 「海老蔵は」→「市川海老蔵は」
    "EP-000006232": (
        "あなたと同じ35歳のとき、海老蔵は",
        "あなたと同じ35歳のとき、市川海老蔵は",
    ),
    # キング牧師: 「マーティン・ルーサー・キング・ジュニアは」→「キング牧師は」
    "EP-2026010220031": (
        "あなたと同じ39歳のとき、マーティン・ルーサー・キング・ジュニアは",
        "あなたと同じ39歳のとき、キング牧師は",
    ),
    # J.M.W.ターナー: 「ジョゼフ・マロード・ウィリアム・ターナーは」→「J.M.W.ターナーは」
    "EP-EFC24774": (
        "あなたと同じ76歳のとき、ジョゼフ・マロード・ウィリアム・ターナーは",
        "あなたと同じ76歳のとき、J.M.W.ターナーは",
    ),
    # 野田洋次郎: 「あなたと同じ5歳のとき RADWIMPSの野田洋次は」
    # → 「あなたと同じ5歳のとき、野田洋次郎は」
    "EP-251219023331875": (
        "あなたと同じ5歳のとき RADWIMPSの野田洋次は",
        "あなたと同じ5歳のとき、野田洋次郎は",
    ),
    "EP-251217204817669": (
        "あなたと同じ7歳のとき RADWIMPSの野田洋次は",
        "あなたと同じ7歳のとき、野田洋次郎は",
    ),
    "EP-251218205305520": (
        "あなたと同じ13歳のとき RADWIMPSの野田洋次は",
        "あなたと同じ13歳のとき、野田洋次郎は",
    ),
    # 加藤翔: 「加藤 翔は」→「加藤翔は」（スペース除去）
    "EP-000002482": (
        "あなたと同じ25歳のとき、加藤 翔は",
        "あなたと同じ25歳のとき、加藤翔は",
    ),
    # ジュリアス・シーザー: 「ガイウス・ユリウス・カエサルは」→「ジュリアス・シーザーは」
    "EP-36F5477D": (
        "あなたと同じ55歳のとき、ガイウス・ユリウス・カエサルは",
        "あなたと同じ55歳のとき、ジュリアス・シーザーは",
    ),
    # クレオパトラ7世: 「クレオパトラは」→「クレオパトラ7世は」
    "EP-000003439": (
        "あなたと同じ30歳のとき、クレオパトラは",
        "あなたと同じ30歳のとき、クレオパトラ7世は",
    ),
    # ローマ教皇ベネディクト16世: 「ベネディクト16世は」→「ローマ教皇ベネディクト16世は」
    "EP-191ADB88": (
        "あなたと同じ95歳のとき、ベネディクト16世は",
        "あなたと同じ95歳のとき、ローマ教皇ベネディクト16世は",
    ),
}


def main(dry_run: bool = True):
    # CSV読み込み
    with open(MASTER_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames

    print(f"=== B1_name_not_in_text 修正 {'(ドライラン)' if dry_run else '(実行)'} ===\n")
    print(f"総エピソード数: {len(rows)}")
    print(f"修正対象: {len(FIXES)}件\n")

    fixed_count = 0
    for row in rows:
        ep_id = row.get("episode_id")
        if ep_id not in FIXES:
            continue

        old_pattern, new_pattern = FIXES[ep_id]
        text = row.get("episode_text", "")

        if old_pattern in text:
            new_text = text.replace(old_pattern, new_pattern, 1)
            row["episode_text"] = new_text
            fixed_count += 1

            print(f"✓ {ep_id} ({row.get('person_name')})")
            print(f"  Before: {old_pattern}")
            print(f"  After:  {new_pattern}")
            print()
        else:
            print(f"⚠️ {ep_id}: パターン不一致")
            print(f"  Expected: {old_pattern}")
            print(f"  Actual:   {text[:80]}...")
            print()

    print("\n=== 結果 ===")
    print(f"修正件数: {fixed_count}/{len(FIXES)}件")

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
