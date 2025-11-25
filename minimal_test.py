#!/usr/bin/env python3
"""
最小限のMCPサーバーテスト
各サーバーを個別にテスト
"""

import subprocess
import time
import sys

def test_memory_server():
    """Memory MCPサーバーの直接テスト"""
    print("\n=== Memory MCP Direct Test ===")

    from stdio_mcp_handler import STDIOMCPServer

    server = STDIOMCPServer(
        "Memory MCP",
        ["npx", "-y", "@modelcontextprotocol/server-memory"]
    )

    if server.start():
        print("✅ Memory MCP started successfully")
        time.sleep(2)

        if server.health_check():
            print("✅ Memory MCP is healthy")
        else:
            print("❌ Memory MCP health check failed")

        server.stop()
        print("✅ Memory MCP stopped")
        return True
    else:
        print("❌ Memory MCP failed to start")
        return False

def test_sequential_server():
    """Sequential Thinking MCPサーバーの直接テスト"""
    print("\n=== Sequential Thinking MCP Direct Test ===")

    from stdio_mcp_handler import STDIOMCPServer

    server = STDIOMCPServer(
        "Sequential Thinking MCP",
        ["npx", "-y", "@modelcontextprotocol/server-sequential-thinking"]
    )

    if server.start():
        print("✅ Sequential Thinking MCP started successfully")
        time.sleep(2)

        if server.health_check():
            print("✅ Sequential Thinking MCP is healthy")
        else:
            print("❌ Sequential Thinking MCP health check failed")

        server.stop()
        print("✅ Sequential Thinking MCP stopped")
        return True
    else:
        print("❌ Sequential Thinking MCP failed to start")
        return False

def test_codex_server():
    """Codex MCPサーバーの直接テスト"""
    print("\n=== Codex MCP Direct Test ===")

    try:
        # ポート確認
        result = subprocess.run(["lsof", "-i", ":8765"], capture_output=True, text=True)
        if result.returncode == 0:
            print("Port 8765 is already in use, killing existing process...")
            subprocess.run(["lsof", "-t", "-i", ":8765"], capture_output=True)
            time.sleep(1)

        # Codexを起動
        process = subprocess.Popen(
            ["python3", "codex_mcp_server.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        time.sleep(3)

        if process.poll() is None:
            print("✅ Codex MCP started successfully")

            # ヘルスチェック
            import requests
            try:
                response = requests.get("http://localhost:8765/health", timeout=2)
                if response.status_code == 200:
                    print("✅ Codex MCP is healthy")
                else:
                    print("❌ Codex MCP health check returned", response.status_code)
            except Exception as e:
                print("❌ Codex MCP health check failed:", e)

            # 停止
            process.terminate()
            time.sleep(1)
            if process.poll() is None:
                process.kill()
            print("✅ Codex MCP stopped")
            return True
        else:
            print("❌ Codex MCP failed to start")
            return False

    except Exception as e:
        print(f"❌ Codex test error: {e}")
        return False

def main():
    """メインテスト実行"""
    print("=" * 60)
    print("MCP最小限動作テスト")
    print("=" * 60)

    results = {
        "memory": test_memory_server(),
        "sequential": test_sequential_server(),
        "codex": test_codex_server()
    }

    print("\n" + "=" * 60)
    print("テスト結果サマリー")
    print("=" * 60)

    for name, success in results.items():
        print(f"  {name}: {'✅ PASS' if success else '❌ FAIL'}")

    success_count = sum(1 for v in results.values() if v)
    print(f"\n成功率: {success_count}/{len(results)} ({success_count*100//len(results)}%)")

    if success_count >= 2:
        print("\n🎉 基本的なMCPサーバーは正常に動作しています")
        return 0
    else:
        print("\n❌ MCPサーバーに問題があります")
        return 1

if __name__ == "__main__":
    sys.exit(main())
