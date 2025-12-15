#!/bin/bash
# エピソードデータベースダッシュボード（EPDB v8）統合起動スクリプト
#
# 用途: APIサーバー（port 8000）とHTTPサーバー（port 8082）を同時に起動
# 使い方: ./scripts/start_epdb.sh

set -e  # エラーで停止

# カラー定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
API_PORT=8000
HTTP_PORT=8082

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  EPDB v8 統合起動${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 環境チェック
echo -e "${YELLOW}[1/4]${NC} 環境をチェック中..."

if [ ! -d "$BACKEND_DIR" ]; then
    echo -e "${RED}✗${NC} backendディレクトリが見つかりません"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗${NC} python3 がインストールされていません"
    exit 1
fi

echo -e "${GREEN}✓${NC} 環境チェック完了"
echo ""

# ポート競合チェック（API）
echo -e "${YELLOW}[2/4]${NC} ポート競合をチェック中..."

if lsof -Pi :$API_PORT -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${YELLOW}⚠${NC}  ポート $API_PORT は既に使用されています"
    PID=$(lsof -Pi :$API_PORT -sTCP:LISTEN -t)
    echo "     プロセスを停止してから再起動します..."
    kill $PID 2>/dev/null || kill -9 $PID 2>/dev/null
    sleep 2
fi

if lsof -Pi :$HTTP_PORT -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${YELLOW}⚠${NC}  ポート $HTTP_PORT は既に使用されています"
    PID=$(lsof -Pi :$HTTP_PORT -sTCP:LISTEN -t)
    echo "     プロセスを停止してから再起動します..."
    kill $PID 2>/dev/null || kill -9 $PID 2>/dev/null
    sleep 2
fi

echo -e "${GREEN}✓${NC} ポート競合チェック完了"
echo ""

# APIサーバー起動
echo -e "${YELLOW}[3/4]${NC} APIサーバー起動中（port $API_PORT）..."

cd "$BACKEND_DIR"
nohup python3 -m uvicorn app.main:app --reload --port $API_PORT > "$PROJECT_ROOT/epdb_api.log" 2>&1 &
API_PID=$!

sleep 3

# ヘルスチェック
if curl -s http://localhost:$API_PORT/api/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} APIサーバー起動完了（PID: $API_PID）"
else
    echo -e "${RED}✗${NC} APIサーバーの起動に失敗しました"
    echo "     ログを確認: $PROJECT_ROOT/epdb_api.log"
    exit 1
fi

echo ""

# HTTPサーバー起動
echo -e "${YELLOW}[4/4]${NC} HTTPサーバー起動中（port $HTTP_PORT）..."

cd "$PROJECT_ROOT"
nohup python3 -m http.server $HTTP_PORT > "$PROJECT_ROOT/epdb_http.log" 2>&1 &
HTTP_PID=$!

sleep 2

echo -e "${GREEN}✓${NC} HTTPサーバー起動完了（PID: $HTTP_PID）"
echo ""

# 起動完了
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  ✓ EPDB v8 起動完了！${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}🌐 ブラウザでアクセス:${NC}"
echo -e "   http://localhost:$HTTP_PORT/preserved/episode_database_dashboard_v8.html"
echo ""
echo -e "${BLUE}📊 APIサーバー:${NC}"
echo -e "   http://localhost:$API_PORT/api/stats/summary"
echo ""
echo -e "${BLUE}📝 ログファイル:${NC}"
echo -e "   API: $PROJECT_ROOT/epdb_api.log"
echo -e "   HTTP: $PROJECT_ROOT/epdb_http.log"
echo ""
echo -e "${YELLOW}⚠️  停止するには:${NC} ./scripts/stop_epdb.sh"
echo ""

# プロセス情報を保存
echo "$API_PID" > "$PROJECT_ROOT/.epdb_api.pid"
echo "$HTTP_PID" > "$PROJECT_ROOT/.epdb_http.pid"

# macOSの場合、ブラウザを開くか確認
if [[ "$OSTYPE" == "darwin"* ]]; then
    read -p "ブラウザを開きますか？ [y/N]: " open_browser
    if [[ "$open_browser" =~ ^[Yy]$ ]]; then
        open "http://localhost:$HTTP_PORT/preserved/episode_database_dashboard_v8.html"
    fi
fi
