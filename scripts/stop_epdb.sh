#!/bin/bash
# エピソードデータベースダッシュボード（EPDB v8）停止スクリプト
#
# 用途: start_epdb.shで起動したサーバーを停止
# 使い方: ./scripts/stop_epdb.sh

set -e

# カラー定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  EPDB v8 停止${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# PIDファイルから停止
if [ -f "$PROJECT_ROOT/.epdb_api.pid" ]; then
    API_PID=$(cat "$PROJECT_ROOT/.epdb_api.pid")
    if kill -0 $API_PID 2>/dev/null; then
        echo -e "${YELLOW}→${NC} APIサーバー停止中（PID: $API_PID）..."
        kill $API_PID
        echo -e "${GREEN}✓${NC} APIサーバー停止完了"
    else
        echo -e "${YELLOW}⚠${NC}  APIサーバーは既に停止しています"
    fi
    rm -f "$PROJECT_ROOT/.epdb_api.pid"
else
    echo -e "${YELLOW}⚠${NC}  APIサーバーのPIDファイルが見つかりません"
fi

if [ -f "$PROJECT_ROOT/.epdb_http.pid" ]; then
    HTTP_PID=$(cat "$PROJECT_ROOT/.epdb_http.pid")
    if kill -0 $HTTP_PID 2>/dev/null; then
        echo -e "${YELLOW}→${NC} HTTPサーバー停止中（PID: $HTTP_PID）..."
        kill $HTTP_PID
        echo -e "${GREEN}✓${NC} HTTPサーバー停止完了"
    else
        echo -e "${YELLOW}⚠${NC}  HTTPサーバーは既に停止しています"
    fi
    rm -f "$PROJECT_ROOT/.epdb_http.pid"
else
    echo -e "${YELLOW}⚠${NC}  HTTPサーバーのPIDファイルが見つかりません"
fi

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  ✓ EPDB v8 停止完了${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
