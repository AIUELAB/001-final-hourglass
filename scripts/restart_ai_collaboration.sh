#!/bin/bash
# ============================================================
# 🔄 AI協調分析システム再起動スクリプト
# ============================================================

CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${CYAN}🔄 AI協調分析システムを再起動中...${NC}\n"

# 停止
"$SCRIPT_DIR/stop_ai_collaboration.sh"

# 3秒待機
echo -e "\n⏳ 待機中 (3秒)..."
sleep 3

# 起動
"$SCRIPT_DIR/unified_startup.sh"

exit 0
