#!/bin/bash
# Git自動コミットスクリプト
# セッション情報を定期的に（5分間隔推奨）自動コミット

set -e

PROJECT_ROOT="/Users/admin/Documents/AIUELAB/001-final-hourglass"
SESSION_DIR="$PROJECT_ROOT/.session"
COMMIT_LOG="$SESSION_DIR/auto_commit.log"

# 現在時刻
TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")

# ログ関数
log() {
    echo "[$TIMESTAMP] $1" >> "$COMMIT_LOG"
    echo "[$TIMESTAMP] $1"
}

# プロジェクトディレクトリに移動
cd "$PROJECT_ROOT" || exit 1

# Gitリポジトリチェック
if [ ! -d ".git" ]; then
    log "❌ Not a git repository"
    exit 1
fi

# 変更があるかチェック
if git diff --quiet .session/ && git diff --cached --quiet .session/; then
    log "ℹ️ No changes to commit in .session/"
    exit 0
fi

# .session/配下のファイルをステージング
git add .session/STATUS.md .session/SESSION_LOG.md .session/serena_memory.json 2>/dev/null || true

# スナップショットは最新のみコミット
if [ -L .session/snapshots/latest.md ]; then
    LATEST_SNAPSHOT=$(readlink .session/snapshots/latest.md)
    git add ".session/snapshots/$LATEST_SNAPSHOT" 2>/dev/null || true
fi

# リカバリーポイントをコミット
git add .session/recovery/*.json 2>/dev/null || true

# .gitignoreに従って変更をチェック
STAGED_FILES=$(git diff --cached --name-only)

if [ -z "$STAGED_FILES" ]; then
    log "ℹ️ No files staged for commit"
    exit 0
fi

# コミットメッセージ生成
COMMIT_MSG="🔄 Auto-save session state @ $TIMESTAMP

Files updated:
$(echo "$STAGED_FILES" | sed 's/^/- /')

🤖 Auto-commit by session recorder
Session ID: $(grep -o 'session_[0-9_]*' .session/STATUS.md | head -1 || echo 'unknown')"

# コミット実行
if git commit -m "$COMMIT_MSG" > /dev/null 2>&1; then
    log "✅ Session state committed successfully"
    log "   Files: $(echo "$STAGED_FILES" | wc -l | tr -d ' ')"
else
    log "⚠️ Commit failed or nothing to commit"
fi

# 古いログをクリーンアップ（100行以上で古い50行を削除）
if [ -f "$COMMIT_LOG" ]; then
    LINE_COUNT=$(wc -l < "$COMMIT_LOG")
    if [ "$LINE_COUNT" -gt 100 ]; then
        tail -n 50 "$COMMIT_LOG" > "$COMMIT_LOG.tmp"
        mv "$COMMIT_LOG.tmp" "$COMMIT_LOG"
        log "🧹 Cleaned up old log entries"
    fi
fi

log "✅ Auto-commit completed"
