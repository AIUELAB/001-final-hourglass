#!/usr/bin/env python3
"""
フェーズ2: 矛盾検出ロジックの改善
Phase 2: Improve Contradiction Detection Logic

改善内容:
1. deprecatedルールを除外
2. category_headerタグを持つルールを特別扱い
3. 文字数範囲チェックの精度向上
"""

import re
import logging
from typing import Dict, List, Set
from unified_rule_management_system import UnifiedRuleRegistry, RuleStatus

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)


def improve_priority_contradiction_detection():
    """優先度矛盾検出の改善版"""
    logger.info("=" * 60)
    logger.info("優先度矛盾検出ロジックの改善")
    logger.info("=" * 60)

    registry = UnifiedRuleRegistry()

    # 1. アクティブなルールのみを対象にする（deprecated除外）
    active_rules = {
        rule_id: rule for rule_id, rule in registry.rules.items()
        if rule.status == RuleStatus.ACTIVE
    }

    logger.info(f"\n対象ルール: {len(active_rules)}件")
    logger.info(f"除外（deprecated）: {len(registry.rules) - len(active_rules)}件")

    # 2. category_headerタグを持つルールを除外
    organizational_rules = {
        rule_id: rule for rule_id, rule in active_rules.items()
        if 'category_header' in rule.tags or 'organizational' in rule.tags
    }

    content_rules = {
        rule_id: rule for rule_id, rule in active_rules.items()
        if rule_id not in organizational_rules
    }

    logger.info(f"\nカテゴリヘッダー（除外）: {len(organizational_rules)}件")
    logger.info(f"実コンテンツルール: {len(content_rules)}件")

    # 3. 類似ルールを検出（content_rulesのみ）
    similar_groups = {}

    for rule_id, rule in content_rules.items():
        # キーワード抽出の精度向上
        keywords = extract_keywords_improved(rule.description)
        key = tuple(sorted(keywords))

        similar_groups.setdefault(key, []).append((rule_id, rule))

    # 4. 優先度矛盾のレポート
    contradictions_found = 0
    false_positives_eliminated = 0

    for key, rules in similar_groups.items():
        if len(rules) > 1:
            priorities = {rule.priority.value for _, rule in rules}
            if len(priorities) > 1:
                # 実際に矛盾しているか詳細チェック
                if is_genuine_priority_contradiction(rules):
                    logger.info(f"\n⚠️ 優先度矛盾検出:")
                    for rule_id, rule in rules:
                        logger.info(f"  {rule_id}: {rule.name} (優先度: {rule.priority.value})")
                    contradictions_found += 1
                else:
                    false_positives_eliminated += 1

    logger.info(f"\n✅ 真の矛盾: {contradictions_found}件")
    logger.info(f"✅ 誤検知除外: {false_positives_eliminated}件")


def extract_keywords_improved(text: str) -> Set[str]:
    """改善されたキーワード抽出"""
    keywords = set()

    # より精密なキーワードリスト
    important_phrases = [
        'エピソード文字数', 'エピソード品質', 'エピソード内容',
        'API使用', 'ダミーデータ', 'calibrated_score',
        '品質妥協', 'グループ名個人化', '表示名括弧',
        '文字数制限', '具体性チェック', '感銘要素',
        '歴史的重要性', '世界的偉業', 'バッチ処理'
    ]

    for phrase in important_phrases:
        if phrase in text:
            keywords.add(phrase)

    return keywords


def is_genuine_priority_contradiction(rules: List[tuple]) -> bool:
    """真の優先度矛盾かどうか判定"""
    # ルール名の類似度をチェック
    names = [rule.name for _, rule in rules]

    # 明らかに異なる機能の場合はfalse
    if len(set(names)) == len(names):
        return False

    # 説明の最初の50文字が類似している場合はtrue
    descriptions_start = [rule.description[:50] for _, rule in rules]
    if len(set(descriptions_start)) < len(descriptions_start):
        return True

    return False


def improve_character_length_detection():
    """文字数範囲矛盾検出の改善版"""
    logger.info("\n" + "=" * 60)
    logger.info("文字数範囲矛盾検出ロジックの改善")
    logger.info("=" * 60)

    registry = UnifiedRuleRegistry()

    # 文字数に関するルールを検出
    length_rules = {}
    for rule_id, rule in registry.rules.items():
        if rule.status != RuleStatus.ACTIVE:
            continue

        # より精密な文字数パターン検出
        length_pattern = r'(\d{2,3})-(\d{2,3})\s*文字'
        matches = re.findall(length_pattern, rule.description)

        if matches:
            length_rules[rule_id] = {
                'name': rule.name,
                'ranges': matches,
                'description_snippet': rule.description[:100]
            }

    logger.info(f"\n文字数関連ルール: {len(length_rules)}件")

    # 統一基準チェック
    STANDARD_RANGE = ('132', '250')

    for rule_id, info in length_rules.items():
        for range_tuple in info['ranges']:
            if range_tuple != STANDARD_RANGE:
                logger.info(f"\n⚠️ 文字数範囲が標準と異なる:")
                logger.info(f"  {rule_id}: {info['name']}")
                logger.info(f"  検出範囲: {range_tuple[0]}-{range_tuple[1]}文字")
                logger.info(f"  標準範囲: {STANDARD_RANGE[0]}-{STANDARD_RANGE[1]}文字")
            else:
                logger.info(f"\n✅ 文字数範囲が標準に準拠:")
                logger.info(f"  {rule_id}: {info['name']} ({range_tuple[0]}-{range_tuple[1]}文字)")


def main():
    """メイン処理"""
    logger.info("=" * 60)
    logger.info("フェーズ2: 矛盾検出ロジック改善開始")
    logger.info("=" * 60)

    # 1. 優先度矛盾検出の改善
    improve_priority_contradiction_detection()

    # 2. 文字数範囲矛盾検出の改善
    improve_character_length_detection()

    logger.info("\n" + "=" * 60)
    logger.info("✅ フェーズ2完了")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
