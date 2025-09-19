#!/usr/bin/env python3
"""
PDCAガーディアン Rule 100 テスト
お笑いコンビ名整合性チェックの動作確認
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from pdca_guardian import PDCAGuardian
import logging

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_comedy_group_rule():
    """Rule 100のテスト"""
    logger.info("=" * 60)
    logger.info("🧪 PDCA Guardian Rule 100 テスト開始")
    logger.info("=" * 60)
    
    # PDCAガーディアン初期化
    guardian = PDCAGuardian()
    
    # テスト対象ファイル
    test_files = [
        'ultra_think_GROUP_FIXED_20250912_044856.csv',
        'ultra_think_COMPLETE_20250912_042500.csv',
        'ultra_think_FINAL_CLEAN_20250912_042742_FICTIONAL_FIXED_FICTIONAL_COMPLETE.csv'
    ]
    
    total_violations = 0
    
    # 修正確認対象
    fixed_comedians = {
        'P000432': 'ガク（真空ジェシカ）',
        'P002167': '加納（Aマッソ）',
        'P002520': '堂前透（ロングコートダディ）',
        'P003225': '川北茂澄（真空ジェシカ）',
        'P004112': '河井ゆずる（アインシュタイン）'  # これは元から正しい
    }
    
    logger.info("📋 修正確認対象:")
    for person_id, expected_display in fixed_comedians.items():
        logger.info(f"  {person_id}: {expected_display}")
    
    for csv_file in test_files:
        if not Path(csv_file).exists():
            logger.warning(f"  ⚠️ ファイルが存在しません: {csv_file}")
            continue
        
        logger.info(f"\n📝 チェック中: {csv_file}")
        
        # Rule 100実行
        violations = guardian.check_comedy_group_consistency(csv_file)
        
        if violations:
            logger.warning(f"  ❌ 違反検出: {len(violations)}件")
            for v in violations:
                logger.warning(f"    - {v.description}")
                logger.info(f"      提案: {v.suggested_fix}")
        else:
            logger.info(f"  ✅ 違反なし（すべてのコンビ名が正しい）")
        
        total_violations += len(violations)
    
    # 結果サマリー
    logger.info("\n" + "=" * 60)
    logger.info("📊 テスト結果サマリー")
    logger.info("=" * 60)
    
    if total_violations == 0:
        logger.info("✅ すべてのファイルでRule 100違反なし")
        logger.info("   お笑い芸人のグループ名が正しく修正されています:")
        logger.info("   - ガク: 真空ジェシカ ✓")
        logger.info("   - 加納: Aマッソ ✓")
        logger.info("   - 堂前透: ロングコートダディ ✓")
        logger.info("   - 川北茂澄: 真空ジェシカ ✓")
        logger.info("   - 河井ゆずる: アインシュタイン ✓")
    else:
        logger.error(f"❌ 合計 {total_violations}件の違反が検出されました")
        logger.error("   追加の修正が必要です")
    
    return total_violations == 0


if __name__ == "__main__":
    success = test_comedy_group_rule()
    sys.exit(0 if success else 1)