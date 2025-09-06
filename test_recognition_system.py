#!/usr/bin/env python3
"""
知名度評価システムのテスト実行
最初の10件のみ処理して動作確認
"""

import asyncio
import pandas as pd
from pathlib import Path
import logging
from multi_api_recognition_system import MultiAPIRecognitionEvaluator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_recognition_system():
    """テスト実行"""
    csv_path = "ultra_think_EPISODE_FINAL_20250901_020106.csv"
    
    if not Path(csv_path).exists():
        logger.error(f"CSVファイルが見つかりません: {csv_path}")
        return
    
    # データ読み込み（最初の10件のみ）
    logger.info("📂 テストデータ読み込み中...")
    df = pd.read_csv(csv_path, encoding='utf-8-sig', nrows=10)
    logger.info(f"✅ {len(df)}件のテストレコードを読み込みました")
    
    # 評価システム初期化
    evaluator = MultiAPIRecognitionEvaluator(csv_path)
    
    # 各レコードを評価
    logger.info("🔄 知名度評価開始...")
    
    for idx, row in df.iterrows():
        logger.info(f"\n--- レコード {idx+1}/{len(df)} ---")
        logger.info(f"名前: {row.get('person_name', '')} / {row.get('person_name_ja', '')}")
        
        # 評価実行
        score = await evaluator.evaluate_person(row)
        
        # 結果表示
        logger.info(f"📊 評価結果:")
        logger.info(f"  最終スコア: {score.final_score:.2f}/10.0")
        logger.info(f"  Google結果: {score.google_results:,}")
        logger.info(f"  YouTube視聴: {score.youtube_views:,}")
        logger.info(f"  Twitter言及: {score.twitter_mentions:,}")
        logger.info(f"  ニュース記事: {score.news_articles:,}")
        logger.info(f"  保護対象: {'✅' if score.is_protected else '❌'}")
        if score.is_protected:
            logger.info(f"  保護理由: {score.protection_reason}")
        logger.info(f"  API成功率: {score.api_success_rate:.1%}")
        
        # 判定
        if score.final_score >= 7.0:
            decision = "🟢 保持（高知名度）"
        elif score.final_score >= 5.0:
            decision = "🟡 保持（中知名度）"
        elif score.final_score >= 3.0:
            decision = "🟠 要検討"
        else:
            decision = "🔴 削除候補"
        
        logger.info(f"  判定: {decision}")
        
        # レート制限対策
        await asyncio.sleep(0.5)
    
    logger.info("\n✨ テスト完了！")


if __name__ == "__main__":
    asyncio.run(test_recognition_system())