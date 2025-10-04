#!/bin/bash
# ============================================================
# 🏥 システムヘルスチェックスクリプト v2.0
# ============================================================
# すべてのシステムコンポーネントの稼働状態を詳細に確認
# ============================================================

set -e

# カラー定義
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly MAGENTA='\033[0;35m'
readonly NC='\033[0m'

# プロジェクト設定
readonly PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly PID_DIR="${PROJECT_ROOT}/.pids"
readonly LOG_DIR="${PROJECT_ROOT}/logs"

# ============================================================
# ヘルスチェック関数
# ============================================================

check_process() {
    local name=$1
    local pid_file="${PID_DIR}/${name}.pid"

    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            echo -e "  ${GREEN}✅ ${name}${NC} - 稼働中 (PID: $pid)"
            return 0
        else
            echo -e "  ${RED}❌ ${name}${NC} - プロセス停止（PIDファイル残存）"
            return 1
        fi
    else
        echo -e "  ${YELLOW}⚠️  ${name}${NC} - 未起動"
        return 1
    fi
}

check_port() {
    local name=$1
    local port=$2

    if lsof -i ":$port" > /dev/null 2>&1; then
        echo -e "  ${GREEN}✅ ${name} (Port ${port})${NC} - リスニング中"
        return 0
    else
        echo -e "  ${RED}❌ ${name} (Port ${port})${NC} - ポート未使用"
        return 1
    fi
}

# port_utils.pyを使った詳細ポート診断
check_port_detailed() {
    local name=$1
    local port=$2
    local service_name=$3
    local pid_file="${PID_DIR}/${name}.pid"

    # port_utils.pyを使って詳細診断
    local diagnosis=$(python3 -c "
import sys
sys.path.insert(0, '${PROJECT_ROOT}/scripts')
from port_utils import check_port_status
from pathlib import Path

pid_file = Path('$pid_file') if '$pid_file' else None
status, pid = check_port_status($port, '$service_name', pid_file)

if status == 'available':
    print('AVAILABLE|0|ポートは空いています')
elif status == 'reusable':
    print(f'REUSABLE|{pid}|正常稼働中（再利用可能）')
elif status == 'unhealthy':
    print(f'UNHEALTHY|{pid}|プロセスは動作中だが健全でない')
elif status == 'occupied':
    print(f'OCCUPIED|{pid}|別のプロセスが使用中')
" 2>/dev/null)

    if [ -z "$diagnosis" ]; then
        echo -e "  ${YELLOW}⚠️  ${name} (Port ${port})${NC} - 診断不可"
        return 2
    fi

    IFS='|' read -r status pid message <<< "$diagnosis"

    case "$status" in
        AVAILABLE)
            echo -e "  ${YELLOW}⚠️  ${name} (Port ${port})${NC} - ${message}"
            return 1
            ;;
        REUSABLE)
            echo -e "  ${GREEN}✅ ${name} (Port ${port})${NC} - ${message} (PID: ${pid})"
            return 0
            ;;
        UNHEALTHY)
            echo -e "  ${RED}❌ ${name} (Port ${port})${NC} - ${message} (PID: ${pid})"
            echo -e "     ${CYAN}→ 推奨: プロセスを再起動してください${NC}"
            return 1
            ;;
        OCCUPIED)
            echo -e "  ${RED}❌ ${name} (Port ${port})${NC} - ${message} (PID: ${pid})"
            echo -e "     ${CYAN}→ 推奨: 競合プロセスを確認してください (ps -p ${pid})${NC}"
            return 1
            ;;
        *)
            echo -e "  ${YELLOW}⚠️  ${name} (Port ${port})${NC} - 不明な状態"
            return 2
            ;;
    esac
}

check_http_endpoint() {
    local name=$1
    local url=$2

    if curl -s -f "$url" > /dev/null 2>&1; then
        echo -e "  ${GREEN}✅ ${name}${NC} - 応答OK"
        return 0
    else
        echo -e "  ${RED}❌ ${name}${NC} - 応答なし"
        return 1
    fi
}

# ============================================================
# メインヘルスチェック
# ============================================================

show_header() {
    echo -e "${CYAN}"
    cat << 'EOF'
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   🏥 システムヘルスチェック - 完全診断                     ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}\n"
}

main() {
    cd "$PROJECT_ROOT" || exit 1

    show_header

    local total_checks=0
    local passed_checks=0

    # ============================================================
    # 1. プロセス稼働状態
    # ============================================================
    echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${MAGENTA}📊 プロセス稼働状態${NC}"
    echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

    # Serena
    total_checks=$((total_checks + 1))
    if check_process "serena"; then
        passed_checks=$((passed_checks + 1))
    fi

    # Codex
    total_checks=$((total_checks + 1))
    if check_process "codex"; then
        passed_checks=$((passed_checks + 1))
    fi

    # PDCAガーディアン
    total_checks=$((total_checks + 1))
    if check_process "pdca_guardian"; then
        passed_checks=$((passed_checks + 1))
    fi

    # 自動同期（オプション）
    if check_process "auto_sync"; then
        # オプションなので合格率に含めない
        :
    fi

    # 監視システム（オプション）
    if pgrep -f "watchdog" > /dev/null; then
        echo -e "  ${GREEN}✅ リアルタイム監視${NC} - 稼働中"
    else
        echo -e "  ${YELLOW}⚠️  リアルタイム監視${NC} - 停止中（オプション）"
    fi

    echo ""

    # ============================================================
    # 2. ネットワークポート（詳細診断）
    # ============================================================
    echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${MAGENTA}🔌 ネットワークポート詳細診断${NC}"
    echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

    # Codex (Port 8765)
    total_checks=$((total_checks + 1))
    if check_port_detailed "codex" 8765 "codex"; then
        passed_checks=$((passed_checks + 1))
    fi

    # Serena (Port 8000)
    total_checks=$((total_checks + 1))
    if check_port_detailed "serena" 8000 "serena"; then
        passed_checks=$((passed_checks + 1))
    fi

    echo ""

    # ============================================================
    # 3. 従来のネットワークポート
    # ============================================================
    echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${MAGENTA}🔌 ネットワークポート状態${NC}"
    echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

    # Serenaポート
    total_checks=$((total_checks + 1))
    if check_port "Serena Dashboard" 24282; then
        passed_checks=$((passed_checks + 1))
    fi

    # Codexポート
    total_checks=$((total_checks + 1))
    if check_port "Codex API" 8765; then
        passed_checks=$((passed_checks + 1))
    fi

    echo ""

    # ============================================================
    # 4. HTTPエンドポイント
    # ============================================================
    echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${MAGENTA}🌐 HTTPエンドポイント応答${NC}"
    echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

    # Serena Health
    total_checks=$((total_checks + 1))
    if check_http_endpoint "Serena Health API" "http://127.0.0.1:24282/health"; then
        passed_checks=$((passed_checks + 1))
    fi

    echo ""

    # ============================================================
    # 5. ファイルシステム
    # ============================================================
    echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${MAGENTA}📁 ファイルシステム状態${NC}"
    echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

    # PIDディレクトリ
    if [ -d "$PID_DIR" ]; then
        local pid_count=$(ls -1 "$PID_DIR"/*.pid 2>/dev/null | wc -l | tr -d ' ')
        echo -e "  ${GREEN}✅ PIDディレクトリ${NC} - ${pid_count}個のPIDファイル"
    else
        echo -e "  ${YELLOW}⚠️  PIDディレクトリ${NC} - 未作成"
    fi

    # ログディレクトリ
    if [ -d "$LOG_DIR" ]; then
        local log_size=$(du -sh "$LOG_DIR" 2>/dev/null | awk '{print $1}')
        echo -e "  ${GREEN}✅ ログディレクトリ${NC} - サイズ: ${log_size}"
    else
        echo -e "  ${YELLOW}⚠️  ログディレクトリ${NC} - 未作成"
    fi

    # 設定ファイル
    if [ -f "${PROJECT_ROOT}/startup_config.json" ]; then
        echo -e "  ${GREEN}✅ startup_config.json${NC} - 存在"
    else
        echo -e "  ${RED}❌ startup_config.json${NC} - 見つかりません"
    fi

    echo ""

    # ============================================================
    # 5. システムリソース
    # ============================================================
    echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${MAGENTA}💻 システムリソース${NC}"
    echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

    # CPU使用率（プロセス別）
    if [ -f "${PID_DIR}/serena.pid" ]; then
        local serena_pid=$(cat "${PID_DIR}/serena.pid")
        local serena_cpu=$(ps -p "$serena_pid" -o %cpu 2>/dev/null | tail -1 | tr -d ' ')
        echo -e "  ${CYAN}Serena CPU${NC}: ${serena_cpu}%"
    fi

    if [ -f "${PID_DIR}/pdca_guardian.pid" ]; then
        local pdca_pid=$(cat "${PID_DIR}/pdca_guardian.pid")
        local pdca_cpu=$(ps -p "$pdca_pid" -o %cpu 2>/dev/null | tail -1 | tr -d ' ')
        echo -e "  ${CYAN}PDCA Guardian CPU${NC}: ${pdca_cpu}%"
    fi

    # メモリ使用率
    local total_mem=$(sysctl -n hw.memsize | awk '{print $1/1024/1024/1024}')
    echo -e "  ${CYAN}総メモリ${NC}: ${total_mem}GB"

    echo ""

    # ============================================================
    # 6. 総合判定
    # ============================================================
    echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${MAGENTA}📋 総合判定${NC}"
    echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

    local pass_rate=$((passed_checks * 100 / total_checks))

    echo -e "  ${CYAN}チェック項目${NC}: ${total_checks}項目"
    echo -e "  ${GREEN}合格${NC}: ${passed_checks}項目"
    echo -e "  ${RED}不合格${NC}: $((total_checks - passed_checks))項目"
    echo -e "  ${YELLOW}合格率${NC}: ${pass_rate}%"
    echo ""

    if [ $pass_rate -ge 80 ]; then
        echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${GREEN}║                                                              ║${NC}"
        echo -e "${GREEN}║   ✅ システムは正常に稼働しています                        ║${NC}"
        echo -e "${GREEN}║                                                              ║${NC}"
        echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
        echo ""

        echo -e "${CYAN}🔗 ダッシュボード:${NC}"
        echo "  • Serena: http://127.0.0.1:24282/dashboard/index.html"
        echo "  • Codex: http://localhost:8765"
        echo ""

        exit 0
    elif [ $pass_rate -ge 50 ]; then
        echo -e "${YELLOW}╔══════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${YELLOW}║                                                              ║${NC}"
        echo -e "${YELLOW}║   ⚠️  一部のシステムに問題があります                       ║${NC}"
        echo -e "${YELLOW}║                                                              ║${NC}"
        echo -e "${YELLOW}╚══════════════════════════════════════════════════════════════╝${NC}"
        echo ""

        echo -e "${CYAN}📝 推奨アクション:${NC}"
        echo "  • システム再起動: ./scripts/unified_claude_startup.sh"
        echo "  • ログ確認: ls -lh ${LOG_DIR}"
        echo ""

        exit 1
    else
        echo -e "${RED}╔══════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${RED}║                                                              ║${NC}"
        echo -e "${RED}║   ❌ 重大な問題が検出されました                            ║${NC}"
        echo -e "${RED}║                                                              ║${NC}"
        echo -e "${RED}╚══════════════════════════════════════════════════════════════╝${NC}"
        echo ""

        echo -e "${CYAN}📝 緊急アクション:${NC}"
        echo "  • すべてのプロセス停止: ./scripts/stop_ai_collaboration.sh"
        echo "  • システム再起動: ./scripts/unified_claude_startup.sh"
        echo "  • エラーログ確認: tail -f ${LOG_DIR}/*.log"
        echo ""

        exit 2
    fi
}

main "$@"
