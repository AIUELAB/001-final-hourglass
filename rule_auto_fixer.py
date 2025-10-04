#!/usr/bin/env python3
"""
ルール矛盾自動修正システム
Rule Contradiction Auto-Fixer

目的:
1. 検出された矛盾を自動修正
2. 文字数範囲の統一
3. 重複ルールの統合
4. 説明文の自動生成

Created: 2025-10-02
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import asdict
from unified_rule_management_system import UnifiedRuleRegistry, Rule, RulePriority, RuleStatus

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)


class RuleAutoFixer:
    """ルール矛盾自動修正器"""

    def __init__(self):
        self.registry = UnifiedRuleRegistry()
        self.fixes_applied = []
        self.pdca_source = self._load_pdca_source()

    def _load_pdca_source(self) -> str:
        """pdca_guardian.pyのソースコードをロード"""
        pdca_path = Path("pdca_guardian.py")
        if pdca_path.exists():
            with open(pdca_path, 'r', encoding='utf-8') as f:
                return f.read()
        return ""

    def fix_all_contradictions(self):
        """すべての矛盾を自動修正"""
        logger.info("🔧 ルール矛盾自動修正開始...\n")

        # 1. 文字数範囲の統一
        self.fix_character_length_conflicts()

        # 2. 重複ルールの統合
        self.merge_duplicate_rules()

        # 3. 説明文の自動生成
        self.add_missing_descriptions()

        # 4. 優先度の整理
        self.fix_priority_conflicts()

        # レポート生成（レジストリは各修正で自動保存されている）
        self._generate_fix_report()

        logger.info("\n✅ 矛盾修正完了")

    def fix_character_length_conflicts(self):
        """文字数範囲を132-250に統一"""
        logger.info("=" * 60)
        logger.info("1. 文字数範囲の統一")
        logger.info("=" * 60)

        # 統一基準: 132-250文字（2025-09-22の更新に合わせる）
        STANDARD_MIN = 132
        STANDARD_MAX = 250

        # 対象ルール
        target_rules = ['FORMAT_001', 'RULE_151', 'RULE_160']
        fixed_count = 0

        for rule_id in target_rules:
            if rule_id in self.registry.rules:
                rule = self.registry.rules[rule_id]

                # 説明文を更新
                new_description = self._update_character_length_description(
                    rule.description, STANDARD_MIN, STANDARD_MAX
                )

                if new_description != rule.description:
                    updates = {
                        'description': new_description,
                        'updated_at': self._get_timestamp()
                    }

                    # FORMAT_001の優先度をHIGHに維持（他はMEDIUM）
                    if rule_id == 'FORMAT_001':
                        updates['priority'] = RulePriority.HIGH

                    self.registry.update_rule(rule_id, updates)

                    logger.info(f"✅ {rule_id}: 文字数範囲を{STANDARD_MIN}-{STANDARD_MAX}に統一")

                    self.fixes_applied.append({
                        'type': 'character_length_unification',
                        'rule_id': rule_id,
                        'old_description': rule.description[:50] + '...',
                        'new_description': new_description[:50] + '...'
                    })
                    fixed_count += 1

        logger.info(f"\n修正完了: {fixed_count}件\n")

    def _update_character_length_description(self, description: str, min_len: int, max_len: int) -> str:
        """文字数範囲の説明を更新"""
        # 既存の文字数範囲を新しい範囲に置換
        patterns = [
            r'\d{2,3}-\d{2,3}文字',
            r'\d{2,3}文字以上\d{2,3}文字以下',
            r'最小\d{2,3}.*最大\d{2,3}',
        ]

        new_range = f"{min_len}-{max_len}文字"

        for pattern in patterns:
            description = re.sub(pattern, new_range, description)

        # 更新履歴を追加
        if '2025-09-22更新' not in description:
            description += f"\n（2025-10-02更新: 文字数範囲を{min_len}-{max_len}に統一）"

        return description

    def merge_duplicate_rules(self):
        """重複ルールを統合"""
        logger.info("=" * 60)
        logger.info("2. 重複ルールの統合")
        logger.info("=" * 60)

        # ENTITY_TYPE_001 と RULE_154 の統合
        self._merge_entity_type_rules()

        logger.info("")

    def _merge_entity_type_rules(self):
        """グループ名チェックルールを統合"""
        source_id = 'ENTITY_TYPE_001'
        target_id = 'RULE_154'

        if source_id not in self.registry.rules or target_id not in self.registry.rules:
            logger.warning(f"⚠️ {source_id} または {target_id} が見つかりません")
            return

        source_rule = self.registry.rules[source_id]
        target_rule = self.registry.rules[target_id]

        # 統合された説明文
        merged_description = f"""グループ名個人化チェック

【目的】
グループ名が個人（person）として誤って登録されていないかチェック。

【チェック項目】
1. entity_type が 'person' でperson_nameにグループ名が使用されていないか
2. person_name_display でグループ名を正しく表記しているか
3. 複数人組のグループを個人として扱っていないか

【元のルール】
- {source_id}: {source_rule.description[:50]}...
- {target_id}: {target_rule.description[:50]}...

（2025-10-02統合: {source_id}と{target_id}を統合）
"""

        # ENTITY_TYPE_001を強化版として更新
        updates = {
            'description': merged_description,
            'priority': RulePriority.CRITICAL,
            'replaces': target_id,
            'updated_at': self._get_timestamp()
        }

        self.registry.update_rule(source_id, updates)

        # RULE_154を非推奨化
        self.registry.deprecate_rule(target_id, replacement_id=source_id)

        logger.info(f"✅ {source_id} と {target_id} を統合")
        logger.info(f"   {target_id} は非推奨化（{source_id}に置換）")

        self.fixes_applied.append({
            'type': 'rule_merge',
            'source_id': source_id,
            'target_id': target_id,
            'action': 'merged and deprecated'
        })

    def add_missing_descriptions(self):
        """説明文を自動生成"""
        logger.info("=" * 60)
        logger.info("3. 説明文の自動生成")
        logger.info("=" * 60)

        # 説明なしルールを検索
        no_description_rules = [
            rule_id for rule_id, rule in self.registry.rules.items()
            if rule.description == "（説明なし）"
        ]

        logger.info(f"説明なしルール: {len(no_description_rules)}件")

        generated_count = 0

        for rule_id in no_description_rules[:10]:  # 最初の10件を処理
            description = self._generate_description_from_implementation(rule_id)

            if description and description != "（説明なし）":
                updates = {
                    'description': description + "\n（自動生成された説明 - 要レビュー）",
                    'updated_at': self._get_timestamp()
                }

                self.registry.update_rule(rule_id, updates)

                logger.info(f"✅ {rule_id}: 説明を自動生成")

                self.fixes_applied.append({
                    'type': 'description_generation',
                    'rule_id': rule_id,
                    'description': description[:50] + '...'
                })
                generated_count += 1

        logger.info(f"\n自動生成完了: {generated_count}件")
        logger.info(f"残り: {len(no_description_rules) - generated_count}件（手動レビュー推奨）\n")

    def _generate_description_from_implementation(self, rule_id: str) -> str:
        """実装コードから説明を自動生成"""
        # pdca_guardian.pyから該当ルールの実装を検索
        pattern = rf"{rule_id}[^\n]*\n([^\n]{{50,200}})"
        match = re.search(pattern, self.pdca_source)

        if not match:
            return "（説明なし）"

        implementation_snippet = match.group(1).strip()

        # キーワードから説明を推定
        if 'calibrated_score' in implementation_snippet:
            return f"{rule_id}: calibrated_scoreフィールドの使用に関するチェック"
        elif 'API' in implementation_snippet or 'api' in implementation_snippet:
            return f"{rule_id}: API関連の検証ルール"
        elif 'ダミー' in implementation_snippet:
            return f"{rule_id}: ダミーデータの使用禁止チェック"
        elif 'エピソード' in implementation_snippet:
            return f"{rule_id}: エピソード品質に関するルール"
        elif '文字数' in implementation_snippet or 'length' in implementation_snippet:
            return f"{rule_id}: 文字数制限に関するルール"
        else:
            return f"{rule_id}: {implementation_snippet[:50]}..."

    def fix_priority_conflicts(self):
        """優先度の矛盾を修正"""
        logger.info("=" * 60)
        logger.info("4. 優先度の整理")
        logger.info("=" * 60)

        # RULE_101をカテゴリヘッダーとして特別扱い
        if 'RULE_101' in self.registry.rules:
            updates = {
                'description': 'エピソード関連の違反タイプ（RULE_101-108のカテゴリヘッダー）',
                'priority': RulePriority.LOW,  # カテゴリヘッダーなので優先度を下げる
                'tags': ['category_header', 'organizational'],
                'updated_at': self._get_timestamp()
            }

            self.registry.update_rule('RULE_101', updates)

            logger.info("✅ RULE_101: カテゴリヘッダーとして再定義")

            self.fixes_applied.append({
                'type': 'priority_fix',
                'rule_id': 'RULE_101',
                'action': 'marked as category header'
            })

        logger.info("")

    def _get_timestamp(self) -> str:
        """タイムスタンプ取得"""
        from datetime import datetime
        return datetime.now().isoformat()

    def _generate_fix_report(self):
        """修正レポート生成"""
        logger.info("=" * 60)
        logger.info("📊 修正レポート")
        logger.info("=" * 60)

        total_fixes = len(self.fixes_applied)
        logger.info(f"総修正数: {total_fixes}件\n")

        # タイプ別集計
        by_type = {}
        for fix in self.fixes_applied:
            fix_type = fix['type']
            by_type.setdefault(fix_type, []).append(fix)

        for fix_type, fixes in by_type.items():
            logger.info(f"  {fix_type}: {len(fixes)}件")

        # 詳細をJSON出力
        report = {
            'timestamp': self._get_timestamp(),
            'total_fixes': total_fixes,
            'by_type': {k: len(v) for k, v in by_type.items()},
            'fixes': self.fixes_applied
        }

        with open("rule_fixes_report.json", 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.info(f"\n📄 詳細レポート: rule_fixes_report.json")


def main():
    """メイン処理"""
    fixer = RuleAutoFixer()
    fixer.fix_all_contradictions()

    logger.info("\n" + "=" * 60)
    logger.info("✅ すべての矛盾修正が完了しました")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
