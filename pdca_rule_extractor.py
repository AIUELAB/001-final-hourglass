#!/usr/bin/env python3
"""
PDCAガーディアンルール抽出ツール
PDCA Guardian Rule Extractor

目的:
- pdca_guardian.pyから全ルール(RULE_001-169)を抽出
- unified_rule_management_systemへマイグレーション
- ルール定義の正規化とバリデーション

Created: 2025-10-02
"""

import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from unified_rule_management_system import (
    Rule, RuleCategory, RulePriority, RuleStatus,
    UnifiedRuleRegistry
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)


class PDCARuleExtractor:
    """PDCAガーディアンルール抽出器"""

    def __init__(self, source_file: str = "pdca_guardian.py"):
        self.source_file = Path(source_file)
        self.rules: Dict[str, Dict] = {}

    def extract_all_rules(self) -> List[Dict]:
        """すべてのルールを抽出"""
        logger.info(f"🔍 ルール抽出開始: {self.source_file}")

        with open(self.source_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # ViolationTypeからルールタイプを抽出
        violation_types = self._extract_violation_types(content)

        # RULE_XXXパターンでルールを抽出
        rule_patterns = self._extract_rule_patterns(content)

        # ルール定義を抽出
        rule_definitions = self._extract_rule_definitions(content)

        # 統合
        all_rules = self._merge_rule_info(violation_types, rule_patterns, rule_definitions)

        logger.info(f"✅ ルール抽出完了: {len(all_rules)}件")
        return all_rules

    def _extract_violation_types(self, content: str) -> Dict[str, str]:
        """ViolationTypeからルールタイプを抽出"""
        types = {}

        # class ViolationType(Enum): の後を探す
        pattern = r'class ViolationType\(Enum\):(.*?)(?=\n    [A-Z_]+ = |class |def )'
        match = re.search(pattern, content, re.DOTALL)

        if match:
            enum_content = match.group(1)

            # 各エントリーを抽出
            entry_pattern = r'([A-Z_]+)\s*=\s*"([^"]+)"'
            for entry_match in re.finditer(entry_pattern, enum_content):
                type_name = entry_match.group(1)
                description = entry_match.group(2)
                types[type_name] = description

        logger.info(f"  ViolationType: {len(types)}個")
        return types

    def _extract_rule_patterns(self, content: str) -> Dict[str, List[str]]:
        """RULE_XXXパターンを抽出"""
        patterns = {}

        # RULE_XXXを全文検索
        rule_pattern = r'RULE_(\d+)'
        matches = re.finditer(rule_pattern, content)

        for match in matches:
            rule_num = match.group(1)
            rule_id = f"RULE_{rule_num}"

            # 前後のコンテキストを取得
            start = max(0, match.start() - 200)
            end = min(len(content), match.end() + 200)
            context = content[start:end]

            patterns.setdefault(rule_id, []).append(context)

        logger.info(f"  RULE_XXXパターン: {len(patterns)}個")
        return patterns

    def _extract_rule_definitions(self, content: str) -> Dict[str, Dict]:
        """ルール定義を抽出（コメントから）"""
        definitions = {}

        # ルール定義パターン: # RULE_XXX: 説明文
        pattern = r'# (RULE_\d+):?\s*([^\n]+)'
        matches = re.finditer(pattern, content)

        for match in matches:
            rule_id = match.group(1)
            description = match.group(2).strip()

            definitions[rule_id] = {
                'description': description,
                'source_line': content[:match.start()].count('\n') + 1
            }

        logger.info(f"  ルール定義: {len(definitions)}個")
        return definitions

    def _merge_rule_info(
        self,
        violation_types: Dict[str, str],
        rule_patterns: Dict[str, List[str]],
        rule_definitions: Dict[str, Dict]
    ) -> List[Dict]:
        """ルール情報をマージ"""

        merged = []

        # すべてのRULE_XXXを収集
        all_rule_ids = set(rule_patterns.keys()) | set(rule_definitions.keys())

        for rule_id in sorted(all_rule_ids):
            rule_num = int(rule_id.split('_')[1])

            # 説明文を取得
            description = rule_definitions.get(rule_id, {}).get('description', '')

            if not description:
                # パターンから推測
                contexts = rule_patterns.get(rule_id, [])
                if contexts:
                    description = self._infer_description_from_context(contexts[0])

            # カテゴリを推測
            category = self._infer_category(rule_id, description)

            # 優先度を推測
            priority = self._infer_priority(rule_id, description)

            merged.append({
                'rule_id': rule_id,
                'description': description,
                'category': category,
                'priority': priority,
                'rule_num': rule_num
            })

        return merged

    def _infer_description_from_context(self, context: str) -> str:
        """コンテキストから説明を推測"""
        # コメント行を探す
        lines = context.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('#') and 'RULE' in line:
                # コメントから説明を抽出
                description = line.split(':', 1)[-1].strip()
                if description and not description.startswith('RULE'):
                    return description

        return "（説明なし）"

    def _infer_category(self, rule_id: str, description: str) -> RuleCategory:
        """カテゴリを推測"""
        desc_lower = description.lower()

        # キーワードマッチング
        if any(kw in desc_lower for kw in ['api', 'dummy', 'ダミー']):
            return RuleCategory.API_USAGE
        elif any(kw in desc_lower for kw in ['エピソード', 'episode', '文字数', '長さ']):
            return RuleCategory.EPISODE_FORMAT
        elif any(kw in desc_lower for kw in ['具体', '感銘', '事実', 'ハルシネーション']):
            return RuleCategory.EPISODE_CONTENT
        elif any(kw in desc_lower for kw in ['エンティティ', 'entity', 'グループ', '架空']):
            return RuleCategory.ENTITY_TYPE
        elif any(kw in desc_lower for kw in ['表示名', 'display', '括弧']):
            return RuleCategory.DISPLAY_NAME
        elif any(kw in desc_lower for kw in ['カラム', 'column', 'スキーマ', 'schema']):
            return RuleCategory.DATABASE_SCHEMA
        elif any(kw in desc_lower for kw in ['品質', 'quality', '削除率', 'データ']):
            return RuleCategory.DATA_QUALITY
        else:
            return RuleCategory.DATA_QUALITY  # デフォルト

    def _infer_priority(self, rule_id: str, description: str) -> RulePriority:
        """優先度を推測"""
        desc_lower = description.lower()

        # キーワードマッチング
        if any(kw in desc_lower for kw in ['critical', '致命', '即座', '必須', 'api未使用']):
            return RulePriority.CRITICAL
        elif any(kw in desc_lower for kw in ['重要', 'important', '警告', '異常']):
            return RulePriority.HIGH
        elif any(kw in desc_lower for kw in ['推奨', 'should', '確認']):
            return RulePriority.MEDIUM
        else:
            return RulePriority.MEDIUM  # デフォルト

    def migrate_to_registry(self, registry: UnifiedRuleRegistry):
        """レジストリにマイグレーション"""
        logger.info("🔄 PDCAルールをレジストリにマイグレーション...")

        all_rules = self.extract_all_rules()

        migrated_count = 0
        for rule_data in all_rules:
            rule = Rule(
                rule_id=rule_data['rule_id'],
                name=rule_data['description'][:50],  # 最初の50文字
                description=rule_data['description'],
                category=rule_data['category'],
                priority=rule_data['priority'],
                status=RuleStatus.ACTIVE,
                source_file='pdca_guardian.py',
                function_name=None,
                created_at='2025-10-02T00:00:00',
                updated_at='2025-10-02T00:00:00',
                version='v1.0.0',
                related_rules=[],
                replaces=None,
                replaced_by=None,
                tags=['pdca', 'migrated'],
                examples=[]
            )

            if registry.add_rule(rule):
                migrated_count += 1

        logger.info(f"✅ マイグレーション完了: {migrated_count}/{len(all_rules)}件")


def main():
    """メイン処理"""
    logger.info("🚀 PDCAルール抽出・マイグレーション開始")

    # 抽出
    extractor = PDCARuleExtractor()
    rules = extractor.extract_all_rules()

    # 統計
    logger.info(f"\n📊 抽出結果:")
    logger.info(f"  総ルール数: {len(rules)}件")

    # カテゴリ別
    by_category = {}
    for rule in rules:
        cat = rule['category'].value
        by_category[cat] = by_category.get(cat, 0) + 1

    for cat, count in sorted(by_category.items()):
        logger.info(f"  {cat}: {count}件")

    # レジストリにマイグレーション
    registry = UnifiedRuleRegistry()
    extractor.migrate_to_registry(registry)

    # ドキュメント生成
    registry.export_to_markdown()

    logger.info("\n✅ すべての処理が完了しました")


if __name__ == "__main__":
    main()
