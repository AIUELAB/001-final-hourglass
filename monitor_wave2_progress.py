#!/usr/bin/env python3
"""
Wave2追加処理の進捗モニター
"""

import time
import subprocess
import os
from datetime import datetime

def check_process_status():
    """プロセス状態を確認"""
    result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
    return 'add_extended_persons_wave2.py' in result.stdout

def get_latest_stats():
    """最新の統計を取得"""
    if os.path.exists('wave2_addition.log'):
        with open('wave2_addition.log', 'r') as f:
            lines = f.readlines()
            
        # 最新の進捗を探す
        progress = None
        added = []
        
        for line in reversed(lines):
            if '進捗:' in line:
                progress = line.strip()
                break
            if '✅' in line or '⚠️' in line:
                added.append(line.strip())
                if len(added) >= 5:
                    break
        
        return progress, added[::-1]
    return None, []

def main():
    print("=" * 60)
    print("📊 Wave2追加処理モニター")
    print("=" * 60)
    
    start_time = datetime.now()
    last_progress = None
    
    while True:
        # プロセス確認
        if not check_process_status():
            print("\n✅ 処理完了！")
            break
        
        # 統計取得
        progress, recent_adds = get_latest_stats()
        
        # 進捗が更新されたら表示
        if progress and progress != last_progress:
            elapsed = datetime.now() - start_time
            print(f"\n[{elapsed}] {progress}")
            last_progress = progress
            
            # 最近の追加を表示
            if recent_adds:
                for add in recent_adds[-3:]:
                    print(f"  {add[:80]}...")
        
        time.sleep(5)
    
    # 最終統計
    print("\n" + "=" * 60)
    print("📊 最終統計")
    print("=" * 60)
    
    # ログファイルから統計を抽出
    if os.path.exists('wave2_addition.log'):
        with open('wave2_addition.log', 'r') as f:
            lines = f.readlines()
        
        for line in lines[-30:]:
            if any(keyword in line for keyword in ['追加成功', '累計', '達成率', 'API使用']):
                print(line.strip())

if __name__ == "__main__":
    main()