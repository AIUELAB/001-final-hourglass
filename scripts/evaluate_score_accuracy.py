# ruff: noqa: E402
#!/usr/bin/env python3
"""
LLMスコアと既存スコアの精度評価スクリプト

サンプルエピソードをLLMで評価し、既存スコアとの差異を分析する
"""

import random
import sys
from pathlib import Path

# backendモジュールをインポートするためのパス追加
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

import json
from datetime import datetime
from typing import Dict, List

import pandas as pd

from app.utils.llm_scorer import SEVEN_AXES, LLMScorer, compare_scores

CSV_PATH = PROJECT_ROOT / "MASTER_EPISODES_CURRENT.csv"
REPORT_DIR = PROJECT_ROOT / "reports"


def select_diverse_samples(df: pd.DataFrame, n: int = 50) -> pd.DataFrame:
    """
    多様なサンプルを選択（カテゴリ・スコア帯を分散）

    Args:
        df: エピソードDataFrame
        n: サンプル数

    Returns:
        サンプルDataFrame
    """
    samples = []

    # カテゴリ別に均等サンプリング
    categories = df["category"].unique()
    per_category = max(1, n // len(categories))

    for cat in categories:
        cat_df = df[df["category"] == cat]
        if len(cat_df) > 0:
            sample_size = min(per_category, len(cat_df))
            samples.append(cat_df.sample(n=sample_size, random_state=42))

    # 結合してシャッフル
    result = pd.concat(samples, ignore_index=True)

    # 目標数に調整
    if len(result) > n:
        result = result.sample(n=n, random_state=42)
    elif len(result) < n:
        remaining = n - len(result)
        additional = df[~df.index.isin(result.index)].sample(n=min(remaining, len(df) - len(result)), random_state=42)
        result = pd.concat([result, additional], ignore_index=True)

    return result


def extract_existing_scores(row: pd.Series) -> Dict[str, float]:
    """
    既存の7軸スコアを抽出

    Args:
        row: エピソード行

    Returns:
        7軸スコアの辞書
    """
    scores = {}
    for axis in SEVEN_AXES:
        value = row.get(axis)
        if pd.notna(value) and value != "":
            try:
                scores[axis] = float(value)
            except (ValueError, TypeError):
                scores[axis] = 0.0
        else:
            scores[axis] = 0.0
    return scores


def run_evaluation(sample_size: int = 50, dry_run: bool = False):
    """
    評価を実行

    Args:
        sample_size: サンプル数
        dry_run: Trueの場合、LLM呼び出しをスキップ
    """
    print("=" * 80)
    print("📊 LLMスコア精度評価")
    print("=" * 80)
    print()

    # データ読み込み
    print("Step 1: データ読み込み中...")
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    print(f"  ✅ 読み込み完了: {len(df):,}件")
    print()

    # サンプル選択
    print(f"Step 2: {sample_size}件のサンプルを選択中...")
    samples = select_diverse_samples(df, sample_size)
    print("  ✅ サンプル選択完了")
    print(f"  カテゴリ分布: {samples['category'].value_counts().to_dict()}")
    print()

    if dry_run:
        print("🔍 Dry Runモード - LLM呼び出しをスキップ")
        return

    # LLMスコアラー初期化
    print("Step 3: LLMスコアラー初期化...")
    try:
        scorer = LLMScorer()
        print("  ✅ 初期化完了")
    except ValueError as e:
        print(f"  ❌ エラー: {e}")
        return
    print()

    # 評価実行
    print(f"Step 4: {sample_size}件を評価中...")
    results = []

    def progress_callback(current, total, success):
        status = "✅" if success else "❌"
        print(f"  {status} {current}/{total} 完了")

    for idx, (_, row) in enumerate(samples.iterrows()):
        episode_dict = {
            "person_name": row.get("person_name", ""),
            "age": row.get("age", 0),
            "category": row.get("category", ""),
            "episode_type": row.get("episode_type", ""),
            "episode_text": row.get("episode_text", ""),
        }

        # LLMスコアリング
        llm_result = scorer.score_episode(**episode_dict)

        # 既存スコア取得
        existing_scores = extract_existing_scores(row)

        # 比較
        comparison = compare_scores(existing_scores, llm_result.scores) if llm_result.success else {}

        results.append(
            {
                "episode_id": row.get("episode_id", ""),
                "person_name": row.get("person_name", ""),
                "category": row.get("category", ""),
                "llm_success": llm_result.success,
                "existing_scores": existing_scores,
                "llm_scores": llm_result.scores,
                "reasoning": llm_result.reasoning,
                "comparison": comparison,
                "error": llm_result.error_message,
            }
        )

        progress_callback(idx + 1, sample_size, llm_result.success)

    print()

    # 結果分析
    print("Step 5: 結果分析...")
    success_count = sum(1 for r in results if r["llm_success"])
    print(f"  成功率: {success_count}/{sample_size} ({100*success_count/sample_size:.1f}%)")

    # 軸別の差異分析
    axis_diffs = {axis: [] for axis in SEVEN_AXES}
    significant_diffs = {axis: 0 for axis in SEVEN_AXES}

    for r in results:
        if r["llm_success"] and r["comparison"]:
            for axis in SEVEN_AXES:
                if axis in r["comparison"]:
                    diff = r["comparison"][axis]["difference"]
                    axis_diffs[axis].append(diff)
                    if r["comparison"][axis]["significant"]:
                        significant_diffs[axis] += 1

    print()
    print("  軸別差異分析:")
    print("  " + "-" * 60)
    print(f"  {'軸名':<16} {'平均差':>8} {'標準偏差':>10} {'有意差':>8}")
    print("  " + "-" * 60)

    analysis = {}
    for axis in SEVEN_AXES:
        diffs = axis_diffs[axis]
        if diffs:
            import statistics

            mean_diff = statistics.mean(diffs)
            std_diff = statistics.stdev(diffs) if len(diffs) > 1 else 0
            sig_count = significant_diffs[axis]

            analysis[axis] = {
                "mean_diff": round(mean_diff, 2),
                "std_diff": round(std_diff, 2),
                "significant_count": sig_count,
                "total": len(diffs),
            }

            print(f"  {axis:<16} {mean_diff:>+8.2f} {std_diff:>10.2f} {sig_count:>5}/{len(diffs)}")

    print("  " + "-" * 60)
    print()

    # 使用統計
    usage = scorer.get_usage_stats()
    print("Step 6: 使用統計:")
    print(f"  リクエスト数: {usage['request_count']}")
    print(f"  総トークン数: {usage['total_tokens']:,}")
    print(f"  推定コスト: ${usage['estimated_cost_usd']:.4f}")
    print()

    # レポート保存
    print("Step 7: レポート保存中...")
    REPORT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORT_DIR / f"llm_score_evaluation_{timestamp}.json"

    report = {
        "timestamp": timestamp,
        "sample_size": sample_size,
        "success_count": success_count,
        "success_rate": success_count / sample_size,
        "axis_analysis": analysis,
        "usage_stats": usage,
        "detailed_results": results,
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"  ✅ レポート保存: {report_path}")
    print()

    # サマリー
    print("=" * 80)
    print("📈 評価サマリー")
    print("=" * 80)
    print()

    # バイアス分析
    bias_axes = [axis for axis, data in analysis.items() if abs(data["mean_diff"]) >= 0.5]
    if bias_axes:
        print("⚠️ バイアスが疑われる軸（平均差±0.5以上）:")
        for axis in bias_axes:
            data = analysis[axis]
            direction = "高め" if data["mean_diff"] > 0 else "低め"
            print(f"  - {axis}: LLMが{direction}に評価（差: {data['mean_diff']:+.2f}）")
    else:
        print("✅ 大きなバイアスは検出されませんでした")

    print()

    # 推奨事項
    print("💡 推奨事項:")
    high_variance_axes = [axis for axis, data in analysis.items() if data["std_diff"] >= 1.5]
    if high_variance_axes:
        print("  - 以下の軸は評価基準の見直しを推奨:")
        for axis in high_variance_axes:
            print(f"    - {axis}（標準偏差: {analysis[axis]['std_diff']:.2f}）")
    else:
        print("  - 全軸で評価の一貫性が確認されました")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="LLMスコアと既存スコアの精度評価")
    parser.add_argument("--sample-size", type=int, default=50, help="評価するサンプル数（デフォルト: 50）")
    parser.add_argument("--dry-run", action="store_true", help="Dry Runモード（LLM呼び出しをスキップ）")

    args = parser.parse_args()
    run_evaluation(sample_size=args.sample_size, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
