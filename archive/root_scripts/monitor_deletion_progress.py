#!/usr/bin/env python3
"""
削除システム進捗モニター
Deletion System Progress Monitor
"""

import json
import time
from datetime import datetime
from pathlib import Path
import pandas as pd

def monitor_progress():
    """進捗をモニタリング"""

    results_dir = Path('deletion_results')

    # 最新のintermediate_resultsファイルを探す
    intermediate_files = list(results_dir.glob('intermediate_results_*.json'))

    if not intermediate_files:
        print("⏳ まだ結果ファイルがありません...")
        return None

    # 最新のファイルを取得
    latest_file = max(intermediate_files, key=lambda p: p.stat().st_mtime)

    with open(latest_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if 'results' not in data:
        return None

    results = data['results']
    total_processed = len(results)

    # 推奨分布を計算
    recommendations = {}
    for r in results:
        rec = r.get('recommendation', 'UNKNOWN')
        recommendations[rec] = recommendations.get(rec, 0) + 1

    print(f"\n{'='*60}")
    print(f"📊 削除システム進捗レポート")
    print(f"{'='*60}")
    print(f"⏰ 現在時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 ファイル: {latest_file.name}")
    print(f"✅ 処理済み: {total_processed} 件")
    print(f"")
    print(f"📈 削除推奨分布:")
    for rec, count in sorted(recommendations.items()):
        percentage = (count / total_processed * 100) if total_processed > 0 else 0
        print(f"  - {rec}: {count} 件 ({percentage:.1f}%)")

    # 削除推奨率を計算
    delete_count = (
        recommendations.get('DELETE_HIGH_CONFIDENCE', 0) +
        recommendations.get('DELETE_MEDIUM_CONFIDENCE', 0)
    )
    delete_rate = (delete_count / total_processed * 100) if total_processed > 0 else 0

    print(f"\n🗑️ 総削除推奨率: {delete_rate:.1f}% ({delete_count}/{total_processed} 件)")

    # 推定残り時間（1件4秒として計算）
    remaining = 4701 - total_processed
    estimated_seconds = remaining * 4
    hours = estimated_seconds // 3600
    minutes = (estimated_seconds % 3600) // 60

    if remaining > 0:
        print(f"⏱️ 推定残り時間: 約{hours}時間{minutes}分 (残り{remaining}件)")
    else:
        print(f"✨ 処理完了!")

    print(f"{'='*60}\n")

    return total_processed

if __name__ == "__main__":
    print("削除システム進捗モニターを開始します...")
    print("Ctrl+Cで終了")

    while True:
        try:
            processed = monitor_progress()

            # 処理完了したら終了
            if processed and processed >= 4701:
                print("🎉 全データの処理が完了しました!")
                break

            # 30秒待機
            time.sleep(30)

        except KeyboardInterrupt:
            print("\nモニターを終了します")
            break
        except Exception as e:
            print(f"エラー: {e}")
            time.sleep(30)
