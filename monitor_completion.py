#!/usr/bin/env python3
"""
処理完了監視スクリプト
バックグラウンド処理の完了を検知して通知
"""

import time
import os
import subprocess
from pathlib import Path
from datetime import datetime
import json

def check_process_running(pid=71408):
    """プロセスが実行中か確認"""
    try:
        result = subprocess.run(
            ["ps", "-p", str(pid)],
            capture_output=True,
            text=True
        )
        return pid in result.stdout
    except:
        return False

def get_latest_progress():
    """最新の進捗を取得"""
    log_files = list(Path('.').glob('recognition_full_*.log'))
    if not log_files:
        return None, None
    
    latest_log = max(log_files, key=lambda f: f.stat().st_mtime)
    
    # 最後の進捗行を探す
    progress = None
    completed = False
    
    try:
        with open(latest_log, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in reversed(lines[-100:]):
                if '進捗:' in line:
                    parts = line.split('進捗:')[1].strip()
                    progress = parts
                    # 4701/4701 をチェック
                    if '4701/4701' in parts:
                        completed = True
                    break
                elif '処理完了' in line or '全件処理完了' in line:
                    completed = True
    except:
        pass
    
    return progress, completed

def notify_completion():
    """完了通知を送信"""
    try:
        # macOS通知
        subprocess.run([
            "osascript", "-e",
            'display notification "Wikipedia知名度評価システムの処理が完了しました！" with title "処理完了" sound name "Glass"'
        ])
    except:
        pass
    
    # コンソール通知
    print("\n" + "="*60)
    print("✅ 処理完了！")
    print("="*60)
    print(f"完了時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def get_result_files():
    """結果ファイルを取得"""
    result_files = {
        'csv': list(Path('.').glob('recognition_results_ALL_*.csv')),
        'stats': list(Path('.').glob('recognition_results_ALL_*_stats.json')),
        'report': list(Path('.').glob('FINAL_REPORT_*.md'))
    }
    
    latest_files = {}
    for key, files in result_files.items():
        if files:
            latest_files[key] = max(files, key=lambda f: f.stat().st_mtime)
    
    return latest_files

def main():
    """メイン監視ループ"""
    print("🔍 処理完了を監視中...")
    print(f"開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 60)
    
    check_count = 0
    last_progress = None
    
    while True:
        check_count += 1
        
        # プロセス確認
        is_running = check_process_running(71408)
        
        # 進捗確認
        progress, completed = get_latest_progress()
        
        # 進捗が更新された場合のみ表示
        if progress and progress != last_progress:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 進捗: {progress}")
            last_progress = progress
        
        # 完了判定
        if completed or not is_running:
            print("\n" + "="*60)
            
            if completed:
                print("✅ 処理が正常に完了しました！")
            else:
                print("⚠️ プロセスが終了しました")
            
            # 結果ファイル確認
            result_files = get_result_files()
            
            if result_files:
                print("\n📁 生成されたファイル:")
                if 'csv' in result_files:
                    print(f"  結果CSV: {result_files['csv']}")
                if 'stats' in result_files:
                    print(f"  統計JSON: {result_files['stats']}")
                if 'report' in result_files:
                    print(f"  最終レポート: {result_files['report']}")
            
            # 完了通知
            notify_completion()
            
            # 統計情報を読み込んで表示
            if 'stats' in result_files:
                try:
                    with open(result_files['stats'], 'r', encoding='utf-8') as f:
                        stats = json.load(f)
                        if 'stats' in stats:
                            print("\n📊 処理統計:")
                            s = stats['stats']
                            print(f"  処理件数: {s.get('total_processed', 0):,}")
                            print(f"  削除候補: {s.get('deletion_candidates', 0):,}")
                            print(f"  Wikipedia発見: {s.get('wikipedia_found', 0):,}")
                except:
                    pass
            
            print("="*60)
            break
        
        # 10秒待機
        time.sleep(10)
        
        # 5分ごとに状態表示
        if check_count % 30 == 0:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 監視継続中... (PID: 71408 {'実行中' if is_running else '停止'})")

if __name__ == "__main__":
    main()