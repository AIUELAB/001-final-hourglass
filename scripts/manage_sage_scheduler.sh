#!/bin/bash
# SAGE エピソード生成スケジューラ管理 (Smart Adaptive Generation Engine)
#
# 使用方法:
#   ./scripts/manage_sage_scheduler.sh start    # 自動実行開始（毎日4:00）
#   ./scripts/manage_sage_scheduler.sh stop     # 自動実行停止
#   ./scripts/manage_sage_scheduler.sh status   # 状態確認
#   ./scripts/manage_sage_scheduler.sh run      # 手動実行（10件）
#   ./scripts/manage_sage_scheduler.sh run 5    # 手動実行（5件）
#   ./scripts/manage_sage_scheduler.sh test     # モックテスト（API不要）

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

PLIST_NAME="com.aiuelab.hourglass.sage"
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
        <string>${PROJECT_ROOT}/scripts/sage/cli.py</string>
        <string>--strategy</string>
        <string>epgen_first</string>
        <string>--target</string>
        <string>10</string>
        <string>--execute</string>
    </array>

    <key>WorkingDirectory</key>
    <string>${PROJECT_ROOT}</string>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>4</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>

    <key>StandardOutPath</key>
    <string>${LOG_DIR}/sage_scheduler.log</string>

    <key>StandardErrorPath</key>
    <string>${LOG_DIR}/sage_scheduler_error.log</string>

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

# ログローテーション
rotate_logs() {
    local log_file="$1"
    local max_size=10485760  # 10MB

    if [ -f "$log_file" ]; then
        local size=$(stat -f%z "$log_file" 2>/dev/null || echo 0)
        if [ "$size" -gt "$max_size" ]; then
            local timestamp=$(date +%Y%m%d_%H%M%S)
            mv "$log_file" "${log_file%.log}_${timestamp}.log"
            echo "ログローテーション: ${log_file%.log}_${timestamp}.log"
        fi
    fi
}

# 古いログを削除（30日以上）
cleanup_old_logs() {
    find "$LOG_DIR" -name "sage_*.log" -mtime +30 -delete 2>/dev/null || true
    find "$LOG_DIR" -name "run_*.json" -mtime +30 -delete 2>/dev/null || true
    find "$LOG_DIR" -name "diff_*.json" -mtime +30 -delete 2>/dev/null || true
}

case "$1" in
    start)
        echo "=== SAGE 生成スケジューラ開始 ==="

        # ログディレクトリ作成
        mkdir -p "$LOG_DIR"

        # plistを作成
        create_plist

        # 既存のジョブを停止（エラー無視）
        launchctl unload "$PLIST_PATH" 2>/dev/null || true

        # ジョブを開始
        launchctl load "$PLIST_PATH"

        echo "スケジューラを開始しました"
        echo "  毎日 4:00 に自動実行されます"
        echo "  戦略: epgen_first"
        echo "  目標: 10件/日"
        echo "  ログ: $LOG_DIR/sage_scheduler.log"
        ;;

    stop)
        echo "=== SAGE 生成スケジューラ停止 ==="

        if [ -f "$PLIST_PATH" ]; then
            launchctl unload "$PLIST_PATH" 2>/dev/null || true
            rm -f "$PLIST_PATH"
            echo "スケジューラを停止しました"
        else
            echo "スケジューラは既に停止しています"
        fi
        ;;

    status)
        echo "=== SAGE 生成スケジューラ状態 ==="

        if launchctl list 2>/dev/null | grep -q "$PLIST_NAME"; then
            echo "スケジューラ: 実行中（毎日 4:00）"
        else
            echo "スケジューラ: 停止中"
        fi

        echo ""
        echo "=== 最近の実行結果 ==="
        cd "$PROJECT_ROOT"

        # 最新の実行ログを表示
        latest_run=$(ls -t "$LOG_DIR"/run_*.json 2>/dev/null | head -1)
        if [ -n "$latest_run" ] && [ -f "$latest_run" ]; then
            echo "最新ログ: $latest_run"
            python3 -c "
import json
with open('$latest_run') as f:
    d = json.load(f)
    print(f\"  実行日時: {d.get('started_at', 'N/A')}\")
    print(f\"  生成数: {d.get('generated_count', 0)}\")
    print(f\"  採用数: {d.get('accepted_count', 0)}\")
    print(f\"  棄却数: {d.get('rejected_count', 0)}\")
    rate = d.get('acceptance_rate', 0) * 100
    print(f\"  採用率: {rate:.1f}%\")
"
        else
            echo "実行ログがありません"
        fi

        echo ""
        echo "=== ログファイル ==="
        if [ -f "$LOG_DIR/sage_scheduler.log" ]; then
            echo "スケジューラログ: $(wc -l < "$LOG_DIR/sage_scheduler.log") 行"
            echo "--- 最新5行 ---"
            tail -5 "$LOG_DIR/sage_scheduler.log"
        fi
        ;;

    run)
        echo "=== SAGE 生成 手動実行 ==="
        cd "$PROJECT_ROOT"

        # ログローテーション
        rotate_logs "$LOG_DIR/sage_scheduler.log"
        cleanup_old_logs

        target=${2:-10}
        echo "目標生成数: $target"
        echo ""

        "$PROJECT_ROOT/venv/bin/python" scripts/sage/cli.py \
            --strategy epgen_first \
            --target "$target" \
            --execute
        ;;

    test)
        echo "=== SAGE 生成 モックテスト ==="
        cd "$PROJECT_ROOT"

        target=${2:-3}
        echo "目標生成数: $target（モックモード）"
        echo ""

        "$PROJECT_ROOT/venv/bin/python" scripts/sage/cli.py \
            --strategy epgen_first \
            --target "$target" \
            --mock \
            --dry-run
        ;;

    rotate)
        echo "=== ログローテーション ==="
        rotate_logs "$LOG_DIR/sage_scheduler.log"
        rotate_logs "$LOG_DIR/sage_scheduler_error.log"
        cleanup_old_logs
        echo "完了"
        ;;

    *)
        echo "SAGE エピソード生成スケジューラ管理 (Smart Adaptive Generation Engine)"
        echo ""
        echo "使用方法:"
        echo "  $0 start      自動実行開始（毎日4:00）"
        echo "  $0 stop       自動実行停止"
        echo "  $0 status     状態確認"
        echo "  $0 run        手動実行（10件）"
        echo "  $0 run 5      手動実行（5件）"
        echo "  $0 test       モックテスト（API不要）"
        echo "  $0 rotate     ログローテーション"
        ;;
esac
