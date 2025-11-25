#!/bin/bash
#
# ダッシュボード統合起動スクリプト
# エピソードメインデータベース v6 の安定稼働環境を構築
#
# 使用方法:
#   ./scripts/start_dashboard.sh         # 全サービス起動
#   ./scripts/start_dashboard.sh --check # 状態確認のみ
#   ./scripts/start_dashboard.sh --stop  # 全サービス停止
#

set -e

# プロジェクトルート
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

# 設定
HTTP_PORT=8082
API_PORT=8000
PRESERVED_DIR="$PROJECT_ROOT/preserved"
LOG_DIR="$PROJECT_ROOT/logs"
VENV_PYTHON="$PROJECT_ROOT/venv/bin/python"

# 色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ログディレクトリ作成
mkdir -p "$LOG_DIR"

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_status() {
    echo -e "${BLUE}[STATUS]${NC} $1"
}

# プロセスチェック
check_http_server() {
    if pgrep -f "python.*http.server.*$HTTP_PORT" > /dev/null 2>&1; then
        return 0
    fi
    return 1
}

check_api_server() {
    if curl -s "http://localhost:$API_PORT/api/stats/summary" > /dev/null 2>&1; then
        return 0
    fi
    return 1
}

# HTTPサーバー起動
start_http_server() {
    if check_http_server; then
        log_info "HTTPサーバー(port:$HTTP_PORT) は既に起動中"
        return 0
    fi

    log_info "HTTPサーバーを起動中... (port:$HTTP_PORT)"
    cd "$PRESERVED_DIR"
    nohup python3 -m http.server $HTTP_PORT > "$LOG_DIR/http_server.log" 2>&1 &
    HTTP_PID=$!
    cd "$PROJECT_ROOT"

    # 起動確認
    sleep 1
    if check_http_server; then
        log_info "HTTPサーバー起動成功 (PID: $HTTP_PID)"
        return 0
    else
        log_error "HTTPサーバー起動失敗"
        return 1
    fi
}

# ヒートマップデータ生成
generate_heatmap() {
    log_info "ヒートマップデータを生成中..."
    if [ -f "$VENV_PYTHON" ]; then
        "$VENV_PYTHON" "$PROJECT_ROOT/scripts/generate_heatmap_data.py" \
            --output "$PRESERVED_DIR/heatmap_data.json" 2>&1 | tail -10
    else
        python3 "$PROJECT_ROOT/scripts/generate_heatmap_data.py" \
            --output "$PRESERVED_DIR/heatmap_data.json" 2>&1 | tail -10
    fi
}

# 状態確認
check_status() {
    echo ""
    echo "========================================"
    echo "  ダッシュボード環境 ステータス"
    echo "========================================"
    echo ""

    # HTTPサーバー
    if check_http_server; then
        HTTP_PID=$(pgrep -f "python.*http.server.*$HTTP_PORT" | head -1)
        log_status "HTTPサーバー(port:$HTTP_PORT): ${GREEN}稼働中${NC} (PID: $HTTP_PID)"
    else
        log_status "HTTPサーバー(port:$HTTP_PORT): ${RED}停止${NC}"
    fi

    # APIサーバー
    if check_api_server; then
        log_status "APIサーバー(port:$API_PORT): ${GREEN}稼働中${NC}"
    else
        log_status "APIサーバー(port:$API_PORT): ${YELLOW}停止/未確認${NC}"
    fi

    # ヒートマップデータ
    if [ -f "$PRESERVED_DIR/heatmap_data.json" ]; then
        HEATMAP_DATE=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M" "$PRESERVED_DIR/heatmap_data.json")
        log_status "ヒートマップデータ: ${GREEN}存在${NC} (更新: $HEATMAP_DATE)"
    else
        log_status "ヒートマップデータ: ${RED}未生成${NC}"
    fi

    # ダッシュボードURL
    echo ""
    echo "--------------------------------------"
    echo "  ダッシュボードURL"
    echo "--------------------------------------"
    echo "  http://localhost:$HTTP_PORT/episode_database_dashboard_v6.html"
    echo ""
}

# サービス停止
stop_services() {
    log_info "サービスを停止中..."

    # HTTPサーバー停止
    if pgrep -f "python.*http.server.*$HTTP_PORT" > /dev/null 2>&1; then
        pkill -f "python.*http.server.*$HTTP_PORT"
        log_info "HTTPサーバー停止完了"
    else
        log_info "HTTPサーバーは既に停止中"
    fi
}

# メイン処理
main() {
    case "${1:-}" in
        --check|-c)
            check_status
            ;;
        --stop|-s)
            stop_services
            ;;
        --generate|-g)
            generate_heatmap
            ;;
        --help|-h)
            echo "使用方法: $0 [オプション]"
            echo ""
            echo "オプション:"
            echo "  (なし)     全サービス起動"
            echo "  --check    状態確認のみ"
            echo "  --stop     サービス停止"
            echo "  --generate ヒートマップデータ再生成"
            echo "  --help     このヘルプを表示"
            ;;
        *)
            echo ""
            echo "========================================"
            echo "  ダッシュボード統合起動"
            echo "========================================"
            echo ""

            # ヒートマップデータ生成/更新
            if [ ! -f "$PRESERVED_DIR/heatmap_data.json" ]; then
                generate_heatmap
            else
                # 24時間以上経過していたら更新
                HEATMAP_AGE=$(( $(date +%s) - $(stat -f %m "$PRESERVED_DIR/heatmap_data.json") ))
                if [ $HEATMAP_AGE -gt 86400 ]; then
                    log_warn "ヒートマップデータが古いため更新します"
                    generate_heatmap
                fi
            fi

            # HTTPサーバー起動
            start_http_server

            # 状態表示
            check_status

            log_info "ダッシュボード環境の準備完了!"
            echo ""
            echo "ブラウザで以下のURLにアクセスしてください:"
            echo "  http://localhost:$HTTP_PORT/episode_database_dashboard_v6.html"
            echo ""
            ;;
    esac
}

main "$@"
