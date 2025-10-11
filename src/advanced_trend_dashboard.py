#!/usr/bin/env python3
"""
高度トレンド分析ダッシュボード（Phase 11.2）
Advanced Trend Analysis Dashboard

Phase 11.1の高度予測エンジン結果を可視化

機能:
- AutoML実験履歴の可視化
- アンサンブル予測結果の表示
- モデル合意度トレンド
- 寄与因子分析
- リアルタイムメトリクス
- インタラクティブグラフ（Plotly）
- アラート管理
"""

import os
import sys
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import statistics

# プロジェクトルート設定
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    go = None  # 型ヒント用のダミー
    make_subplots = None
    px = None
    print("⚠️ Plotlyがインストールされていません。基本的なテキストベース表示のみ利用可能です。")
    print("   インストール: pip install plotly")


@dataclass
class PredictionTrend:
    """予測トレンドデータ"""
    timestamp: str
    failure_probability: float
    risk_level: str
    model_agreement: float
    ensemble_predictions: Dict[str, float]


@dataclass
class AutoMLExperiment:
    """AutoML実験データ"""
    experiment_id: str
    timestamp: str
    best_model: str
    best_score: float
    cv_mean: float
    cv_std: float
    model_scores: Dict[str, float]


@dataclass
class DashboardMetrics:
    """ダッシュボードメトリクス"""
    total_predictions: int
    avg_failure_probability: float
    avg_model_agreement: float
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    latest_prediction: Optional[PredictionTrend]
    latest_experiment: Optional[AutoMLExperiment]


class AdvancedTrendDashboard:
    """高度トレンド分析ダッシュボード"""

    def __init__(self, db_path: Path = PROJECT_ROOT / "unified_quality.db"):
        self.db_path = db_path
        self.reports_dir = PROJECT_ROOT / "reports" / "advanced_trends"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        # データベーステーブル初期化
        self._init_database_tables()

    def _init_database_tables(self):
        """データベーステーブル初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # advanced_prediction_history テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS advanced_prediction_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prediction_id TEXT NOT NULL UNIQUE,
                timestamp TEXT NOT NULL,
                failure_probability REAL NOT NULL,
                risk_level TEXT NOT NULL,
                model_agreement REAL NOT NULL,
                confidence REAL NOT NULL,
                ensemble_predictions TEXT NOT NULL,
                contributing_factors TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # automl_experiments テーブル（既存スキーマを尊重）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS automl_experiments (
                experiment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                best_model_name TEXT NOT NULL,
                best_params TEXT,
                cv_scores TEXT,
                mean_cv_score REAL,
                std_cv_score REAL,
                feature_importance TEXT,
                model_path TEXT
            )
        """)

        conn.commit()
        conn.close()

    def generate_comprehensive_dashboard(
        self,
        hours: int = 24,
        include_plots: bool = True
    ) -> Dict[str, Any]:
        """
        包括的ダッシュボード生成

        Args:
            hours: 分析時間範囲
            include_plots: Plotlyグラフを含めるか

        Returns:
            ダッシュボードデータ
        """
        print("=" * 80)
        print("📊 Phase 11.2 - 高度トレンド分析ダッシュボード")
        print("=" * 80)
        print(f"分析期間: 過去{hours}時間")
        print(f"生成時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        print()

        dashboard = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "analysis_period_hours": hours,
                "plotly_enabled": PLOTLY_AVAILABLE and include_plots
            },
            "sections": {}
        }

        # セクション1: サマリーメトリクス
        print("📌 セクション1: サマリーメトリクス")
        print("-" * 80)
        metrics = self._get_summary_metrics(hours)
        dashboard["sections"]["summary"] = metrics
        self._print_summary_metrics(metrics)
        print()

        # セクション2: 予測トレンド分析
        print("📌 セクション2: 予測トレンド分析")
        print("-" * 80)
        prediction_trends = self._analyze_prediction_trends(hours)
        dashboard["sections"]["prediction_trends"] = prediction_trends
        self._print_prediction_trends(prediction_trends)
        print()

        # セクション3: AutoML実験履歴
        print("📌 セクション3: AutoML実験履歴")
        print("-" * 80)
        automl_history = self._get_automl_history(limit=10)
        dashboard["sections"]["automl_history"] = automl_history
        self._print_automl_history(automl_history)
        print()

        # セクション4: モデル合意度分析
        print("📌 セクション4: モデル合意度分析")
        print("-" * 80)
        agreement_analysis = self._analyze_model_agreement(hours)
        dashboard["sections"]["model_agreement"] = agreement_analysis
        self._print_agreement_analysis(agreement_analysis)
        print()

        # セクション5: リスクレベル分布
        print("📌 セクション5: リスクレベル分布")
        print("-" * 80)
        risk_distribution = self._analyze_risk_distribution(hours)
        dashboard["sections"]["risk_distribution"] = risk_distribution
        self._print_risk_distribution(risk_distribution)
        print()

        # セクション6: 寄与因子分析
        print("📌 セクション6: 寄与因子分析")
        print("-" * 80)
        factor_analysis = self._analyze_contributing_factors(hours)
        dashboard["sections"]["contributing_factors"] = factor_analysis
        self._print_factor_analysis(factor_analysis)
        print()

        # セクション7: アラート一覧
        print("📌 セクション7: アラート一覧")
        print("-" * 80)
        alerts = self._generate_alerts(metrics, prediction_trends)
        dashboard["sections"]["alerts"] = alerts
        self._print_alerts(alerts)
        print()

        # Plotlyグラフ生成
        if PLOTLY_AVAILABLE and include_plots:
            print("📌 セクション8: インタラクティブグラフ生成")
            print("-" * 80)
            plots = self._generate_plotly_graphs(dashboard)
            dashboard["sections"]["plots"] = plots
            print(f"✅ {len(plots)}個のグラフを生成しました")
            print()

        print("=" * 80)
        print("✅ ダッシュボード生成完了")
        print("=" * 80)

        return dashboard

    def _get_summary_metrics(self, hours: int) -> DashboardMetrics:
        """サマリーメトリクス取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()

        # 総予測数
        cursor.execute("""
            SELECT COUNT(*) FROM advanced_prediction_history
            WHERE timestamp >= ?
        """, (cutoff_time,))
        total_predictions = cursor.fetchone()[0]

        # 平均障害確率
        cursor.execute("""
            SELECT AVG(failure_probability) FROM advanced_prediction_history
            WHERE timestamp >= ?
        """, (cutoff_time,))
        avg_failure_prob = cursor.fetchone()[0] or 0.0

        # 平均モデル合意度
        cursor.execute("""
            SELECT AVG(model_agreement) FROM advanced_prediction_history
            WHERE timestamp >= ?
        """, (cutoff_time,))
        avg_agreement = cursor.fetchone()[0] or 0.0

        # リスクレベル別カウント
        cursor.execute("""
            SELECT risk_level, COUNT(*) FROM advanced_prediction_history
            WHERE timestamp >= ?
            GROUP BY risk_level
        """, (cutoff_time,))
        risk_counts = dict(cursor.fetchall())

        # 最新予測
        cursor.execute("""
            SELECT prediction_id, timestamp, failure_probability, risk_level,
                   model_agreement, ensemble_predictions
            FROM advanced_prediction_history
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        latest_row = cursor.fetchone()
        latest_prediction = None
        if latest_row:
            latest_prediction = PredictionTrend(
                timestamp=latest_row[1],
                failure_probability=latest_row[2],
                risk_level=latest_row[3],
                model_agreement=latest_row[4],
                ensemble_predictions=json.loads(latest_row[5])
            )

        # 最新AutoML実験
        cursor.execute("""
            SELECT experiment_id, timestamp, best_model_name,
                   mean_cv_score, std_cv_score, cv_scores
            FROM automl_experiments
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        latest_exp_row = cursor.fetchone()
        latest_experiment = None
        if latest_exp_row:
            cv_scores_data = json.loads(latest_exp_row[5]) if latest_exp_row[5] else {}
            latest_experiment = AutoMLExperiment(
                experiment_id=str(latest_exp_row[0]),
                timestamp=latest_exp_row[1],
                best_model=latest_exp_row[2],
                best_score=latest_exp_row[3] or 0.0,
                cv_mean=latest_exp_row[3] or 0.0,
                cv_std=latest_exp_row[4] or 0.0,
                model_scores=cv_scores_data
            )

        conn.close()

        return DashboardMetrics(
            total_predictions=total_predictions,
            avg_failure_probability=avg_failure_prob,
            avg_model_agreement=avg_agreement,
            high_risk_count=risk_counts.get("HIGH", 0),
            medium_risk_count=risk_counts.get("MEDIUM", 0),
            low_risk_count=risk_counts.get("LOW", 0),
            latest_prediction=latest_prediction,
            latest_experiment=latest_experiment
        )

    def _analyze_prediction_trends(self, hours: int) -> Dict[str, Any]:
        """予測トレンド分析"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()

        cursor.execute("""
            SELECT timestamp, failure_probability, model_agreement, risk_level
            FROM advanced_prediction_history
            WHERE timestamp >= ?
            ORDER BY timestamp ASC
        """, (cutoff_time,))

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return {
                "data_points": 0,
                "time_series": [],
                "statistics": {}
            }

        time_series = []
        failure_probs = []
        agreements = []

        for row in rows:
            time_series.append({
                "timestamp": row[0],
                "failure_probability": row[1],
                "model_agreement": row[2],
                "risk_level": row[3]
            })
            failure_probs.append(row[1])
            agreements.append(row[2])

        statistics_data = {
            "failure_probability": {
                "mean": round(statistics.mean(failure_probs), 4),
                "median": round(statistics.median(failure_probs), 4),
                "min": round(min(failure_probs), 4),
                "max": round(max(failure_probs), 4),
                "std_dev": round(statistics.stdev(failure_probs), 4) if len(failure_probs) > 1 else 0.0
            },
            "model_agreement": {
                "mean": round(statistics.mean(agreements), 4),
                "median": round(statistics.median(agreements), 4),
                "min": round(min(agreements), 4),
                "max": round(max(agreements), 4),
                "std_dev": round(statistics.stdev(agreements), 4) if len(agreements) > 1 else 0.0
            }
        }

        return {
            "data_points": len(time_series),
            "time_series": time_series,
            "statistics": statistics_data
        }

    def _get_automl_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """AutoML実験履歴取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT experiment_id, timestamp, best_model_name,
                   mean_cv_score, std_cv_score, cv_scores
            FROM automl_experiments
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))

        experiments = []
        for row in cursor.fetchall():
            cv_scores_data = json.loads(row[5]) if row[5] else {}
            experiments.append({
                "experiment_id": str(row[0]),
                "timestamp": row[1],
                "best_model": row[2],
                "best_score": row[3] or 0.0,
                "cv_mean": row[3] or 0.0,
                "cv_std": row[4] or 0.0,
                "model_scores": cv_scores_data,
                "training_duration": None  # 既存スキーマにはない
            })

        conn.close()
        return experiments

    def _analyze_model_agreement(self, hours: int) -> Dict[str, Any]:
        """モデル合意度分析"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()

        cursor.execute("""
            SELECT model_agreement
            FROM advanced_prediction_history
            WHERE timestamp >= ?
        """, (cutoff_time,))

        agreements = [row[0] for row in cursor.fetchall()]
        conn.close()

        if not agreements:
            return {
                "count": 0,
                "statistics": {},
                "distribution": {}
            }

        # 合意度の分布
        distribution = {
            "excellent": sum(1 for a in agreements if a >= 0.95),  # 95%以上
            "good": sum(1 for a in agreements if 0.85 <= a < 0.95),  # 85-95%
            "fair": sum(1 for a in agreements if 0.75 <= a < 0.85),  # 75-85%
            "poor": sum(1 for a in agreements if a < 0.75)  # 75%未満
        }

        return {
            "count": len(agreements),
            "statistics": {
                "mean": round(statistics.mean(agreements), 4),
                "median": round(statistics.median(agreements), 4),
                "min": round(min(agreements), 4),
                "max": round(max(agreements), 4),
                "std_dev": round(statistics.stdev(agreements), 4) if len(agreements) > 1 else 0.0
            },
            "distribution": distribution
        }

    def _analyze_risk_distribution(self, hours: int) -> Dict[str, Any]:
        """リスクレベル分布分析"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()

        cursor.execute("""
            SELECT risk_level, COUNT(*) as count,
                   AVG(failure_probability) as avg_prob,
                   AVG(model_agreement) as avg_agreement
            FROM advanced_prediction_history
            WHERE timestamp >= ?
            GROUP BY risk_level
        """, (cutoff_time,))

        distribution = {}
        for row in cursor.fetchall():
            distribution[row[0]] = {
                "count": row[1],
                "avg_failure_probability": round(row[2], 4),
                "avg_model_agreement": round(row[3], 4)
            }

        conn.close()
        return distribution

    def _analyze_contributing_factors(self, hours: int) -> Dict[str, Any]:
        """寄与因子分析"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()

        cursor.execute("""
            SELECT contributing_factors
            FROM advanced_prediction_history
            WHERE timestamp >= ?
        """, (cutoff_time,))

        all_factors = []
        factor_importance = {}

        for row in cursor.fetchall():
            factors = json.loads(row[0])
            for factor in factors:
                factor_name = factor["feature"]
                importance = factor["importance"]

                if factor_name not in factor_importance:
                    factor_importance[factor_name] = []
                factor_importance[factor_name].append(importance)

        conn.close()

        # 各因子の平均重要度を計算
        avg_importance = {}
        for factor, importances in factor_importance.items():
            avg_importance[factor] = round(statistics.mean(importances), 4)

        # 重要度順にソート
        sorted_factors = sorted(
            avg_importance.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return {
            "total_unique_factors": len(sorted_factors),
            "top_factors": [
                {"feature": name, "avg_importance": importance}
                for name, importance in sorted_factors[:10]
            ],
            "all_factors": dict(sorted_factors)
        }

    def _generate_alerts(
        self,
        metrics: DashboardMetrics,
        trends: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """アラート生成"""
        alerts = []

        # 高リスク予測の割合が高い場合
        total = metrics.total_predictions
        if total > 0:
            high_risk_ratio = metrics.high_risk_count / total
            if high_risk_ratio > 0.3:  # 30%以上
                alerts.append({
                    "level": "critical",
                    "category": "risk_distribution",
                    "message": f"高リスク予測の割合が高い: {high_risk_ratio*100:.1f}% ({metrics.high_risk_count}/{total})",
                    "timestamp": datetime.now().isoformat()
                })

        # 平均モデル合意度が低い場合
        if metrics.avg_model_agreement < 0.75:
            alerts.append({
                "level": "high",
                "category": "model_agreement",
                "message": f"モデル合意度が低い: {metrics.avg_model_agreement*100:.1f}%",
                "timestamp": datetime.now().isoformat()
            })

        # 最新予測が高リスクの場合
        if metrics.latest_prediction and metrics.latest_prediction.risk_level == "HIGH":
            alerts.append({
                "level": "high",
                "category": "latest_prediction",
                "message": f"最新予測が高リスク: 障害確率 {metrics.latest_prediction.failure_probability*100:.1f}%",
                "timestamp": datetime.now().isoformat()
            })

        # 予測データポイントが少ない場合
        data_points = trends.get("data_points", 0)
        if data_points < 5:
            alerts.append({
                "level": "info",
                "category": "data_availability",
                "message": f"予測データポイントが少ない: {data_points}件",
                "timestamp": datetime.now().isoformat()
            })

        return alerts

    def _generate_plotly_graphs(self, dashboard: Dict[str, Any]) -> Dict[str, str]:
        """Plotlyグラフ生成"""
        if not PLOTLY_AVAILABLE:
            return {}

        plots = {}

        # グラフ1: 予測トレンド（障害確率＋モデル合意度）
        prediction_trends = dashboard["sections"]["prediction_trends"]
        if prediction_trends["data_points"] > 0:
            fig1 = self._create_prediction_trend_plot(prediction_trends)
            plot1_path = self.reports_dir / "prediction_trends.html"
            fig1.write_html(str(plot1_path))
            plots["prediction_trends"] = str(plot1_path)

        # グラフ2: リスクレベル分布
        risk_dist = dashboard["sections"]["risk_distribution"]
        if risk_dist:
            fig2 = self._create_risk_distribution_plot(risk_dist)
            plot2_path = self.reports_dir / "risk_distribution.html"
            fig2.write_html(str(plot2_path))
            plots["risk_distribution"] = str(plot2_path)

        # グラフ3: モデル合意度分布
        agreement = dashboard["sections"]["model_agreement"]
        if agreement["count"] > 0:
            fig3 = self._create_agreement_distribution_plot(agreement)
            plot3_path = self.reports_dir / "agreement_distribution.html"
            fig3.write_html(str(plot3_path))
            plots["agreement_distribution"] = str(plot3_path)

        # グラフ4: 寄与因子（Top 10）
        factors = dashboard["sections"]["contributing_factors"]
        if factors["total_unique_factors"] > 0:
            fig4 = self._create_contributing_factors_plot(factors)
            plot4_path = self.reports_dir / "contributing_factors.html"
            fig4.write_html(str(plot4_path))
            plots["contributing_factors"] = str(plot4_path)

        # グラフ5: AutoML実験履歴
        automl = dashboard["sections"]["automl_history"]
        if automl:
            fig5 = self._create_automl_history_plot(automl)
            plot5_path = self.reports_dir / "automl_history.html"
            fig5.write_html(str(plot5_path))
            plots["automl_history"] = str(plot5_path)

        return plots

    def _create_prediction_trend_plot(self, trends: Dict[str, Any]) -> Any:
        """予測トレンドグラフ作成"""
        time_series = trends["time_series"]

        timestamps = [point["timestamp"] for point in time_series]
        failure_probs = [point["failure_probability"] * 100 for point in time_series]
        agreements = [point["model_agreement"] * 100 for point in time_series]

        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=("障害確率の推移", "モデル合意度の推移"),
            vertical_spacing=0.15
        )

        # 障害確率
        fig.add_trace(
            go.Scatter(
                x=timestamps,
                y=failure_probs,
                mode='lines+markers',
                name='障害確率',
                line=dict(color='#e74c3c', width=2),
                marker=dict(size=6)
            ),
            row=1, col=1
        )

        # モデル合意度
        fig.add_trace(
            go.Scatter(
                x=timestamps,
                y=agreements,
                mode='lines+markers',
                name='モデル合意度',
                line=dict(color='#3498db', width=2),
                marker=dict(size=6)
            ),
            row=2, col=1
        )

        fig.update_xaxes(title_text="時刻", row=2, col=1)
        fig.update_yaxes(title_text="障害確率 (%)", row=1, col=1)
        fig.update_yaxes(title_text="モデル合意度 (%)", row=2, col=1)

        fig.update_layout(
            title_text="予測トレンド分析",
            height=600,
            showlegend=True
        )

        return fig

    def _create_risk_distribution_plot(self, risk_dist: Dict[str, Any]) -> Any:
        """リスクレベル分布グラフ作成"""
        labels = list(risk_dist.keys())
        values = [risk_dist[label]["count"] for label in labels]

        colors = {
            "HIGH": "#e74c3c",
            "MEDIUM": "#f39c12",
            "LOW": "#27ae60"
        }
        color_list = [colors.get(label, "#95a5a6") for label in labels]

        fig = go.Figure(data=[
            go.Pie(
                labels=labels,
                values=values,
                marker=dict(colors=color_list),
                textinfo='label+percent',
                hovertemplate='<b>%{label}</b><br>件数: %{value}<br>割合: %{percent}<extra></extra>'
            )
        ])

        fig.update_layout(
            title_text="リスクレベル分布",
            height=400
        )

        return fig

    def _create_agreement_distribution_plot(self, agreement: Dict[str, Any]) -> Any:
        """モデル合意度分布グラフ作成"""
        dist = agreement["distribution"]
        labels = ["優秀 (≥95%)", "良好 (85-95%)", "普通 (75-85%)", "要改善 (<75%)"]
        values = [dist["excellent"], dist["good"], dist["fair"], dist["poor"]]

        fig = go.Figure(data=[
            go.Bar(
                x=labels,
                y=values,
                marker=dict(color=['#27ae60', '#3498db', '#f39c12', '#e74c3c']),
                text=values,
                textposition='auto'
            )
        ])

        fig.update_layout(
            title_text="モデル合意度分布",
            xaxis_title="合意度レベル",
            yaxis_title="予測回数",
            height=400
        )

        return fig

    def _create_contributing_factors_plot(self, factors: Dict[str, Any]) -> Any:
        """寄与因子グラフ作成"""
        top_factors = factors["top_factors"]
        features = [f["feature"] for f in top_factors]
        importances = [f["avg_importance"] * 100 for f in top_factors]

        fig = go.Figure(data=[
            go.Bar(
                x=importances,
                y=features,
                orientation='h',
                marker=dict(color='#3498db'),
                text=[f"{imp:.2f}%" for imp in importances],
                textposition='auto'
            )
        ])

        fig.update_layout(
            title_text="寄与因子分析（Top 10）",
            xaxis_title="平均重要度 (%)",
            yaxis_title="特徴量",
            height=500
        )

        return fig

    def _create_automl_history_plot(self, automl: List[Dict[str, Any]]) -> Any:
        """AutoML実験履歴グラフ作成"""
        experiment_ids = [exp["experiment_id"][-8:] for exp in automl]  # 短縮ID
        cv_scores = [exp["cv_mean"] for exp in automl]
        cv_stds = [exp["cv_std"] for exp in automl]

        fig = go.Figure(data=[
            go.Bar(
                x=experiment_ids,
                y=cv_scores,
                error_y=dict(type='data', array=cv_stds),
                marker=dict(color='#9b59b6'),
                text=[f"{score:.4f}" for score in cv_scores],
                textposition='auto'
            )
        ])

        fig.update_layout(
            title_text="AutoML実験履歴（CVスコア）",
            xaxis_title="実験ID",
            yaxis_title="CVスコア（F1-weighted）",
            height=400
        )

        return fig

    # プリント関数群
    def _print_summary_metrics(self, metrics: DashboardMetrics):
        """サマリーメトリクス表示"""
        print(f"  総予測数: {metrics.total_predictions}件")
        print(f"  平均障害確率: {metrics.avg_failure_probability*100:.2f}%")
        print(f"  平均モデル合意度: {metrics.avg_model_agreement*100:.2f}%")
        print()
        print(f"  【リスクレベル分布】")
        print(f"    - HIGH: {metrics.high_risk_count}件")
        print(f"    - MEDIUM: {metrics.medium_risk_count}件")
        print(f"    - LOW: {metrics.low_risk_count}件")

        if metrics.latest_prediction:
            print()
            print(f"  【最新予測】")
            print(f"    - 時刻: {metrics.latest_prediction.timestamp}")
            print(f"    - 障害確率: {metrics.latest_prediction.failure_probability*100:.2f}%")
            print(f"    - リスクレベル: {metrics.latest_prediction.risk_level}")
            print(f"    - モデル合意度: {metrics.latest_prediction.model_agreement*100:.2f}%")

    def _print_prediction_trends(self, trends: Dict[str, Any]):
        """予測トレンド表示"""
        print(f"  データポイント数: {trends['data_points']}件")

        if trends["data_points"] > 0:
            stats = trends["statistics"]
            print()
            print(f"  【障害確率統計】")
            print(f"    - 平均: {stats['failure_probability']['mean']*100:.2f}%")
            print(f"    - 中央値: {stats['failure_probability']['median']*100:.2f}%")
            print(f"    - 最小/最大: {stats['failure_probability']['min']*100:.2f}% / {stats['failure_probability']['max']*100:.2f}%")
            print(f"    - 標準偏差: {stats['failure_probability']['std_dev']*100:.2f}%")
            print()
            print(f"  【モデル合意度統計】")
            print(f"    - 平均: {stats['model_agreement']['mean']*100:.2f}%")
            print(f"    - 中央値: {stats['model_agreement']['median']*100:.2f}%")
            print(f"    - 最小/最大: {stats['model_agreement']['min']*100:.2f}% / {stats['model_agreement']['max']*100:.2f}%")

    def _print_automl_history(self, experiments: List[Dict[str, Any]]):
        """AutoML実験履歴表示"""
        print(f"  実験数: {len(experiments)}件")

        if experiments:
            print()
            print(f"  【最新5実験】")
            for i, exp in enumerate(experiments[:5], 1):
                print(f"  {i}. [{exp['timestamp']}] {exp['best_model']}")
                print(f"     CVスコア: {exp['cv_mean']:.4f} ± {exp['cv_std']:.4f}")
                if exp.get('training_duration'):
                    print(f"     訓練時間: {exp['training_duration']:.2f}秒")

    def _print_agreement_analysis(self, analysis: Dict[str, Any]):
        """モデル合意度分析表示"""
        if analysis["count"] == 0:
            print("  データなし")
            return

        stats = analysis["statistics"]
        dist = analysis["distribution"]

        print(f"  予測数: {analysis['count']}件")
        print()
        print(f"  【統計】")
        print(f"    - 平均: {stats['mean']*100:.2f}%")
        print(f"    - 中央値: {stats['median']*100:.2f}%")
        print(f"    - 最小/最大: {stats['min']*100:.2f}% / {stats['max']*100:.2f}%")
        print()
        print(f"  【分布】")
        print(f"    - 優秀 (≥95%): {dist['excellent']}件")
        print(f"    - 良好 (85-95%): {dist['good']}件")
        print(f"    - 普通 (75-85%): {dist['fair']}件")
        print(f"    - 要改善 (<75%): {dist['poor']}件")

    def _print_risk_distribution(self, distribution: Dict[str, Any]):
        """リスクレベル分布表示"""
        if not distribution:
            print("  データなし")
            return

        for level, data in distribution.items():
            print(f"  【{level}】")
            print(f"    - 件数: {data['count']}")
            print(f"    - 平均障害確率: {data['avg_failure_probability']*100:.2f}%")
            print(f"    - 平均モデル合意度: {data['avg_model_agreement']*100:.2f}%")
            print()

    def _print_factor_analysis(self, analysis: Dict[str, Any]):
        """寄与因子分析表示"""
        print(f"  ユニーク因子数: {analysis['total_unique_factors']}")

        if analysis['top_factors']:
            print()
            print(f"  【Top 10 寄与因子】")
            for i, factor in enumerate(analysis['top_factors'][:10], 1):
                print(f"  {i}. {factor['feature']}: {factor['avg_importance']*100:.2f}%")

    def _print_alerts(self, alerts: List[Dict[str, Any]]):
        """アラート表示"""
        print(f"  アラート数: {len(alerts)}件")

        if alerts:
            print()
            level_symbols = {
                "critical": "🔴",
                "high": "🟡",
                "info": "🔵"
            }
            for i, alert in enumerate(alerts, 1):
                symbol = level_symbols.get(alert["level"], "⚪")
                print(f"  {i}. {symbol} [{alert['level'].upper()}] {alert['message']}")
                print(f"     カテゴリ: {alert['category']}")

    def save_dashboard(
        self,
        dashboard: Dict[str, Any],
        filename: Optional[str] = None
    ) -> Path:
        """ダッシュボードをJSON形式で保存"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"advanced_trend_dashboard_{timestamp}.json"

        output_path = self.reports_dir / filename

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(dashboard, f, indent=2, ensure_ascii=False)

        print(f"\n✅ ダッシュボード保存: {output_path}")
        return output_path


def main():
    """メイン関数"""
    import argparse

    parser = argparse.ArgumentParser(description="Phase 11.2 高度トレンド分析ダッシュボード")
    parser.add_argument("--generate", action="store_true", help="ダッシュボード生成")
    parser.add_argument("--hours", type=int, default=24, help="分析時間範囲（時間）")
    parser.add_argument("--save", action="store_true", help="JSON形式で保存")
    parser.add_argument("--plots", action="store_true", help="Plotlyグラフ生成")

    args = parser.parse_args()

    dashboard_system = AdvancedTrendDashboard()

    if args.generate:
        dashboard = dashboard_system.generate_comprehensive_dashboard(
            hours=args.hours,
            include_plots=args.plots
        )

        if args.save:
            dashboard_system.save_dashboard(dashboard)

        if args.plots and PLOTLY_AVAILABLE:
            print()
            print("📊 インタラクティブグラフ:")
            for plot_name, plot_path in dashboard["sections"]["plots"].items():
                print(f"  - {plot_name}: {plot_path}")
    else:
        print("オプションを指定してください。--help で使用方法を確認できます。")
        print()
        print("使用例:")
        print("  python src/advanced_trend_dashboard.py --generate --hours 24 --save --plots")


if __name__ == "__main__":
    main()
