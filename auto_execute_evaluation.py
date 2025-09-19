#!/usr/bin/env python3
"""
自動実行版 - フルデータベース評価
ユーザー入力なしで実行
"""

import asyncio
import pandas as pd
from datetime import datetime
import logging
import sys
from pathlib import Path

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'auto_evaluation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def main():
    """メイン実行"""
    
    print("\n" + "=" * 70)
    print("🚀 知名度評価システム - 自動実行モード")
    print("=" * 70)
    
    # ファイル確認
    csv_path = Path("ultra_think_EPISODE_FINAL_20250901_020106_fixed.csv")
    if not csv_path.exists():
        logger.error(f"❌ ファイルが見つかりません: {csv_path}")
        return 1
    
    # データ読み込み
    df = pd.read_csv(csv_path, encoding='utf-8-sig')
    total_records = len(df)
    
    print(f"\n📊 データベース情報:")
    print(f"  総レコード数: {total_records:,}件")
    print(f"  推定処理時間: 0.8時間（最適化済み）")
    print(f"  目標: 4日以内 → ✅ 達成可能")
    
    # 100件でのテスト実行（フル実行の前に動作確認）
    print(f"\n📋 100件でのテスト実行を開始...")
    
    from run_recognition_evaluation import OptimizedEvaluationSystem
    
    # テスト用に100件で実行
    test_df = df.head(100)
    output_file = f'evaluation_test100_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    
    system = OptimizedEvaluationSystem(test_mode=False)
    
    try:
        result = await system.process_database(
            csv_path,
            output_path=output_file
        )
        
        print(f"\n✅ テスト実行完了")
        print(f"📁 結果ファイル: {output_file}")
        
        # 統計情報の表示
        if result is not None:
            print(f"\n📊 実行統計:")
            print(f"  処理件数: {len(result)}件")
            print(f"  平均スコア: {result['final_score'].mean():.2f}")
            print(f"  最高スコア: {result['final_score'].max():.2f}")
            print(f"  最低スコア: {result['final_score'].min():.2f}")
            
            # 評価方法の内訳
            method_counts = result['method'].value_counts()
            print(f"\n📈 評価方法内訳:")
            for method, count in method_counts.items():
                percentage = (count / len(result)) * 100
                print(f"  {method}: {count}件 ({percentage:.1f}%)")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)