#!/usr/bin/env python3
"""
MCP プロファイル切り替えスクリプト

使用方法:
    python scripts/switch_mcp_profile.py <profile_name>
    python scripts/switch_mcp_profile.py --list
    python scripts/switch_mcp_profile.py --current
    python scripts/switch_mcp_profile.py --recommend "検索したい"

Created: 2025-11-21
Phase: 18-C
"""

import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent
PROFILES_FILE = PROJECT_ROOT / "mcp_profiles.json"
CLAUDE_GLOBAL_CONFIG = Path.home() / ".claude.json"
BACKUP_SUFFIX = f".backup_phase18c_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


class MCPProfileManager:
    """MCPプロファイル管理クラス"""

    def __init__(self):
        self.profiles = self.load_profiles()
        self.claude_config = self.load_claude_config()

    def load_profiles(self) -> dict:
        """プロファイル定義を読み込み"""
        if not PROFILES_FILE.exists():
            print(f"❌ プロファイル定義ファイルが見つかりません: {PROFILES_FILE}")
            sys.exit(1)

        with open(PROFILES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_claude_config(self) -> dict:
        """Claude グローバル設定を読み込み"""
        if not CLAUDE_GLOBAL_CONFIG.exists():
            print(f"❌ Claude設定ファイルが見つかりません: {CLAUDE_GLOBAL_CONFIG}")
            sys.exit(1)

        with open(CLAUDE_GLOBAL_CONFIG, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_claude_config(self):
        """Claude グローバル設定を保存"""
        with open(CLAUDE_GLOBAL_CONFIG, "w", encoding="utf-8") as f:
            json.dump(self.claude_config, f, indent=2, ensure_ascii=False)

    def save_profiles(self):
        """プロファイル定義を保存"""
        with open(PROFILES_FILE, "w", encoding="utf-8") as f:
            json.dump(self.profiles, f, indent=2, ensure_ascii=False)

    def backup_claude_config(self):
        """Claude 設定のバックアップ作成"""
        backup_path = Path(str(CLAUDE_GLOBAL_CONFIG) + BACKUP_SUFFIX)
        shutil.copy2(CLAUDE_GLOBAL_CONFIG, backup_path)
        print(f"✅ バックアップ作成: {backup_path}")
        return backup_path

    def list_profiles(self):
        """利用可能なプロファイル一覧を表示"""
        print("\n" + "=" * 80)
        print("📋 利用可能なMCPプロファイル")
        print("=" * 80 + "\n")

        active_profile = self.profiles.get("active_profile", "minimal")

        for profile_name, profile_data in self.profiles["profiles"].items():
            is_active = " (✅ 現在有効)" if profile_name == active_profile else ""
            print(f"🔹 {profile_name}{is_active}")
            print(f"   説明: {profile_data['description']}")
            print(f"   用途: {profile_data['use_case']}")
            print(f"   コンテキスト消費: {profile_data['estimated_context_usage']}")
            print(f"   Free space予測: {profile_data['estimated_free_space']}")
            print()

    def get_current_profile(self) -> str:
        """現在のアクティブプロファイルを取得"""
        return self.profiles.get("active_profile", "minimal")

    def recommend_profile(self, user_input: str) -> Optional[str]:
        """ユーザー入力から推奨プロファイルを選択"""
        auto_rules = self.profiles.get("auto_switch_rules", [])

        # 優先度順にソート
        sorted_rules = sorted(auto_rules, key=lambda x: x.get("priority", 0), reverse=True)

        for rule in sorted_rules:
            keywords = rule.get("keywords", [])
            if any(kw in user_input for kw in keywords):
                return rule["profile"]

        return "minimal"

    def switch_profile(self, profile_name: str):
        """指定プロファイルに切り替え"""
        # プロファイルの検証
        if profile_name not in self.profiles["profiles"]:
            print(f"❌ プロファイル '{profile_name}' が見つかりません")
            print(f"\n利用可能なプロファイル: {', '.join(self.profiles['profiles'].keys())}")
            sys.exit(1)

        profile = self.profiles["profiles"][profile_name]

        print("\n" + "=" * 80)
        print(f"🔄 プロファイル '{profile_name}' に切り替え中...")
        print("=" * 80 + "\n")

        print(f"📝 説明: {profile['description']}")
        print(f"🎯 用途: {profile['use_case']}")
        print(f"📊 推定コンテキスト: {profile['estimated_context_usage']}")
        print(f"💾 推定Free space: {profile['estimated_free_space']}")
        print()

        # バックアップ作成
        backup_path = self.backup_claude_config()

        # MCPサーバー設定を更新
        print("🔧 MCPサーバー設定を更新中...")
        self.update_mcp_servers(profile["mcps"])

        # アクティブプロファイルを更新
        self.profiles["active_profile"] = profile_name
        self.save_profiles()

        # Claude設定を保存
        self.save_claude_config()

        print("\n" + "=" * 80)
        print("✅ プロファイル切り替え完了！")
        print("=" * 80 + "\n")

        print("⚠️  重要: 以下の手順でClaude Codeを再起動してください:")
        print()
        print("1. Claude Code/Cursorを完全終了（⌘Q）")
        print("2. 5秒待つ")
        print("3. Claude Code/Cursorを再起動")
        print()
        print("再起動後、以下のコマンドで効果を確認できます:")
        print("  /context")
        print()
        print(f"💡 元に戻す場合: cp {backup_path} {CLAUDE_GLOBAL_CONFIG}")
        print()

    def update_mcp_servers(self, mcp_config: Dict[str, bool]):
        """Claude グローバル設定のMCPサーバーを更新"""
        # 既存のmcpServersを取得
        if "mcpServers" not in self.claude_config:
            self.claude_config["mcpServers"] = {}

        mcp_servers = self.claude_config["mcpServers"]

        # 各MCPサーバーの有効/無効を設定
        for mcp_name, is_enabled in mcp_config.items():
            if is_enabled:
                # 有効化: サーバー定義を追加（既に存在する場合は保持）
                if mcp_name not in mcp_servers:
                    # デフォルト定義を追加
                    mcp_servers[mcp_name] = self.get_mcp_default_config(mcp_name)
                print(f"  ✅ {mcp_name}: 有効化")
            else:
                # 無効化: サーバー定義を削除
                if mcp_name in mcp_servers:
                    del mcp_servers[mcp_name]
                    print(f"  ❌ {mcp_name}: 無効化")

    def get_mcp_default_config(self, mcp_name: str) -> dict:
        """MCPサーバーのデフォルト設定を取得"""
        defaults = {
            "fetch": {"type": "stdio", "command": "uvx", "args": ["mcp-server-fetch"], "env": {}},
            "brave-search": {
                "type": "stdio",
                "command": "npx",
                "args": ["-y", "brave-search-mcp"],
                "env": {"BRAVE_API_KEY": os.getenv("BRAVE_API_KEY", "")},
            },
            "firecrawl": {
                "type": "stdio",
                "command": "npx",
                "args": ["-y", "firecrawl-mcp"],
                "env": {
                    "FIRECRAWL_API_KEY": os.getenv("FIRECRAWL_API_KEY", ""),
                    "FIRECRAWL_RETRY_MAX_ATTEMPTS": "5",
                    "FIRECRAWL_RETRY_INITIAL_DELAY": "2000",
                    "FIRECRAWL_RETRY_MAX_DELAY": "30000",
                    "FIRECRAWL_RETRY_BACKOFF_FACTOR": "3",
                    "FIRECRAWL_CREDIT_WARNING_THRESHOLD": "2000",
                    "FIRECRAWL_CREDIT_CRITICAL_THRESHOLD": "500",
                },
            },
            "playwright": {"type": "stdio", "command": "npx", "args": ["@playwright/mcp@latest"], "env": {}},
            "context7": {"type": "http", "url": "https://mcp.context7.com/mcp"},
        }

        # ~/.claude.jsonから既存設定を取得（存在する場合）
        existing_config = self.claude_config.get("mcpServers", {}).get(mcp_name)
        if existing_config:
            return existing_config

        return defaults.get(mcp_name, {})


def main():
    """メイン処理"""
    manager = MCPProfileManager()

    # コマンドライン引数の処理
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python scripts/switch_mcp_profile.py <profile_name>")
        print("  python scripts/switch_mcp_profile.py --list")
        print("  python scripts/switch_mcp_profile.py --current")
        print('  python scripts/switch_mcp_profile.py --recommend "タスク内容"')
        sys.exit(1)

    command = sys.argv[1]

    if command == "--list":
        manager.list_profiles()
    elif command == "--current":
        current = manager.get_current_profile()
        profile = manager.profiles["profiles"][current]
        print(f"\n現在のプロファイル: {current}")
        print(f"説明: {profile['description']}")
        print(f"コンテキスト消費: {profile['estimated_context_usage']}")
        print()
    elif command == "--recommend":
        if len(sys.argv) < 3:
            print("❌ タスク内容を指定してください")
            sys.exit(1)
        user_input = " ".join(sys.argv[2:])
        recommended = manager.recommend_profile(user_input)
        profile = manager.profiles["profiles"][recommended]
        print(f"\n推奨プロファイル: {recommended}")
        print(f"理由: {profile['description']}")
        print("\n実行する場合:")
        print(f"  python scripts/switch_mcp_profile.py {recommended}")
        print()
    else:
        # プロファイル切り替え
        manager.switch_profile(command)


if __name__ == "__main__":
    main()
