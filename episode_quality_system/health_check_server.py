#!/usr/bin/env python3
"""
ヘルスチェックサーバー
統一エピソードファクトリv2の健全性を監視
"""

import json
import time
import psutil
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timedelta
from typing import Dict, Any, List
import os
import sys

# プロダクションパスを追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from unified_episode_factory_v2 import UnifiedEpisodeFactory, EpisodeGenerationRequest


class HealthStatus:
    """システム健全性ステータス管理"""

    def __init__(self):
        self.start_time = datetime.now()
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0
        self.last_request_time = None
        self.last_error = None
        self.response_times = []
        self.max_response_times = 100  # 最新100件を保持

    def record_request(self, success: bool, response_time_ms: float, error: str = None):
        """リクエストを記録"""
        self.request_count += 1
        self.last_request_time = datetime.now()

        if success:
            self.success_count += 1
        else:
            self.error_count += 1
            self.last_error = error

        # レスポンスタイムを記録
        self.response_times.append(response_time_ms)
        if len(self.response_times) > self.max_response_times:
            self.response_times.pop(0)

    def get_status(self) -> Dict[str, Any]:
        """現在のステータスを取得"""
        uptime = datetime.now() - self.start_time
        success_rate = (self.success_count / self.request_count * 100) if self.request_count > 0 else 100

        # レスポンスタイム統計
        if self.response_times:
            avg_response = sum(self.response_times) / len(self.response_times)
            p95_response = sorted(self.response_times)[int(len(self.response_times) * 0.95)]
            p99_response = sorted(self.response_times)[int(len(self.response_times) * 0.99)]
        else:
            avg_response = p95_response = p99_response = 0

        return {
            "status": "healthy" if success_rate >= 95 else "degraded" if success_rate >= 80 else "unhealthy",
            "uptime_seconds": int(uptime.total_seconds()),
            "request_count": self.request_count,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": round(success_rate, 2),
            "avg_response_time_ms": round(avg_response, 2),
            "p95_response_time_ms": round(p95_response, 2),
            "p99_response_time_ms": round(p99_response, 2),
            "last_request_time": self.last_request_time.isoformat() if self.last_request_time else None,
            "last_error": self.last_error
        }


class SystemMonitor:
    """システムリソース監視"""

    @staticmethod
    def get_system_metrics() -> Dict[str, Any]:
        """システムメトリクスを取得"""
        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=1)

        # メモリ使用率
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used_mb = memory.used / (1024 * 1024)
        memory_available_mb = memory.available / (1024 * 1024)

        # ディスク使用率
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        disk_free_gb = disk.free / (1024 * 1024 * 1024)

        # プロセス情報
        process = psutil.Process()
        process_cpu = process.cpu_percent()
        process_memory = process.memory_info().rss / (1024 * 1024)  # MB
        process_threads = process.num_threads()

        return {
            "system": {
                "cpu_percent": round(cpu_percent, 2),
                "memory_percent": round(memory_percent, 2),
                "memory_used_mb": round(memory_used_mb, 2),
                "memory_available_mb": round(memory_available_mb, 2),
                "disk_percent": round(disk_percent, 2),
                "disk_free_gb": round(disk_free_gb, 2)
            },
            "process": {
                "cpu_percent": round(process_cpu, 2),
                "memory_mb": round(process_memory, 2),
                "thread_count": process_threads
            }
        }


class FactoryHealthChecker:
    """エピソードファクトリの健全性チェック"""

    def __init__(self):
        self.factory = None
        self.factory_initialized = False
        self.initialization_error = None

        # ファクトリの初期化を試みる
        self._initialize_factory()

    def _initialize_factory(self):
        """ファクトリを初期化"""
        try:
            self.factory = UnifiedEpisodeFactory(use_optimized=True)
            self.factory_initialized = True
        except Exception as e:
            self.initialization_error = str(e)
            self.factory_initialized = False

    def check_factory_health(self) -> Dict[str, Any]:
        """ファクトリの健全性をチェック"""
        if not self.factory_initialized:
            return {
                "healthy": False,
                "error": f"Factory initialization failed: {self.initialization_error}"
            }

        # テストエピソード生成
        try:
            start_time = time.time()

            request = EpisodeGenerationRequest(
                person_name="テスト太郎",
                age=30,
                category="test",
                min_quality_score=70.0,
                max_attempts=1
            )

            response = self.factory.generate(request)
            elapsed_ms = (time.time() - start_time) * 1000

            return {
                "healthy": response.success,
                "response_time_ms": round(elapsed_ms, 2),
                "quality_score": response.quality_score if response.success else 0,
                "error": response.error_message if not response.success else None
            }

        except Exception as e:
            return {
                "healthy": False,
                "error": str(e)
            }

    def check_dependencies(self) -> Dict[str, Any]:
        """依存関係をチェック"""
        dependencies = {}

        # 必要なファイルの存在チェック
        required_files = [
            "unified_episode_factory_v2.py",
            "optimized_validation_system.py",
            "expanded_episode_templates.py",
            "mandatory_pipeline.py",
            "complete_person_facts.json"
        ]

        for file in required_files:
            dependencies[file] = os.path.exists(file)

        # データベースのチェック
        if os.path.exists("complete_person_facts.json"):
            try:
                with open("complete_person_facts.json", 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    person_count = len(data.get("persons", {}))
                    dependencies["database_persons"] = person_count
                    dependencies["database_valid"] = True
            except Exception:
                dependencies["database_valid"] = False
        else:
            dependencies["database_valid"] = False

        return dependencies


# グローバル変数
health_status = HealthStatus()
system_monitor = SystemMonitor()
factory_checker = FactoryHealthChecker()


class HealthCheckHandler(BaseHTTPRequestHandler):
    """HTTPハンドラー"""

    def do_GET(self):
        """GETリクエスト処理"""
        if self.path == '/health':
            self._handle_health_check()
        elif self.path == '/metrics':
            self._handle_metrics()
        elif self.path == '/ready':
            self._handle_readiness()
        elif self.path == '/live':
            self._handle_liveness()
        else:
            self.send_error(404, "Not Found")

    def _handle_health_check(self):
        """総合ヘルスチェック"""
        # ファクトリチェック
        factory_health = factory_checker.check_factory_health()

        # レスポンスタイム記録
        if factory_health["healthy"]:
            health_status.record_request(
                True,
                factory_health.get("response_time_ms", 0)
            )
        else:
            health_status.record_request(
                False,
                0,
                factory_health.get("error", "Unknown error")
            )

        # ステータス取得
        status = health_status.get_status()
        system_metrics = system_monitor.get_system_metrics()
        dependencies = factory_checker.check_dependencies()

        # 総合判定
        overall_healthy = (
            status["status"] == "healthy" and
            factory_health["healthy"] and
            all(dependencies.values() if isinstance(dependencies, dict) else [])
        )

        response = {
            "healthy": overall_healthy,
            "timestamp": datetime.now().isoformat(),
            "version": "2.0.0",
            "service": "episode-factory",
            "status": status,
            "factory": factory_health,
            "system": system_metrics,
            "dependencies": dependencies
        }

        # レスポンス送信
        self.send_response(200 if overall_healthy else 503)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response, ensure_ascii=False, indent=2).encode('utf-8'))

    def _handle_metrics(self):
        """Prometheus形式のメトリクス"""
        metrics = []

        # アプリケーションメトリクス
        status = health_status.get_status()
        metrics.append(f'episode_factory_uptime_seconds {status["uptime_seconds"]}')
        metrics.append(f'episode_factory_request_total {status["request_count"]}')
        metrics.append(f'episode_factory_success_total {status["success_count"]}')
        metrics.append(f'episode_factory_error_total {status["error_count"]}')
        metrics.append(f'episode_factory_success_rate {status["success_rate"]}')
        metrics.append(f'episode_factory_response_time_avg_ms {status["avg_response_time_ms"]}')
        metrics.append(f'episode_factory_response_time_p95_ms {status["p95_response_time_ms"]}')
        metrics.append(f'episode_factory_response_time_p99_ms {status["p99_response_time_ms"]}')

        # システムメトリクス
        system_metrics = system_monitor.get_system_metrics()
        metrics.append(f'system_cpu_percent {system_metrics["system"]["cpu_percent"]}')
        metrics.append(f'system_memory_percent {system_metrics["system"]["memory_percent"]}')
        metrics.append(f'system_disk_percent {system_metrics["system"]["disk_percent"]}')
        metrics.append(f'process_cpu_percent {system_metrics["process"]["cpu_percent"]}')
        metrics.append(f'process_memory_mb {system_metrics["process"]["memory_mb"]}')
        metrics.append(f'process_thread_count {system_metrics["process"]["thread_count"]}')

        # レスポンス送信
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain; version=0.0.4')
        self.end_headers()
        self.wfile.write('\n'.join(metrics).encode('utf-8'))

    def _handle_readiness(self):
        """Readinessプローブ（起動完了チェック）"""
        ready = factory_checker.factory_initialized

        self.send_response(200 if ready else 503)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()

        response = {
            "ready": ready,
            "timestamp": datetime.now().isoformat()
        }

        if not ready:
            response["error"] = factory_checker.initialization_error

        self.wfile.write(json.dumps(response).encode('utf-8'))

    def _handle_liveness(self):
        """Livenessプローブ（生存チェック）"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()

        response = {
            "alive": True,
            "timestamp": datetime.now().isoformat()
        }

        self.wfile.write(json.dumps(response).encode('utf-8'))

    def log_message(self, format, *args):
        """アクセスログを抑制（必要に応じて有効化）"""
        pass


def run_health_check_server(port: int = 8000):
    """ヘルスチェックサーバーを起動"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, HealthCheckHandler)

    print(f"🏥 ヘルスチェックサーバー起動")
    print(f"📍 ポート: {port}")
    print(f"🔗 エンドポイント:")
    print(f"  - http://localhost:{port}/health  (総合ヘルスチェック)")
    print(f"  - http://localhost:{port}/metrics (Prometheusメトリクス)")
    print(f"  - http://localhost:{port}/ready   (Readinessプローブ)")
    print(f"  - http://localhost:{port}/live    (Livenessプローブ)")
    print(f"\n⌨️  Ctrl+C で終了")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 ヘルスチェックサーバー停止")
        httpd.shutdown()


def main():
    """メイン処理"""
    import argparse

    parser = argparse.ArgumentParser(description='ヘルスチェックサーバー')
    parser.add_argument('--port', type=int, default=8000,
                       help='リスニングポート (default: 8000)')
    args = parser.parse_args()

    run_health_check_server(args.port)


if __name__ == "__main__":
    main()