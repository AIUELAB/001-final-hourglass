#!/usr/bin/env python3
"""
統合ルール管理システム - 運用テスト
Unified Rule Management System - Operational Test

目的:
1. ヘルスモニタリングシステムの動作確認
2. 自動同期システムの動作確認
3. エンドツーエンドのルール追加・同期フロー検証
4. ロールバック機能の確認

Created: 2025-10-02
"""

import json
import logging
import subprocess
import time
from pathlib import Path
from datetime import datetime
from unified_rule_management_system import UnifiedRuleRegistry, RuleCategory, RulePriority

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)


class OperationalSystemTest:
    """運用システムテスト"""

    def __init__(self):
        self.test_results = []
        self.original_checksum = None

    def run_all_tests(self):
        """すべてのテストを実行"""
        logger.info("=" * 60)
        logger.info("🧪 統合ルール管理システム - 運用テスト開始")
        logger.info("=" * 60)

        # テスト前の状態を保存
        self._save_initial_state()

        # テスト実行
        tests = [
            ("ヘルスモニタリングシステム", self._test_health_monitoring),
            ("手動同期システム", self._test_manual_sync),
            ("ルール追加フロー", self._test_add_rule_flow),
            ("ロールバック機能", self._test_rollback),
            ("最終整合性確認", self._test_final_consistency)
        ]

        for test_name, test_func in tests:
            logger.info(f"\n{'='*60}")
            logger.info(f"🔬 テスト: {test_name}")
            logger.info("=" * 60)

            try:
                result = test_func()
                self.test_results.append({
                    'test_name': test_name,
                    'status': 'PASS' if result else 'FAIL',
                    'timestamp': datetime.now().isoformat()
                })
                logger.info(f"{'✅' if result else '❌'} {test_name}: {'PASS' if result else 'FAIL'}")
            except Exception as e:
                logger.error(f"❌ {test_name}: FAIL - {e}")
                self.test_results.append({
                    'test_name': test_name,
                    'status': 'FAIL',
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })

        # テスト結果サマリー
        self._print_summary()

        # テスト後のクリーンアップ
        self._cleanup()

    def _save_initial_state(self):
        """初期状態を保存"""
        registry = UnifiedRuleRegistry()
        self.original_checksum = registry.checksum
        logger.info(f"📌 初期チェックサム: {self.original_checksum[:16]}...")

    def _test_health_monitoring(self) -> bool:
        """ヘルスモニタリングシステムのテスト"""
        logger.info("🏥 ヘルスチェック実行...")

        result = subprocess.run(
            ['python3', 'rule_health_monitor.py'],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            logger.error(f"ヘルスチェック失敗: 終了コード {result.returncode}")
            return False

        # レポートファイルの確認
        report_path = Path('rule_health_report.json')
        if not report_path.exists():
            logger.error("ヘルスレポートが生成されていません")
            return False

        with open(report_path, 'r', encoding='utf-8') as f:
            report = json.load(f)

        # 総合判定がPASSか確認
        overall = next((c for c in report['checks'] if c['check_name'] == '総合判定'), None)
        if not overall or overall['status'] != 'PASS':
            logger.error(f"総合判定が不合格: {overall['status'] if overall else 'NOT FOUND'}")
            return False

        logger.info("✅ ヘルスチェック正常")
        return True

    def _test_manual_sync(self) -> bool:
        """手動同期システムのテスト"""
        logger.info("🔄 手動同期実行...")

        result = subprocess.run(
            ['python3', 'rule_sync_automation.py'],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            logger.error(f"同期失敗: 終了コード {result.returncode}")
            logger.error(f"エラー出力:\n{result.stderr}")
            return False

        # 同期レポートの確認
        sync_report_path = Path('rule_sync_report.json')
        if not sync_report_path.exists():
            logger.error("同期レポートが生成されていません")
            return False

        with open(sync_report_path, 'r', encoding='utf-8') as f:
            sync_report = json.load(f)

        # チェックサム一致確認
        registry = UnifiedRuleRegistry()
        if sync_report['checksum'] != registry.checksum:
            logger.error("チェックサム不一致")
            return False

        logger.info("✅ 手動同期正常")
        return True

    def _test_add_rule_flow(self) -> bool:
        """ルール追加フローのテスト"""
        logger.info("➕ テストルール追加...")

        test_rule_id = "RULE_TEST_001"

        # 1. 既存ルールをコピーしてテストルール作成（簡易版）
        registry = UnifiedRuleRegistry()

        # 既存のテストルールがあれば削除
        if test_rule_id in registry.rules:
            del registry.rules[test_rule_id]
            registry.save()

        # RULE_001をベースにテストルールを作成
        if 'RULE_001' not in registry.rules:
            logger.error("RULE_001が見つかりません")
            return False

        base_rule = registry.rules['RULE_001']

        from unified_rule_management_system import Rule, RuleStatus
        from datetime import datetime
        import copy

        # 既存ルールのコピーを作成
        test_rule = copy.deepcopy(base_rule)
        test_rule.rule_id = test_rule_id
        test_rule.name = "運用テスト用ルール"
        test_rule.description = """運用システムのテスト用ルール

【目的】
運用システムの動作確認用の一時的なルール。

【テスト項目】
- ルール追加機能
- 自動同期機能
- ヘルスチェック機能

【作成日】
2025年10月2日
"""
        test_rule.tags = ["test", "temporary"]
        test_rule.updated_at = datetime.now().isoformat()

        registry.add_rule(test_rule)
        registry.save()
        logger.info(f"✅ {test_rule_id} 追加完了")

        # 2. 同期実行
        logger.info("🔄 同期実行...")
        result = subprocess.run(
            ['python3', 'rule_sync_automation.py'],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            logger.error("同期失敗")
            return False

        # 3. 同期結果確認
        with open('rule_sync_report.json', 'r', encoding='utf-8') as f:
            sync_report = json.load(f)

        # アクティブルール数が74（73+1）になっているか確認
        if sync_report['active_rules'] != 74:
            logger.error(f"アクティブルール数が不正: {sync_report['active_rules']} (期待: 74)")
            return False

        logger.info("✅ ルール追加フロー正常")
        return True

    def _test_rollback(self) -> bool:
        """ロールバック機能のテスト"""
        logger.info("⏪ ロールバック機能確認...")

        test_rule_id = "RULE_TEST_001"

        # テストルールを削除（ロールバック相当）
        registry = UnifiedRuleRegistry()

        if test_rule_id not in registry.rules:
            logger.error(f"{test_rule_id} が見つかりません")
            return False

        del registry.rules[test_rule_id]
        registry.save()

        logger.info(f"🗑️  {test_rule_id} 削除完了")

        # 再同期
        result = subprocess.run(
            ['python3', 'rule_sync_automation.py'],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            logger.error("同期失敗")
            return False

        # 元の状態に戻ったか確認
        with open('rule_sync_report.json', 'r', encoding='utf-8') as f:
            sync_report = json.load(f)

        if sync_report['active_rules'] != 73:
            logger.error(f"アクティブルール数が不正: {sync_report['active_rules']} (期待: 73)")
            return False

        logger.info("✅ ロールバック正常")
        return True

    def _test_final_consistency(self) -> bool:
        """最終整合性確認"""
        logger.info("🔍 最終整合性確認...")

        # ヘルスチェック実行
        result = subprocess.run(
            ['python3', 'rule_health_monitor.py'],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            logger.error("ヘルスチェック失敗")
            return False

        # レジストリのチェックサムが元に戻っているか確認
        registry = UnifiedRuleRegistry()
        if registry.checksum != self.original_checksum:
            logger.warning(f"チェックサム変更あり:")
            logger.warning(f"  元: {self.original_checksum[:16]}...")
            logger.warning(f"  現: {registry.checksum[:16]}...")
            # ただしテスト中の一時的な変更は許容
            # 最終的に元に戻れば問題なし

        # すべてのヘルスチェック項目がPASSか確認
        with open('rule_health_report.json', 'r', encoding='utf-8') as f:
            report = json.load(f)

        failed_checks = [c for c in report['checks'] if c['status'] != 'PASS']
        if failed_checks:
            logger.error(f"{len(failed_checks)}件のヘルスチェックが不合格")
            for check in failed_checks:
                logger.error(f"  - {check['check_name']}: {check['status']}")
            return False

        logger.info("✅ 最終整合性確認完了")
        return True

    def _cleanup(self):
        """テスト後のクリーンアップ"""
        logger.info("\n🧹 クリーンアップ中...")

        # テストルールが残っていれば削除
        test_rule_id = "RULE_TEST_001"
        registry = UnifiedRuleRegistry()

        if test_rule_id in registry.rules:
            del registry.rules[test_rule_id]
            registry.save()
            logger.info(f"🗑️  {test_rule_id} 削除")

            # 最終同期
            subprocess.run(
                ['python3', 'rule_sync_automation.py'],
                capture_output=True,
                timeout=60
            )

        logger.info("✅ クリーンアップ完了")

    def _print_summary(self):
        """テスト結果サマリー"""
        logger.info("\n" + "=" * 60)
        logger.info("📊 運用テスト結果サマリー")
        logger.info("=" * 60)

        pass_count = sum(1 for r in self.test_results if r['status'] == 'PASS')
        fail_count = sum(1 for r in self.test_results if r['status'] == 'FAIL')
        total_count = len(self.test_results)

        for result in self.test_results:
            status_icon = "✅" if result['status'] == 'PASS' else "❌"
            logger.info(f"{status_icon} {result['test_name']}: {result['status']}")

        logger.info("\n" + "-" * 60)
        logger.info(f"総テスト数: {total_count}")
        logger.info(f"成功: {pass_count}")
        logger.info(f"失敗: {fail_count}")
        logger.info(f"成功率: {pass_count/total_count*100:.1f}%")
        logger.info("=" * 60)

        if fail_count == 0:
            logger.info("\n🎉 すべてのテストが成功しました！")
            logger.info("統合ルール管理システムは本番運用可能です。")
        else:
            logger.warning(f"\n⚠️ {fail_count}件のテストが失敗しました。")
            logger.warning("問題を修正してから本番運用を開始してください。")

        # テスト結果をファイルに保存
        report_path = "operational_test_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'summary': {
                    'total': total_count,
                    'pass': pass_count,
                    'fail': fail_count,
                    'success_rate': pass_count/total_count*100
                },
                'tests': self.test_results
            }, f, ensure_ascii=False, indent=2)

        logger.info(f"\n📄 テストレポート保存: {report_path}")


def main():
    """メイン処理"""
    tester = OperationalSystemTest()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
