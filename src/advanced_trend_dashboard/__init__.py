#!/usr/bin/env python3
"""高度トレンドダッシュボード パッケージ

Phase 11.2 - 高度予測エンジン結果の可視化

機能:
- AutoML実験履歴の可視化
- アンサンブル予測結果の表示
- モデル合意度トレンド
- 寄与因子分析
- リアルタイムメトリクス
- インタラクティブグラフ（Plotly）
- アラート管理
"""

from .dashboard import AdvancedTrendDashboard, main
from .models import AutoMLExperiment, DashboardMetrics, PredictionTrend
from .plots import (
    PLOTLY_AVAILABLE,
    create_agreement_distribution_plot,
    create_automl_history_plot,
    create_contributing_factors_plot,
    create_prediction_trend_plot,
    create_risk_distribution_plot,
)
from .printers import (
    print_agreement_analysis,
    print_alerts,
    print_automl_history,
    print_factor_analysis,
    print_prediction_trends,
    print_risk_distribution,
    print_summary_metrics,
)

__all__ = [
    # Main class
    "AdvancedTrendDashboard",
    "main",
    # Models
    "PredictionTrend",
    "AutoMLExperiment",
    "DashboardMetrics",
    # Plots
    "PLOTLY_AVAILABLE",
    "create_prediction_trend_plot",
    "create_risk_distribution_plot",
    "create_agreement_distribution_plot",
    "create_contributing_factors_plot",
    "create_automl_history_plot",
    # Printers
    "print_summary_metrics",
    "print_prediction_trends",
    "print_automl_history",
    "print_agreement_analysis",
    "print_risk_distribution",
    "print_factor_analysis",
    "print_alerts",
]
