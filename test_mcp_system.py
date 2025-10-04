#!/usr/bin/env python3
"""
MCPシステムテスト
各サーバーを順番に起動してテスト
"""

import time
from mcp_management_system import UnifiedMCPManager

def test_servers():
    """各サーバーをテスト"""

    manager = UnifiedMCPManager()

    # Serenaをテスト（SSE）
    print("\n=== Testing Serena (SSE) ===")
    success = manager.start_server("serena")
    print(f"Serena start: {'✅' if success else '❌'}")
    time.sleep(3)

    # Codexをテスト（HTTP）
    print("\n=== Testing Codex (HTTP) ===")
    success = manager.start_server("codex")
    print(f"Codex start: {'✅' if success else '❌'}")
    time.sleep(3)

    # Memoryをテスト（STDIO）
    print("\n=== Testing Memory (STDIO) ===")
    success = manager.start_server("memory")
    print(f"Memory start: {'✅' if success else '❌'}")
    time.sleep(3)

    # Sequential Thinkingをテスト（STDIO）
    print("\n=== Testing Sequential-thinking (STDIO) ===")
    success = manager.start_server("sequential-thinking")
    print(f"Sequential-thinking start: {'✅' if success else '❌'}")
    time.sleep(3)

    # Smitheryをテスト（STDIO）
    print("\n=== Testing Smithery (STDIO) ===")
    success = manager.start_server("smithery")
    print(f"Smithery start: {'✅' if success else '❌'}")
    time.sleep(3)

    # ステータス確認
    print("\n=== Current Status ===")
    status = manager.status_all()
    for name, state in status.items():
        print(f"  {name}: {state}")

    # ヘルスチェック
    print("\n=== Health Check ===")
    for name in manager.servers.keys():
        health = manager.health_check(name)
        print(f"  {name}: {'✅ Healthy' if health else '❌ Unhealthy'}")

    # 10秒待機
    print("\n⏳ Running for 10 seconds...")
    time.sleep(10)

    # 停止
    print("\n=== Stopping All Servers ===")
    manager.stop_all()

    print("\n✅ Test completed")

if __name__ == "__main__":
    test_servers()