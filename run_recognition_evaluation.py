#!/usr/bin/env python3
"""
知名度評価本番実行スクリプト
データベース全体に知名度スコアを付与
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from datetime import datetime

# 環境変数読み込み
from dotenv import load_dotenv
load_dotenv()

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """メイン処理"""
    logger.info("=" * 60)
    logger.info("🚀 知名度評価システム起動")
    logger.info("=" * 60)
    
    # 品質ゲートチェック
    logger.info("🔍 品質ゲートチェック中...")
    from quality_gates import enforce_quality_gates
    
    if not enforce_quality_gates("multi_api_recognition_system.py"):
        logger.error("❌ 品質ゲート失敗")
        sys.exit(1)
    
    logger.info("✅ 品質ゲート通過")
    
    # CSVファイル確認
    csv_path = "ultra_think_EPISODE_FINAL_20250901_020106.csv"
    
    if not Path(csv_path).exists():
        # 代替ファイルを探す
        alt_files = list(Path(".").glob("ultra_think*EPISODE*.csv"))
        if alt_files:
            csv_path = str(alt_files[-1])
            logger.info(f"📁 代替ファイル使用: {csv_path}")
        else:
            logger.error("❌ CSVファイルが見つかりません")
            sys.exit(1)
    
    # PDCAサイクル開始
    logger.info("🔄 PDCAサイクル開始")
    from pdca_guardian import PDCAGuardian
    
    guardian = PDCAGuardian()
    plan = {
        "goal": "データベース全体への知名度スコア付与",
        "target": "全レコード",
        "method": "マルチAPI評価",
        "apis": ["SerpAPI", "Brave", "YouTube", "Twitter", "News"],
        "protection": "教科書人物・架空キャラクター保護"
    }
    cycle_id = guardian.start_pdca_cycle(plan)
    
    # 評価実行
    logger.info("🎯 知名度評価開始")
    from multi_api_recognition_system import MultiAPIRecognitionEvaluator
    
    try:
        evaluator = MultiAPIRecognitionEvaluator(csv_path)
        
        # 非同期処理実行
        start_time = datetime.now()
        asyncio.run(evaluator.process_database())
        end_time = datetime.now()
        
        # 処理時間
        duration = (end_time - start_time).total_seconds()
        logger.info(f"⏱️ 処理時間: {duration:.1f}秒")
        
        # PDCAサイクル完了
        guardian.complete_cycle(cycle_id, {
            "status": "成功",
            "duration": duration,
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info("✨ 知名度評価完了！")
        
        # ダッシュボード更新
        logger.info("📊 PDCAダッシュボード更新中...")
        from pdca_dashboard import PDCADashboard
        
        dashboard = PDCADashboard()
        dashboard.save_dashboard()
        logger.info("✅ ダッシュボード更新完了")
        
    except Exception as e:
        logger.error(f"❌ エラー発生: {e}")
        guardian.record_violation(
            "EXECUTION_ERROR",
            f"知名度評価中にエラー: {str(e)}"
        )
        sys.exit(1)
    
    logger.info("=" * 60)
    logger.info("🎉 すべての処理が正常に完了しました")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()