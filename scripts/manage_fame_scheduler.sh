#!/bin/bash
# Fame Score自動更新スケジューラー管理スクリプト

PLIST_PATH="$HOME/Library/LaunchAgents/com.hourglass.fame-score-update.plist"
LABEL="com.hourglass.fame-score-update"

case "$1" in
    start)
        echo "スケジューラーを開始します..."
        launchctl load "$PLIST_PATH"
        echo "完了: 3日毎に自動更新が実行されます"
        ;;
    stop)
        echo "スケジューラーを停止します..."
        launchctl unload "$PLIST_PATH"
        echo "完了: 自動更新を停止しました"
        ;;
    status)
        if launchctl list | grep -q "$LABEL"; then
            echo "状態: 実行中"
            launchctl list "$LABEL"
        else
            echo "状態: 停止中"
        fi
        ;;
    run-now)
        echo "今すぐ更新を実行します..."
        cd "$(dirname "$0")/.." || exit 1
        python3 scripts/update_fame_scores_incremental.py
        ;;
    dry-run)
        echo "ドライラン（更新対象の確認）..."
        cd "$(dirname "$0")/.." || exit 1
        python3 scripts/update_fame_scores_incremental.py --dry-run
        ;;
    *)
        echo "使用方法: $0 {start|stop|status|run-now|dry-run}"
        echo ""
        echo "  start    - 3日毎の自動更新を開始"
        echo "  stop     - 自動更新を停止"
        echo "  status   - スケジューラーの状態を確認"
        echo "  run-now  - 今すぐ差分更新を実行"
        echo "  dry-run  - 更新対象を確認（実行なし）"
        exit 1
        ;;
esac
