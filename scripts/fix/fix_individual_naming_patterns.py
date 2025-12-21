#!/usr/bin/env python3
"""
個人名含みパターンの名義変更スクリプト

処理対象:
- 「○○の兄弟△△」→「△△」（個人名部分を抽出）
- 「グループ名（個人名）」→「個人名」（括弧内の個人名を抽出）

例:
  「岩崎弥太郎の兄弟岩崎弥之助」→「岩崎弥之助」
  「ライト兄弟（ウィルバー）」→「ウィルバー・ライト」
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))


# 名義変更ルール
NAMING_RULES = {
    # 「○○の兄弟△△」パターン
    "岩崎弥太郎の兄弟岩崎弥之助": "岩崎弥之助",
    # 「グループ名（個人名）」パターン
    "ライト兄弟（ウィルバー）": "ウィルバー・ライト",
    "ライト兄弟（オーヴィル）": "オーヴィル・ライト",
    # 「グループ名・個人名」パターン（Phase 6追加）
    "カーペンターズ・カレン・カーペンター": "カレン・カーペンター",
    "カーペンターズのカレン・カーペンター": "カレン・カーペンター",
}


def get_or_create_person_id(df: pd.DataFrame, name: str) -> str:
    """既存のperson_idを取得、なければ生成"""
    existing = df[df["person_name"] == name]
    if not existing.empty:
        return existing["person_id"].iloc[0]
    hash_val = hashlib.md5(name.encode()).hexdigest()[:8].upper()
    return f"P{hash_val}"


def process_naming_patterns(
    df: pd.DataFrame,
    dry_run: bool = True,
) -> tuple[pd.DataFrame, dict]:
    """個人名含みパターンを処理"""

    report = {
        "timestamp": datetime.now().isoformat(),
        "renamed": [],
        "not_found": [],
        "errors": [],
    }

    renamed_count = 0

    for old_name, new_name in NAMING_RULES.items():
        matches = df[df["person_name"] == old_name]

        if len(matches) == 0:
            print(f"  {old_name}: 見つかりません（スキップ）")
            report["not_found"].append(old_name)
            continue

        for idx, row in matches.iterrows():
            episode_id = row["episode_id"]
            print(f"  {episode_id}: {old_name} → {new_name}")

            if dry_run:
                report["renamed"].append(
                    {
                        "episode_id": episode_id,
                        "old_name": old_name,
                        "new_name": new_name,
                        "dry_run": True,
                    }
                )
            else:
                try:
                    person_id = get_or_create_person_id(df, new_name)
                    df.at[idx, "person_name"] = new_name
                    df.at[idx, "person_id"] = person_id
                    df.at[idx, "source"] = f"NAMING_FIX_{row.get('source', '')}"

                    report["renamed"].append(
                        {
                            "episode_id": episode_id,
                            "old_name": old_name,
                            "new_name": new_name,
                            "dry_run": False,
                        }
                    )
                    renamed_count += 1
                    print("    ✅ 名義変更完了")
                except Exception as e:
                    print(f"    ❌ エラー: {e}")
                    report["errors"].append(
                        {
                            "episode_id": episode_id,
                            "error": str(e),
                        }
                    )

    report["summary"] = {
        "renamed_count": renamed_count if not dry_run else len(report["renamed"]),
        "not_found_count": len(report["not_found"]),
        "error_count": len(report["errors"]),
    }

    if not dry_run:
        print(f"\n✅ {renamed_count}件名義変更完了")

    return df, report


def main():
    parser = argparse.ArgumentParser(description="個人名含みパターンの名義変更")
    parser.add_argument("--execute", action="store_true", help="実際に実行")
    parser.add_argument(
        "--output",
        type=str,
        default="reports/individual_naming_fix.json",
        help="レポート出力先",
    )
    args = parser.parse_args()

    csv_path = "preserved/data/MASTER_EPISODES_CURRENT.csv"
    print(f"📂 読み込み: {csv_path}")
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    print(f"📋 総エピソード数: {len(df)}件")

    if args.execute:
        backup_path = csv_path.replace(".csv", f"_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        df.to_csv(backup_path, index=False, encoding="utf-8-sig")
        print(f"💾 バックアップ: {backup_path}")

    dry_run = not args.execute
    mode = "[DRY-RUN]" if dry_run else "[EXECUTE]"
    print(f"\n🚀 {mode} 処理開始...")
    print(f"対象パターン: {len(NAMING_RULES)}件")

    df_updated, report = process_naming_patterns(df, dry_run=dry_run)

    if args.execute:
        df_updated.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print(f"\n💾 保存完了: {csv_path}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = args.output.replace(".json", f"_{timestamp}.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"📄 レポート: {output_path}")

    print("\n" + "=" * 60)
    print("サマリー")
    print("=" * 60)
    print(f"  対象パターン: {len(NAMING_RULES)}件")
    print(f"  名義変更: {len(report['renamed'])}件")
    print(f"  見つからず: {len(report['not_found'])}件")
    print(f"  エラー: {len(report['errors'])}件")


if __name__ == "__main__":
    main()
