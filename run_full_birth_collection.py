#!/usr/bin/env python3
"""
全データに対する誕生年取得実行スクリプト
Wikipedia APIを使用した確定情報取得
"""

import pandas as pd
import logging
from datetime import datetime
from wikipedia_birth_collector_enhanced import WikipediaBirthCollector

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'full_birth_collection_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def main():
    """メイン処理"""
    # 入力ファイル
    input_file = "ultra_think_WITH_BIRTH_YEARS_20250917_135652.csv"
    logger.info("=" * 70)
    logger.info("🚀 誕生年確定取得システム - フル実行")
    logger.info("=" * 70)
    logger.info(f"📂 入力ファイル: {input_file}")

    # データ読み込み
    df = pd.read_csv(input_file, encoding='utf-8-sig')
    logger.info(f"✅ {len(df)}件のレコード読み込み完了")

    # 現在の取得状況
    has_birth_year = df['birth_year_int'].notna().sum()
    total = len(df)
    current_rate = (has_birth_year / total * 100) if total > 0 else 0

    logger.info(f"\n📊 現在の取得状況:")
    logger.info(f"  取得済み: {has_birth_year:,}件")
    logger.info(f"  未取得: {total - has_birth_year:,}件")
    logger.info(f"  取得率: {current_rate:.1f}%")

    # カテゴリ別状況
    logger.info(f"\n📋 カテゴリ別未取得状況:")
    missing_by_category = df[df['birth_year_int'].isna()].groupby('category').size().sort_values(ascending=False)
    for category, count in missing_by_category.head(10).items():
        logger.info(f"  {category}: {count}件")

    # Wikipedia コレクター初期化
    logger.info(f"\n🔍 Wikipedia API収集開始")
    logger.info("=" * 70)
    collector = WikipediaBirthCollector()

    # 優先順位をつけて処理
    # 1. 高認知度の人物から処理
    df_sorted = df.sort_values('recognition_score', ascending=False, na_position='last')

    # バッチサイズを調整（APIレート制限を考慮）
    batch_size = 100

    # 処理実行
    logger.info(f"⚙️ バッチサイズ: {batch_size}件")
    logger.info(f"⏱️ 推定処理時間: 約{(total - has_birth_year) * 0.5 / 60:.0f}分")
    logger.info("=" * 70)

    df_result = collector.process_dataframe(df_sorted, batch_size=batch_size)

    # 結果を元の順序に戻す
    df_result = df_result.sort_values('person_id')

    # 結果を保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"ultra_think_WITH_WIKIPEDIA_BIRTHS_{timestamp}.csv"
    df_result.to_csv(output_file, index=False, encoding='utf-8-sig')
    logger.info(f"\n💾 結果保存: {output_file}")

    # 最終統計
    new_has_birth_year = df_result['birth_year_int'].notna().sum()
    new_rate = (new_has_birth_year / total * 100) if total > 0 else 0
    added = new_has_birth_year - has_birth_year

    logger.info("=" * 70)
    logger.info("🎯 最終結果")
    logger.info("=" * 70)
    logger.info(f"  取得前: {has_birth_year:,}件 ({current_rate:.1f}%)")
    logger.info(f"  取得後: {new_has_birth_year:,}件 ({new_rate:.1f}%)")
    logger.info(f"  新規取得: {added:,}件 (+{new_rate - current_rate:.1f}%)")
    logger.info("=" * 70)

    # カテゴリ別成功率
    logger.info("\n📊 カテゴリ別取得率:")
    for category in df_result['category'].unique():
        if pd.notna(category):
            cat_df = df_result[df_result['category'] == category]
            cat_total = len(cat_df)
            cat_has = cat_df['birth_year_int'].notna().sum()
            cat_rate = (cat_has / cat_total * 100) if cat_total > 0 else 0
            logger.info(f"  {category}: {cat_has}/{cat_total} ({cat_rate:.1f}%)")

    logger.info("\n✅ 処理完了")


if __name__ == "__main__":
    main()