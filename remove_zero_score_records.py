#!/usr/bin/env python3
"""
recognition_score=0のレコードをデータベースから削除
"""

import pandas as pd
from datetime import datetime
import logging

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)
logger = logging.getLogger(__name__)

def remove_zero_score_records(input_file: str):
    """recognition_score=0のレコードを削除"""
    
    logger.info("="*60)
    logger.info("🗑️ recognition_score=0のレコード削除処理開始")
    logger.info("="*60)
    
    try:
        # データ読み込み
        logger.info(f"データ読み込み: {input_file}")
        df = pd.read_csv(input_file, encoding='utf-8-sig')
        total_records = len(df)
        logger.info(f"総レコード数: {total_records}")
        
        # recognition_score=0のレコードを特定
        zero_score_mask = df['recognition_score'] == 0.0
        zero_score_count = zero_score_mask.sum()
        
        logger.info(f"recognition_score=0のレコード数: {zero_score_count}")
        logger.info(f"削除率: {zero_score_count/total_records*100:.1f}%")
        
        # 削除対象のサンプル表示
        if zero_score_count > 0:
            logger.info("\n削除対象サンプル（最初の10件）:")
            sample_df = df[zero_score_mask].head(10)[['person_id', 'name', 'recognition_score', 'reason']]
            for idx, row in sample_df.iterrows():
                logger.info(f"  - {row['person_id']}: {row['name']} (理由: {row['reason']})")
        
        # 削除実行
        logger.info("\n削除実行中...")
        df_filtered = df[~zero_score_mask].copy()
        remaining_records = len(df_filtered)
        
        # 結果ファイル保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"database_cleaned_{timestamp}.csv"
        df_filtered.to_csv(output_file, index=False, encoding='utf-8-sig')
        
        # 削除リスト保存
        deleted_list_file = f"deleted_records_{timestamp}.csv"
        df[zero_score_mask].to_csv(deleted_list_file, index=False, encoding='utf-8-sig')
        
        # 統計レポート
        logger.info("\n" + "="*60)
        logger.info("📊 削除処理完了")
        logger.info("="*60)
        logger.info(f"削除前: {total_records}件")
        logger.info(f"削除数: {zero_score_count}件")
        logger.info(f"削除後: {remaining_records}件")
        logger.info(f"削除率: {zero_score_count/total_records*100:.1f}%")
        
        # ファイル情報
        logger.info(f"\n✅ クリーンデータベース: {output_file}")
        logger.info(f"📋 削除リスト: {deleted_list_file}")
        
        # 品質チェック
        logger.info("\n🔍 品質チェック:")
        
        # 有名人が残っているか確認
        famous_people = ['吉田美和', '中村正人', 'PSY', 'BTS', 'フィッシャーズ', '東海オンエア']
        for person in famous_people:
            if any(person in str(name) for name in df_filtered['name'].values):
                logger.info(f"  ✅ {person}: 保持")
            else:
                remaining_in_original = any(person in str(name) for name in df['name'].values)
                if remaining_in_original:
                    logger.warning(f"  ❌ {person}: 削除された（要確認）")
        
        # スコア分布
        logger.info("\n📈 残存データのスコア分布:")
        score_ranges = [
            (9.0, 10.0, "超有名人"),
            (7.0, 9.0, "有名人"),
            (5.0, 7.0, "中程度"),
            (3.0, 5.0, "低認知度"),
            (0.1, 3.0, "極低認知度")
        ]
        
        for min_score, max_score, label in score_ranges:
            count = len(df_filtered[(df_filtered['recognition_score'] >= min_score) & 
                                   (df_filtered['recognition_score'] < max_score)])
            if count > 0:
                logger.info(f"  {label} ({min_score:.1f}-{max_score:.1f}): {count}件")
        
        return output_file, deleted_list_file
        
    except Exception as e:
        logger.error(f"エラー発生: {e}")
        raise

def main():
    """メイン処理"""
    import argparse
    
    parser = argparse.ArgumentParser(description='recognition_score=0のレコードを削除')
    parser.add_argument('--input', type=str,
                       default='reprocessed_ALL_20250910_025225.csv',
                       help='入力CSVファイル')
    
    args = parser.parse_args()
    
    # 削除処理実行
    output_file, deleted_list = remove_zero_score_records(args.input)
    
    logger.info("\n✅ 全処理完了")
    logger.info(f"クリーンデータベースが作成されました: {output_file}")

if __name__ == "__main__":
    main()