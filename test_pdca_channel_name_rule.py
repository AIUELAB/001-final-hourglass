#!/usr/bin/env python3
"""
PDCAガーディアン Rule 099 テスト
チャンネル名誤登録チェックの動作確認
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


def test_channel_name_rule():
    """Rule 099のテスト"""
    logger.info("=" * 60)
    logger.info("🧪 PDCA Guardian Rule 099 テスト開始")
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
        
        # Rule 099実行
        violations = guardian.check_channel_names(csv_file)
        
        if violations:
            logger.warning(f"  ❌ 違反検出: {len(violations)}件")
            for v in violations:
                logger.warning(f"    - {v.description}")
                logger.info(f"      提案: {v.suggested_fix}")
        else:
            logger.info(f"  ✅ 違反なし")
        
        total_violations += len(violations)
    
    # 結果サマリー
    logger.info("\n" + "=" * 60)
    logger.info("📊 テスト結果サマリー")
    logger.info("=" * 60)
    
    if total_violations == 0:
        logger.info("✅ すべてのファイルでRule 099違反なし")
        logger.info("   P001061（ヒカキンゲームズ）が正しく削除されています")
    else:
        logger.error(f"❌ 合計 {total_violations}件の違反が検出されました")
        logger.error("   追加のチャンネル名パターンが見つかりました")
    
    return total_violations == 0


if __name__ == "__main__":
    success = test_channel_name_rule()
    sys.exit(0 if success else 1)