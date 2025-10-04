#!/usr/bin/env python3
"""
Prometheus Metrics Exporter for Multi-Agent Quality System
Phase 4 - Production Monitoring
"""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY
from prometheus_client.core import CollectorRegistry
from aiohttp import web
import asyncio
import time
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

# メトリクス定義
class QualitySystemMetrics:
    def __init__(self):
        # カウンターメトリクス
        self.episode_processed = Counter(
            'quality_episodes_processed_total',
            'Total number of episodes processed',
            ['agent', 'status']
        )

        self.consensus_decisions = Counter(
            'quality_consensus_decisions_total',
            'Total consensus decisions made',
            ['method', 'result']
        )

        self.api_requests = Counter(
            'quality_api_requests_total',
            'Total API requests',
            ['endpoint', 'method', 'status']
        )

        # ヒストグラムメトリクス
        self.processing_time = Histogram(
            'quality_processing_duration_seconds',
            'Episode processing duration',
            ['agent'],
            buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        )

        self.consensus_time = Histogram(
            'quality_consensus_duration_seconds',
            'Consensus formation duration',
            ['method'],
            buckets=[0.05, 0.1, 0.25, 0.5, 1.0]
        )

        self.ml_prediction_time = Histogram(
            'quality_ml_prediction_duration_seconds',
            'ML model prediction duration',
            buckets=[0.01, 0.025, 0.05, 0.1, 0.25]
        )

        # ゲージメトリクス
        self.active_agents = Gauge(
            'quality_active_agents',
            'Number of active agents',
            ['type']
        )

        self.consensus_confidence = Gauge(
            'quality_consensus_confidence',
            'Current consensus confidence score'
        )

        self.ml_model_accuracy = Gauge(
            'quality_ml_model_accuracy',
            'Current ML model accuracy'
        )

        self.cache_hit_rate = Gauge(
            'quality_cache_hit_rate',
            'Cache hit rate percentage'
        )

        self.queue_size = Gauge(
            'quality_queue_size',
            'Current queue size',
            ['queue_name']
        )

        self.error_rate = Gauge(
            'quality_error_rate',
            'Current error rate per minute'
        )

        # システムメトリクス
        self.memory_usage = Gauge(
            'quality_memory_usage_bytes',
            'Memory usage in bytes',
            ['component']
        )

        self.cpu_usage = Gauge(
            'quality_cpu_usage_percent',
            'CPU usage percentage',
            ['component']
        )

class MetricsExporter:
    """メトリクスエクスポーター"""

    def __init__(self, port: int = 9090):
        self.port = port
        self.metrics = QualitySystemMetrics()
        self.app = web.Application()
        self.setup_routes()

    def setup_routes(self):
        """ルート設定"""
        self.app.router.add_get('/metrics', self.handle_metrics)
        self.app.router.add_get('/health', self.handle_health)

    async def handle_metrics(self, request: web.Request) -> web.Response:
        """メトリクスエンドポイント"""
        try:
            # サンプルメトリクス更新（実際にはシステムから取得）
            await self.update_sample_metrics()

            # メトリクス生成
            metrics_output = generate_latest(REGISTRY)
            return web.Response(
                text=metrics_output.decode('utf-8'),
                content_type='text/plain; version=0.0.4'
            )
        except Exception as e:
            logger.error(f"メトリクス生成エラー: {e}")
            return web.Response(status=500)

    async def handle_health(self, request: web.Request) -> web.Response:
        """ヘルスチェックエンドポイント"""
        return web.json_response({'status': 'healthy'})

    async def update_sample_metrics(self):
        """サンプルメトリクス更新（デモ用）"""
        import random

        # エピソード処理
        self.metrics.episode_processed.labels(
            agent='fact_checker',
            status='success'
        ).inc()

        # 処理時間
        self.metrics.processing_time.labels(
            agent='fact_checker'
        ).observe(random.uniform(0.1, 2.0))

        # コンセンサス
        self.metrics.consensus_decisions.labels(
            method='weighted',
            result='approved'
        ).inc()

        # アクティブエージェント
        self.metrics.active_agents.labels(type='fact_checker').set(1)
        self.metrics.active_agents.labels(type='quality_guard').set(1)
        self.metrics.active_agents.labels(type='semantic').set(1)
        self.metrics.active_agents.labels(type='code_analyzer').set(1)
        self.metrics.active_agents.labels(type='security').set(1)

        # 信頼度スコア
        self.metrics.consensus_confidence.set(random.uniform(0.7, 1.0))

        # MLモデル精度
        self.metrics.ml_model_accuracy.set(random.uniform(0.85, 0.95))

        # キャッシュヒット率
        self.metrics.cache_hit_rate.set(random.uniform(60, 90))

        # キューサイズ
        self.metrics.queue_size.labels(queue_name='episodes').set(
            random.randint(0, 100)
        )

        # エラー率
        self.metrics.error_rate.set(random.uniform(0, 5))

    def record_episode_processing(
        self,
        agent: str,
        status: str,
        duration: float
    ):
        """エピソード処理記録"""
        self.metrics.episode_processed.labels(
            agent=agent,
            status=status
        ).inc()

        self.metrics.processing_time.labels(
            agent=agent
        ).observe(duration)

    def record_consensus_decision(
        self,
        method: str,
        result: str,
        duration: float,
        confidence: float
    ):
        """コンセンサス決定記録"""
        self.metrics.consensus_decisions.labels(
            method=method,
            result=result
        ).inc()

        self.metrics.consensus_time.labels(
            method=method
        ).observe(duration)

        self.metrics.consensus_confidence.set(confidence)

    def record_api_request(
        self,
        endpoint: str,
        method: str,
        status: int
    ):
        """APIリクエスト記録"""
        self.metrics.api_requests.labels(
            endpoint=endpoint,
            method=method,
            status=str(status)
        ).inc()

    def update_ml_metrics(
        self,
        accuracy: float,
        prediction_time: float
    ):
        """機械学習メトリクス更新"""
        self.metrics.ml_model_accuracy.set(accuracy)
        self.metrics.ml_prediction_time.observe(prediction_time)

    def update_system_metrics(
        self,
        component: str,
        memory_bytes: int,
        cpu_percent: float
    ):
        """システムメトリクス更新"""
        self.metrics.memory_usage.labels(
            component=component
        ).set(memory_bytes)

        self.metrics.cpu_usage.labels(
            component=component
        ).set(cpu_percent)

    async def start(self):
        """エクスポーター起動"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', self.port)
        await site.start()
        logger.info(f"Prometheus exporter started on port {self.port}")

        # 無限ループで待機
        while True:
            await asyncio.sleep(3600)

async def main():
    """メイン処理"""
    logging.basicConfig(level=logging.INFO)

    exporter = MetricsExporter()

    print("="*60)
    print("📊 Prometheus Metrics Exporter")
    print("="*60)
    print(f"Starting on port {exporter.port}")
    print(f"Metrics endpoint: http://localhost:{exporter.port}/metrics")
    print(f"Health endpoint: http://localhost:{exporter.port}/health")

    try:
        await exporter.start()
    except KeyboardInterrupt:
        print("\n⚠️ Shutting down...")

if __name__ == "__main__":
    asyncio.run(main())