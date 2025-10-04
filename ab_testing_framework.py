#!/usr/bin/env python3
"""
A/B Testing Framework - 実験管理と段階的ロールアウト
Phase 5 - Continuous Improvement
"""

import asyncio
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field, asdict
import numpy as np
from scipy import stats
import pandas as pd
import logging
from enum import Enum
from collections import defaultdict
import random
import uuid

logger = logging.getLogger(__name__)

class ExperimentStatus(Enum):
    """実験ステータス"""
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ROLLED_BACK = "rolled_back"

class VariantType(Enum):
    """バリアントタイプ"""
    CONTROL = "control"
    TREATMENT = "treatment"

@dataclass
class Variant:
    """実験バリアント"""
    name: str
    type: VariantType
    config: Dict[str, Any]
    traffic_percentage: float
    description: str = ""

@dataclass
class ExperimentMetrics:
    """実験メトリクス"""
    variant_name: str
    samples: int = 0
    successes: int = 0
    failures: int = 0
    total_value: float = 0.0
    sum_squares: float = 0.0  # 分散計算用
    conversion_rate: float = 0.0
    average_value: float = 0.0
    confidence_interval: Tuple[float, float] = (0.0, 0.0)

@dataclass
class Experiment:
    """A/B実験定義"""
    experiment_id: str
    name: str
    description: str
    start_time: datetime
    end_time: Optional[datetime]
    status: ExperimentStatus
    variants: List[Variant]
    target_metric: str
    minimum_samples: int = 1000
    confidence_level: float = 0.95
    metrics: Dict[str, ExperimentMetrics] = field(default_factory=dict)
    feature_flags: Dict[str, Any] = field(default_factory=dict)

class ABTestingFramework:
    """A/Bテスティングフレームワーク"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.experiments: Dict[str, Experiment] = {}
        self.user_assignments: Dict[str, Dict[str, str]] = defaultdict(dict)
        self.feature_flags: Dict[str, Any] = {}
        self.rollout_policies: Dict[str, Callable] = {}

        # Canary Release設定
        self.canary_percentages = [5, 10, 25, 50, 100]
        self.canary_current = {}

    def create_experiment(
        self,
        name: str,
        description: str,
        control_config: Dict[str, Any],
        treatment_config: Dict[str, Any],
        traffic_split: Tuple[float, float] = (0.5, 0.5),
        target_metric: str = "quality_score",
        minimum_samples: int = 1000
    ) -> Experiment:
        """実験作成"""
        experiment_id = str(uuid.uuid4())

        # バリアント作成
        control = Variant(
            name="control",
            type=VariantType.CONTROL,
            config=control_config,
            traffic_percentage=traffic_split[0],
            description="Control group"
        )

        treatment = Variant(
            name="treatment",
            type=VariantType.TREATMENT,
            config=treatment_config,
            traffic_percentage=traffic_split[1],
            description="Treatment group"
        )

        # 実験作成
        experiment = Experiment(
            experiment_id=experiment_id,
            name=name,
            description=description,
            start_time=datetime.now(),
            end_time=None,
            status=ExperimentStatus.DRAFT,
            variants=[control, treatment],
            target_metric=target_metric,
            minimum_samples=minimum_samples,
            metrics={
                "control": ExperimentMetrics(variant_name="control"),
                "treatment": ExperimentMetrics(variant_name="treatment")
            }
        )

        self.experiments[experiment_id] = experiment
        logger.info(f"✅ 実験作成: {name} (ID: {experiment_id})")

        return experiment

    def start_experiment(self, experiment_id: str):
        """実験開始"""
        if experiment_id not in self.experiments:
            raise ValueError(f"実験が見つかりません: {experiment_id}")

        experiment = self.experiments[experiment_id]
        experiment.status = ExperimentStatus.RUNNING
        experiment.start_time = datetime.now()

        logger.info(f"🚀 実験開始: {experiment.name}")

    def get_variant(
        self,
        experiment_id: str,
        user_id: str,
        sticky: bool = True
    ) -> Optional[Variant]:
        """ユーザーのバリアント取得"""
        if experiment_id not in self.experiments:
            return None

        experiment = self.experiments[experiment_id]

        if experiment.status != ExperimentStatus.RUNNING:
            return None

        # Sticky assignment
        if sticky and user_id in self.user_assignments[experiment_id]:
            variant_name = self.user_assignments[experiment_id][user_id]
            return next(v for v in experiment.variants if v.name == variant_name)

        # 新規割り当て
        assignment_hash = int(hashlib.md5(
            f"{experiment_id}:{user_id}".encode()
        ).hexdigest(), 16)

        threshold = 0.0
        for variant in experiment.variants:
            threshold += variant.traffic_percentage
            if (assignment_hash % 100) / 100.0 < threshold:
                if sticky:
                    self.user_assignments[experiment_id][user_id] = variant.name
                return variant

        return experiment.variants[0]  # Fallback to control

    def record_event(
        self,
        experiment_id: str,
        variant_name: str,
        success: bool,
        value: Optional[float] = None
    ):
        """イベント記録"""
        if experiment_id not in self.experiments:
            return

        experiment = self.experiments[experiment_id]
        if variant_name not in experiment.metrics:
            return

        metrics = experiment.metrics[variant_name]
        metrics.samples += 1

        if success:
            metrics.successes += 1

        if value is not None:
            metrics.total_value += value
            metrics.sum_squares += value ** 2

        # メトリクス更新
        self._update_metrics(metrics)

    def _update_metrics(self, metrics: ExperimentMetrics):
        """メトリクス更新"""
        if metrics.samples > 0:
            metrics.conversion_rate = metrics.successes / metrics.samples
            metrics.average_value = metrics.total_value / metrics.samples

            # 信頼区間計算（Wilson score interval）
            if metrics.samples >= 30:
                z = stats.norm.ppf(0.975)  # 95%信頼区間
                p = metrics.conversion_rate
                n = metrics.samples

                denominator = 1 + z**2 / n
                center = (p + z**2 / (2*n)) / denominator
                margin = z * np.sqrt(p * (1-p) / n + z**2 / (4*n**2)) / denominator

                metrics.confidence_interval = (
                    max(0, center - margin),
                    min(1, center + margin)
                )

    def calculate_statistical_significance(
        self,
        experiment_id: str
    ) -> Dict[str, Any]:
        """統計的有意性計算"""
        if experiment_id not in self.experiments:
            return {}

        experiment = self.experiments[experiment_id]
        control_metrics = experiment.metrics.get("control")
        treatment_metrics = experiment.metrics.get("treatment")

        if not control_metrics or not treatment_metrics:
            return {}

        # 最小サンプル数チェック
        if (control_metrics.samples < 30 or
            treatment_metrics.samples < 30):
            return {
                'significant': False,
                'p_value': None,
                'message': 'Insufficient samples'
            }

        # Z検定（比率の差）
        p1 = control_metrics.conversion_rate
        p2 = treatment_metrics.conversion_rate
        n1 = control_metrics.samples
        n2 = treatment_metrics.samples

        p_pooled = (control_metrics.successes + treatment_metrics.successes) / (n1 + n2)
        se = np.sqrt(p_pooled * (1 - p_pooled) * (1/n1 + 1/n2))

        if se == 0:
            return {
                'significant': False,
                'p_value': 1.0,
                'message': 'No variance'
            }

        z_score = (p2 - p1) / se
        p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))

        # 効果サイズ（Cohen's h）
        h = 2 * (np.arcsin(np.sqrt(p2)) - np.arcsin(np.sqrt(p1)))

        # 検定力計算
        power = self._calculate_power(n1, n2, h)

        return {
            'significant': p_value < (1 - experiment.confidence_level),
            'p_value': p_value,
            'z_score': z_score,
            'effect_size': h,
            'power': power,
            'lift': ((p2 - p1) / p1 * 100) if p1 > 0 else 0,
            'control_rate': p1,
            'treatment_rate': p2,
            'confidence_level': experiment.confidence_level
        }

    def _calculate_power(self, n1: int, n2: int, effect_size: float) -> float:
        """検定力計算"""
        # 簡略化された検定力計算
        n_harmonic = 2 * n1 * n2 / (n1 + n2)
        nc_parameter = effect_size * np.sqrt(n_harmonic / 2)
        z_alpha = stats.norm.ppf(0.975)  # 両側検定
        power = 1 - stats.norm.cdf(z_alpha - nc_parameter)
        return max(0, min(1, power))

    def should_stop_experiment(
        self,
        experiment_id: str
    ) -> Tuple[bool, str]:
        """実験停止判定"""
        if experiment_id not in self.experiments:
            return False, "Experiment not found"

        experiment = self.experiments[experiment_id]
        significance = self.calculate_statistical_significance(experiment_id)

        # 最小サンプル数到達
        total_samples = sum(
            m.samples for m in experiment.metrics.values()
        )

        if total_samples < experiment.minimum_samples:
            return False, f"Need more samples: {total_samples}/{experiment.minimum_samples}"

        # 統計的有意性
        if significance.get('significant'):
            if significance.get('power', 0) > 0.8:
                return True, "Statistical significance reached with adequate power"

        # 実験期間
        if experiment.end_time and datetime.now() > experiment.end_time:
            return True, "Experiment duration exceeded"

        # 有害性チェック（treatment群が著しく悪い）
        if significance.get('lift', 0) < -20:  # 20%以上の悪化
            return True, "Treatment performing significantly worse"

        return False, "Continue experiment"

    def rollout_canary(
        self,
        experiment_id: str,
        current_percentage: Optional[int] = None
    ) -> int:
        """カナリアリリース段階的ロールアウト"""
        if experiment_id not in self.experiments:
            return 0

        # 現在のパーセンテージ取得
        if current_percentage is None:
            current_percentage = self.canary_current.get(experiment_id, 0)

        # 次のステージ
        next_percentage = current_percentage
        for pct in self.canary_percentages:
            if pct > current_percentage:
                next_percentage = pct
                break

        # バリアント更新
        experiment = self.experiments[experiment_id]
        if experiment.variants:
            treatment = next((v for v in experiment.variants
                            if v.type == VariantType.TREATMENT), None)
            if treatment:
                treatment.traffic_percentage = next_percentage / 100.0
                control = next((v for v in experiment.variants
                              if v.type == VariantType.CONTROL), None)
                if control:
                    control.traffic_percentage = 1.0 - treatment.traffic_percentage

        self.canary_current[experiment_id] = next_percentage
        logger.info(f"📈 カナリアロールアウト: {next_percentage}%")

        return next_percentage

    def rollback_experiment(self, experiment_id: str):
        """実験ロールバック"""
        if experiment_id not in self.experiments:
            return

        experiment = self.experiments[experiment_id]
        experiment.status = ExperimentStatus.ROLLED_BACK
        experiment.end_time = datetime.now()

        # すべてのトラフィックをcontrolに戻す
        for variant in experiment.variants:
            if variant.type == VariantType.CONTROL:
                variant.traffic_percentage = 1.0
            else:
                variant.traffic_percentage = 0.0

        # ユーザー割り当てクリア
        self.user_assignments[experiment_id].clear()

        logger.warning(f"⚠️ 実験ロールバック: {experiment.name}")

    def get_experiment_report(self, experiment_id: str) -> Dict[str, Any]:
        """実験レポート生成"""
        if experiment_id not in self.experiments:
            return {}

        experiment = self.experiments[experiment_id]
        significance = self.calculate_statistical_significance(experiment_id)

        report = {
            'experiment': {
                'id': experiment_id,
                'name': experiment.name,
                'status': experiment.status.value,
                'start_time': experiment.start_time.isoformat(),
                'end_time': experiment.end_time.isoformat() if experiment.end_time else None,
                'duration_hours': (
                    (experiment.end_time or datetime.now()) - experiment.start_time
                ).total_seconds() / 3600
            },
            'metrics': {},
            'statistical_analysis': significance,
            'recommendation': self._generate_recommendation(experiment, significance)
        }

        # 各バリアントのメトリクス
        for variant_name, metrics in experiment.metrics.items():
            report['metrics'][variant_name] = {
                'samples': metrics.samples,
                'conversion_rate': metrics.conversion_rate,
                'confidence_interval': metrics.confidence_interval,
                'average_value': metrics.average_value
            }

        return report

    def _generate_recommendation(
        self,
        experiment: Experiment,
        significance: Dict[str, Any]
    ) -> str:
        """推奨事項生成"""
        if not significance.get('significant'):
            return "Continue experiment to gather more data"

        lift = significance.get('lift', 0)

        if lift > 5:
            return "Strong positive impact - recommend full rollout"
        elif lift > 0:
            return "Positive impact - consider gradual rollout"
        elif lift > -5:
            return "Negligible impact - review implementation cost"
        else:
            return "Negative impact - recommend rollback"

    def export_results(self, experiment_id: str, format: str = 'json') -> str:
        """結果エクスポート"""
        report = self.get_experiment_report(experiment_id)

        if format == 'json':
            return json.dumps(report, indent=2, default=str)
        elif format == 'csv':
            metrics_df = pd.DataFrame(report['metrics']).T
            return metrics_df.to_csv()
        else:
            raise ValueError(f"Unsupported format: {format}")

async def test_ab_framework():
    """A/Bテストフレームワークのテスト"""
    framework = ABTestingFramework()

    # 実験作成
    experiment = framework.create_experiment(
        name="ML Weight Optimization",
        description="Test new ML weight algorithm",
        control_config={'algorithm': 'current', 'weights': [1.0, 1.0, 1.0]},
        treatment_config={'algorithm': 'optimized', 'weights': [1.2, 0.8, 1.1]},
        traffic_split=(0.5, 0.5),
        target_metric="quality_score"
    )

    # 実験開始
    framework.start_experiment(experiment.experiment_id)

    # シミュレートされたデータ
    print("📊 A/Bテスト実行中...")
    for i in range(2000):
        user_id = f"user_{i}"
        variant = framework.get_variant(experiment.experiment_id, user_id)

        if variant:
            # シミュレートされた結果（treatment群が少し良い）
            if variant.type == VariantType.TREATMENT:
                success = random.random() < 0.35  # 35% conversion
                value = random.gauss(85, 10)
            else:
                success = random.random() < 0.30  # 30% conversion
                value = random.gauss(80, 10)

            framework.record_event(
                experiment.experiment_id,
                variant.name,
                success,
                value
            )

        # 定期的なチェック
        if i % 500 == 499:
            should_stop, reason = framework.should_stop_experiment(
                experiment.experiment_id
            )
            print(f"  サンプル {i+1}: {reason}")

            if should_stop:
                break

    # 結果レポート
    report = framework.get_experiment_report(experiment.experiment_id)

    print("\n" + "="*70)
    print("🔬 A/Bテスト結果")
    print("="*70)
    print(f"実験名: {report['experiment']['name']}")
    print(f"ステータス: {report['experiment']['status']}")
    print(f"期間: {report['experiment']['duration_hours']:.2f}時間")

    print("\nメトリクス:")
    for variant, metrics in report['metrics'].items():
        print(f"  {variant}:")
        print(f"    サンプル数: {metrics['samples']}")
        print(f"    変換率: {metrics['conversion_rate']:.2%}")
        print(f"    信頼区間: [{metrics['confidence_interval'][0]:.2%}, {metrics['confidence_interval'][1]:.2%}]")

    print("\n統計分析:")
    stats_analysis = report['statistical_analysis']
    if stats_analysis:
        print(f"  有意性: {stats_analysis.get('significant')}")
        print(f"  p値: {stats_analysis.get('p_value', 'N/A'):.4f}" if stats_analysis.get('p_value') else "  p値: N/A")
        print(f"  リフト: {stats_analysis.get('lift', 0):.1f}%")
        print(f"  検定力: {stats_analysis.get('power', 0):.2f}")

    print(f"\n推奨: {report['recommendation']}")

if __name__ == "__main__":
    asyncio.run(test_ab_framework())