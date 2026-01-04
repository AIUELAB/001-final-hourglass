#!/usr/bin/env python3
"""
Batch External Fact Check - Wikipedia/Wikidata APIを使用した外部検証

機能:
- API制限を考慮した段階的実行
- 検証結果のキャッシュ
- 差分検証モード（前回からの変更分のみ）
- 進捗レポート生成

使用方法:
    # 全エピソードを検証（制限付き）
    python scripts/batch_external_fact_check.py --max-persons 100

    # 差分検証（前回から変更された人物のみ）
    python scripts/batch_external_fact_check.py --diff-only

    # 特定の人物を検証
    python scripts/batch_external_fact_check.py --persons "大谷翔平" "手塚治虫"

    # レポートのみ生成
    python scripts/batch_external_fact_check.py --report-only
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.external_fact_checker import ExternalFactChecker
from src.birth_year_database import get_birth_year

MASTER_CSV = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
REPORT_DIR = PROJECT_ROOT / "src/reports"
CACHE_DIR = PROJECT_ROOT / "preserved/fact_cache"
VERIFICATION_HISTORY_FILE = REPORT_DIR / "external_fact_check_history.json"


def load_verification_history() -> dict:
    """検証履歴を読み込み"""
    if VERIFICATION_HISTORY_FILE.exists():
        with open(VERIFICATION_HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"verified_persons": {}, "last_full_scan": None}


def save_verification_history(history: dict) -> None:
    """検証履歴を保存"""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    with open(VERIFICATION_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def get_unique_persons() -> list[dict]:
    """ユニークな人物リストを取得"""
    persons = {}

    with open(MASTER_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            person_name = row.get("person_name", "")
            person_type = row.get("person_type", "REAL")

            # 架空キャラはスキップ
            if person_type == "FICTIONAL":
                continue

            if person_name and person_name not in persons:
                birth_year = get_birth_year(person_name)
                persons[person_name] = {
                    "person_name": person_name,
                    "person_id": row.get("person_id", ""),
                    "birth_year": birth_year,
                    "episode_count": 1,
                }
            elif person_name in persons:
                persons[person_name]["episode_count"] += 1

    # エピソード数でソート（多い順）
    return sorted(persons.values(), key=lambda x: x["episode_count"], reverse=True)


def batch_verify_persons(
    persons: list[dict],
    max_persons: int = 100,
    delay_seconds: float = 1.5,
    progress_callback=None,
) -> dict:
    """
    人物をバッチで検証

    Args:
        persons: 検証対象の人物リスト
        max_persons: 最大検証人数
        delay_seconds: API呼び出し間隔
        progress_callback: 進捗コールバック

    Returns:
        検証結果の辞書
    """
    checker = ExternalFactChecker(delay_seconds=delay_seconds)
    history = load_verification_history()

    results = {
        "timestamp": datetime.now().isoformat(),
        "total_persons": len(persons),
        "verified_count": 0,
        "skipped_count": 0,
        "results": [],
        "summary": {
            "verified": 0,
            "mismatch": 0,
            "not_found": 0,
            "unknown": 0,
            "partially_verified": 0,
        },
    }

    target_persons = persons[:max_persons]

    for i, person in enumerate(target_persons):
        person_name = person["person_name"]
        birth_year = person["birth_year"]

        if progress_callback:
            progress_callback(i + 1, len(target_persons), person_name)

        # 検証実行
        try:
            verification = checker.verify_person(person_name, birth_year)

            person_result = {
                "person_name": person_name,
                "expected_birth_year": birth_year,
                "episode_count": person["episode_count"],
                "verification": verification,
                "status": verification["overall_status"],
            }

            results["results"].append(person_result)
            status = verification["overall_status"]
            if status in results["summary"]:
                results["summary"][status] += 1
            else:
                results["summary"][status] = 1
            results["verified_count"] += 1

            # 履歴更新
            history["verified_persons"][person_name] = {
                "verified_at": datetime.now().isoformat(),
                "status": verification["overall_status"],
                "birth_year": birth_year,
            }

        except Exception as e:
            print(f"  Error verifying {person_name}: {e}")
            results["results"].append(
                {
                    "person_name": person_name,
                    "error": str(e),
                    "status": "error",
                }
            )

    # 履歴保存
    save_verification_history(history)

    return results


def generate_report(results: dict, output_path: Path) -> None:
    """検証レポートを生成"""
    report = {
        "title": "External Fact Check Batch Report",
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "total_persons": results["total_persons"],
            "verified_count": results["verified_count"],
            "verification_rate": (
                results["verified_count"] / results["total_persons"] * 100 if results["total_persons"] > 0 else 0
            ),
            "status_breakdown": results["summary"],
        },
        "mismatches": [r for r in results["results"] if r.get("status") == "mismatch"],
        "not_found": [r for r in results["results"] if r.get("status") in ["not_found", "unknown"]],
        "verified": [r for r in results["results"] if r.get("status") == "verified"],
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\nReport saved: {output_path}")


def print_summary(results: dict) -> None:
    """サマリーを表示"""
    print("\n" + "=" * 60)
    print("Batch External Fact Check - Summary")
    print("=" * 60)

    print(f"\nTotal persons: {results['total_persons']}")
    print(f"Verified: {results['verified_count']}")

    print("\nStatus breakdown:")
    for status, count in results["summary"].items():
        pct = count / results["verified_count"] * 100 if results["verified_count"] > 0 else 0
        print(f"  {status}: {count} ({pct:.1f}%)")

    # 不一致を表示
    mismatches = [r for r in results["results"] if r.get("status") == "mismatch"]
    if mismatches:
        print(f"\nMismatches ({len(mismatches)}):")
        for m in mismatches[:10]:
            print(f"  - {m['person_name']}: expected {m.get('expected_birth_year')}")

    # 未発見を表示
    not_found = [r for r in results["results"] if r.get("status") in ["not_found", "unknown"]]
    if not_found:
        print(f"\nNot found ({len(not_found)}):")
        for n in not_found[:10]:
            print(f"  - {n['person_name']}")


def main():
    parser = argparse.ArgumentParser(description="Batch external fact check using Wikipedia/Wikidata")
    parser.add_argument("--max-persons", type=int, default=50, help="Maximum persons to verify")
    parser.add_argument("--delay", type=float, default=1.5, help="Delay between API calls (seconds)")
    parser.add_argument("--persons", nargs="+", help="Specific persons to verify")
    parser.add_argument("--diff-only", action="store_true", help="Only verify unverified persons")
    parser.add_argument("--report-only", action="store_true", help="Only generate report from cache")
    parser.add_argument("--output", help="Output report path")

    args = parser.parse_args()

    print("=" * 60)
    print("Batch External Fact Check")
    print("=" * 60)

    # 人物リスト取得
    print("\nLoading persons from master CSV...")
    all_persons = get_unique_persons()
    print(f"  Total unique persons: {len(all_persons)}")

    # フィルタリング
    if args.persons:
        target_persons = [p for p in all_persons if p["person_name"] in args.persons]
    elif args.diff_only:
        history = load_verification_history()
        verified_names = set(history["verified_persons"].keys())
        target_persons = [p for p in all_persons if p["person_name"] not in verified_names]
        print(f"  Unverified persons: {len(target_persons)}")
    else:
        target_persons = all_persons

    if args.report_only:
        # キャッシュからレポート生成のみ
        history = load_verification_history()
        results = {
            "total_persons": len(all_persons),
            "verified_count": len(history["verified_persons"]),
            "summary": defaultdict(int),
            "results": [],
        }
        for name, info in history["verified_persons"].items():
            results["summary"][info["status"]] += 1
            results["results"].append(
                {
                    "person_name": name,
                    "status": info["status"],
                }
            )
        print_summary(results)
        return

    # 進捗表示
    def progress_callback(current, total, person_name):
        print(f"  [{current}/{total}] {person_name}")

    # 検証実行
    print(f"\nStarting verification (max {args.max_persons} persons)...")
    results = batch_verify_persons(
        target_persons,
        max_persons=args.max_persons,
        delay_seconds=args.delay,
        progress_callback=progress_callback,
    )

    # サマリー表示
    print_summary(results)

    # レポート保存
    if args.output:
        output_path = Path(args.output)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = REPORT_DIR / f"external_fact_check_{timestamp}.json"

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    generate_report(results, output_path)


if __name__ == "__main__":
    main()
