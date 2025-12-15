#!/usr/bin/env python3
"""
統合ルール管理システム - ヘルスモニタリング
Unified Rule Management System - Health Monitoring

目的:
1. ルールレジストリの整合性を継続的に監視
2. 同期ステータスの検証
3. 異常検出とアラート
4. 運用メトリクスの収集

Created: 2025-10-02
"""

import json
import logging
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from unified_rule_management_system import UnifiedRuleRegistry, RuleStatus

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class HealthCheckResult:
    """ヘルスチェック結果"""
    check_name: str
    status: str  # PASS, WARN, FAIL
    message: str
    details: Optional[Dict] = None
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class RuleHealthMonitor:
    """ルールヘルスモニター"""

    def __init__(
        self,
        registry_path: str = "rules_registry.json",
        sync_report_path: str = "rule_sync_report.json"
    ):
        self.registry_path = Path(registry_path)
        self.sync_report_path = Path(sync_report_path)
        self.registry = UnifiedRuleRegistry(str(registry_path))

        # ヘルスチェック閾値
        self.thresholds = {
            'documentation_rate': 95.0,  # 95%以上
            'max_contradictions': 0,     # 0件
            'sync_age_hours': 24,        # 24時間以内
            'checksum_match': True       # チェックサム一致必須
        }

    def run_all_checks(self) -> List[HealthCheckResult]:
        """すべてのヘルスチェックを実行"""
        logger.info("🏥 ヘルスチェック開始...")

        checks = []

        # 1. ドキュメント完全性チェック
        checks.append(self._check_documentation())

        # 2. 矛盾検出チェック
        checks.append(self._check_contradictions())

        # 3. 同期ステータスチェック
        checks.append(self._check_sync_status())

        # 4. ファイル整合性チェック
        checks.append(self._check_file_integrity())

        # 5. ルール統計チェック
        checks.append(self._check_rule_statistics())

        # 総合判定
        overall = self._generate_overall_status(checks)
        checks.append(overall)

        return checks

    def _check_documentation(self) -> HealthCheckResult:
        """ドキュメント完全性チェック"""
        active_rules = self.registry.get_active_rules()
        total = len(active_rules)
        documented = sum(1 for rule in active_rules if rule.description)

        rate = (documented / total * 100) if total > 0 else 0

        if rate >= self.thresholds['documentation_rate']:
            status = "PASS"
            message = f"ドキュメント率 {rate:.1f}% (閾値: {self.thresholds['documentation_rate']}%以上)"
        else:
            status = "WARN"
            message = f"ドキュメント率が低下 {rate:.1f}% (閾値: {self.thresholds['documentation_rate']}%)"

        return HealthCheckResult(
            check_name="ドキュメント完全性",
            status=status,
            message=message,
            details={
                'total_rules': total,
                'documented_rules': documented,
                'documentation_rate': rate
            }
        )

    def _check_contradictions(self) -> HealthCheckResult:
        """矛盾検出チェック"""
        conflicts = self.registry.detect_conflicts()

        count = len(conflicts)

        if count <= self.thresholds['max_contradictions']:
            status = "PASS"
            message = f"矛盾なし ({count}件)"
        else:
            status = "FAIL"
            message = f"矛盾検出 {count}件 (閾値: {self.thresholds['max_contradictions']}件)"

        return HealthCheckResult(
            check_name="矛盾検出",
            status=status,
            message=message,
            details={
                'contradiction_count': count,
                'contradictions': conflicts[:5] if conflicts else []  # 最初の5件のみ
            }
        )

    def _check_sync_status(self) -> HealthCheckResult:
        """同期ステータスチェック"""
        if not self.sync_report_path.exists():
            return HealthCheckResult(
                check_name="同期ステータス",
                status="WARN",
                message="同期レポートが見つかりません",
                details={'sync_report_exists': False}
            )

        with open(self.sync_report_path, 'r', encoding='utf-8') as f:
            sync_report = json.load(f)

        # 同期時刻の確認
        sync_time = datetime.fromisoformat(sync_report['sync_timestamp'])
        age_hours = (datetime.now() - sync_time).total_seconds() / 3600

        # チェックサムの確認
        checksum_match = sync_report['checksum'] == self.registry.checksum

        if age_hours <= self.thresholds['sync_age_hours'] and checksum_match:
            status = "PASS"
            message = f"同期正常 ({age_hours:.1f}時間前)"
        elif not checksum_match:
            status = "FAIL"
            message = "チェックサム不一致 - 再同期が必要"
        else:
            status = "WARN"
            message = f"同期が古い ({age_hours:.1f}時間前, 閾値: {self.thresholds['sync_age_hours']}時間)"

        return HealthCheckResult(
            check_name="同期ステータス",
            status=status,
            message=message,
            details={
                'last_sync': sync_report['sync_timestamp'],
                'age_hours': age_hours,
                'checksum_match': checksum_match,
                'targets_synced': sync_report['targets_synced']
            }
        )

    def _check_file_integrity(self) -> HealthCheckResult:
        """ファイル整合性チェック"""
        issues = []

        # rules_registry.jsonの存在確認
        if not self.registry_path.exists():
            issues.append("rules_registry.json が存在しません")

        # pdca_guardian.pyの存在確認
        pdca_file = Path("pdca_guardian.py")
        if not pdca_file.exists():
            issues.append("pdca_guardian.py が存在しません")
        else:
            # AUTO-GENERATED RULESマーカーの確認
            with open(pdca_file, 'r', encoding='utf-8') as f:
                content = f.read()
            if '# AUTO-GENERATED RULES START' not in content:
                issues.append("pdca_guardian.py に同期マーカーがありません")

        # episode_guardian_config.jsonの存在確認
        config_file = Path("episode_guardian_config.json")
        if not config_file.exists():
            issues.append("episode_guardian_config.json が存在しません")
        else:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            if 'unified_rules' not in config:
                issues.append("episode_guardian_config.json に unified_rules セクションがありません")

        if not issues:
            status = "PASS"
            message = "すべてのファイルが正常"
        else:
            status = "FAIL"
            message = f"{len(issues)}件の問題を検出"

        return HealthCheckResult(
            check_name="ファイル整合性",
            status=status,
            message=message,
            details={'issues': issues}
        )

    def _check_rule_statistics(self) -> HealthCheckResult:
        """ルール統計チェック"""
        # 手動で統計を計算
        total_rules = len(self.registry.rules)
        active_rules = len([r for r in self.registry.rules.values() if r.status == RuleStatus.ACTIVE])
        deprecated_rules = len([r for r in self.registry.rules.values() if r.status == RuleStatus.DEPRECATED])

        stats = {
            'total_rules': total_rules,
            'active_rules': active_rules,
            'deprecated_rules': deprecated_rules
        }

        # 異常検出
        issues = []

        # アクティブルールが極端に少ない
        if stats['active_rules'] < 50:
            issues.append(f"アクティブルール数が少ない ({stats['active_rules']}件)")

        # 非推奨ルールが多すぎる
        deprecation_rate = (stats['deprecated_rules'] / stats['total_rules'] * 100) if stats['total_rules'] > 0 else 0
        if deprecation_rate > 20:
            issues.append(f"非推奨ルール率が高い ({deprecation_rate:.1f}%)")

        if not issues:
            status = "PASS"
            message = f"ルール統計正常 ({stats['active_rules']}アクティブ, {stats['deprecated_rules']}非推奨)"
        else:
            status = "WARN"
            message = f"{len(issues)}件の統計異常"

        return HealthCheckResult(
            check_name="ルール統計",
            status=status,
            message=message,
            details=stats
        )

    def _generate_overall_status(self, checks: List[HealthCheckResult]) -> HealthCheckResult:
        """総合ステータス判定"""
        fail_count = sum(1 for check in checks if check.status == "FAIL")
        warn_count = sum(1 for check in checks if check.status == "WARN")
        pass_count = sum(1 for check in checks if check.status == "PASS")

        if fail_count > 0:
            status = "FAIL"
            message = f"ヘルスチェック失敗: {fail_count}件のFAIL, {warn_count}件のWARN"
        elif warn_count > 0:
            status = "WARN"
            message = f"ヘルスチェック警告: {warn_count}件のWARN"
        else:
            status = "PASS"
            message = f"ヘルスチェック合格: すべて正常 ({pass_count}件)"

        return HealthCheckResult(
            check_name="総合判定",
            status=status,
            message=message,
            details={
                'total_checks': len(checks),
                'pass_count': pass_count,
                'warn_count': warn_count,
                'fail_count': fail_count
            }
        )

    def save_health_report(self, checks: List[HealthCheckResult], output_path: str = "rule_health_report.json"):
        """ヘルスレポート保存"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_checks': len(checks) - 1,  # 総合判定を除く
                'pass': sum(1 for c in checks if c.status == "PASS" and c.check_name != "総合判定"),
                'warn': sum(1 for c in checks if c.status == "WARN"),
                'fail': sum(1 for c in checks if c.status == "FAIL")
            },
            'checks': [asdict(check) for check in checks]
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.info(f"📄 ヘルスレポート保存: {output_path}")

    def print_health_report(self, checks: List[HealthCheckResult]):
        """ヘルスレポート表示"""
        print("\n" + "=" * 60)
        print("📊 統合ルール管理システム - ヘルスチェック結果")
        print("=" * 60)

        for check in checks:
            status_icon = {
                "PASS": "✅",
                "WARN": "⚠️",
                "FAIL": "❌"
            }.get(check.status, "❓")

            print(f"\n{status_icon} {check.check_name}: {check.status}")
            print(f"   {check.message}")

            if check.details and check.check_name != "総合判定":
                print(f"   詳細: {json.dumps(check.details, ensure_ascii=False, indent=6)}")

        print("\n" + "=" * 60)


def main():
    """メイン処理"""
    logger.info("🏥 統合ルール管理システム - ヘルスモニタリング起動")

    monitor = RuleHealthMonitor()

    # すべてのヘルスチェック実行
    checks = monitor.run_all_checks()

    # レポート表示
    monitor.print_health_report(checks)

    # レポート保存
    monitor.save_health_report(checks)

    # 終了コード判定
    overall = next(c for c in checks if c.check_name == "総合判定")
    exit_code = 0 if overall.status == "PASS" else (1 if overall.status == "WARN" else 2)

    logger.info(f"\n✅ ヘルスモニタリング完了 (終了コード: {exit_code})")
    return exit_code


if __name__ == "__main__":
    exit(main())
