#!/usr/bin/env python3
"""
Recognition Processing Monitor
処理進捗のリアルタイムモニタリング
"""

import json
import time
import os
from datetime import datetime
from pathlib import Path
import subprocess


def get_process_info():
    """プロセス情報を取得"""
    try:
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True
        )
        for line in result.stdout.split('\n'):
            if 'run_full_recognition_all' in line and 'grep' not in line:
                parts = line.split()
                return {
                    'pid': parts[1],
                    'cpu': parts[2],
                    'mem': parts[3],
                    'start_time': parts[8],
                    'running': True
                }
    except:
        pass
    return {'running': False}


def get_latest_progress():
    """最新の進捗を取得"""
    log_files = list(Path('.').glob('recognition_full_*.log'))
    if not log_files:
        return None
    
    latest_log = max(log_files, key=lambda f: f.stat().st_mtime)
    
    # 最後の進捗行を探す
    progress = None
    errors = 0
    checkpoints = 0
    
    try:
        with open(latest_log, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in reversed(lines[-1000:]):  # 最後の1000行から検索
                if '進捗:' in line:
                    # 例: "2025-09-08 20:47:05,388 - INFO - 進捗: 740/4701 (15.7%)"
                    parts = line.split('進捗:')[1].strip()
                    progress = parts
                    break
                elif 'ERROR' in line:
                    errors += 1
                elif 'チェックポイント' in line:
                    checkpoints += 1
    except:
        pass
    
    return {
        'progress': progress,
        'errors': errors,
        'checkpoints': checkpoints,
        'log_file': str(latest_log)
    }


def get_cache_stats():
    """キャッシュ統計を取得"""
    cache_dir = Path('cache/wikipedia')
    if cache_dir.exists():
        cache_files = list(cache_dir.glob('*.json'))
        total_size = sum(f.stat().st_size for f in cache_files) / 1024 / 1024  # MB
        return {
            'files': len(cache_files),
            'size_mb': round(total_size, 2)
        }
    return {'files': 0, 'size_mb': 0}


def display_dashboard():
    """ダッシュボード表示"""
    os.system('clear')
    
    print("=" * 60)
    print("📊 Wikipedia知名度評価システム - 進捗モニター")
    print("=" * 60)
    print()
    
    # プロセス情報
    process = get_process_info()
    if process['running']:
        print(f"✅ プロセス実行中")
        print(f"   PID: {process['pid']}")
        print(f"   CPU: {process['cpu']}%")
        print(f"   メモリ: {process['mem']}%")
        print(f"   開始時刻: {process['start_time']}")
    else:
        print("❌ プロセスが実行されていません")
    
    print()
    
    # 進捗情報
    progress_info = get_latest_progress()
    if progress_info and progress_info['progress']:
        print(f"📈 処理進捗: {progress_info['progress']}")
        
        # 進捗バーを表示
        if '/' in progress_info['progress']:
            parts = progress_info['progress'].split('/')
            current = int(parts[0])
            total = int(parts[1].split()[0])
            percentage = current / total * 100
            
            bar_length = 40
            filled = int(bar_length * percentage / 100)
            bar = '█' * filled + '░' * (bar_length - filled)
            print(f"   [{bar}] {percentage:.1f}%")
            
            # 推定完了時刻
            if current > 0:
                # 簡易計算
                print(f"   推定残り時間: 計算中...")
    
    print()
    
    # キャッシュ統計
    cache = get_cache_stats()
    print(f"💾 キャッシュ統計:")
    print(f"   ファイル数: {cache['files']:,}")
    print(f"   サイズ: {cache['size_mb']:.2f} MB")
    
    print()
    
    # 更新時刻
    print(f"🕐 更新時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("Ctrl+C で終了")
    print("=" * 60)


def main():
    """メイン処理"""
    try:
        while True:
            display_dashboard()
            time.sleep(10)  # 10秒ごとに更新
    except KeyboardInterrupt:
        print("\n\nモニタリングを終了しました")


if __name__ == "__main__":
    main()
