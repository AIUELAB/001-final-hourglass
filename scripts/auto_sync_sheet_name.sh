#!/bin/bash

# Google Sheetsスプレッドシート名自動同期スクリプト
# バックグラウンドで実行して、CSVファイル名の変更を監視

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "🔍 Ultra Think CSV ファイル名監視システム"
echo "================================"
echo ""

# Pythonスクリプトの存在確認
if [ ! -f "auto_sheet_name_sync.py" ]; then
    echo "❌ auto_sheet_name_sync.py が見つかりません"
    exit 1
fi

# 引数処理
case "$1" in
    start)
        echo "▶️  監視を開始します..."
        nohup python3 auto_sheet_name_sync.py --monitor > sheet_sync.log 2>&1 &
        echo $! > sheet_sync.pid
        echo "✅ バックグラウンドで監視を開始しました (PID: $(cat sheet_sync.pid))"
        echo "📝 ログファイル: sheet_sync.log"
        ;;

    stop)
        if [ -f sheet_sync.pid ]; then
            PID=$(cat sheet_sync.pid)
            kill $PID 2>/dev/null
            rm sheet_sync.pid
            echo "⏹️  監視を停止しました (PID: $PID)"
        else
            echo "⚠️  実行中の監視プロセスが見つかりません"
        fi
        ;;

    status)
        if [ -f sheet_sync.pid ]; then
            PID=$(cat sheet_sync.pid)
            if ps -p $PID > /dev/null 2>&1; then
                echo "✅ 監視中 (PID: $PID)"
                echo ""
                echo "最近のログ:"
                tail -n 5 sheet_sync.log 2>/dev/null || echo "ログなし"
            else
                echo "❌ プロセスが停止しています"
                rm sheet_sync.pid
            fi
        else
            echo "⚠️  監視は実行されていません"
        fi
        ;;

    sync)
        echo "🔄 手動同期を実行します..."
        python3 auto_sheet_name_sync.py --manual
        ;;

    monitor)
        echo "📊 フォアグラウンドで監視を開始します (Ctrl+C で停止)"
        python3 auto_sheet_name_sync.py --monitor
        ;;

    *)
        echo "使用方法: $0 {start|stop|status|sync|monitor}"
        echo ""
        echo "コマンド:"
        echo "  start   - バックグラウンドで監視を開始"
        echo "  stop    - 監視を停止"
        echo "  status  - 監視状態を確認"
        echo "  sync    - 手動で一度だけ同期"
        echo "  monitor - フォアグラウンドで監視（デバッグ用）"
        echo ""
        echo "例:"
        echo "  $0 start   # 監視を開始"
        echo "  $0 sync    # 今すぐ同期"
        exit 1
        ;;
esac
