#!/usr/bin/env python3
"""
STDIO Mode MCP Server Handler
JSON-RPC通信をサポートするMCPサーバー専用ハンドラー
Created: 2025-10-01
"""

import subprocess
import json
import threading
import queue
import time
from pathlib import Path
from typing import Optional, Dict, Any
import sys

class STDIOMCPServer:
    """STDIO方式のMCPサーバーハンドラー"""

    def __init__(self, name: str, command: list):
        self.name = name
        self.command = command
        self.process: Optional[subprocess.Popen] = None
        self.request_id = 0
        self.responses = {}
        self.response_queue = queue.Queue()
        self.is_running = False
        self.reader_thread: Optional[threading.Thread] = None

    def start(self) -> bool:
        """サーバーを起動"""
        try:
            print(f"🔄 Starting {self.name} in STDIO mode...")

            # STDIOモードでプロセスを起動
            self.process = subprocess.Popen(
                self.command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line buffered
                universal_newlines=True
            )

            self.is_running = True

            # 読み取りスレッドを開始
            self.reader_thread = threading.Thread(target=self._read_output, daemon=True)
            self.reader_thread.start()

            # 初期化リクエストを送信
            if self._initialize():
                print(f"✅ {self.name} started successfully in STDIO mode")
                return True
            else:
                print(f"❌ {self.name} initialization failed")
                self.stop()
                return False

        except Exception as e:
            print(f"❌ Failed to start {self.name}: {e}")
            return False

    def _initialize(self) -> bool:
        """JSON-RPC初期化"""
        try:
            # MCP初期化リクエスト
            init_request = {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "0.1.0",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "MCP Manager",
                        "version": "1.0.0"
                    }
                },
                "id": self._get_next_id()
            }

            # リクエスト送信
            response = self._send_request(init_request)

            if response and "result" in response:
                print(f"🔹 {self.name} initialized: {response['result'].get('serverInfo', {})}")

                # initialized通知を送信
                initialized_notification = {
                    "jsonrpc": "2.0",
                    "method": "initialized",
                    "params": {}
                }
                self._send_notification(initialized_notification)
                return True

            return False

        except Exception as e:
            print(f"❌ Initialization error for {self.name}: {e}")
            return False

    def _send_request(self, request: Dict[str, Any], timeout: float = 5.0) -> Optional[Dict]:
        """リクエストを送信して応答を待つ"""
        if not self.process or not self.process.stdin:
            return None

        try:
            request_id = request.get("id")
            request_json = json.dumps(request) + "\n"

            # リクエスト送信
            self.process.stdin.write(request_json)
            self.process.stdin.flush()

            # 応答を待つ
            start_time = time.time()
            while time.time() - start_time < timeout:
                if request_id in self.responses:
                    return self.responses.pop(request_id)
                time.sleep(0.1)

            print(f"⚠️ Timeout waiting for response from {self.name}")
            return None

        except Exception as e:
            print(f"❌ Error sending request to {self.name}: {e}")
            return None

    def _send_notification(self, notification: Dict[str, Any]):
        """通知を送信（応答を待たない）"""
        if not self.process or not self.process.stdin:
            return

        try:
            notification_json = json.dumps(notification) + "\n"
            self.process.stdin.write(notification_json)
            self.process.stdin.flush()
        except Exception as e:
            print(f"❌ Error sending notification to {self.name}: {e}")

    def _read_output(self):
        """stdout読み取りスレッド"""
        if not self.process or not self.process.stdout:
            return

        try:
            while self.is_running:
                line = self.process.stdout.readline()
                if not line:
                    break

                line = line.strip()
                if not line:
                    continue

                try:
                    # JSON-RPCメッセージをパース
                    message = json.loads(line)

                    # レスポンスの場合
                    if "id" in message and "result" in message:
                        self.responses[message["id"]] = message
                    # エラーの場合
                    elif "id" in message and "error" in message:
                        print(f"🔴 Error from {self.name}: {message['error']}")
                        self.responses[message["id"]] = message
                    # 通知の場合
                    elif "method" in message and "id" not in message:
                        print(f"🔔 Notification from {self.name}: {message['method']}")

                except json.JSONDecodeError:
                    # JSON以外の出力（デバッグメッセージなど）
                    if line:
                        print(f"📝 {self.name}: {line}")

        except Exception as e:
            print(f"❌ Reader thread error for {self.name}: {e}")

    def _get_next_id(self) -> int:
        """次のリクエストIDを取得"""
        self.request_id += 1
        return self.request_id

    def stop(self):
        """サーバーを停止"""
        self.is_running = False

        if self.process:
            try:
                # shutdown通知を送信
                shutdown_notification = {
                    "jsonrpc": "2.0",
                    "method": "shutdown",
                    "params": {}
                }
                self._send_notification(shutdown_notification)
                time.sleep(0.5)

                # プロセス終了
                self.process.terminate()
                time.sleep(1)

                if self.process.poll() is None:
                    self.process.kill()

                print(f"✅ {self.name} stopped")

            except Exception as e:
                print(f"❌ Error stopping {self.name}: {e}")

    def is_alive(self) -> bool:
        """プロセスが生きているか確認"""
        return self.process is not None and self.process.poll() is None

    def health_check(self) -> bool:
        """ヘルスチェック"""
        if not self.is_alive():
            return False

        # pingリクエストを送信
        ping_request = {
            "jsonrpc": "2.0",
            "method": "ping",
            "params": {},
            "id": self._get_next_id()
        }

        response = self._send_request(ping_request, timeout=2.0)
        return response is not None


def test_stdio_servers():
    """STDIO MCPサーバーをテスト"""

    servers = {
        "memory": STDIOMCPServer(
            "Memory MCP",
            ["npx", "-y", "@modelcontextprotocol/server-memory"]
        ),
        "sequential": STDIOMCPServer(
            "Sequential Thinking MCP",
            ["npx", "-y", "@modelcontextprotocol/server-sequential-thinking"]
        )
    }

    # サーバー起動
    for name, server in servers.items():
        success = server.start()
        print(f"{name}: {'✅ Started' if success else '❌ Failed'}")

    # 5秒待機
    print("\n⏳ Running for 5 seconds...")
    time.sleep(5)

    # ヘルスチェック
    print("\n📊 Health Check:")
    for name, server in servers.items():
        if server.is_alive():
            health = server.health_check()
            print(f"{name}: {'✅ Healthy' if health else '⚠️ Unhealthy'}")
        else:
            print(f"{name}: ❌ Not running")

    # サーバー停止
    print("\n🔴 Stopping servers...")
    for server in servers.values():
        server.stop()

    print("\n✅ Test completed")


if __name__ == "__main__":
    test_stdio_servers()