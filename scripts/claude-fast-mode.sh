#!/bin/bash

# 001-final-hourglass Claude Code Fast Mode
# 権限確認をスキップして高速開発モードを有効化

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║     🚀 001-final-hourglass Claude Code Fast Mode          ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""
echo "⚡ 高速開発モード起動中..."
echo ""

# プロジェクトディレクトリに移動
cd /Users/admin/Documents/AIUELAB/001-final-hourglass

# 環境変数を設定
export CLAUDE_SKIP_ALL_PERMISSIONS=true

# 自動承認モードステータスを確認
if [ -f ~/.claude/auto-mode-status ]; then
    echo "✅ 自動承認モード: 有効"
    echo "  - ~/.claude/auto-mode-status: $(cat ~/.claude/auto-mode-status)"
else
    echo "⚠️  自動承認モードファイルが見つかりません"
    echo "🟢 AUTO-ACCEPT" > ~/.claude/auto-mode-status
    echo "✅ 自動承認モードを有効化しました"
fi

echo "  - 環境変数 CLAUDE_SKIP_ALL_PERMISSIONS=$CLAUDE_SKIP_ALL_PERMISSIONS"
echo ""

# Serena MCPサーバーの状態確認
if pgrep -f "serena-mcp-server.*001-final-hourglass" > /dev/null; then
    echo "✅ Serena MCPサーバー: 稼働中"
else
    echo "🔄 Serena MCPサーバーを起動しています..."
    python3 scripts/start_serena_server.py &
    sleep 2
    echo "✅ Serena MCPサーバー: 起動完了"
fi
echo ""

# Claude Codeを権限スキップモードで起動
echo "📌 権限確認をスキップしてClaude Codeを起動します"
echo ""
echo "⚠️  注意:"
echo "  • このモードではファイル操作の確認がスキップされます"
echo "  • 開発環境でのみ使用してください"
echo "  • 本番環境では通常モードを推奨します"
echo ""

# コマンド実行
claude --dangerously-skip-permissions

echo ""
echo "✅ 高速開発モード終了"
