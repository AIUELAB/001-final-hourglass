#!/usr/bin/env python3
"""
統合ルール管理システム - 包括的テスト
Comprehensive Test Suite for Unified Rule Management System

テスト項目:
1. ルールレジストリの整合性
2. ルール競合検出
3. 同期システムの動作確認
4. ロールバック機能
5. パフォーマンステスト

Created: 2025-10-02
"""

import json
import logging
from pathlib import Path
from unified_rule_management_system import (
    UnifiedRuleRegistry, Rule, RuleCategory, RulePriority, RuleStatus
)
from rule_sync_automation import RuleSyncAutomation, RuleConflictResolver

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)


class UnifiedRuleSystemTester:
    """統合ルールシステムテスター"""

    def __init__(self):
        self.registry = UnifiedRuleRegistry()
        self.test_results = {
            'passed': 0,
            'failed': 0,
            'tests': []
        }

    def run_all_tests(self):
        """全テスト実行"""
        logger.info("🧪 統合ルール管理システム - 包括的テスト開始\n")

        self.test_registry_integrity()
        self.test_rule_conflicts()
        self.test_sync_system()
        self.test_rollback()
        self.test_performance()

        self._print_summary()

    def test_registry_integrity(self):
        """テスト1: レジストリ整合性"""
        logger.info("=" * 60)
        logger.info("Test 1: レジストリ整合性チェック")
        logger.info("=" * 60)

        # サブテスト1-1: ルール数の確認
        total_rules = len(self.registry.rules)
        self._assert(
            "1-1: ルール総数チェック",
            total_rules > 0,
            f"Expected >0, Got {total_rules}"
        )

        # サブテスト1-2: アクティブルール数
        active_rules = len(self.registry.get_active_rules())
        self._assert(
            "1-2: アクティブルール数チェック",
            active_rules > 0,
            f"Expected >0, Got {active_rules}"
        )

        # サブテスト1-3: チェックサムの存在
        self._assert(
            "1-3: チェックサム存在確認",
            self.registry.checksum is not None,
            "Checksum should exist"
        )

        # サブテスト1-4: ルールIDのユニーク性
        rule_ids = list(self.registry.rules.keys())
        unique_ids = set(rule_ids)
        self._assert(
            "1-4: ルールIDユニーク性",
            len(rule_ids) == len(unique_ids),
            f"Duplicate rule IDs found"
        )

        # サブテスト1-5: カテゴリ分類の完全性
        uncategorized = [
            r for r in self.registry.rules.values()
            if not r.category
        ]
        self._assert(
            "1-5: カテゴリ未分類チェック",
            len(uncategorized) == 0,
            f"{len(uncategorized)} rules without category"
        )

        logger.info("")

    def test_rule_conflicts(self):
        """テスト2: ルール競合検出"""
        logger.info("=" * 60)
        logger.info("Test 2: ルール競合検出")
        logger.info("=" * 60)

        conflicts = self.registry.detect_conflicts()

        logger.info(f"検出された競合: {len(conflicts)}件")

        # サブテスト2-1: 競合検出機能の動作確認
        self._assert(
            "2-1: 競合検出機能の動作",
            isinstance(conflicts, list),
            "Conflict detection returned list"
        )

        # サブテスト2-2: 競合解決機能
        if conflicts:
            resolver = RuleConflictResolver(self.registry)
            result = resolver.detect_and_resolve()
            self._assert(
                "2-2: 競合解決試行",
                result is not None,
                "Conflict resolver executed"
            )

        logger.info("")

    def test_sync_system(self):
        """テスト3: 同期システム"""
        logger.info("=" * 60)
        logger.info("Test 3: 同期システム動作確認")
        logger.info("=" * 60)

        sync = RuleSyncAutomation()

        # サブテスト3-1: バックアップ作成
        backup_dir = Path("rule_backups")
        self._assert(
            "3-1: バックアップディレクトリ存在",
            backup_dir.exists(),
            "Backup directory created"
        )

        # サブテスト3-2: 同期レポート生成
        report_path = Path("rule_sync_report.json")
        self._assert(
            "3-2: 同期レポート生成",
            report_path.exists(),
            "Sync report created"
        )

        # サブテスト3-3: レポート内容の検証
        if report_path.exists():
            with open(report_path, 'r') as f:
                report = json.load(f)

            self._assert(
                "3-3: レポート内容検証",
                'total_rules' in report and 'active_rules' in report,
                "Report contains required fields"
            )

        # サブテスト3-4: episode_guardian_config.jsonの更新
        config_path = Path("episode_guardian_config.json")
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)

            self._assert(
                "3-4: EpisodeGuardian設定更新",
                'unified_rules' in config,
                "unified_rules added to config"
            )

        logger.info("")

    def test_rollback(self):
        """テスト4: ロールバック機能"""
        logger.info("=" * 60)
        logger.info("Test 4: ロールバック機能")
        logger.info("=" * 60)

        backup_dir = Path("rule_backups")

        # サブテスト4-1: バックアップファイルの存在確認
        backups = list(backup_dir.glob("*.backup_*"))
        self._assert(
            "4-1: バックアップファイル存在",
            len(backups) > 0,
            f"{len(backups)} backup files found"
        )

        # サブテスト4-2: バックアップファイルの完全性
        if backups:
            latest_backup = sorted(backups)[-1]
            self._assert(
                "4-2: バックアップファイル完全性",
                latest_backup.stat().st_size > 0,
                "Backup file is not empty"
            )

        logger.info("")

    def test_performance(self):
        """テスト5: パフォーマンステスト"""
        logger.info("=" * 60)
        logger.info("Test 5: パフォーマンステスト")
        logger.info("=" * 60)

        import time

        # サブテスト5-1: レジストリ読み込み速度
        start = time.time()
        test_registry = UnifiedRuleRegistry()
        load_time = time.time() - start

        self._assert(
            "5-1: レジストリ読み込み速度",
            load_time < 1.0,
            f"Load time: {load_time:.3f}s (should be <1s)"
        )

        # サブテスト5-2: アクティブルール取得速度
        start = time.time()
        active_rules = test_registry.get_active_rules()
        query_time = time.time() - start

        self._assert(
            "5-2: アクティブルール取得速度",
            query_time < 0.1,
            f"Query time: {query_time:.3f}s (should be <0.1s)"
        )

        # サブテスト5-3: 競合検出速度
        start = time.time()
        conflicts = test_registry.detect_conflicts()
        detect_time = time.time() - start

        self._assert(
            "5-3: 競合検出速度",
            detect_time < 2.0,
            f"Detect time: {detect_time:.3f}s (should be <2s)"
        )

        logger.info("")

    def _assert(self, test_name: str, condition: bool, message: str):
        """アサーション"""
        if condition:
            logger.info(f"  ✅ {test_name}: PASS")
            self.test_results['passed'] += 1
            self.test_results['tests'].append({
                'name': test_name,
                'status': 'PASS',
                'message': message
            })
        else:
            logger.error(f"  ❌ {test_name}: FAIL - {message}")
            self.test_results['failed'] += 1
            self.test_results['tests'].append({
                'name': test_name,
                'status': 'FAIL',
                'message': message
            })

    def _print_summary(self):
        """テスト結果サマリー"""
        logger.info("\n" + "=" * 60)
        logger.info("📊 テスト結果サマリー")
        logger.info("=" * 60)

        total = self.test_results['passed'] + self.test_results['failed']
        success_rate = (self.test_results['passed'] / total * 100) if total > 0 else 0

        logger.info(f"総テスト数: {total}")
        logger.info(f"成功: {self.test_results['passed']} ({success_rate:.1f}%)")
        logger.info(f"失敗: {self.test_results['failed']}")

        if self.test_results['failed'] == 0:
            logger.info("\n✅ すべてのテストに合格しました！")
        else:
            logger.warning("\n⚠️ 一部のテストに失敗しました")

        # 結果をJSONで保存
        with open("test_results.json", 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, ensure_ascii=False, indent=2)

        logger.info(f"\n📄 詳細結果: test_results.json")


def main():
    """メイン処理"""
    tester = UnifiedRuleSystemTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
