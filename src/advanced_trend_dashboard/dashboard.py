#!/usr/bin/env python3
"""高度トレンドダッシュボード - メインクラス"""

import json
import statistics
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.database_utils import get_connection

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

PROJECT_ROOT = Path(__file__).parent.parent.parent


class AdvancedTrendDashboard:
    """高度トレンド分析ダッシュボード"""

    def __init__(self, db_path: Path = PROJECT_ROOT / "unified_quality.db"):
        self.db_path = db_path
        self.reports_dir = PROJECT_ROOT / "reports" / "advanced_trends"
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self._init_database_tables()

    def _init_database_tables(self):
        """データベーステーブル初期化"""
        conn = get_connection(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS advanced_prediction_history (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
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

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS automl_experiments (
                experiment_id INTEGER PRIMARY KEY AUTO_INCREMENT,
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

    def generate_comprehensive_dashboard(self, hours: int = 24, include_plots: bool = True) -> Dict[str, Any]:
        """包括的ダッシュボード生成"""
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
                "plotly_enabled": PLOTLY_AVAILABLE and include_plots,
            },
            "sections": {},
        }

        # セクション1-7: データ取得と表示
        self._build_all_sections(dashboard, hours)

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

    def _build_all_sections(self, dashboard: Dict[str, Any], hours: int) -> None:
        """全セクションを構築"""
        # セクション1: サマリーメトリクス
        print("📌 セクション1: サマリーメトリクス")
        print("-" * 80)
        metrics = self._get_summary_metrics(hours)
        dashboard["sections"]["summary"] = metrics
        print_summary_metrics(metrics)
        print()

        # セクション2: 予測トレンド分析
        print("📌 セクション2: 予測トレンド分析")
        print("-" * 80)
        prediction_trends = self._analyze_prediction_trends(hours)
        dashboard["sections"]["prediction_trends"] = prediction_trends
        print_prediction_trends(prediction_trends)
        print()

        # セクション3: AutoML実験履歴
        print("📌 セクション3: AutoML実験履歴")
        print("-" * 80)
        automl_history = self._get_automl_history(limit=10)
        dashboard["sections"]["automl_history"] = automl_history
        print_automl_history(automl_history)
        print()

        # セクション4: モデル合意度分析
        print("📌 セクション4: モデル合意度分析")
        print("-" * 80)
        agreement_analysis = self._analyze_model_agreement(hours)
        dashboard["sections"]["model_agreement"] = agreement_analysis
        print_agreement_analysis(agreement_analysis)
        print()

        # セクション5: リスクレベル分布
        print("📌 セクション5: リスクレベル分布")
        print("-" * 80)
        risk_distribution = self._analyze_risk_distribution(hours)
        dashboard["sections"]["risk_distribution"] = risk_distribution
        print_risk_distribution(risk_distribution)
        print()

        # セクション6: 寄与因子分析
        print("📌 セクション6: 寄与因子分析")
        print("-" * 80)
        factor_analysis = self._analyze_contributing_factors(hours)
        dashboard["sections"]["contributing_factors"] = factor_analysis
        print_factor_analysis(factor_analysis)
        print()

        # セクション7: アラート一覧
        print("📌 セクション7: アラート一覧")
        print("-" * 80)
        alerts = self._generate_alerts(metrics, prediction_trends)
        dashboard["sections"]["alerts"] = alerts
        print_alerts(alerts)
        print()

    def _get_summary_metrics(self, hours: int) -> DashboardMetrics:
        """サマリーメトリクス取得"""
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()

        cursor.execute(
            "SELECT COUNT(*) FROM advanced_prediction_history WHERE timestamp >= ?",
            (cutoff_time,),
        )
        total_predictions = cursor.fetchone()[0]

        cursor.execute(
            "SELECT AVG(failure_probability) FROM advanced_prediction_history WHERE timestamp >= ?",
            (cutoff_time,),
        )
        avg_failure_prob = cursor.fetchone()[0] or 0.0

        cursor.execute(
            "SELECT AVG(model_agreement) FROM advanced_prediction_history WHERE timestamp >= ?",
            (cutoff_time,),
        )
        avg_agreement = cursor.fetchone()[0] or 0.0

        cursor.execute(
            """SELECT risk_level, COUNT(*) FROM advanced_prediction_history
            WHERE timestamp >= ? GROUP BY risk_level""",
            (cutoff_time,),
        )
        risk_counts = dict(cursor.fetchall())

        latest_prediction = self._get_latest_prediction(cursor)
        latest_experiment = self._get_latest_experiment(cursor)

        conn.close()

        return DashboardMetrics(
            total_predictions=total_predictions,
            avg_failure_probability=avg_failure_prob,
            avg_model_agreement=avg_agreement,
            high_risk_count=risk_counts.get("HIGH", 0),
            medium_risk_count=risk_counts.get("MEDIUM", 0),
            low_risk_count=risk_counts.get("LOW", 0),
            latest_prediction=latest_prediction,
            latest_experiment=latest_experiment,
        )

    def _get_latest_prediction(self, cursor) -> Optional[PredictionTrend]:
        """最新予測を取得"""
        cursor.execute("""
            SELECT prediction_id, timestamp, failure_probability, risk_level,
                   model_agreement, ensemble_predictions
            FROM advanced_prediction_history ORDER BY timestamp DESC LIMIT 1
        """)
        row = cursor.fetchone()
        if not row:
            return None
        return PredictionTrend(
            timestamp=row[1],
            failure_probability=row[2],
            risk_level=row[3],
            model_agreement=row[4],
            ensemble_predictions=json.loads(row[5]),
        )

    def _get_latest_experiment(self, cursor) -> Optional[AutoMLExperiment]:
        """最新AutoML実験を取得"""
        cursor.execute("""
            SELECT experiment_id, timestamp, best_model_name,
                   mean_cv_score, std_cv_score, cv_scores
            FROM automl_experiments ORDER BY timestamp DESC LIMIT 1
        """)
        row = cursor.fetchone()
        if not row:
            return None
        cv_scores_data = json.loads(row[5]) if row[5] else {}
        return AutoMLExperiment(
            experiment_id=str(row[0]),
            timestamp=row[1],
            best_model=row[2],
            best_score=row[3] or 0.0,
            cv_mean=row[3] or 0.0,
            cv_std=row[4] or 0.0,
            model_scores=cv_scores_data,
        )

    def _analyze_prediction_trends(self, hours: int) -> Dict[str, Any]:
        """予測トレンド分析"""
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()

        cursor.execute(
            """SELECT timestamp, failure_probability, model_agreement, risk_level
            FROM advanced_prediction_history WHERE timestamp >= ? ORDER BY timestamp ASC""",
            (cutoff_time,),
        )
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return {"data_points": 0, "time_series": [], "statistics": {}}

        time_series = []
        failure_probs = []
        agreements = []

        for row in rows:
            time_series.append(
                {
                    "timestamp": row[0],
                    "failure_probability": row[1],
                    "model_agreement": row[2],
                    "risk_level": row[3],
                }
            )
            failure_probs.append(row[1])
            agreements.append(row[2])

        return {
            "data_points": len(time_series),
            "time_series": time_series,
            "statistics": self._compute_statistics(failure_probs, agreements),
        }

    def _compute_statistics(self, failure_probs: List[float], agreements: List[float]) -> Dict[str, Any]:
        """統計情報を計算"""
        return {
            "failure_probability": {
                "mean": round(statistics.mean(failure_probs), 4),
                "median": round(statistics.median(failure_probs), 4),
                "min": round(min(failure_probs), 4),
                "max": round(max(failure_probs), 4),
                "std_dev": round(statistics.stdev(failure_probs), 4) if len(failure_probs) > 1 else 0.0,
            },
            "model_agreement": {
                "mean": round(statistics.mean(agreements), 4),
                "median": round(statistics.median(agreements), 4),
                "min": round(min(agreements), 4),
                "max": round(max(agreements), 4),
                "std_dev": round(statistics.stdev(agreements), 4) if len(agreements) > 1 else 0.0,
            },
        }

    def _get_automl_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """AutoML実験履歴取得"""
        conn = get_connection(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """SELECT experiment_id, timestamp, best_model_name,
                      mean_cv_score, std_cv_score, cv_scores
            FROM automl_experiments ORDER BY timestamp DESC LIMIT ?""",
            (limit,),
        )

        experiments = []
        for row in cursor.fetchall():
            cv_scores_data = json.loads(row[5]) if row[5] else {}
            experiments.append(
                {
                    "experiment_id": str(row[0]),
                    "timestamp": row[1],
                    "best_model": row[2],
                    "best_score": row[3] or 0.0,
                    "cv_mean": row[3] or 0.0,
                    "cv_std": row[4] or 0.0,
                    "model_scores": cv_scores_data,
                    "training_duration": None,
                }
            )

        conn.close()
        return experiments

    def _analyze_model_agreement(self, hours: int) -> Dict[str, Any]:
        """モデル合意度分析"""
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()

        cursor.execute(
            "SELECT model_agreement FROM advanced_prediction_history WHERE timestamp >= ?",
            (cutoff_time,),
        )
        agreements = [row[0] for row in cursor.fetchall()]
        conn.close()

        if not agreements:
            return {"count": 0, "statistics": {}, "distribution": {}}

        distribution = {
            "excellent": sum(1 for a in agreements if a >= 0.95),
            "good": sum(1 for a in agreements if 0.85 <= a < 0.95),
            "fair": sum(1 for a in agreements if 0.75 <= a < 0.85),
            "poor": sum(1 for a in agreements if a < 0.75),
        }

        return {
            "count": len(agreements),
            "statistics": {
                "mean": round(statistics.mean(agreements), 4),
                "median": round(statistics.median(agreements), 4),
                "min": round(min(agreements), 4),
                "max": round(max(agreements), 4),
                "std_dev": round(statistics.stdev(agreements), 4) if len(agreements) > 1 else 0.0,
            },
            "distribution": distribution,
        }

    def _analyze_risk_distribution(self, hours: int) -> Dict[str, Any]:
        """リスクレベル分布分析"""
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()

        cursor.execute(
            """SELECT risk_level, COUNT(*) as count,
                      AVG(failure_probability) as avg_prob,
                      AVG(model_agreement) as avg_agreement
            FROM advanced_prediction_history WHERE timestamp >= ? GROUP BY risk_level""",
            (cutoff_time,),
        )

        distribution = {}
        for row in cursor.fetchall():
            distribution[row[0]] = {
                "count": row[1],
                "avg_failure_probability": round(row[2], 4),
                "avg_model_agreement": round(row[3], 4),
            }

        conn.close()
        return distribution

    def _analyze_contributing_factors(self, hours: int) -> Dict[str, Any]:
        """寄与因子分析"""
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()

        cursor.execute(
            "SELECT contributing_factors FROM advanced_prediction_history WHERE timestamp >= ?",
            (cutoff_time,),
        )

        factor_importance: Dict[str, List[float]] = {}
        for row in cursor.fetchall():
            factors = json.loads(row[0])
            for factor in factors:
                name = factor["feature"]
                importance = factor["importance"]
                if name not in factor_importance:
                    factor_importance[name] = []
                factor_importance[name].append(importance)

        conn.close()

        avg_importance = {f: round(statistics.mean(imps), 4) for f, imps in factor_importance.items()}
        sorted_factors = sorted(avg_importance.items(), key=lambda x: x[1], reverse=True)

        return {
            "total_unique_factors": len(sorted_factors),
            "top_factors": [
                {"feature": name, "avg_importance": importance} for name, importance in sorted_factors[:10]
            ],
            "all_factors": dict(sorted_factors),
        }

    def _generate_alerts(self, metrics: DashboardMetrics, trends: Dict[str, Any]) -> List[Dict[str, Any]]:
        """アラート生成"""
        alerts = []
        total = metrics.total_predictions

        if total > 0:
            high_risk_ratio = metrics.high_risk_count / total
            if high_risk_ratio > 0.3:
                alerts.append(
                    {
                        "level": "critical",
                        "category": "risk_distribution",
                        "message": f"高リスク予測の割合が高い: {high_risk_ratio * 100:.1f}% ({metrics.high_risk_count}/{total})",
                        "timestamp": datetime.now().isoformat(),
                    }
                )

        if metrics.avg_model_agreement < 0.75:
            alerts.append(
                {
                    "level": "high",
                    "category": "model_agreement",
                    "message": f"モデル合意度が低い: {metrics.avg_model_agreement * 100:.1f}%",
                    "timestamp": datetime.now().isoformat(),
                }
            )

        if metrics.latest_prediction and metrics.latest_prediction.risk_level == "HIGH":
            alerts.append(
                {
                    "level": "high",
                    "category": "latest_prediction",
                    "message": f"最新予測が高リスク: 障害確率 {metrics.latest_prediction.failure_probability * 100:.1f}%",
                    "timestamp": datetime.now().isoformat(),
                }
            )

        data_points = trends.get("data_points", 0)
        if data_points < 5:
            alerts.append(
                {
                    "level": "info",
                    "category": "data_availability",
                    "message": f"予測データポイントが少ない: {data_points}件",
                    "timestamp": datetime.now().isoformat(),
                }
            )

        return alerts

    def _generate_plotly_graphs(self, dashboard: Dict[str, Any]) -> Dict[str, str]:
        """Plotlyグラフ生成"""
        if not PLOTLY_AVAILABLE:
            return {}

        plots = {}

        # グラフ1: 予測トレンド
        prediction_trends = dashboard["sections"]["prediction_trends"]
        if prediction_trends["data_points"] > 0:
            fig = create_prediction_trend_plot(prediction_trends)
            if fig:
                path = self.reports_dir / "prediction_trends.html"
                fig.write_html(str(path))
                plots["prediction_trends"] = str(path)

        # グラフ2: リスクレベル分布
        risk_dist = dashboard["sections"]["risk_distribution"]
        if risk_dist:
            fig = create_risk_distribution_plot(risk_dist)
            if fig:
                path = self.reports_dir / "risk_distribution.html"
                fig.write_html(str(path))
                plots["risk_distribution"] = str(path)

        # グラフ3: モデル合意度分布
        agreement = dashboard["sections"]["model_agreement"]
        if agreement["count"] > 0:
            fig = create_agreement_distribution_plot(agreement)
            if fig:
                path = self.reports_dir / "agreement_distribution.html"
                fig.write_html(str(path))
                plots["agreement_distribution"] = str(path)

        # グラフ4: 寄与因子
        factors = dashboard["sections"]["contributing_factors"]
        if factors["total_unique_factors"] > 0:
            fig = create_contributing_factors_plot(factors)
            if fig:
                path = self.reports_dir / "contributing_factors.html"
                fig.write_html(str(path))
                plots["contributing_factors"] = str(path)

        # グラフ5: AutoML履歴
        automl = dashboard["sections"]["automl_history"]
        if automl:
            fig = create_automl_history_plot(automl)
            if fig:
                path = self.reports_dir / "automl_history.html"
                fig.write_html(str(path))
                plots["automl_history"] = str(path)

        return plots

    def save_dashboard(self, dashboard: Dict[str, Any], filename: Optional[str] = None) -> Path:
        """ダッシュボードをJSON形式で保存"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"advanced_trend_dashboard_{timestamp}.json"

        output_path = self.reports_dir / filename

        with open(output_path, "w", encoding="utf-8") as f:
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
        dashboard = dashboard_system.generate_comprehensive_dashboard(hours=args.hours, include_plots=args.plots)

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
        print("  python -m src.advanced_trend_dashboard --generate --hours 24 --save --plots")


if __name__ == "__main__":
    main()
