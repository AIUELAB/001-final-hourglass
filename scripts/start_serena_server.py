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

# port_utilsをインポート
sys.path.insert(0, str(Path(__file__).parent))
from port_utils import check_port_status, wait_for_port, check_http_endpoint

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent

# ログファイル
LOG_FILE = PROJECT_ROOT / "logs" / "serena.log"
LOG_FILE.parent.mkdir(exist_ok=True)

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

def kill_process_gracefully(pid: int, timeout: int = 5) -> bool:
    """プロセスをグレースフルに終了"""
    try:
        log_message(f"プロセス(PID: {pid})にSIGTERM送信...", "INFO")
        os.kill(pid, signal.SIGTERM)

        # タイムアウトまで待機
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                os.kill(pid, 0)
                time.sleep(0.5)
            except ProcessLookupError:
                log_message("プロセスが正常に終了しました", "SUCCESS")
                return True

        # タイムアウト後はSIGKILL
        log_message(f"タイムアウト、SIGKILL送信...", "WARNING")
        os.kill(pid, signal.SIGKILL)
        time.sleep(1)
        log_message("プロセスを強制終了しました", "INFO")
        return True

    except ProcessLookupError:
        log_message("プロセスは既に終了していました", "INFO")
        return True
    except Exception as e:
        log_message(f"プロセス終了エラー: {e}", "ERROR")
        return False

def start_serena_server():
    """Serenaサーバーを起動"""
    try:
        port = 8000
        pid_file = PROJECT_ROOT / ".pids" / "serena.pid"
        pid_file.parent.mkdir(exist_ok=True)

        log_message("Serena MCPサーバー起動処理...", "INFO")
        log_message(f"ポート: {port}", "INFO")

        # ポート状態の詳細チェック
        status, existing_pid = check_port_status(port, "serena", pid_file)

        if status == 'reusable':
            log_message(f"✅ 既存のSerenaサーバー(PID: {existing_pid})を再利用します", "SUCCESS")
            log_message(f"ℹ️ ポート{port}で正常稼働中のため起動をスキップ", "INFO")

            # ヘルスチェック
            health_url = f"http://localhost:{port}/health"
            if check_http_endpoint(health_url):
                log_message("✅ ヘルスチェック成功", "SUCCESS")
                return True
            else:
                log_message("⚠️ ヘルスチェック失敗、再起動します", "WARNING")
                status = 'unhealthy'

        if status == 'unhealthy' or status == 'occupied':
            log_message(f"⚠️ ポート{port}が不正な状態です (PID: {existing_pid})", "WARNING")
            if kill_process_gracefully(existing_pid):
                log_message("✅ 既存プロセスを終了しました", "INFO")
            else:
                log_message("❌ プロセス終了に失敗", "ERROR")
                return False
            time.sleep(1)

        elif status == 'available':
            log_message(f"✅ ポート{port}は利用可能です", "INFO")

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
        with open(pid_file, "w") as f:
            f.write(str(process.pid))

        log_message(f"Serenaサーバーを起動しました (PID: {process.pid})", "SUCCESS")

        # ポートが開くまで待機
        log_message(f"⏳ ポート{port}の起動を待機中...", "INFO")
        if not wait_for_port(port, timeout=15):
            log_message(f"❌ サーバーが起動しませんでした（タイムアウト）", "ERROR")
            return False

        log_message("✅ Serenaサーバーが正常に起動しています", "SUCCESS")
        log_message(f"📊 ダッシュボード: {SERENA_CONFIG['dashboard_url']}", "INFO")
        log_message(f"🔌 API: {SERENA_CONFIG['api_url']}", "INFO")

        # ヘルスチェック
        health_url = f"http://localhost:{port}/health"
        if check_http_endpoint(health_url):
            log_message("✅ ヘルスチェック成功", "SUCCESS")
        else:
            log_message("⚠️ ヘルスチェックは失敗しましたが起動は成功", "WARNING")

        return True
            
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