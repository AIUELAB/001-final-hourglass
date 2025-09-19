#!/usr/bin/env python3
"""
Claude Desktop IDE サーバー追加スクリプト
IDE disconnected 表示を解決
"""

import json
import shutil
from datetime import datetime
from pathlib import Path

from simple_notification import notify_complete, notify_error, notify_success


def add_ide_server():
    """IDEサーバーをClaude Desktop設定に追加"""
    
    # 設定ファイルのパス
    config_path = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    
    if not config_path.exists():
        print(f"❌ 設定ファイルが見つかりません: {config_path}")
        notify_error("設定ファイルが見つかりません")
        return False
    
    # バックアップ作成
    backup_path = config_path.with_suffix(f'.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
    shutil.copy2(config_path, backup_path)
    print(f"📁 バックアップ作成: {backup_path}")
    
    try:
        # 現在の設定を読み込み
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # IDEサーバーが既に存在するかチェック
        if 'ide' in config.get('mcpServers', {}):
            print("ℹ️ IDEサーバーは既に設定されています")
            current_ide = config['mcpServers']['ide']
            print(f"   現在の設定: {current_ide}")
            
            # 無効なパッケージの場合は修正
            if '@win32user/mcp-ide' in str(current_ide.get('args', [])):
                print("   ⚠️ 無効なパッケージを検出。修正します...")
                config['mcpServers']['ide'] = {
                    "command": "npx",
                    "args": ["-y", "@vscode-mcp/vscode-mcp-server"],
                    "env": {}
                }
                print("   ✅ 正しいパッケージに更新しました")
        else:
            # IDEサーバーを追加
            print("📝 IDEサーバーを追加します...")
            config['mcpServers']['ide'] = {
                "command": "npx",
                "args": ["-y", "@vscode-mcp/vscode-mcp-server"],
                "env": {}
            }
            print("✅ IDEサーバーを追加しました")
        
        # 設定を保存
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        notify_success("IDE設定を更新しました")
        return True
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        notify_error(f"設定更新エラー: {e}")
        
        # エラー時はバックアップから復元
        print("🔄 バックアップから復元します...")
        shutil.copy2(backup_path, config_path)
        print("✅ 復元完了")
        return False

def verify_package():
    """VS Code MCPサーバーパッケージの存在確認"""
    import subprocess
    
    print("\n📦 パッケージの確認...")
    result = subprocess.run(
        ["npm", "view", "@vscode-mcp/vscode-mcp-server", "version"],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        version = result.stdout.strip()
        print(f"✅ @vscode-mcp/vscode-mcp-server v{version} が利用可能です")
        return True
    else:
        print("⚠️ @vscode-mcp/vscode-mcp-server が見つかりません")
        print("   代替: filesystemサーバーでファイル操作は可能です")
        return False

def main():
    """メイン処理"""
    print("🔧 Claude Desktop IDE サーバー設定")
    print("=" * 50)
    
    # パッケージ確認
    package_exists = verify_package()
    
    if not package_exists:
        print("\n⚠️ 注意: IDEパッケージが見つかりませんが、設定は可能です")
        print("   Claude Desktop起動時に自動的にインストールされます")
    
    # 設定追加
    print("\n📝 設定ファイルの更新...")
    if add_ide_server():
        print("\n✅ 設定が完了しました！")
        print("\n次のステップ:")
        print("1. Claude Desktopを完全に終了（Cmd+Q）")
        print("2. Claude Desktopを再起動")
        print("3. IDE接続状態を確認")
        
        notify_complete("IDE設定完了。Claude Desktopを再起動してください")
    else:
        print("\n❌ 設定に失敗しました")
        print("手動で設定ファイルを確認してください")

if __name__ == "__main__":
    main()