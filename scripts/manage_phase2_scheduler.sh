#!/bin/bash
# Phase 2 Google検索スケジューラ管理
#
# 使用方法:
#   ./scripts/manage_phase2_scheduler.sh start    # 自動実行開始
#   ./scripts/manage_phase2_scheduler.sh stop     # 自動実行停止
#   ./scripts/manage_phase2_scheduler.sh status   # 状態確認
#   ./scripts/manage_phase2_scheduler.sh run      # 手動実行（クォータ上限まで）
#   ./scripts/manage_phase2_scheduler.sh run 10   # 手動実行（10件のみ）

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

PLIST_NAME="com.aiuelab.hourglass.phase2"
PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_NAME}.plist"
LOG_DIR="$PROJECT_ROOT/src/reports/logs"

# launchd plist を生成
create_plist() {
    mkdir -p "$LOG_DIR"
    cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${PLIST_NAME}</string>

    <key>ProgramArguments</key>
    <array>
        <string>${PROJECT_ROOT}/venv/bin/python</string>
        <string>${PROJECT_ROOT}/scripts/update_fame_scores_phase2.py</string>
        <string>--execute</string>
        <string>--auto</string>
    </array>

    <key>WorkingDirectory</key>
    <string>${PROJECT_ROOT}</string>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>3</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>

    <key>StandardOutPath</key>
    <string>${LOG_DIR}/phase2_scheduler.log</string>

    <key>StandardErrorPath</key>
    <string>${LOG_DIR}/phase2_scheduler_error.log</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin</string>
        <key>PYTHONPATH</key>
        <string>${PROJECT_ROOT}</string>
    </dict>
</dict>
</plist>
EOF
    echo "plist作成: $PLIST_PATH"
}

case "$1" in
    start)
        echo "=== Phase 2 スケジューラ開始 ==="

        # ログディレクトリ作成
        mkdir -p "$LOG_DIR"

        # plistを作成
        create_plist

        # 既存のジョブを停止（エラー無視）
        launchctl unload "$PLIST_PATH" 2>/dev/null || true

        # ジョブを開始
        launchctl load "$PLIST_PATH"

        echo "スケジューラを開始しました"
        echo "  毎日 3:00 に自動実行されます"
        echo "  ログ: $LOG_DIR/phase2_scheduler.log"
        ;;

    stop)
        echo "=== Phase 2 スケジューラ停止 ==="

        if [ -f "$PLIST_PATH" ]; then
            launchctl unload "$PLIST_PATH" 2>/dev/null || true
            rm -f "$PLIST_PATH"
            echo "スケジューラを停止しました"
        else
            echo "スケジューラは既に停止しています"
        fi
        ;;

    status)
        echo "=== Phase 2 スケジューラ状態 ==="

        if launchctl list 2>/dev/null | grep -q "$PLIST_NAME"; then
            echo "スケジューラ: 実行中（毎日 3:00）"
        else
            echo "スケジューラ: 停止中"
        fi

        echo ""
        echo "=== クォータ・キャッシュ状況 ==="
        cd "$PROJECT_ROOT"
        "$PROJECT_ROOT/venv/bin/python" scripts/check_phase2_status.py 2>/dev/null || \
            sqlite3 data/cache/fame_score.db "
                SELECT
                    COUNT(*) as '総人物数',
                    COUNT(google_hits) as 'Google検索済み',
                    COUNT(*) - COUNT(google_hits) as '残り'
                FROM fame_cache
            " -header -column

        echo ""
        # 最新ログの最後5行
        if [ -f "$LOG_DIR/phase2_scheduler.log" ]; then
            echo "=== 最新ログ（5行） ==="
            tail -5 "$LOG_DIR/phase2_scheduler.log"
        fi
        ;;

    run)
        echo "=== Phase 2 手動実行 ==="
        cd "$PROJECT_ROOT"
        if [ -n "$2" ]; then
            echo "最大クエリ数: $2"
            "$PROJECT_ROOT/venv/bin/python" scripts/update_fame_scores_phase2.py --execute --max-queries "$2"
        else
            echo "クォータ上限まで実行"
            "$PROJECT_ROOT/venv/bin/python" scripts/update_fame_scores_phase2.py --execute
        fi
        ;;

    *)
        echo "Phase 2 Google検索スケジューラ管理"
        echo ""
        echo "使用方法:"
        echo "  $0 start      自動実行開始（毎日3:00）"
        echo "  $0 stop       自動実行停止"
        echo "  $0 status     状態確認"
        echo "  $0 run        手動実行（クォータ上限まで）"
        echo "  $0 run 10     手動実行（10件のみ）"
        ;;
esac
