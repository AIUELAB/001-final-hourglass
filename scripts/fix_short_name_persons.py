#!/usr/bin/env python3
"""
短名人物の手動修正スクリプト。

Wikidata検索で正しくマッチできない短名の歴史的人物を
手動で正しいエンティティに紐付ける。
"""

import csv
import json
from datetime import datetime
from pathlib import Path

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent
CSV_PATH = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
REPORT_PATH = PROJECT_ROOT / "src" / "reports" / f"short_name_fixes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

# 手動修正マッピング
# format: person_id -> (wikidata_qid, sitelinks_count, reason)
MANUAL_FIXES = {
    "P9FD76A6": ("Q8963", 181, "ケプラー → ヨハネス・ケプラー（ドイツの天文学者）"),
    "PE1E5DFB": ("Q8753", 167, "フェルミ → エンリコ・フェルミ（イタリアの物理学者）"),
    "P3943D87": ("Q455980", 12, "UA → UA（日本の歌手、作詞家）"),
    "P5D9ABB5": ("Q1201902", 26, "タマ → たま（貴志駅の猫駅長、1999-2015）"),
}


def calculate_fame_score_v3(
    multi_lang_pv: float,
    sitelinks: float,
    google_hits: float = 0,
) -> float:
    """Fame Score v3を計算（scorer.pyと同じ計算式）"""
    import math

    # 正規化パラメータ（scorer.pyと同じ）
    MAX_PV = 10_000_000
    MAX_SITELINKS = 200
    MAX_GOOGLE_HITS = 1_000_000_000

    # PV: 対数スケール
    norm_pv = math.log1p(multi_lang_pv) / math.log1p(MAX_PV) if multi_lang_pv > 0 else 0

    # sitelinks: 線形スケール
    norm_sl = min(sitelinks / MAX_SITELINKS, 1.0) if sitelinks > 0 else 0

    # google_hits: 対数スケール
    norm_gh = math.log1p(google_hits) / math.log1p(MAX_GOOGLE_HITS) if google_hits > 0 else 0

    # 重み付け合計（Phase 1: Google検索なし）
    if google_hits > 0:
        # Phase 2
        score = (0.40 * norm_pv + 0.25 * norm_sl + 0.15 * 0 + 0.20 * norm_gh) * 1000
    else:
        # Phase 1 (inlinksは使用しない)
        score = (0.50 * norm_pv + 0.30 * norm_sl + 0.20 * 0) * 1000

    return round(score, 2)


def main(dry_run: bool = False) -> dict:
    """CSVを修正"""

    # CSVを読み込み
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    changes = []

    for row in rows:
        person_id = row.get("person_id", "")

        if person_id in MANUAL_FIXES:
            qid, new_sitelinks, reason = MANUAL_FIXES[person_id]

            old_sitelinks = float(row.get("sitelinks_count", 0) or 0)
            old_score = float(row.get("fame_score_v3", 0) or 0)

            # 現在の値を取得
            multi_lang_pv = float(row.get("multi_lang_pv", 0) or 0)
            google_hits_str = row.get("google_hits", "") or ""
            google_hits = float(google_hits_str) if google_hits_str.strip() else 0

            # 新しいスコアを計算
            new_score = calculate_fame_score_v3(multi_lang_pv, new_sitelinks, google_hits)

            change = {
                "person_id": person_id,
                "person_name": row.get("person_name", ""),
                "reason": reason,
                "wikidata_qid": qid,
                "old_sitelinks": old_sitelinks,
                "new_sitelinks": new_sitelinks,
                "old_score": old_score,
                "new_score": new_score,
                "diff": new_sitelinks - old_sitelinks,
            }
            changes.append(change)

            if not dry_run:
                row["sitelinks_count"] = str(new_sitelinks)
                row["fame_score_v3"] = str(new_score)

    # CSVを書き出し
    if not dry_run and changes:
        with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    # レポート作成
    report = {
        "timestamp": datetime.now().isoformat(),
        "mode": "dry-run" if dry_run else "applied",
        "total_fixes": len(changes),
        "changes": changes,
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return report


if __name__ == "__main__":
    import sys

    dry_run = "--dry-run" in sys.argv

    print(f"短名人物修正スクリプト ({'dry-run' if dry_run else '実行'}モード)")
    print("=" * 50)

    report = main(dry_run=dry_run)

    print(f"\n修正対象: {report['total_fixes']}件")
    for c in report["changes"]:
        print(f"\n{c['person_name']} ({c['person_id']}):")
        print(f"  理由: {c['reason']}")
        print(f"  sitelinks: {c['old_sitelinks']:.0f} → {c['new_sitelinks']} (差分: {c['diff']:+.0f})")
        print(f"  fame_score_v3: {c['old_score']:.2f} → {c['new_score']:.2f}")

    print(f"\nレポート: {REPORT_PATH}")
