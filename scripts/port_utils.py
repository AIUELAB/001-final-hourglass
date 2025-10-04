#!/usr/bin/env python3
"""
ポート管理ユーティリティ

ポートの可用性チェック、プロセスの健全性確認、再利用判定を提供
"""

import subprocess
import socket
import time
from typing import Optional, Tuple
from pathlib import Path

def is_port_available(port: int) -> bool:
    """ポートが利用可能かチェック"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', port))
            return True
    except OSError:
        return False

def get_process_using_port(port: int) -> Optional[int]:
    """指定ポートを使用しているプロセスのPIDを取得"""
    try:
        result = subprocess.run(
            ['lsof', '-ti', f':{port}'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return int(result.stdout.strip().split()[0])
        return None
    except (subprocess.TimeoutExpired, ValueError):
        return None

def is_process_healthy(pid: int, process_name: str) -> bool:
    """プロセスが健全に動作しているかチェック"""
    try:
        # プロセスが存在するか
        result = subprocess.run(
            ['ps', '-p', str(pid), '-o', 'comm='],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode != 0:
            return False

        # プロセス名が一致するか
        if process_name.lower() not in result.stdout.lower():
            return False

        return True
    except subprocess.TimeoutExpired:
        return False

def check_port_status(port: int, service_name: str, pid_file: Optional[Path] = None) -> Tuple[str, Optional[int]]:
    """
    ポートの状態を詳細にチェック

    Returns:
        (status, pid) where status is:
        - 'available': ポートが空いている
        - 'reusable': 正しいサービスが健全に動作中
        - 'occupied': 別のプロセスが使用中
        - 'unhealthy': サービスは動作中だが健全でない
    """
    # ポートが空いているかチェック
    if is_port_available(port):
        return ('available', None)

    # ポートを使用しているプロセスを特定
    pid_using_port = get_process_using_port(port)
    if pid_using_port is None:
        return ('available', None)

    # PIDファイルがある場合、一致を確認
    if pid_file and pid_file.exists():
        try:
            with open(pid_file) as f:
                expected_pid = int(f.read().strip())
            if expected_pid != pid_using_port:
                return ('occupied', pid_using_port)
        except (ValueError, OSError):
            pass

    # プロセスの健全性チェック
    if is_process_healthy(pid_using_port, service_name):
        return ('reusable', pid_using_port)
    else:
        return ('unhealthy', pid_using_port)

def check_http_endpoint(url: str, timeout: int = 5) -> bool:
    """HTTPエンドポイントの健全性チェック"""
    try:
        import urllib.request
        req = urllib.request.Request(url, method='GET')
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status in (200, 201, 204)
    except Exception:
        return False

def wait_for_port(port: int, timeout: int = 10) -> bool:
    """ポートがリッスン状態になるまで待機"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if not is_port_available(port):
            return True
        time.sleep(0.5)
    return False
