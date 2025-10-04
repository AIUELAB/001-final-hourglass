#!/bin/bash
# ============================================================
# 🔍 AI協調分析システム状態確認スクリプト
# ============================================================

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_DIR="${PROJECT_ROOT}/.pids"

echo -e "${CYAN}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║   🔍 AI協調分析システム状態確認                         ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}\n"

# プロセス状態確認関数
check_process() {
    local name=$1
    local pid_file="${PID_DIR}/${name}.pid"

    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ ${name}${NC} - 稼働中 (PID: $pid)"
            return 0
        else
            echo -e "${RED}❌ ${name}${NC} - 停止中 (PIDファイルは存在)"
            return 1
        fi
    else
        echo -e "${YELLOW}⚠️  ${name}${NC} - 未起動"
        return 1
    fi
}

# 各サービスの状態確認
echo -e "${CYAN}📊 サービス状態:${NC}"
check_process "Serena MCP Server"
SERENA_STATUS=$?

check_process "Codex MCP Server"
CODEX_STATUS=$?

check_process "自動同期システム"
SYNC_STATUS=$?

# 監視プロセス確認
echo ""
if pgrep -f "watchdog" > /dev/null; then
    echo -e "${GREEN}✅ リアルタイム監視${NC} - 稼働中"
    MONITOR_STATUS=0
else
    echo -e "${YELLOW}⚠️  リアルタイム監視${NC} - 停止中"
    MONITOR_STATUS=1
fi

# ポート確認
echo -e "\n${CYAN}🔌 ポート状態:${NC}"

if lsof -i :8000 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Serena (8000)${NC} - リスニング中"
else
    echo -e "${RED}❌ Serena (8000)${NC} - 未使用"
fi

if lsof -i :8765 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Codex (8765)${NC} - リスニング中"
else
    echo -e "${RED}❌ Codex (8765)${NC} - 未使用"
fi

# ログファイル確認
echo -e "\n${CYAN}📝 ログファイル:${NC}"

if [ -f "${PROJECT_ROOT}/.unified_startup.log" ]; then
    echo -e "${GREEN}✅ 起動ログ${NC} - $(wc -l < "${PROJECT_ROOT}/.unified_startup.log") 行"
    echo "   最終更新: $(stat -f "%Sm" "${PROJECT_ROOT}/.unified_startup.log")"
else
    echo -e "${YELLOW}⚠️  起動ログ${NC} - ファイルなし"
fi

if [ -f "${PROJECT_ROOT}/sync_log.json" ]; then
    echo -e "${GREEN}✅ 同期ログ${NC} - 存在"
else
    echo -e "${YELLOW}⚠️  同期ログ${NC} - ファイルなし"
fi

# 総合判定
echo -e "\n${CYAN}📋 総合判定:${NC}"
if [ $SERENA_STATUS -eq 0 ] && [ $CODEX_STATUS -eq 0 ]; then
    echo -e "${GREEN}✅ AI協調分析システムは正常に稼働しています${NC}"
    exit 0
else
    echo -e "${YELLOW}⚠️  一部のサービスが停止しています${NC}"
    echo -e "${YELLOW}  → 再起動: ./scripts/unified_startup.sh${NC}"
    exit 1
fi
