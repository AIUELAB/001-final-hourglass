#!/usr/bin/env python3
"""
フルデータベース評価実行スクリプト
4日以内の処理完了を目指す最適化版
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
import logging

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'full_evaluation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def estimate_processing_time(total_records: int) -> dict:
    """処理時間を推定"""

    # 最適化要素
    ml_skip_rate = 0.35  # ML判定による35%スキップ
    cache_hit_rate = 0.15  # キャッシュヒット15%

    # API呼び出し数の推定
    api_calls_needed = total_records * (1 - ml_skip_rate) * (1 - cache_hit_rate)

    # 階層別処理時間（秒）
    tier1_ratio = 0.4  # 40% - 簡易評価
    tier2_ratio = 0.4  # 40% - 標準評価
    tier3_ratio = 0.2  # 20% - 詳細評価

    tier1_time = 2  # 2秒/件
    tier2_time = 5  # 5秒/件
    tier3_time = 10  # 10秒/件

    # 平均処理時間
    avg_time_per_api = (
        tier1_time * tier1_ratio +
        tier2_time * tier2_ratio +
        tier3_time * tier3_ratio
    )

    # 並列処理による高速化（5ワーカー）
    parallel_factor = 5

    # 総処理時間（秒）
    total_seconds = (api_calls_needed * avg_time_per_api) / parallel_factor

    # レート制限による追加待機時間（20%バッファ）
    rate_limit_buffer = 1.2
    total_seconds_with_buffer = total_seconds * rate_limit_buffer

    return {
        'total_records': total_records,
        'api_calls': int(api_calls_needed),
        'ml_skipped': int(total_records * ml_skip_rate),
        'cache_hits': int(total_records * cache_hit_rate),
        'total_seconds': total_seconds_with_buffer,
        'total_hours': total_seconds_with_buffer / 3600,
        'total_days': total_seconds_with_buffer / 86400,
        'completion_time': datetime.now() + timedelta(seconds=total_seconds_with_buffer)
    }

def display_execution_plan(estimates: dict):
    """実行計画を表示"""

    print("\n" + "=" * 70)
    print("📊 フルデータベース評価 - 実行計画")
    print("=" * 70)

    print(f"\n📈 データベース統計:")
    print(f"  総レコード数: {estimates['total_records']:,}件")
    print(f"  ML事前判定でスキップ: {estimates['ml_skipped']:,}件")
    print(f"  キャッシュヒット予想: {estimates['cache_hits']:,}件")
    print(f"  API呼び出し必要数: {estimates['api_calls']:,}件")

    print(f"\n⏱️ 推定処理時間:")
    print(f"  総処理時間: {estimates['total_hours']:.1f}時間")
    print(f"  日数換算: {estimates['total_days']:.1f}日")
    print(f"  完了予定: {estimates['completion_time'].strftime('%Y年%m月%d日 %H:%M')}")

    if estimates['total_days'] <= 4:
        print(f"\n✅ 目標達成: 4日以内に処理完了可能！")
    else:
        print(f"\n⚠️ 追加最適化が必要: 目標4日に対して{estimates['total_days']:.1f}日")

    print("\n" + "=" * 70)

async def execute_full_evaluation():
    """フルデータベース評価を実行"""

    # データベースファイルの確認
    csv_path = Path("ultra_think_EPISODE_FINAL_20250901_020106_fixed.csv")

    if not csv_path.exists():
        logger.error(f"❌ データベースファイルが見つかりません: {csv_path}")
        return False

    # CSVファイルから総レコード数を取得
    import pandas as pd
    df = pd.read_csv(csv_path, encoding='utf-8-sig')
    total_records = len(df)

    logger.info(f"📂 データベース読み込み完了: {total_records:,}件")

    # 処理時間推定
    estimates = estimate_processing_time(total_records)
    display_execution_plan(estimates)

    # ユーザー確認
    print("\n実行を開始しますか？ (y/n): ", end='')
    user_input = input().strip().lower()

    if user_input != 'y':
        print("❌ 実行をキャンセルしました")
        return False

    print("\n🚀 評価処理を開始します...")

    # 実際の評価実行
    from run_recognition_evaluation import OptimizedEvaluationSystem

    system = OptimizedEvaluationSystem(test_mode=False)

    try:
        # プログレスバー表示用
        import time
        start_time = time.time()

        # バッチ処理で実行
        batch_size = 100
        processed = 0

        for i in range(0, total_records, batch_size):
            batch = df.iloc[i:i+batch_size]

            # バッチ処理（実際にはrun_recognition_evaluation.pyのprocess_databaseを呼ぶ）
            await system.process_batch(batch)

            processed += len(batch)
            elapsed = time.time() - start_time
            progress = (processed / total_records) * 100

            # 残り時間推定
            if processed > 0:
                total_estimated = (elapsed / processed) * total_records
                remaining = total_estimated - elapsed
                eta = datetime.now() + timedelta(seconds=remaining)

                print(f"\r進捗: {progress:.1f}% ({processed:,}/{total_records:,}) | "
                      f"残り時間: {remaining/3600:.1f}時間 | "
                      f"完了予定: {eta.strftime('%H:%M')}", end='')

        print()  # 改行

        # 最終統計
        total_time = time.time() - start_time
        print(f"\n✅ 処理完了！")
        print(f"  総処理時間: {total_time/3600:.1f}時間")
        print(f"  平均処理速度: {total_records/total_time:.1f}件/秒")

        # キャッシュ保存
        system.save_cache()

        return True

    except KeyboardInterrupt:
        print("\n\n⚠️ ユーザーによる中断")
        system.save_cache()
        return False

    except Exception as e:
        logger.error(f"❌ エラー発生: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """メインエントリポイント"""

    print("\n" + "=" * 70)
    print("🎯 知名度評価システム - フルデータベース実行")
    print("最適化版 - 4日以内の処理完了目標")
    print("=" * 70)

    # 最適化状況の確認
    print("\n📊 最適化機能:")
    print("  ✅ ML事前フィルタリング（35%削減）")
    print("  ✅ 3層キャッシュシステム")
    print("  ✅ 5ワーカー並列処理")
    print("  ✅ 階層別評価（Tier1/2/3）")
    print("  ✅ スマートレート制限管理")

    # 非同期実行
    success = asyncio.run(execute_full_evaluation())

    if success:
        print("\n🎉 すべての処理が正常に完了しました！")
    else:
        print("\n⚠️ 処理が中断されました")

    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
