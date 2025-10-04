#!/usr/bin/env python3
"""
残存問題の修正
Fix Remaining Issues

問題:
1. RULE_160の名前に古い「150-250」が残存
"""

import logging
from unified_rule_management_system import UnifiedRuleRegistry
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)


def main():
    """残存問題を修正"""
    logger.info("=" * 60)
    logger.info("残存問題の修正")
    logger.info("=" * 60)

    registry = UnifiedRuleRegistry()

    # RULE_160の名前を更新
    logger.info("\nRULE_160の名前を132-250に更新...")

    rule_160_updates = {
        'name': '文字数制限（132-250）',
        'updated_at': datetime.now().isoformat()
    }

    success = registry.update_rule('RULE_160', rule_160_updates)
    if success:
        logger.info("✅ RULE_160の名前を更新完了")
    else:
        logger.error("❌ RULE_160の更新に失敗")

    logger.info("\n" + "=" * 60)
    logger.info("✅ 修正完了")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
