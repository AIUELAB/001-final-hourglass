#!/usr/bin/env python3
"""
多年参照エピソードスキャン

MASTER CSVを走査し、「本文に3つ以上の異なる年が出る」エピソードを抽出。
各エピソードについて:
  (a) 年候補一覧
  (b) 推定対象年
  (c) INFO/WARNING/CRITICAL の分類
  (d) サンプル10件
を JSON で src/reports/ に出力する。
"""

import csv
import json
import sys
from datetime import datetime
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from rules.rule_174_temporal_consistency import TemporalConsistencyChecker

MASTER_CSV = project_root / "preserved/data/MASTER_EPISODES_CURRENT.csv"
OUTPUT_DIR = project_root / "src/reports"


def scan_multi_year_episodes(max_samples: int = 10) -> dict:
    """多年参照エピソードをスキャン"""
    checker = TemporalConsistencyChecker()

    results = {
        "scan_date": datetime.now().isoformat(),
        "total_episodes": 0,
        "multi_year_episodes": 0,
        "by_severity": {"CRITICAL": 0, "WARNING": 0, "INFO": 0, "NONE": 0},
        "samples": [],
        "all_flagged": [],
    }

    with open(MASTER_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            results["total_episodes"] += 1
            episode_text = row.get("episode_text", "")
            episode_id = row.get("episode_id", "")
            person_name = row.get("person_name", "")

            # 年齢と生年を取得
            try:
                age = int(float(row.get("age") or 0))
            except (ValueError, TypeError):
                age = 0

            try:
                birth_year = int(float(row.get("birth_year") or 0))
                if birth_year < 1 or birth_year > 2100:
                    birth_year = None
            except (ValueError, TypeError):
                birth_year = None

            # 年を抽出
            years = checker.extract_all_years(episode_text)

            # 3年以上の参照がある場合のみ処理
            if len(years) < 3:
                continue

            results["multi_year_episodes"] += 1

            # 対象年を推定
            target_year, method = checker.determine_target_year(episode_text, age, birth_year)

            # 分類
            issue = checker.classify_multi_year_episode(episode_text, age, birth_year)

            if issue:
                severity = issue.severity
                message = issue.message
            else:
                severity = "NONE"
                message = "対象年確定済み（経歴文脈として許容）"

            results["by_severity"][severity] += 1

            # 結果を記録
            entry = {
                "episode_id": episode_id,
                "person_name": person_name,
                "age": age,
                "birth_year": birth_year,
                "year_candidates": years,
                "year_span": max(years) - min(years) if years else 0,
                "target_year": target_year,
                "estimation_method": method,
                "severity": severity,
                "message": message,
                "text_preview": episode_text[:150] + "..." if len(episode_text) > 150 else episode_text,
            }

            results["all_flagged"].append(entry)

            # サンプルを収集（各severity から均等に）
            if len(results["samples"]) < max_samples:
                results["samples"].append(entry)

    # 統計を追加
    results["statistics"] = {
        "multi_year_ratio": (
            results["multi_year_episodes"] / results["total_episodes"] if results["total_episodes"] > 0 else 0
        ),
        "critical_ratio": (
            results["by_severity"]["CRITICAL"] / results["multi_year_episodes"]
            if results["multi_year_episodes"] > 0
            else 0
        ),
        "warning_ratio": (
            results["by_severity"]["WARNING"] / results["multi_year_episodes"]
            if results["multi_year_episodes"] > 0
            else 0
        ),
        "info_ratio": (
            results["by_severity"]["INFO"] / results["multi_year_episodes"] if results["multi_year_episodes"] > 0 else 0
        ),
        "false_positive_estimate": (
            (results["by_severity"]["INFO"] + results["by_severity"]["NONE"]) / results["multi_year_episodes"]
            if results["multi_year_episodes"] > 0
            else 0
        ),
    }

    return results


def main():
    """メイン処理"""
    print("=" * 60)
    print("多年参照エピソードスキャン")
    print("=" * 60)

    # スキャン実行
    results = scan_multi_year_episodes(max_samples=10)

    # 結果出力
    print(f"\n総エピソード数: {results['total_episodes']}")
    print(f"多年参照エピソード: {results['multi_year_episodes']}")
    print(f"  - CRITICAL: {results['by_severity']['CRITICAL']}")
    print(f"  - WARNING: {results['by_severity']['WARNING']}")
    print(f"  - INFO: {results['by_severity']['INFO']}")
    print(f"  - NONE (許容): {results['by_severity']['NONE']}")

    print(f"\n偽陽性率推定: {results['statistics']['false_positive_estimate']:.1%}")

    # サンプル表示
    print("\n" + "=" * 60)
    print("サンプル10件")
    print("=" * 60)
    for i, sample in enumerate(results["samples"][:10], 1):
        print(f"\n[{i}] {sample['episode_id']} - {sample['person_name']} ({sample['age']}歳)")
        print(f"    年候補: {sample['year_candidates']}")
        print(f"    対象年: {sample['target_year']} ({sample['estimation_method']})")
        print(f"    分類: {sample['severity']} - {sample['message']}")

    # JSON出力（all_flaggedは別ファイルに）
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # サマリー（samples付き）
    summary_output = {
        "scan_date": results["scan_date"],
        "total_episodes": results["total_episodes"],
        "multi_year_episodes": results["multi_year_episodes"],
        "by_severity": results["by_severity"],
        "statistics": results["statistics"],
        "samples": results["samples"],
    }

    summary_path = OUTPUT_DIR / "multi_year_scan_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary_output, f, ensure_ascii=False, indent=2)
    print(f"\n✅ サマリー出力: {summary_path}")

    # 全件リスト（別ファイル）
    if results["all_flagged"]:
        all_path = OUTPUT_DIR / "multi_year_scan_all.json"
        with open(all_path, "w", encoding="utf-8") as f:
            json.dump(results["all_flagged"], f, ensure_ascii=False, indent=2)
        print(f"✅ 全件リスト出力: {all_path}")

    print("\n" + "=" * 60)
    print("スキャン完了")
    print("=" * 60)

    return results


if __name__ == "__main__":
    main()
