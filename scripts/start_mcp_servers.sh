#!/bin/bash

# MCP Servers 最適化スタートアップスクリプト v2.0
# 2025年10月1日更新 - 安全性と効率性を向上

set -e  # エラー時に停止

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ログ関数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 起動時間を記録
START_TIME=$(date +%s)

log_info "🧹 MCP管理システム起動準備開始..."

# 1. 既存プロセスの安全なクリーンアップ
log_info "既存プロセスの確認と終了..."
CLEANUP_COUNT=0

# プロセス確認とクリーンアップ
for process in "mcp_management_system.py" "serena-mcp-server" "codex_mcp_server" "stability_test.py" "monitor_mcp_servers.sh"; do
    if pgrep -f "$process" > /dev/null 2>&1; then
        log_warning "プロセス $process を終了中..."
        pkill -f "$process" 2>/dev/null && CLEANUP_COUNT=$((CLEANUP_COUNT + 1))
    fi
done

# NPXプロセスの特別処理
if pgrep -f "npx.*@modelcontextprotocol" > /dev/null 2>&1; then
    log_warning "NPX MCPサーバーを終了中..."
    pkill -f "npx.*@modelcontextprotocol" 2>/dev/null && CLEANUP_COUNT=$((CLEANUP_COUNT + 1))
fi

if [ $CLEANUP_COUNT -gt 0 ]; then
    log_warning "プロセス$CLEANUP_COUNT個を終了しました"
    sleep 3  # プロセス終了待機
else
    log_success "クリーンアップ不要 - プロセス競合なし"
fi

# 2. ポート解放の最適化
log_info "ポート状態の確認と解放..."
PORT_CLEANUP=0

# Port 8000 (Serena)
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    log_warning "Port 8000を解放中..."
    lsof -t -i:8000 2>/dev/null | xargs kill -9 2>/dev/null && PORT_CLEANUP=$((PORT_CLEANUP + 1))
fi

# Port 8765 (Codex)
if lsof -Pi :8765 -sTCP:LISTEN -t >/dev/null 2>&1; then
    log_warning "Port 8765を解放中..."
    lsof -t -i:8765 2>/dev/null | xargs kill -9 2>/dev/null && PORT_CLEANUP=$((PORT_CLEANUP + 1))
fi

if [ $PORT_CLEANUP -gt 0 ]; then
    log_warning "ポート$PORT_CLEANUP個を解放しました"
    sleep 2
else
    log_success "ポート競合なし"
fi

# 3. プロジェクトディレクトリの確認
PROJECT_DIR="$(dirname "$0")/.."
if ! cd "$PROJECT_DIR"; then
    log_error "プロジェクトディレクトリに移動できません: $PROJECT_DIR"
    exit 1
fi
log_success "プロジェクトディレクトリ: $(pwd)"

# 4. 環境変数の読み込み
if [ -f .env ]; then
    # 安全な環境変数読み込み（コメント行と空行を除外）
    set -a  # 環境変数の自動エクスポート
    source <(grep -v '^#\|^$' .env)
    set +a
    log_success "環境変数を読み込みました"
else
    log_warning ".envファイルが見つかりません"
fi

# 5. Python環境の確認
if ! command -v python3 &> /dev/null; then
    log_error "Python3が見つかりません"
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
log_success "Python環境: $PYTHON_VERSION"

# 6. 依存関係の確認
if [ -f requirements.txt ]; then
    log_info "依存関係を確認中..."
    # 主要パッケージの存在確認
    python3 -c "import requests, json, subprocess" 2>/dev/null || {
        log_error "必要なPythonパッケージが不足しています"
        log_info "pip install -r requirements.txt を実行してください"
        exit 1
    }
    log_success "依存関係OK"
fi

# 7. 単一MCPマネージャーの起動
log_info ""
log_info "🚀 最適化MCPマネージャーを起動します..."

# 終了時のクリーンアップ（シグナルハンドリング強化）
cleanup() {
    echo ""
    log_warning "🛑 シャットダウンシーケンス開始..."

    # graceful shutdown
    pkill -TERM -f "mcp_management_system.py" 2>/dev/null
    sleep 5

    # force shutdown if needed
    if pgrep -f "mcp_management_system.py" > /dev/null 2>&1; then
        log_warning "強制終了を実行..."
        pkill -KILL -f "mcp_management_system.py" 2>/dev/null
    fi

    log_success "クリーンアップ完了"
    exit 0
}

trap cleanup INT TERM EXIT

# MCPマネージャー起動
if ! python3 mcp_management_system.py start-all; then
    log_error "MCPマネージャーの起動に失敗しました"
    exit 1
fi

# 起動時間の表示
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
log_success "起動完了 (所要時間: ${DURATION}秒)"
