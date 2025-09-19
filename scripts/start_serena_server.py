#!/usr/bin/env python3
"""
🚀 Serena MCP Server 自動起動スクリプト
Claude Code起動時に自動的にSerenaサーバーを起動する永続設定
"""

import subprocess
import json
import os
import sys
import time
import psutil
from pathlib import Path
import signal
import atexit

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent

# ログファイル
LOG_FILE = PROJECT_ROOT / "serena_startup.log"

# Serena設定
SERENA_CONFIG = {
    "command": "uvx",
    "args": [
        "--from",
        "git+https://github.com/oraios/serena",
        "serena-mcp-server",
        "--transport", "sse",
        "--port", "8000",
        "--project", str(PROJECT_ROOT),
        "--enable-web-dashboard", "true",
        "--log-level", "INFO"
    ],
    "dashboard_url": "http://127.0.0.1:24282/dashboard/index.html",
    "api_url": "http://localhost:8000"
}

def log_message(message, level="INFO"):
    """ログメッセージを記録"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{level}] {message}\n"
    
    print(f"🔹 {message}")
    
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_entry)

def is_serena_running():
    """Serenaサーバーが既に起動しているかチェック"""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info.get('cmdline')
            if cmdline and 'serena-mcp-server' in ' '.join(cmdline):
                return True, proc.info['pid']
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False, None

def kill_existing_serena():
    """既存のSerenaプロセスを終了"""
    running, pid = is_serena_running()
    if running:
        log_message(f"既存のSerenaプロセス（PID: {pid}）を終了します", "WARNING")
        try:
            os.kill(pid, signal.SIGTERM)
            time.sleep(2)
            # まだ生きていたら強制終了
            if is_serena_running()[0]:
                os.kill(pid, signal.SIGKILL)
                time.sleep(1)
            log_message("既存のSerenaプロセスを終了しました", "INFO")
        except Exception as e:
            log_message(f"プロセス終了エラー: {e}", "ERROR")

def start_serena_server():
    """Serenaサーバーを起動"""
    try:
        # 既存プロセスのチェックと終了
        if is_serena_running()[0]:
            kill_existing_serena()
        
        log_message("Serena MCPサーバーを起動しています...", "INFO")
        
        # コマンドを構築
        cmd = [SERENA_CONFIG["command"]] + SERENA_CONFIG["args"]
        
        # Serenaサーバーを起動（バックグラウンド）
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=PROJECT_ROOT
        )
        
        # プロセスIDを記録
        pid_file = PROJECT_ROOT / ".serena_pid"
        with open(pid_file, "w") as f:
            f.write(str(process.pid))
        
        log_message(f"Serenaサーバーを起動しました (PID: {process.pid})", "SUCCESS")
        
        # 起動確認（5秒待機）
        time.sleep(5)
        
        if process.poll() is None:
            log_message("✅ Serenaサーバーが正常に起動しています", "SUCCESS")
            log_message(f"📊 ダッシュボード: {SERENA_CONFIG['dashboard_url']}", "INFO")
            log_message(f"🔌 API: {SERENA_CONFIG['api_url']}", "INFO")
            return True
        else:
            # エラー出力を取得
            stdout, stderr = process.communicate()
            log_message(f"Serenaサーバーの起動に失敗しました", "ERROR")
            if stderr:
                log_message(f"エラー詳細: {stderr}", "ERROR")
            return False
            
    except Exception as e:
        log_message(f"Serenaサーバー起動エラー: {str(e)}", "ERROR")
        return False

def update_startup_config():
    """起動設定にSerena自動起動を追加"""
    config_file = PROJECT_ROOT / "startup_config.json"
    
    try:
        # 既存の設定を読み込み
        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
        else:
            config = {}
        
        # Serena自動起動設定を追加
        if "serena_settings" not in config:
            config["serena_settings"] = {}
        
        config["serena_settings"].update({
            "auto_start_serena": True,
            "serena_port": 8000,
            "enable_dashboard": True,
            "dashboard_url": SERENA_CONFIG["dashboard_url"],
            "api_url": SERENA_CONFIG["api_url"],
            "project_path": str(PROJECT_ROOT)
        })
        
        # 設定を保存
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        log_message("起動設定を更新しました", "SUCCESS")
        
    except Exception as e:
        log_message(f"設定更新エラー: {str(e)}", "ERROR")

def cleanup():
    """終了時のクリーンアップ"""
    pid_file = PROJECT_ROOT / ".serena_pid"
    if pid_file.exists():
        try:
            with open(pid_file, "r") as f:
                pid = int(f.read().strip())
            
            # プロセスが存在するか確認
            if psutil.pid_exists(pid):
                log_message(f"Serenaサーバー (PID: {pid}) を停止します", "INFO")
                os.kill(pid, signal.SIGTERM)
                time.sleep(2)
            
            # PIDファイルを削除
            pid_file.unlink()
            
        except Exception as e:
            log_message(f"クリーンアップエラー: {e}", "WARNING")

def main():
    """メイン処理"""
    log_message("=" * 50, "INFO")
    log_message("🚀 Serena自動起動スクリプト開始", "INFO")
    
    # クリーンアップハンドラを登録
    atexit.register(cleanup)
    
    # Serenaサーバーを起動
    if start_serena_server():
        # 起動設定を更新
        update_startup_config()
        
        log_message("=" * 50, "INFO")
        log_message("✨ Serena MCPサーバーが起動完了しました！", "SUCCESS")
        log_message("=" * 50, "INFO")
        
        # バックグラウンドで実行を継続
        print("\n📌 Serenaサーバーはバックグラウンドで実行中です")
        print("停止するには: pkill -f serena-mcp-server")
        
        return 0
    else:
        log_message("❌ Serenaサーバーの起動に失敗しました", "ERROR")
        return 1

if __name__ == "__main__":
    sys.exit(main())