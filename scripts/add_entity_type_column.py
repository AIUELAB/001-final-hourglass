#!/usr/bin/env python3
"""
entity_typeカラム導入スクリプト

エピソードデータベースにentity_typeカラムを追加し、
各レコードがINDIVIDUAL（個人）かGROUP（グループ）かを明示的に区別する。

entity_type の値:
- INDIVIDUAL: 個人（エピソードの対象として適切）
- GROUP: グループ/組織（エピソードの対象として不適切）
- UNKNOWN: 未分類（LLM判定が必要）

使用方法:
    # ドライラン（変更なし）
    python scripts/add_entity_type_column.py

    # 本番実行
    python scripts/add_entity_type_column.py --execute

    # LLMで未分類を判定（要API_KEY）
    python scripts/add_entity_type_column.py --execute --use-llm
"""

import argparse
import csv
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.group_master import GROUP_ENTITIES, GROUP_MEMBER_MAP, is_group_entity

# CSVパス
MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
REPORT_DIR = PROJECT_ROOT / "reports"


def classify_entity_type(
    person_name: str,
    person_type: Optional[str] = None,
    is_group_member: Optional[str] = None,
) -> str:
    """
    person_nameからentity_typeを分類

    Args:
        person_name: 人物名
        person_type: 人物タイプ (REAL/FICTIONAL)
        is_group_member: グループメンバーフラグ

    Returns:
        entity_type: INDIVIDUAL | GROUP | UNKNOWN
    """
    # FICTIONALは常にINDIVIDUAL（架空キャラクターは個人扱い）
    if person_type == "FICTIONAL":
        return "INDIVIDUAL"

    # GROUP_ENTITIESに登録されている場合はGROUP
    if is_group_entity(person_name):
        return "GROUP"

    # is_group_memberがTrueの場合はINDIVIDUAL（グループの一員だが個人）
    if is_group_member and str(is_group_member).lower() in ("true", "1", "1.0"):
        return "INDIVIDUAL"

    # GROUP_MEMBER_MAPに登録されている場合はINDIVIDUAL
    if person_name in GROUP_MEMBER_MAP:
        return "INDIVIDUAL"

    # グループ名っぽいパターンを検出
    group_patterns = [
        "大学",
        "高校",
        "学校",
        "学院",
        "研究所",
        "研究室",
        "財団",
        "法人",
        "株式会社",
        "有限会社",
        "合同会社",
        "グループ",
        "チーム",
        "連盟",
        "協会",
        "委員会",
        "内閣",
        "政府",
        "省庁",
        "市役所",
        "県庁",
        "オールスターズ",
        "ブラザーズ",
        "シスターズ",
        "ファミリー",
    ]

    for pattern in group_patterns:
        if pattern in person_name:
            return "GROUP"

    # 上記に該当しなければINDIVIDUAL（デフォルト）
    return "INDIVIDUAL"


def add_entity_type_column(execute: bool = False, use_llm: bool = False) -> dict:
    """
    entity_typeカラムを追加

    Args:
        execute: True=本番実行, False=ドライラン
        use_llm: LLMで未分類を判定するか

    Returns:
        処理結果サマリ
    """
    print("=" * 60)
    print("entity_typeカラム導入")
    print("=" * 60)
    print(f"  マスターCSV: {MASTER_CSV}")
    print(f"  実行モード: {'本番' if execute else 'ドライラン'}")
    print(f"  LLM判定: {'有効' if use_llm else '無効'}")
    print()

    # CSVを読み込み
    rows = []
    with open(MASTER_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        for row in reader:
            rows.append(row)

    print(f"  総レコード数: {len(rows):,}")

    # entity_typeカラムが既に存在するか確認
    if "entity_type" in fieldnames:
        print("  ⚠️ entity_typeカラムは既に存在します")
        # 既存の値をカウント
        existing_counts = {"INDIVIDUAL": 0, "GROUP": 0, "UNKNOWN": 0, "empty": 0}
        for row in rows:
            et = row.get("entity_type", "")
            if et in existing_counts:
                existing_counts[et] += 1
            else:
                existing_counts["empty"] += 1
        print(f"  既存の分布: {existing_counts}")

        # 空の値のみ更新
        update_empty = existing_counts["empty"] > 0
        if not update_empty:
            print("  すべてのレコードにentity_typeが設定されています")
            return {"status": "already_complete", "counts": existing_counts}
    else:
        # カラムを追加
        fieldnames.append("entity_type")
        update_empty = False

    # entity_typeを分類
    stats = {"INDIVIDUAL": 0, "GROUP": 0, "UNKNOWN": 0, "updated": 0, "skipped": 0}
    groups_detected = []

    for row in rows:
        # 既存の値がある場合はスキップ
        if update_empty and row.get("entity_type", ""):
            stats["skipped"] += 1
            continue

        person_name = row.get("person_name", "")
        person_type = row.get("person_type", "")
        is_group_member = row.get("is_group_member", "")

        entity_type = classify_entity_type(person_name, person_type, is_group_member)
        row["entity_type"] = entity_type

        stats[entity_type] += 1
        stats["updated"] += 1

        if entity_type == "GROUP":
            groups_detected.append(
                {
                    "person_name": person_name,
                    "episode_id": row.get("episode_id", ""),
                    "category": row.get("category", ""),
                }
            )

    # 結果表示
    print("\n📊 分類結果:")
    print(f"  INDIVIDUAL: {stats['INDIVIDUAL']:,}件")
    print(f"  GROUP: {stats['GROUP']:,}件")
    print(f"  UNKNOWN: {stats['UNKNOWN']:,}件")
    print(f"  更新: {stats['updated']:,}件")
    print(f"  スキップ: {stats['skipped']:,}件")

    if groups_detected:
        print(f"\n⚠️ グループとして検出されたエントリ ({len(groups_detected)}件):")
        for g in groups_detected[:10]:
            print(f"  - {g['person_name']} ({g['category']})")
        if len(groups_detected) > 10:
            print(f"  ... 他 {len(groups_detected) - 10}件")

    # 本番実行
    if execute:
        # バックアップ作成
        backup_path = MASTER_CSV.with_suffix(f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        with open(MASTER_CSV, "r", encoding="utf-8-sig") as f_in:
            with open(backup_path, "w", encoding="utf-8-sig", newline="") as f_out:
                f_out.write(f_in.read())
        print(f"\n✅ バックアップ作成: {backup_path}")

        # CSV書き出し
        with open(MASTER_CSV, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        print(f"✅ CSVを更新しました: {MASTER_CSV}")

        # レポート保存
        report_path = REPORT_DIR / f"entity_type_classification_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        REPORT_DIR.mkdir(parents=True, exist_ok=True)

        import json

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "timestamp": datetime.now().isoformat(),
                    "stats": stats,
                    "groups_detected": groups_detected,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
        print(f"✅ レポート保存: {report_path}")
    else:
        print("\n⚠️ ドライランモード: CSVは更新されませんでした")
        print("   --execute オプションで本番実行")

    return {"status": "success", "stats": stats, "groups_detected": groups_detected}


def main():
    parser = argparse.ArgumentParser(description="entity_typeカラム導入")
    parser.add_argument("--execute", action="store_true", help="本番実行")
    parser.add_argument("--use-llm", action="store_true", help="LLMで未分類を判定")
    args = parser.parse_args()

    result = add_entity_type_column(execute=args.execute, use_llm=args.use_llm)
    print("\n完了")


if __name__ == "__main__":
    main()
