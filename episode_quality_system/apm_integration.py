"""
APM (Application Performance Management) 統合システム

New Relic、Datadog、AppDynamics等の主要APMツールとの統合を提供。
エピソードファクトリのパフォーマンスとビジネスメトリクスを監視。
"""

import os
import json
import time
import asyncio
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import threading
from queue import Queue
import logging
import hashlib
from contextlib import contextmanager
from functools import wraps

# APMプロバイダー用のSDKインポート（オプショナル）
try:
    import newrelic.agent as newrelic_agent
    HAS_NEWRELIC = True
except ImportError:
    HAS_NEWRELIC = False

try:
    from datadog import initialize as dd_initialize, statsd
    from datadog_api_client import ApiClient, Configuration
    from datadog_api_client.v2.api.metrics_api import MetricsApi
    HAS_DATADOG = True
except ImportError:
    HAS_DATADOG = False

try:
    from appdynamicsrest import AppDynamicsClient
    HAS_APPDYNAMICS = True
except ImportError:
    HAS_APPDYNAMICS = False

# Elastic APM
try:
    from elasticapm import Client as ElasticAPMClient
    HAS_ELASTIC_APM = True
except ImportError:
    HAS_ELASTIC_APM = False


@dataclass
class APMConfig:
    """APM設定"""
    provider: str  # newrelic, datadog, appdynamics, elastic
    api_key: Optional[str] = None
    app_name: str = "episode-factory"
    environment: str = "production"
    service_name: str = "episode-factory"

    # Provider specific configs
    newrelic_license_key: Optional[str] = None
    datadog_api_key: Optional[str] = None
    datadog_app_key: Optional[str] = None
    appdynamics_account_name: Optional[str] = None
    appdynamics_controller_host: Optional[str] = None
    elastic_server_url: Optional[str] = None
    elastic_secret_token: Optional[str] = None

    # Common settings
    sample_rate: float = 1.0  # 1.0 = 100%
    flush_interval: int = 10  # seconds
    max_batch_size: int = 100
    debug: bool = False


class NewRelicIntegration:
    """New Relic APM統合"""

    def __init__(self, config: APMConfig):
        self.config = config
        self.enabled = HAS_NEWRELIC and config.newrelic_license_key

        if self.enabled:
            newrelic_agent.initialize(
                config_file=None,
                environment=config.environment,
                license_key=config.newrelic_license_key,
                app_name=config.app_name
            )

    @contextmanager
    def transaction(self, name: str, group: str = "Custom"):
        """トランザクション記録"""
        if self.enabled:
            with newrelic_agent.BackgroundTask(
                newrelic_agent.application(),
                name=name,
                group=group
            ):
                yield
        else:
            yield

    def record_metric(self, name: str, value: float):
        """カスタムメトリクス記録"""
        if self.enabled:
            newrelic_agent.record_custom_metric(f"Custom/{name}", value)

    def record_event(self, event_type: str, attributes: Dict[str, Any]):
        """カスタムイベント記録"""
        if self.enabled:
            newrelic_agent.record_custom_event(event_type, attributes)

    def add_custom_parameter(self, key: str, value: Any):
        """カスタムパラメータ追加"""
        if self.enabled:
            newrelic_agent.add_custom_parameter(key, value)


class DatadogIntegration:
    """Datadog APM統合"""

    def __init__(self, config: APMConfig):
        self.config = config
        self.enabled = HAS_DATADOG and config.datadog_api_key

        if self.enabled:
            dd_initialize(
                api_key=config.datadog_api_key,
                app_key=config.datadog_app_key,
                host_name=os.environ.get('DD_AGENT_HOST', 'localhost')
            )

    def increment(self, metric: str, value: int = 1, tags: List[str] = None):
        """カウンタメトリクス"""
        if self.enabled:
            statsd.increment(metric, value, tags=tags)

    def gauge(self, metric: str, value: float, tags: List[str] = None):
        """ゲージメトリクス"""
        if self.enabled:
            statsd.gauge(metric, value, tags=tags)

    def histogram(self, metric: str, value: float, tags: List[str] = None):
        """ヒストグラムメトリクス"""
        if self.enabled:
            statsd.histogram(metric, value, tags=tags)

    def timing(self, metric: str, value: float, tags: List[str] = None):
        """タイミングメトリクス"""
        if self.enabled:
            statsd.timing(metric, value, tags=tags)

    @contextmanager
    def timed(self, metric: str, tags: List[str] = None):
        """時間計測コンテキスト"""
        if self.enabled:
            with statsd.timed(metric, tags=tags):
                yield
        else:
            yield

    def event(self, title: str, text: str, tags: List[str] = None,
              alert_type: str = "info"):
        """イベント送信"""
        if self.enabled:
            statsd.event(title, text, tags=tags, alert_type=alert_type)


class AppDynamicsIntegration:
    """AppDynamics APM統合"""

    def __init__(self, config: APMConfig):
        self.config = config
        self.enabled = (HAS_APPDYNAMICS and
                       config.appdynamics_account_name and
                       config.appdynamics_controller_host)
        self.client = None

        if self.enabled:
            self.client = AppDynamicsClient(
                account=config.appdynamics_account_name,
                host=config.appdynamics_controller_host,
                port=443,
                ssl=True,
                api_token=config.api_key
            )

    def start_transaction(self, name: str) -> Optional[str]:
        """トランザクション開始"""
        if self.enabled:
            # AppDynamics固有の実装
            transaction_id = hashlib.md5(
                f"{name}_{time.time()}".encode()
            ).hexdigest()
            return transaction_id
        return None

    def end_transaction(self, transaction_id: str, status: str = "SUCCESS"):
        """トランザクション終了"""
        if self.enabled and transaction_id:
            # AppDynamics固有の実装
            pass

    def report_metric(self, metric_path: str, value: float):
        """メトリクス報告"""
        if self.enabled:
            # AppDynamics固有の実装
            pass


class ElasticAPMIntegration:
    """Elastic APM統合"""

    def __init__(self, config: APMConfig):
        self.config = config
        self.enabled = (HAS_ELASTIC_APM and
                       config.elastic_server_url)
        self.client = None

        if self.enabled:
            self.client = ElasticAPMClient({
                'SERVICE_NAME': config.service_name,
                'SERVER_URL': config.elastic_server_url,
                'SECRET_TOKEN': config.elastic_secret_token,
                'ENVIRONMENT': config.environment,
            })

    @contextmanager
    def capture_span(self, name: str, span_type: str = "custom"):
        """スパンキャプチャ"""
        if self.enabled and self.client:
            with self.client.capture_span(name, span_type=span_type):
                yield
        else:
            yield

    def capture_exception(self, exc_info=None):
        """例外キャプチャ"""
        if self.enabled and self.client:
            self.client.capture_exception(exc_info=exc_info)

    def capture_message(self, message: str, level: str = "info"):
        """メッセージキャプチャ"""
        if self.enabled and self.client:
            self.client.capture_message(message, level=level)


class UnifiedAPMManager:
    """統合APMマネージャー

    複数のAPMプロバイダーを統一インターフェースで管理
    """

    def __init__(self, config: APMConfig):
        self.config = config
        self.providers: Dict[str, Any] = {}

        # プロバイダー初期化
        self._initialize_providers()

        # メトリクスバッファ
        self.metrics_buffer = Queue()
        self.events_buffer = Queue()

        # バックグラウンドフラッシャー
        self._start_background_flusher()

        # ビジネスメトリクス収集器
        self.business_metrics = BusinessMetricsCollector(self)

    def _initialize_providers(self):
        """プロバイダー初期化"""
        if self.config.provider == "newrelic" or self.config.newrelic_license_key:
            self.providers['newrelic'] = NewRelicIntegration(self.config)

        if self.config.provider == "datadog" or self.config.datadog_api_key:
            self.providers['datadog'] = DatadogIntegration(self.config)

        if self.config.provider == "appdynamics" or self.config.appdynamics_account_name:
            self.providers['appdynamics'] = AppDynamicsIntegration(self.config)

        if self.config.provider == "elastic" or self.config.elastic_server_url:
            self.providers['elastic'] = ElasticAPMIntegration(self.config)

    def _start_background_flusher(self):
        """バックグラウンドフラッシャー起動"""
        def flusher():
            while True:
                time.sleep(self.config.flush_interval)
                self._flush_buffers()

        thread = threading.Thread(target=flusher, daemon=True)
        thread.start()

    def _flush_buffers(self):
        """バッファフラッシュ"""
        # メトリクスフラッシュ
        metrics_batch = []
        while not self.metrics_buffer.empty() and len(metrics_batch) < self.config.max_batch_size:
            metrics_batch.append(self.metrics_buffer.get())

        if metrics_batch:
            self._send_metrics_batch(metrics_batch)

        # イベントフラッシュ
        events_batch = []
        while not self.events_buffer.empty() and len(events_batch) < self.config.max_batch_size:
            events_batch.append(self.events_buffer.get())

        if events_batch:
            self._send_events_batch(events_batch)

    def _send_metrics_batch(self, metrics: List[Dict[str, Any]]):
        """メトリクスバッチ送信"""
        for metric in metrics:
            self.record_metric(
                metric['name'],
                metric['value'],
                metric.get('tags', []),
                immediate=True
            )

    def _send_events_batch(self, events: List[Dict[str, Any]]):
        """イベントバッチ送信"""
        for event in events:
            self.record_event(
                event['type'],
                event['attributes'],
                immediate=True
            )

    @contextmanager
    def transaction(self, name: str, transaction_type: str = "web"):
        """統合トランザクション"""
        start_time = time.time()
        transaction_id = None

        try:
            # New Relic
            if 'newrelic' in self.providers:
                with self.providers['newrelic'].transaction(name):
                    pass

            # AppDynamics
            if 'appdynamics' in self.providers:
                transaction_id = self.providers['appdynamics'].start_transaction(name)

            # Elastic APM
            if 'elastic' in self.providers:
                with self.providers['elastic'].capture_span(name):
                    pass

            yield

            # 成功メトリクス
            duration = time.time() - start_time
            self.record_metric(f"transaction.{name}.duration", duration)
            self.record_metric(f"transaction.{name}.success", 1)

        except Exception as e:
            # エラーメトリクス
            duration = time.time() - start_time
            self.record_metric(f"transaction.{name}.duration", duration)
            self.record_metric(f"transaction.{name}.error", 1)

            # 例外キャプチャ
            if 'elastic' in self.providers:
                self.providers['elastic'].capture_exception()

            raise

        finally:
            # AppDynamics終了
            if transaction_id and 'appdynamics' in self.providers:
                self.providers['appdynamics'].end_transaction(transaction_id)

    def record_metric(self, name: str, value: float,
                     tags: List[str] = None, immediate: bool = False):
        """統合メトリクス記録"""
        if not immediate:
            self.metrics_buffer.put({
                'name': name,
                'value': value,
                'tags': tags or []
            })
            return

        # New Relic
        if 'newrelic' in self.providers:
            self.providers['newrelic'].record_metric(name, value)

        # Datadog
        if 'datadog' in self.providers:
            self.providers['datadog'].gauge(
                f"{self.config.service_name}.{name}",
                value,
                tags=tags
            )

        # AppDynamics
        if 'appdynamics' in self.providers:
            self.providers['appdynamics'].report_metric(name, value)

    def record_event(self, event_type: str, attributes: Dict[str, Any],
                    immediate: bool = False):
        """統合イベント記録"""
        if not immediate:
            self.events_buffer.put({
                'type': event_type,
                'attributes': attributes
            })
            return

        # New Relic
        if 'newrelic' in self.providers:
            self.providers['newrelic'].record_event(event_type, attributes)

        # Datadog
        if 'datadog' in self.providers:
            self.providers['datadog'].event(
                event_type,
                json.dumps(attributes),
                tags=[f"{k}:{v}" for k, v in attributes.items()]
            )

    @contextmanager
    def timed(self, metric_name: str, tags: List[str] = None):
        """時間計測"""
        start_time = time.time()

        try:
            # Datadog
            if 'datadog' in self.providers:
                with self.providers['datadog'].timed(metric_name, tags=tags):
                    pass

            yield

        finally:
            duration = time.time() - start_time
            self.record_metric(f"{metric_name}.duration", duration, tags)

    def increment(self, metric_name: str, value: int = 1, tags: List[str] = None):
        """カウンタインクリメント"""
        # Datadog
        if 'datadog' in self.providers:
            self.providers['datadog'].increment(metric_name, value, tags)

        # その他のプロバイダー
        self.record_metric(f"{metric_name}.count", value, tags)


class BusinessMetricsCollector:
    """ビジネスメトリクス収集器

    エピソードファクトリ固有のビジネスメトリクスを収集
    """

    def __init__(self, apm_manager: UnifiedAPMManager):
        self.apm = apm_manager
        self.metrics_cache = {}

    def record_episode_generation(self,
                                 episode_id: str,
                                 character_count: int,
                                 quality_score: float,
                                 generation_time: float,
                                 person_name: str,
                                 category: str,
                                 validation_stages: List[str],
                                 success: bool):
        """エピソード生成メトリクス"""
        tags = [
            f"category:{category}",
            f"success:{success}",
            f"validation_stages:{len(validation_stages)}"
        ]

        # パフォーマンスメトリクス
        self.apm.record_metric("episode.generation_time", generation_time, tags)
        self.apm.record_metric("episode.character_count", character_count, tags)
        self.apm.record_metric("episode.quality_score", quality_score, tags)

        # 成功/失敗カウント
        if success:
            self.apm.increment("episode.success", tags=tags)
        else:
            self.apm.increment("episode.failure", tags=tags)

        # カテゴリ別メトリクス
        self.apm.increment(f"episode.category.{category}", tags=tags)

        # イベント記録
        self.apm.record_event("EpisodeGenerated", {
            "episode_id": episode_id,
            "person_name": person_name,
            "category": category,
            "character_count": character_count,
            "quality_score": quality_score,
            "generation_time": generation_time,
            "validation_stages": ",".join(validation_stages),
            "success": success
        })

    def record_validation_performance(self,
                                     validator_name: str,
                                     execution_time: float,
                                     passed: bool,
                                     error_message: Optional[str] = None):
        """バリデーション性能メトリクス"""
        tags = [
            f"validator:{validator_name}",
            f"passed:{passed}"
        ]

        self.apm.record_metric(f"validation.{validator_name}.time", execution_time, tags)

        if passed:
            self.apm.increment(f"validation.{validator_name}.pass", tags=tags)
        else:
            self.apm.increment(f"validation.{validator_name}.fail", tags=tags)
            if error_message:
                self.apm.record_event("ValidationFailed", {
                    "validator": validator_name,
                    "error": error_message
                })

    def record_database_operation(self,
                                 operation: str,
                                 table: str,
                                 duration: float,
                                 row_count: int,
                                 success: bool):
        """データベース操作メトリクス"""
        tags = [
            f"operation:{operation}",
            f"table:{table}",
            f"success:{success}"
        ]

        self.apm.record_metric(f"db.{operation}.duration", duration, tags)
        self.apm.record_metric(f"db.{operation}.rows", row_count, tags)

        if success:
            self.apm.increment(f"db.{operation}.success", tags=tags)
        else:
            self.apm.increment(f"db.{operation}.error", tags=tags)

    def record_api_call(self,
                       endpoint: str,
                       method: str,
                       status_code: int,
                       response_time: float,
                       payload_size: int):
        """API呼び出しメトリクス"""
        tags = [
            f"endpoint:{endpoint}",
            f"method:{method}",
            f"status:{status_code}",
            f"status_category:{status_code // 100}xx"
        ]

        self.apm.record_metric("api.response_time", response_time, tags)
        self.apm.record_metric("api.payload_size", payload_size, tags)
        self.apm.increment(f"api.status.{status_code}", tags=tags)

        # SLI用メトリクス
        if status_code < 500:
            self.apm.increment("api.success", tags=tags)
        else:
            self.apm.increment("api.error", tags=tags)

    def record_cache_operation(self,
                              operation: str,
                              hit: bool,
                              latency: float,
                              key: str):
        """キャッシュ操作メトリクス"""
        tags = [
            f"operation:{operation}",
            f"hit:{hit}"
        ]

        self.apm.record_metric(f"cache.{operation}.latency", latency, tags)

        if hit:
            self.apm.increment("cache.hit", tags=tags)
        else:
            self.apm.increment("cache.miss", tags=tags)

        # ヒット率計算
        self._update_hit_rate()

    def _update_hit_rate(self):
        """キャッシュヒット率更新"""
        if 'cache_hits' not in self.metrics_cache:
            self.metrics_cache['cache_hits'] = 0
            self.metrics_cache['cache_total'] = 0

        # 簡易的なヒット率計算（実際はAPMツール側で集計）
        self.metrics_cache['cache_total'] += 1
        hit_rate = self.metrics_cache['cache_hits'] / self.metrics_cache['cache_total']
        self.apm.record_metric("cache.hit_rate", hit_rate)


def apm_decorator(metric_name: str = None):
    """APMデコレータ

    関数の実行時間とエラー率を自動的に記録
    """
    def decorator(func: Callable):
        nonlocal metric_name
        if metric_name is None:
            metric_name = f"{func.__module__}.{func.__name__}"

        @wraps(func)
        def wrapper(*args, **kwargs):
            # APMマネージャーの取得（グローバルまたは引数から）
            apm = kwargs.pop('apm', None) or getattr(args[0], 'apm', None)

            if not apm or not isinstance(apm, UnifiedAPMManager):
                # APMなしで実行
                return func(*args, **kwargs)

            with apm.timed(metric_name):
                try:
                    result = func(*args, **kwargs)
                    apm.increment(f"{metric_name}.success")
                    return result
                except Exception as e:
                    apm.increment(f"{metric_name}.error")
                    raise

        return wrapper
    return decorator


# 使用例とテストコード
if __name__ == "__main__":
    # 設定
    config = APMConfig(
        provider="datadog",  # または newrelic, appdynamics, elastic
        datadog_api_key=os.environ.get("DD_API_KEY"),
        datadog_app_key=os.environ.get("DD_APP_KEY"),
        environment="development",
        debug=True
    )

    # APMマネージャー初期化
    apm = UnifiedAPMManager(config)

    # トランザクション例
    with apm.transaction("episode_generation", "custom"):
        # ビジネスメトリクス記録
        apm.business_metrics.record_episode_generation(
            episode_id="ep_001",
            character_count=150,
            quality_score=95.0,
            generation_time=0.5,
            person_name="大谷翔平",
            category="スポーツ選手",
            validation_stages=["pre_validation", "content_validation", "quality_check"],
            success=True
        )

    # API呼び出し記録
    apm.business_metrics.record_api_call(
        endpoint="/api/generate",
        method="POST",
        status_code=200,
        response_time=0.123,
        payload_size=1024
    )

    # キャッシュ操作
    apm.business_metrics.record_cache_operation(
        operation="get",
        hit=True,
        latency=0.001,
        key="person:ohtani"
    )

    print("APM統合システムの初期化と基本操作が完了しました")