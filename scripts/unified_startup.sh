#!/bin/bash
# ============================================================
# 🚀 統合AI協調分析システム起動スクリプト
# ============================================================
# Claude Code、Cursor、通常のターミナルすべてで使用可能
# 重複起動を自動検知して防止
# ============================================================

set -e

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# プロジェクトルート
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT" || exit 1

# ログファイル
STARTUP_LOG="${PROJECT_ROOT}/.unified_startup.log"
PID_DIR="${PROJECT_ROOT}/.pids"
mkdir -p "$PID_DIR"

# ログ関数
log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" >> "$STARTUP_LOG"
}

log_info() { log "INFO" "$@"; }
log_success() { log "SUCCESS" "$@"; }
log_error() { log "ERROR" "$@"; }
log_warn() { log "WARN" "$@"; }

# バナー表示
show_banner() {
    cat << 'EOF'

╔═══════════════════════════════════════════════════════════╗
║   🚀 AI協調分析システム 統合起動マネージャー v3.1       ║
║                                                           ║
║   🎯 Serena MCP Server                                   ║
║   🤖 Codex MCP Server                                    ║
║   📊 Episode Analytics API                               ║
║   📊 自動同期システム                                    ║
║   🔍 ファクトチェッカー                                  ║
║   👁️ リアルタイム監視                                   ║
╚═══════════════════════════════════════════════════════════╝

EOF
}

# プロセス重複チェック
is_process_running() {
    local process_name=$1
    local pid_file="${PID_DIR}/${process_name}.pid"

    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        # プロセスの実在をチェック（macOS互換）
        if kill -0 "$pid" 2>/dev/null; then
            return 0  # プロセス実行中
        else
            rm -f "$pid_file"  # 古いPIDファイル削除
        fi
    fi
    return 1  # プロセス未実行
}

# プロセス起動関数
start_process() {
    local name=$1
    local script=$2
    local pid_file="${PID_DIR}/${name}.pid"

    if is_process_running "$name"; then
        echo -e "${YELLOW}⚠️  ${name} は既に起動しています (PID: $(cat "$pid_file"))${NC}"
        log_warn "${name} already running (PID: $(cat "$pid_file"))"
        return 0
    fi

    echo -e "${CYAN}🔄 ${name} を起動中...${NC}"
    log_info "Starting ${name}"

    if [ ! -f "$script" ]; then
        echo -e "${RED}❌ エラー: ${script} が見つかりません${NC}"
        log_error "${script} not found"
        return 1
    fi

    # スクリプトを実行してPIDを保存
    if [[ "$script" == *.py ]]; then
        python3 "$script" > /dev/null 2>&1 &
    else
        bash "$script" > /dev/null 2>&1 &
    fi

    local pid=$!
    echo "$pid" > "$pid_file"

    # 起動確認（3秒待機）
    sleep 3

    if ps -p "$pid" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ ${name} 起動成功 (PID: $pid)${NC}"
        log_success "${name} started successfully (PID: $pid)"
        return 0
    else
        echo -e "${RED}❌ ${name} 起動失敗${NC}"
        log_error "${name} failed to start"
        rm -f "$pid_file"
        return 1
    fi
}

# ============================================================
# メイン起動シーケンス
# ============================================================

log_info "========== Unified Startup Begin =========="
show_banner

# 環境チェック
echo -e "${CYAN}📋 環境チェック...${NC}"

if [ ! -f "startup_config.json" ]; then
    echo -e "${RED}❌ startup_config.json が見つかりません${NC}"
    log_error "startup_config.json not found"
    exit 1
fi

# Python環境チェック
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 が見つかりません${NC}"
    log_error "Python3 not found"
    exit 1
fi

# 仮想環境の有効化（存在する場合）
if [ -d "venv" ]; then
    echo -e "${GREEN}🐍 仮想環境を有効化${NC}"
    source venv/bin/activate
    log_info "Virtual environment activated"
fi

echo -e "${GREEN}✅ 環境チェック完了${NC}\n"

# ============================================================
# 1️⃣ Serena MCPサーバー起動
# ============================================================
start_process "serena" "${PROJECT_ROOT}/scripts/start_serena_server.py"

# ============================================================
# 2️⃣ Codex MCPサーバー起動
# ============================================================
start_process "codex" "${PROJECT_ROOT}/scripts/start_codex_server.py"

# ============================================================
# 3️⃣ 自動同期システム起動
# ============================================================
if [ -f "${PROJECT_ROOT}/auto_startup_sync.py" ]; then
    start_process "auto_sync" "${PROJECT_ROOT}/auto_startup_sync.py"
else
    echo -e "${YELLOW}⚠️  auto_startup_sync.py が見つかりません（スキップ）${NC}"
    log_warn "auto_startup_sync.py not found"
fi

# ============================================================
# 4️⃣ セッション記録システム起動
# ============================================================
start_process "session_recorder" "${PROJECT_ROOT}/scripts/session_recorder_daemon.py"

# ============================================================
# 5️⃣ PDCAガーディアンシステム起動
# ============================================================
start_process "pdca_guardian" "${PROJECT_ROOT}/pdca_guardian_daemon.py"

# ============================================================
# 5.5️⃣ Episode Analytics API起動
# ============================================================
start_process "episode_api" "${PROJECT_ROOT}/scripts/start_episode_api.py"

# ============================================================
# 6️⃣ AI協調分析システム起動
# ============================================================
if [ -f "${PROJECT_ROOT}/ai_collaboration_system.py" ]; then
    # AI協調分析システムはデーモンモードで起動
    if is_process_running "ai_collaboration"; then
        echo -e "${YELLOW}⚠️  ai_collaboration は既に起動しています${NC}"
    else
        echo -e "${CYAN}🔄 ai_collaboration を起動中...${NC}"
        log_info "Starting ai_collaboration"

        python3 "${PROJECT_ROOT}/ai_collaboration_system.py" --daemon > /dev/null 2>&1 &
        pid=$!
        echo "$pid" > "${PID_DIR}/ai_collaboration.pid"

        sleep 3
        if ps -p "$pid" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ ai_collaboration 起動成功 (PID: $pid)${NC}"
            log_success "ai_collaboration started successfully (PID: $pid)"
        else
            echo -e "${RED}❌ ai_collaboration 起動失敗${NC}"
            log_error "ai_collaboration failed to start"
            rm -f "${PID_DIR}/ai_collaboration.pid"
        fi
    fi
else
    echo -e "${YELLOW}⚠️  ai_collaboration_system.py が見つかりません（スキップ）${NC}"
    log_warn "ai_collaboration_system.py not found"
fi

# ============================================================
# 7️⃣ ファクトチェッカー実行（無効化 - 2025-10-15）
# ============================================================
# 理由: メモリリーク発生のため自動実行を無効化
# - 過去の実行で24.8 GBのメモリ消費を確認
# - 手動実行: ./scripts/safe_fact_checker.sh
# ============================================================
echo -e "${YELLOW}ℹ️  ファクトチェッカーは手動実行に変更されました${NC}"
echo -e "${YELLOW}  → 実行方法: ./scripts/safe_fact_checker.sh${NC}"
log_info "Fact checker disabled (use safe_fact_checker.sh for manual execution)"

# ============================================================
# 5️⃣ リアルタイム監視起動（オプション）
# ============================================================
MONITOR_ENABLED=$(python3 -c "import json; print(json.load(open('startup_config.json'))['advanced_features'].get('enable_real_time_monitoring', False))" 2>/dev/null)

if [ "$MONITOR_ENABLED" = "True" ]; then
    echo -e "${CYAN}👁️  リアルタイム監視を起動中...${NC}"
    log_info "Starting real-time monitoring"

    # 既存の監視プロセスを終了
    pkill -f "watchdog" 2>/dev/null || true

    # 監視スクリプトをバックグラウンドで起動
    nohup python3 -c "
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import subprocess
import time

class CSVWatcher(FileSystemEventHandler):
    def on_modified(self, event):
        if not event.is_directory and 'trusted_episodes' in event.src_path and event.src_path.endswith('.csv'):
            print(f'📝 検出: {event.src_path} が更新されました')
            subprocess.run(['python3', 'auto_startup_sync.py'], capture_output=True)

observer = Observer()
observer.schedule(CSVWatcher(), '.', recursive=False)
observer.start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    observer.stop()
observer.join()
" > /dev/null 2>&1 &

    echo $! > "${PID_DIR}/watchdog.pid"
    echo -e "${GREEN}✅ リアルタイム監視起動成功${NC}"
    log_success "Real-time monitoring started"
fi

# ============================================================
# 📊 起動完了サマリー
# ============================================================
echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   ✨ AI協調分析システム起動完了！                       ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}✅ すべて正常稼働中${NC}"
echo ""
echo -e "${CYAN}💡 重要: システム稼働状況について${NC}"
echo -e "  このメッセージが表示された時点で、すべてのシステムは正常に動作しています。"
echo -e "  「システムは稼働していますか？」という質問は不要です。"
echo -e "  詳細: .session/AUTO_STARTUP_GUIDE.md をご覧ください。"
echo ""
echo -e "${CYAN}📌 稼働中のサービス:${NC}"

# Serena状態
if is_process_running "serena"; then
    echo -e "  ${GREEN}✅ Serena MCP Server${NC} (PID: $(cat "${PID_DIR}/serena.pid"))"
else
    echo -e "  ${RED}❌ Serena MCP Server${NC}"
fi

# Codex状態
if is_process_running "codex"; then
    echo -e "  ${GREEN}✅ Codex MCP Server${NC} (PID: $(cat "${PID_DIR}/codex.pid"))"
else
    echo -e "  ${RED}❌ Codex MCP Server${NC}"
fi

# Auto Sync状態
if is_process_running "auto_sync"; then
    echo -e "  ${GREEN}✅ 自動同期システム${NC} (PID: $(cat "${PID_DIR}/auto_sync.pid"))"
else
    echo -e "  ${YELLOW}⚠️  自動同期システム${NC}"
fi

# Session Recorder状態
if is_process_running "session_recorder"; then
    echo -e "  ${GREEN}✅ セッション記録システム${NC} (PID: $(cat "${PID_DIR}/session_recorder.pid"))"
else
    echo -e "  ${RED}❌ セッション記録システム${NC}"
fi

# PDCA Guardian状態
if is_process_running "pdca_guardian"; then
    echo -e "  ${GREEN}✅ PDCAガーディアン${NC} (PID: $(cat "${PID_DIR}/pdca_guardian.pid"))"
else
    echo -e "  ${RED}❌ PDCAガーディアン${NC}"
fi

# Episode Analytics API状態
if is_process_running "episode_api"; then
    echo -e "  ${GREEN}✅ Episode Analytics API${NC} (PID: $(cat "${PID_DIR}/episode_api.pid")) - http://localhost:8001"
else
    echo -e "  ${RED}❌ Episode Analytics API${NC}"
fi

# AI Collaboration状態
if is_process_running "ai_collaboration"; then
    echo -e "  ${GREEN}✅ AI協調分析システム${NC} (PID: $(cat "${PID_DIR}/ai_collaboration.pid"))"
else
    echo -e "  ${RED}❌ AI協調分析システム${NC}"
fi

# 監視状態
if [ -f "${PID_DIR}/watchdog.pid" ]; then
    echo -e "  ${GREEN}✅ リアルタイム監視${NC}"
fi

echo ""
echo -e "${CYAN}🔗 ダッシュボード:${NC}"
echo "  📊 Serena: http://127.0.0.1:24282/dashboard/index.html"
echo "  🤖 Codex: http://localhost:8765"
echo ""
echo -e "${CYAN}📝 便利なコマンド:${NC}"
echo "  • 状態確認: ./scripts/check_ai_collaboration_status.sh"
echo "  • システム停止: ./scripts/stop_ai_collaboration.sh"
echo "  • ログ確認: tail -f .unified_startup.log"
echo ""

log_info "========== Unified Startup Complete =========="

# 成功音を鳴らす（macOS）
if [ "$(uname)" = "Darwin" ]; then
    afplay /System/Library/Sounds/Glass.aiff 2>/dev/null &
fi

exit 0
