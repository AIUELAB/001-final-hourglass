#!/usr/bin/env python3
"""
PERSON ID 重複検出スクリプト（CI用）

機能:
1. 異体字による重複候補を検出
2. 同一person_nameで複数IDを持つケースを検出
3. --strict オプションで1件でも検出された場合にexit 1

使用方法:
    # 通常実行（レポート出力のみ）
    python scripts/batch/check_person_id_duplicates.py

    # CIモード（1件でも検出でexit 1）
    python scripts/batch/check_person_id_duplicates.py --strict

出力:
    src/reports/person_id_duplicate_check_YYYYMMDD_HHMMSS.json
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.csv_path_resolver import get_master_csv_path, get_reports_dir
from src.validators.variant_normalizer import detect_variant_duplicates


def find_exact_duplicates(df: pd.DataFrame) -> list:
    """同一person_nameに複数person_idが存在するケースを検出"""
    from collections import defaultdict

    name_to_ids = defaultdict(set)
    for _, row in df.iterrows():
        name_to_ids[row["person_name"]].add(row["person_id"])

    duplicates = []
    for name, ids in name_to_ids.items():
        if len(ids) > 1:
            duplicates.append(
                {
                    "person_name": name,
                    "person_ids": list(ids),
                    "count": len(ids),
                    "risk": "HIGH",
                }
            )
    return duplicates


def main():
    parser = argparse.ArgumentParser(description="PERSON ID重複チェック")
    parser.add_argument("--strict", action="store_true", help="1件でも検出された場合にexit 1")
    parser.add_argument("--csv", type=str, help="チェック対象のCSVパス（省略時はマスターCSV）")
    args = parser.parse_args()

    print("=" * 60)
    print("🔍 PERSON ID 重複定期チェック")
    print("=" * 60)

    # CSV読み込み
    csv_path = Path(args.csv) if args.csv else get_master_csv_path()
    df = pd.read_csv(csv_path, low_memory=False)

    timestamp = datetime.now()
    print(f"実行時刻: {timestamp.isoformat()}")
    print(f"総レコード数: {len(df)}")
    print(f"ユニーク人物数: {df['person_id'].nunique()}")

    # 1. 異体字重複を検出
    variant_duplicates = detect_variant_duplicates(df)

    # 2. 同一名で複数IDを検出
    exact_duplicates = find_exact_duplicates(df)

    total_issues = len(variant_duplicates) + len(exact_duplicates)
    print(f"異体字重複: {len(variant_duplicates)}件")
    print(f"同一名複数ID: {len(exact_duplicates)}件")

    # レポート作成
    result = {
        "timestamp": timestamp.isoformat(),
        "total_records": len(df),
        "unique_persons": int(df["person_id"].nunique()),
        "issues_found": total_issues,
        "variant_duplicates": variant_duplicates,
        "exact_duplicates": exact_duplicates,
        "status": "FAIL" if total_issues > 0 else "PASS",
    }

    # レポート保存
    reports_dir = get_reports_dir()
    report_name = f"person_id_duplicate_check_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
    report_path = reports_dir / report_name

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print()
    if total_issues == 0:
        print("✅ PASS: PERSON ID重複なし")
    else:
        print(f"⚠️ FAIL: {total_issues}件の問題を検出")
        for dup in variant_duplicates[:5]:
            print(f"  - 異体字: {dup['normalized']} ({len(dup['variants'])}表記)")
        for dup in exact_duplicates[:5]:
            print(f"  - 同一名複数ID: {dup['person_name']} ({len(dup['person_ids'])}ID)")

    print(f"\n📄 レポート: {report_path}")

    # strict モードの場合、問題があればexit 1
    if args.strict and total_issues > 0:
        sys.exit(1)

    return result


if __name__ == "__main__":
    main()
