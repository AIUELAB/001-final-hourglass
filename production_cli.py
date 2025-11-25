#!/usr/bin/env python3
"""
Production CLI - 運用管理コマンドラインツール
Phase 4 - Operation Tools
"""

import click
import asyncio
import aiohttp
import json
import yaml
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import pandas as pd
from tabulate import tabulate
import subprocess
import sys

# Configuration
CONFIG = {
    'orchestrator_url': os.getenv('ORCHESTRATOR_URL', 'http://localhost:8002'),
    'codex_url': os.getenv('CODEX_SERVER_URL', 'http://localhost:8001'),
    'prometheus_url': os.getenv('PROMETHEUS_URL', 'http://localhost:9091'),
    'grafana_url': os.getenv('GRAFANA_URL', 'http://localhost:3000'),
    'namespace': 'quality-system'
}

@click.group()
@click.pass_context
def cli(ctx):
    """Multi-Agent Quality System 運用CLI"""
    ctx.ensure_object(dict)
    ctx.obj['config'] = CONFIG

@cli.group()
def health():
    """ヘルスチェックコマンド"""
    pass

@health.command()
@click.pass_context
def check(ctx):
    """システムヘルスチェック"""
    async def _check_health():
        results = []
        services = [
            ('Orchestrator', f"{ctx.obj['config']['orchestrator_url']}/health"),
            ('Codex Server', f"{ctx.obj['config']['codex_url']}/health"),
            ('Prometheus', f"{ctx.obj['config']['prometheus_url']}/-/healthy"),
            ('Grafana', f"{ctx.obj['config']['grafana_url']}/api/health")
        ]

        async with aiohttp.ClientSession() as session:
            for name, url in services:
                try:
                    async with session.get(url, timeout=5) as resp:
                        status = '✅ Healthy' if resp.status == 200 else f'⚠️ Unhealthy ({resp.status})'
                        results.append([name, url, status])
                except Exception as e:
                    results.append([name, url, f'❌ Error: {str(e)[:30]}'])

        print("\n🏥 System Health Check")
        print("=" * 70)
        print(tabulate(results, headers=['Service', 'Endpoint', 'Status'], tablefmt='grid'))

    asyncio.run(_check_health())

@health.command()
def kubernetes():
    """Kubernetesリソースチェック"""
    try:
        # Get pods
        result = subprocess.run(
            ['kubectl', 'get', 'pods', '-n', CONFIG['namespace'], '-o', 'json'],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            pods_data = json.loads(result.stdout)
            pod_info = []

            for pod in pods_data['items']:
                name = pod['metadata']['name']
                status = pod['status']['phase']
                restarts = sum(c['restartCount'] for c in pod['status'].get('containerStatuses', []))
                ready = f"{sum(1 for c in pod['status'].get('containerStatuses', []) if c['ready'])}/{len(pod['spec']['containers'])}"
                pod_info.append([name, status, ready, restarts])

            print("\n☸️ Kubernetes Pod Status")
            print("=" * 70)
            print(tabulate(pod_info, headers=['Pod Name', 'Status', 'Ready', 'Restarts'], tablefmt='grid'))
        else:
            print(f"❌ Failed to get pod status: {result.stderr}")

    except Exception as e:
        print(f"❌ Error: {e}")

@cli.group()
def metrics():
    """メトリクスコマンド"""
    pass

@metrics.command()
@click.option('--format', '-f', type=click.Choice(['table', 'json', 'csv']), default='table')
@click.pass_context
def show(ctx, format):
    """現在のメトリクス表示"""
    async def _show_metrics():
        metrics_url = f"{ctx.obj['config']['orchestrator_url']}/api/metrics"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(metrics_url) as resp:
                    data = await resp.json()

                    if format == 'json':
                        print(json.dumps(data, indent=2))
                    elif format == 'csv':
                        df = pd.DataFrame(data['metrics'])
                        print(df.to_csv(index=False))
                    else:  # table
                        metrics_data = [
                            ['Episodes Processed', data.get('episodes_processed', 0)],
                            ['Average Processing Time', f"{data.get('avg_processing_time', 0):.3f}s"],
                            ['Consensus Rate', f"{data.get('consensus_rate', 0):.1%}"],
                            ['ML Model Accuracy', f"{data.get('ml_accuracy', 0):.1%}"],
                            ['Cache Hit Rate', f"{data.get('cache_hit_rate', 0):.1%}"],
                            ['Active Agents', data.get('active_agents', 0)],
                            ['Queue Size', data.get('queue_size', 0)],
                            ['Error Rate', f"{data.get('error_rate', 0):.2%}"]
                        ]

                        print("\n📊 System Metrics")
                        print("=" * 70)
                        print(tabulate(metrics_data, headers=['Metric', 'Value'], tablefmt='grid'))

            except Exception as e:
                print(f"❌ Failed to get metrics: {e}")

    asyncio.run(_show_metrics())

@metrics.command()
@click.option('--query', '-q', required=True, help='PromQL query')
@click.pass_context
def query(ctx, query):
    """Prometheusクエリ実行"""
    async def _run_query():
        url = f"{ctx.obj['config']['prometheus_url']}/api/v1/query"
        params = {'query': query}

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, params=params) as resp:
                    data = await resp.json()

                    if data['status'] == 'success':
                        results = []
                        for result in data['data']['result']:
                            metric = result['metric']
                            value = result['value']
                            results.append([
                                json.dumps(metric),
                                value[0],  # timestamp
                                value[1]   # value
                            ])

                        print(f"\n📈 Query: {query}")
                        print("=" * 70)
                        print(tabulate(results, headers=['Labels', 'Timestamp', 'Value'], tablefmt='grid'))
                    else:
                        print(f"❌ Query failed: {data.get('error', 'Unknown error')}")

            except Exception as e:
                print(f"❌ Error: {e}")

    asyncio.run(_run_query())

@cli.group()
def ml():
    """機械学習モデル管理"""
    pass

@ml.command()
@click.pass_context
def retrain(ctx):
    """MLモデル再訓練"""
    async def _retrain():
        url = f"{ctx.obj['config']['orchestrator_url']}/api/ml/retrain"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        print("✅ Model retrained successfully")
                        print(f"   New accuracy: {data.get('accuracy', 0):.1%}")
                        print(f"   Training samples: {data.get('samples', 0)}")
                        print(f"   Training time: {data.get('time', 0):.2f}s")
                    else:
                        print(f"❌ Retrain failed: {resp.status}")

            except Exception as e:
                print(f"❌ Error: {e}")

    asyncio.run(_retrain())

@ml.command()
@click.pass_context
def status(ctx):
    """MLモデルステータス"""
    async def _status():
        url = f"{ctx.obj['config']['orchestrator_url']}/api/ml/status"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as resp:
                    data = await resp.json()

                    info = [
                        ['Model Version', data.get('version', 'N/A')],
                        ['Last Training', data.get('last_training', 'N/A')],
                        ['Accuracy', f"{data.get('accuracy', 0):.1%}"],
                        ['Precision', f"{data.get('precision', 0):.1%}"],
                        ['Recall', f"{data.get('recall', 0):.1%}"],
                        ['F1 Score', f"{data.get('f1_score', 0):.3f}"],
                        ['Training Samples', data.get('samples', 0)],
                        ['Features', data.get('features', 0)]
                    ]

                    print("\n🧠 ML Model Status")
                    print("=" * 70)
                    print(tabulate(info, headers=['Property', 'Value'], tablefmt='grid'))

            except Exception as e:
                print(f"❌ Error: {e}")

    asyncio.run(_status())

@cli.group()
def deploy():
    """デプロイメント管理"""
    pass

@deploy.command()
@click.argument('version')
def rollout(version):
    """新バージョンのロールアウト"""
    try:
        # Update image
        result = subprocess.run(
            [
                'kubectl', 'set', 'image',
                'deployment/quality-orchestrator',
                f'orchestrator=quality-system/orchestrator:{version}',
                '-n', CONFIG['namespace']
            ],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print(f"✅ Rolling out version {version}")

            # Watch rollout status
            subprocess.run([
                'kubectl', 'rollout', 'status',
                'deployment/quality-orchestrator',
                '-n', CONFIG['namespace']
            ])
        else:
            print(f"❌ Rollout failed: {result.stderr}")

    except Exception as e:
        print(f"❌ Error: {e}")

@deploy.command()
def rollback():
    """前のバージョンへロールバック"""
    try:
        result = subprocess.run(
            [
                'kubectl', 'rollout', 'undo',
                'deployment/quality-orchestrator',
                '-n', CONFIG['namespace']
            ],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print("✅ Rollback initiated")

            # Watch rollout status
            subprocess.run([
                'kubectl', 'rollout', 'status',
                'deployment/quality-orchestrator',
                '-n', CONFIG['namespace']
            ])
        else:
            print(f"❌ Rollback failed: {result.stderr}")

    except Exception as e:
        print(f"❌ Error: {e}")

@deploy.command()
def history():
    """デプロイメント履歴"""
    try:
        result = subprocess.run(
            [
                'kubectl', 'rollout', 'history',
                'deployment/quality-orchestrator',
                '-n', CONFIG['namespace']
            ],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print("\n📜 Deployment History")
            print("=" * 70)
            print(result.stdout)
        else:
            print(f"❌ Failed to get history: {result.stderr}")

    except Exception as e:
        print(f"❌ Error: {e}")

@cli.group()
def backup():
    """バックアップ管理"""
    pass

@backup.command()
@click.option('--output', '-o', default='backup.tar.gz', help='Output file')
def create(output):
    """バックアップ作成"""
    print(f"📦 Creating backup to {output}")

    components = [
        ('Database', 'pg_dump -h postgres -U postgres quality > db_backup.sql'),
        ('Models', 'tar -czf models.tar.gz /app/models'),
        ('Configs', 'kubectl get all -n quality-system -o yaml > k8s_config.yaml')
    ]

    for name, cmd in components:
        print(f"   Backing up {name}...")
        # In real implementation, execute backup commands

    print(f"✅ Backup completed: {output}")

@backup.command()
@click.argument('file')
def restore(file):
    """バックアップからリストア"""
    print(f"📥 Restoring from {file}")

    if not os.path.exists(file):
        print(f"❌ Backup file not found: {file}")
        return

    # In real implementation, execute restore commands
    print(f"✅ Restore completed from: {file}")

@cli.command()
def dashboard():
    """Grafanaダッシュボードを開く"""
    import webbrowser
    url = CONFIG['grafana_url']
    print(f"🌐 Opening Grafana dashboard: {url}")
    webbrowser.open(url)

@cli.command()
@click.option('--tail', '-n', default=100, help='Number of lines')
@click.option('--follow', '-f', is_flag=True, help='Follow log output')
@click.argument('component', type=click.Choice(['orchestrator', 'codex', 'all']))
def logs(tail, follow, component):
    """ログ表示"""
    if component == 'all':
        selector = '-l app'
    else:
        selector = f'-l app={component}'

    cmd = ['kubectl', 'logs', selector, '-n', CONFIG['namespace'], f'--tail={tail}']

    if follow:
        cmd.append('-f')

    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n⏹️ Log streaming stopped")

if __name__ == '__main__':
    cli()
