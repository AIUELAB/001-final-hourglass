#!/bin/bash
# Phase 2 毎日自動実行スケジューラー管理
#
# 使用方法:
#   ./scripts/manage_phase2_scheduler.sh start   # 開始
#   ./scripts/manage_phase2_scheduler.sh stop    # 停止
#   ./scripts/manage_phase2_scheduler.sh status  # 状態確認
#   ./scripts/manage_phase2_scheduler.sh run     # 手動実行（100件）

PLIST_PATH="$HOME/Library/LaunchAgents/com.hourglass.fame-phase2-daily.plist"
LABEL="com.hourglass.fame-phase2-daily"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

case "$1" in
    start)
        echo "Phase 2 毎日自動実行を開始..."
        launchctl load "$PLIST_PATH" 2>/dev/null
        if launchctl list | grep -q "$LABEL"; then
            echo "✅ 開始しました（毎日 6:00 に100件処理）"
        else
            echo "❌ 開始に失敗しました"
            exit 1
        fi
        ;;
    stop)
        echo "Phase 2 毎日自動実行を停止..."
        launchctl unload "$PLIST_PATH" 2>/dev/null
        if ! launchctl list | grep -q "$LABEL"; then
            echo "✅ 停止しました"
        else
            echo "❌ 停止に失敗しました"
            exit 1
        fi
        ;;
    status)
        echo "=== Phase 2 スケジューラー状態 ==="
        if launchctl list | grep -q "$LABEL"; then
            echo "状態: ✅ 稼働中（毎日 6:00）"
        else
            echo "状態: ⏸️ 停止中"
        fi
        echo ""
        echo "=== キャッシュ状況 ==="
        cd "$PROJECT_DIR"
        sqlite3 data/cache/fame_score.db "
            SELECT
                COUNT(*) as '総人物数',
                COUNT(google_hits) as 'Google検索済み',
                COUNT(*) - COUNT(google_hits) as '残り',
                ROUND(COUNT(google_hits) * 100.0 / COUNT(*), 1) || '%' as 'カバレッジ'
            FROM fame_cache
        " -header -column
        echo ""
        REMAINING=$(sqlite3 data/cache/fame_score.db "SELECT COUNT(*) - COUNT(google_hits) FROM fame_cache")
        DAYS=$((REMAINING / 100 + 1))
        echo "完了予定: 約${DAYS}日後（100件/日）"
        ;;
    run)
        echo "Phase 2 手動実行（100件）..."
        cd "$PROJECT_DIR"
        ./venv/bin/python scripts/update_fame_scores_phase2.py --execute --max-queries 100
        ;;
    *)
        echo "使用方法: $0 {start|stop|status|run}"
        echo ""
        echo "  start  - 毎日自動実行を開始（6:00 AM）"
        echo "  stop   - 毎日自動実行を停止"
        echo "  status - 状態とキャッシュ状況を表示"
        echo "  run    - 今すぐ100件処理"
        exit 1
        ;;
esac
