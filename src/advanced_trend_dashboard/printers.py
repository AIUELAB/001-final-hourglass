#!/usr/bin/env python3
"""高度トレンドダッシュボード - コンソール出力"""

from typing import Any, Dict, List

from .models import DashboardMetrics


def print_summary_metrics(metrics: DashboardMetrics) -> None:
    """サマリーメトリクス表示"""
    print(f"  総予測数: {metrics.total_predictions}件")
    print(f"  平均障害確率: {metrics.avg_failure_probability * 100:.2f}%")
    print(f"  平均モデル合意度: {metrics.avg_model_agreement * 100:.2f}%")
    print()
    print("  【リスクレベル分布】")
    print(f"    - HIGH: {metrics.high_risk_count}件")
    print(f"    - MEDIUM: {metrics.medium_risk_count}件")
    print(f"    - LOW: {metrics.low_risk_count}件")

    if metrics.latest_prediction:
        print()
        print("  【最新予測】")
        print(f"    - 時刻: {metrics.latest_prediction.timestamp}")
        print(f"    - 障害確率: {metrics.latest_prediction.failure_probability * 100:.2f}%")
        print(f"    - リスクレベル: {metrics.latest_prediction.risk_level}")
        print(f"    - モデル合意度: {metrics.latest_prediction.model_agreement * 100:.2f}%")


def print_prediction_trends(trends: Dict[str, Any]) -> None:
    """予測トレンド表示"""
    print(f"  データポイント数: {trends['data_points']}件")

    if trends["data_points"] > 0:
        stats = trends["statistics"]
        print()
        print("  【障害確率統計】")
        print(f"    - 平均: {stats['failure_probability']['mean'] * 100:.2f}%")
        print(f"    - 中央値: {stats['failure_probability']['median'] * 100:.2f}%")
        fp_min = stats["failure_probability"]["min"] * 100
        fp_max = stats["failure_probability"]["max"] * 100
        print(f"    - 最小/最大: {fp_min:.2f}% / {fp_max:.2f}%")
        print(f"    - 標準偏差: {stats['failure_probability']['std_dev'] * 100:.2f}%")
        print()
        print("  【モデル合意度統計】")
        print(f"    - 平均: {stats['model_agreement']['mean'] * 100:.2f}%")
        print(f"    - 中央値: {stats['model_agreement']['median'] * 100:.2f}%")
        ma_min = stats["model_agreement"]["min"] * 100
        ma_max = stats["model_agreement"]["max"] * 100
        print(f"    - 最小/最大: {ma_min:.2f}% / {ma_max:.2f}%")


def print_automl_history(experiments: List[Dict[str, Any]]) -> None:
    """AutoML実験履歴表示"""
    print(f"  実験数: {len(experiments)}件")

    if experiments:
        print()
        print("  【最新5実験】")
        for i, exp in enumerate(experiments[:5], 1):
            print(f"  {i}. [{exp['timestamp']}] {exp['best_model']}")
            print(f"     CVスコア: {exp['cv_mean']:.4f} ± {exp['cv_std']:.4f}")
            if exp.get("training_duration"):
                print(f"     訓練時間: {exp['training_duration']:.2f}秒")


def print_agreement_analysis(analysis: Dict[str, Any]) -> None:
    """モデル合意度分析表示"""
    if analysis["count"] == 0:
        print("  データなし")
        return

    stats = analysis["statistics"]
    dist = analysis["distribution"]

    print(f"  予測数: {analysis['count']}件")
    print()
    print("  【統計】")
    print(f"    - 平均: {stats['mean'] * 100:.2f}%")
    print(f"    - 中央値: {stats['median'] * 100:.2f}%")
    print(f"    - 最小/最大: {stats['min'] * 100:.2f}% / {stats['max'] * 100:.2f}%")
    print()
    print("  【分布】")
    print(f"    - 優秀 (≥95%): {dist['excellent']}件")
    print(f"    - 良好 (85-95%): {dist['good']}件")
    print(f"    - 普通 (75-85%): {dist['fair']}件")
    print(f"    - 要改善 (<75%): {dist['poor']}件")


def print_risk_distribution(distribution: Dict[str, Any]) -> None:
    """リスクレベル分布表示"""
    if not distribution:
        print("  データなし")
        return

    for level, data in distribution.items():
        print(f"  【{level}】")
        print(f"    - 件数: {data['count']}")
        print(f"    - 平均障害確率: {data['avg_failure_probability'] * 100:.2f}%")
        print(f"    - 平均モデル合意度: {data['avg_model_agreement'] * 100:.2f}%")
        print()


def print_factor_analysis(analysis: Dict[str, Any]) -> None:
    """寄与因子分析表示"""
    print(f"  ユニーク因子数: {analysis['total_unique_factors']}")

    if analysis["top_factors"]:
        print()
        print("  【Top 10 寄与因子】")
        for i, factor in enumerate(analysis["top_factors"][:10], 1):
            print(f"  {i}. {factor['feature']}: {factor['avg_importance'] * 100:.2f}%")


def print_alerts(alerts: List[Dict[str, Any]]) -> None:
    """アラート表示"""
    print(f"  アラート数: {len(alerts)}件")

    if alerts:
        print()
        level_symbols = {"critical": "🔴", "high": "🟡", "info": "🔵"}
        for i, alert in enumerate(alerts, 1):
            symbol = level_symbols.get(alert["level"], "⚪")
            print(f"  {i}. {symbol} [{alert['level'].upper()}] {alert['message']}")
            print(f"     カテゴリ: {alert['category']}")
