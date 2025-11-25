#!/bin/bash
#
# エピソードメインデータベース v3 起動スクリプト
#
# 使い方: ./start-episode-db.sh
#

set -e  # エラーで停止

# カラー定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# プロジェクトルート
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
BACKEND_LOG="$PROJECT_ROOT/backend.log"
PORT=8000

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  エピソードメインデータベース v3 起動${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# ステップ1: 環境チェック
echo -e "${YELLOW}[1/5]${NC} 環境をチェック中..."

# プロジェクトルート確認
if [ ! -d "$PROJECT_ROOT" ]; then
    echo -e "${RED}✗${NC} プロジェクトルートが見つかりません: $PROJECT_ROOT"
    exit 1
fi

# バックエンドディレクトリ確認
if [ ! -d "$BACKEND_DIR" ]; then
    echo -e "${RED}✗${NC} backendディレクトリが見つかりません"
    exit 1
fi

# Python確認
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗${NC} python3 がインストールされていません"
    exit 1
fi

# CSVファイル確認
if [ ! -f "$PROJECT_ROOT/MASTER_EPISODES_CURRENT.csv" ]; then
    echo -e "${YELLOW}⚠${NC}  MASTER_EPISODES_CURRENT.csv が見つかりません"
    echo "     データベースは空の状態で起動します"
fi

echo -e "${GREEN}✓${NC} 環境チェック完了"
echo ""

# ステップ2: ポート競合チェック
echo -e "${YELLOW}[2/5]${NC} ポート $PORT の使用状況を確認中..."

if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${YELLOW}⚠${NC}  ポート $PORT は既に使用されています"

    # プロセス情報を取得
    PID=$(lsof -Pi :$PORT -sTCP:LISTEN -t)
    PROCESS_INFO=$(ps -p $PID -o comm= 2>/dev/null || echo "不明なプロセス")

    echo "     プロセス: $PROCESS_INFO (PID: $PID)"
    echo ""
    echo -e "     ${BLUE}選択肢:${NC}"
    echo "     1) 既存プロセスを停止して再起動"
    echo "     2) そのまま継続（既に起動済みの場合）"
    echo "     3) キャンセル"
    echo ""
    read -p "     選択してください [1/2/3]: " choice

    case $choice in
        1)
            echo -e "${YELLOW}→${NC} プロセスを停止中..."
            kill $PID 2>/dev/null || kill -9 $PID 2>/dev/null
            sleep 2
            echo -e "${GREEN}✓${NC} プロセスを停止しました"
            ;;
        2)
            echo -e "${GREEN}✓${NC} 既存のサーバーを使用します"
            echo ""
            echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            echo -e "${GREEN}  ✓ サーバーは既に起動しています${NC}"
            echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            echo ""
            echo -e "${BLUE}🌐 ブラウザでアクセス:${NC} http://localhost:$PORT/"
            echo ""

            # macOSの場合、ブラウザを開く
            if [[ "$OSTYPE" == "darwin"* ]]; then
                read -p "ブラウザを開きますか？ [y/N]: " open_browser
                if [[ "$open_browser" =~ ^[Yy]$ ]]; then
                    open "http://localhost:$PORT/"
                fi
            fi

            exit 0
            ;;
        3)
            echo -e "${YELLOW}→${NC} キャンセルしました"
            exit 0
            ;;
        *)
            echo -e "${RED}✗${NC} 無効な選択です"
            exit 1
            ;;
    esac
else
    echo -e "${GREEN}✓${NC} ポート $PORT は使用可能です"
fi
echo ""

# ステップ3: 依存関係チェック
echo -e "${YELLOW}[3/5]${NC} Python依存関係を確認中..."

cd "$BACKEND_DIR"

# FastAPIとuvicornがインストールされているか確認
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo -e "${YELLOW}⚠${NC}  FastAPIがインストールされていません"
    echo "     インストールを実行中..."
    pip install -q fastapi uvicorn[standard] 2>&1 | tail -n 5
fi

if ! python3 -c "import uvicorn" 2>/dev/null; then
    echo -e "${YELLOW}⚠${NC}  Uvicornがインストールされていません"
    echo "     インストールを実行中..."
    pip install -q uvicorn[standard] 2>&1 | tail -n 5
fi

echo -e "${GREEN}✓${NC} 依存関係チェック完了"
echo ""

# ステップ4: バックエンド起動
echo -e "${YELLOW}[4/5]${NC} バックエンドを起動中..."

# 古いログファイルをバックアップ
if [ -f "$BACKEND_LOG" ]; then
    mv "$BACKEND_LOG" "$BACKEND_LOG.old" 2>/dev/null || true
fi

# バックグラウンドで起動
cd "$BACKEND_DIR"
nohup python3 -m uvicorn app.main:app --reload --port $PORT > "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!

echo -e "${GREEN}✓${NC} バックエンドを起動しました (PID: $BACKEND_PID)"
echo "     ログ: $BACKEND_LOG"
echo ""

# ステップ5: 起動確認（ヘルスチェック）
echo -e "${YELLOW}[5/5]${NC} サーバーの起動を確認中..."

MAX_WAIT=30
WAIT_COUNT=0

while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    if curl -s http://localhost:$PORT/api/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} サーバーが正常に起動しました"
        break
    fi

    # プロセスが死んでいないか確認
    if ! kill -0 $BACKEND_PID 2>/dev/null; then
        echo -e "${RED}✗${NC} サーバーの起動に失敗しました"
        echo ""
        echo "最後の10行のログ:"
        tail -n 10 "$BACKEND_LOG"
        exit 1
    fi

    sleep 1
    WAIT_COUNT=$((WAIT_COUNT + 1))
    echo -n "."
done
echo ""

if [ $WAIT_COUNT -ge $MAX_WAIT ]; then
    echo -e "${RED}✗${NC} サーバーの起動タイムアウト（${MAX_WAIT}秒）"
    echo ""
    echo "ログを確認してください: $BACKEND_LOG"
    exit 1
fi

# 起動成功
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  ✓ エピソードメインデータベース v3 起動完了！${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}🌐 アクセスURL:${NC}"
echo "   ダッシュボード v3: http://localhost:$PORT/"
echo "   ダッシュボード v2: http://localhost:$PORT/v2"
echo "   API仕様書:         http://localhost:$PORT/docs"
echo ""
echo -e "${BLUE}📋 管理コマンド:${NC}"
echo "   ログ表示:   tail -f $BACKEND_LOG"
echo "   停止:       kill $BACKEND_PID"
echo ""

# macOSの場合、ブラウザを開く提案
if [[ "$OSTYPE" == "darwin"* ]]; then
    read -p "ブラウザでダッシュボードを開きますか？ [Y/n]: " open_browser
    if [[ ! "$open_browser" =~ ^[Nn]$ ]]; then
        open "http://localhost:$PORT/"
        echo -e "${GREEN}✓${NC} ブラウザを開きました"
    fi
fi

echo ""
echo -e "${YELLOW}💡 ヒント:${NC} Ctrl+C でこのスクリプトを終了しても、サーバーは稼働し続けます"
echo ""
