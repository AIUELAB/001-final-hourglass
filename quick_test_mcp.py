#!/usr/bin/env python3
"""
MCPシステムクイックテスト
修正後の動作確認
"""

import time
import sys
from mcp_management_system import UnifiedMCPManager

def quick_test():
    """クイックテスト実行"""

    print("=" * 60)
    print("MCP管理システム - クイックテスト")
    print("=" * 60)

    manager = UnifiedMCPManager()

    # テスト対象サーバー
    test_servers = [
        ("serena", "SSE", "Serena MCP（プロジェクト管理）"),
        ("codex", "HTTP", "Codex MCP（AI協調）"),
        ("memory", "STDIO", "Memory MCP（長期記憶）"),
        ("sequential-thinking", "STDIO", "Sequential Thinking MCP（順次思考）")
    ]

    results = {}

    for server_id, transport, description in test_servers:
        print(f"\n📌 {description} ({transport})")
        print("-" * 40)

        # 起動
        print(f"  起動中...")
        success = manager.start_server(server_id)
        results[server_id] = {"started": success}

        if success:
            print(f"  ✅ 起動成功")
            time.sleep(2)

            # ヘルスチェック
            health = manager.health_check(server_id)
            results[server_id]["health"] = health
            print(f"  ヘルス: {'✅ Healthy' if health else '⚠️ Check Failed'}")
        else:
            print(f"  ❌ 起動失敗")
            results[server_id]["health"] = False

    # 結果サマリー
    print("\n" + "=" * 60)
    print("📊 テスト結果サマリー")
    print("=" * 60)

    success_count = 0
    for server_id, result in results.items():
        status = "✅" if result["started"] and result["health"] else "⚠️" if result["started"] else "❌"
        print(f"  {status} {server_id}: 起動={result['started']}, ヘルス={result.get('health', False)}")
        if result["started"]:
            success_count += 1

    print(f"\n成功率: {success_count}/{len(test_servers)} ({success_count*100//len(test_servers)}%)")

    # クリーンアップ
    print("\n🧹 クリーンアップ中...")
    manager.stop_all()

    print("\n✅ テスト完了")

    # 成功判定
    if success_count >= 3:  # 4つのうち3つ以上成功でOK
        print("\n🎉 システムは正常に動作しています")
        return 0
    else:
        print("\n⚠️ 一部のサーバーに問題があります")
        return 1

if __name__ == "__main__":
    sys.exit(quick_test())
