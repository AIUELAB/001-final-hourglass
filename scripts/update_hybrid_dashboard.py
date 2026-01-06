#!/usr/bin/env python3
"""
Hybrid Generator Dashboard Updater

実行ログを集計してダッシュボードを更新する。
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict


PROJECT_ROOT = Path(__file__).parent.parent
LOGS_DIR = PROJECT_ROOT / "src" / "reports" / "logs"
DASHBOARD_PATH = PROJECT_ROOT / "preserved" / "hybrid_generator_dashboard.html"


def collect_run_logs(days: int = 30) -> list[dict]:
    """直近N日間の実行ログを収集"""
    cutoff = datetime.now() - timedelta(days=days)
    logs = []

    for log_file in sorted(LOGS_DIR.glob("run_*.json")):
        try:
            with open(log_file, encoding="utf-8") as f:
                data = json.load(f)

            # 日付をパース
            started_at = datetime.fromisoformat(data.get("started_at", ""))
            if started_at >= cutoff:
                data["_file"] = log_file.name
                logs.append(data)
        except (json.JSONDecodeError, ValueError):
            continue

    return logs


def aggregate_stats(logs: list[dict]) -> dict:
    """ログを集計"""
    stats = {
        "total_runs": len(logs),
        "total_generated": 0,
        "total_accepted": 0,
        "total_rejected": 0,
        "dry_run_count": 0,
        "execute_count": 0,
        "epgen_attempts": 0,
        "epgen_successes": 0,
        "legacy_attempts": 0,
        "legacy_successes": 0,
        "fallback_count": 0,
        "rejection_reasons": defaultdict(int),
        "daily_stats": defaultdict(
            lambda: {
                "generated": 0,
                "accepted": 0,
                "rejected": 0,
            }
        ),
        "avg_acceptance_rate": 0.0,
        "epgen_success_rate": 0.0,
        "legacy_success_rate": 0.0,
    }

    for log in logs:
        stats["total_generated"] += log.get("generated_count", 0)
        stats["total_accepted"] += log.get("accepted_count", 0)
        stats["total_rejected"] += log.get("rejected_count", 0)

        if log.get("dry_run", False):
            stats["dry_run_count"] += 1
        else:
            stats["execute_count"] += 1

        # Router stats
        router = log.get("router_stats", {})
        stats["epgen_attempts"] += router.get("epgen_attempts", 0)
        stats["epgen_successes"] += router.get("epgen_successes", 0)
        stats["legacy_attempts"] += router.get("legacy_attempts", 0)
        stats["legacy_successes"] += router.get("legacy_successes", 0)
        stats["fallback_count"] += router.get("fallback_count", 0)

        # Rejection reasons
        for rejection in log.get("rejections", []):
            reason = rejection.get("reason", "unknown")
            stats["rejection_reasons"][reason] += 1

        # Daily stats
        started_at = log.get("started_at", "")
        if started_at:
            date = started_at[:10]
            stats["daily_stats"][date]["generated"] += log.get("generated_count", 0)
            stats["daily_stats"][date]["accepted"] += log.get("accepted_count", 0)
            stats["daily_stats"][date]["rejected"] += log.get("rejected_count", 0)

    # Calculate rates
    if stats["total_generated"] > 0:
        stats["avg_acceptance_rate"] = stats["total_accepted"] / stats["total_generated"] * 100

    if stats["epgen_attempts"] > 0:
        stats["epgen_success_rate"] = stats["epgen_successes"] / stats["epgen_attempts"] * 100

    if stats["legacy_attempts"] > 0:
        stats["legacy_success_rate"] = stats["legacy_successes"] / stats["legacy_attempts"] * 100

    # Convert defaultdicts to regular dicts
    stats["rejection_reasons"] = dict(stats["rejection_reasons"])
    stats["daily_stats"] = dict(stats["daily_stats"])

    return stats


def generate_dashboard_html(stats: dict) -> str:
    """ダッシュボードHTMLを生成"""

    # Daily stats for chart
    dates = sorted(stats["daily_stats"].keys())[-14:]  # Last 14 days
    daily_data = [stats["daily_stats"].get(d, {"generated": 0, "accepted": 0}) for d in dates]

    # Rejection reasons for pie chart
    rejection_labels = list(stats["rejection_reasons"].keys())
    rejection_values = list(stats["rejection_reasons"].values())

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hybrid Generator Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #1a1a2e; color: #eee; padding: 20px; }}
        h1 {{ text-align: center; margin-bottom: 30px; color: #00d9ff; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .stat-card {{ background: #16213e; border-radius: 12px; padding: 20px; text-align: center; }}
        .stat-value {{ font-size: 2.5em; font-weight: bold; color: #00d9ff; }}
        .stat-label {{ color: #888; margin-top: 5px; }}
        .stat-sub {{ font-size: 0.9em; color: #666; margin-top: 5px; }}
        .chart-container {{ background: #16213e; border-radius: 12px; padding: 20px; margin-bottom: 30px; }}
        .chart-title {{ font-size: 1.2em; margin-bottom: 15px; color: #00d9ff; }}
        .charts-row {{ display: grid; grid-template-columns: 2fr 1fr; gap: 20px; }}
        .rate-good {{ color: #4caf50; }}
        .rate-warning {{ color: #ff9800; }}
        .rate-bad {{ color: #f44336; }}
        .updated {{ text-align: center; color: #666; margin-top: 20px; }}
        @media (max-width: 800px) {{ .charts-row {{ grid-template-columns: 1fr; }} }}
    </style>
</head>
<body>
    <h1>Hybrid Generator Dashboard</h1>

    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-value">{stats["total_runs"]}</div>
            <div class="stat-label">Total Runs</div>
            <div class="stat-sub">dry-run: {stats["dry_run_count"]} / execute: {stats["execute_count"]}</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{stats["total_accepted"]}</div>
            <div class="stat-label">Episodes Accepted</div>
            <div class="stat-sub">of {stats["total_generated"]} generated</div>
        </div>
        <div class="stat-card">
            <div class="stat-value {'rate-good' if stats['avg_acceptance_rate'] >= 70 else 'rate-warning' if stats['avg_acceptance_rate'] >= 50 else 'rate-bad'}">{stats["avg_acceptance_rate"]:.1f}%</div>
            <div class="stat-label">Acceptance Rate</div>
            <div class="stat-sub">target: >= 70%</div>
        </div>
        <div class="stat-card">
            <div class="stat-value {'rate-good' if stats['epgen_success_rate'] >= 80 else 'rate-warning'}">{stats["epgen_success_rate"]:.1f}%</div>
            <div class="stat-label">EPGEN Success Rate</div>
            <div class="stat-sub">{stats["epgen_successes"]}/{stats["epgen_attempts"]} attempts</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{stats["fallback_count"]}</div>
            <div class="stat-label">Fallbacks</div>
            <div class="stat-sub">EPGEN -> Legacy</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{stats["total_rejected"]}</div>
            <div class="stat-label">Rejected</div>
            <div class="stat-sub">quality gates</div>
        </div>
    </div>

    <div class="charts-row">
        <div class="chart-container">
            <div class="chart-title">Daily Generation (Last 14 Days)</div>
            <canvas id="dailyChart"></canvas>
        </div>
        <div class="chart-container">
            <div class="chart-title">Rejection Reasons</div>
            <canvas id="rejectionChart"></canvas>
        </div>
    </div>

    <div class="updated">Last updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>

    <script>
        // Daily chart
        new Chart(document.getElementById('dailyChart'), {{
            type: 'bar',
            data: {{
                labels: {json.dumps(dates)},
                datasets: [
                    {{
                        label: 'Accepted',
                        data: {json.dumps([d["accepted"] for d in daily_data])},
                        backgroundColor: 'rgba(0, 217, 255, 0.7)',
                    }},
                    {{
                        label: 'Generated',
                        data: {json.dumps([d["generated"] for d in daily_data])},
                        backgroundColor: 'rgba(100, 100, 100, 0.5)',
                    }}
                ]
            }},
            options: {{
                responsive: true,
                scales: {{
                    y: {{ beginAtZero: true, grid: {{ color: '#333' }} }},
                    x: {{ grid: {{ color: '#333' }} }}
                }},
                plugins: {{ legend: {{ labels: {{ color: '#eee' }} }} }}
            }}
        }});

        // Rejection pie chart
        new Chart(document.getElementById('rejectionChart'), {{
            type: 'doughnut',
            data: {{
                labels: {json.dumps(rejection_labels)},
                datasets: [{{
                    data: {json.dumps(rejection_values)},
                    backgroundColor: [
                        '#ff6384', '#36a2eb', '#ffce56', '#4bc0c0', '#9966ff', '#ff9f40'
                    ]
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{ legend: {{ labels: {{ color: '#eee' }}, position: 'bottom' }} }}
            }}
        }});
    </script>
</body>
</html>"""

    return html


def main():
    """メイン処理"""
    print("Collecting run logs...")
    logs = collect_run_logs(days=30)
    print(f"Found {len(logs)} logs")

    print("Aggregating stats...")
    stats = aggregate_stats(logs)

    print("Generating dashboard HTML...")
    html = generate_dashboard_html(stats)

    print(f"Writing to {DASHBOARD_PATH}...")
    DASHBOARD_PATH.write_text(html, encoding="utf-8")

    print("Done!")
    print("\nSummary:")
    print(f"  Total runs: {stats['total_runs']}")
    print(f"  Acceptance rate: {stats['avg_acceptance_rate']:.1f}%")
    print(f"  EPGEN success rate: {stats['epgen_success_rate']:.1f}%")


if __name__ == "__main__":
    main()
