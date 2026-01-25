#!/usr/bin/env python3
"""
PERSON ID統合スクリプト。

使用方法:
    # ドライラン（変更なし、影響確認のみ）
    python scripts/merge_person_ids.py --dry-run

    # 本番実行
    python scripts/merge_person_ids.py --execute
"""

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd

# パス設定
MASTER_CSV = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")
MAPPING_JSON = Path("src/reports/person_merge_mapping.json")
REPORT_DIR = Path("src/reports")


def load_mapping():
    """統合マッピングを読み込み"""
    with open(MAPPING_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def run_dry_run():
    """ドライラン（変更なし、影響確認のみ）"""
    print("=" * 60)
    print("PERSON ID統合 - ドライラン")
    print("=" * 60)
    print()

    mapping = load_mapping()
    df = pd.read_csv(MASTER_CSV, low_memory=False)

    print(f"マスターCSV: {len(df)} レコード")
    print(f"統合対象: {len(mapping['merges'])} クラスター")
    print()

    # 統合前の人物数
    before_persons = df["person_id"].nunique()

    # 影響を集計
    total_merge_from = 0
    total_episodes_affected = 0

    for merge in mapping["merges"]:
        primary_id = merge["primary_id"]
        merge_from = merge["merge_from"]
        official_name = merge["official_name"]

        for old_id in merge_from:
            count = len(df[df["person_id"] == old_id])
            total_merge_from += 1
            total_episodes_affected += count

    # 統合後の人物数（予測）
    after_persons = before_persons - total_merge_from

    print("=== 影響サマリー ===")
    print(f"統合元ID数: {total_merge_from}")
    print(f"影響エピソード数: {total_episodes_affected}")
    print(f"人物数: {before_persons} → {after_persons} (-{total_merge_from})")
    print()

    # 上位10件の詳細
    print("=== 統合詳細（上位10件）===")
    for i, merge in enumerate(sorted(mapping["merges"], key=lambda x: x["total_episodes"], reverse=True)[:10]):
        primary_id = merge["primary_id"]
        official_name = merge["official_name"]
        merge_from = merge["merge_from"]
        merge_from_names = merge["merge_from_names"]

        print(f"\n{i + 1}. {official_name} ({primary_id})")
        for old_id, old_name in zip(merge_from, merge_from_names):
            count = len(df[df["person_id"] == old_id])
            print(f"   ← {old_name} ({old_id}): {count}件")

    print()
    print("ドライラン完了。本番適用は --execute オプションで実行してください。")


def run_execute():
    """本番実行"""
    print("=" * 60)
    print("PERSON ID統合 - 本番実行")
    print("=" * 60)
    print()

    # バックアップ作成
    backup_path = MASTER_CSV.with_name(f"MASTER_EPISODES_CURRENT.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    shutil.copy(MASTER_CSV, backup_path)
    print(f"バックアップ作成: {backup_path}")

    mapping = load_mapping()
    df = pd.read_csv(MASTER_CSV, low_memory=False)

    print(f"マスターCSV: {len(df)} レコード")
    print(f"統合対象: {len(mapping['merges'])} クラスター")
    print()

    # 統合前の統計
    before_persons = df["person_id"].nunique()
    before_records = len(df)

    # 統合処理
    merge_log = []
    for merge in mapping["merges"]:
        primary_id = merge["primary_id"]
        official_name = merge["official_name"]
        merge_from = merge["merge_from"]

        for old_id in merge_from:
            # person_id を置換
            mask = df["person_id"] == old_id
            count = mask.sum()

            if count > 0:
                df.loc[mask, "person_id"] = primary_id
                df.loc[mask, "person_name"] = official_name

                merge_log.append(
                    {
                        "old_id": old_id,
                        "new_id": primary_id,
                        "new_name": official_name,
                        "episode_count": count,
                    }
                )

        # 正IDのperson_nameも更新
        mask = df["person_id"] == primary_id
        df.loc[mask, "person_name"] = official_name

    # 統合後の統計
    after_persons = df["person_id"].nunique()
    after_records = len(df)

    # CSV保存
    df.to_csv(MASTER_CSV, index=False, encoding="utf-8-sig")
    print(f"CSV保存完了: {MASTER_CSV}")

    # レポート出力
    report = {
        "timestamp": datetime.now().isoformat(),
        "backup_path": str(backup_path),
        "before": {
            "persons": before_persons,
            "records": before_records,
        },
        "after": {
            "persons": after_persons,
            "records": after_records,
        },
        "merged_ids": len(merge_log),
        "merge_log": merge_log,
    }

    report_path = REPORT_DIR / f"person_merge_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"レポート保存: {report_path}")

    # 結果サマリー
    print()
    print("=== 統合結果 ===")
    print(f"人物数: {before_persons} → {after_persons} (-{before_persons - after_persons})")
    print(f"レコード数: {before_records} → {after_records}")
    print(f"統合ID数: {len(merge_log)}")

    # 整合性チェック
    print()
    print("=== 整合性チェック ===")
    if after_records == before_records:
        print("✓ レコード数一致（エピソード消失なし）")
    else:
        print(f"✗ レコード数不一致！ 差分: {after_records - before_records}")

    # 重複チェック
    duplicate_persons = df.groupby(["person_id", "person_name"]).size()
    inconsistent = df.groupby("person_id")["person_name"].nunique()
    inconsistent_ids = inconsistent[inconsistent > 1]

    if len(inconsistent_ids) == 0:
        print("✓ person_id と person_name の整合性OK")
    else:
        print(f"✗ 不整合あり: {len(inconsistent_ids)} 件")
        for pid in inconsistent_ids.index[:5]:
            names = df[df["person_id"] == pid]["person_name"].unique()
            print(f"  {pid}: {list(names)}")


def main():
    parser = argparse.ArgumentParser(description="PERSON ID統合スクリプト")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="ドライラン（変更なし、影響確認のみ）",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="本番実行（CSV更新）",
    )

    args = parser.parse_args()

    if args.dry_run:
        run_dry_run()
    elif args.execute:
        run_execute()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
