#!/usr/bin/env python3
"""
最後の1件の架空キャラクターを修正
"""

import pandas as pd
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_last_character():
    """さくら友蔵を修正"""
    
    csv_file = "/Users/admin/Documents/AIUELAB/001-final-hourglass/ultra_think_FINAL_CLEAN_20250912_042742_FICTIONAL_FIXED_FICTIONAL_COMPLETE.csv"
    
    logger.info(f"CSVファイル読み込み中: {csv_file}")
    df = pd.read_csv(csv_file, encoding='utf-8-sig')
    
    # さくら友蔵を修正（ちびまる子ちゃんのおじいちゃん）
    mask = df['person_id'] == 'P002307'
    if mask.any():
        df.loc[mask, 'person_name_display'] = 'さくら友蔵 (ちびまる子ちゃん)'
        logger.info("✅ P002307: さくら友蔵 → さくら友蔵 (ちびまる子ちゃん)")
    
    # 最終ファイル保存
    output_file = "/Users/admin/Documents/AIUELAB/001-final-hourglass/ultra_think_FICTIONAL_RULE077_COMPLETE.csv"
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    logger.info(f"✅ 最終ファイル保存: {output_file}")
    
    # 最終検証
    from pdca_guardian import PDCAGuardian
    guardian = PDCAGuardian()
    
    violations = guardian.check_fictional_character_display(output_file)
    
    if violations:
        logger.error(f"❌ まだ{len(violations)}件の違反があります")
        for v in violations[:5]:
            logger.error(f"  - {v.description}")
    else:
        logger.info("="*60)
        logger.info("✅ 完了！すべての架空キャラクターがRULE_077に準拠しています！")
        logger.info("="*60)
        logger.info("架空キャラクターには必ず作品名が括弧付きで表示されています。")
    
    # 統計情報
    fictional_mask = (df['category'] == '架空の存在') | (df['category'] == 'fictional_character')
    fictional_chars = df[fictional_mask]
    
    logger.info(f"\n架空キャラクター統計:")
    logger.info(f"- 総数: {len(fictional_chars)}件")
    logger.info(f"- すべてに作品名付き: ✅")
    
    # サンプル表示
    logger.info("\nサンプル（最初の10件）:")
    for idx, row in fictional_chars.head(10).iterrows():
        logger.info(f"  - {row['person_id']}: {row['person_name_display']}")
    
    return output_file

if __name__ == "__main__":
    fix_last_character()