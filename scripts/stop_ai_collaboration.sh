#!/bin/bash
# ============================================================
# 🛑 AI協調分析システム停止スクリプト
# ============================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_DIR="${PROJECT_ROOT}/.pids"

echo -e "${CYAN}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║   🛑 AI協調分析システム停止                             ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}\n"

# プロセス停止関数
stop_process() {
    local name=$1
    local pid_file="${PID_DIR}/${name}.pid"

    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            echo -e "${YELLOW}🛑 ${name} を停止中 (PID: $pid)...${NC}"
            kill "$pid" 2>/dev/null

            # 停止確認（最大5秒待機）
            for i in {1..5}; do
                if ! ps -p "$pid" > /dev/null 2>&1; then
                    echo -e "${GREEN}✅ ${name} 停止完了${NC}"
                    rm -f "$pid_file"
                    return 0
                fi
                sleep 1
            done

            # 強制終了
            echo -e "${YELLOW}⚠️  強制終了を実行...${NC}"
            kill -9 "$pid" 2>/dev/null
            rm -f "$pid_file"
            echo -e "${GREEN}✅ ${name} 強制停止完了${NC}"
        else
            echo -e "${YELLOW}⚠️  ${name} は既に停止しています${NC}"
            rm -f "$pid_file"
        fi
    else
        echo -e "${YELLOW}⚠️  ${name} のPIDファイルが見つかりません${NC}"
    fi
}

# 各サービスを停止
stop_process "Serena MCP Server"
stop_process "Codex MCP Server"
stop_process "自動同期システム"

# 監視プロセスを停止
echo -e "${YELLOW}🛑 リアルタイム監視を停止中...${NC}"
pkill -f "watchdog" 2>/dev/null && echo -e "${GREEN}✅ リアルタイム監視停止完了${NC}" || echo -e "${YELLOW}⚠️  監視プロセスなし${NC}"
rm -f "${PID_DIR}/watchdog.pid"

echo ""
echo -e "${GREEN}✅ すべてのサービスを停止しました${NC}"

exit 0
