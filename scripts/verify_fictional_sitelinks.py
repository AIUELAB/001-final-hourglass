#!/usr/bin/env python3
"""
FICTIONALキャラクターのsitelinks再検証スクリプト。

拡張されたFICTIONAL_TYPESを使用して、現在sitelinks > 0の
架空キャラクターを再検証し、正しいWikidataエンティティにマッチさせる。

使用方法:
    python scripts/verify_fictional_sitelinks.py --dry-run
    python scripts/verify_fictional_sitelinks.py --execute
"""

import argparse
import csv
import json
import math
import sys
from datetime import datetime
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.fame_score_v3.wikidata_disambiguation import (
    disambiguate_person,
)

# 定数
MASTER_CSV_PATH = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")
REPORT_DIR = Path("src/reports")


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


def get_fictional_with_sitelinks(csv_path: Path) -> list[dict]:
    """sitelinks > 0のFICTIONALキャラクターを取得"""
    fictional = []
    seen = set()

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = row.get("person_id", "")
            if pid in seen:
                continue
            seen.add(pid)

            ptype = row.get("person_type", "REAL")
            sitelinks_str = row.get("sitelinks_count", "0")
            multi_lang_pv_str = row.get("multi_lang_pv", "0")
            fame_score_str = row.get("fame_score_v3", "0")

            try:
                sitelinks = float(sitelinks_str) if sitelinks_str else 0
                multi_lang_pv = float(multi_lang_pv_str) if multi_lang_pv_str else 0
                fame_score = float(fame_score_str) if fame_score_str else 0
            except ValueError:
                continue

            if ptype == "FICTIONAL" and sitelinks > 0:
                fictional.append(
                    {
                        "person_id": pid,
                        "person_name": row.get("person_name", ""),
                        "person_type": ptype,
                        "sitelinks_count": int(sitelinks),
                        "multi_lang_pv": multi_lang_pv,
                        "fame_score_v3": fame_score,
                    }
                )

    return fictional


def verify_person(person: dict) -> dict:
    """個人を再検証"""
    name = person["person_name"]
    old_sitelinks = person["sitelinks_count"]

    # 新同定アルゴリズムで再検索
    result = disambiguate_person(
        name=name,
        person_type="FICTIONAL",
        min_confidence=30.0,  # 低めで許容
    )

    if result.success:
        new_sitelinks = result.sitelinks
        changed = new_sitelinks != old_sitelinks

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
            "old_score": person["fame_score_v3"],
            "new_score": new_score,
            "selected_qid": result.selected_qid,
            "confidence": result.confidence,
            "changed": changed,
        }
    else:
        # マッチしない場合はsitelinks=0
        new_score = calculate_fame_score_v3(person["multi_lang_pv"], 0)

        return {
            "person_id": person["person_id"],
            "person_name": name,
            "status": "no_match",
            "old_sitelinks": old_sitelinks,
            "new_sitelinks": 0,
            "old_score": person["fame_score_v3"],
            "new_score": new_score,
            "selected_qid": None,
            "confidence": 0,
            "rejection_reason": result.rejection_reason,
            "changed": old_sitelinks != 0,
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
    parser = argparse.ArgumentParser(description="FICTIONALキャラクターsitelinks再検証")
    parser.add_argument("--dry-run", action="store_true", help="ドライラン")
    parser.add_argument("--execute", action="store_true", help="本番実行")
    parser.add_argument("--limit", type=int, default=0, help="処理件数上限")

    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        parser.print_help()
        return

    print("=== FICTIONALキャラクター sitelinks再検証 ===\n")

    # 対象取得
    print("対象キャラクター取得中...")
    fictional = get_fictional_with_sitelinks(MASTER_CSV_PATH)
    print(f"sitelinks > 0のFICTIONAL: {len(fictional)}人\n")

    if args.limit > 0:
        fictional = fictional[: args.limit]
        print(f"制限後: {len(fictional)}人\n")

    if not fictional:
        print("対象者がいません")
        return

    # 検証実行
    print("再検証中...")
    results = []
    for i, person in enumerate(fictional, 1):
        if i % 10 == 0:
            print(f"  進捗: {i}/{len(fictional)}")
        result = verify_person(person)
        results.append(result)

    # 結果集計
    verified = sum(1 for r in results if r["status"] == "verified")
    updated = sum(1 for r in results if r["status"] == "updated")
    no_match = sum(1 for r in results if r["status"] == "no_match")
    changed = [r for r in results if r["changed"]]

    print("\n=== 結果 ===")
    print(f"変更なし（正常）: {verified}人")
    print(f"sitelinks更新: {updated}人")
    print(f"マッチなし（0に変更）: {no_match}人")
    print(f"合計変更対象: {len(changed)}人")

    # 変更サンプル
    if changed:
        print("\n=== 変更サンプル（上位15件） ===")
        for r in changed[:15]:
            qid = r.get("selected_qid", "なし")
            reason = r.get("rejection_reason", "")
            detail = qid if qid else reason
            print(f"{r['person_name']}: sitelinks {r['old_sitelinks']} → {r['new_sitelinks']} ({detail})")

    # レポート保存
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        "timestamp": datetime.now().isoformat(),
        "mode": "dry-run" if args.dry_run else "execute",
        "total_checked": len(fictional),
        "verified": verified,
        "updated": updated,
        "no_match": no_match,
        "changes": changed,
    }
    report_path = REPORT_DIR / f"fictional_sitelinks_verify_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\nレポート: {report_path}")

    # CSV更新
    if args.execute and changed:
        print("\nCSV更新中...")
        count = update_csv(MASTER_CSV_PATH, results)
        print(f"更新完了: {count}行")
    elif args.dry_run:
        print("\n（ドライラン: CSVは更新されていません）")


if __name__ == "__main__":
    main()
