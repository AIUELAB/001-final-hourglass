"""
自動スケーリングとリソース最適化システム

予測的スケーリング、リソース最適化、コスト管理を統合した
インテリジェントな自動スケーリングシステム。
"""

import os
import json
import time
import math
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import numpy as np
from collections import deque
import threading
import logging
from enum import Enum


class ScalingStrategy(Enum):
    """スケーリング戦略"""
    REACTIVE = "reactive"  # リアクティブ（閾値ベース）
    PREDICTIVE = "predictive"  # 予測的（ML/統計ベース）
    SCHEDULED = "scheduled"  # スケジュール（時間ベース）
    HYBRID = "hybrid"  # ハイブリッド（組み合わせ）


class ResourceType(Enum):
    """リソースタイプ"""
    CPU = "cpu"
    MEMORY = "memory"
    NETWORK = "network"
    DISK = "disk"
    REQUESTS = "requests"
    CUSTOM = "custom"


@dataclass
class ScalingPolicy:
    """スケーリングポリシー"""

    # 基本設定
    name: str
    enabled: bool = True
    strategy: ScalingStrategy = ScalingStrategy.HYBRID

    # スケーリング範囲
    min_replicas: int = 2
    max_replicas: int = 20
    target_replicas: int = 5

    # CPU基準
    cpu_target_utilization: float = 70.0  # %
    cpu_scale_up_threshold: float = 80.0
    cpu_scale_down_threshold: float = 30.0

    # メモリ基準
    memory_target_utilization: float = 75.0  # %
    memory_scale_up_threshold: float = 85.0
    memory_scale_down_threshold: float = 40.0

    # リクエスト基準
    requests_per_second_target: float = 100.0
    requests_per_second_scale_up: float = 150.0
    requests_per_second_scale_down: float = 50.0

    # レイテンシ基準
    latency_target_p99: float = 100.0  # ms
    latency_scale_up_p99: float = 200.0
    latency_scale_down_p99: float = 50.0

    # スケーリング動作
    scale_up_increment: int = 2  # 一度に増やすレプリカ数
    scale_down_increment: int = 1  # 一度に減らすレプリカ数
    scale_up_cooldown: int = 60  # 秒
    scale_down_cooldown: int = 300  # 秒
    scale_up_stabilization: int = 30  # 安定化期間（秒）
    scale_down_stabilization: int = 120

    # 予測設定
    prediction_window: int = 300  # 予測ウィンドウ（秒）
    prediction_confidence: float = 0.8  # 予測信頼度閾値

    # コスト設定
    cost_per_replica_hour: float = 0.05  # $/hour
    max_daily_cost: float = 100.0  # $/day
    cost_optimization_enabled: bool = True


@dataclass
class ResourceMetrics:
    """リソースメトリクス"""
    timestamp: datetime
    cpu_usage: float  # %
    memory_usage: float  # %
    network_in: float  # Mbps
    network_out: float  # Mbps
    disk_usage: float  # %
    requests_per_second: float
    latency_p50: float  # ms
    latency_p95: float
    latency_p99: float
    error_rate: float  # %
    active_connections: int
    queue_length: int


class MetricsCollector:
    """メトリクス収集器"""

    def __init__(self, window_size: int = 300):
        self.window_size = window_size
        self.metrics_history: deque = deque(maxlen=window_size)
        self.lock = threading.Lock()

    def collect(self) -> ResourceMetrics:
        """現在のメトリクスを収集"""
        # 実際の実装ではPrometheusやCloudWatchから取得
        metrics = ResourceMetrics(
            timestamp=datetime.utcnow(),
            cpu_usage=self._get_cpu_usage(),
            memory_usage=self._get_memory_usage(),
            network_in=self._get_network_in(),
            network_out=self._get_network_out(),
            disk_usage=self._get_disk_usage(),
            requests_per_second=self._get_rps(),
            latency_p50=self._get_latency_p50(),
            latency_p95=self._get_latency_p95(),
            latency_p99=self._get_latency_p99(),
            error_rate=self._get_error_rate(),
            active_connections=self._get_active_connections(),
            queue_length=self._get_queue_length()
        )

        with self.lock:
            self.metrics_history.append(metrics)

        return metrics

    def get_average_metrics(self, duration_seconds: int = 60) -> ResourceMetrics:
        """指定期間の平均メトリクス取得"""
        with self.lock:
            recent_metrics = [
                m for m in self.metrics_history
                if m.timestamp > datetime.utcnow() - timedelta(seconds=duration_seconds)
            ]

        if not recent_metrics:
            return self.collect()

        # 平均計算
        avg_metrics = ResourceMetrics(
            timestamp=datetime.utcnow(),
            cpu_usage=np.mean([m.cpu_usage for m in recent_metrics]),
            memory_usage=np.mean([m.memory_usage for m in recent_metrics]),
            network_in=np.mean([m.network_in for m in recent_metrics]),
            network_out=np.mean([m.network_out for m in recent_metrics]),
            disk_usage=np.mean([m.disk_usage for m in recent_metrics]),
            requests_per_second=np.mean([m.requests_per_second for m in recent_metrics]),
            latency_p50=np.mean([m.latency_p50 for m in recent_metrics]),
            latency_p95=np.mean([m.latency_p95 for m in recent_metrics]),
            latency_p99=np.mean([m.latency_p99 for m in recent_metrics]),
            error_rate=np.mean([m.error_rate for m in recent_metrics]),
            active_connections=int(np.mean([m.active_connections for m in recent_metrics])),
            queue_length=int(np.mean([m.queue_length for m in recent_metrics]))
        )

        return avg_metrics

    def _get_cpu_usage(self) -> float:
        """CPU使用率取得（モック）"""
        # 実際はpsutil or /proc/statから取得
        import random
        return 50 + random.uniform(-20, 30)

    def _get_memory_usage(self) -> float:
        """メモリ使用率取得（モック）"""
        import random
        return 60 + random.uniform(-15, 25)

    def _get_network_in(self) -> float:
        """ネットワーク入力取得（モック）"""
        import random
        return random.uniform(10, 100)

    def _get_network_out(self) -> float:
        """ネットワーク出力取得（モック）"""
        import random
        return random.uniform(10, 100)

    def _get_disk_usage(self) -> float:
        """ディスク使用率取得（モック）"""
        import random
        return 40 + random.uniform(-5, 10)

    def _get_rps(self) -> float:
        """RPS取得（モック）"""
        import random
        return 80 + random.uniform(-30, 50)

    def _get_latency_p50(self) -> float:
        """P50レイテンシ取得（モック）"""
        import random
        return 20 + random.uniform(-5, 10)

    def _get_latency_p95(self) -> float:
        """P95レイテンシ取得（モック）"""
        import random
        return 50 + random.uniform(-10, 20)

    def _get_latency_p99(self) -> float:
        """P99レイテンシ取得（モック）"""
        import random
        return 80 + random.uniform(-20, 40)

    def _get_error_rate(self) -> float:
        """エラー率取得（モック）"""
        import random
        return random.uniform(0, 2)

    def _get_active_connections(self) -> int:
        """アクティブ接続数取得（モック）"""
        import random
        return random.randint(100, 1000)

    def _get_queue_length(self) -> int:
        """キュー長取得（モック）"""
        import random
        return random.randint(0, 50)


class PredictiveScaler:
    """予測的スケーラー

    時系列予測を使用して将来のリソース需要を予測
    """

    def __init__(self, history_size: int = 1440):  # 24時間分（1分毎）
        self.history_size = history_size
        self.history: deque = deque(maxlen=history_size)
        self.model = None

    def add_data_point(self, metrics: ResourceMetrics):
        """データポイント追加"""
        self.history.append({
            'timestamp': metrics.timestamp.timestamp(),
            'cpu': metrics.cpu_usage,
            'memory': metrics.memory_usage,
            'rps': metrics.requests_per_second,
            'latency': metrics.latency_p99
        })

    def predict_load(self, future_minutes: int = 5) -> Dict[str, float]:
        """将来の負荷予測"""
        if len(self.history) < 60:
            # データ不足の場合は予測せず
            return {}

        # 簡易的な線形外挿（実際はARIMA、Prophet等を使用）
        recent_data = list(self.history)[-60:]  # 直近1時間

        predictions = {}
        for metric in ['cpu', 'memory', 'rps', 'latency']:
            values = [d[metric] for d in recent_data]
            trend = np.polyfit(range(len(values)), values, 1)[0]
            current = values[-1]
            predicted = current + (trend * future_minutes)
            predictions[metric] = max(0, predicted)

        return predictions

    def get_seasonality(self) -> Dict[str, Any]:
        """季節性パターン検出"""
        if len(self.history) < self.history_size:
            return {}

        # 時間帯別の平均負荷計算
        hourly_patterns = {}
        for hour in range(24):
            hour_data = [
                d for d in self.history
                if datetime.fromtimestamp(d['timestamp']).hour == hour
            ]
            if hour_data:
                hourly_patterns[hour] = {
                    'cpu': np.mean([d['cpu'] for d in hour_data]),
                    'memory': np.mean([d['memory'] for d in hour_data]),
                    'rps': np.mean([d['rps'] for d in hour_data])
                }

        return hourly_patterns


class ScalingDecisionEngine:
    """スケーリング判断エンジン"""

    def __init__(self, policy: ScalingPolicy):
        self.policy = policy
        self.last_scale_time = datetime.utcnow()
        self.last_scale_action = None
        self.current_replicas = policy.target_replicas

    def decide(self, metrics: ResourceMetrics,
               predictions: Optional[Dict[str, float]] = None) -> Tuple[str, int]:
        """スケーリング判断

        Returns:
            (action, target_replicas): actionは'scale_up', 'scale_down', 'no_change'
        """
        # クールダウン確認
        if not self._check_cooldown():
            return ('no_change', self.current_replicas)

        # 戦略に応じた判断
        if self.policy.strategy == ScalingStrategy.REACTIVE:
            return self._reactive_decision(metrics)
        elif self.policy.strategy == ScalingStrategy.PREDICTIVE:
            return self._predictive_decision(metrics, predictions)
        elif self.policy.strategy == ScalingStrategy.SCHEDULED:
            return self._scheduled_decision()
        else:  # HYBRID
            return self._hybrid_decision(metrics, predictions)

    def _check_cooldown(self) -> bool:
        """クールダウン期間チェック"""
        elapsed = (datetime.utcnow() - self.last_scale_time).total_seconds()

        if self.last_scale_action == 'scale_up':
            return elapsed >= self.policy.scale_up_cooldown
        elif self.last_scale_action == 'scale_down':
            return elapsed >= self.policy.scale_down_cooldown

        return True

    def _reactive_decision(self, metrics: ResourceMetrics) -> Tuple[str, int]:
        """リアクティブスケーリング判断"""
        scale_up_signals = 0
        scale_down_signals = 0

        # CPU基準
        if metrics.cpu_usage > self.policy.cpu_scale_up_threshold:
            scale_up_signals += 2
        elif metrics.cpu_usage < self.policy.cpu_scale_down_threshold:
            scale_down_signals += 1

        # メモリ基準
        if metrics.memory_usage > self.policy.memory_scale_up_threshold:
            scale_up_signals += 2
        elif metrics.memory_usage < self.policy.memory_scale_down_threshold:
            scale_down_signals += 1

        # RPS基準
        if metrics.requests_per_second > self.policy.requests_per_second_scale_up:
            scale_up_signals += 1
        elif metrics.requests_per_second < self.policy.requests_per_second_scale_down:
            scale_down_signals += 1

        # レイテンシ基準
        if metrics.latency_p99 > self.policy.latency_scale_up_p99:
            scale_up_signals += 2
        elif metrics.latency_p99 < self.policy.latency_scale_down_p99:
            scale_down_signals += 1

        # 判断
        if scale_up_signals >= 3:
            new_replicas = min(
                self.current_replicas + self.policy.scale_up_increment,
                self.policy.max_replicas
            )
            return ('scale_up', new_replicas)
        elif scale_down_signals >= 3 and scale_up_signals == 0:
            new_replicas = max(
                self.current_replicas - self.policy.scale_down_increment,
                self.policy.min_replicas
            )
            return ('scale_down', new_replicas)

        return ('no_change', self.current_replicas)

    def _predictive_decision(self, metrics: ResourceMetrics,
                           predictions: Optional[Dict[str, float]]) -> Tuple[str, int]:
        """予測的スケーリング判断"""
        if not predictions:
            return self._reactive_decision(metrics)

        # 予測値に基づく判断
        predicted_cpu = predictions.get('cpu', metrics.cpu_usage)
        predicted_memory = predictions.get('memory', metrics.memory_usage)
        predicted_rps = predictions.get('rps', metrics.requests_per_second)
        predicted_latency = predictions.get('latency', metrics.latency_p99)

        # 必要レプリカ数の計算
        cpu_required = math.ceil(
            (predicted_cpu / self.policy.cpu_target_utilization) * self.current_replicas
        )
        memory_required = math.ceil(
            (predicted_memory / self.policy.memory_target_utilization) * self.current_replicas
        )
        rps_required = math.ceil(
            predicted_rps / self.policy.requests_per_second_target
        )

        target_replicas = max(cpu_required, memory_required, rps_required)
        target_replicas = max(min(target_replicas, self.policy.max_replicas),
                             self.policy.min_replicas)

        if target_replicas > self.current_replicas:
            return ('scale_up', target_replicas)
        elif target_replicas < self.current_replicas:
            return ('scale_down', target_replicas)

        return ('no_change', self.current_replicas)

    def _scheduled_decision(self) -> Tuple[str, int]:
        """スケジュールベーススケーリング判断"""
        current_hour = datetime.utcnow().hour

        # ビジネスアワー設定（例）
        if 9 <= current_hour < 18:  # 9:00-18:00
            target = max(10, self.policy.min_replicas)
        elif 18 <= current_hour < 22:  # 18:00-22:00 (ピーク時間)
            target = max(15, self.policy.min_replicas)
        else:  # 夜間
            target = self.policy.min_replicas

        if target > self.current_replicas:
            return ('scale_up', target)
        elif target < self.current_replicas:
            return ('scale_down', target)

        return ('no_change', self.current_replicas)

    def _hybrid_decision(self, metrics: ResourceMetrics,
                        predictions: Optional[Dict[str, float]]) -> Tuple[str, int]:
        """ハイブリッドスケーリング判断"""
        # 複数の戦略を組み合わせ
        reactive_action, reactive_target = self._reactive_decision(metrics)
        predictive_action, predictive_target = self._predictive_decision(metrics, predictions)
        scheduled_action, scheduled_target = self._scheduled_decision()

        # 最も積極的なスケーリングを採用
        if reactive_action == 'scale_up' or predictive_action == 'scale_up':
            target = max(reactive_target, predictive_target)
            return ('scale_up', target)
        elif scheduled_action == 'scale_up':
            return ('scale_up', scheduled_target)
        elif reactive_action == 'scale_down' and predictive_action != 'scale_up':
            target = min(reactive_target, predictive_target)
            return ('scale_down', target)

        return ('no_change', self.current_replicas)

    def update_state(self, action: str, replicas: int):
        """状態更新"""
        self.last_scale_action = action
        self.last_scale_time = datetime.utcnow()
        self.current_replicas = replicas


class AutoScaler:
    """自動スケーラー統合クラス"""

    def __init__(self, policy: ScalingPolicy):
        self.policy = policy
        self.metrics_collector = MetricsCollector()
        self.predictive_scaler = PredictiveScaler()
        self.decision_engine = ScalingDecisionEngine(policy)
        self.running = False
        self.logger = logging.getLogger(__name__)

    async def start(self):
        """自動スケーリング開始"""
        self.running = True
        self.logger.info("AutoScaler started")

        while self.running:
            try:
                # メトリクス収集
                metrics = self.metrics_collector.collect()
                self.predictive_scaler.add_data_point(metrics)

                # 予測
                predictions = None
                if self.policy.strategy in [ScalingStrategy.PREDICTIVE, ScalingStrategy.HYBRID]:
                    predictions = self.predictive_scaler.predict_load()

                # スケーリング判断
                action, target_replicas = self.decision_engine.decide(metrics, predictions)

                if action != 'no_change':
                    await self._execute_scaling(action, target_replicas)
                    self.decision_engine.update_state(action, target_replicas)

                # ログ記録
                self.logger.info(
                    f"Scaling Decision: {action}, Current: {self.decision_engine.current_replicas}, "
                    f"Target: {target_replicas}, CPU: {metrics.cpu_usage:.1f}%, "
                    f"Memory: {metrics.memory_usage:.1f}%, RPS: {metrics.requests_per_second:.1f}"
                )

            except Exception as e:
                self.logger.error(f"AutoScaler error: {e}")

            await asyncio.sleep(30)  # 30秒間隔でチェック

    async def stop(self):
        """自動スケーリング停止"""
        self.running = False
        self.logger.info("AutoScaler stopped")

    async def _execute_scaling(self, action: str, target_replicas: int):
        """スケーリング実行"""
        self.logger.info(f"Executing {action} to {target_replicas} replicas")

        # 実際の実装ではKubernetes APIやAWS Auto Scaling APIを呼び出す
        # kubectl scale deployment episode-factory --replicas={target_replicas}
        # or
        # aws autoscaling set-desired-capacity --auto-scaling-group-name episode-factory --desired-capacity {target_replicas}

        await asyncio.sleep(1)  # モック遅延


# 使用例
if __name__ == "__main__":
    import asyncio

    # ポリシー設定
    policy = ScalingPolicy(
        name="episode-factory-autoscaling",
        strategy=ScalingStrategy.HYBRID,
        min_replicas=2,
        max_replicas=20,
        cpu_target_utilization=70.0,
        memory_target_utilization=75.0,
        requests_per_second_target=100.0
    )

    # 自動スケーラー起動
    async def main():
        scaler = AutoScaler(policy)

        # 10秒間のデモ実行
        task = asyncio.create_task(scaler.start())
        await asyncio.sleep(10)
        await scaler.stop()
        task.cancel()

    asyncio.run(main())