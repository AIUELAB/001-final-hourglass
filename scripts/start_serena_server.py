#!/usr/bin/env python3
"""
🚀 Serena MCP Server 自動起動スクリプト
Claude Code起動時に自動的にSerenaサーバーを起動する永続設定
"""

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import psutil

# port_utilsとport_registryをインポート
sys.path.insert(0, str(Path(__file__).parent))
from port_registry import get_registry, update_allocation
from port_utils import check_http_endpoint, wait_for_port

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
        "--transport",
        "sse",
        "--port",
        "8000",
        "--project",
        str(PROJECT_ROOT),
        "--enable-web-dashboard",
        "true",
        "--log-level",
        "INFO",
    ],
    "dashboard_url": "http://127.0.0.1:24282/dashboard/index.html",
    "api_url": "http://localhost:8000",
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
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmdline = proc.info.get("cmdline")
            if cmdline and "serena-mcp-server" in " ".join(cmdline):
                return True, proc.info["pid"]
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
        log_message("タイムアウト、SIGKILL送信...", "WARNING")
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
    """Serenaサーバーを起動（ポートレジストリ対応版）"""
    try:
        preferred_port = 8000
        pid_file = PROJECT_ROOT / ".pids" / "serena.pid"
        pid_file.parent.mkdir(exist_ok=True)

        log_message("Serena MCPサーバー起動処理...", "INFO")
        log_message(f"優先ポート: {preferred_port}", "INFO")

        # === ポートレジストリを使用した割り当て ===
        registry = get_registry()
        allocated_port, allocation_status = registry.allocate_port(
            service_name="serena",
            project_path=str(PROJECT_ROOT),
            preferred_port=preferred_port,
            health_endpoint=f"http://localhost:{preferred_port}/health",
        )

        log_message(f"ポート割り当て: {allocated_port} (status={allocation_status})", "INFO")

        # 既存プロセスを再利用する場合
        if allocation_status == "reused":
            log_message(f"✅ 既存のSerenaサーバーを再利用します (port={allocated_port})", "SUCCESS")
            log_message(f"ℹ️ ポート{allocated_port}で正常稼働中のため起動をスキップ", "INFO")

            # ヘルスチェック
            health_url = f"http://localhost:{allocated_port}/health"
            if check_http_endpoint(health_url):
                log_message("✅ ヘルスチェック成功", "SUCCESS")
                return True
            else:
                log_message("⚠️ ヘルスチェック失敗、新規起動します", "WARNING")
                # 既存の割り当てを解放して新規起動
                registry.release_port(allocated_port, str(PROJECT_ROOT))
                allocated_port, _ = registry.allocate_port(
                    service_name="serena",
                    project_path=str(PROJECT_ROOT),
                    preferred_port=preferred_port,
                    health_endpoint=f"http://localhost:{preferred_port}/health",
                )

        # ポートが優先ポートと異なる場合は警告
        if allocated_port != preferred_port:
            log_message(f"⚠️ 優先ポート{preferred_port}は使用中のため、ポート{allocated_port}を使用します", "WARNING")

        log_message(f"Serena MCPサーバーを起動しています... (port={allocated_port})", "INFO")

        # コマンドを構築（ポート番号を動的に設定）
        cmd = [
            SERENA_CONFIG["command"],
            "--from",
            "git+https://github.com/oraios/serena",
            "serena-mcp-server",
            "--transport",
            "sse",
            "--port",
            str(allocated_port),  # 動的ポート
            "--project",
            str(PROJECT_ROOT),
            "--enable-web-dashboard",
            "true",
            "--log-level",
            "INFO",
        ]

        # Serenaサーバーを起動（バックグラウンド）
        # ✅ FIX: ログファイルへの直接出力でバッファブロッキング回避
        with open(LOG_FILE, "a", encoding="utf-8") as log_file:
            process = subprocess.Popen(
                cmd,
                stdout=log_file,
                stderr=log_file,
                text=False,  # ファイルハンドルを使用する場合はFalse
                cwd=PROJECT_ROOT,
                start_new_session=True,  # 親プロセスから独立
            )

        # プロセスIDを記録
        with open(pid_file, "w") as f:
            f.write(str(process.pid))

        log_message(f"Serenaサーバーを起動しました (PID: {process.pid})", "SUCCESS")

        # レジストリにPIDを登録
        update_allocation(allocated_port, process.pid, "healthy")

        # ポートが開くまで待機
        log_message(f"⏳ ポート{allocated_port}の起動を待機中...", "INFO")
        # ✅ FIX: タイムアウトを60秒に延長（Serenaの初期化時間を考慮）
        if not wait_for_port(allocated_port, timeout=60):
            log_message("❌ サーバーが起動しませんでした（タイムアウト）", "ERROR")
            registry.release_port(allocated_port, str(PROJECT_ROOT))
            return False

        log_message("✅ Serenaサーバーが正常に起動しています", "SUCCESS")
        log_message("📊 ダッシュボード: http://127.0.0.1:24282/dashboard/index.html", "INFO")
        log_message(f"🔌 API: http://localhost:{allocated_port}", "INFO")

        # ✅ FIX: プロセスベースのヘルスチェック（/healthエンドポイントは存在しない）
        time.sleep(3)  # プロセス安定化待機
        try:
            proc = psutil.Process(process.pid)
            if proc.is_running() and "serena" in " ".join(proc.cmdline()).lower():
                log_message("✅ ヘルスチェック成功（プロセス確認）", "SUCCESS")
                update_allocation(allocated_port, process.pid, "healthy")
            else:
                log_message("⚠️ プロセスは起動したが状態が不明", "WARNING")
                update_allocation(allocated_port, process.pid, "unhealthy")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            log_message("⚠️ プロセス確認失敗、ポートリッスン状態で判定", "WARNING")
            update_allocation(allocated_port, process.pid, "healthy")

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

        config["serena_settings"].update(
            {
                "auto_start_serena": True,
                "serena_port": 8000,
                "enable_dashboard": True,
                "dashboard_url": SERENA_CONFIG["dashboard_url"],
                "api_url": SERENA_CONFIG["api_url"],
                "project_path": str(PROJECT_ROOT),
            }
        )

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

    # ❌ RCA-Kaizen #015: atexit.register(cleanup)を削除
    # デーモンプロセスは起動後もバックグラウンドで動作するため、
    # スクリプト終了時にプロセスを停止してはいけない。
    # 停止は別途 stop_serena_server.py で実装。

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
