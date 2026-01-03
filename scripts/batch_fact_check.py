#!/usr/bin/env python3
"""
Batch Fact Check - 全エピソードの事実確認バッチ処理

Usage:
    python scripts/batch_fact_check.py           # ドライラン
    python scripts/batch_fact_check.py --apply   # 本番適用
"""

import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

import pandas as pd

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.fact_checker import FactChecker


def run_batch_fact_check(
    csv_path: Path,
    apply: bool = False,
    verbose: bool = True,
) -> dict:
    """
    全エピソードに対してファクトチェックを実行

    Args:
        csv_path: マスターCSVのパス
        apply: Trueなら結果をCSVに保存
        verbose: 詳細表示

    Returns:
        dict: 実行結果のサマリー
    """
    print("=== Batch Fact Check ===")
    print(f"モード: {'本番適用' if apply else 'ドライラン'}")
    print()

    # 1. データ読み込み
    print("1. データ読み込み中...")
    df = pd.read_csv(csv_path, low_memory=False)
    total = len(df)
    print(f"   エピソード数: {total:,}")

    # 現在の状態
    current_status = df["fact_check_result"].value_counts(dropna=False)
    print("\n   現在の状態:")
    for status, count in current_status.head(5).items():
        pct = count / total * 100
        print(f"   - {status}: {count:,} ({pct:.1f}%)")

    # 2. ファクトチェッカー初期化
    checker = FactChecker()

    # 3. バッチ処理
    print("\n2. ファクトチェック実行中...")
    results = []
    result_counts = Counter()
    violations_by_type = Counter()

    for idx, row in df.iterrows():
        person_id = row.get("person_id", "")
        person_name = row.get("person_name", "")
        episode_text = row.get("episode_text", "")

        # birth_yearの取得（カラム名の違いに対応）
        birth_year = None
        for col in ["birth_year", "person_birth_year", "生年"]:
            if col in row and pd.notna(row[col]):
                try:
                    birth_year = int(row[col])
                    break
                except (ValueError, TypeError):
                    pass

        # ファクトチェック実行
        report = checker.check_episode(
            person_id=str(person_id),
            person_name=str(person_name),
            episode_text=str(episode_text) if pd.notna(episode_text) else "",
            birth_year=birth_year,
        )

        # 結果を記録
        result_value = report.result.value
        results.append(
            {
                "idx": idx,
                "person_name": person_name,
                "result": result_value,
                "score": report.total_score,
                "violations": len(report.violations),
                "violation_types": [v.violation_type for v in report.violations],
            }
        )

        result_counts[result_value] += 1

        for v in report.violations:
            violations_by_type[v.violation_type] += 1

        # 進捗表示
        if verbose and (idx + 1) % 1000 == 0:
            print(f"   処理中: {idx + 1:,}/{total:,}")

    print(f"   処理完了: {total:,}件")

    # 4. 結果サマリー
    print("\n3. 結果サマリー")
    print("   ファクトチェック結果:")
    for result, count in sorted(result_counts.items(), key=lambda x: -x[1]):
        pct = count / total * 100
        print(f"   - {result}: {count:,} ({pct:.1f}%)")

    if violations_by_type:
        print("\n   違反タイプ別:")
        for vtype, count in sorted(violations_by_type.items(), key=lambda x: -x[1]):
            print(f"   - {vtype}: {count:,}")

    # 5. CSVへの適用
    if apply:
        print("\n4. CSV更新中...")

        # 結果を日本語に変換
        result_mapping = {
            "verified": "確認済み",
            "unverified": "未確認",
            "incorrect": "要修正",
            "suspicious": "要精査",
            "partial": "部分確認",
        }

        for r in results:
            idx = r["idx"]
            result_ja = result_mapping.get(r["result"], r["result"])
            df.at[idx, "fact_check_result"] = result_ja

        # 保存
        df.to_csv(csv_path, index=False)
        print(f"   保存完了: {csv_path}")

    # 6. レポート生成
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = Path(f"src/reports/fact_check_batch_{timestamp}.json")
    report_data = {
        "timestamp": timestamp,
        "total_episodes": total,
        "mode": "apply" if apply else "dry_run",
        "results": dict(result_counts),
        "violations_by_type": dict(violations_by_type),
        "samples": {
            "verified": [r for r in results if r["result"] == "verified"][:5],
            "incorrect": [r for r in results if r["result"] == "incorrect"][:10],
            "suspicious": [r for r in results if r["result"] == "suspicious"][:10],
        },
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    print(f"\n5. レポート保存: {report_path}")

    # 結果サマリー
    summary = {
        "total": total,
        "verified": result_counts.get("verified", 0),
        "verified_pct": result_counts.get("verified", 0) / total * 100,
        "violations_total": sum(violations_by_type.values()),
        "applied": apply,
    }

    print("\n=== 完了 ===")
    print(f"確認済み: {summary['verified']:,}件 ({summary['verified_pct']:.1f}%)")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Batch Fact Check")
    parser.add_argument("--apply", action="store_true", help="本番適用（CSVに保存）")
    parser.add_argument("--quiet", action="store_true", help="詳細表示を抑制")
    args = parser.parse_args()

    csv_path = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")

    if not csv_path.exists():
        print(f"Error: {csv_path} が見つかりません")
        sys.exit(1)

    run_batch_fact_check(
        csv_path=csv_path,
        apply=args.apply,
        verbose=not args.quiet,
    )


if __name__ == "__main__":
    main()
