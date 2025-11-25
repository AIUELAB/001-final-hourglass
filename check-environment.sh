#!/bin/bash
#
# エピソードメインデータベース v3 環境チェックスクリプト
#
# 使い方: ./check-environment.sh
#

# カラー定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# プロジェクトルート
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
PORT=8000

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  環境チェック - エピソードメインデータベース v3${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

ERRORS=0
WARNINGS=0

# チェック1: Pythonバージョン
echo -e "${YELLOW}[1/10]${NC} Python環境を確認中..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    echo -e "  ${GREEN}✓${NC} Python: $PYTHON_VERSION"
else
    echo -e "  ${RED}✗${NC} Python3がインストールされていません"
    ERRORS=$((ERRORS + 1))
fi

# チェック2: pip
echo -e "${YELLOW}[2/10]${NC} pipを確認中..."
if command -v pip &> /dev/null || command -v pip3 &> /dev/null; then
    PIP_VERSION=$(pip3 --version 2>&1 | awk '{print $2}')
    echo -e "  ${GREEN}✓${NC} pip: $PIP_VERSION"
else
    echo -e "  ${RED}✗${NC} pipがインストールされていません"
    ERRORS=$((ERRORS + 1))
fi

# チェック3: FastAPI
echo -e "${YELLOW}[3/10]${NC} FastAPIを確認中..."
if python3 -c "import fastapi" 2>/dev/null; then
    FASTAPI_VERSION=$(python3 -c "import fastapi; print(fastapi.__version__)" 2>/dev/null)
    echo -e "  ${GREEN}✓${NC} FastAPI: $FASTAPI_VERSION"
else
    echo -e "  ${YELLOW}⚠${NC}  FastAPIがインストールされていません"
    echo "      インストール: pip install fastapi"
    WARNINGS=$((WARNINGS + 1))
fi

# チェック4: Uvicorn
echo -e "${YELLOW}[4/10]${NC} Uvicornを確認中..."
if python3 -c "import uvicorn" 2>/dev/null; then
    UVICORN_VERSION=$(python3 -c "import uvicorn; print(uvicorn.__version__)" 2>/dev/null)
    echo -e "  ${GREEN}✓${NC} Uvicorn: $UVICORN_VERSION"
else
    echo -e "  ${YELLOW}⚠${NC}  Uvicornがインストールされていません"
    echo "      インストール: pip install uvicorn[standard]"
    WARNINGS=$((WARNINGS + 1))
fi

# チェック5: バックエンドディレクトリ
echo -e "${YELLOW}[5/10]${NC} バックエンドディレクトリを確認中..."
if [ -d "$BACKEND_DIR" ]; then
    echo -e "  ${GREEN}✓${NC} バックエンド: $BACKEND_DIR"

    # main.pyの存在確認
    if [ -f "$BACKEND_DIR/app/main.py" ]; then
        echo -e "  ${GREEN}✓${NC} app/main.py: 存在"
    else
        echo -e "  ${RED}✗${NC} app/main.py: 見つかりません"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo -e "  ${RED}✗${NC} backendディレクトリが見つかりません"
    ERRORS=$((ERRORS + 1))
fi

# チェック6: CSVデータファイル
echo -e "${YELLOW}[6/10]${NC} データファイルを確認中..."
if [ -f "$PROJECT_ROOT/MASTER_EPISODES_CURRENT.csv" ]; then
    FILE_SIZE=$(ls -lh "$PROJECT_ROOT/MASTER_EPISODES_CURRENT.csv" | awk '{print $5}')
    echo -e "  ${GREEN}✓${NC} MASTER_EPISODES_CURRENT.csv: $FILE_SIZE"
else
    echo -e "  ${YELLOW}⚠${NC}  MASTER_EPISODES_CURRENT.csv: 見つかりません"
    echo "      データベースは空の状態で起動します"
    WARNINGS=$((WARNINGS + 1))
fi

# チェック7: データベースファイル
echo -e "${YELLOW}[7/10]${NC} データベースを確認中..."
if [ -f "$BACKEND_DIR/characters.db" ]; then
    DB_SIZE=$(ls -lh "$BACKEND_DIR/characters.db" | awk '{print $5}')
    echo -e "  ${GREEN}✓${NC} characters.db: $DB_SIZE"

    # レコード数確認（sqlite3が利用可能な場合）
    if command -v sqlite3 &> /dev/null; then
        RECORD_COUNT=$(sqlite3 "$BACKEND_DIR/characters.db" "SELECT COUNT(*) FROM characters;" 2>/dev/null || echo "0")
        echo -e "  ${GREEN}✓${NC} レコード数: $RECORD_COUNT件"
    fi
else
    echo -e "  ${YELLOW}⚠${NC}  characters.db: 見つかりません"
    echo "      初回起動時に自動作成されます"
    WARNINGS=$((WARNINGS + 1))
fi

# チェック8: ポート使用状況
echo -e "${YELLOW}[8/10]${NC} ポート $PORT の使用状況を確認中..."
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    PID=$(lsof -Pi :$PORT -sTCP:LISTEN -t)
    PROCESS=$(ps -p $PID -o comm= 2>/dev/null || echo "不明")
    echo -e "  ${YELLOW}⚠${NC}  ポート $PORT は使用中"
    echo "      プロセス: $PROCESS (PID: $PID)"
    echo "      停止: kill $PID"
    WARNINGS=$((WARNINGS + 1))
else
    echo -e "  ${GREEN}✓${NC} ポート $PORT は使用可能"
fi

# チェック9: ダッシュボードファイル
echo -e "${YELLOW}[9/10]${NC} ダッシュボードファイルを確認中..."
if [ -f "$PROJECT_ROOT/preserved/episode_database_dashboard_v3.html" ]; then
    V3_SIZE=$(ls -lh "$PROJECT_ROOT/preserved/episode_database_dashboard_v3.html" | awk '{print $5}')
    echo -e "  ${GREEN}✓${NC} dashboard_v3.html: $V3_SIZE"
else
    echo -e "  ${RED}✗${NC} dashboard_v3.html: 見つかりません"
    ERRORS=$((ERRORS + 1))
fi

if [ -f "$PROJECT_ROOT/preserved/episode_database_dashboard_v2.html" ]; then
    V2_SIZE=$(ls -lh "$PROJECT_ROOT/preserved/episode_database_dashboard_v2.html" | awk '{print $5}')
    echo -e "  ${GREEN}✓${NC} dashboard_v2.html: $V2_SIZE"
fi

# チェック10: Node.js（オプション）
echo -e "${YELLOW}[10/10]${NC} Node.js環境を確認中（オプション）..."
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version 2>&1)
    NPM_VERSION=$(npm --version 2>&1)
    echo -e "  ${GREEN}✓${NC} Node.js: $NODE_VERSION"
    echo -e "  ${GREEN}✓${NC} npm: $NPM_VERSION"

    # フロントエンドディレクトリ
    if [ -d "$FRONTEND_DIR" ]; then
        echo -e "  ${GREEN}✓${NC} frontend/: 存在"
        if [ -d "$FRONTEND_DIR/node_modules" ]; then
            echo -e "  ${GREEN}✓${NC} node_modules/: インストール済み"
        else
            echo -e "  ${YELLOW}⚠${NC}  node_modules/: 未インストール"
            echo "      インストール: cd frontend && npm install"
            WARNINGS=$((WARNINGS + 1))
        fi
    fi
else
    echo -e "  ${BLUE}○${NC} Node.js: 未インストール（ダッシュボードv3では不要）"
fi

# サマリー
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  チェック完了${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✓ すべてのチェックに合格しました！${NC}"
    echo ""
    echo -e "エピソードメインデータベース v3 を起動できます："
    echo -e "  ${BLUE}./start-episode-db.sh${NC}"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠ $WARNINGS 個の警告がありますが、起動可能です${NC}"
    echo ""
    echo -e "エピソードメインデータベース v3 を起動できます："
    echo -e "  ${BLUE}./start-episode-db.sh${NC}"
    exit 0
else
    echo -e "${RED}✗ $ERRORS 個のエラーがあります${NC}"
    if [ $WARNINGS -gt 0 ]; then
        echo -e "${YELLOW}⚠ $WARNINGS 個の警告があります${NC}"
    fi
    echo ""
    echo -e "エラーを修正してから起動してください"
    echo ""
    echo -e "${BLUE}推奨アクション:${NC}"
    if ! command -v python3 &> /dev/null; then
        echo "  1. Python3をインストール: brew install python3"
    fi
    if ! python3 -c "import fastapi" 2>/dev/null || ! python3 -c "import uvicorn" 2>/dev/null; then
        echo "  2. 依存関係をインストール: cd backend && pip install -r requirements.txt"
    fi
    exit 1
fi
