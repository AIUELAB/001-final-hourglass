#!/usr/bin/env python3
"""
文章品質ドライラン検査スクリプト v2（精度向上版）

ルールA: 終止形の誤り
  A1: 「〜にありた」→「〜にいた」
  A2: 「繋がりた」→「繋がった」
  A3: 「〜になりた」→「〜になった」
  A4: 「〜となりた」→「〜となった」
  A5: 「〜がりた」→「〜がった」（上がりた、下がりた等）
  A6: その他「〜りた。」（要レビュー）

ルールB: 末尾句点欠落（「」」「！」「？」で終わる場合は除外）

ルールC: 導入文パターンの「は、」→「は」
"""

import csv
import re
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
REPORT_DIR = PROJECT_ROOT / "src" / "reports" / "logs"


def detect_rule_a(text: str) -> list[dict]:
    """ルールA: 終止形の誤り検出（精度向上版）"""
    findings = []

    # A1: 「〜にありた」→「〜にいた」
    pattern_a1 = re.compile(r"にありた([。、]|$)")
    for m in pattern_a1.finditer(text):
        findings.append(
            {
                "subtype": "A1",
                "original": f"にありた{m.group(1)}",
                "fixed": f"にいた{m.group(1)}",
                "pattern": "にありた → にいた",
                "auto_fix": True,
            }
        )

    # A2: 「繋がりた」→「繋がった」
    pattern_a2 = re.compile(r"繋がりた([。、]|$)")
    for m in pattern_a2.finditer(text):
        findings.append(
            {
                "subtype": "A2",
                "original": f"繋がりた{m.group(1)}",
                "fixed": f"繋がった{m.group(1)}",
                "pattern": "繋がりた → 繋がった",
                "auto_fix": True,
            }
        )

    # A3: 「〜になりた」→「〜になった」
    pattern_a3 = re.compile(r"になりた([。、]|$)")
    for m in pattern_a3.finditer(text):
        findings.append(
            {
                "subtype": "A3",
                "original": f"になりた{m.group(1)}",
                "fixed": f"になった{m.group(1)}",
                "pattern": "になりた → になった",
                "auto_fix": True,
            }
        )

    # A4: 「〜となりた」→「〜となった」
    pattern_a4 = re.compile(r"となりた([。、]|$)")
    for m in pattern_a4.finditer(text):
        findings.append(
            {
                "subtype": "A4",
                "original": f"となりた{m.group(1)}",
                "fixed": f"となった{m.group(1)}",
                "pattern": "となりた → となった",
                "auto_fix": True,
            }
        )

    # A5: 「〜がりた」→「〜がった」（上がりた、下がりた、広がりた等）
    pattern_a5 = re.compile(r"(上|下|広|拡|高|深)がりた([。、]|$)")
    for m in pattern_a5.finditer(text):
        findings.append(
            {
                "subtype": "A5",
                "original": f"{m.group(1)}がりた{m.group(2)}",
                "fixed": f"{m.group(1)}がった{m.group(2)}",
                "pattern": f"{m.group(1)}がりた → {m.group(1)}がった",
                "auto_fix": True,
            }
        )

    return findings


def detect_rule_b(text: str) -> list[dict]:
    """ルールB: 末尾句点欠落検出（精度向上版）"""
    findings = []

    text_stripped = text.strip()
    if not text_stripped:
        return findings

    # 末尾が。！？」で終わっている場合はOK
    valid_endings = ("。", "！", "？", "」", "!", "?")
    if text_stripped.endswith(valid_endings):
        return findings

    # それ以外は句点欠落
    last_chars = text_stripped[-30:] if len(text_stripped) > 30 else text_stripped
    findings.append(
        {
            "subtype": "B",
            "original": f"...{last_chars}",
            "fixed": f"...{last_chars}。",
            "pattern": "末尾に句点追加",
            "auto_fix": True,
        }
    )

    return findings


def detect_rule_c(text: str) -> list[dict]:
    """ルールC: 導入文パターンの「は、」検出（改行崩れ対応）"""
    findings = []

    # パターン: 「あなたと同じXX歳のとき、{人名}は、」（改行崩れも含む）
    # csv_writer.py の _fix_text_quality と同一パターンを使用
    pattern = re.compile(
        r"(あなたと同じ\d+歳のとき[、,]?[ \t]*\n?[ \t]*)" r"([^、。\n]{2,30})" r"(は)" r"([ \t]*\n?[ \t]*)" r"、"
    )
    for m in pattern.finditer(text):
        intro = m.group(1)
        name = m.group(2)
        ws = m.group(4)  # ホワイトスペース/改行
        original_text = f"{intro}{name}は{ws}、"
        fixed_text = f"{intro}{name}は{ws}"
        findings.append(
            {
                "subtype": "C",
                "original": original_text,
                "fixed": fixed_text,
                "pattern": "導入文「は、」→「は」(改行崩れ含む)",
                "auto_fix": True,
            }
        )

    return findings


def main() -> int:
    """メイン処理（戻り値: 0=問題なし, 1=問題あり）"""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORT_DIR / f"text_quality_dryrun_v2_{timestamp}.log"

    results = defaultdict(list)
    episode_ids_by_rule = defaultdict(set)

    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            episode_id = row.get("episode_id", "")
            text = row.get("episode_text", "")

            if not text:
                continue

            # ルールA
            for finding in detect_rule_a(text):
                finding["episode_id"] = episode_id
                results["A"].append(finding)
                episode_ids_by_rule["A"].add(episode_id)

            # ルールB
            for finding in detect_rule_b(text):
                finding["episode_id"] = episode_id
                results["B"].append(finding)
                episode_ids_by_rule["B"].add(episode_id)

            # ルールC
            for finding in detect_rule_c(text):
                finding["episode_id"] = episode_id
                results["C"].append(finding)
                episode_ids_by_rule["C"].add(episode_id)

    # サブタイプ別集計
    subtype_counts = defaultdict(int)
    for rule, items in results.items():
        for item in items:
            subtype_counts[item["subtype"]] += 1

    # レポート出力
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("=== 文章品質ドライラン検査結果 v2 ===\n")
        f.write("=" * 60 + "\n")
        f.write(f"検査日時: {datetime.now().isoformat()}\n")
        f.write(f"対象ファイル: {CSV_PATH}\n\n")

        # サマリー
        f.write("【サマリー】\n")
        f.write(f"  ルールA (終止形誤り): {len(results['A'])}件 ({len(episode_ids_by_rule['A'])}エピソード)\n")
        for st in ["A1", "A2", "A3", "A4", "A5"]:
            if subtype_counts[st] > 0:
                f.write(f"    - {st}: {subtype_counts[st]}件\n")
        f.write(f"  ルールB (句点欠落): {len(results['B'])}件\n")
        f.write(f"  ルールC (導入文は、): {len(results['C'])}件\n")
        total = len(results["A"]) + len(results["B"]) + len(results["C"])
        f.write(f"  合計: {total}件\n\n")

        # 対象episode_id一覧
        f.write("【対象episode_id一覧】\n")
        all_ids = episode_ids_by_rule["A"] | episode_ids_by_rule["B"] | episode_ids_by_rule["C"]
        f.write(f"  総数: {len(all_ids)}エピソード\n")
        for i, eid in enumerate(sorted(all_ids)[:50]):
            f.write(f"  {eid}\n")
        if len(all_ids) > 50:
            f.write(f"  ... 他 {len(all_ids) - 50}件\n")
        f.write("\n")

        # 詳細（上位10件ずつ）
        for rule in ["A", "B", "C"]:
            items = results[rule]
            f.write("-" * 60 + "\n")
            f.write(f"【ルール{rule}】 検出数: {len(items)}件\n")
            f.write("-" * 60 + "\n")
            for i, item in enumerate(items[:10]):
                f.write(f"  [{i+1}] {item['episode_id']} ({item['subtype']})\n")
                f.write(f"      Before: {item['original'][:60]}\n")
                f.write(f"      After:  {item['fixed'][:60]}\n")
                f.write(f"      AutoFix: {item['auto_fix']}\n\n")
            if len(items) > 10:
                f.write(f"  ... 他 {len(items) - 10}件\n\n")

    # コンソール出力
    print("=" * 60)
    print("=== 文章品質ドライラン検査結果 v2 ===")
    print("=" * 60)
    print(f"ルールA (終止形誤り): {len(results['A'])}件")
    for st in ["A1", "A2", "A3", "A4", "A5"]:
        if subtype_counts[st] > 0:
            print(f"  - {st}: {subtype_counts[st]}件")
    print(f"ルールB (句点欠落): {len(results['B'])}件")
    print(f"ルールC (導入文は、): {len(results['C'])}件")
    total = len(results["A"]) + len(results["B"]) + len(results["C"])
    print(f"合計: {total}件 ({len(all_ids)}エピソード)")
    print(f"\n詳細ログ: {report_path}")

    # 終了コード: 問題があれば1、なければ0
    return 1 if total > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
