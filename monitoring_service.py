#!/usr/bin/env python3
"""
運用監視サービス
リアルタイムメトリクス収集、アラート、ヘルスチェック
"""

import asyncio
import psutil
import time
import json
from datetime import datetime, timedelta
from pathlib import Path
import logging
from typing import Dict, List, Optional
import aiohttp
from collections import deque
import statistics

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)
logger = logging.getLogger(__name__)


class MonitoringService:
    """監視サービスクラス"""
    
    def __init__(self):
        """初期化"""
        self.metrics = {
            'system': deque(maxlen=1000),
            'application': deque(maxlen=1000),
            'api': deque(maxlen=1000),
            'errors': deque(maxlen=100)
        }
        
        self.thresholds = {
            'cpu_percent': 80,
            'memory_percent': 85,
            'disk_percent': 90,
            'error_rate': 5,
            'response_time': 10,
            'api_failure_rate': 10
        }
        
        self.alerts = []
        self.health_status = 'healthy'
        
    async def collect_system_metrics(self):
        """システムメトリクス収集"""
        while True:
            try:
                metrics = {
                    'timestamp': datetime.now().isoformat(),
                    'cpu_percent': psutil.cpu_percent(interval=1),
                    'memory_percent': psutil.virtual_memory().percent,
                    'disk_percent': psutil.disk_usage('/').percent,
                    'network_io': {
                        'bytes_sent': psutil.net_io_counters().bytes_sent,
                        'bytes_recv': psutil.net_io_counters().bytes_recv
                    },
                    'process_count': len(psutil.pids())
                }
                
                self.metrics['system'].append(metrics)
                
                # 閾値チェック
                await self.check_system_thresholds(metrics)
                
                logger.debug(f"System metrics: CPU={metrics['cpu_percent']}%, "
                           f"Memory={metrics['memory_percent']}%")
                
            except Exception as e:
                logger.error(f"System metrics collection error: {e}")
            
            await asyncio.sleep(30)  # 30秒ごと
    
    async def collect_application_metrics(self):
        """アプリケーションメトリクス収集"""
        while True:
            try:
                # ログファイルから処理統計を取得
                log_files = list(Path('logs').glob('production_*.log'))
                if log_files:
                    latest_log = max(log_files, key=lambda p: p.stat().st_mtime)
                    
                    metrics = await self.parse_application_logs(latest_log)
                    metrics['timestamp'] = datetime.now().isoformat()
                    
                    self.metrics['application'].append(metrics)
                    
                    # エラー率チェック
                    if metrics['error_rate'] > self.thresholds['error_rate']:
                        await self.create_alert(
                            'HIGH_ERROR_RATE',
                            f"Error rate {metrics['error_rate']}% exceeds threshold",
                            'critical'
                        )
                
            except Exception as e:
                logger.error(f"Application metrics collection error: {e}")
            
            await asyncio.sleep(60)  # 1分ごと
    
    async def parse_application_logs(self, log_file: Path) -> Dict:
        """ログファイル解析"""
        metrics = {
            'processed_count': 0,
            'success_count': 0,
            'error_count': 0,
            'error_rate': 0,
            'avg_processing_time': 0,
            'cache_hit_rate': 0
        }
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()[-1000:]  # 最新1000行
                
                for line in lines:
                    if '処理完了' in line:
                        metrics['processed_count'] += 1
                    elif '成功' in line:
                        metrics['success_count'] += 1
                    elif 'ERROR' in line or '失敗' in line:
                        metrics['error_count'] += 1
                        self.metrics['errors'].append({
                            'timestamp': datetime.now().isoformat(),
                            'message': line.strip()
                        })
                
                # エラー率計算
                if metrics['processed_count'] > 0:
                    metrics['error_rate'] = (
                        metrics['error_count'] / metrics['processed_count'] * 100
                    )
                
        except Exception as e:
            logger.error(f"Log parsing error: {e}")
        
        return metrics
    
    async def check_api_health(self):
        """APIヘルスチェック"""
        api_endpoints = {
            'google': 'https://www.googleapis.com/customsearch/v1',
            'youtube': 'https://www.googleapis.com/youtube/v3',
            'twitter': 'https://api.twitter.com/2',
            'news': 'https://newsapi.org/v2',
            'brave': 'https://api.search.brave.com/res/v1'
        }
        
        while True:
            try:
                health_results = {}
                
                async with aiohttp.ClientSession() as session:
                    for name, url in api_endpoints.items():
                        try:
                            start_time = time.time()
                            async with session.head(url, timeout=5) as response:
                                response_time = time.time() - start_time
                                
                                health_results[name] = {
                                    'status': 'healthy' if response.status < 500 else 'unhealthy',
                                    'response_time': response_time,
                                    'status_code': response.status
                                }
                        except Exception as e:
                            health_results[name] = {
                                'status': 'unhealthy',
                                'error': str(e)
                            }
                
                # メトリクス保存
                self.metrics['api'].append({
                    'timestamp': datetime.now().isoformat(),
                    'health': health_results
                })
                
                # 失敗率チェック
                unhealthy_count = sum(
                    1 for r in health_results.values() 
                    if r['status'] == 'unhealthy'
                )
                
                if unhealthy_count > len(api_endpoints) * 0.5:
                    await self.create_alert(
                        'API_HEALTH_CRITICAL',
                        f"{unhealthy_count}/{len(api_endpoints)} APIs are unhealthy",
                        'critical'
                    )
                
            except Exception as e:
                logger.error(f"API health check error: {e}")
            
            await asyncio.sleep(300)  # 5分ごと
    
    async def check_system_thresholds(self, metrics: Dict):
        """システム閾値チェック"""
        # CPU使用率
        if metrics['cpu_percent'] > self.thresholds['cpu_percent']:
            await self.create_alert(
                'HIGH_CPU',
                f"CPU usage {metrics['cpu_percent']}% exceeds threshold",
                'warning'
            )
        
        # メモリ使用率
        if metrics['memory_percent'] > self.thresholds['memory_percent']:
            await self.create_alert(
                'HIGH_MEMORY',
                f"Memory usage {metrics['memory_percent']}% exceeds threshold",
                'warning'
            )
        
        # ディスク使用率
        if metrics['disk_percent'] > self.thresholds['disk_percent']:
            await self.create_alert(
                'HIGH_DISK',
                f"Disk usage {metrics['disk_percent']}% exceeds threshold",
                'critical'
            )
    
    async def create_alert(self, alert_type: str, message: str, severity: str):
        """アラート作成"""
        alert = {
            'id': f"{alert_type}_{int(time.time())}",
            'type': alert_type,
            'message': message,
            'severity': severity,
            'timestamp': datetime.now().isoformat(),
            'resolved': False
        }
        
        self.alerts.append(alert)
        logger.warning(f"🚨 Alert: [{severity}] {message}")
        
        # 通知送信
        await self.send_notification(alert)
    
    async def send_notification(self, alert: Dict):
        """通知送信"""
        # Slack通知
        if alert['severity'] == 'critical':
            await self.send_slack_notification(alert)
        
        # メール通知
        if alert['severity'] in ['critical', 'warning']:
            await self.send_email_notification(alert)
    
    async def send_slack_notification(self, alert: Dict):
        """Slack通知"""
        webhook_url = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
        
        payload = {
            'text': f"🚨 *{alert['severity'].upper()} Alert*",
            'attachments': [{
                'color': 'danger' if alert['severity'] == 'critical' else 'warning',
                'fields': [
                    {'title': 'Type', 'value': alert['type'], 'short': True},
                    {'title': 'Time', 'value': alert['timestamp'], 'short': True},
                    {'title': 'Message', 'value': alert['message'], 'short': False}
                ]
            }]
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status == 200:
                        logger.info("Slack notification sent")
        except Exception as e:
            logger.error(f"Slack notification error: {e}")
    
    async def send_email_notification(self, alert: Dict):
        """メール通知（簡略版）"""
        logger.info(f"Email notification would be sent: {alert['message']}")
    
    def get_health_status(self) -> Dict:
        """ヘルスステータス取得"""
        # 最新のメトリクスから状態判定
        issues = []
        
        if self.metrics['system']:
            latest_system = self.metrics['system'][-1]
            if latest_system['cpu_percent'] > self.thresholds['cpu_percent']:
                issues.append('High CPU usage')
            if latest_system['memory_percent'] > self.thresholds['memory_percent']:
                issues.append('High memory usage')
        
        if self.metrics['application']:
            latest_app = self.metrics['application'][-1]
            if latest_app['error_rate'] > self.thresholds['error_rate']:
                issues.append('High error rate')
        
        # 未解決のクリティカルアラート
        critical_alerts = [
            a for a in self.alerts 
            if a['severity'] == 'critical' and not a['resolved']
        ]
        
        if critical_alerts:
            issues.append(f"{len(critical_alerts)} critical alerts")
        
        # ステータス判定
        if issues:
            self.health_status = 'unhealthy' if critical_alerts else 'degraded'
        else:
            self.health_status = 'healthy'
        
        return {
            'status': self.health_status,
            'issues': issues,
            'metrics_summary': self.get_metrics_summary(),
            'active_alerts': len([a for a in self.alerts if not a['resolved']]),
            'timestamp': datetime.now().isoformat()
        }
    
    def get_metrics_summary(self) -> Dict:
        """メトリクスサマリー取得"""
        summary = {}
        
        # システムメトリクス平均
        if self.metrics['system']:
            recent_system = list(self.metrics['system'])[-10:]
            summary['avg_cpu'] = statistics.mean(
                [m['cpu_percent'] for m in recent_system]
            )
            summary['avg_memory'] = statistics.mean(
                [m['memory_percent'] for m in recent_system]
            )
        
        # アプリケーションメトリクス
        if self.metrics['application']:
            recent_app = list(self.metrics['application'])[-10:]
            summary['total_processed'] = sum(
                [m['processed_count'] for m in recent_app]
            )
            summary['avg_error_rate'] = statistics.mean(
                [m['error_rate'] for m in recent_app]
            )
        
        # API健全性
        if self.metrics['api']:
            latest_api = self.metrics['api'][-1]
            healthy_apis = sum(
                1 for api in latest_api['health'].values() 
                if api['status'] == 'healthy'
            )
            summary['api_health_percentage'] = (
                healthy_apis / len(latest_api['health']) * 100
            )
        
        return summary
    
    async def export_metrics(self, output_file: str = 'monitoring_metrics.json'):
        """メトリクスエクスポート"""
        export_data = {
            'timestamp': datetime.now().isoformat(),
            'health_status': self.get_health_status(),
            'metrics': {
                'system': list(self.metrics['system'])[-100:],
                'application': list(self.metrics['application'])[-100:],
                'api': list(self.metrics['api'])[-20:],
                'errors': list(self.metrics['errors'])
            },
            'alerts': self.alerts[-50:],
            'thresholds': self.thresholds
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Metrics exported to {output_file}")
    
    async def run(self):
        """監視サービス実行"""
        logger.info("🔍 Monitoring service started")
        
        # 並行タスク起動
        tasks = [
            asyncio.create_task(self.collect_system_metrics()),
            asyncio.create_task(self.collect_application_metrics()),
            asyncio.create_task(self.check_api_health()),
            asyncio.create_task(self.periodic_export())
        ]
        
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            logger.info("Monitoring service stopped")
        except Exception as e:
            logger.error(f"Monitoring service error: {e}")
    
    async def periodic_export(self):
        """定期的なメトリクスエクスポート"""
        while True:
            await asyncio.sleep(3600)  # 1時間ごと
            await self.export_metrics()


# HTTPエンドポイント（オプション）
from aiohttp import web

async def health_endpoint(request):
    """ヘルスチェックエンドポイント"""
    service = request.app['monitoring_service']
    health = service.get_health_status()
    
    status_code = 200 if health['status'] == 'healthy' else 503
    
    return web.json_response(health, status=status_code)

async def metrics_endpoint(request):
    """メトリクスエンドポイント"""
    service = request.app['monitoring_service']
    
    metrics = {
        'system': list(service.metrics['system'])[-10:],
        'application': list(service.metrics['application'])[-10:],
        'api': list(service.metrics['api'])[-5:]
    }
    
    return web.json_response(metrics)

async def alerts_endpoint(request):
    """アラートエンドポイント"""
    service = request.app['monitoring_service']
    
    active_alerts = [
        a for a in service.alerts 
        if not a['resolved']
    ]
    
    return web.json_response({'alerts': active_alerts})


def create_app():
    """Webアプリケーション作成"""
    app = web.Application()
    
    # 監視サービス初期化
    monitoring_service = MonitoringService()
    app['monitoring_service'] = monitoring_service
    
    # ルート設定
    app.router.add_get('/health', health_endpoint)
    app.router.add_get('/metrics', metrics_endpoint)
    app.router.add_get('/alerts', alerts_endpoint)
    
    return app


async def main():
    """メイン実行"""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--web':
        # Webサーバーモード
        app = create_app()
        runner = web.AppRunner(app)
        await runner.setup()
        
        site = web.TCPSite(runner, 'localhost', 8080)
        await site.start()
        
        logger.info("Monitoring web server started at http://localhost:8080")
        
        # 監視サービス実行
        await app['monitoring_service'].run()
    else:
        # スタンドアロンモード
        service = MonitoringService()
        await service.run()


if __name__ == "__main__":
    asyncio.run(main())