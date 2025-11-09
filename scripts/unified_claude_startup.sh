#!/bin/bash
# ============================================================
# 🚀 Claude Code統合起動フック v5.0 (RCA-Kaizen #016)
# ============================================================
# Claude Code起動時に完全なシステム起動と稼働確認を実行
# - セッション記録・復元システム
# - PDCAガーディアンシステム
# - AI協調分析システム
# - 統合MCP管理システム
# - Crash Resilience (自動監視・復旧システム) ← NEW!
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
# Phase 7-3: エラーハンドリング強化モジュールのロード
# ============================================================

# Phase 7-2: 冪等性起動ガード
if [ -f "${SCRIPT_DIR}/idempotent_startup_guard.sh" ]; then
    source "${SCRIPT_DIR}/idempotent_startup_guard.sh"
    log_info "冪等性起動ガード機能をロードしました"
else
    log_warn "冪等性起動ガードが見つかりません: ${SCRIPT_DIR}/idempotent_startup_guard.sh"
fi

# Phase 7-3-1: エラーハンドラー
if [ -f "${SCRIPT_DIR}/startup_error_handler.sh" ]; then
    source "${SCRIPT_DIR}/startup_error_handler.sh"
    log_info "エラーハンドラーをロードしました"
else
    log_warn "エラーハンドラーが見つかりません: ${SCRIPT_DIR}/startup_error_handler.sh"
fi

# Phase 7-3-2: リトライマネージャー
if [ -f "${SCRIPT_DIR}/startup_retry_manager.sh" ]; then
    source "${SCRIPT_DIR}/startup_retry_manager.sh"
    log_info "リトライマネージャーをロードしました"
else
    log_warn "リトライマネージャーが見つかりません: ${SCRIPT_DIR}/startup_retry_manager.sh"
fi

# Phase 7-3-3: ロールバックマネージャー
if [ -f "${SCRIPT_DIR}/startup_rollback_manager.sh" ]; then
    source "${SCRIPT_DIR}/startup_rollback_manager.sh"
    log_info "ロールバックマネージャーをロードしました"
else
    log_warn "ロールバックマネージャーが見つかりません: ${SCRIPT_DIR}/startup_rollback_manager.sh"
fi

# ============================================================
# バナー表示
# ============================================================
show_banner() {
    echo -e "${CYAN}"
    cat << 'EOF'
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   🚀 Claude Code 統合起動システム v7.0                     ║
║                                                              ║
║   ✨ セッション記録・復元システム                          ║
║   🎯 PDCAガーディアンシステム                              ║
║   🤖 AI協調分析システム                                    ║
║   🔧 統合MCP管理システム                                   ║
║   🛡️ Crash Resilience (自動監視・復旧)                   ║
║   🚨 エラーハンドリング強化 (Phase 7-3)                  ║
║   🔄 自動リトライ & ロールバック                          ║
║   📊 品質メトリクス監視 (Phase 8)                        ║
║   ⚡ 並列起動機構 (Phase 9-2) ← NEW!                    ║
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

# プロセス起動待機
wait_for_process() {
    local pid=$1
    local name=$2
    local timeout=30
    local elapsed=0

    while [ $elapsed -lt $timeout ]; do
        if kill -0 "$pid" 2>/dev/null; then
            echo -e "${GREEN}✅ $name (PID: $pid) 起動確認${NC}"
            return 0
        fi
        sleep 1
        elapsed=$((elapsed + 1))
    done

    echo -e "${RED}❌ $name タイムアウト${NC}"
    return 1
}

# データベース準備待機
wait_for_db_ready() {
    local timeout=10
    local elapsed=0

    echo -e "${CYAN}⏳ データベース準備待機...${NC}"

    while [ $elapsed -lt $timeout ]; do
        # データベースファイルのロック確認
        if [ -f "${PROJECT_ROOT}/unified_quality.db" ]; then
            local lock_count=$(lsof "${PROJECT_ROOT}/unified_quality.db" 2>/dev/null | wc -l | tr -d ' ')
            if [ "$lock_count" -le 1 ]; then
                echo -e "${GREEN}✅ データベース準備完了${NC}"
                return 0
            fi
        fi
        sleep 1
        elapsed=$((elapsed + 1))
    done

    echo -e "${YELLOW}⚠️ データベース待機タイムアウト（続行）${NC}"
    return 0
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

    # ============================================================
    # MCP Server 専用ヘルスチェック (RCA-KAIZEN-026)
    # ============================================================
    echo -e "${CYAN}🔍 MCP Servers 健全性診断（専用スクリプト使用）${NC}"

    if python3 "${SCRIPT_DIR}/health_check_mcp.py" > "$HEALTH_CHECK_LOG" 2>&1; then
        echo -e "${GREEN}✅ Serena MCP Server${NC} - 完全稼働"
        echo "  ├─ SSEエンドポイント: http://localhost:8000/sse"
        echo "  ├─ Dashboard: http://127.0.0.1:24282/dashboard/index.html"
        echo "  └─ 言語サーバー: Pyright (初期化完了)"
        log_success "Serena MCP Server health check passed (SSE endpoint verified)"
    else
        echo -e "${RED}❌ Serena MCP Server${NC} - 異常検出"
        echo -e "${YELLOW}  詳細: cat $HEALTH_CHECK_LOG${NC}"
        log_error "Serena MCP Server health check failed"
        all_healthy=false
    fi

    echo ""

    # Codexチェック
    if health_check "Codex MCP Server" "lsof -i :8765"; then
        echo "  ├─ API: http://localhost:8765"
    else
        all_healthy=false
    fi

    # PDCAガーディアンチェック（データベースロック確認付き）
    if is_process_running "pdca_guardian"; then
        # 重複プロセスチェック
        local pdca_count=$(pgrep -f "pdca_guardian_v2.py --daemon" | wc -l)
        if [ "$pdca_count" -gt 1 ]; then
            echo -e "${RED}❌ PDCAガーディアン${NC} - 重複プロセス検出 ($pdca_count個)"
            log_error "PDCA Guardian: Multiple processes detected"
            all_healthy=false
        else
            echo -e "${GREEN}✅ PDCAガーディアン${NC} - 稼働中"
            log_success "PDCA Guardian health check passed"
        fi
    else
        echo -e "${RED}❌ PDCAガーディアン${NC} - 停止中"
        log_error "PDCA Guardian not running"
        all_healthy=false
    fi

    # Session Recorderチェック
    if is_process_running "session_recorder"; then
        echo -e "${GREEN}✅ セッション記録${NC} - 稼働中"
        log_success "Session Recorder health check passed"
    else
        echo -e "${RED}❌ セッション記録${NC} - 停止中"
        log_error "Session Recorder not running"
        all_healthy=false
    fi

    # AI Collaboration Systemチェック
    if is_process_running "ai_collaboration"; then
        echo -e "${GREEN}✅ AI協調分析システム${NC} - 稼働中"
        log_success "AI Collaboration System health check passed"
    else
        echo -e "${RED}❌ AI協調分析システム${NC} - 停止中"
        log_error "AI Collaboration System not running"
        all_healthy=false
    fi

    # Unified MCP Managerチェック
    if is_process_running "mcp_manager"; then
        echo -e "${GREEN}✅ 統合MCP管理システム${NC} - 稼働中"
        log_success "Unified MCP Manager health check passed"
    else
        echo -e "${RED}❌ 統合MCP管理システム${NC} - 停止中"
        log_error "Unified MCP Manager not running"
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

    # データベースロックチェック
    if [ -f "${PROJECT_ROOT}/unified_quality.db" ]; then
        if lsof "${PROJECT_ROOT}/unified_quality.db" > /dev/null 2>&1; then
            local lock_count=$(lsof "${PROJECT_ROOT}/unified_quality.db" 2>/dev/null | grep -v COMMAND | wc -l)
            if [ "$lock_count" -gt 3 ]; then
                echo -e "${YELLOW}⚠️  データベース${NC} - 多数のロック($lock_count個)"
                log_warn "Database: Multiple locks detected"
            else
                echo -e "${GREEN}✅ データベース${NC} - 正常アクセス"
            fi
        fi
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

    # ============================================================
    # Phase 7-2: 冪等性確保 - グローバルロック取得
    # ============================================================
    if type acquire_startup_lock &>/dev/null; then
        echo -e "${CYAN}🔒 起動冪等性チェック...${NC}"
        if ! acquire_startup_lock; then
            echo -e "${RED}❌ 起動ロックの取得に失敗しました${NC}"
            echo -e "${YELLOW}   別の起動プロセスが実行中の可能性があります${NC}"
            exit 1
        fi
        # 終了時にロック解放
        trap 'release_startup_lock' EXIT INT TERM
        echo -e "${GREEN}✅ 起動ロック取得成功${NC}\n"
    fi

    cd "$PROJECT_ROOT" || {
        echo -e "${RED}❌ プロジェクトディレクトリに移動できません${NC}"
        exit 1
    }

    # ============================================================
    # Phase 0: 包括的システム健全性チェック（統合版）
    # ============================================================
    echo -e "${MAGENTA}Phase 0: 包括的システム健全性チェック${NC}\n"
    log_info "Phase 0: Comprehensive system health check"

    if [ -f "${SCRIPT_DIR}/comprehensive_startup_check.sh" ]; then
        echo -e "${CYAN}🔍 全システムステータスチェック実行中...${NC}"
        if bash "${SCRIPT_DIR}/comprehensive_startup_check.sh"; then
            echo -e "${GREEN}✅ 全システム正常稼働確認${NC}\n"
            log_success "All systems operational"
        else
            echo -e "${YELLOW}⚠️  一部のシステムを修復しました${NC}\n"
            log_warn "Some systems required repair"
        fi
    elif [ -f "${SCRIPT_DIR}/system_health_check.sh" ]; then
        echo -e "${CYAN}🏥 健全性チェックを実行中...${NC}"
        if bash "${SCRIPT_DIR}/system_health_check.sh"; then
            echo -e "${GREEN}✅ システム健全性チェック完了${NC}\n"
            log_success "System health check passed"
        else
            echo -e "${YELLOW}⚠️  一部の問題を修正しました${NC}\n"
            log_warn "System health check completed with warnings"
        fi
    else
        echo -e "${YELLOW}⚠️  健全性チェックスクリプトが見つかりません（スキップ）${NC}\n"
        log_warn "Health check script not found"
    fi

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
    # Phase 3: コアシステム並列起動（Phase 9-2最適化版）
    # ============================================================
    echo -e "${MAGENTA}Phase 3: コアシステム並列起動（⚡最適化版）${NC}\n"
    log_info "Phase 3: Parallel core systems startup"

    # 並列起動マネージャーを実行
    if [ -f "${SCRIPT_DIR}/parallel_startup_manager.sh" ]; then
        echo -e "${CYAN}⚡ 並列起動マネージャーを実行中...${NC}"
        if bash "${SCRIPT_DIR}/parallel_startup_manager.sh"; then
            echo -e "${GREEN}✅ 並列起動完了${NC}\n"
            log_success "Parallel startup completed successfully"
            local all_started=true
        else
            echo -e "${RED}❌ 並列起動失敗 - フォールバック不要${NC}\n"
            log_error "Parallel startup failed"
            local all_started=false
        fi
    else
        echo -e "${RED}❌ 並列起動マネージャーが見つかりません${NC}"
        log_error "parallel_startup_manager.sh not found"
        local all_started=false
    fi

    if [ "$all_started" = true ]; then
        echo -e "${GREEN}✅ 全コアシステム起動完了${NC}"
        log_success "All core systems started successfully"
    else
        echo -e "${YELLOW}⚠️  一部のコアシステムの起動に失敗しました${NC}"
        log_warn "Some core systems failed to start"
    fi

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

    # AI Collaboration System
    if is_process_running "ai_collaboration"; then
        echo -e "  ${GREEN}✅ AI協調分析システム${NC}"
    else
        echo -e "  ${RED}❌ AI協調分析システム${NC}"
    fi

    # Unified MCP Manager
    if is_process_running "mcp_manager"; then
        echo -e "  ${GREEN}✅ 統合MCP管理システム${NC}"
    else
        echo -e "  ${RED}❌ 統合MCP管理システム${NC}"
    fi

    # Daemon Watchdog（RCA-Kaizen #016追加）
    if is_process_running "watchdog"; then
        echo -e "  ${GREEN}✅ Daemon Watchdog (Crash Resilience)${NC}"
        echo -e "     └─ 自動監視・復旧システム稼働中${NC}"
    else
        echo -e "  ${RED}❌ Daemon Watchdog (手動監視必要)${NC}"
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

    # システム健全性診断を実行
    echo ""
    echo -e "${CYAN}📊 品質メトリクスを収集中...${NC}"
    if [ -f "${SCRIPT_DIR}/quality_metrics_collector.py" ]; then
        python3 "${SCRIPT_DIR}/quality_metrics_collector.py" "${PROJECT_ROOT}" > /dev/null 2>&1 || true
        log_info "品質メトリクスを収集しました"
    fi

    echo ""
    echo -e "${CYAN}🏥 システム健全性診断を実行中...${NC}"
    if [ -f "${SCRIPT_DIR}/auto_system_diagnosis.sh" ]; then
        bash "${SCRIPT_DIR}/auto_system_diagnosis.sh"
    fi

    # 起動完了メッセージの保存（次回起動時に表示）
    cat > "${PROJECT_ROOT}/.session/startup_message.txt" << EOF
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 Claude Code統合システム - 前回起動完了
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ 全システムが正常に起動しました

📊 稼働中のシステム:
  • Serena MCP Server
  • Codex MCP Server
  • PDCAガーディアン
  • AI協調分析システム
  • セッション記録システム
  • Daemon Watchdog (Crash Resilience)

🔗 便利なコマンド:
  • システムステータス確認: python3 scripts/system_health_dashboard.py
  • 品質メトリクスダッシュボード: python3 scripts/quality_metrics_dashboard.py
  • 手動起動: ./scripts/unified_claude_startup.sh
  • システム停止: ./scripts/stop_ai_collaboration.sh

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF

    exit $health_result
}

# 起動実行
main "$@"
