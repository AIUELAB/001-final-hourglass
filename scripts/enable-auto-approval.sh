#!/bin/bash

# 自動承認モードを有効化するスクリプト

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║     ⚡ Claude Code 自動承認モード設定                     ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# ~/.claudeディレクトリの作成
if [ ! -d ~/.claude ]; then
    mkdir -p ~/.claude
    echo "📁 ~/.claudeディレクトリを作成しました"
fi

# 自動承認モードを有効化
echo "🟢 AUTO-ACCEPT" > ~/.claude/auto-mode-status
echo "✅ 自動承認モードを有効化しました"

# 環境変数を設定（現在のシェルセッション用）
export CLAUDE_SKIP_ALL_PERMISSIONS=true
echo "✅ 環境変数 CLAUDE_SKIP_ALL_PERMISSIONS=true を設定しました"

# .bashrcまたは.zshrcに永続的に追加
SHELL_CONFIG=""
if [ -n "$ZSH_VERSION" ]; then
    SHELL_CONFIG="$HOME/.zshrc"
elif [ -n "$BASH_VERSION" ]; then
    SHELL_CONFIG="$HOME/.bashrc"
fi

if [ -n "$SHELL_CONFIG" ]; then
    # 既に設定があるか確認
    if ! grep -q "CLAUDE_SKIP_ALL_PERMISSIONS" "$SHELL_CONFIG"; then
        echo "" >> "$SHELL_CONFIG"
        echo "# Claude Code 自動承認モード" >> "$SHELL_CONFIG"
        echo "export CLAUDE_SKIP_ALL_PERMISSIONS=true" >> "$SHELL_CONFIG"
        echo "✅ $SHELL_CONFIG に環境変数を追加しました"
    else
        echo "ℹ️  環境変数は既に設定されています"
    fi
fi

# テスト音を再生
echo ""
echo "🔊 承認音のテスト..."
./scripts/play-approval-sound.sh
echo "✅ 承認音が再生されました"

echo ""
echo "設定状態:"
echo "  ✅ 自動承認モード: 有効"
echo "  - ~/.claude/auto-mode-status: $(cat ~/.claude/auto-mode-status)"
echo "  - 環境変数 CLAUDE_SKIP_ALL_PERMISSIONS=$CLAUDE_SKIP_ALL_PERMISSIONS"
echo ""
echo "  ⚡ 高速モード: 利用可能"
echo "  - 実行: ./scripts/claude-fast-mode.sh"
echo ""
echo "  🔊 承認音: 有効"
echo "  - 自動承認時に音が鳴ります"
echo ""
echo "✨ 設定が完了しました！"
echo "次回のシェル起動時から環境変数が有効になります。"
echo ""
echo "今すぐ使用する場合:"
echo "  source $SHELL_CONFIG"
