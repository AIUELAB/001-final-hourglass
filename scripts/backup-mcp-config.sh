#!/bin/bash
# MCP設定バックアップスクリプト
# 使用方法: bash scripts/backup-mcp-config.sh

set -e

# 色付きエコー関数
info() { echo -e "\033[1;34m[INFO]\033[0m $*"; }
success() { echo -e "\033[1;32m[SUCCESS]\033[0m $*"; }
error() { echo -e "\033[1;31m[ERROR]\033[0m $*"; }

# バックアップディレクトリ
BACKUP_DIR=".claude/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# ディレクトリ作成
mkdir -p "$BACKUP_DIR"

info "MCP設定のバックアップを開始します..."

# グローバル設定のバックアップ
GLOBAL_CONFIG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
if [ -f "$GLOBAL_CONFIG" ]; then
  cp "$GLOBAL_CONFIG" "$BACKUP_DIR/claude_desktop_config_${TIMESTAMP}.json"
  success "グローバル設定をバックアップしました"
else
  error "グローバル設定ファイルが見つかりません: $GLOBAL_CONFIG"
fi

# プロジェクト固有設定のバックアップ
PROJECT_CONFIG=".claude/claude_code_config.json"
if [ -f "$PROJECT_CONFIG" ]; then
  cp "$PROJECT_CONFIG" "$BACKUP_DIR/claude_code_config_${TIMESTAMP}.json"
  success "プロジェクト設定をバックアップしました"
else
  error "プロジェクト設定ファイルが見つかりません: $PROJECT_CONFIG"
fi

# LaunchAgent設定のバックアップ
LAUNCH_AGENT="$HOME/Library/LaunchAgents/com.anthropic.claude.env.plist"
if [ -f "$LAUNCH_AGENT" ]; then
  cp "$LAUNCH_AGENT" "$BACKUP_DIR/com.anthropic.claude.env_${TIMESTAMP}.plist"
  success "LaunchAgent設定をバックアップしました"
fi

# バックアップ一覧表示
info "バックアップファイル一覧:"
ls -lh "$BACKUP_DIR" | grep "$TIMESTAMP"

# 古いバックアップの削除（30日以上前）
find "$BACKUP_DIR" -name "*.json" -type f -mtime +30 -delete 2>/dev/null || true
find "$BACKUP_DIR" -name "*.plist" -type f -mtime +30 -delete 2>/dev/null || true

success "✅ バックアップが完了しました: $BACKUP_DIR"
