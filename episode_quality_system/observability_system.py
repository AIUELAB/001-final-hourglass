#!/usr/bin/env python3
"""
観測可能性（Observability）システム
分散トレーシング、構造化ログ、カスタムメトリクスの実装
"""

import time
import json
import logging
import uuid
import functools
from typing import Any, Dict, Optional, Callable, List
from dataclasses import dataclass, asdict, field
from datetime import datetime
from contextlib import contextmanager
from enum import Enum
import traceback

# OpenTelemetry imports
try:
    from opentelemetry import trace, metrics
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.exporter.prometheus import PrometheusMetricExporter
    from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    print("⚠️ OpenTelemetry not installed. Tracing disabled.")


class LogLevel(Enum):
    """ログレベル定義"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class MetricType(Enum):
    """メトリクスタイプ定義"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class TraceContext:
    """トレースコンテキスト"""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    baggage: Dict[str, Any] = field(default_factory=dict)
    start_time: float = field(default_factory=time.time)


@dataclass
class LogEntry:
    """構造化ログエントリ"""
    timestamp: str
    level: str
    message: str
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    service: str = "episode-factory"
    version: str = "2.0.0"
    environment: str = "production"
    attributes: Dict[str, Any] = field(default_factory=dict)
    error: Optional[Dict[str, Any]] = None


class StructuredLogger:
    """構造化ログシステム"""

    def __init__(self, service_name: str = "episode-factory"):
        self.service_name = service_name
        self.logger = logging.getLogger(service_name)
        self._setup_json_handler()

    def _setup_json_handler(self):
        """JSON形式のログハンドラー設定"""
        handler = logging.StreamHandler()
        handler.setFormatter(self.JSONFormatter())
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    class JSONFormatter(logging.Formatter):
        """JSON形式のログフォーマッター"""

        def format(self, record: logging.LogRecord) -> str:
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "level": record.levelname,
                "message": record.getMessage(),
                "logger": record.name,
                "file": record.filename,
                "line": record.lineno,
                "function": record.funcName,
                "thread": record.thread,
                "thread_name": record.threadName,
                "process": record.process,
            }

            # トレース情報を追加
            if hasattr(record, 'trace_id'):
                log_entry["trace_id"] = record.trace_id
            if hasattr(record, 'span_id'):
                log_entry["span_id"] = record.span_id

            # エラー情報を追加
            if record.exc_info:
                log_entry["error"] = {
                    "type": record.exc_info[0].__name__,
                    "message": str(record.exc_info[1]),
                    "stacktrace": traceback.format_exception(*record.exc_info)
                }

            # カスタム属性を追加
            if hasattr(record, 'attributes'):
                log_entry["attributes"] = record.attributes

            return json.dumps(log_entry, ensure_ascii=False)

    def log(self, level: LogLevel, message: str, **attributes):
        """構造化ログ出力"""
        log_method = getattr(self.logger, level.value.lower())

        # 現在のトレースコンテキストを取得
        if OTEL_AVAILABLE:
            span = trace.get_current_span()
            if span and span.is_recording():
                context = span.get_span_context()
                extra = {
                    'trace_id': format(context.trace_id, '032x'),
                    'span_id': format(context.span_id, '016x'),
                    'attributes': attributes
                }
            else:
                extra = {'attributes': attributes}
        else:
            extra = {'attributes': attributes}

        log_method(message, extra=extra)

    def debug(self, message: str, **attributes):
        self.log(LogLevel.DEBUG, message, **attributes)

    def info(self, message: str, **attributes):
        self.log(LogLevel.INFO, message, **attributes)

    def warning(self, message: str, **attributes):
        self.log(LogLevel.WARNING, message, **attributes)

    def error(self, message: str, exception: Optional[Exception] = None, **attributes):
        if exception:
            attributes['error_type'] = type(exception).__name__
            attributes['error_message'] = str(exception)
        self.log(LogLevel.ERROR, message, **attributes)

    def critical(self, message: str, **attributes):
        self.log(LogLevel.CRITICAL, message, **attributes)


class DistributedTracer:
    """分散トレーシングシステム"""

    def __init__(self, service_name: str = "episode-factory",
                 jaeger_host: str = "localhost",
                 jaeger_port: int = 6831):
        self.service_name = service_name
        self.tracer = None

        if OTEL_AVAILABLE:
            self._initialize_tracer(jaeger_host, jaeger_port)

    def _initialize_tracer(self, jaeger_host: str, jaeger_port: int):
        """トレーサーの初期化"""
        resource = Resource.create({
            "service.name": self.service_name,
            "service.version": "2.0.0",
            "deployment.environment": "production"
        })

        # Jaegerエクスポーター設定
        jaeger_exporter = JaegerExporter(
            agent_host_name=jaeger_host,
            agent_port=jaeger_port,
        )

        # TracerProvider設定
        provider = TracerProvider(resource=resource)
        processor = BatchSpanProcessor(jaeger_exporter)
        provider.add_span_processor(processor)

        # グローバルTracerProvider設定
        trace.set_tracer_provider(provider)
        self.tracer = trace.get_tracer(self.service_name)

    @contextmanager
    def trace_operation(self, operation_name: str, **attributes):
        """オペレーションのトレーシング"""
        if not OTEL_AVAILABLE or not self.tracer:
            yield None
            return

        with self.tracer.start_as_current_span(operation_name) as span:
            # 属性を設定
            for key, value in attributes.items():
                span.set_attribute(key, str(value))

            try:
                yield span
            except Exception as e:
                # エラー情報を記録
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise

    def trace_function(self, func: Callable) -> Callable:
        """関数デコレータとしてのトレーシング"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            operation_name = f"{func.__module__}.{func.__name__}"

            with self.trace_operation(operation_name) as span:
                # 関数の引数を属性として記録
                if span:
                    span.set_attribute("function.module", func.__module__)
                    span.set_attribute("function.name", func.__name__)

                result = func(*args, **kwargs)

                # 結果のサイズを記録
                if span and result:
                    if hasattr(result, '__len__'):
                        span.set_attribute("result.size", len(result))

                return result

        return wrapper


class MetricsCollector:
    """カスタムメトリクス収集システム"""

    def __init__(self, service_name: str = "episode-factory"):
        self.service_name = service_name
        self.metrics = {}
        self.meter = None

        if OTEL_AVAILABLE:
            self._initialize_metrics()

    def _initialize_metrics(self):
        """メトリクスプロバイダーの初期化"""
        # Prometheusエクスポーター
        prometheus_exporter = PrometheusMetricExporter(port=9090)

        # MeterProvider設定
        reader = PeriodicExportingMetricReader(
            exporter=prometheus_exporter,
            export_interval_millis=10000
        )

        provider = MeterProvider(
            resource=Resource.create({
                "service.name": self.service_name
            }),
            metric_readers=[reader]
        )

        metrics.set_meter_provider(provider)
        self.meter = metrics.get_meter(self.service_name)

        # 基本メトリクスを作成
        self._create_default_metrics()

    def _create_default_metrics(self):
        """デフォルトメトリクスの作成"""
        if not self.meter:
            return

        # カウンター
        self.metrics['request_count'] = self.meter.create_counter(
            name="episode_factory_requests_total",
            description="Total number of requests",
            unit="1"
        )

        self.metrics['error_count'] = self.meter.create_counter(
            name="episode_factory_errors_total",
            description="Total number of errors",
            unit="1"
        )

        # ゲージ
        self.metrics['active_requests'] = self.meter.create_up_down_counter(
            name="episode_factory_active_requests",
            description="Number of active requests",
            unit="1"
        )

        # ヒストグラム
        self.metrics['response_time'] = self.meter.create_histogram(
            name="episode_factory_response_time_seconds",
            description="Response time in seconds",
            unit="s"
        )

        self.metrics['quality_score'] = self.meter.create_histogram(
            name="episode_factory_quality_score",
            description="Episode quality score",
            unit="1"
        )

    def increment_counter(self, name: str, value: float = 1.0, **labels):
        """カウンターをインクリメント"""
        if name in self.metrics:
            self.metrics[name].add(value, labels)

    def set_gauge(self, name: str, value: float, **labels):
        """ゲージ値を設定"""
        if name in self.metrics:
            self.metrics[name].add(value, labels)

    def record_histogram(self, name: str, value: float, **labels):
        """ヒストグラム値を記録"""
        if name in self.metrics:
            self.metrics[name].record(value, labels)

    @contextmanager
    def measure_time(self, metric_name: str = "response_time", **labels):
        """時間計測コンテキストマネージャー"""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.record_histogram(metric_name, duration, **labels)


class SLICollector:
    """SLI（Service Level Indicator）収集"""

    def __init__(self):
        self.sli_metrics = {
            'availability': [],
            'latency': [],
            'error_rate': [],
            'throughput': []
        }

    def record_request(self, success: bool, latency_ms: float):
        """リクエストを記録"""
        timestamp = datetime.utcnow()

        # 可用性
        self.sli_metrics['availability'].append({
            'timestamp': timestamp,
            'success': success
        })

        # レイテンシ
        self.sli_metrics['latency'].append({
            'timestamp': timestamp,
            'value': latency_ms
        })

        # エラー率
        if not success:
            self.sli_metrics['error_rate'].append({
                'timestamp': timestamp,
                'error': True
            })

    def calculate_sli(self, window_minutes: int = 5) -> Dict[str, float]:
        """SLI計算"""
        now = datetime.utcnow()
        window_start = now.timestamp() - (window_minutes * 60)

        # 可用性計算
        recent_availability = [
            m for m in self.sli_metrics['availability']
            if m['timestamp'].timestamp() > window_start
        ]
        availability = (
            sum(1 for m in recent_availability if m['success']) /
            len(recent_availability) * 100
        ) if recent_availability else 100.0

        # レイテンシ計算（P95）
        recent_latency = [
            m['value'] for m in self.sli_metrics['latency']
            if m['timestamp'].timestamp() > window_start
        ]
        p95_latency = self._calculate_percentile(recent_latency, 95) if recent_latency else 0

        # エラー率計算
        recent_errors = [
            m for m in self.sli_metrics['error_rate']
            if m['timestamp'].timestamp() > window_start
        ]
        error_rate = (len(recent_errors) / len(recent_availability) * 100) if recent_availability else 0

        # スループット計算
        throughput = len(recent_availability) / (window_minutes * 60) if window_minutes > 0 else 0

        return {
            'availability': availability,
            'p95_latency_ms': p95_latency,
            'error_rate': error_rate,
            'throughput_rps': throughput
        }

    def _calculate_percentile(self, values: List[float], percentile: int) -> float:
        """パーセンタイル計算"""
        if not values:
            return 0
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]


class ObservabilityIntegration:
    """観測可能性統合クラス"""

    def __init__(self, service_name: str = "episode-factory"):
        self.logger = StructuredLogger(service_name)
        self.tracer = DistributedTracer(service_name)
        self.metrics = MetricsCollector(service_name)
        self.sli_collector = SLICollector()

    @contextmanager
    def observe_operation(self, operation_name: str, **attributes):
        """オペレーション全体の観測"""
        # ロギング
        self.logger.info(f"Starting operation: {operation_name}",
                        operation=operation_name, **attributes)

        # メトリクス
        self.metrics.increment_counter('request_count',
                                      operation=operation_name)
        self.metrics.set_gauge('active_requests', 1)

        # トレーシング
        with self.tracer.trace_operation(operation_name, **attributes) as span:
            start_time = time.time()
            success = False

            try:
                yield span
                success = True
                self.logger.info(f"Completed operation: {operation_name}")

            except Exception as e:
                self.logger.error(f"Failed operation: {operation_name}",
                                 exception=e)
                self.metrics.increment_counter('error_count',
                                             operation=operation_name)
                raise

            finally:
                # 実行時間記録
                duration = (time.time() - start_time) * 1000
                self.metrics.record_histogram('response_time', duration / 1000,
                                            operation=operation_name)

                # SLI記録
                self.sli_collector.record_request(success, duration)

                # アクティブリクエスト減少
                self.metrics.set_gauge('active_requests', -1)

    def get_health_status(self) -> Dict[str, Any]:
        """ヘルスステータス取得"""
        sli = self.sli_collector.calculate_sli()

        return {
            'status': 'healthy' if sli['availability'] >= 99.9 else 'degraded',
            'sli': sli,
            'timestamp': datetime.utcnow().isoformat()
        }


# 使用例：エピソードファクトリへの統合
class ObservableEpisodeFactory:
    """観測可能性を統合したエピソードファクトリ"""

    def __init__(self):
        self.observability = ObservabilityIntegration("episode-factory")

    def generate_episode(self, person_name: str, age: int) -> str:
        """観測可能なエピソード生成"""
        with self.observability.observe_operation(
            "generate_episode",
            person_name=person_name,
            age=age
        ):
            # 実際のエピソード生成処理
            time.sleep(0.01)  # シミュレート

            # 品質スコアを記録
            quality_score = 95.0 + 5.0 * (0.5 - time.time() % 1)
            self.observability.metrics.record_histogram(
                'quality_score',
                quality_score,
                person=person_name
            )

            episode = f"{person_name}（{age}歳）のエピソード"

            self.observability.logger.info(
                "Episode generated successfully",
                person=person_name,
                age=age,
                quality_score=quality_score,
                episode_length=len(episode)
            )

            return episode


def main():
    """デモ実行"""
    print("🔍 観測可能性システムデモ")
    print("=" * 50)

    factory = ObservableEpisodeFactory()

    # テスト実行
    for i in range(5):
        try:
            episode = factory.generate_episode(f"テスト太郎{i}", 30 + i)
            print(f"✅ Generated: {episode}")
        except Exception as e:
            print(f"❌ Error: {e}")

    # ヘルスステータス表示
    health = factory.observability.get_health_status()
    print("\n📊 Health Status:")
    print(json.dumps(health, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
