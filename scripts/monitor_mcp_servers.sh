#!/bin/bash

# MCP Servers モニタリングスクリプト
# サーバーの状態を継続的に監視

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ヘッダー表示
show_header() {
    clear
    echo "======================================="
    echo "    MCP Server Monitor v1.0"
    echo "    $(date '+%Y-%m-%d %H:%M:%S')"
    echo "======================================="
    echo ""
}

# プロセス確認
check_process() {
    local name=$1
    local pattern=$2

    if pgrep -f "$pattern" > /dev/null; then
        echo -e "${GREEN}✅ $name: Running${NC}"
        return 0
    else
        echo -e "${RED}❌ $name: Stopped${NC}"
        return 1
    fi
}

# ポート確認
check_port() {
    local name=$1
    local port=$2

    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; then
        echo -e "${GREEN}✅ $name (Port $port): Open${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️  $name (Port $port): Closed${NC}"
        return 1
    fi
}

# HTTPヘルスチェック
check_http() {
    local name=$1
    local url=$2

    if curl -s -f -o /dev/null "$url" 2>/dev/null; then
        echo -e "${GREEN}✅ $name Health: OK${NC}"
        return 0
    else
        echo -e "${RED}❌ $name Health: Failed${NC}"
        return 1
    fi
}

# メインループ
while true; do
    show_header

    echo "🔍 Process Status:"
    echo "-------------------"
    check_process "MCP Manager" "mcp_management_system.py"
    check_process "Serena MCP" "serena-mcp-server"
    check_process "Codex MCP" "codex_mcp_server"
    check_process "Memory MCP" "@modelcontextprotocol/server-memory"
    check_process "Sequential MCP" "@modelcontextprotocol/server-sequential"

    echo ""
    echo "🌐 Port Status:"
    echo "-------------------"
    check_port "Serena" 8000
    check_port "Codex" 8765

    echo ""
    echo "💊 Health Checks:"
    echo "-------------------"
    check_http "Codex API" "http://localhost:8765/health"

    echo ""
    echo "📊 Summary:"
    echo "-------------------"

    # カウント
    running_count=0
    total_count=5

    pgrep -f "mcp_management_system.py" > /dev/null && ((running_count++))
    pgrep -f "serena-mcp-server" > /dev/null && ((running_count++))
    pgrep -f "codex_mcp_server" > /dev/null && ((running_count++))
    pgrep -f "@modelcontextprotocol/server-memory" > /dev/null && ((running_count++))
    pgrep -f "@modelcontextprotocol/server-sequential" > /dev/null && ((running_count++))

    echo "Active Servers: $running_count/$total_count"

    if [ $running_count -eq $total_count ]; then
        echo -e "${GREEN}System Status: All servers running${NC}"
    elif [ $running_count -ge 3 ]; then
        echo -e "${YELLOW}System Status: Partially operational${NC}"
    else
        echo -e "${RED}System Status: Critical - Multiple servers down${NC}"
    fi

    echo ""
    echo "-------------------"
    echo "Press Ctrl+C to exit"
    echo "Refreshing in 10 seconds..."

    sleep 10
done