# ruff: noqa: E402
#!/usr/bin/env python3
"""
5軸スコア再計算スクリプト

改善されたルールベース計算で5軸スコアを再計算し、
スコア分布を正規化する
"""

import sys
from pathlib import Path

# backendモジュールをインポートするためのパス追加
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

import json
import statistics
from datetime import datetime
from typing import Dict

import pandas as pd

from app.utils.score_calculator import (
    calculate_composite_score,
    calculate_educational_value_score,
    calculate_empathy_score,
    calculate_generation_quality_score,
    calculate_memorability_score,
    calculate_surprise_score,
    format_composite_score,
)

CSV_PATH = PROJECT_ROOT / "MASTER_EPISODES_CURRENT.csv"
REPORT_DIR = PROJECT_ROOT / "reports"

# 再計算対象の5軸
FIVE_AXES = ["memorability_score", "empathy_score", "surprise_score", "generation_quality_score", "educational_value"]


def analyze_distribution(values: list) -> Dict:
    """スコア分布を分析"""
    if not values:
        return {}

    return {
        "count": len(values),
        "mean": round(statistics.mean(values), 2),
        "median": round(statistics.median(values), 2),
        "stdev": round(statistics.stdev(values), 2) if len(values) > 1 else 0,
        "min": round(min(values), 2),
        "max": round(max(values), 2),
        "distribution": {
            "9.0-10.0": sum(1 for v in values if v >= 9.0),
            "8.0-8.9": sum(1 for v in values if 8.0 <= v < 9.0),
            "7.0-7.9": sum(1 for v in values if 7.0 <= v < 8.0),
            "6.0-6.9": sum(1 for v in values if 6.0 <= v < 7.0),
            "5.0-5.9": sum(1 for v in values if 5.0 <= v < 6.0),
            "1.0-4.9": sum(1 for v in values if v < 5.0),
        },
    }


def recalculate_five_axes(dry_run: bool = True, update_composite: bool = True):
    """
    5軸スコアを再計算

    Args:
        dry_run: Trueの場合、実際の保存は行わない
        update_composite: Trueの場合、composite_scoreも再計算
    """
    print("=" * 80)
    print("📊 5軸スコア再計算（改善版ルールベース）")
    print("=" * 80)
    print()

    # データ読み込み
    print("Step 1: データ読み込み中...")
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    print(f"  ✅ 読み込み完了: {len(df):,}件")
    print()

    # 再計算前の分布
    print("Step 2: 再計算前の分布分析...")
    before_stats = {}
    for axis in FIVE_AXES:
        values = []
        for val in df[axis]:
            if pd.notna(val) and val != "":
                try:
                    values.append(float(val))
                except (ValueError, TypeError):
                    pass
        before_stats[axis] = analyze_distribution(values)
        print(
            f"  {axis}: 平均={before_stats[axis].get('mean', 'N/A')}, "
            f"標準偏差={before_stats[axis].get('stdev', 'N/A')}"
        )
    print()

    # 再計算
    print("Step 3: 5軸スコア再計算中...")
    changes = {axis: {"updated": 0, "no_change": 0, "diffs": []} for axis in FIVE_AXES}

    for idx, row in df.iterrows():
        episode_dict = row.to_dict()

        # 各軸を計算
        new_scores = {
            "memorability_score": calculate_memorability_score(episode_dict),
            "empathy_score": calculate_empathy_score(episode_dict),
            "surprise_score": calculate_surprise_score(episode_dict),
            "generation_quality_score": calculate_generation_quality_score(episode_dict),
            "educational_value": calculate_educational_value_score(episode_dict),
        }

        for axis, new_score in new_scores.items():
            old_val = row.get(axis)
            try:
                old_score = float(old_val) if pd.notna(old_val) and old_val != "" else None
            except (ValueError, TypeError):
                old_score = None

            if old_score is None or abs(new_score - old_score) > 0.01:
                changes[axis]["updated"] += 1
                if old_score is not None:
                    changes[axis]["diffs"].append(new_score - old_score)
                df.at[idx, axis] = new_score
            else:
                changes[axis]["no_change"] += 1

        if (idx + 1) % 500 == 0:
            print(f"  処理中... {idx + 1:,}/{len(df):,}件")

    print("  ✅ 再計算完了")
    print()

    # 変更サマリー
    print("Step 4: 変更サマリー:")
    for axis in FIVE_AXES:
        updated = changes[axis]["updated"]
        diffs = changes[axis]["diffs"]
        avg_diff = statistics.mean(diffs) if diffs else 0
        print(f"  {axis}:")
        print(f"    更新: {updated:,}件")
        print(f"    平均変化: {avg_diff:+.2f}点")
    print()

    # composite_score再計算
    if update_composite:
        print("Step 5: composite_score再計算中...")
        composite_updated = 0
        for idx, row in df.iterrows():
            episode_dict = row.to_dict()
            new_composite = calculate_composite_score(episode_dict)
            df.at[idx, "composite_score"] = format_composite_score(new_composite)
            composite_updated += 1
        print(f"  ✅ 再計算完了: {composite_updated:,}件")
        print()

    # 再計算後の分布
    print("Step 6: 再計算後の分布分析...")
    after_stats = {}
    for axis in FIVE_AXES:
        values = []
        for val in df[axis]:
            if pd.notna(val) and val != "":
                try:
                    values.append(float(val))
                except (ValueError, TypeError):
                    pass
        after_stats[axis] = analyze_distribution(values)
        print(
            f"  {axis}: 平均={after_stats[axis].get('mean', 'N/A')}, "
            f"標準偏差={after_stats[axis].get('stdev', 'N/A')}"
        )
    print()

    # 分布の改善確認
    print("Step 7: 分布改善の確認:")
    print("  " + "-" * 60)
    print(f"  {'軸名':<16} {'前:標準偏差':>12} {'後:標準偏差':>12} {'改善':>8}")
    print("  " + "-" * 60)
    for axis in FIVE_AXES:
        before_std = before_stats[axis].get("stdev", 0)
        after_std = after_stats[axis].get("stdev", 0)
        improved = "✅" if after_std > before_std else "➖"
        print(f"  {axis:<16} {before_std:>12.2f} {after_std:>12.2f} {improved:>8}")
    print("  " + "-" * 60)
    print()

    if dry_run:
        print("=" * 80)
        print("🔍 Dry Run モード - 実際の保存は行いません")
        print("   保存するには --save オプションを付けて実行してください")
        print("=" * 80)
    else:
        # バックアップ作成
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = PROJECT_ROOT / f"MASTER_EPISODES_CURRENT_backup_before_5axes_{timestamp}.csv"

        print("Step 8: バックアップ作成中...")
        original_df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
        original_df.to_csv(backup_path, index=False, encoding="utf-8-sig")
        print(f"  ✅ バックアップ作成: {backup_path}")
        print()

        # 保存
        print("Step 9: 保存中...")
        df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
        print(f"  ✅ 保存完了: {CSV_PATH}")
        print()

        # data/ ディレクトリにも同期
        data_csv_path = PROJECT_ROOT / "data" / "MASTER_EPISODES_CURRENT.csv"
        if data_csv_path.parent.exists():
            df.to_csv(data_csv_path, index=False, encoding="utf-8-sig")
            print(f"  ✅ 同期完了: {data_csv_path}")

        print()
        print("=" * 80)
        print("✅ 5軸スコア再計算が完了しました！")
        print("=" * 80)

    # レポート保存
    REPORT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORT_DIR / f"five_axes_recalculation_report_{timestamp}.json"

    report = {
        "timestamp": timestamp,
        "saved": not dry_run,
        "before_stats": before_stats,
        "after_stats": after_stats,
        "changes": {
            axis: {
                "updated": changes[axis]["updated"],
                "avg_diff": statistics.mean(changes[axis]["diffs"]) if changes[axis]["diffs"] else 0,
            }
            for axis in FIVE_AXES
        },
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print()
    print(f"📄 レポート出力: {report_path}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="5軸スコア再計算スクリプト")
    parser.add_argument("--save", action="store_true", help="実際にCSVに保存する（デフォルトはdry run）")
    parser.add_argument("--no-composite", action="store_true", help="composite_scoreの再計算をスキップ")

    args = parser.parse_args()
    recalculate_five_axes(dry_run=not args.save, update_composite=not args.no_composite)


if __name__ == "__main__":
    main()
