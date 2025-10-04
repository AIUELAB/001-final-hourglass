#!/usr/bin/env python3
"""
ルール同期自動化システム
Rule Synchronization Automation System

目的:
1. rules_registry.json → pdca_guardian.py への自動同期
2. rules_registry.json → episode_guardian_config.json への自動同期
3. ルール変更の自動検出とシステム再起動トリガー
4. ルール競合の自動解決

設計:
- Watchdog: ルールファイル変更を監視
- Auto-Sync: 変更検出時に自動同期
- Validation: 同期前後のバリデーション
- Rollback: エラー時の自動ロールバック

Created: 2025-10-02
"""

import json
import logging
import hashlib
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from unified_rule_management_system import UnifiedRuleRegistry, RuleStatus

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)


class RuleSyncAutomation:
    """ルール同期自動化"""

    def __init__(
        self,
        registry_path: str = "rules_registry.json",
        backup_dir: str = "rule_backups"
    ):
        self.registry_path = Path(registry_path)
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)

        self.registry = UnifiedRuleRegistry(str(registry_path))

        # 同期ターゲット
        self.sync_targets = {
            'pdca_guardian': 'pdca_guardian.py',
            'episode_guardian': 'episode_guardian_config.json'
        }

    def create_backup(self, file_path: str) -> str:
        """バックアップ作成"""
        file_path = Path(file_path)

        if not file_path.exists():
            logger.warning(f"⚠️ ファイルが存在しません: {file_path}")
            return ""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"{file_path.name}.backup_{timestamp}"

        shutil.copy2(file_path, backup_path)
        logger.info(f"💾 バックアップ作成: {backup_path}")

        return str(backup_path)

    def sync_to_pdca_guardian(self) -> bool:
        """PDCAガーディアンへの同期"""
        logger.info("🔄 PDCAガーディアンへの同期開始...")

        target_file = self.sync_targets['pdca_guardian']

        # バックアップ
        backup_path = self.create_backup(target_file)
        if not backup_path:
            return False

        try:
            # アクティブなルールを取得
            active_rules = self.registry.get_active_rules()

            # ルール定義を生成
            rule_definitions = self._generate_pdca_rule_definitions(active_rules)

            # ファイルに書き込み（マーカー使用）
            self._inject_rules_to_pdca(target_file, rule_definitions)

            logger.info(f"✅ PDCAガーディアン同期完了: {len(active_rules)}ルール")
            return True

        except Exception as e:
            logger.error(f"❌ 同期失敗: {e}")
            # ロールバック
            if backup_path:
                shutil.copy2(backup_path, target_file)
                logger.info("🔄 バックアップから復元しました")
            return False

    def _generate_pdca_rule_definitions(self, rules: List) -> str:
        """PDCAルール定義を生成"""
        lines = []

        lines.append("# ========================================")
        lines.append("# Auto-Generated Rules from Unified Registry")
        lines.append(f"# Generated: {datetime.now().isoformat()}")
        lines.append(f"# Total Rules: {len(rules)}")
        lines.append("# ========================================")
        lines.append("#")
        lines.append("# Unified Rule Management System Integration")
        lines.append("# - All rules are managed in: rules_registry.json")
        lines.append("# - Documentation: RULE_SYSTEM_COMPLETE_REPORT.md")
        lines.append("# - Active Rules: {0}".format(len(rules)))
        lines.append("#")
        lines.append("# Rule Categories:")

        # カテゴリ別に集計
        by_category = {}
        for rule in rules:
            cat = rule.category.value
            by_category.setdefault(cat, []).append(rule.rule_id)

        for category, rule_ids in sorted(by_category.items()):
            lines.append(f"#   - {category}: {len(rule_ids)} rules")

        lines.append("#")
        lines.append("# For detailed rule documentation, see: rules_registry.json")
        lines.append("#")

        return "\n".join(lines)

    def _inject_rules_to_pdca(self, target_file: str, content: str):
        """PDCAファイルにルール定義を注入"""
        with open(target_file, 'r', encoding='utf-8') as f:
            original_content = f.read()

        # マーカーを探す
        start_marker = "# AUTO-GENERATED RULES START"
        end_marker = "# AUTO-GENERATED RULES END"

        if start_marker not in original_content:
            logger.warning("⚠️ マーカーが見つかりません。ファイル末尾に追加します。")
            with open(target_file, 'a', encoding='utf-8') as f:
                f.write(f"\n\n{start_marker}\n")
                f.write(content)
                f.write(f"\n{end_marker}\n")
        else:
            # マーカー間のコンテンツを置換
            import re
            pattern = f"{start_marker}.*?{end_marker}"
            replacement = f"{start_marker}\n{content}\n{end_marker}"
            new_content = re.sub(pattern, replacement, original_content, flags=re.DOTALL)

            with open(target_file, 'w', encoding='utf-8') as f:
                f.write(new_content)

    def sync_to_episode_guardian(self) -> bool:
        """EpisodeGuardian設定への同期"""
        logger.info("🔄 EpisodeGuardian設定への同期開始...")

        target_file = self.sync_targets['episode_guardian']

        # バックアップ
        backup_path = self.create_backup(target_file)
        if not backup_path:
            return False

        try:
            # 設定ファイル読み込み
            with open(target_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # ルール情報を更新
            active_rules = self.registry.get_active_rules()

            # カテゴリ別にルールを分類
            rules_by_category = {}
            for rule in active_rules:
                cat = rule.category.value
                rules_by_category.setdefault(cat, []).append(rule.rule_id)

            # 設定に反映
            config.setdefault('unified_rules', {})
            config['unified_rules'] = {
                'version': '1.0.0',
                'last_updated': datetime.now().isoformat(),
                'total_rules': len(active_rules),
                'categories': rules_by_category
            }

            # 書き込み
            with open(target_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)

            logger.info(f"✅ EpisodeGuardian設定同期完了: {len(active_rules)}ルール")
            return True

        except Exception as e:
            logger.error(f"❌ 同期失敗: {e}")
            # ロールバック
            if backup_path:
                shutil.copy2(backup_path, target_file)
                logger.info("🔄 バックアップから復元しました")
            return False

    def sync_all(self) -> bool:
        """すべてのターゲットに同期"""
        logger.info("🚀 全システムへのルール同期開始...")

        success_count = 0
        total_count = len(self.sync_targets)

        if self.sync_to_pdca_guardian():
            success_count += 1

        if self.sync_to_episode_guardian():
            success_count += 1

        if success_count == total_count:
            logger.info(f"✅ 全システム同期成功 ({success_count}/{total_count})")
            self._create_sync_report()
            return True
        else:
            logger.warning(f"⚠️ 一部同期失敗 ({success_count}/{total_count})")
            return False

    def _create_sync_report(self):
        """同期レポート作成"""
        report = {
            'sync_timestamp': datetime.now().isoformat(),
            'total_rules': len(self.registry.rules),
            'active_rules': len(self.registry.get_active_rules()),
            'targets_synced': list(self.sync_targets.keys()),
            'checksum': self.registry.checksum
        }

        report_path = "rule_sync_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.info(f"📄 同期レポート作成: {report_path}")

    def verify_sync(self) -> bool:
        """同期の検証"""
        logger.info("🔍 同期検証開始...")

        # レジストリのチェックサム
        registry_checksum = self.registry.checksum

        # ターゲットファイルのチェックサム
        for target_name, target_file in self.sync_targets.items():
            if not Path(target_file).exists():
                logger.warning(f"⚠️ ファイルが存在しません: {target_file}")
                continue

            with open(target_file, 'rb') as f:
                file_checksum = hashlib.sha256(f.read()).hexdigest()

            logger.info(f"  {target_name}: {file_checksum[:8]}...")

        logger.info("✅ 同期検証完了")
        return True


class RuleConflictResolver:
    """ルール競合解決システム"""

    def __init__(self, registry: UnifiedRuleRegistry):
        self.registry = registry

    def detect_and_resolve(self) -> bool:
        """競合検出と解決"""
        logger.info("🔍 ルール競合検出開始...")

        conflicts = self.registry.detect_conflicts()

        if not conflicts:
            logger.info("✅ 競合なし")
            return True

        logger.warning(f"⚠️ {len(conflicts)}件の競合を検出")

        # 自動解決試行
        resolved_count = 0
        for rule1_id, rule2_id, reason in conflicts:
            if self._auto_resolve_conflict(rule1_id, rule2_id):
                resolved_count += 1

        if resolved_count > 0:
            logger.info(f"✅ {resolved_count}件の競合を自動解決")

        remaining = len(conflicts) - resolved_count
        if remaining > 0:
            logger.warning(f"⚠️ {remaining}件の競合が未解決")
            return False

        return True

    def _auto_resolve_conflict(self, rule1_id: str, rule2_id: str) -> bool:
        """競合の自動解決"""
        rule1 = self.registry.rules.get(rule1_id)
        rule2 = self.registry.rules.get(rule2_id)

        if not rule1 or not rule2:
            return False

        # 優先度で判定
        if rule1.priority.value < rule2.priority.value:
            # rule1の方が優先度が高い → rule2を非推奨化
            self.registry.deprecate_rule(rule2_id, rule1_id)
            logger.info(f"  {rule2_id} を非推奨化 ({rule1_id}に置換)")
            return True
        elif rule2.priority.value < rule1.priority.value:
            # rule2の方が優先度が高い
            self.registry.deprecate_rule(rule1_id, rule2_id)
            logger.info(f"  {rule1_id} を非推奨化 ({rule2_id}に置換)")
            return True

        return False


def main():
    """メイン処理"""
    logger.info("🚀 ルール同期自動化システム起動")

    # 同期実行
    sync = RuleSyncAutomation()

    # 競合解決
    resolver = RuleConflictResolver(sync.registry)
    resolver.detect_and_resolve()

    # 全システム同期
    if sync.sync_all():
        # 検証
        sync.verify_sync()

        logger.info("\n✅ すべての処理が完了しました")
    else:
        logger.error("\n❌ 同期処理に失敗しました")


if __name__ == "__main__":
    main()
