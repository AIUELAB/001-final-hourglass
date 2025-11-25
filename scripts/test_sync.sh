#!/bin/bash
# 同期テスト実行スクリプト

PROJECT_DIR="/Users/admin/Documents/AIUELAB/001-final-hourglass"
echo "PDCAガーディアン ルール同期テスト実行"
echo "======================================"

# 同期スクリプトを実行
bash "$PROJECT_DIR/scripts/run_daily_sync.sh"

# 結果確認
if [ $? -eq 0 ]; then
    echo -e "\n✅ テスト成功！"
    echo "最新のログ："
    LATEST_LOG=$(ls -t $PROJECT_DIR/logs/cron/sync_*.log 2>/dev/null | head -1)
    if [ -n "$LATEST_LOG" ]; then
        tail -n 20 "$LATEST_LOG"
    fi
else
    echo -e "\n❌ テスト失敗"
    echo "エラーログを確認してください："
    LATEST_LOG=$(ls -t $PROJECT_DIR/logs/cron/sync_*.log 2>/dev/null | head -1)
    if [ -n "$LATEST_LOG" ]; then
        tail -n 50 "$LATEST_LOG"
    fi
fi
