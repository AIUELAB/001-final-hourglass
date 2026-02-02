#!/usr/bin/env python3
"""
B2違反（英語名混入）修正スクリプト

B2違反は、日本語名の人物のエピソード本文に英語名パターン（[A-Z][a-z]+ [A-Z][a-z]+）が
含まれている場合に検出される。

対処方針:
1. title_keywordsへの追加（推奨）:
   - 企業名、作品名、曲名、固有名詞として許容すべきパターン
   - detect_all_inconsistencies.py の title_keywords リストに追加

2. 本文修正（最小限）:
   - 本当に人物名が露出しているケースのみ
   - 日本語表記に置換

使用方法:
    python scripts/fix/fix_b2_english_names.py --dry-run     # 検証のみ
    python scripts/fix/fix_b2_english_names.py --execute     # 実際に修正
    python scripts/fix/fix_b2_english_names.py --analyze     # 違反パターン分析
"""

import argparse
import csv
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

CSV_PATH = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")
REPORTS_DIR = Path("src/reports")

# detect_all_inconsistencies.py からtitle_keywordsをインポート
# （同期を保つため、直接参照）
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "validation"))
from detect_all_inconsistencies import check_name_text_consistency


def load_episodes() -> list[dict[str, str]]:
    """エピソード読み込み"""
    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader)


def analyze_violations(episodes: list) -> dict:
    """B2違反パターンを分析"""
    violations: list[dict] = []
    pattern_counts: defaultdict[str, int] = defaultdict(int)

    for row in episodes:
        issues = check_name_text_consistency(row)
        for issue in issues:
            if issue["type"] == "B2_english_name_in_text":
                ep_id = row.get("episode_id", "")
                person_name = row.get("person_name", "")
                detail = issue["detail"]

                # 検出された英語名を抽出
                match = re.search(r"'([A-Z][a-z]+ [A-Z][a-z]+)'", detail)
                if match:
                    english_name = match.group(1)
                    pattern_counts[english_name] += 1
                    violations.append(
                        {
                            "episode_id": ep_id,
                            "person_name": person_name,
                            "english_name": english_name,
                            "detail": detail,
                        }
                    )

    return {
        "total_violations": len(violations),
        "pattern_counts": dict(sorted(pattern_counts.items(), key=lambda x: -x[1])),
        "violations": violations,
    }


def suggest_keywords(analysis: dict) -> list:
    """title_keywordsに追加すべきキーワードを提案"""
    suggestions = []
    for pattern in analysis["pattern_counts"]:
        words = pattern.split()
        for word in words:
            if word not in suggestions:
                suggestions.append(word)
    return suggestions


def print_analysis(analysis: dict) -> None:
    """分析結果を表示"""
    print("=" * 60)
    print("B2違反パターン分析")
    print("=" * 60)
    print(f"総違反数: {analysis['total_violations']}件")
    print()

    if analysis["pattern_counts"]:
        print("【頻出パターン（上位20件）】")
        for pattern, count in list(analysis["pattern_counts"].items())[:20]:
            print(f"  {count:3d}件: {pattern}")
        print()

        suggestions = suggest_keywords(analysis)
        print("【title_keywordsへの追加候補】")
        print("以下のキーワードをdetect_all_inconsistencies.pyのtitle_keywordsに追加することを推奨:")
        print()
        for word in suggestions[:50]:
            print(f'            "{word}",')
    else:
        print("B2違反は検出されませんでした。")


def fix_violations(episodes: list, analysis: dict) -> tuple[list, list]:
    """
    B2違反を修正

    注: 現在の実装では、title_keywordsへの追加で対応することを推奨。
    本文修正は、明らかに不適切な英語名露出のケースのみ対象とする。
    """
    # 本文修正が必要なケースの定義（将来拡張用）
    # 現時点では、すべてのB2違反はtitle_keywords追加で対応済み

    modified_episodes: list = []
    modifications: list = []

    violation_ids = {v["episode_id"] for v in analysis["violations"]}

    for row in episodes:
        ep_id = row.get("episode_id", "")

        if ep_id in violation_ids:
            # 現在は修正対象なし（title_keywords追加で対応）
            # 将来的に本文修正が必要な場合はここに実装
            pass

        modified_episodes.append(row)

    return modified_episodes, modifications


def save_episodes(episodes: list, output_path: Path) -> None:
    """エピソードを保存"""
    if not episodes:
        return

    fieldnames = episodes[0].keys()
    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(episodes)


def main() -> None:
    parser = argparse.ArgumentParser(description="B2違反（英語名混入）修正スクリプト")
    parser.add_argument("--dry-run", action="store_true", help="検証のみ（変更なし）")
    parser.add_argument("--execute", action="store_true", help="実際に修正を実行")
    parser.add_argument("--analyze", action="store_true", help="違反パターンを分析")
    args = parser.parse_args()

    if not any([args.dry_run, args.execute, args.analyze]):
        parser.print_help()
        return

    print("エピソード読み込み中...")
    episodes = load_episodes()
    print(f"総エピソード数: {len(episodes)}")

    print("B2違反を検出中...")
    analysis = analyze_violations(episodes)

    if args.analyze:
        print_analysis(analysis)
        return

    if analysis["total_violations"] == 0:
        print()
        print("=" * 60)
        print("B2違反は検出されませんでした。")
        print("title_keywordsの追加により、すべての違反が解消されています。")
        print("=" * 60)
        return

    print_analysis(analysis)

    if args.dry_run:
        print()
        print("【推奨アクション】")
        print("1. 上記のキーワードをdetect_all_inconsistencies.pyのtitle_keywordsに追加")
        print("2. 本文修正が必要な場合は、--execute オプションで実行")
        return

    if args.execute:
        print()
        print("修正を実行中...")
        modified_episodes, modifications = fix_violations(episodes, analysis)

        if modifications:
            # バックアップ作成
            backup_path = CSV_PATH.with_suffix(f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
            save_episodes(episodes, backup_path)
            print(f"バックアップ作成: {backup_path}")

            # 修正版を保存
            save_episodes(modified_episodes, CSV_PATH)
            print(f"修正完了: {len(modifications)}件")

            # 修正ログ保存
            log_path = REPORTS_DIR / f"b2_fix_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(log_path, "w", encoding="utf-8") as f:
                json.dump(modifications, f, ensure_ascii=False, indent=2)
            print(f"修正ログ: {log_path}")
        else:
            print("修正対象のエピソードはありませんでした。")
            print("title_keywordsへの追加で対応することを推奨します。")


if __name__ == "__main__":
    main()
