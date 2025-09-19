#!/usr/bin/env python3
"""
検索処理の進捗をモニタリング
"""

import pandas as pd
import time
import os
from datetime import datetime

def monitor_progress():
    """進捗状況をモニタリング"""
    csv_file = "ultra_think_with_search_counts_20250915_140948.csv"

    print("=" * 60)
    print("🔍 Google検索結果数取得 - 進捗モニター")
    print("=" * 60)

    start_time = datetime.now()

    while True:
        try:
            # CSVファイルを読み込み
            df = pd.read_csv(csv_file)

            # 検索済みレコード数を確認
            searched = df[df['search_result_count'] > 0]
            total_searched = len(searched)

            # 統計情報
            if total_searched > 0:
                avg_results = searched['search_result_count'].mean()
                max_results = searched['search_result_count'].max()
                min_results = searched['search_result_count'].min()

                # 進捗状況
                progress = (total_searched / 1000) * 100
                elapsed = (datetime.now() - start_time).total_seconds()
                rate = total_searched / (elapsed / 60) if elapsed > 0 else 0
                eta = (1000 - total_searched) / rate if rate > 0 else 0

                # 表示
                os.system('clear')
                print("=" * 60)
                print("🔍 Google検索結果数取得 - 進捗モニター")
                print("=" * 60)
                print(f"\n📊 進捗状況:")
                print(f"  完了: {total_searched}/1000 ({progress:.1f}%)")
                print(f"  処理速度: {rate:.1f} 件/分")
                print(f"  推定残り時間: {eta:.1f} 分")

                print(f"\n📈 統計:")
                print(f"  平均検索結果数: {avg_results:,.0f}")
                print(f"  最大: {max_results:,.0f}")
                print(f"  最小: {min_results:,.0f}")

                # 最新の5件を表示
                print(f"\n🆕 最新の検索結果:")
                latest = searched.nlargest(5, 'search_timestamp' if 'search_timestamp' in df.columns else searched.index)
                for _, row in latest.iterrows():
                    name = row['person_name_display']
                    count = row['search_result_count']
                    print(f"  {name}: {count:,} 件")

                if total_searched >= 1000:
                    print(f"\n✅ 処理完了！")
                    break
            else:
                print("⏳ 検索開始待機中...")

            # 10秒待機
            time.sleep(10)

        except Exception as e:
            print(f"エラー: {e}")
            time.sleep(10)

if __name__ == "__main__":
    monitor_progress()