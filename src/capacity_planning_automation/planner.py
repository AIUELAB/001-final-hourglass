#!/usr/bin/env python3
"""容量計画自動化 - メインプランナー"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.database_utils import get_connection

from .models import CapacityForecast, CapacityPlan, ScalingRecommendation

# プロジェクトルート設定
PROJECT_ROOT = Path(__file__).parent.parent.parent

try:
    import numpy as np
    from sklearn.linear_model import LinearRegression

    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


class CapacityPlanningAutomation:
    """容量計画自動化クラス"""

    def __init__(self, db_path: Path = PROJECT_ROOT / "unified_quality.db"):
        self.db_path = db_path
        self.reports_dir = PROJECT_ROOT / "reports" / "capacity_planning"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        # 容量閾値（パーセント）
        self.capacity_thresholds = {"cpu": 80.0, "memory": 85.0, "disk": 90.0}

        # 予測モデル
        self.models: Dict[str, Any] = {}
        self.scalers: Dict[str, Any] = {}

        # データベーステーブル初期化
        self._init_database_tables()

    def _init_database_tables(self):
        """データベーステーブル初期化"""
        conn = get_connection(self.db_path)
        cursor = conn.cursor()

        # capacity_forecasts テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS capacity_forecasts (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                timestamp TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                current_usage REAL NOT NULL,
                predicted_usage_7d REAL,
                predicted_usage_30d REAL,
                predicted_usage_90d REAL,
                growth_rate_daily REAL,
                days_until_threshold INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # capacity_recommendations テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS capacity_recommendations (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                timestamp TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                action TEXT NOT NULL,
                urgency TEXT NOT NULL,
                current_capacity REAL NOT NULL,
                recommended_capacity REAL NOT NULL,
                reason TEXT NOT NULL,
                estimated_days INTEGER,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # capacity_plans テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS capacity_plans (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                plan_id TEXT NOT NULL UNIQUE,
                generated_at TEXT NOT NULL,
                forecast_period_days INTEGER NOT NULL,
                forecasts TEXT NOT NULL,
                recommendations TEXT NOT NULL,
                alerts TEXT NOT NULL,
                summary TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def generate_capacity_plan(self, forecast_days: int = 90, history_days: int = 30) -> CapacityPlan:
        """
        容量計画を生成

        Args:
            forecast_days: 予測期間（日数）
            history_days: 履歴データ期間（日数）

        Returns:
            容量計画
        """
        print("=" * 80)
        print("📊 Phase 11.3 - 容量計画自動化システム")
        print("=" * 80)
        print(f"予測期間: {forecast_days}日間")
        print(f"履歴データ: 過去{history_days}日間")
        print(f"生成時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        print()

        # ステップ1: リソース使用量データの収集
        print("📌 ステップ1: リソース使用量データの収集")
        print("-" * 80)
        resource_data = self._collect_resource_data(history_days)
        print(f"✅ CPU データポイント: {len(resource_data['cpu'])}件")
        print(f"✅ メモリ データポイント: {len(resource_data['memory'])}件")
        print(f"✅ ディスク データポイント: {len(resource_data['disk'])}件")
        print()

        # ステップ2: 容量予測
        print("📌 ステップ2: 容量予測の生成")
        print("-" * 80)
        forecasts = []
        for resource_type in ["cpu", "memory", "disk"]:
            forecast = self._generate_forecast(resource_type, resource_data[resource_type], forecast_days)
            forecasts.append(forecast)
            self._print_forecast(forecast)
        print()

        # ステップ3: スケーリング推奨事項の生成
        print("📌 ステップ3: スケーリング推奨事項の生成")
        print("-" * 80)
        recommendations = self._generate_recommendations(forecasts)
        for rec in recommendations:
            self._print_recommendation(rec)
        print()

        # ステップ4: アラートの生成
        print("📌 ステップ4: アラートの生成")
        print("-" * 80)
        alerts = self._generate_alerts(forecasts, recommendations)
        print(f"✅ 生成されたアラート: {len(alerts)}件")
        for alert in alerts:
            self._print_alert(alert)
        print()

        # ステップ5: サマリー作成
        summary = self._generate_summary(forecasts, recommendations, alerts)

        # 容量計画オブジェクト作成
        capacity_plan = CapacityPlan(
            generated_at=datetime.now().isoformat(),
            forecast_period_days=forecast_days,
            forecasts=forecasts,
            recommendations=recommendations,
            alerts=alerts,
            summary=summary,
        )

        # データベースに保存
        self._save_capacity_plan(capacity_plan)

        print("=" * 80)
        print("✅ 容量計画生成完了")
        print("=" * 80)

        return capacity_plan

    def _collect_resource_data(self, days: int) -> Dict[str, List[Tuple[str, float]]]:
        """リソース使用量データ収集"""
        conn = get_connection(self.db_path)
        cursor = conn.cursor()

        cutoff_time = (datetime.now() - timedelta(days=days)).isoformat()

        # system_metricsテーブルからデータ取得
        cursor.execute(
            """
            SELECT timestamp, cpu_percent, memory_percent, disk_percent
            FROM system_metrics
            WHERE timestamp >= ?
            ORDER BY timestamp ASC
        """,
            (cutoff_time,),
        )

        rows = cursor.fetchall()
        conn.close()

        # リソースタイプ別に整理
        resource_data: Dict[str, List[Tuple[str, float]]] = {"cpu": [], "memory": [], "disk": []}

        for row in rows:
            timestamp = row[0]
            resource_data["cpu"].append((timestamp, row[1]))
            resource_data["memory"].append((timestamp, row[2]))
            resource_data["disk"].append((timestamp, row[3]))

        return resource_data

    def _generate_forecast(
        self, resource_type: str, data: List[Tuple[str, float]], forecast_days: int
    ) -> CapacityForecast:
        """容量予測を生成"""

        if len(data) < 2:
            # データ不足の場合は現在値を返す
            current_usage = data[0][1] if data else 0.0
            return CapacityForecast(
                resource_type=resource_type,
                current_usage=current_usage,
                predicted_usage_7d=current_usage,
                predicted_usage_30d=current_usage,
                predicted_usage_90d=current_usage,
                capacity_threshold=self.capacity_thresholds[resource_type],
                days_until_threshold=None,
                growth_rate_daily=0.0,
            )

        # 現在の使用率
        current_usage = data[-1][1]

        # 成長率計算
        values = [val for _, val in data]
        growth_rate = self._calculate_growth_rate(values)

        # 予測
        if SKLEARN_AVAILABLE and len(data) >= 10:
            # 機械学習ベースの予測
            pred_7d, pred_30d, pred_90d = self._ml_forecast(data, forecast_days)
        else:
            # 線形成長率ベースの予測
            pred_7d = current_usage + (growth_rate * 7)
            pred_30d = current_usage + (growth_rate * 30)
            pred_90d = current_usage + (growth_rate * 90)

        # 閾値到達までの日数計算
        threshold = self.capacity_thresholds[resource_type]
        days_until_threshold = self._calculate_days_until_threshold(current_usage, growth_rate, threshold)

        return CapacityForecast(
            resource_type=resource_type,
            current_usage=round(current_usage, 2),
            predicted_usage_7d=round(max(0, min(100, pred_7d)), 2),
            predicted_usage_30d=round(max(0, min(100, pred_30d)), 2),
            predicted_usage_90d=round(max(0, min(100, pred_90d)), 2),
            capacity_threshold=threshold,
            days_until_threshold=days_until_threshold,
            growth_rate_daily=round(growth_rate, 4),
        )

    def _calculate_growth_rate(self, values: List[float]) -> float:
        """成長率計算（日次）"""
        if len(values) < 2:
            return 0.0

        # 最初と最後の値から平均的な成長率を計算
        first_val = values[0]
        last_val = values[-1]
        days = len(values)

        if days <= 1:
            return 0.0

        growth_rate = (last_val - first_val) / days
        return growth_rate

    def _ml_forecast(self, data: List[Tuple[str, float]], forecast_days: int) -> Tuple[float, float, float]:
        """機械学習ベースの予測"""
        # データを時間インデックスと値に分割
        timestamps = [datetime.fromisoformat(ts) for ts, _ in data]
        values = np.array([val for _, val in data]).reshape(-1, 1)

        # 時間インデックス（エポック秒からの経過日数）
        start_time = timestamps[0]
        X = np.array([(ts - start_time).total_seconds() / 86400 for ts in timestamps]).reshape(-1, 1)

        # 線形回帰モデル
        model = LinearRegression()
        model.fit(X, values)

        # 予測
        current_day = X[-1][0]
        pred_7d = model.predict([[current_day + 7]])[0][0]
        pred_30d = model.predict([[current_day + 30]])[0][0]
        pred_90d = model.predict([[current_day + 90]])[0][0]

        return pred_7d, pred_30d, pred_90d

    def _calculate_days_until_threshold(
        self, current_usage: float, growth_rate: float, threshold: float
    ) -> Optional[int]:
        """閾値到達までの日数計算"""
        if growth_rate <= 0:
            return None

        if current_usage >= threshold:
            return 0

        days = (threshold - current_usage) / growth_rate
        return int(days) if days > 0 else None

    def _generate_recommendations(self, forecasts: List[CapacityForecast]) -> List[ScalingRecommendation]:
        """スケーリング推奨事項の生成"""
        recommendations = []

        for forecast in forecasts:
            rec = self._analyze_forecast_and_recommend(forecast)
            if rec:
                recommendations.append(rec)

        return recommendations

    def _analyze_forecast_and_recommend(self, forecast: CapacityForecast) -> Optional[ScalingRecommendation]:
        """予測を分析して推奨事項を生成"""

        resource_type = forecast.resource_type
        current = forecast.current_usage
        pred_30d = forecast.predicted_usage_30d
        threshold = forecast.capacity_threshold
        days_until = forecast.days_until_threshold

        # アクション判定
        action = "no_action"
        urgency = "low"
        recommended_capacity = current
        reason = "現在の容量で十分です"

        # 30日後の予測が閾値を超える場合
        if pred_30d >= threshold:
            action = "scale_up"
            recommended_capacity = pred_30d * 1.2  # 20%のバッファ

            if days_until is not None:
                if days_until <= 7:
                    urgency = "critical"
                    reason = f"予測では{days_until}日後に容量閾値（{threshold}%）に到達します。緊急のスケールアップが必要です。"
                elif days_until <= 14:
                    urgency = "high"
                    reason = f"予測では{days_until}日後に容量閾値（{threshold}%）に到達します。早期のスケールアップを推奨します。"
                elif days_until <= 30:
                    urgency = "medium"
                    reason = f"予測では{days_until}日後に容量閾値（{threshold}%）に到達します。スケールアップの計画を開始してください。"
            else:
                urgency = "medium"
                reason = f"30日後の予測使用率が{pred_30d:.1f}%で閾値（{threshold}%）を超えます。"

        # 現在の使用率が非常に低く、成長率も低い場合
        elif current < 30.0 and forecast.growth_rate_daily < 0.1:
            action = "scale_down"
            urgency = "low"
            recommended_capacity = max(50.0, current * 1.5)  # 最低50%は確保
            reason = f"現在の使用率が{current:.1f}%と低く、成長率も低いため、リソースの最適化が可能です。"

        # アクションがある場合のみ推奨事項を返す
        if action != "no_action":
            return ScalingRecommendation(
                resource_type=resource_type,
                action=action,
                urgency=urgency,
                current_capacity=round(current, 2),
                recommended_capacity=round(recommended_capacity, 2),
                reason=reason,
                estimated_days_until_needed=days_until,
            )

        return None

    def _generate_alerts(
        self, forecasts: List[CapacityForecast], recommendations: List[ScalingRecommendation]
    ) -> List[Dict[str, Any]]:
        """アラートの生成"""
        alerts = []

        # 容量不足アラート
        for forecast in forecasts:
            if forecast.days_until_threshold is not None and forecast.days_until_threshold <= 30:
                level = "critical" if forecast.days_until_threshold <= 7 else "high"
                alerts.append(
                    {
                        "level": level,
                        "category": "capacity_shortage",
                        "resource": forecast.resource_type,
                        "message": f"{forecast.resource_type.upper()}容量が{forecast.days_until_threshold}日後に閾値到達の予測",
                        "current_usage": forecast.current_usage,
                        "threshold": forecast.capacity_threshold,
                        "timestamp": datetime.now().isoformat(),
                    }
                )

        # 緊急推奨事項アラート
        for rec in recommendations:
            if rec.urgency in ["critical", "high"]:
                alerts.append(
                    {
                        "level": rec.urgency,
                        "category": "scaling_recommendation",
                        "resource": rec.resource_type,
                        "message": f"{rec.resource_type.upper()}: {rec.action} - {rec.reason}",
                        "action": rec.action,
                        "timestamp": datetime.now().isoformat(),
                    }
                )

        # 高成長率アラート
        for forecast in forecasts:
            if forecast.growth_rate_daily > 1.0:  # 1日あたり1%以上の成長
                alerts.append(
                    {
                        "level": "info",
                        "category": "high_growth_rate",
                        "resource": forecast.resource_type,
                        "message": f"{forecast.resource_type.upper()}の使用率が高い成長率（日次{forecast.growth_rate_daily:.2f}%）を示しています",
                        "growth_rate": forecast.growth_rate_daily,
                        "timestamp": datetime.now().isoformat(),
                    }
                )

        return alerts

    def _generate_summary(
        self,
        forecasts: List[CapacityForecast],
        recommendations: List[ScalingRecommendation],
        alerts: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """サマリー生成"""

        # 最も緊急性の高いリソース
        most_critical = None
        min_days = float("inf")

        for forecast in forecasts:
            if forecast.days_until_threshold is not None and forecast.days_until_threshold < min_days:
                min_days = forecast.days_until_threshold
                most_critical = forecast.resource_type

        # アクションが必要な推奨事項の数
        critical_recommendations = sum(1 for rec in recommendations if rec.urgency == "critical")
        high_recommendations = sum(1 for rec in recommendations if rec.urgency == "high")

        # 総合ステータス
        if critical_recommendations > 0 or min_days <= 7:
            overall_status = "critical"
            status_message = "緊急の容量対応が必要です"
        elif high_recommendations > 0 or min_days <= 14:
            overall_status = "warning"
            status_message = "早期の容量対応を推奨します"
        elif len(recommendations) > 0 or min_days <= 30:
            overall_status = "attention"
            status_message = "容量計画の確認が必要です"
        else:
            overall_status = "healthy"
            status_message = "現在の容量で十分です"

        return {
            "overall_status": overall_status,
            "status_message": status_message,
            "most_critical_resource": most_critical,
            "days_until_critical": int(min_days) if min_days != float("inf") else None,
            "total_recommendations": len(recommendations),
            "critical_recommendations": critical_recommendations,
            "high_recommendations": high_recommendations,
            "total_alerts": len(alerts),
            "resource_summary": {
                forecast.resource_type: {
                    "current": forecast.current_usage,
                    "predicted_30d": forecast.predicted_usage_30d,
                    "growth_rate": forecast.growth_rate_daily,
                }
                for forecast in forecasts
            },
        }

    def _save_capacity_plan(self, plan: CapacityPlan):
        """容量計画をデータベースに保存"""
        conn = get_connection(self.db_path)
        cursor = conn.cursor()

        plan_id = f"plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 容量計画を保存
        cursor.execute(
            """
            INSERT INTO capacity_plans
            (plan_id, generated_at, forecast_period_days, forecasts, recommendations, alerts, summary)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                plan_id,
                plan.generated_at,
                plan.forecast_period_days,
                json.dumps(
                    [
                        {
                            "resource_type": f.resource_type,
                            "current_usage": f.current_usage,
                            "predicted_usage_7d": f.predicted_usage_7d,
                            "predicted_usage_30d": f.predicted_usage_30d,
                            "predicted_usage_90d": f.predicted_usage_90d,
                            "growth_rate_daily": f.growth_rate_daily,
                            "days_until_threshold": f.days_until_threshold,
                        }
                        for f in plan.forecasts
                    ]
                ),
                json.dumps(
                    [
                        {
                            "resource_type": r.resource_type,
                            "action": r.action,
                            "urgency": r.urgency,
                            "current_capacity": r.current_capacity,
                            "recommended_capacity": r.recommended_capacity,
                            "reason": r.reason,
                            "estimated_days": r.estimated_days_until_needed,
                        }
                        for r in plan.recommendations
                    ]
                ),
                json.dumps(plan.alerts),
                json.dumps(plan.summary),
            ),
        )

        # 個別の予測と推奨事項も保存
        for forecast in plan.forecasts:
            cursor.execute(
                """
                INSERT INTO capacity_forecasts
                (timestamp, resource_type, current_usage, predicted_usage_7d,
                 predicted_usage_30d, predicted_usage_90d, growth_rate_daily, days_until_threshold)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    plan.generated_at,
                    forecast.resource_type,
                    forecast.current_usage,
                    forecast.predicted_usage_7d,
                    forecast.predicted_usage_30d,
                    forecast.predicted_usage_90d,
                    forecast.growth_rate_daily,
                    forecast.days_until_threshold,
                ),
            )

        for rec in plan.recommendations:
            cursor.execute(
                """
                INSERT INTO capacity_recommendations
                (timestamp, resource_type, action, urgency, current_capacity,
                 recommended_capacity, reason, estimated_days)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    plan.generated_at,
                    rec.resource_type,
                    rec.action,
                    rec.urgency,
                    rec.current_capacity,
                    rec.recommended_capacity,
                    rec.reason,
                    rec.estimated_days_until_needed,
                ),
            )

        conn.commit()
        conn.close()

    # プリント関数群
    def _print_forecast(self, forecast: CapacityForecast):
        """予測を表示"""
        print(f"  【{forecast.resource_type.upper()}】")
        print(f"    現在の使用率: {forecast.current_usage:.2f}%")
        print(f"    7日後予測: {forecast.predicted_usage_7d:.2f}%")
        print(f"    30日後予測: {forecast.predicted_usage_30d:.2f}%")
        print(f"    90日後予測: {forecast.predicted_usage_90d:.2f}%")
        print(f"    成長率（日次）: {forecast.growth_rate_daily:.4f}%")
        print(f"    容量閾値: {forecast.capacity_threshold:.2f}%")
        if forecast.days_until_threshold is not None:
            print(f"    閾値到達まで: {forecast.days_until_threshold}日")
        print()

    def _print_recommendation(self, rec: ScalingRecommendation):
        """推奨事項を表示"""
        urgency_symbols = {"critical": "🔴", "high": "🟡", "medium": "🟠", "low": "🟢"}
        symbol = urgency_symbols.get(rec.urgency, "⚪")

        print(f"  {symbol} [{rec.urgency.upper()}] {rec.resource_type.upper()}: {rec.action}")
        print(f"     現在の容量: {rec.current_capacity:.2f}%")
        print(f"     推奨容量: {rec.recommended_capacity:.2f}%")
        print(f"     理由: {rec.reason}")
        if rec.estimated_days_until_needed is not None:
            print(f"     必要になるまで: {rec.estimated_days_until_needed}日")
        print()

    def _print_alert(self, alert: Dict[str, Any]):
        """アラートを表示"""
        level_symbols = {"critical": "🔴", "high": "🟡", "info": "🔵"}
        symbol = level_symbols.get(alert["level"], "⚪")
        print(f"  {symbol} [{alert['level'].upper()}] {alert['message']}")

    def save_capacity_plan_report(self, plan: CapacityPlan, filename: Optional[str] = None) -> Path:
        """容量計画レポートをJSON形式で保存"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"capacity_plan_{timestamp}.json"

        output_path = self.reports_dir / filename

        plan_dict = {
            "generated_at": plan.generated_at,
            "forecast_period_days": plan.forecast_period_days,
            "forecasts": [
                {
                    "resource_type": f.resource_type,
                    "current_usage": f.current_usage,
                    "predicted_usage_7d": f.predicted_usage_7d,
                    "predicted_usage_30d": f.predicted_usage_30d,
                    "predicted_usage_90d": f.predicted_usage_90d,
                    "capacity_threshold": f.capacity_threshold,
                    "days_until_threshold": f.days_until_threshold,
                    "growth_rate_daily": f.growth_rate_daily,
                }
                for f in plan.forecasts
            ],
            "recommendations": [
                {
                    "resource_type": r.resource_type,
                    "action": r.action,
                    "urgency": r.urgency,
                    "current_capacity": r.current_capacity,
                    "recommended_capacity": r.recommended_capacity,
                    "reason": r.reason,
                    "estimated_days_until_needed": r.estimated_days_until_needed,
                }
                for r in plan.recommendations
            ],
            "alerts": plan.alerts,
            "summary": plan.summary,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(plan_dict, f, indent=2, ensure_ascii=False)

        print(f"\n✅ 容量計画レポート保存: {output_path}")
        return output_path


def main():
    """メイン関数"""
    import argparse

    parser = argparse.ArgumentParser(description="Phase 11.3 容量計画自動化システム")
    parser.add_argument("--generate", action="store_true", help="容量計画を生成")
    parser.add_argument("--forecast-days", type=int, default=90, help="予測期間（日数）")
    parser.add_argument("--history-days", type=int, default=30, help="履歴データ期間（日数）")
    parser.add_argument("--save", action="store_true", help="JSON形式で保存")

    args = parser.parse_args()

    capacity_system = CapacityPlanningAutomation()

    if args.generate:
        plan = capacity_system.generate_capacity_plan(forecast_days=args.forecast_days, history_days=args.history_days)

        # サマリー表示
        print()
        print("=" * 80)
        print("📈 容量計画サマリー")
        print("=" * 80)
        summary = plan.summary
        print(f"総合ステータス: {summary['overall_status'].upper()}")
        print(f"ステータスメッセージ: {summary['status_message']}")
        if summary["most_critical_resource"]:
            print(f"最も重要なリソース: {summary['most_critical_resource'].upper()}")
            if summary["days_until_critical"]:
                print(f"クリティカルまで: {summary['days_until_critical']}日")
        print(f"推奨事項総数: {summary['total_recommendations']}件")
        print(f"  - Critical: {summary['critical_recommendations']}件")
        print(f"  - High: {summary['high_recommendations']}件")
        print(f"アラート総数: {summary['total_alerts']}件")
        print("=" * 80)

        if args.save:
            capacity_system.save_capacity_plan_report(plan)
    else:
        print("オプションを指定してください。--help で使用方法を確認できます。")
        print()
        print("使用例:")
        print("  python src/capacity_planning_automation.py --generate --forecast-days 90 --history-days 30 --save")
