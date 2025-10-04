#!/bin/bash

# MCP Manager サービスインストールスクリプト
# macOSとLinuxの両方に対応

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🔧 MCP Manager Service Installer"
echo "================================"

# OS検出
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "📱 macOS を検出しました"
    OS="macos"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "🐧 Linux を検出しました"
    OS="linux"
else
    echo "❌ サポートされていないOS: $OSTYPE"
    exit 1
fi

# macOS (launchd) セットアップ
if [ "$OS" == "macos" ]; then
    echo ""
    echo "📝 launchd サービスを設定中..."

    # ログディレクトリ作成
    mkdir -p ~/Library/Logs/MCP

    # plistファイルをコピー
    cp "$SCRIPT_DIR/com.mcp.manager.plist" ~/Library/LaunchAgents/

    # 既存のサービスをアンロード（エラーは無視）
    launchctl unload ~/Library/LaunchAgents/com.mcp.manager.plist 2>/dev/null || true

    # サービスをロード
    launchctl load ~/Library/LaunchAgents/com.mcp.manager.plist

    echo "✅ launchdサービスを登録しました"
    echo ""
    echo "📋 サービス管理コマンド:"
    echo "  起動: launchctl start com.mcp.manager"
    echo "  停止: launchctl stop com.mcp.manager"
    echo "  状態: launchctl list | grep mcp.manager"
    echo "  ログ: tail -f ~/Library/Logs/MCP/mcp-manager.log"
fi

# Linux (systemd) セットアップ
if [ "$OS" == "linux" ]; then
    echo ""
    echo "📝 systemd サービスを設定中..."

    # systemdサービスファイルをコピー
    sudo cp "$SCRIPT_DIR/mcp-manager.service" /etc/systemd/system/

    # パスを現在のユーザーと環境に合わせて調整
    sudo sed -i "s|User=admin|User=$USER|g" /etc/systemd/system/mcp-manager.service
    sudo sed -i "s|/Users/admin|$HOME|g" /etc/systemd/system/mcp-manager.service

    # systemdをリロード
    sudo systemctl daemon-reload

    # サービスを有効化
    sudo systemctl enable mcp-manager.service

    # サービスを開始
    sudo systemctl start mcp-manager.service

    echo "✅ systemdサービスを登録しました"
    echo ""
    echo "📋 サービス管理コマンド:"
    echo "  起動: sudo systemctl start mcp-manager"
    echo "  停止: sudo systemctl stop mcp-manager"
    echo "  再起動: sudo systemctl restart mcp-manager"
    echo "  状態: sudo systemctl status mcp-manager"
    echo "  ログ: sudo journalctl -u mcp-manager -f"
fi

echo ""
echo "🎉 インストール完了!"
echo ""
echo "🔍 現在のサービス状態:"

if [ "$OS" == "macos" ]; then
    launchctl list | grep mcp.manager || echo "サービスが見つかりません"
else
    sudo systemctl status mcp-manager --no-pager || true
fi

echo ""
echo "📚 詳細なドキュメントは MCP_OPERATIONS_MANUAL.md を参照してください"