#!/usr/bin/env python3
"""
全エピソードスコア再計算スクリプト

composite_scoreを統一された計算方法で再計算し、
全データの一貫性を確保する
"""

import sys
from pathlib import Path

# backendモジュールをインポートするためのパス追加
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

import json
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd

from app.utils.score_calculator import (
    SEVEN_AXIS_FIELDS,
    calculate_composite_score,
    count_valid_axes,
    format_composite_score,
    get_score_breakdown,
)

CSV_PATH = PROJECT_ROOT / "MASTER_EPISODES_CURRENT.csv"
REPORT_DIR = PROJECT_ROOT / "reports"


def recalculate_composite_scores(df: pd.DataFrame, min_axes: int = 1) -> pd.DataFrame:
    """
    全エピソードのcomposite_scoreを再計算

    Args:
        df: エピソードDataFrame
        min_axes: 計算に必要な最低軸数

    Returns:
        更新されたDataFrame
    """
    updated_count = 0
    no_change_count = 0
    newly_calculated = 0
    insufficient_data = 0

    for idx, row in df.iterrows():
        # 行データを辞書に変換
        episode_dict = row.to_dict()

        # 新しいcomposite_scoreを計算
        new_score = calculate_composite_score(episode_dict, min_axes)

        # 現在の値を取得
        current_score = row.get("composite_score")
        current_score_float = None
        if pd.notna(current_score) and current_score != "":
            try:
                current_score_float = float(current_score)
            except (ValueError, TypeError):
                pass

        # 新しいスコアがある場合
        if new_score is not None:
            # 以前のスコアと比較
            if current_score_float is None:
                newly_calculated += 1
                df.at[idx, "composite_score"] = format_composite_score(new_score)
            elif abs(new_score - current_score_float) > 0.01:
                updated_count += 1
                df.at[idx, "composite_score"] = format_composite_score(new_score)
            else:
                no_change_count += 1
        else:
            insufficient_data += 1
            # スコアを空にする（データ不足）
            df.at[idx, "composite_score"] = ""

    return df, {
        "updated": updated_count,
        "no_change": no_change_count,
        "newly_calculated": newly_calculated,
        "insufficient_data": insufficient_data,
        "total": len(df),
    }


def analyze_score_distribution(df: pd.DataFrame) -> Dict:
    """
    スコア分布を分析

    Args:
        df: エピソードDataFrame

    Returns:
        分析結果の辞書
    """
    # composite_scoreの分布
    scores = []
    for val in df["composite_score"]:
        if pd.notna(val) and val != "":
            try:
                scores.append(float(val))
            except (ValueError, TypeError):
                pass

    if not scores:
        return {"error": "No valid scores found"}

    # 基本統計
    stats = {
        "count": len(scores),
        "mean": sum(scores) / len(scores),
        "min": min(scores),
        "max": max(scores),
        "distribution": {
            "9.0-10.0": sum(1 for s in scores if s >= 9.0),
            "8.0-8.9": sum(1 for s in scores if 8.0 <= s < 9.0),
            "7.0-7.9": sum(1 for s in scores if 7.0 <= s < 8.0),
            "6.0-6.9": sum(1 for s in scores if 6.0 <= s < 7.0),
            "5.0-5.9": sum(1 for s in scores if 5.0 <= s < 6.0),
            "0.0-4.9": sum(1 for s in scores if s < 5.0),
        },
    }

    # 各軸の欠損状況
    axis_completeness = {}
    for axis in SEVEN_AXIS_FIELDS:
        valid_count = 0
        for val in df[axis]:
            if pd.notna(val) and val != "":
                try:
                    float(val)
                    valid_count += 1
                except (ValueError, TypeError):
                    pass
        axis_completeness[axis] = {
            "valid": valid_count,
            "missing": len(df) - valid_count,
            "percentage": (valid_count / len(df)) * 100,
        }

    stats["axis_completeness"] = axis_completeness

    return stats


def main():
    import argparse

    parser = argparse.ArgumentParser(description="全エピソードスコア再計算スクリプト")
    parser.add_argument("--save", action="store_true", help="実際にCSVに保存する（デフォルトはdry run）")
    parser.add_argument("--min-axes", type=int, default=1, help="計算に必要な最低軸数（デフォルト: 1）")
    parser.add_argument("--report", action="store_true", help="詳細レポートをJSONで出力")

    args = parser.parse_args()

    print("=" * 80)
    print("📊 全エピソードスコア再計算")
    print("=" * 80)
    print()

    # CSVファイル読み込み
    print("Step 1: CSVファイル読み込み中...")
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    print(f"  ✅ 読み込み完了: {len(df):,}件")
    print()

    # 再計算前の分布
    print("Step 2: 再計算前のスコア分布...")
    before_stats = analyze_score_distribution(df)
    print(f"  有効スコア数: {before_stats['count']:,}件")
    print(f"  平均スコア: {before_stats['mean']:.2f}")
    print(f"  最小/最大: {before_stats['min']:.2f} / {before_stats['max']:.2f}")
    print()

    # 軸の完全性
    print("Step 3: 7軸スコアの完全性...")
    for axis, info in before_stats["axis_completeness"].items():
        pct = info["percentage"]
        bar = "█" * int(pct / 5)
        print(f"  {axis}: {info['valid']:,}件 ({pct:.1f}%) {bar}")
    print()

    # スコア再計算
    print(f"Step 4: composite_score再計算中（最低軸数: {args.min_axes}）...")
    df, recalc_stats = recalculate_composite_scores(df, args.min_axes)
    print("  ✅ 再計算完了")
    print(f"    - 更新: {recalc_stats['updated']:,}件")
    print(f"    - 新規計算: {recalc_stats['newly_calculated']:,}件")
    print(f"    - 変更なし: {recalc_stats['no_change']:,}件")
    print(f"    - データ不足: {recalc_stats['insufficient_data']:,}件")
    print()

    # 再計算後の分布
    print("Step 5: 再計算後のスコア分布...")
    after_stats = analyze_score_distribution(df)
    print(f"  有効スコア数: {after_stats['count']:,}件")
    print(f"  平均スコア: {after_stats['mean']:.2f}")
    print()

    print("  分布詳細:")
    for range_name, count in after_stats["distribution"].items():
        pct = (count / after_stats["count"]) * 100 if after_stats["count"] > 0 else 0
        bar = "█" * int(pct / 2)
        print(f"    {range_name}: {count:,}件 ({pct:.1f}%) {bar}")
    print()

    if args.save:
        # バックアップ作成
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = PROJECT_ROOT / f"MASTER_EPISODES_CURRENT_backup_before_recalc_{timestamp}.csv"

        print("Step 6: バックアップ作成中...")
        original_df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
        original_df.to_csv(backup_path, index=False, encoding="utf-8-sig")
        print(f"  ✅ バックアップ作成: {backup_path}")
        print()

        # 保存
        print("Step 7: 保存中...")
        df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
        print(f"  ✅ 保存完了: {CSV_PATH}")
        print()

        print("=" * 80)
        print("✅ 全エピソードスコア再計算が完了しました！")
        print("=" * 80)
    else:
        print("=" * 80)
        print("🔍 Dry Run モード - 実際の保存は行いません")
        print("   保存するには --save オプションを付けて実行してください")
        print("=" * 80)

    # レポート出力
    if args.report:
        REPORT_DIR.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = REPORT_DIR / f"score_recalculation_report_{timestamp}.json"

        report = {
            "timestamp": timestamp,
            "csv_path": str(CSV_PATH),
            "min_axes": args.min_axes,
            "saved": args.save,
            "before_stats": before_stats,
            "after_stats": after_stats,
            "recalculation_stats": recalc_stats,
        }

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print()
        print(f"📄 レポート出力: {report_path}")


if __name__ == "__main__":
    main()
