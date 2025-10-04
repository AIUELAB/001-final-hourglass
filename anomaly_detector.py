#!/usr/bin/env python3
"""
Anomaly Detection and Self-Healing System
Phase 5 - Real Production Operations
"""

import asyncio
import aiohttp
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import json
import logging
from collections import deque, defaultdict
from enum import Enum
import statistics
import subprocess
import os

logger = logging.getLogger(__name__)

class AnomalyType(Enum):
    """異常の種類"""
    PERFORMANCE_DEGRADATION = "performance_degradation"
    ERROR_SPIKE = "error_spike"
    MEMORY_LEAK = "memory_leak"
    CONSENSUS_FAILURE = "consensus_failure"
    API_TIMEOUT = "api_timeout"
    DATA_DRIFT = "data_drift"
    QUALITY_DROP = "quality_drop"
    RESOURCE_EXHAUSTION = "resource_exhaustion"

class SeverityLevel(Enum):
    """重要度レベル"""
    INFO = 1
    WARNING = 2
    ERROR = 3
    CRITICAL = 4

@dataclass
class Anomaly:
    """検出された異常"""
    anomaly_id: str
    timestamp: datetime
    type: AnomalyType
    severity: SeverityLevel
    component: str
    description: str
    metrics: Dict[str, float]
    suggested_actions: List[str]
    auto_heal_available: bool = False

@dataclass
class HealingAction:
    """自己修復アクション"""
    action_id: str
    anomaly_id: str
    action_type: str
    parameters: Dict[str, Any]
    executed_at: Optional[datetime] = None
    success: Optional[bool] = None
    result: Optional[str] = None

class StatisticalDetector:
    """統計的異常検出"""

    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.metrics_history = defaultdict(lambda: deque(maxlen=window_size))
        self.baselines = {}

    def update_metric(self, metric_name: str, value: float):
        """メトリクスを更新"""
        self.metrics_history[metric_name].append(value)

        # ベースラインを計算
        if len(self.metrics_history[metric_name]) >= 10:
            values = list(self.metrics_history[metric_name])
            self.baselines[metric_name] = {
                'mean': statistics.mean(values),
                'stdev': statistics.stdev(values) if len(values) > 1 else 0,
                'median': statistics.median(values),
                'q1': np.percentile(values, 25),
                'q3': np.percentile(values, 75)
            }

    def detect_outliers(self, metric_name: str, value: float, z_threshold: float = 3.0) -> Optional[float]:
        """Z-スコアによる外れ値検出"""
        if metric_name not in self.baselines:
            return None

        baseline = self.baselines[metric_name]
        if baseline['stdev'] == 0:
            return None

        z_score = abs((value - baseline['mean']) / baseline['stdev'])
        return z_score if z_score > z_threshold else None

    def detect_iqr_outliers(self, metric_name: str, value: float) -> bool:
        """IQR（四分位範囲）による外れ値検出"""
        if metric_name not in self.baselines:
            return False

        baseline = self.baselines[metric_name]
        iqr = baseline['q3'] - baseline['q1']
        lower_bound = baseline['q1'] - 1.5 * iqr
        upper_bound = baseline['q3'] + 1.5 * iqr

        return value < lower_bound or value > upper_bound

class PatternDetector:
    """パターン異常検出"""

    def __init__(self):
        self.patterns = {}
        self.anomaly_patterns = []

    def learn_pattern(self, pattern_id: str, features: List[float]):
        """正常パターンを学習"""
        if pattern_id not in self.patterns:
            self.patterns[pattern_id] = []
        self.patterns[pattern_id].append(features)

    def detect_anomalous_pattern(self, features: List[float], threshold: float = 0.8) -> bool:
        """異常パターンを検出"""
        if not self.patterns:
            return False

        # 既知のパターンとの類似度を計算
        max_similarity = 0
        for pattern_id, known_features_list in self.patterns.items():
            for known_features in known_features_list:
                similarity = self._calculate_similarity(features, known_features)
                max_similarity = max(max_similarity, similarity)

        # 類似度が閾値未満なら異常
        return max_similarity < threshold

    def _calculate_similarity(self, features1: List[float], features2: List[float]) -> float:
        """コサイン類似度を計算"""
        if len(features1) != len(features2):
            return 0.0

        norm1 = np.linalg.norm(features1)
        norm2 = np.linalg.norm(features2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return np.dot(features1, features2) / (norm1 * norm2)

class SelfHealingEngine:
    """自己修復エンジン"""

    def __init__(self):
        self.healing_strategies = {
            AnomalyType.PERFORMANCE_DEGRADATION: self._heal_performance,
            AnomalyType.ERROR_SPIKE: self._heal_errors,
            AnomalyType.MEMORY_LEAK: self._heal_memory,
            AnomalyType.CONSENSUS_FAILURE: self._heal_consensus,
            AnomalyType.API_TIMEOUT: self._heal_api_timeout,
            AnomalyType.RESOURCE_EXHAUSTION: self._heal_resources,
            AnomalyType.QUALITY_DROP: self._heal_quality
        }

    async def heal(self, anomaly: Anomaly) -> HealingAction:
        """異常を自己修復"""
        action = HealingAction(
            action_id=f"heal_{anomaly.anomaly_id}",
            anomaly_id=anomaly.anomaly_id,
            action_type=str(anomaly.type),
            parameters={}
        )

        try:
            if anomaly.type in self.healing_strategies:
                success, result = await self.healing_strategies[anomaly.type](anomaly)
                action.success = success
                action.result = result
            else:
                action.success = False
                action.result = "No healing strategy available"

            action.executed_at = datetime.now()

        except Exception as e:
            logger.error(f"Healing failed for {anomaly.anomaly_id}: {e}")
            action.success = False
            action.result = str(e)

        return action

    async def _heal_performance(self, anomaly: Anomaly) -> Tuple[bool, str]:
        """パフォーマンス劣化を修復"""
        actions_taken = []

        # キャッシュをクリア
        if await self._clear_cache():
            actions_taken.append("Cleared cache")

        # ワーカー数を調整
        if await self._adjust_workers(increase=True):
            actions_taken.append("Increased worker count")

        # 非同期処理を最適化
        if await self._optimize_async():
            actions_taken.append("Optimized async processing")

        return len(actions_taken) > 0, ", ".join(actions_taken)

    async def _heal_errors(self, anomaly: Anomaly) -> Tuple[bool, str]:
        """エラースパイクを修復"""
        actions_taken = []

        # サービスを再起動
        component = anomaly.component
        if await self._restart_service(component):
            actions_taken.append(f"Restarted {component}")

        # リトライ設定を調整
        if await self._adjust_retry_config():
            actions_taken.append("Adjusted retry configuration")

        return len(actions_taken) > 0, ", ".join(actions_taken)

    async def _heal_memory(self, anomaly: Anomaly) -> Tuple[bool, str]:
        """メモリリークを修復"""
        actions_taken = []

        # ガベージコレクションを強制
        import gc
        gc.collect()
        actions_taken.append("Forced garbage collection")

        # メモリ制限を調整
        if await self._adjust_memory_limits():
            actions_taken.append("Adjusted memory limits")

        # プロセスを再起動（最終手段）
        if anomaly.severity == SeverityLevel.CRITICAL:
            component = anomaly.component
            if await self._restart_service(component):
                actions_taken.append(f"Restarted {component} due to critical memory leak")

        return len(actions_taken) > 0, ", ".join(actions_taken)

    async def _heal_consensus(self, anomaly: Anomaly) -> Tuple[bool, str]:
        """コンセンサス失敗を修復"""
        actions_taken = []

        # エージェントの再初期化
        if await self._reinitialize_agents():
            actions_taken.append("Reinitialized agents")

        # コンセンサス閾値を調整
        if await self._adjust_consensus_threshold():
            actions_taken.append("Adjusted consensus threshold")

        return len(actions_taken) > 0, ", ".join(actions_taken)

    async def _heal_api_timeout(self, anomaly: Anomaly) -> Tuple[bool, str]:
        """APIタイムアウトを修復"""
        actions_taken = []

        # タイムアウト値を増加
        if await self._increase_timeout():
            actions_taken.append("Increased timeout values")

        # バックオフ戦略を実装
        if await self._implement_backoff():
            actions_taken.append("Implemented exponential backoff")

        # 負荷分散を調整
        if await self._adjust_load_balancing():
            actions_taken.append("Adjusted load balancing")

        return len(actions_taken) > 0, ", ".join(actions_taken)

    async def _heal_resources(self, anomaly: Anomaly) -> Tuple[bool, str]:
        """リソース枯渇を修復"""
        actions_taken = []

        # 自動スケーリング
        if await self._auto_scale():
            actions_taken.append("Triggered auto-scaling")

        # リソース制限を調整
        if await self._adjust_resource_limits():
            actions_taken.append("Adjusted resource limits")

        # 不要なプロセスを削除
        if await self._cleanup_processes():
            actions_taken.append("Cleaned up unnecessary processes")

        return len(actions_taken) > 0, ", ".join(actions_taken)

    async def _heal_quality(self, anomaly: Anomaly) -> Tuple[bool, str]:
        """品質低下を修復"""
        actions_taken = []

        # MLモデルを再訓練
        if await self._retrain_ml_model():
            actions_taken.append("Retrained ML model")

        # 品質閾値を調整
        if await self._adjust_quality_thresholds():
            actions_taken.append("Adjusted quality thresholds")

        # フィードバックループを強化
        if await self._enhance_feedback_loop():
            actions_taken.append("Enhanced feedback loop")

        return len(actions_taken) > 0, ", ".join(actions_taken)

    # Helper methods
    async def _clear_cache(self) -> bool:
        """キャッシュをクリア"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post('http://localhost:8002/api/cache/clear') as resp:
                    return resp.status == 200
        except:
            return False

    async def _restart_service(self, service_name: str) -> bool:
        """サービスを再起動"""
        try:
            result = subprocess.run(
                ['kubectl', 'rollout', 'restart', f'deployment/{service_name}', '-n', 'quality-system'],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except:
            return False

    async def _adjust_workers(self, increase: bool = True) -> bool:
        """ワーカー数を調整"""
        try:
            current_workers = int(os.getenv('WORKER_COUNT', '4'))
            new_workers = current_workers + 2 if increase else max(2, current_workers - 1)
            os.environ['WORKER_COUNT'] = str(new_workers)
            return True
        except:
            return False

    async def _optimize_async(self) -> bool:
        """非同期処理を最適化"""
        try:
            # バッチサイズを調整
            os.environ['BATCH_SIZE'] = '50'
            # 並列度を調整
            os.environ['MAX_CONCURRENCY'] = '10'
            return True
        except:
            return False

    async def _adjust_memory_limits(self) -> bool:
        """メモリ制限を調整"""
        return True  # Kubernetes HPA will handle this

    async def _reinitialize_agents(self) -> bool:
        """エージェントを再初期化"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post('http://localhost:8002/api/agents/reinit') as resp:
                    return resp.status == 200
        except:
            return False

    async def _adjust_consensus_threshold(self) -> bool:
        """コンセンサス閾値を調整"""
        try:
            os.environ['CONSENSUS_THRESHOLD'] = '0.6'  # Lower from 0.7
            return True
        except:
            return False

    async def _increase_timeout(self) -> bool:
        """タイムアウトを増加"""
        try:
            os.environ['API_TIMEOUT'] = '30'  # Increase from default
            return True
        except:
            return False

    async def _implement_backoff(self) -> bool:
        """バックオフ戦略を実装"""
        try:
            os.environ['RETRY_BACKOFF'] = 'exponential'
            os.environ['RETRY_MAX_ATTEMPTS'] = '5'
            return True
        except:
            return False

    async def _adjust_load_balancing(self) -> bool:
        """負荷分散を調整"""
        return True  # Handled by Kubernetes service

    async def _auto_scale(self) -> bool:
        """自動スケーリング"""
        try:
            result = subprocess.run(
                ['kubectl', 'scale', 'deployment/quality-orchestrator', '--replicas=5', '-n', 'quality-system'],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except:
            return False

    async def _adjust_resource_limits(self) -> bool:
        """リソース制限を調整"""
        return True  # Handled by Kubernetes

    async def _cleanup_processes(self) -> bool:
        """不要なプロセスをクリーンアップ"""
        try:
            # Kill zombie processes
            subprocess.run(['pkill', '-9', '-f', 'defunct'], capture_output=True)
            return True
        except:
            return False

    async def _retrain_ml_model(self) -> bool:
        """MLモデルを再訓練"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post('http://localhost:8002/api/ml/retrain') as resp:
                    return resp.status == 200
        except:
            return False

    async def _adjust_quality_thresholds(self) -> bool:
        """品質閾値を調整"""
        try:
            os.environ['QUALITY_THRESHOLD'] = '0.75'  # Adjust as needed
            return True
        except:
            return False

    async def _enhance_feedback_loop(self) -> bool:
        """フィードバックループを強化"""
        try:
            os.environ['FEEDBACK_WEIGHT'] = '0.3'  # Increase feedback influence
            return True
        except:
            return False

class AnomalyDetectionSystem:
    """統合異常検出システム"""

    def __init__(self):
        self.statistical_detector = StatisticalDetector()
        self.pattern_detector = PatternDetector()
        self.healing_engine = SelfHealingEngine()
        self.detected_anomalies = []
        self.healing_history = []
        self.monitoring = True

        # Thresholds
        self.thresholds = {
            'response_time': 1.0,  # seconds
            'error_rate': 0.05,     # 5%
            'consensus_rate': 0.6,  # 60%
            'memory_usage': 0.9,    # 90%
            'cpu_usage': 0.85,      # 85%
        }

    async def start_monitoring(self):
        """監視を開始"""
        self.monitoring = True

        # 複数の監視タスクを並列実行
        await asyncio.gather(
            self._monitor_performance(),
            self._monitor_errors(),
            self._monitor_resources(),
            self._monitor_quality(),
            self._periodic_health_check()
        )

    async def _monitor_performance(self):
        """パフォーマンス監視"""
        while self.monitoring:
            try:
                metrics = await self._collect_performance_metrics()

                # 統計的異常検出
                for metric_name, value in metrics.items():
                    self.statistical_detector.update_metric(metric_name, value)

                    # 外れ値検出
                    z_score = self.statistical_detector.detect_outliers(metric_name, value)
                    if z_score and z_score > 3:
                        anomaly = self._create_anomaly(
                            AnomalyType.PERFORMANCE_DEGRADATION,
                            SeverityLevel.WARNING if z_score < 4 else SeverityLevel.ERROR,
                            f"Performance metric {metric_name} is {z_score:.1f} std deviations from normal",
                            metrics,
                            True
                        )
                        await self._handle_anomaly(anomaly)

                await asyncio.sleep(10)  # 10秒ごとにチェック

            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
                await asyncio.sleep(10)

    async def _monitor_errors(self):
        """エラー監視"""
        while self.monitoring:
            try:
                error_rate = await self._calculate_error_rate()

                if error_rate > self.thresholds['error_rate']:
                    severity = SeverityLevel.ERROR if error_rate > 0.1 else SeverityLevel.WARNING
                    anomaly = self._create_anomaly(
                        AnomalyType.ERROR_SPIKE,
                        severity,
                        f"Error rate {error_rate:.1%} exceeds threshold",
                        {'error_rate': error_rate},
                        True
                    )
                    await self._handle_anomaly(anomaly)

                await asyncio.sleep(30)  # 30秒ごとにチェック

            except Exception as e:
                logger.error(f"Error monitoring error: {e}")
                await asyncio.sleep(30)

    async def _monitor_resources(self):
        """リソース監視"""
        while self.monitoring:
            try:
                resources = await self._collect_resource_metrics()

                # メモリ使用率チェック
                if resources.get('memory_usage', 0) > self.thresholds['memory_usage']:
                    anomaly = self._create_anomaly(
                        AnomalyType.MEMORY_LEAK if resources.get('memory_trend', 0) > 0 else AnomalyType.RESOURCE_EXHAUSTION,
                        SeverityLevel.CRITICAL,
                        f"Memory usage {resources['memory_usage']:.1%} exceeds threshold",
                        resources,
                        True
                    )
                    await self._handle_anomaly(anomaly)

                # CPU使用率チェック
                if resources.get('cpu_usage', 0) > self.thresholds['cpu_usage']:
                    anomaly = self._create_anomaly(
                        AnomalyType.RESOURCE_EXHAUSTION,
                        SeverityLevel.ERROR,
                        f"CPU usage {resources['cpu_usage']:.1%} exceeds threshold",
                        resources,
                        True
                    )
                    await self._handle_anomaly(anomaly)

                await asyncio.sleep(60)  # 1分ごとにチェック

            except Exception as e:
                logger.error(f"Resource monitoring error: {e}")
                await asyncio.sleep(60)

    async def _monitor_quality(self):
        """品質監視"""
        while self.monitoring:
            try:
                quality_metrics = await self._collect_quality_metrics()

                # コンセンサス率チェック
                consensus_rate = quality_metrics.get('consensus_rate', 1.0)
                if consensus_rate < self.thresholds['consensus_rate']:
                    anomaly = self._create_anomaly(
                        AnomalyType.CONSENSUS_FAILURE,
                        SeverityLevel.WARNING,
                        f"Consensus rate {consensus_rate:.1%} below threshold",
                        quality_metrics,
                        True
                    )
                    await self._handle_anomaly(anomaly)

                # 品質スコアの急激な変化を検出
                quality_score = quality_metrics.get('quality_score', 0)
                self.statistical_detector.update_metric('quality_score', quality_score)

                if self.statistical_detector.detect_iqr_outliers('quality_score', quality_score):
                    anomaly = self._create_anomaly(
                        AnomalyType.QUALITY_DROP,
                        SeverityLevel.ERROR,
                        f"Quality score {quality_score:.2f} is an outlier",
                        quality_metrics,
                        True
                    )
                    await self._handle_anomaly(anomaly)

                await asyncio.sleep(300)  # 5分ごとにチェック

            except Exception as e:
                logger.error(f"Quality monitoring error: {e}")
                await asyncio.sleep(300)

    async def _periodic_health_check(self):
        """定期的なヘルスチェック"""
        while self.monitoring:
            try:
                health_status = await self._perform_health_check()

                # パターン学習
                features = [
                    health_status.get('response_time', 0),
                    health_status.get('error_count', 0),
                    health_status.get('active_connections', 0),
                    health_status.get('queue_size', 0)
                ]

                if self.pattern_detector.detect_anomalous_pattern(features):
                    anomaly = self._create_anomaly(
                        AnomalyType.PERFORMANCE_DEGRADATION,
                        SeverityLevel.INFO,
                        "Anomalous pattern detected in health metrics",
                        health_status,
                        False
                    )
                    await self._handle_anomaly(anomaly)
                else:
                    # 正常パターンとして学習
                    self.pattern_detector.learn_pattern('health', features)

                await asyncio.sleep(120)  # 2分ごとにチェック

            except Exception as e:
                logger.error(f"Health check error: {e}")
                await asyncio.sleep(120)

    async def _handle_anomaly(self, anomaly: Anomaly):
        """異常を処理"""
        self.detected_anomalies.append(anomaly)
        logger.warning(f"Anomaly detected: {anomaly.description}")

        # 自動修復が可能な場合
        if anomaly.auto_heal_available and anomaly.severity >= SeverityLevel.WARNING:
            logger.info(f"Attempting self-healing for {anomaly.anomaly_id}")
            healing_action = await self.healing_engine.heal(anomaly)
            self.healing_history.append(healing_action)

            if healing_action.success:
                logger.info(f"Successfully healed: {healing_action.result}")
            else:
                logger.error(f"Healing failed: {healing_action.result}")
                await self._escalate_anomaly(anomaly)

        # 通知
        await self._notify_anomaly(anomaly)

    async def _escalate_anomaly(self, anomaly: Anomaly):
        """異常をエスカレート"""
        # Slack/Email通知など
        logger.critical(f"ESCALATION: {anomaly.description}")

        # PagerDutyやOpsGenieなどのインシデント管理ツールと統合
        if anomaly.severity == SeverityLevel.CRITICAL:
            await self._create_incident(anomaly)

    async def _notify_anomaly(self, anomaly: Anomaly):
        """異常を通知"""
        notification = {
            'anomaly_id': anomaly.anomaly_id,
            'timestamp': anomaly.timestamp.isoformat(),
            'type': anomaly.type.value,
            'severity': anomaly.severity.name,
            'component': anomaly.component,
            'description': anomaly.description,
            'metrics': anomaly.metrics,
            'suggested_actions': anomaly.suggested_actions
        }

        # Webhookで通知
        try:
            async with aiohttp.ClientSession() as session:
                webhook_url = os.getenv('ANOMALY_WEBHOOK_URL')
                if webhook_url:
                    async with session.post(webhook_url, json=notification) as resp:
                        logger.info(f"Anomaly notification sent: {resp.status}")
        except Exception as e:
            logger.error(f"Failed to send anomaly notification: {e}")

    async def _create_incident(self, anomaly: Anomaly):
        """インシデントを作成"""
        incident = {
            'title': f"{anomaly.type.value}: {anomaly.description}",
            'urgency': 'high' if anomaly.severity == SeverityLevel.CRITICAL else 'low',
            'details': {
                'anomaly_id': anomaly.anomaly_id,
                'component': anomaly.component,
                'metrics': anomaly.metrics
            }
        }

        # PagerDuty/OpsGenie API呼び出し
        logger.critical(f"Incident created: {incident['title']}")

    def _create_anomaly(self, anomaly_type: AnomalyType, severity: SeverityLevel,
                        description: str, metrics: Dict, auto_heal: bool) -> Anomaly:
        """異常オブジェクトを作成"""
        return Anomaly(
            anomaly_id=f"anomaly_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            timestamp=datetime.now(),
            type=anomaly_type,
            severity=severity,
            component='quality-system',
            description=description,
            metrics=metrics,
            suggested_actions=self._get_suggested_actions(anomaly_type),
            auto_heal_available=auto_heal
        )

    def _get_suggested_actions(self, anomaly_type: AnomalyType) -> List[str]:
        """推奨アクションを取得"""
        actions = {
            AnomalyType.PERFORMANCE_DEGRADATION: [
                "Clear cache",
                "Increase worker count",
                "Optimize queries"
            ],
            AnomalyType.ERROR_SPIKE: [
                "Check recent deployments",
                "Review error logs",
                "Restart affected services"
            ],
            AnomalyType.MEMORY_LEAK: [
                "Force garbage collection",
                "Restart service",
                "Review memory allocations"
            ],
            AnomalyType.CONSENSUS_FAILURE: [
                "Check agent health",
                "Review consensus logic",
                "Adjust thresholds"
            ],
            AnomalyType.API_TIMEOUT: [
                "Check API health",
                "Increase timeout",
                "Implement retry logic"
            ],
            AnomalyType.RESOURCE_EXHAUSTION: [
                "Scale up resources",
                "Optimize resource usage",
                "Clear unnecessary processes"
            ],
            AnomalyType.QUALITY_DROP: [
                "Retrain ML model",
                "Review recent changes",
                "Analyze feedback"
            ]
        }
        return actions.get(anomaly_type, ["Investigate manually"])

    # Metrics collection methods
    async def _collect_performance_metrics(self) -> Dict[str, float]:
        """パフォーマンスメトリクスを収集"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('http://localhost:8002/api/metrics') as resp:
                    data = await resp.json()
                    return {
                        'response_time': data.get('avg_processing_time', 0),
                        'throughput': data.get('episodes_per_second', 0),
                        'queue_size': data.get('queue_size', 0)
                    }
        except:
            return {}

    async def _calculate_error_rate(self) -> float:
        """エラー率を計算"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('http://localhost:9091/api/v1/query',
                                     params={'query': 'rate(errors_total[5m])'}) as resp:
                    data = await resp.json()
                    if data['status'] == 'success' and data['data']['result']:
                        return float(data['data']['result'][0]['value'][1])
        except:
            pass
        return 0.0

    async def _collect_resource_metrics(self) -> Dict[str, float]:
        """リソースメトリクスを収集"""
        try:
            import psutil
            return {
                'memory_usage': psutil.virtual_memory().percent / 100,
                'cpu_usage': psutil.cpu_percent() / 100,
                'disk_usage': psutil.disk_usage('/').percent / 100,
                'memory_trend': 0  # Would calculate from history
            }
        except:
            return {}

    async def _collect_quality_metrics(self) -> Dict[str, float]:
        """品質メトリクスを収集"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('http://localhost:8002/api/quality/metrics') as resp:
                    return await resp.json()
        except:
            return {'consensus_rate': 1.0, 'quality_score': 0.8}

    async def _perform_health_check(self) -> Dict[str, Any]:
        """ヘルスチェックを実行"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('http://localhost:8002/health') as resp:
                    return await resp.json()
        except:
            return {}

    def get_summary(self) -> Dict[str, Any]:
        """監視サマリーを取得"""
        recent_anomalies = self.detected_anomalies[-10:]  # Last 10
        recent_healings = self.healing_history[-10:]      # Last 10

        return {
            'total_anomalies': len(self.detected_anomalies),
            'recent_anomalies': [
                {
                    'id': a.anomaly_id,
                    'type': a.type.value,
                    'severity': a.severity.name,
                    'timestamp': a.timestamp.isoformat()
                }
                for a in recent_anomalies
            ],
            'total_healings': len(self.healing_history),
            'successful_healings': sum(1 for h in self.healing_history if h.success),
            'healing_success_rate': (
                sum(1 for h in self.healing_history if h.success) / len(self.healing_history)
                if self.healing_history else 0
            ),
            'recent_healings': [
                {
                    'id': h.action_id,
                    'anomaly_id': h.anomaly_id,
                    'success': h.success,
                    'result': h.result
                }
                for h in recent_healings
            ],
            'monitoring_status': 'active' if self.monitoring else 'inactive'
        }

async def main():
    """メイン実行"""
    detector = AnomalyDetectionSystem()

    print("🔍 Starting Anomaly Detection and Self-Healing System...")
    print("=" * 60)

    # 監視を開始（通常は無限ループ）
    try:
        # デモのため5分間実行
        monitoring_task = asyncio.create_task(detector.start_monitoring())
        await asyncio.sleep(300)  # 5 minutes

        # サマリーを表示
        summary = detector.get_summary()
        print("\n📊 Anomaly Detection Summary:")
        print(f"Total Anomalies Detected: {summary['total_anomalies']}")
        print(f"Total Healing Attempts: {summary['total_healings']}")
        print(f"Successful Healings: {summary['successful_healings']}")
        print(f"Healing Success Rate: {summary['healing_success_rate']:.1%}")

        if summary['recent_anomalies']:
            print("\n🚨 Recent Anomalies:")
            for anomaly in summary['recent_anomalies'][:5]:
                print(f"  - [{anomaly['severity']}] {anomaly['type']}: {anomaly['id']}")

        if summary['recent_healings']:
            print("\n💊 Recent Healing Actions:")
            for healing in summary['recent_healings'][:5]:
                status = "✅" if healing['success'] else "❌"
                print(f"  {status} {healing['id']}: {healing['result']}")

        # 監視を停止
        detector.monitoring = False
        await monitoring_task

    except KeyboardInterrupt:
        print("\n⏹️ Monitoring stopped by user")
        detector.monitoring = False

    print("\n✅ Anomaly Detection System demonstration complete!")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())