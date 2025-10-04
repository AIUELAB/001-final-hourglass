#!/bin/bash
# launchdセットアップスクリプト
# Git自動コミットを5分間隔で実行

set -e

PLIST_SOURCE="/Users/admin/Documents/AIUELAB/001-final-hourglass/scripts/com.session.autocommit.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/com.session.autocommit.plist"

echo "🔧 Setting up auto-commit with launchd..."

# LaunchAgentsディレクトリを作成
mkdir -p "$HOME/Library/LaunchAgents"

# plistファイルをコピー
cp "$PLIST_SOURCE" "$PLIST_DEST"
echo "✅ Copied plist to $PLIST_DEST"

# 既存のジョブをアンロード（存在する場合）
launchctl unload "$PLIST_DEST" 2>/dev/null || true

# 新しいジョブをロード
launchctl load "$PLIST_DEST"
echo "✅ Loaded launchd job"

# 状態確認
if launchctl list | grep -q "com.session.autocommit"; then
    echo "✅ Auto-commit service is running"
    echo ""
    echo "📋 Job details:"
    launchctl list | grep "com.session.autocommit"
else
    echo "⚠️ Auto-commit service failed to start"
    exit 1
fi

echo ""
echo "🎯 Auto-commit setup complete!"
echo "   - Interval: 5 minutes"
echo "   - Logs: .session/auto_commit*.log"
echo ""
echo "Commands:"
echo "  Start:   launchctl load $PLIST_DEST"
echo "  Stop:    launchctl unload $PLIST_DEST"
echo "  Status:  launchctl list | grep com.session.autocommit"
