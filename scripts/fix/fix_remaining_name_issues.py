#!/usr/bin/env python3
"""
残存する人物名不整合の修正スクリプト

1. 架空キャラ『作品名』形式は正常として除外
2. 「名前の重複」バグ（例: 栗原はるみはるみ）を修正
3. 英語混在の作品名は許容
"""

import argparse
import csv
import re
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
MASTER_CSV_PATH = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
REPORTS_DIR = PROJECT_ROOT / "src/reports/logs"


def analyze_mismatch(person_name: str, text_name: str, episode_text: str) -> dict:
    """
    不整合のタイプと修正方針を分析

    Returns:
        {
            "type": str,  # 分類
            "needs_fix": bool,  # 修正が必要か
            "fix_type": str | None,  # 修正タイプ
            "description": str  # 説明
        }
    """
    # 架空キャラ『作品名』形式のチェック
    work_title_pattern = rf"^{re.escape(person_name)}『.+?』$"
    if re.match(work_title_pattern, text_name):
        return {
            "type": "架空キャラ正常形式",
            "needs_fix": False,
            "fix_type": None,
            "description": f"架空キャラの正常フォーマット: {text_name}",
        }

    # 名前重複バグのチェック（例: 栗原はるみはるみ）
    # パターン: person_nameの後半が重複している
    if len(person_name) >= 2:
        for i in range(1, len(person_name)):
            suffix = person_name[i:]
            if (
                text_name == person_name[:i]
                and episode_text.startswith("あなたと同じ")
                and f"{person_name}{suffix}は" in episode_text
            ):
                return {
                    "type": "名前重複バグ",
                    "needs_fix": True,
                    "fix_type": "duplicate_fix",
                    "description": f"'{person_name}{suffix}'が重複",
                }

    # 部分一致（姓のみ等）
    if person_name.startswith(text_name) or text_name.startswith(person_name):
        return {
            "type": "部分一致",
            "needs_fix": False,
            "fix_type": None,
            "description": f"部分一致: {text_name} vs {person_name}",
        }

    return {"type": "その他", "needs_fix": False, "fix_type": None, "description": "分類不能"}


def fix_duplicate_name(episode_text: str, person_name: str) -> str:
    """名前重複バグを修正"""
    # パターン: あなたと同じ{age}歳のとき、{partial_name}{person_name}は
    # 例: あなたと同じ45歳のとき、栗原はるみはるみは → あなたと同じ45歳のとき、栗原はるみは

    for i in range(1, len(person_name)):
        suffix = person_name[i:]
        wrong_pattern = f"{person_name}{suffix}は"
        correct_pattern = f"{person_name}は"
        if wrong_pattern in episode_text:
            return episode_text.replace(wrong_pattern, correct_pattern, 1)

    return episode_text


def main():
    parser = argparse.ArgumentParser(description="残存する人物名不整合の分析・修正")
    parser.add_argument("--execute", action="store_true", help="修正を実行")
    args = parser.parse_args()

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print("=" * 60)
    print("【残存不整合の分析・修正】")
    print("=" * 60)
    print(f"モード: {'★実行★' if args.execute else 'ドライラン'}")
    print()

    # CSV読み込み
    rows = []
    with open(MASTER_CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)

    # リード文抽出パターン
    lead_pattern = re.compile(r"^あなたと同じ[\d.]+歳のとき、(.+?)は")

    # 分析結果
    stats = {
        "架空キャラ正常形式": 0,
        "名前重複バグ": 0,
        "部分一致": 0,
        "その他": 0,
    }
    fixes = []

    for i, row in enumerate(rows):
        episode_id = row.get("episode_id", "")
        person_name = row.get("person_name", "")
        episode_text = row.get("episode_text", "")

        match = lead_pattern.match(episode_text)
        if not match:
            continue

        text_name = match.group(1)

        # 『作品名』部分を除去して比較
        text_name_clean = re.sub(r"『.+?』$", "", text_name)

        if text_name_clean == person_name:
            continue  # 完全一致（正常）

        # 不整合を分析
        analysis = analyze_mismatch(person_name, text_name, episode_text)
        stats[analysis["type"]] = stats.get(analysis["type"], 0) + 1

        if analysis["needs_fix"]:
            new_text = fix_duplicate_name(episode_text, person_name)
            fixes.append(
                {
                    "index": i,
                    "episode_id": episode_id,
                    "person_name": person_name,
                    "fix_type": analysis["fix_type"],
                    "before": episode_text[:80],
                    "after": new_text[:80],
                }
            )
            if args.execute:
                rows[i]["episode_text"] = new_text

    # 結果出力
    print("【分析結果】")
    for typ, count in stats.items():
        status = "✅ 正常" if typ == "架空キャラ正常形式" else ("🔧 要修正" if typ == "名前重複バグ" else "⚠️ 許容")
        print(f"  {typ}: {count}件 {status}")
    print()

    print(f"【修正対象】{len(fixes)}件")
    for fix in fixes[:5]:
        print(f"  {fix['episode_id']}: {fix['person_name']}")
        print(f"    Before: {fix['before']}...")
        print(f"    After:  {fix['after']}...")
    print()

    # 実行モードなら保存
    if args.execute and fixes:
        backup_path = MASTER_CSV_PATH.parent / f"{MASTER_CSV_PATH.stem}.bak_remaining_{timestamp}.csv"
        with open(MASTER_CSV_PATH, "r", encoding="utf-8-sig") as src:
            with open(backup_path, "w", encoding="utf-8-sig") as dst:
                dst.write(src.read())
        print(f"バックアップ: {backup_path}")

        with open(MASTER_CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print("★ CSV更新完了")

    # レポート保存
    report_path = REPORTS_DIR / f"remaining_analysis_{timestamp}.csv"
    with open(report_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["index", "episode_id", "person_name", "fix_type", "before", "after"])
        writer.writeheader()
        writer.writerows(fixes)
    print(f"レポート: {report_path}")

    print()
    print("=" * 60)
    if args.execute:
        print(f"✅ {len(fixes)}件を修正完了")
    else:
        print("💡 ドライラン完了。--execute で修正を適用")
    print("=" * 60)


if __name__ == "__main__":
    main()
