#!/usr/bin/env python3
"""高度トレンドダッシュボード - Plotlyグラフ生成"""

from typing import Any, Dict, List

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    go = None
    make_subplots = None


def create_prediction_trend_plot(trends: Dict[str, Any]) -> Any:
    """予測トレンドグラフ作成"""
    if not PLOTLY_AVAILABLE:
        return None

    time_series = trends["time_series"]
    timestamps = [point["timestamp"] for point in time_series]
    failure_probs = [point["failure_probability"] * 100 for point in time_series]
    agreements = [point["model_agreement"] * 100 for point in time_series]

    fig = make_subplots(
        rows=2,
        cols=1,
        subplot_titles=("障害確率の推移", "モデル合意度の推移"),
        vertical_spacing=0.15,
    )

    fig.add_trace(
        go.Scatter(
            x=timestamps,
            y=failure_probs,
            mode="lines+markers",
            name="障害確率",
            line=dict(color="#e74c3c", width=2),
            marker=dict(size=6),
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=timestamps,
            y=agreements,
            mode="lines+markers",
            name="モデル合意度",
            line=dict(color="#3498db", width=2),
            marker=dict(size=6),
        ),
        row=2,
        col=1,
    )

    fig.update_xaxes(title_text="時刻", row=2, col=1)
    fig.update_yaxes(title_text="障害確率 (%)", row=1, col=1)
    fig.update_yaxes(title_text="モデル合意度 (%)", row=2, col=1)
    fig.update_layout(title_text="予測トレンド分析", height=600, showlegend=True)

    return fig


def create_risk_distribution_plot(risk_dist: Dict[str, Any]) -> Any:
    """リスクレベル分布グラフ作成"""
    if not PLOTLY_AVAILABLE:
        return None

    labels = list(risk_dist.keys())
    values = [risk_dist[label]["count"] for label in labels]
    colors = {"HIGH": "#e74c3c", "MEDIUM": "#f39c12", "LOW": "#27ae60"}
    color_list = [colors.get(label, "#95a5a6") for label in labels]

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                marker=dict(colors=color_list),
                textinfo="label+percent",
                hovertemplate="<b>%{label}</b><br>件数: %{value}<br>割合: %{percent}<extra></extra>",
            )
        ]
    )
    fig.update_layout(title_text="リスクレベル分布", height=400)

    return fig


def create_agreement_distribution_plot(agreement: Dict[str, Any]) -> Any:
    """モデル合意度分布グラフ作成"""
    if not PLOTLY_AVAILABLE:
        return None

    dist = agreement["distribution"]
    labels = ["優秀 (≥95%)", "良好 (85-95%)", "普通 (75-85%)", "要改善 (<75%)"]
    values = [dist["excellent"], dist["good"], dist["fair"], dist["poor"]]

    fig = go.Figure(
        data=[
            go.Bar(
                x=labels,
                y=values,
                marker=dict(color=["#27ae60", "#3498db", "#f39c12", "#e74c3c"]),
                text=values,
                textposition="auto",
            )
        ]
    )
    fig.update_layout(
        title_text="モデル合意度分布",
        xaxis_title="合意度レベル",
        yaxis_title="予測回数",
        height=400,
    )

    return fig


def create_contributing_factors_plot(factors: Dict[str, Any]) -> Any:
    """寄与因子グラフ作成"""
    if not PLOTLY_AVAILABLE:
        return None

    top_factors = factors["top_factors"]
    features = [f["feature"] for f in top_factors]
    importances = [f["avg_importance"] * 100 for f in top_factors]

    fig = go.Figure(
        data=[
            go.Bar(
                x=importances,
                y=features,
                orientation="h",
                marker=dict(color="#3498db"),
                text=[f"{imp:.2f}%" for imp in importances],
                textposition="auto",
            )
        ]
    )
    fig.update_layout(
        title_text="寄与因子分析（Top 10）",
        xaxis_title="平均重要度 (%)",
        yaxis_title="特徴量",
        height=500,
    )

    return fig


def create_automl_history_plot(automl: List[Dict[str, Any]]) -> Any:
    """AutoML実験履歴グラフ作成"""
    if not PLOTLY_AVAILABLE:
        return None

    experiment_ids = [exp["experiment_id"][-8:] for exp in automl]
    cv_scores = [exp["cv_mean"] for exp in automl]
    cv_stds = [exp["cv_std"] for exp in automl]

    fig = go.Figure(
        data=[
            go.Bar(
                x=experiment_ids,
                y=cv_scores,
                error_y=dict(type="data", array=cv_stds),
                marker=dict(color="#9b59b6"),
                text=[f"{score:.4f}" for score in cv_scores],
                textposition="auto",
            )
        ]
    )
    fig.update_layout(
        title_text="AutoML実験履歴（CVスコア）",
        xaxis_title="実験ID",
        yaxis_title="CVスコア（F1-weighted）",
        height=400,
    )

    return fig
