#!/usr/bin/env python3
"""
最適化知名度評価システム - 本番実行スクリプト
98日→4日の短縮を実現
"""

import asyncio
import sys
import os
from datetime import datetime
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'optimized_recognition_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


async def main():
    """メイン実行関数"""

    print("\n" + "=" * 70)
    print("🚀 最適化知名度評価システム - 本番実行")
    print("=" * 70)

    # Check for input file
    csv_path = "ultra_think_EPISODE_FINAL_20250901_020106_fixed.csv"

    if not Path(csv_path).exists():
        logger.error(f"❌ 入力ファイルが見つかりません: {csv_path}")
        print("\n使用方法:")
        print("  python3 run_optimized_recognition.py")
        print("  または")
        print("  python3 run_optimized_recognition.py --test  # テストモード（20件）")
        sys.exit(1)

    # Check for test mode
    test_mode = "--test" in sys.argv or "-t" in sys.argv

    if test_mode:
        print("⚠️ テストモード: 最初の20件のみ処理")
    else:
        print("📂 フルデータベース処理モード")

    # Confirmation for full run
    if not test_mode:
        print("\n" + "=" * 70)
        print("⚠️ 確認")
        print("=" * 70)
        print(f"データベース: {csv_path}")
        print("推定処理時間: 約2.9日（69.9時間）")
        print("API呼び出し: 約8,400回")
        print("\n処理を開始しますか？")
        response = input("続行する場合は 'yes' を入力: ")

        if response.lower() != 'yes':
            print("❌ 処理をキャンセルしました")
            return

    # Import optimized system
    try:
        from optimized_recognition_system import OptimizedRecognitionSystem
    except ImportError as e:
        logger.error(f"❌ システムのインポートに失敗: {e}")
        print("\n必要なモジュールをインストールしてください:")
        print("  pip install scikit-learn joblib pandas numpy")
        sys.exit(1)

    # Initialize system
    logger.info("🔧 システム初期化中...")
    system = OptimizedRecognitionSystem(test_mode=test_mode)

    # Set output path
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = f"optimized_recognition_result_{timestamp}.csv"

    print("\n" + "=" * 70)
    print("📊 処理開始")
    print("=" * 70)
    print(f"入力: {csv_path}")
    print(f"出力: {output_path}")
    print(f"モード: {'テスト（20件）' if test_mode else 'フル処理'}")

    # Start processing
    try:
        result_df = await system.process_database(
            csv_path=csv_path,
            output_path=output_path
        )

        # Success
        print("\n" + "=" * 70)
        print("✅ 処理完了")
        print("=" * 70)

        if system.metrics:
            print(f"\n📊 最終統計:")
            print(f"  処理レコード: {system.metrics.total_records}件")
            print(f"  実行時間: {system.metrics.actual_time_hours:.1f}時間")
            print(f"  API削減: {system.metrics.api_reduction_rate:.1f}%")
            print(f"  キャッシュヒット: {system.metrics.cache_hit_rate:.1f}%")
            print(f"  並列化効果: {system.metrics.parallel_speedup:.1f}x")

        print(f"\n📁 結果ファイル:")
        print(f"  CSV: {output_path}")
        print(f"  メトリクス: {output_path.replace('.csv', '_metrics.json')}")
        print(f"  ログ: optimized_recognition_{timestamp}.log")

        # Sample results
        if len(result_df) > 0:
            print("\n📋 結果サンプル（上位5件）:")
            top_5 = result_df.nlargest(5, 'final_score')[['person_name_ja', 'final_score', 'category']]
            for idx, row in top_5.iterrows():
                name = row.get('person_name_ja', 'N/A')
                score = row.get('final_score', 0)
                category = row.get('category', 'N/A')
                print(f"  {name}: {score:.1f} ({category})")

        return result_df

    except KeyboardInterrupt:
        logger.warning("⚠️ ユーザーによる中断")
        print("\n処理を中断しました")
        return None

    except Exception as e:
        logger.error(f"❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        return None


def run_quick_test():
    """クイックテスト実行"""
    print("\n🧪 クイックテスト実行")
    print("=" * 70)

    # Check dependencies
    try:
        import pandas as pd
        import numpy as np
        from sklearn.ensemble import RandomForestClassifier
        import joblib
        print("✅ 依存関係チェック: OK")
    except ImportError as e:
        print(f"❌ 依存関係エラー: {e}")
        print("\n以下を実行してください:")
        print("  pip install scikit-learn joblib pandas numpy")
        return False

    # Check input file
    csv_path = "ultra_think_EPISODE_FINAL_20250901_020106_fixed.csv"
    if Path(csv_path).exists():
        df = pd.read_csv(csv_path, encoding='utf-8-sig')
        print(f"✅ 入力ファイル: {len(df)}件")
    else:
        print(f"⚠️ 入力ファイルなし（テストデータ使用）")

    # Check components
    components = [
        "ml_pre_filter.py",
        "parallel_processor.py",
        "three_layer_cache.py",
        "tiered_evaluation.py",
        "optimized_recognition_system.py"
    ]

    for component in components:
        if Path(component).exists():
            print(f"✅ {component}: 存在")
        else:
            print(f"❌ {component}: 不足")

    print("\n準備完了！実行コマンド:")
    print("  python3 run_optimized_recognition.py --test  # テスト実行")
    print("  python3 run_optimized_recognition.py         # フル実行")

    return True


if __name__ == "__main__":
    if "--check" in sys.argv:
        # Dependency check
        run_quick_test()
    else:
        # Main execution
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            print("\n\n処理を中断しました")
        except Exception as e:
            print(f"\n❌ 予期しないエラー: {e}")
            import traceback
            traceback.print_exc()
