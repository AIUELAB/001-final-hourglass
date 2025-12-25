#!/usr/bin/env python3
"""
Wikidata同名曖昧性問題の一括修正スクリプト。

短名や一般語で誤ったWikidataエンティティにマッチした人物を検出し、
新同定アルゴリズムで正しいエンティティを再選択する。

使用方法:
    # ドライラン（変更なし、レポートのみ）
    python scripts/fix_wikidata_disambiguation.py --dry-run

    # 本番実行（CSV更新）
    python scripts/fix_wikidata_disambiguation.py --execute

    # 特定人物のみ
    python scripts/fix_wikidata_disambiguation.py --execute --person-id PF632FA6
"""

import argparse
import csv
import json
import math
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.fame_score_v3.wikidata_disambiguation import (
    disambiguate_person,
    DisambiguationResult,
)

# 定数
MASTER_CSV_PATH = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")
REPORT_DIR = Path("src/reports")

# 高リスク条件
SHORT_NAME_THRESHOLD = 5  # 5文字以下の名前
HIGH_SITELINKS_THRESHOLD = 50  # 50以上のsitelinksは疑わしい


def is_latin_name(name: str) -> bool:
    """ラテン文字の名前か判定"""
    latin_chars = sum(1 for c in name if c.isascii() and c.isalpha())
    return latin_chars > len(name) * 0.5


def calculate_fame_score_v3(multi_lang_pv: float, sitelinks: float, inlinks: float = 0) -> float:
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

    # Phase 1 weights (no google_hits)
    raw = 0.50 * norm_pv + 0.30 * norm_sitelinks + 0.20 * 0
    return round(raw * 1000, 2)


def detect_suspicious_persons(csv_path: Path) -> list[dict]:
    """
    疑わしい人物を検出。

    条件:
    - 短名（5文字以下）でsitelinks >= 50
    - ラテン文字の短名（英語圏で一般的な単語と衝突しやすい）

    Returns:
        疑わしい人物のリスト
    """
    suspicious = []
    seen_person_ids = set()

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            person_id = row.get("person_id", "")
            if person_id in seen_person_ids:
                continue
            seen_person_ids.add(person_id)

            name = row.get("person_name", "")
            person_type = row.get("person_type", "REAL")
            sitelinks_str = row.get("sitelinks_count", "0")
            multi_lang_pv_str = row.get("multi_lang_pv", "0")
            fame_score_str = row.get("fame_score_v3", "0")

            try:
                sitelinks = float(sitelinks_str) if sitelinks_str else 0
                multi_lang_pv = float(multi_lang_pv_str) if multi_lang_pv_str else 0
                fame_score = float(fame_score_str) if fame_score_str else 0
            except ValueError:
                continue

            # 短名 + 高sitelinks = 疑わしい
            is_short = len(name) <= SHORT_NAME_THRESHOLD
            is_high_sitelinks = sitelinks >= HIGH_SITELINKS_THRESHOLD

            # ラテン文字の短名は特に危険（国名、数字、一般語にマッチしやすい）
            is_risky = is_short and is_latin_name(name) and is_high_sitelinks

            # 架空キャラクターで高sitelinks = 映画/作品にマッチした可能性
            is_fictional_risk = person_type == "FICTIONAL" and sitelinks >= 30

            if is_risky or is_fictional_risk:
                suspicious.append(
                    {
                        "person_id": person_id,
                        "person_name": name,
                        "person_type": person_type,
                        "sitelinks_count": int(sitelinks),
                        "multi_lang_pv": multi_lang_pv,
                        "fame_score_v3": fame_score,
                        "risk_reason": "short_latin_high_sitelinks" if is_risky else "fictional_high_sitelinks",
                    }
                )

    return suspicious


def fix_person(
    person: dict,
    dry_run: bool = True,
) -> dict:
    """
    個人の曖昧性を解決。

    Returns:
        修正結果の辞書
    """
    name = person["person_name"]
    person_type = person["person_type"]
    old_sitelinks = person["sitelinks_count"]

    # 新同定アルゴリズムで再検索
    result = disambiguate_person(
        name=name,
        person_type=person_type,
        min_confidence=40.0,  # 少し低めで許容
    )

    if result.success:
        new_sitelinks = result.sitelinks
        changed = new_sitelinks != old_sitelinks

        # 新スコア計算
        new_score = calculate_fame_score_v3(
            person["multi_lang_pv"],
            new_sitelinks,
        )

        return {
            "person_id": person["person_id"],
            "person_name": name,
            "status": "fixed" if changed else "unchanged",
            "old_sitelinks": old_sitelinks,
            "new_sitelinks": new_sitelinks,
            "old_score": person["fame_score_v3"],
            "new_score": new_score,
            "selected_qid": result.selected_qid,
            "confidence": result.confidence,
            "changed": changed,
        }
    else:
        # マッチしない場合はsitelinks=0として扱う
        new_sitelinks = 0
        new_score = calculate_fame_score_v3(
            person["multi_lang_pv"],
            0,
        )

        return {
            "person_id": person["person_id"],
            "person_name": name,
            "status": "no_match",
            "old_sitelinks": old_sitelinks,
            "new_sitelinks": new_sitelinks,
            "old_score": person["fame_score_v3"],
            "new_score": new_score,
            "selected_qid": None,
            "confidence": 0,
            "rejection_reason": result.rejection_reason,
            "changed": old_sitelinks != 0,
        }


def update_csv(csv_path: Path, fixes: list[dict]) -> int:
    """
    CSVを更新。

    Returns:
        更新した行数
    """
    # 修正対象をマッピング
    fix_map = {f["person_id"]: f for f in fixes if f["changed"]}
    if not fix_map:
        return 0

    # CSV読み込み
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    # 更新
    updated = 0
    for row in rows:
        pid = row["person_id"]
        if pid in fix_map:
            fix = fix_map[pid]
            row["sitelinks_count"] = str(fix["new_sitelinks"])
            row["fame_score_v3"] = str(fix["new_score"])
            updated += 1

    # 書き込み
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return updated


def main():
    parser = argparse.ArgumentParser(description="Wikidata同名曖昧性問題の修正")
    parser.add_argument("--dry-run", action="store_true", help="ドライラン（変更なし）")
    parser.add_argument("--execute", action="store_true", help="本番実行（CSV更新）")
    parser.add_argument("--person-id", help="特定人物のみ処理")
    parser.add_argument("--limit", type=int, default=0, help="処理件数上限")

    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        parser.print_help()
        return

    print("=== Wikidata同名曖昧性修正 ===\n")

    # 疑わしい人物を検出
    print("疑わしい人物を検出中...")
    suspicious = detect_suspicious_persons(MASTER_CSV_PATH)
    print(f"検出: {len(suspicious)}人\n")

    if args.person_id:
        suspicious = [p for p in suspicious if p["person_id"] == args.person_id]
        print(f"フィルタ後: {len(suspicious)}人\n")

    if args.limit > 0:
        suspicious = suspicious[: args.limit]
        print(f"制限後: {len(suspicious)}人\n")

    if not suspicious:
        print("対象者がいません")
        return

    # 各人物を処理
    print("曖昧性解決中...")
    fixes = []
    for i, person in enumerate(suspicious, 1):
        if i % 10 == 0:
            print(f"  進捗: {i}/{len(suspicious)}")

        fix = fix_person(person, dry_run=args.dry_run)
        fixes.append(fix)

    # 結果集計
    fixed_count = sum(1 for f in fixes if f["status"] == "fixed")
    unchanged_count = sum(1 for f in fixes if f["status"] == "unchanged")
    no_match_count = sum(1 for f in fixes if f["status"] == "no_match")

    print("\n=== 結果 ===")
    print(f"修正対象: {fixed_count}人")
    print(f"変更なし: {unchanged_count}人")
    print(f"マッチなし: {no_match_count}人")

    # 変更サンプル表示
    changed_fixes = [f for f in fixes if f["changed"]]
    if changed_fixes:
        print("\n=== 変更サンプル（上位10件） ===")
        for f in changed_fixes[:10]:
            print(
                f"{f['person_id']} {f['person_name']}: "
                f"sitelinks {f['old_sitelinks']} → {f['new_sitelinks']}, "
                f"score {f['old_score']:.2f} → {f['new_score']:.2f}"
            )

    # レポート保存
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        "timestamp": datetime.now().isoformat(),
        "mode": "dry-run" if args.dry_run else "execute",
        "total_suspicious": len(suspicious),
        "fixed": fixed_count,
        "unchanged": unchanged_count,
        "no_match": no_match_count,
        "changes": [f for f in fixes if f["changed"]],
    }
    report_path = REPORT_DIR / f"wikidata_disambiguation_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\nレポート: {report_path}")

    # CSV更新（本番実行時のみ）
    if args.execute and changed_fixes:
        print("\nCSV更新中...")
        updated = update_csv(MASTER_CSV_PATH, fixes)
        print(f"更新完了: {updated}行")
    elif args.dry_run:
        print("\n（ドライラン: CSVは更新されていません）")


if __name__ == "__main__":
    main()
