#!/usr/bin/env python3
"""
リアルタイム進捗監視サーバー
ログファイルを監視してダッシュボードにデータを提供
"""

import json
import time
import os
import re
from flask import Flask, jsonify, render_template_string
from flask_cors import CORS
from datetime import datetime
import pandas as pd
import threading
from pathlib import Path

app = Flask(__name__)
CORS(app)  # CORS有効化

# グローバル変数で進捗データを管理
progress_data = {
    'status': 'idle',  # idle, running, completed, error
    'start_time': None,
    'total_records': 0,
    'completed': 0,
    'processing': 0,
    'found': 0,
    'not_found': 0,
    'success_rate': 0.0,
    'speed': 0,
    'eta_minutes': 0,
    'recent_logs': [],
    'current_file': None,
    'error_message': None
}

# ログファイルパス
LOG_FILES = [
    'wikipedia_birth_collection.log',
    'firecrawl_birth_collection.log',
    'wikidata_birth_collection.log',
    'full_birth_collection_*.log'
]

def parse_log_line(line: str) -> dict:
    """ログ行をパースして情報を抽出"""
    data = {}

    # 時刻の抽出
    time_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
    if time_match:
        data['timestamp'] = time_match.group(1)

    # 成功/失敗の判定
    if '✅' in line or '取得成功' in line:
        data['status'] = 'success'
        # 人名と誕生年の抽出
        name_match = re.search(r'取得成功: ([^→]+) → (\d{4})', line)
        if name_match:
            data['person_name'] = name_match.group(1)
            data['birth_year'] = name_match.group(2)
    elif '❌' in line or '取得失敗' in line:
        data['status'] = 'failed'
        name_match = re.search(r'取得失敗: (.+)', line)
        if name_match:
            data['person_name'] = name_match.group(1)

    # 進捗情報の抽出
    progress_match = re.search(r'進捗: (\d+)/(\d+) \(([\d.]+)%\)', line)
    if progress_match:
        data['current'] = int(progress_match.group(1))
        data['total'] = int(progress_match.group(2))
        data['percentage'] = float(progress_match.group(3))

    # 統計情報の抽出
    if '取得成功:' in line and '件' in line:
        stats_match = re.search(r'取得成功: (\d+)件', line)
        if stats_match:
            data['found_count'] = int(stats_match.group(1))

    return data

def monitor_log_files():
    """ログファイルを監視して進捗データを更新"""
    global progress_data

    while True:
        try:
            # 最新のログファイルを探す
            latest_log = None
            latest_time = 0

            for pattern in LOG_FILES:
                if '*' in pattern:
                    # ワイルドカードパターンの処理
                    base_name = pattern.replace('*', '')
                    for file in Path('.').glob(pattern):
                        if file.exists():
                            mtime = file.stat().st_mtime
                            if mtime > latest_time:
                                latest_time = mtime
                                latest_log = str(file)
                else:
                    # 通常のファイル名
                    if Path(pattern).exists():
                        mtime = Path(pattern).stat().st_mtime
                        if mtime > latest_time:
                            latest_time = mtime
                            latest_log = pattern

            if latest_log:
                progress_data['current_file'] = latest_log

                # ログファイルを読み込み
                with open(latest_log, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                # 最新の行から情報を抽出
                recent_entries = []
                for line in reversed(lines[-100:]):  # 最新100行を処理
                    parsed = parse_log_line(line)
                    if parsed:
                        recent_entries.append(parsed)

                        # 統計情報の更新
                        if 'current' in parsed:
                            progress_data['completed'] = parsed['current']
                        if 'total' in parsed:
                            progress_data['total_records'] = parsed['total']
                        if 'found_count' in parsed:
                            progress_data['found'] = parsed['found_count']

                # 最新ログエントリの保存（最大20件）
                progress_data['recent_logs'] = recent_entries[:20]

                # 成功率の計算
                if progress_data['completed'] > 0:
                    progress_data['success_rate'] = (
                        progress_data['found'] / progress_data['completed'] * 100
                    )

                # 処理速度とETAの計算
                if progress_data['start_time']:
                    elapsed = time.time() - progress_data['start_time']
                    if elapsed > 0 and progress_data['completed'] > 0:
                        progress_data['speed'] = progress_data['completed'] / (elapsed / 60)  # 件/分
                        remaining = progress_data['total_records'] - progress_data['completed']
                        if progress_data['speed'] > 0:
                            progress_data['eta_minutes'] = remaining / progress_data['speed']

                # ステータスの更新
                if progress_data['completed'] >= progress_data['total_records']:
                    progress_data['status'] = 'completed'
                elif progress_data['completed'] > 0:
                    progress_data['status'] = 'running'

        except Exception as e:
            progress_data['error_message'] = str(e)

        time.sleep(1)  # 1秒ごとに更新

@app.route('/api/progress')
def get_progress():
    """進捗データをJSON形式で返す"""
    return jsonify(progress_data)

@app.route('/api/start/<process_type>')
def start_process(process_type):
    """処理を開始（シミュレーション用）"""
    global progress_data

    # CSVファイルから総レコード数を取得
    csv_files = list(Path('.').glob('ultra_think_*.csv'))
    if csv_files:
        latest_csv = max(csv_files, key=lambda x: x.stat().st_mtime)
        df = pd.read_csv(latest_csv, encoding='utf-8-sig')
        total = len(df)
        missing = df['birth_year_int'].isna().sum()
    else:
        total = 3111
        missing = 2069

    progress_data.update({
        'status': 'running',
        'start_time': time.time(),
        'total_records': missing,
        'completed': 0,
        'processing': 0,
        'found': 0,
        'not_found': 0,
        'success_rate': 0.0,
        'speed': 0,
        'eta_minutes': 0,
        'recent_logs': [],
        'error_message': None
    })

    return jsonify({'status': 'started', 'type': process_type})

@app.route('/api/stop')
def stop_process():
    """処理を停止"""
    global progress_data
    progress_data['status'] = 'idle'
    return jsonify({'status': 'stopped'})

@app.route('/')
def dashboard():
    """ダッシュボードHTMLを返す"""
    # birth_collection_dashboard.htmlを読み込んで返す
    dashboard_path = Path('birth_collection_dashboard.html')
    if dashboard_path.exists():
        with open(dashboard_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # APIエンドポイントをローカルサーバーに変更
            content = content.replace(
                'http://localhost:5000/api/progress',
                '/api/progress'
            )
            return content
    else:
        return "Dashboard file not found", 404

def main():
    """メイン処理"""
    # ログ監視スレッドを開始
    monitor_thread = threading.Thread(target=monitor_log_files, daemon=True)
    monitor_thread.start()

    # Flaskサーバーを起動
    print("🚀 Birth Collection Monitor Server")
    print("📊 Dashboard: http://localhost:5001")
    print("📡 API: http://localhost:5001/api/progress")
    print("-" * 50)

    app.run(host='0.0.0.0', port=5001, debug=False)

if __name__ == '__main__':
    main()
