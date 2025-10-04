#!/usr/bin/env python3
"""
🎯 統合MCP管理システム
全てのMCPサーバーを一元管理する統一システム
Created: 2025-10-01
"""

import subprocess
import json
import os
import sys
import time
# import psutil  # 権限エラーを回避するため使用しない
import signal
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import asyncio
import atexit
from dotenv import load_dotenv
from stdio_mcp_handler import STDIOMCPServer

# .envファイルから環境変数を読み込み
load_dotenv()

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent
LOGS_DIR = PROJECT_ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)

class ServerStatus(Enum):
    """サーバーステータス"""
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    STARTING = "starting"
    STOPPING = "stopping"

@dataclass
class MCPServer:
    """MCPサーバー定義"""
    name: str
    command: str
    args: List[str]
    port: Optional[int] = None
    dashboard_url: Optional[str] = None
    api_url: Optional[str] = None
    priority: int = 0  # 起動優先度（0が最高）
    health_check_url: Optional[str] = None
    auto_start: bool = True
    transport_mode: str = "HTTP"  # HTTP, SSE, STDIO

class UnifiedMCPManager:
    """統合MCP管理システム"""

    def __init__(self):
        self.servers: Dict[str, MCPServer] = {}
        self.processes: Dict[str, subprocess.Popen] = {}
        self.stdio_servers: Dict[str, STDIOMCPServer] = {}  # STDIO型サーバー専用
        self.status: Dict[str, ServerStatus] = {}
        self.log_file = LOGS_DIR / "mcp_manager.log"

        # サーバー定義
        self._initialize_servers()

        # 終了時のクリーンアップ登録
        atexit.register(self.cleanup)
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _initialize_servers(self):
        """サーバー定義の初期化"""

        # Serena MCP Server（最優先）
        self.servers["serena"] = MCPServer(
            name="Serena MCP",
            command="uvx",
            args=[
                "--from", "git+https://github.com/oraios/serena",
                "serena-mcp-server",
                "--transport", "sse",
                "--port", "8000",
                "--project", str(PROJECT_ROOT),
                "--enable-web-dashboard", "true",
                "--log-level", "INFO"
            ],
            port=8000,
            dashboard_url="http://127.0.0.1:24282/dashboard/index.html",
            api_url="http://localhost:8000",
            health_check_url=None,  # SSEトランスポートはHTTPヘルスチェック不可のためプロセス確認のみ
            priority=0,
            auto_start=True,
            transport_mode="SSE"
        )

        # Codex MCP Server（AI協調）
        self.servers["codex"] = MCPServer(
            name="Codex MCP",
            command="python3",
            args=[str(PROJECT_ROOT / "codex_mcp_server.py")],
            port=8765,
            api_url="http://localhost:8765",
            health_check_url="http://localhost:8765/health",
            priority=1,
            auto_start=True
        )

        # Memory MCP Server（長期記憶管理）
        self.servers["memory"] = MCPServer(
            name="Memory MCP",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-memory"],
            port=None,
            api_url=None,
            health_check_url=None,
            priority=1,
            auto_start=True,  # STDIO対応により自動起動可能
            transport_mode="STDIO"
        )

        # Sequential Thinking MCP Server（順次思考処理）
        self.servers["sequential-thinking"] = MCPServer(
            name="Sequential Thinking MCP",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-sequential-thinking"],
            port=None,
            api_url=None,
            health_check_url=None,
            priority=1,
            auto_start=True,  # STDIO対応により自動起動可能
            transport_mode="STDIO"
        )

        # Smithery CLI（MCPツール管理）
        # 注：Smitheryは通常のMCPサーバーではなくCLIツール
        # 現時点では無効化（将来的に別実装が必要）
        self.servers["smithery"] = MCPServer(
            name="Smithery CLI",
            command="npx",
            args=["-y", "@smithery/cli"],  # 正しいパッケージ名
            port=None,
            api_url=None,
            health_check_url=None,
            priority=2,
            auto_start=False,  # CLIツールのため自動起動は無効
            transport_mode="CLI"  # CLIモード（MCPサーバーではない）
        )

        # Ebook MCP Server（電子書籍処理）
        self.servers["ebook"] = MCPServer(
            name="Ebook MCP",
            command="ebook-mcp",
            args=[],
            port=None,
            priority=2,
            auto_start=True,
            transport_mode="STDIO"
        )

        # 他のMCPサーバー設定をここに追加可能

    def log(self, message: str, level: str = "INFO"):
        """ログ記録"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"

        print(f"{'🔴' if level == 'ERROR' else '🟢' if level == 'SUCCESS' else '🔹'} {message}")

        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"{log_entry}\n")

    def is_port_in_use(self, port: int) -> bool:
        """ポートが使用中か確認"""
        try:
            # lsofを使用してポート確認（psutil不要）
            result = subprocess.run(
                ["lsof", "-i", f":{port}"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except:
            return False

    def kill_process_on_port(self, port: int) -> bool:
        """指定ポートのプロセスを終了"""
        try:
            # lsofでPIDを取得
            result = subprocess.run(
                ["lsof", "-t", "-i", f":{port}"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                pid = int(result.stdout.strip().split('\n')[0])
                os.kill(pid, signal.SIGTERM)
                time.sleep(1)
                try:
                    os.kill(pid, 0)  # プロセス存在確認
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                self.log(f"Port {port}のプロセスを終了しました")
                return True
        except Exception as e:
            self.log(f"Port {port}のプロセス終了に失敗: {e}", "ERROR")
        return False

    def start_server(self, name: str) -> bool:
        """サーバーを起動"""
        if name not in self.servers:
            self.log(f"サーバー {name} が定義されていません", "ERROR")
            return False

        server = self.servers[name]

        # STDIOモードのサーバーは専用ハンドラーを使用
        if server.transport_mode == "STDIO":
            return self._start_stdio_server(name)

        # 既に起動している場合
        if name in self.processes and self.processes[name].poll() is None:
            self.log(f"{server.name} は既に起動しています")
            return True

        # ポートが使用中の場合は既存プロセスを終了
        if server.port and self.is_port_in_use(server.port):
            self.log(f"Port {server.port} が使用中です。既存プロセスを終了します")
            self.kill_process_on_port(server.port)
            time.sleep(2)

        # サーバー起動
        try:
            self.status[name] = ServerStatus.STARTING
            self.log(f"{server.name} を起動中...")

            cmd = [server.command] + server.args

            # 環境変数を設定（Smithery用）
            env = os.environ.copy()
            if name == "smithery" and os.getenv("SMITHERY_API_KEY"):
                env["SMITHERY_API_KEY"] = os.getenv("SMITHERY_API_KEY")

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=PROJECT_ROOT,
                env=env
            )

            self.processes[name] = process
            time.sleep(3)  # 起動待機

            # プロセス確認
            if process.poll() is None:
                self.status[name] = ServerStatus.RUNNING
                self.log(f"{server.name} が起動しました", "SUCCESS")

                if server.dashboard_url:
                    self.log(f"Dashboard: {server.dashboard_url}")
                if server.api_url:
                    self.log(f"API: {server.api_url}")

                return True
            else:
                self.status[name] = ServerStatus.ERROR
                self.log(f"{server.name} の起動に失敗しました", "ERROR")
                return False

        except Exception as e:
            self.status[name] = ServerStatus.ERROR
            self.log(f"{server.name} 起動エラー: {e}", "ERROR")
            return False

    def _start_stdio_server(self, name: str) -> bool:
        """STDIOモードのサーバーを起動"""
        if name in self.stdio_servers and self.stdio_servers[name].is_alive():
            self.log(f"{self.servers[name].name} は既に起動しています")
            return True

        server = self.servers[name]
        try:
            # 環境変数を設定
            env = os.environ.copy()
            if name == "smithery" and os.getenv("SMITHERY_API_KEY"):
                env["SMITHERY_API_KEY"] = os.getenv("SMITHERY_API_KEY")

            # STDIOサーバーインスタンスを作成
            cmd = [server.command] + server.args
            stdio_server = STDIOMCPServer(server.name, cmd)

            # 環境変数を考慮して起動
            original_env = os.environ.copy()
            os.environ.update(env)

            success = stdio_server.start()

            # 環境変数を復元
            os.environ.clear()
            os.environ.update(original_env)

            if success:
                self.stdio_servers[name] = stdio_server
                self.status[name] = ServerStatus.RUNNING
                return True
            else:
                self.status[name] = ServerStatus.ERROR
                return False

        except Exception as e:
            self.status[name] = ServerStatus.ERROR
            self.log(f"{server.name} STDIO起動エラー: {e}", "ERROR")
            return False

    def stop_server(self, name: str) -> bool:
        """サーバーを停止"""
        # STDIOサーバーの場合
        if name in self.stdio_servers:
            try:
                self.status[name] = ServerStatus.STOPPING
                self.stdio_servers[name].stop()
                del self.stdio_servers[name]
                self.status[name] = ServerStatus.STOPPED
                return True
            except Exception as e:
                self.log(f"{name} STDIO停止エラー: {e}", "ERROR")
                return False

        # 通常のサーバーの場合
        if name not in self.processes:
            self.log(f"{name} は起動していません")
            return True

        try:
            self.status[name] = ServerStatus.STOPPING
            process = self.processes[name]

            if process.poll() is None:
                process.terminate()
                time.sleep(2)

                if process.poll() is None:
                    process.kill()
                    time.sleep(1)

            del self.processes[name]
            self.status[name] = ServerStatus.STOPPED
            self.log(f"{self.servers[name].name} を停止しました", "SUCCESS")
            return True

        except Exception as e:
            self.log(f"{name} 停止エラー: {e}", "ERROR")
            return False

    def restart_server(self, name: str) -> bool:
        """サーバーを再起動"""
        self.log(f"{self.servers[name].name} を再起動します")
        self.stop_server(name)
        time.sleep(2)
        return self.start_server(name)

    def start_all(self) -> Dict[str, bool]:
        """全サーバーを優先度順に起動"""
        results = {}

        # 優先度順にソート
        sorted_servers = sorted(
            self.servers.items(),
            key=lambda x: x[1].priority
        )

        for name, server in sorted_servers:
            if server.auto_start:
                results[name] = self.start_server(name)
                time.sleep(2)  # サーバー間の起動間隔

        return results

    def stop_all(self):
        """全サーバーを停止"""
        # 通常のサーバーを停止
        for name in list(self.processes.keys()):
            self.stop_server(name)

        # STDIOサーバーを停止
        for name in list(self.stdio_servers.keys()):
            self.stop_server(name)

    def status_all(self) -> Dict[str, str]:
        """全サーバーのステータス取得"""
        status = {}
        for name, server in self.servers.items():
            if server.transport_mode == "STDIO" and name in self.stdio_servers:
                if self.stdio_servers[name].is_alive():
                    status[name] = "🟢 Running (STDIO)"
                else:
                    status[name] = "🔴 Stopped"
            elif name in self.processes and self.processes[name].poll() is None:
                status[name] = "🟢 Running"
            else:
                status[name] = "🔴 Stopped"
        return status

    def health_check(self, name: str, timeout: int = 5) -> bool:
        """ヘルスチェック"""
        if name not in self.servers:
            return False

        server = self.servers[name]

        # CLIツールはヘルスチェック対象外
        if server.transport_mode == "CLI":
            return False

        # STDIOサーバーの場合
        if server.transport_mode == "STDIO" and name in self.stdio_servers:
            return self.stdio_servers[name].health_check()

        # SSEサーバーの場合（Serena）- プロセス確認のみ
        if server.transport_mode == "SSE":
            # SSEはHTTPヘルスチェック非対応、プロセス生存確認のみ
            is_alive = name in self.processes and self.processes[name].poll() is None
            # ダッシュボードチェックは無効化（再起動ループ防止）
            # SSEサーバーはプロセス生存確認のみで十分
            return is_alive

        # HTTPヘルスチェックURLがある場合
        if server.health_check_url:
            try:
                import requests
                response = requests.get(server.health_check_url, timeout=timeout)
                return response.status_code == 200
            except:
                return False

        # プロセス確認のみ
        return name in self.processes and self.processes[name].poll() is None

    def cleanup(self):
        """クリーンアップ処理"""
        self.log("MCPマネージャーをシャットダウンします")
        self.stop_all()

    def _signal_handler(self, signum, frame):
        """シグナルハンドラ"""
        self.log(f"シグナル {signum} を受信しました")
        self.cleanup()
        sys.exit(0)

# CLIインターフェース
def main():
    """メインエントリーポイント"""
    import argparse

    parser = argparse.ArgumentParser(description="統合MCP管理システム")
    parser.add_argument("action", choices=["start", "stop", "restart", "status", "start-all", "stop-all"],
                       help="実行アクション")
    parser.add_argument("--server", help="サーバー名（serena, codex等）")

    args = parser.parse_args()

    manager = UnifiedMCPManager()

    if args.action == "start-all":
        results = manager.start_all()
        print("\n📊 起動結果:")
        for name, success in results.items():
            print(f"  {name}: {'✅' if success else '❌'}")

    elif args.action == "stop-all":
        manager.stop_all()
        print("✅ 全サーバーを停止しました")

    elif args.action == "status":
        status = manager.status_all()
        print("\n📊 サーバーステータス:")
        for name, state in status.items():
            print(f"  {name}: {state}")

    elif args.action in ["start", "stop", "restart"]:
        if not args.server:
            print("❌ --server オプションが必要です")
            sys.exit(1)

        if args.action == "start":
            success = manager.start_server(args.server)
        elif args.action == "stop":
            success = manager.stop_server(args.server)
        else:  # restart
            success = manager.restart_server(args.server)

        if not success:
            sys.exit(1)

    # プロセス維持（バックグラウンド実行時）
    if args.action in ["start", "start-all"]:
        print("\n🔄 MCPマネージャーが実行中です。Ctrl+C で停止します。")

        # サーバー別のヘルスチェック設定
        health_check_intervals = {
            "serena": 300,  # SSEサーバーは5分間隔
            "codex": 60,    # HTTPサーバーは1分間隔
            "memory": 60,   # STDIOサーバーは1分間隔
            "sequential-thinking": 60,
            "smithery": 0   # CLIツールはチェック不要
        }

        # サーバー別のタイムアウト設定
        health_check_timeouts = {
            "serena": 10,   # SSEサーバーは10秒
            "codex": 15,    # Codexは15秒（処理重いため延長）
            "memory": 5,    # STDIOサーバーは5秒
            "sequential-thinking": 5,
            "smithery": 5
        }

        last_check_times = {name: 0 for name in manager.servers.keys()}

        try:
            while True:
                time.sleep(30)  # 30秒ごとにループ
                current_time = time.time()

                # 各サーバーのヘルスチェック
                for name in manager.servers.keys():
                    if name in manager.processes or name in manager.stdio_servers:
                        interval = health_check_intervals.get(name, 60)
                        if interval > 0:  # 0の場合はチェック不要
                            if current_time - last_check_times[name] >= interval:
                                timeout = health_check_timeouts.get(name, 5)
                                if not manager.health_check(name, timeout):
                                    manager.log(f"{name} のヘルスチェック失敗。再起動します。", "WARNING")
                                    manager.restart_server(name)
                                last_check_times[name] = current_time
        except KeyboardInterrupt:
            manager.cleanup()

if __name__ == "__main__":
    main()