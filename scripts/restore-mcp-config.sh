#!/bin/bash
# MCP設定復元スクリプト
# 使用方法: bash scripts/restore-mcp-config.sh [TIMESTAMP]

set -e

# 色付きエコー関数
info() { echo -e "\033[1;34m[INFO]\033[0m $*"; }
success() { echo -e "\033[1;32m[SUCCESS]\033[0m $*"; }
error() { echo -e "\033[1;31m[ERROR]\033[0m $*"; }
warning() { echo -e "\033[1;33m[WARNING]\033[0m $*"; }

BACKUP_DIR=".claude/backups"

# タイムスタンプ引数確認
if [ -z "$1" ]; then
  info "利用可能なバックアップ:"
  ls -lt "$BACKUP_DIR" | grep -E "claude_(desktop|code)_config_[0-9]{8}_[0-9]{6}.json" | head -10
  echo ""
  error "使用方法: $0 <TIMESTAMP>"
  error "例: $0 20251120_123456"
  exit 1
fi

TIMESTAMP="$1"

# バックアップファイル確認
GLOBAL_BACKUP="$BACKUP_DIR/claude_desktop_config_${TIMESTAMP}.json"
PROJECT_BACKUP="$BACKUP_DIR/claude_code_config_${TIMESTAMP}.json"

if [ ! -f "$GLOBAL_BACKUP" ] && [ ! -f "$PROJECT_BACKUP" ]; then
  error "指定されたタイムスタンプのバックアップが見つかりません: $TIMESTAMP"
  exit 1
fi

# 確認プロンプト
warning "以下のファイルを復元します:"
[ -f "$GLOBAL_BACKUP" ] && echo "  - グローバル設定"
[ -f "$PROJECT_BACKUP" ] && echo "  - プロジェクト設定"
echo ""
read -p "復元を続行しますか? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  info "復元をキャンセルしました"
  exit 0
fi

# グローバル設定の復元
if [ -f "$GLOBAL_BACKUP" ]; then
  GLOBAL_CONFIG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
  cp "$GLOBAL_BACKUP" "$GLOBAL_CONFIG"
  success "グローバル設定を復元しました"
fi

# プロジェクト設定の復元
if [ -f "$PROJECT_BACKUP" ]; then
  PROJECT_CONFIG=".claude/claude_code_config.json"
  cp "$PROJECT_BACKUP" "$PROJECT_CONFIG"
  success "プロジェクト設定を復元しました"
fi

info "Claude Desktopを再起動してください:"
echo "  killall Claude && sleep 3 && open -a Claude"

success "✅ 復元が完了しました"
