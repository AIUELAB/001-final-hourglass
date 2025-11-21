#!/usr/bin/env python3
"""
Cost Optimization Algorithm - Phase 11.4

リソース使用量とコストの最適化アルゴリズム
- リソースコスト分析
- 最適化推奨事項
- ROI計算
- コスト削減シミュレーション
"""

import argparse
import json
import sqlite3
import statistics
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.database_utils import get_connection

# ==========================================
# データクラス
# ==========================================


@dataclass
class ResourceCost:
    """リソースコスト情報"""

    resource_type: str
    current_usage: float  # 現在の使用量（%）
    allocated_capacity: float  # 割り当て容量
    unit_cost: float  # 単価（$/unit/hour）
    monthly_cost: float  # 月間コスト
    utilization_rate: float  # 稼働率（%）
    waste_percentage: float  # 無駄な割合（%）


@dataclass
class OptimizationRecommendation:
    """コスト最適化推奨事項"""

    resource_type: str
    recommendation_type: str  # reduce_capacity/increase_efficiency/consolidate/terminate
    current_cost: float
    optimized_cost: float
    monthly_savings: float
    annual_savings: float
    roi_months: float  # 投資回収期間（月）
    implementation_cost: float  # 実装コスト
    priority: str  # high/medium/low
    risk_level: str  # low/medium/high
    description: str
    action_items: List[str]


@dataclass
class CostSimulation:
    """コスト削減シミュレーション"""

    scenario_name: str
    current_monthly_cost: float
    projected_monthly_cost: float
    monthly_savings: float
    annual_savings: float
    implementation_cost: float
    roi_months: float
    confidence_level: float  # 0.0-1.0
    assumptions: List[str]
    risks: List[str]


# ==========================================
# メインクラス
# ==========================================


class CostOptimizationAlgorithm:
    """コスト最適化アルゴリズム"""

    def __init__(self, db_path: str = "unified_quality.db"):
        self.db_path = db_path
        self._init_database_tables()

        # コスト設定（$/unit/hour）
        self.cost_config = {
            "CPU": {
                "unit_cost": 0.05,  # $0.05/vCPU/hour
                "unit_name": "vCPU",
            },
            "MEMORY": {
                "unit_cost": 0.01,  # $0.01/GB/hour
                "unit_name": "GB",
            },
            "DISK": {
                "unit_cost": 0.001,  # $0.001/GB/hour
                "unit_name": "GB",
            },
        }

        # 最適化しきい値
        self.optimization_thresholds = {
            "low_utilization": 30,  # 30%未満の稼働率は低利用
            "high_waste": 40,  # 40%以上の無駄は高い
            "target_utilization": 70,  # 目標稼働率70%
        }

    def _init_database_tables(self):
        """データベーステーブルの初期化"""
        conn = get_connection(self.db_path)
        cursor = conn.cursor()

        # リソースコスト履歴テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS resource_costs (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                timestamp TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                current_usage REAL NOT NULL,
                allocated_capacity REAL NOT NULL,
                unit_cost REAL NOT NULL,
                monthly_cost REAL NOT NULL,
                utilization_rate REAL NOT NULL,
                waste_percentage REAL NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 最適化推奨履歴テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS optimization_recommendations (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                timestamp TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                recommendation_type TEXT NOT NULL,
                current_cost REAL NOT NULL,
                optimized_cost REAL NOT NULL,
                monthly_savings REAL NOT NULL,
                annual_savings REAL NOT NULL,
                roi_months REAL,
                implementation_cost REAL,
                priority TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                description TEXT,
                action_items TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # コストシミュレーション履歴テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cost_simulations (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                timestamp TEXT NOT NULL,
                scenario_name TEXT NOT NULL,
                current_monthly_cost REAL NOT NULL,
                projected_monthly_cost REAL NOT NULL,
                monthly_savings REAL NOT NULL,
                annual_savings REAL NOT NULL,
                implementation_cost REAL NOT NULL,
                roi_months REAL NOT NULL,
                confidence_level REAL NOT NULL,
                assumptions TEXT,
                risks TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # コスト最適化計画テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cost_optimization_plans (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                timestamp TEXT NOT NULL,
                plan_data TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def analyze_resource_costs(self, resource_type: str) -> Optional[ResourceCost]:
        """リソースコストの分析"""
        conn = get_connection(self.db_path)
        cursor = conn.cursor()

        # リソースタイプに応じてカラム名をマッピング
        column_map = {"CPU": "cpu_percent", "MEMORY": "memory_percent", "DISK": "disk_percent"}

        column_name = column_map.get(resource_type)
        if not column_name:
            conn.close()
            return None

        # 最新のリソース使用量を取得
        cursor.execute(f"""
            SELECT {column_name}, timestamp
            FROM system_metrics
            ORDER BY timestamp DESC
            LIMIT 1
        """)

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        current_usage = row[0]
        timestamp = row[1]

        # コスト設定を取得
        cost_config = self.cost_config.get(resource_type, {})
        unit_cost = cost_config.get("unit_cost", 0.0)

        # 仮想的な割り当て容量（100%として計算）
        allocated_capacity = 100.0

        # 稼働率を計算
        utilization_rate = current_usage

        # 無駄な割合を計算（100% - 稼働率）
        waste_percentage = 100.0 - utilization_rate

        # 月間コストを計算（730時間/月）
        monthly_cost = allocated_capacity * unit_cost * 730

        return ResourceCost(
            resource_type=resource_type,
            current_usage=current_usage,
            allocated_capacity=allocated_capacity,
            unit_cost=unit_cost,
            monthly_cost=monthly_cost,
            utilization_rate=utilization_rate,
            waste_percentage=waste_percentage,
        )

    def _analyze_cost_and_recommend(self, cost: ResourceCost) -> Optional[OptimizationRecommendation]:
        """コスト分析から推奨事項を生成"""

        resource_type = cost.resource_type
        utilization = cost.utilization_rate
        waste = cost.waste_percentage
        current_cost = cost.monthly_cost

        # 低稼働率の場合
        if utilization < self.optimization_thresholds["low_utilization"]:
            # 容量削減を推奨
            target_capacity = cost.allocated_capacity * (utilization / 100.0) * 1.3  # 30% buffer
            optimized_cost = target_capacity * cost.unit_cost * 730
            monthly_savings = current_cost - optimized_cost
            annual_savings = monthly_savings * 12

            # 実装コスト（ダウンタイム等）
            implementation_cost = current_cost * 0.1  # 10%を実装コストと仮定

            # ROI計算
            roi_months = implementation_cost / monthly_savings if monthly_savings > 0 else 999

            return OptimizationRecommendation(
                resource_type=resource_type,
                recommendation_type="reduce_capacity",
                current_cost=current_cost,
                optimized_cost=optimized_cost,
                monthly_savings=monthly_savings,
                annual_savings=annual_savings,
                roi_months=roi_months,
                implementation_cost=implementation_cost,
                priority="high" if waste > 50 else "medium",
                risk_level="low",
                description=f"{resource_type}の稼働率が{utilization:.1f}%と低いため、容量削減を推奨",
                action_items=[
                    f"現在の容量{cost.allocated_capacity:.1f}から{target_capacity:.1f}に削減",
                    "削減後の監視を2週間実施",
                    "パフォーマンステストを実行",
                ],
            )

        # 高無駄率の場合
        elif waste > self.optimization_thresholds["high_waste"]:
            # 効率化を推奨
            efficiency_gain = 0.2  # 20%の効率向上を仮定
            optimized_cost = current_cost * (1 - efficiency_gain)
            monthly_savings = current_cost - optimized_cost
            annual_savings = monthly_savings * 12

            implementation_cost = current_cost * 0.05  # 5%

            roi_months = implementation_cost / monthly_savings if monthly_savings > 0 else 999

            return OptimizationRecommendation(
                resource_type=resource_type,
                recommendation_type="increase_efficiency",
                current_cost=current_cost,
                optimized_cost=optimized_cost,
                monthly_savings=monthly_savings,
                annual_savings=annual_savings,
                roi_months=roi_months,
                implementation_cost=implementation_cost,
                priority="medium",
                risk_level="medium",
                description=f"{resource_type}の無駄が{waste:.1f}%あるため、効率化を推奨",
                action_items=["リソース使用パターンの最適化", "自動スケーリングの設定", "使用率のモニタリング強化"],
            )

        return None

    def generate_cost_optimization_plan(self) -> Dict[str, Any]:
        """コスト最適化計画の生成"""
        timestamp = datetime.now().isoformat()

        print("=" * 80)
        print("📊 Phase 11.4 - コスト最適化アルゴリズム")
        print("=" * 80)
        print(f"生成時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        print()

        # ステップ1: リソースコストの分析
        print("📌 ステップ1: リソースコストの分析")
        print("-" * 80)

        resource_types = ["CPU", "MEMORY", "DISK"]
        costs: List[ResourceCost] = []

        for resource_type in resource_types:
            cost = self.analyze_resource_costs(resource_type)
            if cost:
                costs.append(cost)
                print(f"  【{resource_type}】")
                print(f"    現在の使用率: {cost.current_usage:.2f}%")
                print(f"    割り当て容量: {cost.allocated_capacity:.2f}")
                print(f"    単価: ${cost.unit_cost:.4f}/unit/hour")
                print(f"    月間コスト: ${cost.monthly_cost:.2f}")
                print(f"    稼働率: {cost.utilization_rate:.2f}%")
                print(f"    無駄な割合: {cost.waste_percentage:.2f}%")
                print()

                # データベースに保存
                self._save_resource_cost(timestamp, cost)

        # ステップ2: 最適化推奨事項の生成
        print("📌 ステップ2: 最適化推奨事項の生成")
        print("-" * 80)

        recommendations: List[OptimizationRecommendation] = []

        for cost in costs:
            rec = self._analyze_cost_and_recommend(cost)
            if rec:
                recommendations.append(rec)
                print(f"  【推奨事項: {rec.resource_type}】")
                print(f"    タイプ: {rec.recommendation_type}")
                print(f"    優先度: {rec.priority}")
                print(f"    現在コスト: ${rec.current_cost:.2f}/月")
                print(f"    最適化後コスト: ${rec.optimized_cost:.2f}/月")
                print(f"    月間削減額: ${rec.monthly_savings:.2f}")
                print(f"    年間削減額: ${rec.annual_savings:.2f}")
                print(f"    ROI: {rec.roi_months:.1f}ヶ月")
                print(f"    説明: {rec.description}")
                print("    アクション:")
                for action in rec.action_items:
                    print(f"      - {action}")
                print()

                # データベースに保存
                self._save_optimization_recommendation(timestamp, rec)

        if not recommendations:
            print("  ✅ 最適化の必要なし（すべてのリソースが適切に利用されています）")
            print()

        # ステップ3: コスト削減シミュレーション
        print("📌 ステップ3: コスト削減シミュレーション")
        print("-" * 80)

        simulations = self._generate_cost_simulations(costs, recommendations)

        for sim in simulations:
            print(f"  【シナリオ: {sim.scenario_name}】")
            print(f"    現在の月間コスト: ${sim.current_monthly_cost:.2f}")
            print(f"    予測月間コスト: ${sim.projected_monthly_cost:.2f}")
            print(f"    月間削減額: ${sim.monthly_savings:.2f}")
            print(f"    年間削減額: ${sim.annual_savings:.2f}")
            print(f"    実装コスト: ${sim.implementation_cost:.2f}")
            print(f"    ROI: {sim.roi_months:.1f}ヶ月")
            print(f"    信頼度: {sim.confidence_level * 100:.1f}%")
            print("    前提条件:")
            for assumption in sim.assumptions:
                print(f"      - {assumption}")
            print("    リスク:")
            for risk in sim.risks:
                print(f"      - {risk}")
            print()

            # データベースに保存
            self._save_cost_simulation(timestamp, sim)

        # サマリーの計算
        print("=" * 80)
        print("📈 コスト最適化サマリー")
        print("=" * 80)

        total_current_cost = sum(c.monthly_cost for c in costs)
        total_savings = sum(r.monthly_savings for r in recommendations)
        total_annual_savings = total_savings * 12
        avg_roi = statistics.mean([r.roi_months for r in recommendations]) if recommendations else 0

        print(f"現在の総コスト: ${total_current_cost:.2f}/月")
        print(f"削減可能額: ${total_savings:.2f}/月 (${total_annual_savings:.2f}/年)")
        print(f"削減率: {(total_savings / total_current_cost * 100) if total_current_cost > 0 else 0:.1f}%")
        print(f"平均ROI: {avg_roi:.1f}ヶ月")
        print(f"推奨事項数: {len(recommendations)}件")
        print("=" * 80)

        # 計画データを作成
        plan_data = {
            "timestamp": timestamp,
            "costs": [asdict(c) for c in costs],
            "recommendations": [asdict(r) for r in recommendations],
            "simulations": [asdict(s) for s in simulations],
            "summary": {
                "total_current_cost": total_current_cost,
                "total_monthly_savings": total_savings,
                "total_annual_savings": total_annual_savings,
                "savings_percentage": (total_savings / total_current_cost * 100) if total_current_cost > 0 else 0,
                "average_roi_months": avg_roi,
                "recommendation_count": len(recommendations),
            },
        }

        # データベースに計画を保存
        self._save_optimization_plan(timestamp, plan_data)

        return plan_data

    def _generate_cost_simulations(
        self, costs: List[ResourceCost], recommendations: List[OptimizationRecommendation]
    ) -> List[CostSimulation]:
        """コスト削減シミュレーションの生成"""
        simulations = []

        # 現在の総コスト
        current_total_cost = sum(c.monthly_cost for c in costs)

        # シナリオ1: すべての推奨事項を実装
        if recommendations:
            total_savings = sum(r.monthly_savings for r in recommendations)
            total_impl_cost = sum(r.implementation_cost for r in recommendations)
            projected_cost = current_total_cost - total_savings
            annual_savings = total_savings * 12
            roi = total_impl_cost / total_savings if total_savings > 0 else 999

            simulations.append(
                CostSimulation(
                    scenario_name="全推奨事項の実装",
                    current_monthly_cost=current_total_cost,
                    projected_monthly_cost=projected_cost,
                    monthly_savings=total_savings,
                    annual_savings=annual_savings,
                    implementation_cost=total_impl_cost,
                    roi_months=roi,
                    confidence_level=0.85,
                    assumptions=[
                        "すべての推奨事項が計画通りに実装される",
                        "リソース使用パターンが現在と同じ",
                        "コスト削減効果が即座に発揮される",
                    ],
                    risks=["実装中のダウンタイムによる損失", "予期しない互換性問題", "移行作業の遅延"],
                )
            )

        # シナリオ2: 高優先度のみ実装
        high_priority = [r for r in recommendations if r.priority == "high"]
        if high_priority:
            total_savings = sum(r.monthly_savings for r in high_priority)
            total_impl_cost = sum(r.implementation_cost for r in high_priority)
            projected_cost = current_total_cost - total_savings
            annual_savings = total_savings * 12
            roi = total_impl_cost / total_savings if total_savings > 0 else 999

            simulations.append(
                CostSimulation(
                    scenario_name="高優先度のみ実装",
                    current_monthly_cost=current_total_cost,
                    projected_monthly_cost=projected_cost,
                    monthly_savings=total_savings,
                    annual_savings=annual_savings,
                    implementation_cost=total_impl_cost,
                    roi_months=roi,
                    confidence_level=0.95,
                    assumptions=["高優先度項目のみ実装", "リスクの低い変更のみ実施", "段階的な実装"],
                    risks=["全体的なコスト削減効果は限定的", "残りの推奨事項の先送り"],
                )
            )

        # シナリオ3: 段階的実装（6ヶ月計画）
        if recommendations:
            # 6ヶ月で段階的に実装すると仮定
            total_savings = sum(r.monthly_savings for r in recommendations)
            total_impl_cost = sum(r.implementation_cost for r in recommendations)

            # 段階的実装により、初月は50%、3ヶ月目で75%、6ヶ月目で100%の効果
            avg_savings = total_savings * 0.75  # 平均75%の効果
            projected_cost = current_total_cost - avg_savings
            annual_savings = total_savings * 12  # 最終的な年間削減額

            simulations.append(
                CostSimulation(
                    scenario_name="段階的実装（6ヶ月計画）",
                    current_monthly_cost=current_total_cost,
                    projected_monthly_cost=projected_cost,
                    monthly_savings=avg_savings,
                    annual_savings=annual_savings,
                    implementation_cost=total_impl_cost,
                    roi_months=total_impl_cost / avg_savings if avg_savings > 0 else 999,
                    confidence_level=0.90,
                    assumptions=[
                        "6ヶ月で段階的に実装",
                        "初月50%、3ヶ月目75%、6ヶ月目100%の効果",
                        "リスクを最小化しながら実装",
                    ],
                    risks=["削減効果の発現が遅い", "実装期間中のコスト増加の可能性", "計画の遅延リスク"],
                )
            )

        return simulations

    def _save_resource_cost(self, timestamp: str, cost: ResourceCost):
        """リソースコストをデータベースに保存"""
        conn = get_connection(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO resource_costs (
                timestamp, resource_type, current_usage, allocated_capacity,
                unit_cost, monthly_cost, utilization_rate, waste_percentage
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                timestamp,
                cost.resource_type,
                cost.current_usage,
                cost.allocated_capacity,
                cost.unit_cost,
                cost.monthly_cost,
                cost.utilization_rate,
                cost.waste_percentage,
            ),
        )

        conn.commit()
        conn.close()

    def _save_optimization_recommendation(self, timestamp: str, rec: OptimizationRecommendation):
        """最適化推奨事項をデータベースに保存"""
        conn = get_connection(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO optimization_recommendations (
                timestamp, resource_type, recommendation_type, current_cost,
                optimized_cost, monthly_savings, annual_savings, roi_months,
                implementation_cost, priority, risk_level, description, action_items
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                timestamp,
                rec.resource_type,
                rec.recommendation_type,
                rec.current_cost,
                rec.optimized_cost,
                rec.monthly_savings,
                rec.annual_savings,
                rec.roi_months,
                rec.implementation_cost,
                rec.priority,
                rec.risk_level,
                rec.description,
                json.dumps(rec.action_items, ensure_ascii=False),
            ),
        )

        conn.commit()
        conn.close()

    def _save_cost_simulation(self, timestamp: str, sim: CostSimulation):
        """コストシミュレーションをデータベースに保存"""
        conn = get_connection(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO cost_simulations (
                timestamp, scenario_name, current_monthly_cost, projected_monthly_cost,
                monthly_savings, annual_savings, implementation_cost, roi_months,
                confidence_level, assumptions, risks
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                timestamp,
                sim.scenario_name,
                sim.current_monthly_cost,
                sim.projected_monthly_cost,
                sim.monthly_savings,
                sim.annual_savings,
                sim.implementation_cost,
                sim.roi_months,
                sim.confidence_level,
                json.dumps(sim.assumptions, ensure_ascii=False),
                json.dumps(sim.risks, ensure_ascii=False),
            ),
        )

        conn.commit()
        conn.close()

    def _save_optimization_plan(self, timestamp: str, plan_data: Dict[str, Any]):
        """コスト最適化計画をデータベースに保存"""
        conn = get_connection(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO cost_optimization_plans (timestamp, plan_data)
            VALUES (?, ?)
        """,
            (timestamp, json.dumps(plan_data, ensure_ascii=False)),
        )

        conn.commit()
        conn.close()

    def show_history(self, limit: int = 10):
        """コスト最適化計画の履歴を表示"""
        conn = get_connection(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT timestamp, plan_data
            FROM cost_optimization_plans
            ORDER BY created_at DESC
            LIMIT ?
        """,
            (limit,),
        )

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            print("コスト最適化計画の履歴がありません")
            return

        print("=" * 80)
        print("📊 コスト最適化計画の履歴")
        print("=" * 80)

        for i, row in enumerate(rows, 1):
            timestamp = row[0]
            plan_data = json.loads(row[1])
            summary = plan_data.get("summary", {})

            print(f"\n{i}. {timestamp}")
            print(f"   総コスト: ${summary.get('total_current_cost', 0):.2f}/月")
            print(f"   削減可能額: ${summary.get('total_monthly_savings', 0):.2f}/月")
            print(f"   削減率: {summary.get('savings_percentage', 0):.1f}%")
            print(f"   推奨事項数: {summary.get('recommendation_count', 0)}件")


# ==========================================
# メイン処理
# ==========================================


def main():
    parser = argparse.ArgumentParser(description="Cost Optimization Algorithm - Phase 11.4")
    parser.add_argument("--generate", action="store_true", help="コスト最適化計画を生成")
    parser.add_argument("--history", action="store_true", help="コスト最適化計画の履歴を表示")
    parser.add_argument("--limit", type=int, default=10, help="履歴表示の件数")
    parser.add_argument("--save", action="store_true", help="結果をJSONファイルに保存")

    args = parser.parse_args()

    optimizer = CostOptimizationAlgorithm()

    if args.generate:
        plan_data = optimizer.generate_cost_optimization_plan()

        if args.save:
            # レポートディレクトリの作成
            reports_dir = Path("reports/cost_optimization")
            reports_dir.mkdir(parents=True, exist_ok=True)

            # JSONファイルに保存
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"cost_optimization_plan_{timestamp}.json"
            filepath = reports_dir / filename

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(plan_data, f, ensure_ascii=False, indent=2)

            print()
            print(f"✅ レポート保存: {filepath}")

    elif args.history:
        optimizer.show_history(limit=args.limit)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
