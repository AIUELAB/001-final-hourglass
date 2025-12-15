#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PDCAガーディアン健全性監視システム
ルールの実行状況を監視し、問題を早期発見
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from collections import defaultdict
import time


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PDCAHealthMonitor:
    """PDCAガーディアンの健全性を監視"""

    def __init__(self, log_dir: str = "pdca_logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        self.execution_history = []
        self.skip_history = []
        self.error_history = []
        self.performance_metrics = defaultdict(list)

        # 監視対象のクリティカルルール
        self.critical_rules = [
            'RULE_152',  # 文末チェック
            'RULE_160',  # 文字数制限
            'RULE_164',  # 日付形式
            'RULE_165',  # 動詞・形容詞終了
            'RULE_166',  # 事実優先原則
            'RULE_167',  # ファクトチェック
            'RULE_168'   # 品質優先原則
        ]

        # アラート閾値
        self.thresholds = {
            'skip_rate': 0.1,      # 10%以上のスキップで警告
            'error_rate': 0.05,    # 5%以上のエラーで警告
            'execution_time': 1.0,  # 1秒以上で警告
            'coverage_min': 0.9     # 90%未満のカバレッジで警告
        }

    def start_monitoring(self, rule_name: str, context: Dict[str, Any]) -> str:
        """ルール実行の監視開始"""
        monitor_id = f"{rule_name}_{datetime.now().timestamp()}"

        self.execution_history.append({
            'monitor_id': monitor_id,
            'rule': rule_name,
            'start_time': time.time(),
            'context': context,
            'status': 'started'
        })

        return monitor_id

    def end_monitoring(self, monitor_id: str, status: str,
                      result: Optional[Any] = None, error: Optional[str] = None):
        """ルール実行の監視終了"""
        for execution in self.execution_history:
            if execution['monitor_id'] == monitor_id:
                execution['end_time'] = time.time()
                execution['duration'] = execution['end_time'] - execution['start_time']
                execution['status'] = status
                execution['result'] = result
                execution['error'] = error

                # パフォーマンスメトリクス記録
                rule_name = execution['rule']
                self.performance_metrics[rule_name].append(execution['duration'])

                # エラーの場合は別途記録
                if status == 'error':
                    self.error_history.append({
                        'rule': rule_name,
                        'timestamp': datetime.now(),
                        'error': error,
                        'context': execution['context']
                    })

                # スキップの場合も記録
                elif status == 'skipped':
                    self.skip_history.append({
                        'rule': rule_name,
                        'timestamp': datetime.now(),
                        'reason': error or 'Unknown reason',
                        'context': execution['context']
                    })

                break

    def check_preconditions(self, rule_name: str, context: Dict[str, Any]) -> Tuple[bool, str]:
        """実行前提条件のチェック"""

        # RULE_152: 文末チェックの前提条件
        if rule_name == 'RULE_152':
            if 'episode_text' not in context or not context['episode_text']:
                return False, "エピソードテキストが存在しません"

        # RULE_167: ファクトチェックの前提条件
        elif rule_name == 'RULE_167':
            if 'person_data' not in context or context['person_data'] is None:
                return False, "person_dataが提供されていません"

        # ファイル依存のルール
        elif rule_name in ['RULE_077', 'RULE_078', 'RULE_079']:
            if 'csv_file' in context:
                csv_path = Path(context['csv_file'])
                if not csv_path.exists():
                    return False, f"CSVファイルが存在しません: {csv_path}"

        return True, "OK"

    def generate_health_report(self) -> Dict[str, Any]:
        """健全性レポートの生成"""

        # 実行統計の計算
        total_executions = len(self.execution_history)
        successful = sum(1 for e in self.execution_history if e['status'] == 'success')
        errors = sum(1 for e in self.execution_history if e['status'] == 'error')
        skipped = sum(1 for e in self.execution_history if e['status'] == 'skipped')

        # ルール別の統計
        rule_stats = defaultdict(lambda: {'success': 0, 'error': 0, 'skip': 0})
        for execution in self.execution_history:
            rule = execution['rule']
            status = execution['status']
            if status == 'success':
                rule_stats[rule]['success'] += 1
            elif status == 'error':
                rule_stats[rule]['error'] += 1
            elif status == 'skipped':
                rule_stats[rule]['skip'] += 1

        # パフォーマンス統計
        performance_summary = {}
        for rule, durations in self.performance_metrics.items():
            if durations:
                performance_summary[rule] = {
                    'avg_time': sum(durations) / len(durations),
                    'max_time': max(durations),
                    'min_time': min(durations),
                    'total_calls': len(durations)
                }

        # アラート生成
        alerts = self._generate_alerts(total_executions, errors, skipped)

        # クリティカルルールのカバレッジ
        critical_coverage = self._calculate_critical_coverage(rule_stats)

        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_executions': total_executions,
                'successful': successful,
                'errors': errors,
                'skipped': skipped,
                'success_rate': (successful / total_executions * 100) if total_executions > 0 else 0,
                'error_rate': (errors / total_executions * 100) if total_executions > 0 else 0,
                'skip_rate': (skipped / total_executions * 100) if total_executions > 0 else 0
            },
            'rule_statistics': dict(rule_stats),
            'performance': performance_summary,
            'critical_rules_coverage': critical_coverage,
            'alerts': alerts,
            'recent_errors': self.error_history[-5:],  # 最新5件のエラー
            'recent_skips': self.skip_history[-5:]      # 最新5件のスキップ
        }

        return report

    def _generate_alerts(self, total: int, errors: int, skipped: int) -> List[Dict[str, str]]:
        """アラートの生成"""
        alerts = []

        if total > 0:
            error_rate = errors / total
            skip_rate = skipped / total

            if error_rate > self.thresholds['error_rate']:
                alerts.append({
                    'level': 'ERROR',
                    'message': f'エラー率が閾値を超えています: {error_rate:.1%} > {self.thresholds["error_rate"]:.1%}',
                    'timestamp': datetime.now().isoformat()
                })

            if skip_rate > self.thresholds['skip_rate']:
                alerts.append({
                    'level': 'WARNING',
                    'message': f'スキップ率が閾値を超えています: {skip_rate:.1%} > {self.thresholds["skip_rate"]:.1%}',
                    'timestamp': datetime.now().isoformat()
                })

        # パフォーマンス警告
        for rule, durations in self.performance_metrics.items():
            if durations:
                avg_time = sum(durations) / len(durations)
                if avg_time > self.thresholds['execution_time']:
                    alerts.append({
                        'level': 'WARNING',
                        'message': f'{rule}の平均実行時間が遅い: {avg_time:.2f}秒',
                        'timestamp': datetime.now().isoformat()
                    })

        return alerts

    def _calculate_critical_coverage(self, rule_stats: Dict) -> Dict[str, Any]:
        """クリティカルルールのカバレッジ計算"""
        coverage = {}

        for rule in self.critical_rules:
            if rule in rule_stats:
                stats = rule_stats[rule]
                total = stats['success'] + stats['error'] + stats['skip']
                if total > 0:
                    coverage[rule] = {
                        'execution_count': total,
                        'success_rate': (stats['success'] / total * 100),
                        'status': 'ACTIVE'
                    }
                else:
                    coverage[rule] = {
                        'execution_count': 0,
                        'success_rate': 0,
                        'status': 'NOT_EXECUTED'
                    }
            else:
                coverage[rule] = {
                    'execution_count': 0,
                    'success_rate': 0,
                    'status': 'NOT_FOUND'
                }

        # 全体のカバレッジ率
        executed_rules = sum(1 for r in coverage.values() if r['status'] == 'ACTIVE')
        coverage['overall'] = {
            'coverage_percentage': (executed_rules / len(self.critical_rules) * 100),
            'executed': executed_rules,
            'total': len(self.critical_rules)
        }

        return coverage

    def save_report(self, report: Dict[str, Any], filename: Optional[str] = None):
        """レポートの保存"""
        if filename is None:
            filename = f"health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        filepath = self.log_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)

        logger.info(f"健全性レポートを保存: {filepath}")

    def get_historical_analysis(self, days: int = 7) -> Dict[str, Any]:
        """過去N日間の傾向分析"""
        cutoff_time = datetime.now() - timedelta(days=days)

        # 期間内の実行を抽出
        recent_executions = [
            e for e in self.execution_history
            if datetime.fromtimestamp(e.get('start_time', 0)) > cutoff_time
        ]

        # 日別の統計
        daily_stats = defaultdict(lambda: {'success': 0, 'error': 0, 'skip': 0})

        for execution in recent_executions:
            date = datetime.fromtimestamp(execution['start_time']).date()
            status = execution['status']

            if status == 'success':
                daily_stats[str(date)]['success'] += 1
            elif status == 'error':
                daily_stats[str(date)]['error'] += 1
            elif status == 'skipped':
                daily_stats[str(date)]['skip'] += 1

        # トレンド分析
        dates = sorted(daily_stats.keys())
        if len(dates) >= 2:
            first_day_success = daily_stats[dates[0]]['success']
            last_day_success = daily_stats[dates[-1]]['success']
            trend = 'IMPROVING' if last_day_success > first_day_success else 'DECLINING'
        else:
            trend = 'INSUFFICIENT_DATA'

        return {
            'period': f'{days} days',
            'daily_statistics': dict(daily_stats),
            'trend': trend,
            'total_executions': len(recent_executions)
        }

    def display_dashboard(self):
        """ダッシュボード表示"""
        report = self.generate_health_report()

        print("\n" + "=" * 80)
        print("📊 PDCAガーディアン健全性ダッシュボード")
        print("=" * 80)

        # サマリー
        print("\n📈 実行統計:")
        print(f"  総実行数: {report['summary']['total_executions']}")
        print(f"  成功率: {report['summary']['success_rate']:.1f}%")
        print(f"  エラー率: {report['summary']['error_rate']:.1f}%")
        print(f"  スキップ率: {report['summary']['skip_rate']:.1f}%")

        # クリティカルルールカバレッジ
        print("\n🎯 クリティカルルールカバレッジ:")
        coverage = report['critical_rules_coverage']
        for rule, stats in coverage.items():
            if rule != 'overall':
                status_icon = "✅" if stats['status'] == 'ACTIVE' else "❌"
                print(f"  {status_icon} {rule}: {stats['status']} (実行数: {stats['execution_count']})")

        print(f"\n  全体カバレッジ: {coverage['overall']['coverage_percentage']:.1f}%")

        # アラート
        if report['alerts']:
            print("\n⚠️ アラート:")
            for alert in report['alerts']:
                icon = "🔴" if alert['level'] == 'ERROR' else "🟡"
                print(f"  {icon} {alert['message']}")
        else:
            print("\n✅ アラートなし")

        # 最近のエラー
        if report['recent_errors']:
            print("\n❌ 最近のエラー:")
            for error in report['recent_errors'][-3:]:
                print(f"  - {error['rule']}: {error['error'][:50]}...")

        print("\n" + "=" * 80)


def test_health_monitor():
    """テスト実行"""
    monitor = PDCAHealthMonitor()

    # テスト実行をシミュレート
    test_rules = ['RULE_152', 'RULE_160', 'RULE_165', 'RULE_167']

    for i, rule in enumerate(test_rules):
        context = {'episode_text': f'テストエピソード{i}', 'person_data': {'name': f'人物{i}'}}

        # 前提条件チェック
        can_execute, reason = monitor.check_preconditions(rule, context)

        if can_execute:
            # 監視開始
            monitor_id = monitor.start_monitoring(rule, context)

            # 実行をシミュレート
            time.sleep(0.1)  # 実行時間をシミュレート

            # 結果に応じて終了
            if i % 3 == 0:
                monitor.end_monitoring(monitor_id, 'success', result={'violations': []})
            elif i % 3 == 1:
                monitor.end_monitoring(monitor_id, 'error', error='テストエラー')
            else:
                monitor.end_monitoring(monitor_id, 'skipped', error='テストスキップ')
        else:
            # スキップを記録
            monitor.skip_history.append({
                'rule': rule,
                'timestamp': datetime.now(),
                'reason': reason,
                'context': context
            })

    # ダッシュボード表示
    monitor.display_dashboard()

    # レポート保存
    report = monitor.generate_health_report()
    monitor.save_report(report)


if __name__ == "__main__":
    test_health_monitor()
