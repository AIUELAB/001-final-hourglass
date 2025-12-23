#!/usr/bin/env python3
"""
団体名混入定期チェックスクリプト

CI/定期監視用。団体名がperson_nameに混入していないかを検証し、
問題があればexit 1を返す。

Usage:
    # 通常実行（レポート保存あり）
    python scripts/batch/check_group_contamination.py

    # CIモード（1件でも検出でexit 1）
    python scripts/batch/check_group_contamination.py --strict

    # 特定CSVを検証
    python scripts/batch/check_group_contamination.py --csv path/to/file.csv

環境変数:
    GROUP_CHECK_STRICT: "1" で --strict と同等

Exit codes:
    0: 問題なし
    1: 問題あり（--strict時）または実行エラー
"""

import os
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.validators.group_contamination_validator import run_contamination_check


def main():
    import argparse

    parser = argparse.ArgumentParser(description="団体名混入定期チェック")
    parser.add_argument("--csv", type=str, help="対象CSVパス")
    parser.add_argument("--strict", action="store_true", help="1件でも検出したらexit 1")
    parser.add_argument("--no-report", action="store_true", help="レポート保存をスキップ")
    args = parser.parse_args()

    # 環境変数からstrictモードを取得
    strict = args.strict or os.environ.get("GROUP_CHECK_STRICT") == "1"

    csv_path = Path(args.csv) if args.csv else None
    result = run_contamination_check(csv_path=csv_path, save_report=not args.no_report)

    print("=" * 60)
    print("🔍 団体名混入定期チェック")
    print("=" * 60)
    print(f"実行時刻: {result['timestamp']}")

    if "error" in result:
        print(f"❌ エラー: {result['error']}")
        return 1

    print(f"総レコード数: {result['total_records']}")
    print(f"ユニーク人物数: {result['unique_persons']}")
    print(f"混入件数: {result['contamination_count']}")

    if result["status"] == "PASS":
        print("\n✅ PASS: 団体名混入なし")
    else:
        print(f"\n⚠️ FAIL: {result['contamination_count']}件の問題を検出")
        for issue in result["issues"][:5]:
            print(f"  - {issue['person_name']}: {issue['message']}")
        if len(result["issues"]) > 5:
            print(f"  ... 他 {len(result['issues']) - 5}件")

    if result.get("report_path"):
        print(f"\n📄 レポート: {result['report_path']}")

    if strict and result["status"] == "FAIL":
        print("\n❌ Strict mode: 問題が検出されたためexit 1")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
