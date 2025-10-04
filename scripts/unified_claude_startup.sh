#!/bin/bash
# ============================================================
# 🚀 Claude Code統合起動フック v4.0
# ============================================================
# Claude Code起動時に完全なシステム起動と稼働確認を実行
# - セッション記録・復元システム
# - PDCAガーディアンシステム
# - AI協調分析システム
# - 統合MCP管理システム
# ============================================================

set -e  # エラーで即座に停止

# ============================================================
# カラー定義
# ============================================================
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly MAGENTA='\033[0;35m'
readonly WHITE='\033[1;37m'
readonly NC='\033[0m'

# ============================================================
# プロジェクト設定
# ============================================================
readonly PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly SCRIPT_DIR="${PROJECT_ROOT}/scripts"
readonly PID_DIR="${PROJECT_ROOT}/.pids"
readonly LOG_DIR="${PROJECT_ROOT}/logs"
readonly STARTUP_LOG="${LOG_DIR}/unified_startup_$(date +%Y%m%d_%H%M%S).log"
readonly HEALTH_CHECK_LOG="${LOG_DIR}/health_check.log"

# ディレクトリ作成
mkdir -p "$PID_DIR" "$LOG_DIR"

# ============================================================
# ログ関数
# ============================================================
log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" | tee -a "$STARTUP_LOG"
}

log_info() { log "INFO" "$@"; }
log_success() { log "SUCCESS" "$@"; }
log_error() { log "ERROR" "$@"; }
log_warn() { log "WARN" "$@"; }

# ============================================================
# バナー表示
# ============================================================
show_banner() {
    echo -e "${CYAN}"
    cat << 'EOF'
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   🚀 Claude Code 統合起動システム v4.0                     ║
║                                                              ║
║   ✨ セッション記録・復元システム                          ║
║   🎯 PDCAガーディアンシステム                              ║
║   🤖 AI協調分析システム                                    ║
║   🔧 統合MCP管理システム                                   ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}\n"
}

# ============================================================
# プロセス管理関数
# ============================================================

# プロセスの実行確認
is_process_running() {
    local process_name=$1
    local pid_file="${PID_DIR}/${process_name}.pid"

    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            return 0  # 実行中
        else
            rm -f "$pid_file"  # 古いPIDファイル削除
        fi
    fi
    return 1  # 未実行
}

# プロセス起動（改善版 - ポート再利用対応）
start_process_with_retry() {
    local name=$1
    local script=$2
    local max_retries=${3:-3}
    local pid_file="${PID_DIR}/${name}.pid"

    echo -e "${CYAN}🔄 ${name} 起動処理開始...${NC}"
    log_info "Starting ${name} startup process"

    # スクリプトの存在確認
    if [ ! -f "$script" ]; then
        echo -e "${RED}❌ エラー: ${script} が見つかりません${NC}"
        log_error "${script} not found"
        return 1
    fi

    # Pythonスクリプトを直接実行（ポート管理ロジック内蔵）
    if [[ "$script" == *.py ]]; then
        if python3 "$script"; then
            echo -e "${GREEN}✅ ${name}${NC} - 起動/再利用成功"
            log_success "${name} started or reused successfully"
            return 0
        else
            echo -e "${RED}❌ ${name}${NC} - 起動失敗"
            log_error "${name} failed to start"
            return 1
        fi
    else
        # Bashスクリプトの場合は従来通り
        bash "$script" > "${LOG_DIR}/${name}.log" 2>&1 &
        local pid=$!
        echo "$pid" > "$pid_file"

        # 起動確認
        sleep 5
        if ps -p "$pid" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ ${name}${NC} - 起動成功 (PID: $pid)"
            log_success "${name} started successfully (PID: $pid)"
            return 0
        else
            echo -e "${RED}❌ ${name}${NC} - 起動失敗${NC}"
            log_error "${name} failed to start"
            rm -f "$pid_file"
            return 1
        fi
    fi
}

# ============================================================
# ヘルスチェック関数
# ============================================================
health_check() {
    local service_name=$1
    local check_command=$2

    echo -e "${CYAN}🔍 ${service_name} ヘルスチェック中...${NC}"
    log_info "Health check: ${service_name}"

    if eval "$check_command" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ ${service_name}${NC} - 正常稼働"
        log_success "${service_name} health check passed"
        return 0
    else
        echo -e "${RED}❌ ${service_name}${NC} - 異常検出"
        log_error "${service_name} health check failed"
        return 1
    fi
}

# 総合ヘルスチェック
comprehensive_health_check() {
    echo -e "\n${CYAN}╔══════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║  🏥 システムヘルスチェック開始     ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════╝${NC}\n"

    local all_healthy=true

    # Serenaチェック
    if health_check "Serena MCP Server" "curl -s http://127.0.0.1:24282/health"; then
        echo "  ├─ API: http://127.0.0.1:24282"
    else
        all_healthy=false
    fi

    # Codexチェック
    if health_check "Codex MCP Server" "lsof -i :8765"; then
        echo "  ├─ API: http://localhost:8765"
    else
        all_healthy=false
    fi

    # PDCAガーディアンチェック
    if is_process_running "pdca_guardian"; then
        echo -e "${GREEN}✅ PDCAガーディアン${NC} - 稼働中"
        log_success "PDCA Guardian health check passed"
    else
        echo -e "${RED}❌ PDCAガーディアン${NC} - 停止中"
        log_error "PDCA Guardian not running"
        all_healthy=false
    fi

    # 自動同期チェック
    if is_process_running "auto_sync"; then
        echo -e "${GREEN}✅ 自動同期システム${NC} - 稼働中"
        log_success "Auto sync health check passed"
    else
        echo -e "${YELLOW}⚠️  自動同期システム${NC} - 停止中（オプション）"
        log_warn "Auto sync not running"
    fi

    # 監視システムチェック
    if pgrep -f "watchdog" > /dev/null; then
        echo -e "${GREEN}✅ リアルタイム監視${NC} - 稼働中"
        log_success "Watchdog health check passed"
    else
        echo -e "${YELLOW}⚠️  リアルタイム監視${NC} - 停止中（オプション）"
        log_warn "Watchdog not running"
    fi

    echo ""

    if [ "$all_healthy" = true ]; then
        echo -e "${GREEN}╔══════════════════════════════════════╗${NC}"
        echo -e "${GREEN}║  ✅ すべてのシステムが正常稼働    ║${NC}"
        echo -e "${GREEN}╚══════════════════════════════════════╝${NC}"
        log_success "All systems healthy"
        return 0
    else
        echo -e "${YELLOW}╔══════════════════════════════════════╗${NC}"
        echo -e "${YELLOW}║  ⚠️  一部のシステムに問題あり     ║${NC}"
        echo -e "${YELLOW}╚══════════════════════════════════════╝${NC}"
        log_warn "Some systems unhealthy"
        return 1
    fi
}

# ============================================================
# メイン起動シーケンス
# ============================================================
main() {
    log_info "========== Claude Code Unified Startup Begin =========="
    show_banner

    cd "$PROJECT_ROOT" || {
        echo -e "${RED}❌ プロジェクトディレクトリに移動できません${NC}"
        exit 1
    }

    # ============================================================
    # Phase 1: 環境チェック
    # ============================================================
    echo -e "${MAGENTA}Phase 1: 環境チェック${NC}\n"
    log_info "Phase 1: Environment check"

    # Python確認
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ Python3が見つかりません${NC}"
        log_error "Python3 not found"
        exit 1
    fi
    echo -e "${GREEN}✅ Python3${NC} - $(python3 --version)"

    # 仮想環境の有効化
    if [ -d "venv" ]; then
        echo -e "${CYAN}🐍 仮想環境を有効化${NC}"
        source venv/bin/activate
        log_info "Virtual environment activated"
    fi

    # 必須ファイル確認
    local required_files=(
        "startup_config.json"
        "pdca_guardian.py"
    )

    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            echo -e "${RED}❌ 必須ファイルが見つかりません: $file${NC}"
            log_error "Required file not found: $file"
            exit 1
        fi
    done
    echo -e "${GREEN}✅ 必須ファイル確認完了${NC}\n"

    # ============================================================
    # Phase 2: MCPサーバー並行起動
    # ============================================================
    echo -e "${MAGENTA}Phase 2: MCPサーバー起動${NC}\n"
    log_info "Phase 2: MCP servers startup"

    # Serena起動
    start_process_with_retry "serena" "${SCRIPT_DIR}/start_serena_server.py" 3 &
    local serena_pid=$!

    # Codex起動
    start_process_with_retry "codex" "${SCRIPT_DIR}/start_codex_server.py" 3 &
    local codex_pid=$!

    # 並行起動の完了待機
    wait $serena_pid
    local serena_result=$?

    wait $codex_pid
    local codex_result=$?

    if [ $serena_result -ne 0 ] || [ $codex_result -ne 0 ]; then
        echo -e "${YELLOW}⚠️  一部のMCPサーバーの起動に失敗しました${NC}"
        log_warn "Some MCP servers failed to start"
    fi

    echo ""

    # ============================================================
    # Phase 3: PDCAガーディアン起動
    # ============================================================
    echo -e "${MAGENTA}Phase 3: PDCAガーディアン起動${NC}\n"
    log_info "Phase 3: PDCA Guardian startup"

    start_process_with_retry "pdca_guardian" "${PROJECT_ROOT}/pdca_guardian_daemon.py" 3

    echo ""

    # ============================================================
    # Phase 4: 周辺システム起動
    # ============================================================
    echo -e "${MAGENTA}Phase 4: 周辺システム起動${NC}\n"
    log_info "Phase 4: Additional systems startup"

    # 自動同期システム
    if [ -f "${PROJECT_ROOT}/auto_startup_sync.py" ]; then
        start_process_with_retry "auto_sync" "${PROJECT_ROOT}/auto_startup_sync.py" 2
    else
        echo -e "${YELLOW}⚠️  auto_startup_sync.py が見つかりません（スキップ）${NC}"
        log_warn "auto_startup_sync.py not found"
    fi

    # ファクトチェッカー（1回のみ実行）
    if [ -f "${SCRIPT_DIR}/fact_checker.py" ]; then
        echo -e "${CYAN}🔍 ファクトチェック実行中...${NC}"
        if python3 "${SCRIPT_DIR}/fact_checker.py" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ ファクトチェック完了${NC}"
            log_success "Fact check completed"
        else
            echo -e "${YELLOW}⚠️  ファクトチェックで誤記を検出${NC}"
            echo -e "${YELLOW}  → 修正: python3 scripts/fact_checker.py --fix${NC}"
            log_warn "Fact check detected errors"
        fi
    fi

    # リアルタイム監視（オプション）
    local monitor_enabled=$(python3 -c "import json; print(json.load(open('startup_config.json'))['advanced_features'].get('enable_real_time_monitoring', False))" 2>/dev/null)

    if [ "$monitor_enabled" = "True" ]; then
        echo -e "${CYAN}👁️  リアルタイム監視を起動中...${NC}"

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
" > "${LOG_DIR}/watchdog.log" 2>&1 &

        echo $! > "${PID_DIR}/watchdog.pid"
        echo -e "${GREEN}✅ リアルタイム監視起動成功${NC}"
        log_success "Real-time monitoring started"
    fi

    echo ""

    # ============================================================
    # Phase 5: ヘルスチェック
    # ============================================================
    echo -e "${MAGENTA}Phase 5: システムヘルスチェック${NC}\n"
    log_info "Phase 5: Health check"

    sleep 3  # システム安定化待機

    comprehensive_health_check
    local health_result=$?

    # ============================================================
    # Phase 6: 起動完了レポート
    # ============================================================
    echo -e "\n${MAGENTA}Phase 6: 起動完了レポート${NC}\n"
    log_info "Phase 6: Startup report"

    echo -e "${WHITE}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${WHITE}║                                                              ║${NC}"
    echo -e "${WHITE}║   ✨ Claude Code 統合起動完了！                            ║${NC}"
    echo -e "${WHITE}║                                                              ║${NC}"
    echo -e "${WHITE}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    echo -e "${CYAN}📊 稼働中のシステム:${NC}"

    # Serena
    if is_process_running "serena"; then
        echo -e "  ${GREEN}✅ Serena MCP Server${NC}"
        echo -e "     └─ Dashboard: ${BLUE}http://127.0.0.1:24282/dashboard/index.html${NC}"
    else
        echo -e "  ${RED}❌ Serena MCP Server${NC}"
    fi

    # Codex
    if is_process_running "codex"; then
        echo -e "  ${GREEN}✅ Codex MCP Server${NC}"
        echo -e "     └─ API: ${BLUE}http://localhost:8765${NC}"
    else
        echo -e "  ${RED}❌ Codex MCP Server${NC}"
    fi

    # PDCAガーディアン
    if is_process_running "pdca_guardian"; then
        echo -e "  ${GREEN}✅ PDCAガーディアン${NC}"
    else
        echo -e "  ${RED}❌ PDCAガーディアン${NC}"
    fi

    # 自動同期
    if is_process_running "auto_sync"; then
        echo -e "  ${GREEN}✅ 自動同期システム${NC}"
    else
        echo -e "  ${YELLOW}⚠️  自動同期システム${NC}"
    fi

    # 監視
    if pgrep -f "watchdog" > /dev/null; then
        echo -e "  ${GREEN}✅ リアルタイム監視${NC}"
    fi

    echo ""
    echo -e "${CYAN}📝 便利なコマンド:${NC}"
    echo "  • 状態確認: ./scripts/check_system_health.sh"
    echo "  • システム停止: ./scripts/stop_ai_collaboration.sh"
    echo "  • ログ確認: tail -f ${STARTUP_LOG}"
    echo ""

    # 成功音
    if [ "$(uname)" = "Darwin" ] && [ $health_result -eq 0 ]; then
        afplay /System/Library/Sounds/Glass.aiff 2>/dev/null &
    fi

    log_info "========== Claude Code Unified Startup Complete =========="

    exit $health_result
}

# 起動実行
main "$@"
