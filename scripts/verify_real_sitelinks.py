#!/usr/bin/env python3
"""
REAL人物のsitelinks再検証スクリプト。

疑わしいケース（短名ラテン文字、低PV高sitelinks）を
新同定アルゴリズムで再検証し、正しいsitelinkを設定。

使用方法:
    python scripts/verify_real_sitelinks.py --dry-run
    python scripts/verify_real_sitelinks.py --execute
"""

import argparse
import csv
import json
import math
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.fame_score_v3.wikidata_disambiguation import (
    disambiguate_person,
)

MASTER_CSV_PATH = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")
REPORT_DIR = Path("src/reports")


def is_mostly_latin(name: str) -> bool:
    """ラテン文字が主体か判定"""
    latin = sum(1 for c in name if c.isascii() and c.isalpha())
    return latin > len(name) * 0.5


def calculate_fame_score_v3(multi_lang_pv: float, sitelinks: float) -> float:
    """Fame Score v3を計算"""
    MAX_PV = 10_000_000
    MAX_SITELINKS = 200

    def normalize_pv(pv):
        if pv <= 0:
            return 0.0
        return math.log1p(pv) / math.log1p(MAX_PV)

    def normalize_sitelinks(count):
        if count <= 0:
            return 0.0
        return min(count / MAX_SITELINKS, 1.0)

    norm_pv = normalize_pv(multi_lang_pv)
    norm_sitelinks = normalize_sitelinks(sitelinks)
    raw = 0.50 * norm_pv + 0.30 * norm_sitelinks + 0.20 * 0
    return round(raw * 1000, 2)


def get_suspicious_real_persons(csv_path: Path) -> list[dict]:
    """疑わしいREAL人物を取得"""
    suspicious = []
    seen = set()

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = row.get("person_id", "")
            if pid in seen:
                continue
            seen.add(pid)

            ptype = row.get("person_type", "REAL")
            if ptype != "REAL":
                continue

            name = row.get("person_name", "")
            try:
                sitelinks = float(row.get("sitelinks_count", 0) or 0)
                pv = float(row.get("multi_lang_pv", 0) or 0)
                score = float(row.get("fame_score_v3", 0) or 0)
            except ValueError:
                continue

            is_latin = is_mostly_latin(name)
            name_len = len(name)

            # 条件1: 短いラテン文字名 + 高sitelinks
            condition1 = is_latin and name_len <= 4 and sitelinks >= 30

            # 条件2: 低PV(<50k) + 高sitelinks(>=50) = 誤マッチ可能性
            condition2 = pv < 50000 and sitelinks >= 50

            if condition1 or condition2:
                suspicious.append(
                    {
                        "person_id": pid,
                        "person_name": name,
                        "sitelinks_count": int(sitelinks),
                        "multi_lang_pv": pv,
                        "fame_score_v3": score,
                        "reason": "latin_short" if condition1 else "low_pv_high_sitelinks",
                    }
                )

    return suspicious


def verify_person(person: dict) -> dict:
    """人物を再検証"""
    name = person["person_name"]
    old_sitelinks = person["sitelinks_count"]

    result = disambiguate_person(
        name=name,
        person_type="REAL",
        min_confidence=40.0,
    )

    if result.success:
        new_sitelinks = result.sitelinks
        changed = new_sitelinks != old_sitelinks
        diff = new_sitelinks - old_sitelinks

        new_score = calculate_fame_score_v3(
            person["multi_lang_pv"],
            new_sitelinks,
        )

        return {
            "person_id": person["person_id"],
            "person_name": name,
            "status": "verified" if not changed else "updated",
            "old_sitelinks": old_sitelinks,
            "new_sitelinks": new_sitelinks,
            "diff": diff,
            "old_score": person["fame_score_v3"],
            "new_score": new_score,
            "selected_qid": result.selected_qid,
            "confidence": result.confidence,
            "changed": changed,
            "reason": person["reason"],
        }
    else:
        new_score = calculate_fame_score_v3(person["multi_lang_pv"], 0)

        return {
            "person_id": person["person_id"],
            "person_name": name,
            "status": "no_match",
            "old_sitelinks": old_sitelinks,
            "new_sitelinks": 0,
            "diff": -old_sitelinks,
            "old_score": person["fame_score_v3"],
            "new_score": new_score,
            "selected_qid": None,
            "confidence": 0,
            "rejection_reason": result.rejection_reason,
            "changed": old_sitelinks != 0,
            "reason": person["reason"],
        }


def update_csv(csv_path: Path, updates: list[dict]) -> int:
    """CSVを更新"""
    update_map = {u["person_id"]: u for u in updates if u["changed"]}
    if not update_map:
        return 0

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    updated = 0
    for row in rows:
        pid = row["person_id"]
        if pid in update_map:
            upd = update_map[pid]
            row["sitelinks_count"] = str(upd["new_sitelinks"])
            row["fame_score_v3"] = str(upd["new_score"])
            updated += 1

    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return updated


def main():
    parser = argparse.ArgumentParser(description="REAL人物sitelinks再検証")
    parser.add_argument("--dry-run", action="store_true", help="ドライラン")
    parser.add_argument("--execute", action="store_true", help="本番実行")
    parser.add_argument("--limit", type=int, default=0, help="処理件数上限")

    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        parser.print_help()
        return

    print("=== REAL人物 sitelinks再検証 ===\n")

    print("疑わしいケース検出中...")
    suspicious = get_suspicious_real_persons(MASTER_CSV_PATH)
    print(f"検出数: {len(suspicious)}件\n")

    if args.limit > 0:
        suspicious = suspicious[: args.limit]
        print(f"制限後: {len(suspicious)}件\n")

    if not suspicious:
        print("対象者がいません")
        return

    print("再検証中...")
    results = []
    for i, person in enumerate(suspicious, 1):
        if i % 20 == 0:
            print(f"  進捗: {i}/{len(suspicious)}")
        result = verify_person(person)
        results.append(result)

    # 結果集計
    verified = sum(1 for r in results if r["status"] == "verified")
    updated = sum(1 for r in results if r["status"] == "updated")
    no_match = sum(1 for r in results if r["status"] == "no_match")
    changed = [r for r in results if r["changed"]]

    # 増加/減少分類
    increased = [r for r in changed if r["diff"] > 0]
    decreased = [r for r in changed if r["diff"] < 0]

    print("\n=== 結果 ===")
    print(f"変更なし: {verified}件")
    print(f"sitelinks更新: {updated}件")
    print(f"マッチなし: {no_match}件")
    print(f"合計変更: {len(changed)}件")
    print(f"  - 増加: {len(increased)}件")
    print(f"  - 減少: {len(decreased)}件")

    # サンプル表示
    if increased:
        print("\n=== sitelinks増加（上位10件） ===")
        increased.sort(key=lambda x: x["diff"], reverse=True)
        for r in increased[:10]:
            print(f"{r['person_name']}: {r['old_sitelinks']} → {r['new_sitelinks']} (+{r['diff']})")

    if decreased:
        print("\n=== sitelinks減少（上位10件） ===")
        decreased.sort(key=lambda x: x["diff"])
        for r in decreased[:10]:
            print(f"{r['person_name']}: {r['old_sitelinks']} → {r['new_sitelinks']} ({r['diff']})")

    # レポート保存
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        "timestamp": datetime.now().isoformat(),
        "mode": "dry-run" if args.dry_run else "execute",
        "total_checked": len(suspicious),
        "verified": verified,
        "updated": updated,
        "no_match": no_match,
        "increased": len(increased),
        "decreased": len(decreased),
        "changes": changed,
    }
    report_path = REPORT_DIR / f"real_sitelinks_verify_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\nレポート: {report_path}")

    if args.execute and changed:
        print("\nCSV更新中...")
        count = update_csv(MASTER_CSV_PATH, results)
        print(f"更新完了: {count}行")
    elif args.dry_run:
        print("\n（ドライラン: CSVは更新されていません）")


if __name__ == "__main__":
    main()
