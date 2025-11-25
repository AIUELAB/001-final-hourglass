#!/usr/bin/env python3
"""
最終処理完了監視スクリプト
"""

import time
import os
import json
from pathlib import Path
from datetime import datetime

def monitor_completion():
    """処理完了を監視"""

    print("🔍 最終処理完了を監視中...")
    print("="*60)

    log_file = "reprocessing_log.txt"
    start_time = datetime.now()
    last_batch = 0

    while True:
        try:
            # ログファイルをチェック
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                # バッチ進捗を確認
                for line in reversed(lines):
                    if "バッチ処理:" in line:
                        import re
                        match = re.search(r'(\d+)-(\d+)/(\d+)', line)
                        if match:
                            current_end = int(match.group(2))
                            total = int(match.group(3))

                            if current_end > last_batch:
                                last_batch = current_end
                                progress = current_end / total * 100
                                print(f"\r📊 進捗: {current_end}/{total} ({progress:.1f}%)", end="", flush=True)

                    # 完了確認
                    if "最終レポート" in line or "結果ファイル:" in line:
                        print("\n" + "="*60)
                        print("✅ 処理完了を検出！")

                        # 結果ファイルを探す
                        result_files = list(Path('.').glob('reprocessed_ALL_*.csv'))
                        if result_files:
                            latest_file = max(result_files, key=os.path.getctime)
                            print(f"📁 結果ファイル: {latest_file}")

                            # 統計ファイルも確認
                            stats_file = str(latest_file).replace('.csv', '_stats.json')
                            if os.path.exists(stats_file):
                                with open(stats_file, 'r', encoding='utf-8') as f:
                                    stats = json.load(f)
                                print("\n📊 最終統計:")
                                print(f"  処理件数: {stats.get('total_processed', 0)}")
                                print(f"  削除候補: {stats.get('deleted_count', 0)}")
                                print(f"  削除率: {stats.get('deleted_count', 0) / stats.get('total_processed', 1) * 100:.1f}%")
                                print(f"  Wikipedia発見: {stats.get('wikipedia_found', 0)}")
                                print(f"  救済件数: {stats.get('saved_count', 0)}")

                        elapsed = datetime.now() - start_time
                        print(f"\n⏱️ 処理時間: {elapsed}")
                        print("="*60)
                        return True

            # 5秒待機
            time.sleep(5)

        except Exception as e:
            print(f"\nエラー: {e}")
            time.sleep(5)

if __name__ == "__main__":
    monitor_completion()
