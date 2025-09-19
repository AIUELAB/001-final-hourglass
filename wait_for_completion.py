#!/usr/bin/env python3
"""
削除システム完了待機スクリプト
Wait for Deletion System Completion
"""

import json
import time
import sys
from datetime import datetime
from pathlib import Path

def check_completion():
    """処理完了をチェック"""
    
    # 最終結果ファイルのパターン
    results_dir = Path('deletion_results')
    
    # deletion_analysis_complete_*.jsonファイルを探す
    complete_files = list(results_dir.glob('deletion_analysis_complete_*.json'))
    
    if complete_files:
        latest = max(complete_files, key=lambda p: p.stat().st_mtime)
        with open(latest, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        if 'summary' in data and 'total_processed' in data['summary']:
            total = data['summary']['total_processed']
            if total >= 4701:
                return True, total
    
    # intermediate_resultsファイルをチェック
    intermediate_files = list(results_dir.glob('intermediate_results_*.json'))
    if intermediate_files:
        latest = max(intermediate_files, key=lambda p: p.stat().st_mtime)
        try:
            with open(latest, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if 'results' in data:
                count = len(data['results'])
                return count >= 4701, count
        except:
            pass
    
    return False, 0

def monitor_progress():
    """進捗を監視"""
    print("削除システムの完了を待機しています...")
    print(f"開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 60)
    
    last_count = 0
    check_interval = 30  # 30秒ごとにチェック
    
    while True:
        try:
            completed, count = check_completion()
            
            if count != last_count:
                now = datetime.now().strftime('%H:%M:%S')
                print(f"[{now}] 処理済み: {count}/4701 件 ({count/4701*100:.1f}%)")
                last_count = count
            
            if completed:
                print("-" * 60)
                print(f"✅ 処理完了! 総処理件数: {count}")
                print(f"完了時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                return True
                
            time.sleep(check_interval)
            
        except KeyboardInterrupt:
            print("\n監視を中断しました")
            return False
        except Exception as e:
            print(f"エラー: {e}")
            time.sleep(check_interval)

if __name__ == "__main__":
    success = monitor_progress()
    sys.exit(0 if success else 1)