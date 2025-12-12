#!/usr/bin/env python3
"""
EPUP評価比較スクリプト

使用方法:
    python scripts/compare_epup_scores.py \
        --baseline reports/epup_baseline_before_normalization.json \
        --after reports/epup_after_normalization.json \
        --output reports/epup_comparison.json
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

REPORTS_DIR = Path(__file__).parent.parent / "reports"


def load_json(path: Path) -> dict:
    """JSONファイルを読み込み"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def compare_evaluations(baseline: dict, after: dict) -> dict:
    """EPUP評価の前後比較"""
    comparison = {
        "timestamp": datetime.now().isoformat(),
        "baseline_file": str(baseline.get("csv_path", "N/A")),
        "after_file": str(after.get("csv_path", "N/A")),
        "overall": {
            "baseline_score": baseline["epup_score"]["total_score"],
            "after_score": after["epup_score"]["total_score"],
            "delta": after["epup_score"]["total_score"] - baseline["epup_score"]["total_score"],
            "baseline_grade": baseline["epup_score"]["grade"],
            "after_grade": after["epup_score"]["grade"],
        },
        "data_changes": {
            "episodes_before": baseline.get("total_episodes", 0),
            "episodes_after": after.get("total_episodes", 0),
            "episodes_delta": after.get("total_episodes", 0) - baseline.get("total_episodes", 0),
        },
        "individual_changes": {},
        "improvements": [],
        "regressions": [],
    }

    # 各指標の変化を記録
    baseline_scores = baseline["epup_score"].get("individual_scores", {})
    after_scores = after["epup_score"].get("individual_scores", {})

    all_keys = set(baseline_scores.keys()) | set(after_scores.keys())

    for key in sorted(all_keys):
        before_val = baseline_scores.get(key, 0)
        after_val = after_scores.get(key, 0)
        delta = after_val - before_val

        comparison["individual_changes"][key] = {
            "before": before_val,
            "after": after_val,
            "delta": delta,
        }

        if delta > 0.5:
            comparison["improvements"].append(
                {
                    "metric": key,
                    "before": before_val,
                    "after": after_val,
                    "delta": delta,
                }
            )
        elif delta < -0.5:
            comparison["regressions"].append(
                {
                    "metric": key,
                    "before": before_val,
                    "after": after_val,
                    "delta": delta,
                }
            )

    return comparison


def print_comparison(comparison: dict):
    """比較結果を表示"""
    print("=" * 70)
    print("📊 EPUP評価比較レポート")
    print("=" * 70)
    print(f"  生成日時: {comparison['timestamp']}")

    print("\n【総合スコア】")
    overall = comparison["overall"]
    delta_sign = "+" if overall["delta"] >= 0 else ""
    print(f"  処理前: {overall['baseline_score']:.2f} (グレード: {overall['baseline_grade']})")
    print(f"  処理後: {overall['after_score']:.2f} (グレード: {overall['after_grade']})")
    print(f"  変化: {delta_sign}{overall['delta']:.2f}")

    print("\n【データ変化】")
    data = comparison["data_changes"]
    print(f"  エピソード数: {data['episodes_before']} → {data['episodes_after']} ({data['episodes_delta']:+d})")

    if comparison["improvements"]:
        print("\n【改善項目】 ✅")
        for imp in comparison["improvements"]:
            print(f"  {imp['metric']}: {imp['before']:.1f} → {imp['after']:.1f} (+{imp['delta']:.1f})")

    if comparison["regressions"]:
        print("\n【低下項目】 ⚠️")
        for reg in comparison["regressions"]:
            print(f"  {reg['metric']}: {reg['before']:.1f} → {reg['after']:.1f} ({reg['delta']:.1f})")

    print("\n" + "=" * 70)


def main():
    parser = argparse.ArgumentParser(description="EPUP評価比較")
    parser.add_argument("--baseline", required=True, help="ベースラインJSONファイル")
    parser.add_argument("--after", required=True, help="処理後JSONファイル")
    parser.add_argument("--output", help="出力JSONファイル")
    args = parser.parse_args()

    baseline_path = Path(args.baseline)
    after_path = Path(args.after)

    print(f"📂 ベースライン: {baseline_path}")
    print(f"📂 処理後: {after_path}")

    baseline = load_json(baseline_path)
    after = load_json(after_path)

    comparison = compare_evaluations(baseline, after)

    print_comparison(comparison)

    # 出力
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = REPORTS_DIR / f"epup_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(comparison, f, ensure_ascii=False, indent=2)
    print(f"\n📄 レポート保存: {output_path}")


if __name__ == "__main__":
    main()
