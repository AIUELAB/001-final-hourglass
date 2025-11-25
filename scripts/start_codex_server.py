#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Codex MCPサーバー自動起動スクリプト
Claude Code起動時に自動的にCodexサーバーを起動
"""

import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# port_utilsとport_registryをインポート
sys.path.insert(0, str(Path(__file__).parent))
from port_registry import get_registry, update_allocation
from port_utils import check_http_endpoint, wait_for_port


def load_config():
    """設定ファイルを読み込む"""
    config_path = Path(__file__).parent.parent / "startup_config.json"

    if not config_path.exists():
        print(f"❌ 設定ファイルが見つかりません: {config_path}")
        return None

    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def kill_process_gracefully(pid: int, timeout: int = 5):
    """プロセスをグレースフルに終了"""
    try:
        print(f"  プロセス(PID: {pid})にSIGTERM送信...")
        os.kill(pid, signal.SIGTERM)

        # タイムアウトまで待機
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # プロセスが存在するかチェック
                os.kill(pid, 0)
                time.sleep(0.5)
            except ProcessLookupError:
                print("  ✅ プロセスが正常に終了しました")
                return True

        # タイムアウト後はSIGKILL
        print("  ⚠️ タイムアウト、SIGKILL送信...")
        os.kill(pid, signal.SIGKILL)
        time.sleep(1)
        print("  ✅ プロセスを強制終了しました")
        return True

    except ProcessLookupError:
        print("  ℹ️ プロセスは既に終了していました")
        return True
    except Exception as e:
        print(f"  ❌ プロセス終了エラー: {e}")
        return False


def start_codex_server(config: dict):
    """Codex MCPサーバーを起動（ポートレジストリ対応版）"""
    codex_settings = config.get("codex_settings", {})

    if not codex_settings.get("auto_start_codex", False):
        print("  ⚠️ Codex自動起動が無効になっています")
        return False

    preferred_port = codex_settings.get("codex_port", 8765)
    project_path = codex_settings.get("project_path", os.getcwd())
    pid_file = Path(project_path) / ".pids" / "codex.pid"

    print("\n🚀 Codex MCPサーバー起動処理...")
    print(f"  優先ポート: {preferred_port}")
    print(f"  プロジェクト: {project_path}")

    # === ポートレジストリを使用した割り当て ===
    registry = get_registry()
    allocated_port, allocation_status = registry.allocate_port(
        service_name="codex",
        project_path=project_path,
        preferred_port=preferred_port,
        health_endpoint=f"http://localhost:{preferred_port}/health",
    )

    print(f"  ポート割り当て: {allocated_port} (status={allocation_status})")

    # 既存プロセスを再利用する場合
    if allocation_status == "reused":
        print(f"  ✅ 既存のCodexサーバーを再利用します (port={allocated_port})")
        print(f"  ℹ️ ポート{allocated_port}で正常稼働中のため起動をスキップ")

        # ヘルスチェック
        health_url = f"http://localhost:{allocated_port}/health"
        if check_http_endpoint(health_url):
            print("  ✅ ヘルスチェック成功")
            return True
        else:
            print("  ⚠️ ヘルスチェック失敗、新規起動します")
            # 既存の割り当てを解放して新規起動
            registry.release_port(allocated_port, project_path)
            allocated_port, _ = registry.allocate_port(
                service_name="codex",
                project_path=project_path,
                preferred_port=preferred_port,
                health_endpoint=f"http://localhost:{preferred_port}/health",
            )

    # ポートが優先ポートと異なる場合は警告
    if allocated_port != preferred_port:
        print(f"  ⚠️ 優先ポート{preferred_port}は使用中のため、ポート{allocated_port}を使用します")

    # サーバー起動
    server_script = Path(project_path) / "codex_mcp_server.py"

    if not server_script.exists():
        print(f"  ❌ サーバースクリプトが見つかりません: {server_script}")
        registry.release_port(allocated_port, project_path)
        return False

    # バックグラウンドで起動
    log_file = Path(project_path) / "codex_server.log"

    try:
        # Python3で直接起動（動的ポート番号を使用）
        cmd = [
            sys.executable,
            str(server_script),
            "--port",
            str(allocated_port),  # 動的ポート
            "--log-level",
            codex_settings.get("log_level", "INFO"),
        ]

        # ログファイルに出力しながらバックグラウンド実行
        with open(log_file, "a") as log:
            process = subprocess.Popen(
                cmd, stdout=log, stderr=subprocess.STDOUT, cwd=project_path, start_new_session=True
            )

        print(f"  📝 プロセスID: {process.pid}")
        print(f"  📝 ログファイル: {log_file}")

        # PIDファイル保存
        pid_file.parent.mkdir(exist_ok=True)
        with open(pid_file, "w") as f:
            f.write(str(process.pid))

        # レジストリにPIDを登録
        update_allocation(allocated_port, process.pid, "healthy")

        # ポートが開くまで待機
        print(f"  ⏳ ポート{allocated_port}の起動を待機中...")
        # ✅ FIX: タイムアウトを30秒に延長
        if not wait_for_port(allocated_port, timeout=30):
            print("  ❌ サーバーが起動しませんでした（タイムアウト）")
            registry.release_port(allocated_port, project_path)
            return False

        print(f"  ✅ Codex MCPサーバーが起動しました (ポート: {allocated_port})")

        # ヘルスチェック
        health_url = f"http://localhost:{allocated_port}/health"
        if check_http_endpoint(health_url):
            print("  ✅ ヘルスチェック成功")
            update_allocation(allocated_port, process.pid, "healthy")
        else:
            print("  ⚠️ ヘルスチェックは失敗しましたが起動は成功")
            update_allocation(allocated_port, process.pid, "unhealthy")

        return True

    except Exception as e:
        print(f"  ❌ サーバー起動エラー: {e}")
        # ログの最後の数行を表示
        if "log_file" in locals():
            log_file = locals()["log_file"]
            if log_file.exists():
                with open(log_file, "r") as f:
                    lines = f.readlines()
                    if lines:
                        print("  最新のログ:")
                        for line in lines[-5:]:
                            print(f"    {line.strip()}")
            return False

    except Exception as e:
        print(f"  ❌ サーバー起動エラー: {e}")
        return False


def enable_ai_collaboration(config: dict):
    """AI協調機能を有効化"""
    codex_settings = config.get("codex_settings", {})

    if not codex_settings.get("enable_ai_collaboration", False):
        print("  AI協調機能は無効です")
        return

    print("\n🤝 AI協調機能を有効化中...")

    features = codex_settings.get("collaboration_features", {})
    enabled_features = [k for k, v in features.items() if v]

    if enabled_features:
        print("  有効な機能:")
        for feature in enabled_features:
            print(f"    ✅ {feature}")

    # キャッシュディレクトリ作成
    if codex_settings.get("cache_enabled", False):
        cache_dir = Path(codex_settings.get("cache_dir", ".collaboration_cache"))
        cache_dir.mkdir(exist_ok=True)
        print(f"  📁 キャッシュディレクトリ: {cache_dir}")


def main():
    """メイン処理"""
    print("=" * 60)
    print("🤖 Codex MCPサーバー自動起動システム")
    print(f"実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 設定読み込み
    config = load_config()
    if not config:
        return 1

    # Codexサーバー起動
    if start_codex_server(config):
        # AI協調機能有効化
        enable_ai_collaboration(config)

        print("\n✅ Codex MCPサーバーが正常に起動しました")
        print("  AI協調分析システムが利用可能です")

        # 起動成功を記録
        status_file = Path("codex_startup_status.json")
        status = {
            "status": "running",
            "started_at": datetime.now().isoformat(),
            "port": config["codex_settings"]["codex_port"],
            "features": config["codex_settings"].get("collaboration_features", {}),
        }

        with open(status_file, "w") as f:
            json.dump(status, f, indent=2)

        return 0
    else:
        print("\n❌ Codex MCPサーバーの起動に失敗しました")
        return 1


if __name__ == "__main__":
    sys.exit(main())
