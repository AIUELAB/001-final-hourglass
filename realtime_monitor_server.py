#!/usr/bin/env python3
"""
リアルタイム進捗監視サーバー（改善版）
ファイル変更を確実に検知し、WebSocketでリアルタイム配信
"""

import json
import time
import os
import re
import asyncio
import threading
from flask import Flask, jsonify, render_template_string, send_from_directory
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from datetime import datetime
import pandas as pd
from pathlib import Path
from collections import deque

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

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
    'recent_logs': deque(maxlen=50),  # 最新50件を保持
    'current_file': None,
    'error_message': None,
    'last_update': None,
    'file_position': {}  # ファイルごとの読み取り位置を記録
}

# ログファイルパス
LOG_FILES = [
    'wikipedia_birth_collection.log',
    'firecrawl_birth_collection.log',
    'wikidata_birth_collection.log',
    'full_birth_collection_*.log'
]

def parse_log_line(line: str) -> dict:
    """ログ行をパースして情報を抽出（改善版）"""
    data = {}

    # 時刻の抽出
    time_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
    if time_match:
        data['timestamp'] = time_match.group(1)

    # 成功/失敗の判定（複数パターンに対応）
    if '✅' in line or '取得成功' in line or 'SUCCESS' in line:
        data['status'] = 'success'
        # 複数のパターンで人名と誕生年を抽出
        patterns = [
            r'取得成功: ([^→]+) → (\d{4})',
            r'✅ ([^:]+): (\d{4})',
            r'SUCCESS: ([^→]+) → (\d{4})',
            r'Found: ([^→]+) → (\d{4})'
        ]
        for pattern in patterns:
            name_match = re.search(pattern, line)
            if name_match:
                data['person_name'] = name_match.group(1).strip()
                data['birth_year'] = name_match.group(2)
                break

    elif '❌' in line or '取得失敗' in line or 'FAILED' in line or 'NOT_FOUND' in line:
        data['status'] = 'failed'
        patterns = [
            r'取得失敗: (.+)',
            r'❌ ([^:]+)',
            r'FAILED: (.+)',
            r'NOT_FOUND: (.+)'
        ]
        for pattern in patterns:
            name_match = re.search(pattern, line)
            if name_match:
                data['person_name'] = name_match.group(1).strip()
                break

    # 進捗情報の抽出（複数フォーマット対応）
    progress_patterns = [
        r'進捗: (\d+)/(\d+) \(([\d.]+)%\)',
        r'Progress: (\d+)/(\d+) \(([\d.]+)%\)',
        r'\[(\d+)/(\d+)\] \(([\d.]+)%\)',
        r'処理中: (\d+)/(\d+)'
    ]

    for pattern in progress_patterns:
        progress_match = re.search(pattern, line)
        if progress_match:
            data['current'] = int(progress_match.group(1))
            data['total'] = int(progress_match.group(2))
            if len(progress_match.groups()) >= 3:
                data['percentage'] = float(progress_match.group(3))
            else:
                data['percentage'] = (data['current'] / data['total'] * 100) if data['total'] > 0 else 0
            break

    # 統計情報の抽出
    if '取得成功:' in line and '件' in line:
        stats_match = re.search(r'取得成功: (\d+)件', line)
        if stats_match:
            data['found_count'] = int(stats_match.group(1))

    # 完了メッセージの検出
    if '処理完了' in line or 'Completed' in line or '最終結果' in line:
        data['status'] = 'completed'

    return data if data else None

def monitor_log_files_realtime():
    """ログファイルをリアルタイム監視（改善版）"""
    global progress_data

    # ファイルハンドルのキャッシュ
    file_handles = {}
    last_check_time = {}

    while True:
        try:
            # 監視対象のログファイルを探す
            monitored_files = []

            for pattern in LOG_FILES:
                if '*' in pattern:
                    # ワイルドカードパターンの処理
                    for file in Path('.').glob(pattern):
                        if file.exists():
                            monitored_files.append(str(file))
                else:
                    # 通常のファイル名
                    if Path(pattern).exists():
                        monitored_files.append(pattern)

            # 各ファイルをチェック
            for log_file in monitored_files:
                file_path = Path(log_file)

                # ファイルが更新されているか確認
                current_mtime = file_path.stat().st_mtime
                last_mtime = last_check_time.get(log_file, 0)

                if current_mtime > last_mtime:
                    last_check_time[log_file] = current_mtime

                    # ファイルハンドルを取得または作成
                    if log_file not in file_handles:
                        file_handles[log_file] = open(log_file, 'r', encoding='utf-8')
                        # 既存の内容をスキップして最後に移動
                        file_handles[log_file].seek(0, 2)

                    # 新しい行を読み取り
                    handle = file_handles[log_file]
                    new_lines = handle.readlines()

                    if new_lines:
                        progress_data['current_file'] = log_file
                        progress_data['last_update'] = datetime.now().isoformat()

                        # 新しい行を処理
                        for line in new_lines:
                            parsed = parse_log_line(line.strip())
                            if parsed:
                                # リアルタイムでデータを更新
                                if 'current' in parsed:
                                    progress_data['completed'] = parsed['current']
                                if 'total' in parsed:
                                    progress_data['total_records'] = parsed['total']
                                if 'percentage' in parsed:
                                    progress_data['processing'] = parsed['percentage']

                                # ステータスごとのカウント
                                if parsed.get('status') == 'success':
                                    progress_data['found'] += 1
                                elif parsed.get('status') == 'failed':
                                    progress_data['not_found'] += 1

                                # 最新ログに追加
                                progress_data['recent_logs'].append({
                                    'timestamp': datetime.now().isoformat(),
                                    'message': line.strip(),
                                    'data': parsed
                                })

                                # WebSocketで即座に配信
                                socketio.emit('progress_update', progress_data, namespace='/')

                        # 統計の再計算
                        if progress_data['completed'] > 0:
                            progress_data['success_rate'] = (
                                progress_data['found'] / progress_data['completed'] * 100
                            )

                        # 処理速度とETAの計算
                        if progress_data['start_time']:
                            elapsed = time.time() - progress_data['start_time']
                            if elapsed > 0 and progress_data['completed'] > 0:
                                progress_data['speed'] = progress_data['completed'] / (elapsed / 60)
                                remaining = progress_data['total_records'] - progress_data['completed']
                                if progress_data['speed'] > 0:
                                    progress_data['eta_minutes'] = remaining / progress_data['speed']

                        # ステータスの更新
                        if progress_data['total_records'] > 0:
                            if progress_data['completed'] >= progress_data['total_records']:
                                progress_data['status'] = 'completed'
                            elif progress_data['completed'] > 0:
                                progress_data['status'] = 'running'

            # 短い間隔でチェック（0.1秒）
            time.sleep(0.1)

        except Exception as e:
            progress_data['error_message'] = str(e)
            print(f"モニタリングエラー: {e}")
            time.sleep(1)

@app.route('/api/progress')
def get_progress():
    """進捗データをJSON形式で返す"""
    # dequeをリストに変換
    data = progress_data.copy()
    data['recent_logs'] = list(data['recent_logs'])
    return jsonify(data)

@app.route('/api/reset')
def reset_progress():
    """進捗データをリセット"""
    global progress_data
    progress_data.update({
        'status': 'idle',
        'start_time': None,
        'total_records': 0,
        'completed': 0,
        'processing': 0,
        'found': 0,
        'not_found': 0,
        'success_rate': 0.0,
        'speed': 0,
        'eta_minutes': 0,
        'recent_logs': deque(maxlen=50),
        'current_file': None,
        'error_message': None,
        'last_update': None
    })
    return jsonify({'status': 'reset'})

@app.route('/api/start/<process_type>')
def start_process(process_type):
    """処理を開始"""
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
        'recent_logs': deque(maxlen=50),
        'error_message': None,
        'last_update': datetime.now().isoformat()
    })

    socketio.emit('status_changed', {'status': 'running', 'type': process_type})
    return jsonify({'status': 'started', 'type': process_type})

@app.route('/')
def dashboard():
    """ダッシュボードを返す"""
    dashboard_path = Path('realtime_dashboard.html')
    if dashboard_path.exists():
        return send_from_directory('.', 'realtime_dashboard.html')
    else:
        return "Dashboard file not found", 404

@socketio.on('connect')
def handle_connect():
    """WebSocket接続時"""
    print(f"クライアント接続: {request.sid}")
    emit('connected', {'message': 'Connected to realtime monitor'})
    # 現在のデータを送信
    data = progress_data.copy()
    data['recent_logs'] = list(data['recent_logs'])
    emit('progress_update', data)

@socketio.on('disconnect')
def handle_disconnect():
    """WebSocket切断時"""
    print(f"クライアント切断: {request.sid}")

def main():
    """メイン処理"""
    # ログ監視スレッドを開始
    monitor_thread = threading.Thread(target=monitor_log_files_realtime, daemon=True)
    monitor_thread.start()

    # サーバーを起動
    print("=" * 60)
    print("🚀 Realtime Birth Collection Monitor Server")
    print("📊 Dashboard: http://localhost:5002")
    print("📡 API: http://localhost:5002/api/progress")
    print("🔌 WebSocket: ws://localhost:5002")
    print("=" * 60)

    socketio.run(app, host='0.0.0.0', port=5002, debug=False, allow_unsafe_werkzeug=True)

if __name__ == '__main__':
    from flask import request  # WebSocket用
    main()