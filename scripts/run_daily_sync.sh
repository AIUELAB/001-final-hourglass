#!/bin/bash
# PDCAガーディアン 日次同期実行スクリプト

PROJECT_DIR="/Users/admin/Documents/AIUELAB/001-final-hourglass"
LOG_DIR="$PROJECT_DIR/logs/cron"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/sync_$TIMESTAMP.log"
SUMMARY_FILE="$LOG_DIR/sync_summary.log"

# ログディレクトリ作成
mkdir -p "$LOG_DIR"

# 環境設定
export PATH="/usr/local/bin:/usr/bin:/bin"
cd "$PROJECT_DIR" || exit 1

# ログヘッダー
echo "=====================================" >> "$LOG_FILE"
echo "PDCAガーディアン ルール同期" >> "$LOG_FILE"
echo "実行日時: $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"
echo "=====================================" >> "$LOG_FILE"

# Python仮想環境のアクティベート（もし存在すれば）
if [ -f "$PROJECT_DIR/venv/bin/activate" ]; then
    source "$PROJECT_DIR/venv/bin/activate"
fi

# 同期実行
echo "同期開始..." >> "$LOG_FILE"
python3 "$PROJECT_DIR/rule_sync_system.py" >> "$LOG_FILE" 2>&1
SYNC_EXIT_CODE=$?

# 結果記録
if [ $SYNC_EXIT_CODE -eq 0 ]; then
    echo "✅ 同期成功: $(date '+%Y-%m-%d %H:%M:%S')" >> "$SUMMARY_FILE"
    echo "同期が正常に完了しました" >> "$LOG_FILE"

    # 成功通知（macOS通知センター）
    if command -v osascript &> /dev/null; then
        osascript -e 'display notification "PDCAガーディアンのルール同期が完了しました" with title "同期成功"'
    fi
else
    echo "❌ 同期失敗: $(date '+%Y-%m-%d %H:%M:%S')" >> "$SUMMARY_FILE"
    echo "エラーが発生しました (Exit Code: $SYNC_EXIT_CODE)" >> "$LOG_FILE"

    # エラー通知（macOS通知センター）
    if command -v osascript &> /dev/null; then
        osascript -e 'display notification "PDCAガーディアンのルール同期でエラーが発生しました" with title "同期失敗" sound name "Glass"'
    fi
fi

# 古いログファイルの削除（30日以上前）
find "$LOG_DIR" -name "sync_*.log" -mtime +30 -delete

echo "=====================================" >> "$LOG_FILE"
echo "実行完了: $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"
echo "=====================================" >> "$LOG_FILE"

exit $SYNC_EXIT_CODE