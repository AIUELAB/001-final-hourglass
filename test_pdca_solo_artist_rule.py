#!/usr/bin/env python3
"""
PDCAガーディアン Rule 098 テスト
ソロアーティスト冗長括弧チェックの動作確認
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


def test_solo_artist_rule():
    """Rule 098のテスト"""
    logger.info("=" * 60)
    logger.info("🧪 PDCA Guardian Rule 098 テスト開始")
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
    
    for csv_file in test_files:
        if not Path(csv_file).exists():
            logger.warning(f"  ⚠️ ファイルが存在しません: {csv_file}")
            continue
        
        logger.info(f"\n📝 チェック中: {csv_file}")
        
        # Rule 098実行
        violations = guardian.check_solo_artist_brackets(csv_file)
        
        if violations:
            logger.warning(f"  ❌ 違反検出: {len(violations)}件")
            for v in violations:
                logger.warning(f"    - {v.message}")
                logger.info(f"      提案: {v.suggestion}")
        else:
            logger.info(f"  ✅ 違反なし")
        
        total_violations += len(violations)
    
    # 結果サマリー
    logger.info("\n" + "=" * 60)
    logger.info("📊 テスト結果サマリー")
    logger.info("=" * 60)
    
    if total_violations == 0:
        logger.info("✅ すべてのファイルでRule 098違反なし")
        logger.info("   修正が正しく適用されています")
    else:
        logger.error(f"❌ 合計 {total_violations}件の違反が残っています")
        logger.error("   再度修正が必要です")
    
    return total_violations == 0


if __name__ == "__main__":
    success = test_solo_artist_rule()
    sys.exit(0 if success else 1)